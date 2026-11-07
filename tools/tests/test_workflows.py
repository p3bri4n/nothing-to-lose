"""Static checks on .github/workflows/*.yml (text and regex only, no YAML parser).

Run with: ``python -m unittest discover -s tools/tests`` (or ``just tools-test``).
"""

from __future__ import annotations

import pathlib
import re
import unittest

WORKFLOWS_DIR = (
    pathlib.Path(__file__).resolve().parent.parent.parent / ".github" / "workflows"
)

# `uses: owner/repo[/path]@ref [# comment]`; local actions (`./...`) are not matched.
USES_RE = re.compile(
    r"^\s*(?:-\s+)?uses:\s*(?P<action>[^\s@#]+)@(?P<ref>[^\s#]+)\s*(?P<comment>#.*)?$"
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_COMMENT_RE = re.compile(r"^#\s*v?\d+(\.\d+)*\S*\s*$")
MISE_ACTION = "jdx/mise-action"


def workflow_files() -> list[pathlib.Path]:
    return sorted(WORKFLOWS_DIR.glob("*.yml"))


def read_lines(path: pathlib.Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def on_block(lines: list[str]) -> list[str]:
    """Return the lines of the top-level ``on:`` block (until the next top-level key)."""
    block: list[str] = []
    inside = False
    for line in lines:
        if re.match(r"^on:\s*$", line):
            inside = True
            continue
        if inside:
            if line and not line[0].isspace() and not line.startswith("#"):
                break
            block.append(line)
    if not inside:
        raise AssertionError("no top-level 'on:' block")
    return block


class WorkflowFilesTests(unittest.TestCase):
    def test_workflows_exist(self):
        names = {p.name for p in workflow_files()}
        self.assertTrue({"ci.yml", "deploy-viewer.yml", "gpu-eval.yml"} <= names, names)


class ActionPinningTests(unittest.TestCase):
    def test_every_action_is_pinned_by_sha_with_version_comment(self):
        seen = 0
        for path in workflow_files():
            for number, line in enumerate(read_lines(path), start=1):
                if line.lstrip().startswith("#"):
                    continue
                if not re.match(r"^\s*(?:-\s+)?uses:", line):
                    continue
                where = f"{path.name}:{number}"
                match = USES_RE.match(line)
                self.assertIsNotNone(
                    match, f"{where}: cannot parse 'uses:' line: {line!r}"
                )
                if match["action"].startswith("./"):
                    continue
                seen += 1
                self.assertRegex(
                    match["ref"], SHA_RE, f"{where}: not pinned by a 40-hex SHA"
                )
                self.assertIsNotNone(
                    match["comment"], f"{where}: version comment missing"
                )
                self.assertRegex(
                    match["comment"],
                    VERSION_COMMENT_RE,
                    f"{where}: bad version comment",
                )
        self.assertGreater(seen, 0)


class MiseActionTests(unittest.TestCase):
    def test_same_mise_version_everywhere(self):
        versions: dict[str, str] = {}
        for path in workflow_files():
            lines = read_lines(path)
            for index, line in enumerate(lines):
                if MISE_ACTION not in line or "uses:" not in line:
                    continue
                version = None
                # The `with:` block is the run of lines indented deeper than the `uses:` step.
                for following in lines[index + 1 :]:
                    if re.match(r"^\s*-\s", following):
                        break
                    match = re.match(r"^\s+version:\s*(\S+)\s*$", following)
                    if match:
                        version = match[1].strip("\"'")
                        break
                self.assertIsNotNone(
                    version, f"{path.name}:{index + 1}: mise 'version:' missing"
                )
                versions[f"{path.name}:{index + 1}"] = version
        self.assertGreaterEqual(len(versions), 2, versions)
        self.assertEqual(len(set(versions.values())), 1, versions)


class SecurityTests(unittest.TestCase):
    def test_gpu_eval_is_not_triggered_by_pull_request(self):
        block = on_block(read_lines(WORKFLOWS_DIR / "gpu-eval.yml"))
        code = [line for line in block if not line.lstrip().startswith("#")]
        self.assertFalse([line for line in code if "pull_request" in line], code)
        self.assertTrue(
            [line for line in code if "push" in line],
            "gpu-eval.yml should keep its push trigger",
        )

    def test_checkout_does_not_persist_credentials(self):
        for path in workflow_files():
            lines = read_lines(path)
            for index, line in enumerate(lines):
                if "actions/checkout@" not in line:
                    continue
                window = []
                for following in lines[index + 1 :]:
                    if re.match(r"^\s*-\s", following):
                        break
                    window.append(following)
                self.assertTrue(
                    any(
                        re.match(r"^\s+persist-credentials:\s*false\s*$", w)
                        for w in window
                    ),
                    f"{path.name}:{index + 1}: persist-credentials: false missing",
                )


class CiJobTests(unittest.TestCase):
    def test_ci_has_ci_cpu_job(self):
        lines = read_lines(WORKFLOWS_DIR / "ci.yml")
        self.assertTrue(any(re.match(r"^  ci-cpu:\s*$", line) for line in lines))

    def test_checklist_step_is_last_step_of_ci(self):
        lines = read_lines(WORKFLOWS_DIR / "ci.yml")
        names = [line.strip() for line in lines if re.match(r"^      - name:", line)]
        self.assertTrue(
            names[-1].endswith("Liste de contrôle de la pull request"), names[-1]
        )


if __name__ == "__main__":
    unittest.main()
