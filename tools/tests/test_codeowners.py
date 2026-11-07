"""Tests for the server-side CODEOWNERS barrier (decision 0021, step E10b).

Hermetic: only reads files of the repository.
"""

from __future__ import annotations

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CODEOWNERS = ROOT / ".github" / "CODEOWNERS"
RULESET = ROOT / "infra" / "terraform" / "ruleset.tf"
VARIABLES = ROOT / "infra" / "terraform" / "variables.tf"
TFVARS_EXAMPLE = ROOT / "infra" / "terraform" / "terraform.tfvars.example"

OWNER = re.compile(r"^@[A-Za-z0-9]+(-[A-Za-z0-9]+)*(/[A-Za-z0-9_.-]+)?$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def rules() -> list[tuple[str, list[str]]]:
    parsed = []
    for raw in CODEOWNERS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pattern, *owners = line.split()
        parsed.append((pattern, owners))
    return parsed


def expected_owner() -> str:
    """``github_owner`` from variables.tf (default) or, failing that, the tfvars example."""
    variables = VARIABLES.read_text(encoding="utf-8")
    block = re.search(r'variable "github_owner" \{(.*?)\n\}', variables, re.S)
    if block:
        default = re.search(r'default\s*=\s*"([^"]+)"', block.group(1))
        if default:
            return default.group(1)
    example = re.search(
        r'^github_owner\s*=\s*"([^"]+)"',
        TFVARS_EXAMPLE.read_text(encoding="utf-8"),
        re.M,
    )
    if not example:
        raise AssertionError("github_owner not found in variables.tf or tfvars example")
    return example.group(1)


class CodeownersTests(unittest.TestCase):
    def test_file_exists(self):
        self.assertTrue(CODEOWNERS.is_file(), ".github/CODEOWNERS is missing")

    def test_minimal_syntax(self):
        parsed = rules()
        self.assertTrue(parsed, "CODEOWNERS has no rule")
        for pattern, owners in parsed:
            with self.subTest(pattern=pattern):
                self.assertTrue(owners, f"rule {pattern!r} has no owner")
                for owner in owners:
                    self.assertTrue(
                        OWNER.match(owner) or EMAIL.match(owner),
                        f"invalid owner {owner!r}",
                    )

    def test_catch_all_rule_belongs_to_the_repository_owner(self):
        catch_all = [owners for pattern, owners in rules() if pattern == "*"]
        self.assertTrue(catch_all, "no '*' rule: some paths would have no owner")
        # The last matching rule wins on GitHub: check the last '*' rule.
        self.assertEqual(catch_all[-1], [f"@{expected_owner()}"])

    def test_ruleset_requires_code_owner_review(self):
        text = RULESET.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^\s*require_code_owner_review\s*=\s*true\s*$")


if __name__ == "__main__":
    unittest.main()
