"""Tests for tools/hooks/session_start.py (guard error warning and JSON output).

Hermetic: a throw-away project directory; ``git`` failing there only gives "?" values.

Run with: ``python3 -m unittest discover -s tools/tests`` (or ``just tools-test``).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "hooks"))

import session_start

SCRIPT = pathlib.Path(session_start.__file__).resolve()


class GuardErrorCountTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.log = self.root / ".cache" / "hooks" / "guard.log"

    def write_log(self, text: str) -> None:
        self.log.parent.mkdir(parents=True)
        self.log.write_text(text, encoding="utf-8")

    def test_no_log_is_zero(self) -> None:
        self.assertEqual(session_start.guard_error_count(self.root), 0)

    def test_only_hook_error_lines_are_counted(self) -> None:
        self.write_log(
            "2026-11-07T10:00:00+01:00 BLOCKED rule=no-verify command=git commit -n\n"
            "2026-11-07T10:01:00+01:00 hook error: invalid JSON on stdin, command allowed\n"
            "2026-11-07T10:02:00+01:00 current branch unknown: git push\n"
            "2026-11-07T10:03:00+01:00 hook error: RuntimeError('x'), command refused\n"
        )
        self.assertEqual(session_start.guard_error_count(self.root), 2)

    def test_empty_or_unreadable_log_is_zero(self) -> None:
        self.write_log("")
        self.assertEqual(session_start.guard_error_count(self.root), 0)
        self.log.write_bytes(b"\xff\xfe hook error\n")  # not UTF-8: still read
        self.assertEqual(session_start.guard_error_count(self.root), 1)
        self.log.unlink()
        self.log.mkdir()  # a directory is not a log
        self.assertEqual(session_start.guard_error_count(self.root), 0)


class TokenWarningTest(unittest.TestCase):
    def test_machine_account_environment_has_no_warning(self) -> None:
        self.assertIsNone(session_start.token_warning({"GH_TOKEN": "ghp_secret"}))

    def test_github_token_present_warns(self) -> None:
        text = session_start.token_warning({"GH_TOKEN": "a", "GITHUB_TOKEN": "b"})
        self.assertIn("GITHUB_TOKEN est présent", text)
        self.assertNotIn("GH_TOKEN est absent", text)

    def test_gh_token_absent_warns(self) -> None:
        text = session_start.token_warning({})
        self.assertIn("GH_TOKEN est absent", text)
        self.assertNotIn("GITHUB_TOKEN est présent", text)

    def test_empty_values_count_as_absent_or_unset(self) -> None:
        text = session_start.token_warning({"GH_TOKEN": "", "GITHUB_TOKEN": ""})
        self.assertIn("GH_TOKEN est absent", text)
        self.assertNotIn("GITHUB_TOKEN est présent", text)

    def test_both_problems_are_reported_but_no_value_is_shown(self) -> None:
        text = session_start.token_warning({"GITHUB_TOKEN": "ghp_SECRETVALUE"})
        self.assertIn("GITHUB_TOKEN est présent", text)
        self.assertIn("GH_TOKEN est absent", text)
        self.assertNotIn("SECRETVALUE", text)

    def test_build_includes_the_warning_but_never_the_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for full in (False, True):
                text = session_start.build(
                    pathlib.Path(tmp), full, {"GITHUB_TOKEN": "ghp_SECRETVALUE"}
                )
                self.assertIn("Identité GitHub", text)
                self.assertNotIn("SECRETVALUE", text)
                clean = session_start.build(pathlib.Path(tmp), full, {"GH_TOKEN": "x"})
                self.assertNotIn("Identité GitHub", clean)


class BuildTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)

    def log(self, text: str) -> None:
        log = self.root / ".cache" / "hooks" / "guard.log"
        log.parent.mkdir(parents=True)
        log.write_text(text, encoding="utf-8")

    def test_no_warning_without_errors(self) -> None:
        self.log("2026-11-07T10:00:00+01:00 BLOCKED rule=push-force command=x\n")
        for full in (False, True):
            self.assertNotIn("hook error", session_start.build(self.root, full))
            self.assertNotIn("Garde-fou", session_start.build(self.root, full))

    def test_warning_gives_the_count(self) -> None:
        self.log("a hook error: x\nb\nc hook error: y\nd hook error: z\n")
        for full in (False, True):
            text = session_start.build(self.root, full)
            self.assertIn("Garde-fou Bash : 3 ligne(s) « hook error »", text)
            self.assertIn(".cache/hooks/guard.log", text)
            self.assertIn("garde-fous-bash.md", text)

    def test_main_prints_the_warning_in_both_fields(self) -> None:
        self.log("hook error: boom, command refused (git/gh)\n")
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.root)},
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertIn("1 ligne(s) « hook error »", output["systemMessage"])
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("1 ligne(s) « hook error »", context)


if __name__ == "__main__":
    unittest.main()
