"""Tests for tools/check_pr_checklist.py.

Run with: ``python -m unittest discover -s tools/tests`` (or ``just tools-test``).
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import sys
import unittest
from unittest import mock

TOOLS_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS_DIR))

import check_pr_checklist as cpc

TEMPLATE = TOOLS_DIR.parent / ".github" / "pull_request_template.md"
TITLE = "## Liste de contrôle"


def body(*boxes: str, title: str = TITLE) -> str:
    return "## Résumé\n\nTexte.\n\n" + title + "\n\n" + "\n".join(boxes) + "\n"


class CheckBodyTests(unittest.TestCase):
    def test_section_missing(self):
        code, messages = cpc.check_body("## Résumé\n\nRien.\n")
        self.assertEqual(code, 1)
        self.assertIn("absente", messages[0])

    def test_empty_body(self):
        code, messages = cpc.check_body("")
        self.assertEqual(code, 1)
        self.assertIn("absente", messages[0])

    def test_section_empty(self):
        code, messages = cpc.check_body(TITLE + "\n\nRien ici.\n\n## Autre\n- [ ] x\n")
        self.assertEqual(code, 1)
        self.assertIn("vide", messages[0])

    def test_all_checked(self):
        code, _ = cpc.check_body(body("- [x] a", "- [x] b"))
        self.assertEqual(code, 0)

    def test_uppercase_x(self):
        code, _ = cpc.check_body(body("- [X] a", "- [x] b"))
        self.assertEqual(code, 0)

    def test_one_unchecked_is_listed(self):
        code, messages = cpc.check_body(body("- [x] a", "- [ ] manquante", "- [x] c"))
        self.assertEqual(code, 1)
        self.assertIn("Liste de contrôle incomplète", messages[0])
        self.assertEqual(messages[1:], ["- [ ] manquante"])

    def test_crlf(self):
        text = body("- [x] a", "- [ ] b").replace("\n", "\r\n")
        code, messages = cpc.check_body(text)
        self.assertEqual(code, 1)
        self.assertEqual(messages[1:], ["- [ ] b"])
        code, _ = cpc.check_body(body("- [x] a", "- [X] b").replace("\n", "\r\n"))
        self.assertEqual(code, 0)

    def test_whitespace_tolerance(self):
        text = "##   Liste de contrôle  \t\n\n  -   [x]   a  \n\t- [X] b\n"
        code, _ = cpc.check_body(text)
        self.assertEqual(code, 0)

    def test_boxes_outside_section_ignored(self):
        text = (
            "## Résumé\n- [ ] avant\n\n"
            + TITLE
            + "\n- [x] a\n- [x] b\n\n## Suite\n- [ ] après\n"
        )
        code, _ = cpc.check_body(text)
        self.assertEqual(code, 0)

    def test_section_ends_at_next_heading(self):
        text = TITLE + "\n- [x] a\n## Notes\n- [ ] hors section\n"
        code, _ = cpc.check_body(text)
        self.assertEqual(code, 0)

    def test_section_ends_at_end_of_body(self):
        code, _ = cpc.check_body("## Résumé\n\n" + TITLE + "\n- [x] a\n- [ ] b")
        self.assertEqual(code, 1)

    def test_subheading_does_not_end_section(self):
        text = TITLE + "\n- [x] a\n### Détail\n- [ ] b\n"
        code, _ = cpc.check_body(text)
        self.assertEqual(code, 1)

    def test_title_must_be_exact(self):
        for title in (
            "## Liste de controle",
            "## liste de contrôle",
            "# Liste de contrôle",
        ):
            with self.subTest(title=title):
                code, messages = cpc.check_body(body("- [x] a", title=title))
                self.assertEqual(code, 1)
                self.assertIn("absente", messages[0])

    def test_html_comments_ignored(self):
        text = (
            TITLE
            + "\n<!-- Exemple : - [ ] case de démonstration -->\n- [x] a\n"
            + "<!--\n- [ ] multi-ligne\n-->\n"
        )
        code, _ = cpc.check_body(text)
        self.assertEqual(code, 0)


class CheckPullRequestTests(unittest.TestCase):
    def test_dependabot_exempt(self):
        code, messages = cpc.check_pull_request("", "dependabot[bot]")
        self.assertEqual(code, 0)
        self.assertIn("dependabot[bot]", messages[0])

    def test_other_author_checked(self):
        code, _ = cpc.check_pull_request("", "someone")
        self.assertEqual(code, 1)

    def test_lookalike_author_not_exempt(self):
        code, _ = cpc.check_pull_request("", "dependabot")
        self.assertEqual(code, 1)


class MainTests(unittest.TestCase):
    def run_main(self, env: dict[str, str]) -> tuple[int, str]:
        out = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True):
            with contextlib.redirect_stdout(out):
                code = cpc.main()
        return code, out.getvalue()

    def test_pr_body_absent(self):
        code, out = self.run_main({})
        self.assertEqual(code, 1)
        self.assertIn("absente", out)

    def test_reads_environment(self):
        code, _ = self.run_main({"PR_BODY": body("- [x] a")})
        self.assertEqual(code, 0)
        code, out = self.run_main({"PR_BODY": body("- [ ] a")})
        self.assertEqual(code, 1)
        self.assertIn("Liste de contrôle incomplète", out)

    def test_dependabot_from_environment(self):
        code, _ = self.run_main({"PR_AUTHOR": "dependabot[bot]"})
        self.assertEqual(code, 0)


@unittest.skipUnless(TEMPLATE.is_file(), "no .github/pull_request_template.md yet")
class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.text = TEMPLATE.read_text(encoding="utf-8")

    def test_template_unchanged_fails_with_seven_boxes(self):
        code, messages = cpc.check_body(self.text)
        self.assertEqual(code, 1)
        self.assertEqual(len(messages) - 1, 7)

    def test_template_fully_checked_passes(self):
        section = cpc.extract_section(self.text)
        self.assertIsNotNone(section)
        self.assertEqual(len(cpc.parse_checkboxes(section)), 7)
        ticked = self.text.replace("- [ ]", "- [x]")
        code, _ = cpc.check_body(ticked)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
