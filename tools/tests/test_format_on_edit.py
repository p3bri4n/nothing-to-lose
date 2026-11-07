"""Tests for tools/hooks/format_on_edit.py.

Mostly hermetic: ``subprocess.run`` and ``subprocess.Popen`` are mocked (no formatter
is executed) and every project is a temporary directory. A few tests use the real
``git`` in a throw-away repository (configuration guard) and a real child process
(process-group kill); they are skipped when ``git`` is missing or on non-POSIX systems.

Run with: ``python3 -m unittest discover -s tools/tests`` (or ``just tools-test``).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "hooks"))

import format_on_edit as hook

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
REAL_RUN = subprocess.run
REAL_POPEN = subprocess.Popen
GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


def completed(returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], returncode, stdout="", stderr=stderr)


class FakeProc:
    """Stand-in for the ``Popen`` object of the formatter."""

    pid = 4242

    def __init__(self, result) -> None:
        self.result = result
        self.returncode = (
            None if isinstance(result, BaseException) else result.returncode
        )
        self.communicate_timeouts: list[float | None] = []

    def communicate(self, timeout=None):
        self.communicate_timeouts.append(timeout)
        if isinstance(self.result, subprocess.TimeoutExpired):
            if len(self.communicate_timeouts) == 1:
                raise self.result
            return "", ""
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result.stdout, self.result.stderr


class FakeRun:
    """Stand-in for ``subprocess.run`` (git) and ``subprocess.Popen`` (formatter).

    ``fmt_result``: a CompletedProcess (the formatter ran), an exception raised when
    the process is started, or a TimeoutExpired raised by the first ``communicate``.
    """

    def __init__(self, git_code: int = 1, fmt_result=None) -> None:
        self.git_code = git_code
        self.fmt_result = fmt_result if fmt_result is not None else completed(0)
        self.calls: list[tuple[list[str], dict]] = []
        self.procs: list[FakeProc] = []

    def __call__(self, command, **kwargs):
        self.calls.append((list(command), kwargs))
        return completed(self.git_code)

    def popen(self, command, **kwargs):
        self.calls.append((list(command), kwargs))
        if isinstance(self.fmt_result, BaseException) and not isinstance(
            self.fmt_result, subprocess.TimeoutExpired
        ):
            raise self.fmt_result
        proc = FakeProc(self.fmt_result)
        self.procs.append(proc)
        return proc

    @property
    def git_calls(self) -> list[list[str]]:
        return [c for c, _ in self.calls if c[0] == "git"]

    @property
    def fmt_calls(self) -> list[tuple[list[str], dict]]:
        return [(c, k) for c, k in self.calls if c[0] != "git"]


class SkipReasonTest(unittest.TestCase):
    def test_formattable_files(self) -> None:
        for path in ("a.py", "tools/x.toml", "crates/core/src/lib.rs", ".github/a.yml"):
            self.assertIsNone(hook.skip_reason(path), path)

    def test_generated_directories(self) -> None:
        for path in (
            "target/debug/a.json",
            "crates/core/target/a.rs",
            "runs/42/summary.json",
            "shots/a.html",
            "web/node_modules/x/index.js",
            ".cache/hooks/a.py",
            "bake/.cache/a.json",
        ):
            self.assertEqual(hook.skip_reason(path), "generated directory", path)

    def test_top_level_only_directories_are_not_matched_deeper(self) -> None:
        self.assertIsNone(hook.skip_reason("web/runs/a.json"))

    def test_fixtures_are_skipped(self) -> None:
        self.assertEqual(
            hook.skip_reason("tools/tests/fixtures/format/bad.py"), "formatter fixture"
        )

    def test_dot_git_is_never_touched_at_any_depth(self) -> None:
        for path in (".git/config.json", ".git/hooks/x.py", "sub/.git/a.yaml", ".git"):
            self.assertEqual(hook.skip_reason(path), "never touched", path)

    def test_names_that_only_look_like_dot_git_are_formatted(self) -> None:
        for path in (".github/workflows/ci.yml", "a.git/b.py", "gitx/a.py"):
            self.assertIsNone(hook.skip_reason(path), path)

    def test_unhandled_extensions(self) -> None:
        for path in ("README.md", "docs/a.md", "notes.txt", "Makefile", "a.png"):
            self.assertEqual(hook.skip_reason(path), "extension not handled", path)


class PayloadTest(unittest.TestCase):
    def test_extract_file_path(self) -> None:
        payload = {"tool_input": {"file_path": "/x/a.py"}}
        self.assertEqual(hook.extract_file_path(payload), "/x/a.py")

    def test_invalid_payloads(self) -> None:
        for payload in (
            None,
            [],
            "text",
            {},
            {"tool_input": None},
            {"tool_input": "x"},
            {"tool_input": {}},
            {"tool_input": {"file_path": 3}},
            {"tool_input": {"file_path": ""}},
            {"tool_input": {"file_path": "a\0b.py"}},
        ):
            self.assertIsNone(hook.extract_file_path(payload), payload)

    def test_disabled_values(self) -> None:
        self.assertTrue(hook.is_disabled({"NTL_FORMAT_HOOK": "off"}))
        self.assertTrue(hook.is_disabled({"NTL_FORMAT_HOOK": " OFF "}))
        self.assertFalse(hook.is_disabled({"NTL_FORMAT_HOOK": "on"}))
        self.assertFalse(hook.is_disabled({}))


class RunTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name).resolve() / "proj"
        self.root.mkdir()
        self.env = {"CLAUDE_PROJECT_DIR": str(self.root)}

    def make_file(self, relative: str, content: str = "x=1\n") -> pathlib.Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    # Value returned by the (patched) configuration guard; None: configuration clean.
    guard_problem: str | None = None

    def feed(self, payload, fake: FakeRun, env=None, real_popen: bool = False) -> int:
        text = payload if isinstance(payload, str) else json.dumps(payload)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(hook.subprocess, "run", fake))
            if not real_popen:
                stack.enter_context(
                    mock.patch.object(hook.subprocess, "Popen", fake.popen)
                )
            if self.guard_problem is not False:
                stack.enter_context(
                    mock.patch.object(
                        hook, "config_guard_problem", return_value=self.guard_problem
                    )
                )
            stack.enter_context(contextlib.redirect_stdout(out))
            stack.enter_context(contextlib.redirect_stderr(err))
            code = hook.run(text, self.env if env is None else env)
        self.assertEqual(out.getvalue(), "", "the hook must not print on stdout")
        self.assertEqual(err.getvalue(), "")
        return code

    def edit(self, path) -> dict:
        return {"tool_name": "Edit", "tool_input": {"file_path": str(path)}}

    @property
    def log(self) -> pathlib.Path:
        return self.root / ".cache" / "hooks" / "format.log"

    def test_formats_a_normal_file(self) -> None:
        path = self.make_file("tools/a.py")
        fake = FakeRun()
        self.assertEqual(self.feed(self.edit(path), fake), 0)
        self.assertEqual(len(fake.fmt_calls), 1)
        command, kwargs = fake.fmt_calls[0]
        self.assertEqual(
            command,
            [sys.executable, str(self.root / "tools" / "fmt.py"), "--write", str(path)],
        )
        self.assertNotIn("shell", kwargs)
        self.assertEqual(kwargs["cwd"], self.root)
        self.assertIs(kwargs["start_new_session"], True)
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(
            fake.procs[0].communicate_timeouts, [hook.FORMAT_TIMEOUT_SECONDS]
        )
        self.assertFalse(self.log.exists())

    def test_formatter_environment_forbids_mise_auto_install(self) -> None:
        path = self.make_file("tools/a.py")
        fake = FakeRun()
        env = {**self.env, "SOME_VARIABLE": "kept"}
        self.assertEqual(self.feed(self.edit(path), fake, env), 0)
        formatter_env = fake.fmt_calls[0][1]["env"]
        self.assertEqual(formatter_env["MISE_EXEC_AUTO_INSTALL"], "false")
        self.assertEqual(formatter_env["SOME_VARIABLE"], "kept")
        self.assertEqual(formatter_env.get("PATH"), os.environ.get("PATH"))

    def test_git_check_ignore_does_not_read_stdin(self) -> None:
        path = self.make_file("tools/a.py")
        fake = FakeRun()
        self.feed(self.edit(path), fake)
        kwargs = next(k for c, k in fake.calls if c[0] == "git")
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)

    def test_relative_path_is_taken_from_the_project_root(self) -> None:
        self.make_file("tools/a.py")
        fake = FakeRun()
        payload = {"tool_input": {"file_path": "tools/a.py"}}
        self.assertEqual(self.feed(payload, fake), 0)
        self.assertEqual(len(fake.fmt_calls), 1)

    def test_path_outside_the_project(self) -> None:
        with tempfile.TemporaryDirectory() as other:
            outside = pathlib.Path(other) / "a.py"
            outside.write_text("x=1\n", encoding="utf-8")
            fake = FakeRun()
            self.assertEqual(self.feed(self.edit(outside), fake), 0)
        self.assertEqual(fake.calls, [])

    def test_dotdot_cannot_escape_the_project(self) -> None:
        outside = self.root.parent / "outside.py"
        outside.write_text("x=1\n", encoding="utf-8")
        self.make_file("tools/a.py")
        fake = FakeRun()
        payload = {"tool_input": {"file_path": f"{self.root}/tools/../../outside.py"}}
        self.assertEqual(self.feed(payload, fake), 0)
        relative = {"tool_input": {"file_path": "../outside.py"}}
        self.assertEqual(self.feed(relative, fake), 0)
        self.assertEqual(fake.calls, [])

    def test_symlink_pointing_outside_the_project(self) -> None:
        with tempfile.TemporaryDirectory() as other:
            outside = pathlib.Path(other) / "real.py"
            outside.write_text("x=1\n", encoding="utf-8")
            link = self.root / "link.py"
            link.symlink_to(outside)
            fake = FakeRun()
            self.assertEqual(self.feed(self.edit(link), fake), 0)
        self.assertEqual(fake.calls, [])

    def test_symlinked_project_dir_is_resolved(self) -> None:
        real = self.make_file("a.py")
        alias = self.root.parent / "alias"
        alias.symlink_to(self.root)
        env = {"CLAUDE_PROJECT_DIR": str(alias)}
        fake = FakeRun()
        self.assertEqual(self.feed(self.edit(alias / "a.py"), fake, env), 0)
        self.assertEqual(len(fake.fmt_calls), 1)
        self.assertEqual(fake.fmt_calls[0][0][-1], str(real))

    def test_ignored_by_git(self) -> None:
        path = self.make_file("scratch.py")
        fake = FakeRun(git_code=0)
        self.assertEqual(self.feed(self.edit(path), fake), 0)
        self.assertEqual(
            fake.git_calls, [["git", "check-ignore", "-q", "--", "scratch.py"]]
        )
        self.assertEqual(fake.fmt_calls, [])

    def test_git_unable_to_tell_skips_and_logs(self) -> None:
        path = self.make_file("a.py")
        fake = FakeRun(git_code=128)
        self.assertEqual(self.feed(self.edit(path), fake), 0)
        self.assertEqual(fake.fmt_calls, [])
        self.assertIn("check-ignore failed", self.log.read_text(encoding="utf-8"))

    def test_generated_directory(self) -> None:
        path = self.make_file("target/debug/a.json")
        fake = FakeRun()
        self.assertEqual(self.feed(self.edit(path), fake), 0)
        self.assertEqual(fake.calls, [])

    def test_unhandled_extension(self) -> None:
        path = self.make_file("docs/a.md")
        fake = FakeRun()
        self.assertEqual(self.feed(self.edit(path), fake), 0)
        self.assertEqual(fake.calls, [])

    def test_fixture_directory(self) -> None:
        path = self.make_file("tools/tests/fixtures/format/bad.py")
        fake = FakeRun()
        self.assertEqual(self.feed(self.edit(path), fake), 0)
        self.assertEqual(fake.calls, [])

    def test_dot_git_is_never_touched(self) -> None:
        for relative in (".git/hooks/pre.py", ".git/config.json", "sub/.git/a.yaml"):
            path = self.make_file(relative)
            fake = FakeRun()
            self.assertEqual(self.feed(self.edit(path), fake), 0, relative)
            self.assertEqual(fake.calls, [], relative)

    def test_fmt_import_failure_is_logged_as_hook_error(self) -> None:
        path = self.make_file("a.py")
        fake = FakeRun()
        with mock.patch.object(hook, "fmt", None):
            self.assertEqual(self.feed(self.edit(path), fake), 0)
        self.assertEqual(fake.fmt_calls, [])
        self.assertIn("hook error", self.log.read_text(encoding="utf-8"))

    def test_missing_file(self) -> None:
        fake = FakeRun()
        self.assertEqual(self.feed(self.edit(self.root / "nope.py"), fake), 0)
        self.assertEqual(fake.calls, [])

    def test_invalid_json(self) -> None:
        fake = FakeRun()
        for text in ("not json", "", "{", "\x00\xff", "null", "[1, 2]"):
            self.assertEqual(self.feed(text, fake), 0, repr(text))
        self.assertEqual(fake.calls, [])

    def test_json_without_file_path(self) -> None:
        fake = FakeRun()
        self.assertEqual(self.feed({"tool_name": "Write", "tool_input": {}}, fake), 0)
        self.assertEqual(self.feed({"tool_name": "Write"}, fake), 0)
        self.assertEqual(fake.calls, [])

    def test_disabled_by_variable(self) -> None:
        path = self.make_file("a.py")
        fake = FakeRun()
        env = {**self.env, "NTL_FORMAT_HOOK": "off"}
        self.assertEqual(self.feed(self.edit(path), fake, env), 0)
        self.assertEqual(fake.calls, [])

    def test_formatter_exception_exits_0_and_logs(self) -> None:
        path = self.make_file("a.py")
        fake = FakeRun(fmt_result=FileNotFoundError("mise"))
        self.assertEqual(self.feed(self.edit(path), fake), 0)
        text = self.log.read_text(encoding="utf-8")
        self.assertEqual(len(text.splitlines()), 1)
        self.assertIn("a.py", text)
        self.assertIn("cannot run formatter", text)
        self.assertRegex(text, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_formatter_timeout_exits_0_and_logs(self) -> None:
        path = self.make_file("a.py")
        fake = FakeRun(fmt_result=subprocess.TimeoutExpired(["fmt"], 20))
        with mock.patch.object(hook.os, "killpg") as killpg:
            self.assertEqual(self.feed(self.edit(path), fake), 0)
        killpg.assert_called_once_with(FakeProc.pid, signal.SIGKILL)
        self.assertEqual(len(fake.procs[0].communicate_timeouts), 2)  # reaped
        text = self.log.read_text(encoding="utf-8")
        self.assertIn("timed out", text)
        self.assertIn("process group killed", text)

    def test_killpg_failure_does_not_matter(self) -> None:
        path = self.make_file("a.py")
        fake = FakeRun(fmt_result=subprocess.TimeoutExpired(["fmt"], 20))
        with mock.patch.object(hook.os, "killpg", side_effect=ProcessLookupError):
            self.assertEqual(self.feed(self.edit(path), fake), 0)
        self.assertIn("timed out", self.log.read_text(encoding="utf-8"))

    def test_slow_formatting_is_logged(self) -> None:
        path = self.make_file("a.py")
        fake = FakeRun()
        clock = mock.Mock(monotonic=mock.Mock(side_effect=[100.0, 107.5]))
        with mock.patch.object(hook, "time", clock):
            self.assertEqual(self.feed(self.edit(path), fake), 0)
        self.assertIn("slow formatting (7.5s)", self.log.read_text(encoding="utf-8"))

    def test_fast_formatting_is_not_logged(self) -> None:
        path = self.make_file("a.py")
        clock = mock.Mock(monotonic=mock.Mock(side_effect=[100.0, 101.0]))
        with mock.patch.object(hook, "time", clock):
            self.assertEqual(self.feed(self.edit(path), FakeRun()), 0)
        self.assertFalse(self.log.exists())

    def test_formatter_error_exit_is_logged_on_one_line(self) -> None:
        path = self.make_file("a.py")
        fake = FakeRun(fmt_result=completed(1, "error: ruff failed\nsyntax error"))
        self.assertEqual(self.feed(self.edit(path), fake), 0)
        lines = self.log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn("exit 1", lines[0])
        self.assertIn("syntax error", lines[0])

    def test_log_is_appended(self) -> None:
        path = self.make_file("a.py")
        fake = FakeRun(fmt_result=completed(1, "boom"))
        self.feed(self.edit(path), fake)
        self.feed(self.edit(path), fake)
        self.assertEqual(len(self.log.read_text(encoding="utf-8").splitlines()), 2)

    def test_log_is_rotated_beyond_the_size_limit(self) -> None:
        path = self.make_file("a.py")
        fake = FakeRun(fmt_result=completed(1, "boom"))
        self.log.parent.mkdir(parents=True)
        self.log.write_text("old line\n" * 20, encoding="utf-8")
        with mock.patch.object(hook, "LOG_MAX_BYTES", 100):
            self.feed(self.edit(path), fake)
            self.feed(self.edit(path), fake)
        rotated = self.log.with_name("format.log.1")
        self.assertIn("old line", rotated.read_text(encoding="utf-8"))
        text = self.log.read_text(encoding="utf-8")
        self.assertNotIn("old line", text)
        self.assertEqual(len(text.splitlines()), 2)

    def test_unexpected_exception_exits_0_and_logs(self) -> None:
        path = self.make_file("a.py")
        with mock.patch.object(hook, "resolve_in_project", side_effect=OSError("disk")):
            self.assertEqual(self.feed(self.edit(path), FakeRun()), 0)
        self.assertIn("hook error", self.log.read_text(encoding="utf-8"))

    def test_unwritable_log_does_not_matter(self) -> None:
        path = self.make_file("a.py")
        self.make_file(".cache", "a file where a directory is expected")
        fake = FakeRun(fmt_result=completed(1, "boom"))
        self.assertEqual(self.feed(self.edit(path), fake), 0)

    def test_path_with_spaces_and_colon(self) -> None:
        path = self.make_file("my dir: with space/sub dir/a b: c.py")
        fake = FakeRun()
        self.assertEqual(self.feed(self.edit(path), fake), 0)
        self.assertEqual(len(fake.fmt_calls), 1)
        self.assertEqual(fake.fmt_calls[0][0][-1], str(path))
        self.assertEqual(fake.git_calls[0][-1], "my dir: with space/sub dir/a b: c.py")

    def test_project_dir_with_spaces_and_colon(self) -> None:
        base = self.root.parent / "Guide Or Fade : Your command"
        base.mkdir()
        path = base / "a.py"
        path.write_text("x=1\n", encoding="utf-8")
        env = {"CLAUDE_PROJECT_DIR": str(base)}
        fake = FakeRun()
        self.assertEqual(self.feed(self.edit(path), fake, env), 0)
        self.assertEqual(fake.fmt_calls[0][0][-2:], ["--write", str(path)])
        self.assertEqual(fake.fmt_calls[0][1]["cwd"], base)


def git(root: pathlib.Path, *args: str) -> None:
    REAL_RUN(["git", *args], cwd=root, env=GIT_ENV, check=True, capture_output=True)


@unittest.skipUnless(shutil.which("git"), "git is not installed")
class GuardRepoCase(unittest.TestCase):
    """Base class: a real Git repository holding the guarded files, committed."""

    committed = ("mise.toml", ".prettierrc.json", "rust-toolchain.toml")

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name).resolve() / "proj"
        self.root.mkdir()
        git(self.root, "init", "-q")
        (self.root / ".gitignore").write_text("mise.local.toml\n", encoding="utf-8")
        for name in self.committed:
            (self.root / name).write_text("original\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "init")

    def write(self, name: str, text: str = "changed\n") -> None:
        (self.root / name).write_text(text, encoding="utf-8")


class ConfigGuardTest(GuardRepoCase):
    def test_clean_configuration(self) -> None:
        self.assertIsNone(hook.config_guard_problem(self.root))

    def test_modified_file(self) -> None:
        self.write("mise.toml")
        problem = hook.config_guard_problem(self.root)
        self.assertIn("differs from HEAD", problem)
        self.assertIn("mise.toml", problem)

    def test_each_guarded_tracked_file_is_watched(self) -> None:
        for name in self.committed:
            with self.subTest(name=name):
                self.write(name)
                self.assertIn(name, hook.config_guard_problem(self.root))
                git(self.root, "checkout", "--", name)
                self.assertIsNone(hook.config_guard_problem(self.root))

    def test_staged_modification(self) -> None:
        self.write(".prettierrc.json")
        git(self.root, "add", ".prettierrc.json")
        self.assertIn(".prettierrc.json", hook.config_guard_problem(self.root))

    def test_deleted_file(self) -> None:
        (self.root / "rust-toolchain.toml").unlink()
        self.assertIn("rust-toolchain.toml", hook.config_guard_problem(self.root))

    def test_untracked_ignored_mise_local_toml(self) -> None:
        self.write("mise.local.toml")
        self.assertIn("mise.local.toml", hook.config_guard_problem(self.root))

    def test_untracked_not_ignored_file(self) -> None:
        (self.root / ".gitignore").write_text("", encoding="utf-8")
        git(self.root, "add", ".gitignore")
        git(self.root, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "x")
        self.write("mise.local.toml")
        self.assertIn("mise.local.toml", hook.config_guard_problem(self.root))

    def test_absent_from_head_and_disk_is_normal(self) -> None:
        # mise.local.toml is neither in HEAD nor on disk in the base repository.
        self.assertFalse((self.root / "mise.local.toml").exists())
        self.assertIsNone(hook.config_guard_problem(self.root))

    def test_other_files_do_not_matter(self) -> None:
        self.write("other.py")
        self.write("README.md")
        self.assertIsNone(hook.config_guard_problem(self.root))

    def test_git_failure_is_a_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:  # not a Git repository
            problem = hook.config_guard_problem(pathlib.Path(tmp))
        self.assertIn("cannot compare", problem)

    def test_git_timeout_is_a_refusal(self) -> None:
        error = subprocess.TimeoutExpired(["git"], 3)
        with mock.patch.object(hook.subprocess, "run", side_effect=error):
            self.assertIn("cannot compare", hook.config_guard_problem(self.root))

    def test_git_status_takes_no_optional_lock_and_no_stdin(self) -> None:
        with mock.patch.object(
            hook.subprocess, "run", return_value=completed(0)
        ) as run:
            hook.config_guard_problem(self.root)
        command, kwargs = run.call_args.args[0], run.call_args.kwargs
        self.assertEqual(command[:3], ["git", "--no-optional-locks", "status"])
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(
            command[-len(hook.GUARDED_CONFIG_FILES) :], list(hook.GUARDED_CONFIG_FILES)
        )

    def test_guarded_files_list(self) -> None:
        self.assertEqual(
            set(hook.GUARDED_CONFIG_FILES),
            {"mise.toml", "mise.local.toml", ".prettierrc.json", "rust-toolchain.toml"},
        )


class GuardedRunTest(GuardRepoCase):
    """End to end through ``hook.run``: real guard and real Git, mocked formatter."""

    def run_hook(self, relative: str = "tools/a.py"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x=1\n", encoding="utf-8")
        fake = FakeRun()

        def run(command, **kwargs):
            if "status" in command:  # the guard: real Git (run() needs the real Popen)
                with mock.patch.object(hook.subprocess, "Popen", REAL_POPEN):
                    return REAL_RUN(command, **kwargs)
            return fake(command, **kwargs)  # check-ignore: "not ignored"

        payload = json.dumps({"tool_input": {"file_path": str(path)}})
        with (
            mock.patch.object(hook.subprocess, "run", run),
            mock.patch.object(hook.subprocess, "Popen", fake.popen),
        ):
            code = hook.run(payload, {"CLAUDE_PROJECT_DIR": str(self.root)})
        self.assertEqual(code, 0)
        return fake

    @property
    def log_text(self) -> str:
        log = self.root / ".cache" / "hooks" / "format.log"
        return log.read_text(encoding="utf-8") if log.exists() else ""

    def test_modified_configuration_prevents_formatting(self) -> None:
        self.write("mise.toml")
        fake = self.run_hook()
        self.assertEqual(fake.fmt_calls, [])
        self.assertIn("formatting refused", self.log_text)
        self.assertIn("mise.toml", self.log_text)

    def test_clean_configuration_formats(self) -> None:
        fake = self.run_hook()
        self.assertEqual(len(fake.fmt_calls), 1)
        self.assertEqual(self.log_text, "")

    def test_untracked_mise_local_toml_prevents_formatting(self) -> None:
        self.write("mise.local.toml")
        fake = self.run_hook()
        self.assertEqual(fake.fmt_calls, [])
        self.assertIn("mise.local.toml", self.log_text)

    def test_files_absent_from_head_and_disk_format(self) -> None:
        for name in self.committed:
            git(self.root, "rm", "-q", "-f", name)
        git(self.root, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "rm")
        fake = self.run_hook()
        self.assertEqual(len(fake.fmt_calls), 1)
        self.assertEqual(self.log_text, "")

    def test_editing_a_guarded_file_is_refused_too(self) -> None:
        self.write("mise.toml")
        fake = self.run_hook("mise.toml")
        self.assertEqual(fake.fmt_calls, [])


def process_is_alive(pid: int) -> bool:
    """True if the process exists and is not a zombie."""
    try:
        stat = pathlib.Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except FileNotFoundError:
        return False
    except OSError:
        pass
    else:
        return stat.rsplit(")", 1)[1].split()[0] != "Z"
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@unittest.skipUnless(hasattr(os, "killpg"), "needs POSIX process groups")
class ProcessGroupKillTest(unittest.TestCase):
    """A real timeout kills the formatter and the processes it started."""

    def test_timeout_kills_the_grandchildren(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            (root / "a.py").write_text("x=1\n", encoding="utf-8")
            pid_file = root / "grandchild.pid"
            script = (
                "import subprocess, sys, time\n"
                "child = subprocess.Popen(['sleep', '60'])\n"
                f"open({str(pid_file)!r}, 'w').write(str(child.pid))\n"
                "time.sleep(60)\n"
            )
            command = [sys.executable, "-c", script]
            started = time.monotonic()
            with (
                mock.patch.object(hook, "FORMAT_TIMEOUT_SECONDS", 1),
                mock.patch.object(hook, "format_command", return_value=command),
            ):
                hook.format_file(root, root / "a.py", "a.py", {})
            self.assertLess(time.monotonic() - started, 10)
            grandchild = int(pid_file.read_text(encoding="utf-8"))
            for _ in range(50):  # the kernel needs a moment to reap the orphan
                if not process_is_alive(grandchild):
                    break
                time.sleep(0.1)
            else:
                os.kill(grandchild, signal.SIGKILL)
                self.fail("the grandchild survived the timeout")
            log = (root / ".cache" / "hooks" / "format.log").read_text(encoding="utf-8")
            self.assertIn("timed out after 1s", log)


class SettingsTest(unittest.TestCase):
    def hook_entry(self) -> dict:
        settings = json.loads(
            (REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")
        )
        entries = [
            h
            for group in settings["hooks"]["PostToolUse"]
            for h in group["hooks"]
            if "format_on_edit.py" in h["command"]
        ]
        self.assertEqual(len(entries), 1)
        return entries[0]

    def test_hook_timeout_covers_the_worst_case(self) -> None:
        timeout = self.hook_entry()["timeout"]
        self.assertLessEqual(
            hook.FORMAT_TIMEOUT_SECONDS + hook.GIT_TIMEOUT_SECONDS + 3, timeout
        )
        # check-ignore + guard + formatter + reaping, all at their limit.
        self.assertLessEqual(
            hook.FORMAT_TIMEOUT_SECONDS
            + 2 * hook.GIT_TIMEOUT_SECONDS
            + hook.REAP_TIMEOUT_SECONDS,
            timeout,
        )

    def test_hook_is_synchronous_and_never_fails(self) -> None:
        entry = self.hook_entry()
        self.assertNotIn("async", entry)
        self.assertTrue(entry["command"].endswith("|| true"), entry["command"])


class LoadFmtTest(unittest.TestCase):
    def test_loads_the_real_fmt(self) -> None:
        module = hook.load_fmt()
        self.assertIsNotNone(module)
        self.assertTrue(callable(module.formatter_for))

    def test_broken_or_missing_fmt_gives_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            broken = pathlib.Path(tmp) / "fmt.py"
            broken.write_text("raise RuntimeError('boom')\n", encoding="utf-8")
            self.assertIsNone(hook.load_fmt(broken))
            self.assertIsNone(hook.load_fmt(pathlib.Path(tmp) / "missing.py"))
            broken.write_text("def broken(:\n", encoding="utf-8")
            self.assertIsNone(hook.load_fmt(broken))

    def test_failed_load_keeps_the_previously_loaded_module(self) -> None:
        before = sys.modules.get("ntl_fmt")
        with tempfile.TemporaryDirectory() as tmp:
            broken = pathlib.Path(tmp) / "fmt.py"
            broken.write_text("raise RuntimeError('boom')\n", encoding="utf-8")
            hook.load_fmt(broken)
        self.assertIs(sys.modules.get("ntl_fmt"), before)


class MainTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch.dict(hook.os.environ, {"CLAUDE_PROJECT_DIR": tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_main_returns_0_on_garbage_stdin(self) -> None:
        with mock.patch.object(hook.sys, "stdin", io.StringIO("garbage")):
            self.assertEqual(hook.main(), 0)

    def test_main_returns_0_when_stdin_cannot_be_read(self) -> None:
        broken = mock.Mock()
        broken.read.side_effect = OSError("closed")
        with mock.patch.object(hook.sys, "stdin", broken):
            self.assertEqual(hook.main(), 0)


if __name__ == "__main__":
    unittest.main()
