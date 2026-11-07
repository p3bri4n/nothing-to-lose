"""Tests for tools/check_tool_versions.py.

Hermetic: no real tool is ever executed (``subprocess.run`` is mocked) and the
configuration files live in a temporary directory.

Run with: ``python -m unittest discover -s tools/tests`` (or ``just tools-test``).
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import check_tool_versions as cvt

# Real ``--version`` outputs of the pinned versions (captured 2026-11-07).
# Keyed by binary name. Multi-line outputs are kept verbatim because the
# patterns rely on ``re.MULTILINE`` for them.
FIXTURES: dict[str, str] = {
    "node": "v24.22.2\n",
    "python": "Python 3.14.10\n",
    "rustc": "rustc 1.99.1 (58cf8f9c3 2026-10-13)\n",
    "uv": "uv 0.13.7 (x86_64-unknown-linux-gnu)\n",
    "just": "just 1.59.0\n",
    "terraform": "Terraform v1.17.1\non linux_amd64\n\n",
    "gitleaks": "gitleaks version 8.30.1\n",
    "actionlint": (
        "1.7.12\n"
        "installed by downloading from release page\n"
        "built with go1.26.1 compiler for linux/amd64\n"
    ),
    "ruff": "ruff 0.17.3\n",
    "taplo": "taplo 0.10.0\n",
    "prettier": "3.9.10\n",
    "shfmt": "v3.14.1\n",
    "shellcheck": (
        "ShellCheck - shell script analysis tool\n"
        "version: 0.11.0\n"
        "license: GNU General Public License, version 3\n"
        "website: https://www.shellcheck.net\n"
    ),
    "gh": (
        "gh version 2.103.3 (2026-10-26)\n"
        "https://github.com/cli/cli/releases/tag/v2.103.3\n"
    ),
    "claude": "2.1.318 (Claude Code)\n",
}

# Version expected for each fixture, keyed by binary name.
FIXTURE_VERSIONS: dict[str, str] = {
    "node": "24.22.2",
    "python": "3.14.10",
    "rustc": "1.99.1",
    "uv": "0.13.7",
    "just": "1.59.0",
    "terraform": "1.17.1",
    "gitleaks": "8.30.1",
    "actionlint": "1.7.12",
    "ruff": "0.17.3",
    "taplo": "0.10.0",
    "prettier": "3.9.10",
    "shfmt": "3.14.1",
    "shellcheck": "0.11.0",
    "gh": "2.103.3",
    "claude": "2.1.318",
}

# mise.toml body matching the fixtures: mixes bare keys, backend-prefixed keys
# and the table form (rust) as in the real file.
MISE_TOML = """\
[tools]
node = "24.22.2"
python = "3.14.10"
rust = { version = "1.99.1", components = "rustfmt,clippy" }
"aqua:astral-sh/uv" = "0.13.7"
"aqua:casey/just" = "1.59.0"
"aqua:hashicorp/terraform" = "1.17.1"
"aqua:gitleaks/gitleaks" = "8.30.1"
"aqua:rhysd/actionlint" = "1.7.12"
"aqua:astral-sh/ruff" = "0.17.3"
"aqua:tamasfe/taplo" = "0.10.0"
"npm:prettier" = "3.9.10"
"aqua:mvdan/sh" = "3.14.1"
"aqua:koalaman/shellcheck" = "0.11.0"
"aqua:cli/cli" = "2.103.3"
"aqua:anthropics/claude-code" = "2.1.318"
"""

TOOLCHAIN_TOML = '[toolchain]\nchannel = "1.99.1"\n'


def completed(stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    """Build the object ``subprocess.run`` would return."""
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout=stdout, stderr=stderr
    )


def fake_run(outputs: dict[str, str | BaseException]):
    """Return a ``subprocess.run`` replacement answering from ``outputs``.

    A value that is an exception instance is raised instead of returned.
    """

    def run(cmd, **kwargs):
        value = outputs[cmd[0]]
        if isinstance(value, BaseException):
            raise value
        return completed(stdout=value)

    return mock.Mock(side_effect=run)


class ParseVersionTests(unittest.TestCase):
    def test_every_tool_has_a_fixture(self):
        # Adding a tool to TOOLS must come with a real-output fixture.
        binaries = {spec.binary for spec in cvt.TOOLS.values()}
        self.assertEqual(binaries, set(FIXTURES))
        self.assertEqual(set(FIXTURES), set(FIXTURE_VERSIONS))

    def test_parse_real_outputs(self):
        for spec in cvt.TOOLS.values():
            with self.subTest(binary=spec.binary):
                self.assertEqual(
                    cvt.parse_version(FIXTURES[spec.binary], spec.pattern),
                    FIXTURE_VERSIONS[spec.binary],
                )

    def test_multiline_outputs(self):
        # The version is not on the first line (shellcheck, gh) or is followed
        # by extra lines (actionlint, terraform): MULTILINE anchors must cope.
        self.assertEqual(
            cvt.parse_version(FIXTURES["shellcheck"], cvt.TOOLS["shellcheck"].pattern),
            "0.11.0",
        )
        self.assertEqual(
            cvt.parse_version(FIXTURES["gh"], cvt.TOOLS["cli"].pattern), "2.103.3"
        )
        self.assertEqual(
            cvt.parse_version(FIXTURES["actionlint"], cvt.TOOLS["actionlint"].pattern),
            "1.7.12",
        )
        self.assertEqual(
            cvt.parse_version(FIXTURES["terraform"], cvt.TOOLS["terraform"].pattern),
            "1.17.1",
        )

    def test_gh_url_line_is_not_taken_for_the_version(self):
        # The release URL on line 2 contains "v2.103.3" too; the pattern is
        # anchored on "gh version" so a different line-1 version must win.
        output = (
            "gh version 2.103.3 (2026-10-26)\n"
            "https://github.com/cli/cli/releases/tag/v9.9.9\n"
        )
        self.assertEqual(cvt.parse_version(output, cvt.TOOLS["cli"].pattern), "2.103.3")

    def test_crlf_output(self):
        output = FIXTURES["shellcheck"].replace("\n", "\r\n")
        self.assertEqual(
            cvt.parse_version(output, cvt.TOOLS["shellcheck"].pattern), "0.11.0"
        )

    def test_unrecognised_output_returns_none(self):
        for output in ("", "\n", "command not found", "usage: tool [options]\n"):
            for key, spec in cvt.TOOLS.items():
                with self.subTest(output=output, tool=key):
                    self.assertIsNone(cvt.parse_version(output, spec.pattern))

    def test_other_tools_output_is_rejected(self):
        # A tool whose binary was shadowed by another one must not parse.
        self.assertIsNone(
            cvt.parse_version(FIXTURES["gh"], cvt.TOOLS["gitleaks"].pattern)
        )
        self.assertIsNone(cvt.parse_version(FIXTURES["just"], cvt.TOOLS["uv"].pattern))
        self.assertIsNone(
            cvt.parse_version(FIXTURES["ruff"], cvt.TOOLS["taplo"].pattern)
        )

    def test_claude_requires_the_suffix(self):
        pattern = cvt.TOOLS["claude-code"].pattern
        self.assertIsNone(cvt.parse_version("2.1.318\n", pattern))
        self.assertEqual(cvt.parse_version("2.1.318 (Claude Code)", pattern), "2.1.318")

    def test_patterns_have_exactly_one_group(self):
        import re

        for key, spec in cvt.TOOLS.items():
            with self.subTest(tool=key):
                self.assertEqual(re.compile(spec.pattern).groups, 1)

    def test_only_claude_is_local_only(self):
        local = {k for k, s in cvt.TOOLS.items() if s.local_only}
        self.assertEqual(local, {"claude-code"})


class HelpersTests(unittest.TestCase):
    def test_tool_key(self):
        self.assertEqual(cvt.tool_key("node"), "node")
        self.assertEqual(cvt.tool_key("aqua:astral-sh/uv"), "uv")
        self.assertEqual(cvt.tool_key("npm:prettier"), "prettier")
        self.assertEqual(cvt.tool_key("aqua:cli/cli"), "cli")
        self.assertEqual(cvt.tool_key("aqua:mvdan/sh"), "sh")

    def test_expected_version(self):
        self.assertEqual(cvt.expected_version("1.2.3"), "1.2.3")
        self.assertEqual(
            cvt.expected_version({"version": "1.99.1", "components": "rustfmt"}),
            "1.99.1",
        )

    def test_expected_version_rejects_unreadable_entries(self):
        for bad in ({}, {"components": "x"}, {"version": 3}, 42, None, ["1.2.3"]):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                cvt.expected_version(bad)  # type: ignore[arg-type]


class CompareTests(unittest.TestCase):
    def test_same_version_is_ok(self):
        self.assertEqual(cvt.compare("1.2.3", "1.2.3"), "ok")

    def test_different_version_is_mismatch(self):
        self.assertEqual(cvt.compare("1.2.3", "1.2.4"), "mismatch")
        self.assertEqual(cvt.compare("1.2.3", "1.2"), "mismatch")
        self.assertEqual(cvt.compare("1.2.3", "01.2.3"), "mismatch")

    def test_no_version_is_missing(self):
        self.assertEqual(cvt.compare("1.2.3", None), "missing")


class FormatLineTests(unittest.TestCase):
    def test_columns(self):
        line = cvt.format_line("node", "24.22.2", "24.22.2", "ok")
        self.assertEqual(line, "node        24.22.2   24.22.2   ok")
        self.assertEqual(line.split(), ["node", "24.22.2", "24.22.2", "ok"])

    def test_missing_version_shows_a_dash(self):
        line = cvt.format_line("gh", "2.103.3", None, "missing (not found in PATH)")
        self.assertEqual(line.split()[:3], ["gh", "2.103.3", "-"])
        self.assertTrue(line.endswith("missing (not found in PATH)"))

    def test_columns_are_aligned_for_typical_names(self):
        a = cvt.format_line("just", "1.59.0", "1.59.0", "ok")
        b = cvt.format_line("actionlint", "1.7.12", "1.7.12", "ok")
        self.assertEqual(a.index("1.59.0"), b.index("1.7.12"))


class RustToolchainTests(unittest.TestCase):
    def test_consistent(self):
        self.assertIsNone(
            cvt.check_rust_toolchain("1.99.1", {"toolchain": {"channel": "1.99.1"}})
        )

    def test_different_channel(self):
        error = cvt.check_rust_toolchain("1.99.1", {"toolchain": {"channel": "1.98.0"}})
        self.assertIsNotNone(error)
        assert error is not None
        self.assertIn("1.98.0", error)
        self.assertIn("1.99.1", error)

    def test_symbolic_channel_is_rejected(self):
        # "stable" would float: only the exact pinned version is accepted.
        self.assertIsNotNone(
            cvt.check_rust_toolchain("1.99.1", {"toolchain": {"channel": "stable"}})
        )

    def test_missing_channel_or_section(self):
        self.assertIsNotNone(cvt.check_rust_toolchain("1.99.1", {"toolchain": {}}))
        self.assertIsNotNone(cvt.check_rust_toolchain("1.99.1", {}))

    def test_rust_absent_from_mise(self):
        # main() passes "" when mise.toml has no rust entry.
        self.assertIsNotNone(
            cvt.check_rust_toolchain("", {"toolchain": {"channel": "1.99.1"}})
        )


class RunVersionTests(unittest.TestCase):
    SPEC = cvt.TOOLS["just"]

    def run_with(self, **kwargs):
        with mock.patch.object(cvt.subprocess, "run", **kwargs) as run:
            return cvt.run_version(self.SPEC), run

    def test_success(self):
        result, run = self.run_with(return_value=completed(stdout="just 1.59.0\n"))
        self.assertEqual(result, ("1.59.0", ""))
        cmd = run.call_args.args[0]
        self.assertEqual(cmd, ["just", "--version"])
        self.assertEqual(run.call_args.kwargs["timeout"], cvt.TIMEOUT_SECONDS)

    def test_version_on_stderr(self):
        result, _ = self.run_with(return_value=completed(stderr="just 1.59.0\n"))
        self.assertEqual(result, ("1.59.0", ""))

    def test_tool_not_found(self):
        result, _ = self.run_with(side_effect=FileNotFoundError("just"))
        self.assertEqual(result, (None, "not found in PATH"))

    def test_unreadable_output(self):
        for stdout in ("", "garbage\n", "just: error while loading\n"):
            with self.subTest(stdout=stdout):
                result, _ = self.run_with(return_value=completed(stdout=stdout))
                self.assertEqual(result, (None, "unparseable output"))

    def test_timeout(self):
        result, _ = self.run_with(
            side_effect=subprocess.TimeoutExpired(cmd="just", timeout=20)
        )
        self.assertEqual(result[0], None)
        self.assertIn("timeout", result[1])

    def test_non_executable_binary_is_reported_not_raised(self):
        # A non-executable file earlier in PATH raises PermissionError: it must
        # be reported as a failure, not crash the script with a traceback.
        result, _ = self.run_with(side_effect=PermissionError("just"))
        self.assertIsNone(result[0])

    def test_uses_the_spec_args(self):
        spec = cvt.ToolSpec("foo", r"^foo (\d+\.\d+\.\d+)", args=("version", "-s"))
        with mock.patch.object(
            cvt.subprocess, "run", return_value=completed(stdout="foo 1.0.0")
        ) as run:
            self.assertEqual(cvt.run_version(spec), ("1.0.0", ""))
        self.assertEqual(run.call_args.args[0], ["foo", "version", "-s"])


class MainTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        self.write(MISE_TOML, TOOLCHAIN_TOML)
        patcher = mock.patch.object(cvt, "REPO_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, mise: str, toolchain: str) -> None:
        (self.root / "mise.toml").write_text(mise, encoding="utf-8")
        (self.root / "rust-toolchain.toml").write_text(toolchain, encoding="utf-8")

    def invoke(self, argv, outputs=None):
        """Run main(); return (exit code, stdout lines, stderr text, run mock)."""
        run = fake_run(FIXTURES if outputs is None else outputs)
        out, err = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(cvt.subprocess, "run", run),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            code = cvt.main(argv)
        return code, out.getvalue().splitlines(), err.getvalue(), run

    def called_binaries(self, run) -> list[str]:
        return [c.args[0][0] for c in run.call_args_list]

    def test_all_ok(self):
        code, lines, err, run = self.invoke([])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(len(lines), len(FIXTURES))
        for line in lines:
            self.assertTrue(line.endswith(" ok"), line)
        self.assertEqual(run.call_count, len(FIXTURES))

    def test_line_format_and_binary_names(self):
        _, lines, _, _ = self.invoke([])
        by_name = {line.split()[0]: line.split() for line in lines}
        # The report uses the binary name (rustc, shfmt, gh), not the mise key.
        self.assertEqual(by_name["rustc"], ["rustc", "1.99.1", "1.99.1", "ok"])
        self.assertEqual(by_name["shfmt"], ["shfmt", "3.14.1", "3.14.1", "ok"])
        self.assertEqual(by_name["gh"], ["gh", "2.103.3", "2.103.3", "ok"])

    def test_report_follows_mise_order(self):
        _, lines, _, _ = self.invoke([])
        self.assertEqual(
            [line.split()[0] for line in lines],
            [
                "node", "python", "rustc", "uv", "just", "terraform", "gitleaks",
                "actionlint", "ruff", "taplo", "prettier", "shfmt", "shellcheck",
                "gh", "claude",
            ],
        )  # fmt: skip

    def test_version_mismatch(self):
        outputs = {**FIXTURES, "just": "just 1.58.0\n"}
        code, lines, _, _ = self.invoke([], outputs)
        self.assertEqual(code, 1)
        just = next(line for line in lines if line.startswith("just"))
        self.assertEqual(just.split(), ["just", "1.59.0", "1.58.0", "mismatch"])
        # Only the faulty tool is flagged.
        self.assertEqual(sum(not line.endswith(" ok") for line in lines), 1)

    def test_tool_absent(self):
        outputs = {**FIXTURES, "gh": FileNotFoundError("gh")}
        code, lines, _, _ = self.invoke([], outputs)
        self.assertEqual(code, 1)
        gh = next(line for line in lines if line.startswith("gh"))
        self.assertEqual(gh.split()[:3], ["gh", "2.103.3", "-"])
        self.assertIn("missing (not found in PATH)", gh)

    def test_unreadable_output(self):
        outputs = {**FIXTURES, "shellcheck": "something unexpected\n"}
        code, lines, _, _ = self.invoke([], outputs)
        self.assertEqual(code, 1)
        line = next(x for x in lines if x.startswith("shellcheck"))
        self.assertIn("missing (unparseable output)", line)

    def test_one_failure_does_not_stop_the_others(self):
        outputs = {**FIXTURES, "node": FileNotFoundError("node")}
        code, lines, _, run = self.invoke([], outputs)
        self.assertEqual(code, 1)
        self.assertEqual(len(lines), len(FIXTURES))
        self.assertEqual(run.call_count, len(FIXTURES))

    def test_rust_toolchain_inconsistent(self):
        self.write(MISE_TOML, '[toolchain]\nchannel = "1.98.0"\n')
        code, lines, err, _ = self.invoke([])
        self.assertEqual(code, 1)
        self.assertIn("rust-toolchain.toml", err)
        self.assertIn("1.98.0", err)
        # The version report is still produced.
        self.assertEqual(len(lines), len(FIXTURES))

    def test_rust_toolchain_without_channel(self):
        self.write(MISE_TOML, "[toolchain]\ncomponents = []\n")
        code, _, err, _ = self.invoke([])
        self.assertEqual(code, 1)
        self.assertIn("differs", err)

    def test_mise_tool_missing_from_tools_table(self):
        self.write(MISE_TOML + '"aqua:foo/bar" = "1.0.0"\n', TOOLCHAIN_TOML)
        code, lines, err, run = self.invoke([])
        self.assertEqual(code, 1)
        self.assertIn("'bar'", err)
        self.assertIn("no entry in TOOLS", err)
        # The unknown tool is never executed; known ones are still checked.
        self.assertNotIn("bar", self.called_binaries(run))
        self.assertEqual(len(lines), len(FIXTURES))

    def test_unknown_tool_detected_with_print_too(self):
        self.write(MISE_TOML + 'baz = "1.0.0"\n', TOOLCHAIN_TOML)
        code, _, err, run = self.invoke(["--print"])
        self.assertEqual(code, 1)
        self.assertIn("'baz'", err)
        run.assert_not_called()

    def test_ci_skips_claude(self):
        code, lines, _, run = self.invoke(["--ci"])
        self.assertEqual(code, 0)
        self.assertNotIn("claude", self.called_binaries(run))
        self.assertEqual(len(lines), len(FIXTURES) - 1)
        self.assertFalse(any(line.startswith("claude") for line in lines))

    def test_without_ci_claude_is_checked(self):
        _, lines, _, run = self.invoke([])
        self.assertIn("claude", self.called_binaries(run))
        self.assertTrue(any(line.startswith("claude") for line in lines))

    def test_ci_ignores_a_wrong_claude(self):
        # Claude Code is absent on CI runners: its absence must not fail --ci.
        outputs = {**FIXTURES, "claude": FileNotFoundError("claude")}
        code, _, _, _ = self.invoke(["--ci"], outputs)
        self.assertEqual(code, 0)
        code, _, _, _ = self.invoke([], outputs)
        self.assertEqual(code, 1)

    def test_ci_still_fails_on_other_tools(self):
        outputs = {**FIXTURES, "uv": "uv 0.1.0 (x)\n"}
        code, _, _, _ = self.invoke(["--ci"], outputs)
        self.assertEqual(code, 1)

    def test_print_runs_nothing(self):
        code, lines, err, run = self.invoke(["--print"])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        run.assert_not_called()
        self.assertEqual(len(lines), len(FIXTURES))
        self.assertEqual(lines[0], "node 24.22.2")
        self.assertIn("rustc 1.99.1", lines)
        self.assertIn("shfmt 3.14.1", lines)
        self.assertIn("gh 2.103.3", lines)

    def test_print_runs_nothing_even_if_tools_are_broken(self):
        outputs = {name: FileNotFoundError(name) for name in FIXTURES}
        code, lines, _, run = self.invoke(["--print"], outputs)
        self.assertEqual(code, 0)
        run.assert_not_called()
        self.assertEqual(len(lines), len(FIXTURES))

    def test_print_with_ci_drops_claude(self):
        code, lines, _, run = self.invoke(["--print", "--ci"])
        self.assertEqual(code, 0)
        run.assert_not_called()
        self.assertNotIn("claude 2.1.318", lines)
        self.assertEqual(len(lines), len(FIXTURES) - 1)

    def test_print_still_reports_an_inconsistent_toolchain(self):
        self.write(MISE_TOML, '[toolchain]\nchannel = "1.98.0"\n')
        code, _, err, run = self.invoke(["--print"])
        self.assertEqual(code, 1)
        self.assertIn("differs", err)
        run.assert_not_called()

    def test_unreadable_mise_entry_is_an_error(self):
        self.write(MISE_TOML + 'node-extra = { foo = "bar" }\n', TOOLCHAIN_TOML)
        code, _, err, run = self.invoke([])
        self.assertEqual(code, 1)
        self.assertIn("error:", err)
        run.assert_not_called()

    def test_duplicate_tool_key_is_an_error(self):
        self.write(MISE_TOML + '"aqua:x/node" = "1.0.0"\n', TOOLCHAIN_TOML)
        code, _, err, _ = self.invoke([])
        self.assertEqual(code, 1)
        self.assertIn("several entries", err)

    def test_missing_config_file_is_an_error(self):
        (self.root / "mise.toml").unlink()
        code, _, err, run = self.invoke([])
        self.assertEqual(code, 1)
        self.assertIn("error:", err)
        run.assert_not_called()

    def test_unknown_option_exits_with_usage_error(self):
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as ctx,
        ):
            cvt.main(["--nope"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
