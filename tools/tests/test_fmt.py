"""Tests for tools/fmt.py.

The unit tests are hermetic: no formatter is ever executed (``subprocess.run`` is
mocked). One integration test runs the real formatters on the badly formatted
fixtures; each fixture is reported as skipped (with the reason) when ``mise`` or the
formatter is not available.

Run with: ``python3 -m unittest discover -s tools/tests`` (or ``just tools-test``).
"""

from __future__ import annotations

import contextlib
import functools
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import fmt

FIXTURES_DIR = pathlib.Path(__file__).resolve().parent / "fixtures" / "format"
PRETTIER_CONFIG = str(fmt.REPO_ROOT / ".prettierrc.json")


def completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="")


class FormatterSelectionTest(unittest.TestCase):
    def test_every_extension_maps_to_a_known_formatter(self) -> None:
        for ext, name in fmt.EXTENSIONS.items():
            self.assertIn(name, fmt.FORMATTERS, ext)

    def test_mapping_of_the_plan_table(self) -> None:
        expected = {
            "a.rs": "rustfmt",
            "a.py": "ruff",
            "a.toml": "taplo",
            "a.tf": "terraform",
            "a.sh": "shfmt",
            "a.json": "prettier",
            "a.yaml": "prettier",
            "a.yml": "prettier",
            "a.js": "prettier",
            "a.ts": "prettier",
            "a.html": "prettier",
            "a.css": "prettier",
        }
        for path, name in expected.items():
            formatter = fmt.formatter_for(path)
            self.assertIsNotNone(formatter, path)
            self.assertEqual(formatter.name, name, path)

    def test_markdown_and_unknown_extensions_have_no_formatter(self) -> None:
        for path in ("README.md", "docs/a.md", "a.png", "justfile", ".gitignore", "x"):
            self.assertIsNone(fmt.formatter_for(path), path)

    def test_extension_is_case_insensitive_and_uses_the_last_suffix(self) -> None:
        self.assertEqual(fmt.formatter_for("A.PY").name, "ruff")
        self.assertEqual(fmt.formatter_for("a.tar.json").name, "prettier")
        self.assertIsNone(fmt.formatter_for("a.py.md"))

    def test_path_with_spaces_and_colon(self) -> None:
        self.assertEqual(fmt.formatter_for("my dir:x/a b.rs").name, "rustfmt")


class PathFilteringTest(unittest.TestCase):
    def test_fixtures_are_excluded(self) -> None:
        self.assertTrue(fmt.is_excluded("tools/tests/fixtures/format/bad.py"))
        self.assertTrue(fmt.is_excluded("tools/tests/fixtures/format/sub/bad.rs"))

    def test_similar_prefix_is_not_excluded(self) -> None:
        self.assertFalse(fmt.is_excluded("tools/tests/fixtures/format2/a.py"))
        self.assertFalse(fmt.is_excluded("tools/tests/fixtures/other/a.py"))
        self.assertFalse(fmt.is_excluded("tools/fmt.py"))

    def test_filter_paths_drops_excluded_and_unhandled_keeping_order(self) -> None:
        paths = [
            "b.py",
            "README.md",
            "tools/tests/fixtures/format/bad.py",
            "a.toml",
            "image.png",
            "c d:e.sh",
        ]
        self.assertEqual(fmt.filter_paths(paths), ["b.py", "a.toml", "c d:e.sh"])

    def test_group_by_formatter(self) -> None:
        groups = fmt.group_by_formatter(["a.py", "b.json", "c.py", "d.yaml", "e.rs"])
        self.assertEqual(
            groups,
            {
                "rustfmt": ["e.rs"],
                "ruff": ["a.py", "c.py"],
                "prettier": ["b.json", "d.yaml"],
            },
        )

    def test_group_by_formatter_without_files_is_empty(self) -> None:
        self.assertEqual(fmt.group_by_formatter([]), {})
        self.assertEqual(fmt.group_by_formatter(["README.md"]), {})

    def test_display_path(self) -> None:
        root = pathlib.Path("/repo")
        self.assertEqual(fmt.display_path(root / "a" / "b.py", root), "a/b.py")
        self.assertEqual(
            fmt.display_path(pathlib.Path("/elsewhere/b.py"), root), "/elsewhere/b.py"
        )


class BuildCommandTest(unittest.TestCase):
    def command(self, tool: str, mode: str, files: list[str]) -> list[str]:
        return fmt.build_command(fmt.FORMATTERS[tool], mode, files)

    def test_commands_go_through_mise(self) -> None:
        for formatter in fmt.FORMATTERS.values():
            for mode in ("write", "check"):
                command = fmt.build_command(formatter, mode, ["x"])
                self.assertEqual(command[:3], ["mise", "exec", "--"])
                self.assertEqual(command[-1], "x")

    def test_write_and_check_invocations(self) -> None:
        f = ["a"]
        self.assertEqual(
            self.command("rustfmt", "write", f), ["mise", "exec", "--", "rustfmt", "a"]
        )
        self.assertEqual(
            self.command("rustfmt", "check", f),
            ["mise", "exec", "--", "rustfmt", "--check", "a"],
        )
        self.assertEqual(
            self.command("ruff", "write", f),
            ["mise", "exec", "--", "ruff", "format", "a"],
        )
        self.assertEqual(
            self.command("ruff", "check", f),
            ["mise", "exec", "--", "ruff", "format", "--check", "a"],
        )
        self.assertEqual(
            self.command("taplo", "write", f),
            ["mise", "exec", "--", "taplo", "fmt", "a"],
        )
        self.assertEqual(
            self.command("taplo", "check", f),
            ["mise", "exec", "--", "taplo", "fmt", "--check", "a"],
        )
        self.assertEqual(
            self.command("terraform", "write", f),
            ["mise", "exec", "--", "terraform", "fmt", "a"],
        )
        self.assertEqual(
            self.command("terraform", "check", f),
            ["mise", "exec", "--", "terraform", "fmt", "-check", "-diff", "a"],
        )
        self.assertEqual(
            self.command("shfmt", "write", f),
            ["mise", "exec", "--", "shfmt", "-i", "2", "-ci", "-w", "a"],
        )
        self.assertEqual(
            self.command("shfmt", "check", f),
            ["mise", "exec", "--", "shfmt", "-i", "2", "-ci", "-d", "a"],
        )
        self.assertEqual(
            self.command("prettier", "write", f),
            [
                "mise",
                "exec",
                "--",
                "prettier",
                "--write",
                "--config",
                PRETTIER_CONFIG,
                "a",
            ],
        )
        self.assertEqual(
            self.command("prettier", "check", f),
            [
                "mise",
                "exec",
                "--",
                "prettier",
                "--check",
                "--config",
                PRETTIER_CONFIG,
                "a",
            ],
        )

    def test_only_prettier_forces_a_config_file(self) -> None:
        for name, formatter in fmt.FORMATTERS.items():
            for mode in ("write", "check"):
                command = fmt.build_command(formatter, mode, ["x"])
                self.assertEqual("--config" in command, name == "prettier", name)

    def test_prettier_config_is_taken_from_the_given_root(self) -> None:
        root = pathlib.Path("/some/root")
        command = fmt.build_command(fmt.FORMATTERS["prettier"], "write", ["a"], root)
        self.assertEqual(
            command[command.index("--config") + 1], "/some/root/.prettierrc.json"
        )

    def test_files_stay_single_arguments(self) -> None:
        files = ["dir with space/a b.py", "c:d.py", "e;rm -rf.py", "$(x).py"]
        command = self.command("ruff", "check", files)
        self.assertEqual(command[-len(files) :], files)

    def test_leading_dash_is_not_read_as_an_option(self) -> None:
        command = self.command("ruff", "write", ["-n.py", "ok.py"])
        self.assertEqual(command[-2:], ["./-n.py", "ok.py"])

    def test_unknown_mode_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.command("ruff", "both", ["a.py"])


class RunFormatterTest(unittest.TestCase):
    ROOT = pathlib.Path("/repo")

    def run_with(self, **kwargs) -> tuple[bool, str]:
        stderr = io.StringIO()
        with (
            mock.patch.object(subprocess, "run", **kwargs) as run,
            contextlib.redirect_stderr(stderr),
        ):
            ok = fmt.run_formatter(fmt.FORMATTERS["ruff"], "check", ["a.py"], self.ROOT)
        self.assertEqual(run.call_count, 1)
        self.last_call = run.call_args
        return ok, stderr.getvalue()

    def test_success(self) -> None:
        ok, err = self.run_with(return_value=completed(0))
        self.assertTrue(ok)
        self.assertEqual(err, "")
        args, kwargs = self.last_call
        self.assertEqual(args[0][:3], ["mise", "exec", "--"])
        self.assertEqual(kwargs["cwd"], self.ROOT)
        self.assertNotIn("shell", kwargs)

    def test_unformatted_file_fails(self) -> None:
        ok, err = self.run_with(return_value=completed(1))
        self.assertFalse(ok)
        self.assertIn("ruff needs formatting", err)

    def test_missing_mise_fails(self) -> None:
        ok, err = self.run_with(side_effect=FileNotFoundError("mise"))
        self.assertFalse(ok)
        self.assertIn("not in PATH", err)

    def test_timeout_fails(self) -> None:
        ok, err = self.run_with(side_effect=subprocess.TimeoutExpired("mise", 1))
        self.assertFalse(ok)
        self.assertIn("timed out", err)

    def test_permission_error_fails(self) -> None:
        ok, _ = self.run_with(side_effect=PermissionError())
        self.assertFalse(ok)

    def test_generic_os_error_fails_with_its_class_name(self) -> None:
        ok, err = self.run_with(side_effect=OSError(8, "Exec format error"))
        self.assertFalse(ok)
        self.assertIn("cannot run ruff (OSError)", err)

    def test_write_failure_message(self) -> None:
        stderr = io.StringIO()
        with (
            mock.patch.object(subprocess, "run", return_value=completed(2)),
            contextlib.redirect_stderr(stderr),
        ):
            ok = fmt.run_formatter(fmt.FORMATTERS["ruff"], "write", ["a.py"], self.ROOT)
        self.assertFalse(ok)
        self.assertIn("ruff failed (exit 2, 1 file(s))", stderr.getvalue())


class ResolveExplicitTest(unittest.TestCase):
    def test_resolves_relative_to_the_current_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            (root / "sub").mkdir()
            (root / "sub" / "a.py").write_text("")
            with contextlib.chdir(root / "sub"):
                paths, errors = fmt.resolve_explicit(["a.py", "../sub/a.py"], root)
        self.assertEqual(paths, ["sub/a.py", "sub/a.py"])
        self.assertEqual(errors, [])

    def test_file_outside_the_root_is_kept_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp).resolve()
            (base / "root").mkdir()
            outside = base / "b.py"
            outside.write_text("")
            paths, errors = fmt.resolve_explicit([str(outside)], base / "root")
        self.assertEqual(paths, [outside.as_posix()])
        self.assertEqual(errors, [])

    def test_missing_file_and_directory_are_errors_and_others_are_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            (root / "ok.py").write_text("")
            (root / "adir").mkdir()
            raw = [str(root / "missing.py"), str(root / "adir"), str(root / "ok.py")]
            paths, errors = fmt.resolve_explicit(raw, root)
        self.assertEqual(paths, ["ok.py"])
        self.assertEqual(
            errors,
            [f"error: not a file: {raw[0]}", f"error: not a file: {raw[1]}"],
        )

    def test_empty_input(self) -> None:
        self.assertEqual(fmt.resolve_explicit([], pathlib.Path("/repo")), ([], []))


class MainTest(unittest.TestCase):
    def run_main(self, argv: list[str], **patches) -> tuple[int, mock.Mock]:
        with contextlib.ExitStack() as stack:
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            self.stderr = io.StringIO()
            stack.enter_context(contextlib.redirect_stderr(self.stderr))
            run = stack.enter_context(
                mock.patch.object(subprocess, "run", return_value=completed(0))
            )
            for name, value in patches.items():
                stack.enter_context(mock.patch.object(fmt, name, value))
            code = fmt.main(argv)
        return code, run

    def test_mode_is_required(self) -> None:
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as ctx,
        ):
            fmt.main([])
        self.assertEqual(ctx.exception.code, 2)

    def test_modes_are_mutually_exclusive(self) -> None:
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as ctx,
        ):
            fmt.main(["--write", "--check"])
        self.assertEqual(ctx.exception.code, 2)

    def test_without_paths_uses_tracked_files_and_excludes_fixtures(self) -> None:
        tracked = [
            "tools/fmt.py",
            "README.md",
            "tools/tests/fixtures/format/bad.py",
            "mise.toml",
        ]
        code, run = self.run_main(["--check"], tracked_files=lambda root: tracked)
        self.assertEqual(code, 0)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(len(commands), 2)  # ruff and taplo only
        self.assertIn("tools/fmt.py", commands[0])
        all_args = [arg for command in commands for arg in command]
        self.assertNotIn("tools/tests/fixtures/format/bad.py", all_args)

    def test_write_mode_runs_the_write_commands(self) -> None:
        code, run = self.run_main(
            ["--write"], tracked_files=lambda root: ["a.py", "b.sh"]
        )
        self.assertEqual(code, 0)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(
            commands,
            [
                ["mise", "exec", "--", "ruff", "format", "a.py"],
                ["mise", "exec", "--", "shfmt", "-i", "2", "-ci", "-w", "b.sh"],
            ],
        )

    def test_git_listing_failure_gives_exit_1_and_runs_nothing(self) -> None:
        failures = (
            subprocess.CalledProcessError(128, ["git", "ls-files"]),
            FileNotFoundError("git"),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):

                def broken(root: pathlib.Path, failure=failure) -> list[str]:
                    raise failure

                code, run = self.run_main(["--check"], tracked_files=broken)
                self.assertEqual(code, 1)
                self.assertIn("cannot list Git files", self.stderr.getvalue())
                run.assert_not_called()

    def test_no_rust_file_runs_no_rustfmt(self) -> None:
        code, run = self.run_main(
            ["--check"], tracked_files=lambda root: ["a.py", "b.json"]
        )
        self.assertEqual(code, 0)
        tools = [call.args[0][3] for call in run.call_args_list]
        self.assertNotIn("rustfmt", tools)
        self.assertEqual(tools, ["ruff", "prettier"])

    def test_empty_selection_succeeds_without_running_anything(self) -> None:
        code, run = self.run_main(["--check"], tracked_files=lambda root: ["a.md"])
        self.assertEqual(code, 0)
        run.assert_not_called()

    def test_failure_of_one_formatter_gives_exit_1_but_runs_the_others(self) -> None:
        results = [completed(1), completed(0)]
        with contextlib.ExitStack() as stack:
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            run = stack.enter_context(
                mock.patch.object(subprocess, "run", side_effect=results)
            )
            stack.enter_context(
                mock.patch.object(fmt, "tracked_files", lambda root: ["a.py", "b.toml"])
            )
            code = fmt.main(["--check"])
        self.assertEqual(code, 1)
        self.assertEqual(run.call_count, 2)

    def test_explicit_paths_are_not_excluded_and_unknown_ones_skipped(self) -> None:
        readme = fmt.REPO_ROOT / "README.md"
        paths = [str(FIXTURES_DIR / "bad.py"), str(pathlib.Path(__file__)), str(readme)]
        code, run = self.run_main(["--check", *paths])
        self.assertEqual(code, 0)
        self.assertEqual(run.call_count, 1)  # ruff only: README.md is skipped
        command = run.call_args_list[0].args[0]
        self.assertIn("tools/tests/fixtures/format/bad.py", command)
        self.assertIn("tools/tests/test_fmt.py", command)
        self.assertNotIn("README.md", command)

    def test_missing_explicit_path_fails(self) -> None:
        code, run = self.run_main(["--check", "does/not/exist.py"])
        self.assertEqual(code, 1)
        run.assert_not_called()


@functools.cache
def formatter_available(tool: str) -> bool:
    """True if ``mise exec -- <tool> --version`` works (computed once per tool)."""
    try:
        proc = subprocess.run(
            ["mise", "exec", "--", tool, "--version"],
            cwd=fmt.REPO_ROOT,
            capture_output=True,
            timeout=60,
            check=False,
        )
    except subprocess.SubprocessError:
        return False
    except OSError:
        return False
    return proc.returncode == 0


@unittest.skipUnless(shutil.which("mise"), "mise is not installed")
class FixtureIntegrationTest(unittest.TestCase):
    """Run the real formatters: every badly formatted fixture must be detected."""

    def test_each_fixture_is_detected_as_unformatted(self) -> None:
        fixtures = sorted(p for p in FIXTURES_DIR.iterdir() if p.is_file())
        self.assertTrue(fixtures, "no fixture found")
        for path in fixtures:
            with self.subTest(fixture=path.name):
                formatter = fmt.formatter_for(path.name)
                self.assertIsNotNone(formatter, path.name)
                if not formatter_available(formatter.name):
                    self.skipTest(f"{formatter.name} is not available through mise")
                relative = fmt.display_path(path, fmt.REPO_ROOT)
                command = fmt.build_command(formatter, "check", [relative])
                proc = subprocess.run(
                    command,
                    cwd=fmt.REPO_ROOT,
                    capture_output=True,
                    timeout=120,
                    check=False,
                )
                self.assertNotEqual(
                    proc.returncode, 0, f"{relative} should be reported as unformatted"
                )


@unittest.skipUnless(shutil.which("mise"), "mise is not installed")
class PrettierConfigIsolationTest(unittest.TestCase):
    """A ``prettier.config.js`` next to a formatted file must never be executed."""

    def test_booby_trapped_config_next_to_the_file_is_not_executed(self) -> None:
        if not formatter_available("prettier"):
            self.skipTest("prettier is not available through mise")
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp).resolve()
            witness = directory / "witness.txt"
            (directory / "prettier.config.js").write_text(
                f'require("fs").writeFileSync({json.dumps(str(witness))}, "run");\n'
                "module.exports = {};\n",
                encoding="utf-8",
            )
            target = directory / "x.js"
            prettier = fmt.FORMATTERS["prettier"]

            def run(command: list[str]) -> subprocess.CompletedProcess:
                target.write_text("const   a  =  1\n", encoding="utf-8")
                return subprocess.run(
                    command,
                    cwd=fmt.REPO_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )

            # Control: without --config the trap fires, so the test proves something.
            control = ["mise", "exec", "--", "prettier", "--write", str(target)]
            proc = run(control)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(witness.exists(), "the control run must execute the trap")
            witness.unlink()

            proc = run(fmt.build_command(prettier, "write", [str(target)]))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse(witness.exists(), "the trapped config was executed")
            self.assertEqual(target.read_text(encoding="utf-8"), "const a = 1;\n")

            proc = run(fmt.build_command(prettier, "check", [str(target)]))
            self.assertNotEqual(proc.returncode, 0)  # unformatted: reported, not run
            self.assertFalse(witness.exists(), "the trapped config was executed")


if __name__ == "__main__":
    unittest.main()
