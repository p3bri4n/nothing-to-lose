"""Tests for .githooks/pre-commit, .gitleaks.toml and the related justfile recipes.

Hermetic: every repository is a temporary directory and mise is replaced by a stub
script, so neither gitleaks nor the real mise is executed. The real end-to-end check
(a genuine secret, the real gitleaks) is ``just verify-pp secrets``.

Run with: ``python3 -m unittest discover -s tools/tests`` (or ``just tools-test``).
"""

from __future__ import annotations

import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
import tomllib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
HOOK = REPO_ROOT / ".githooks" / "pre-commit"
GIT = shutil.which("git")
BASH = shutil.which("bash")
ENV_BIN = shutil.which("env")
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


class StaticFilesTest(unittest.TestCase):
    def test_hook_is_executable_bash_script(self) -> None:
        mode = HOOK.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR, "the hook must be executable")
        self.assertEqual(HOOK.read_text().splitlines()[0], "#!/usr/bin/env bash")

    @unittest.skipUnless(BASH, "bash is required")
    def test_hook_has_valid_syntax(self) -> None:
        result = subprocess.run(
            [BASH, "-n", str(HOOK)], check=False, capture_output=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_hook_is_tracked_as_executable_by_git(self) -> None:
        # Mode 100755 in the index, otherwise the hook is silently ignored after a clone.
        result = subprocess.run(
            ["git", "ls-files", "--stage", ".githooks/pre-commit"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout:
            self.skipTest("the hook is not (yet) tracked by git")
        self.assertTrue(result.stdout.startswith("100755"), result.stdout)

    def test_gitleaks_config_extends_defaults_without_allowlist(self) -> None:
        config = tomllib.loads((REPO_ROOT / ".gitleaks.toml").read_text())
        self.assertIs(config["extend"]["useDefault"], True)
        self.assertNotIn("allowlist", config)
        self.assertNotIn("allowlists", config)

    def test_justfile_recipes(self) -> None:
        text = (REPO_ROOT / "justfile").read_text()
        self.assertIn("git config core.hooksPath .githooks", text)
        self.assertIn("gitleaks git --pre-commit --staged --redact", text)
        self.assertRegex(text, r"(?m)^    gitleaks git --redact$")
        lint = next(line for line in text.splitlines() if line.startswith("lint:"))
        self.assertIn("secrets-scan", lint.split())
        setup = text.split("\nsetup:", 1)[1].split("\n\n", 1)[0]
        self.assertIn("just hooks-install", setup)


@unittest.skipUnless(GIT and BASH and ENV_BIN, "git, bash and env are required")
class HookBehaviourTest(unittest.TestCase):
    """Run ``git commit`` in a throw-away repository with the real hook."""

    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ntl-hooks-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        # A space in the path checks the quoting.
        self.repo = self.tmp / "repo with space"
        (self.repo / ".githooks").mkdir(parents=True)
        shutil.copy2(HOOK, self.repo / ".githooks" / "pre-commit")
        self.home = self.tmp / "home"
        self.home.mkdir()
        # A PATH holding only git, bash and env: no mise in it.
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for tool in (GIT, BASH, ENV_BIN):
            (self.bin / pathlib.Path(tool).name).symlink_to(tool)
        self.git("init", "-q")
        self.git("config", "core.hooksPath", ".githooks")
        (self.repo / "a.txt").write_text("hello\n")
        self.git("add", "a.txt")

    def git(self, *args: str, env_extra: dict[str, str] | None = None):
        env = {
            **GIT_ENV,
            "HOME": str(self.home),
            "PATH": str(self.bin),
            **(env_extra or {}),
        }
        return subprocess.run(
            [GIT, "-C", str(self.repo), *args],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def write_stub_mise(
        self, directory: pathlib.Path, gitleaks_ok: bool, checks_ok: bool = True
    ) -> pathlib.Path:
        """A fake mise that logs its arguments.

        It fails on ``exec -- gitleaks version`` if ``gitleaks_ok`` is false, and on
        ``exec -- just pre-commit`` if ``checks_ok`` is false.
        """
        directory.mkdir(parents=True, exist_ok=True)
        log = self.tmp / "mise.log"
        stub = directory / "mise"
        stub.write_text(
            "#!/usr/bin/env bash\n"
            f'printf "%s\\n" "$*" >> "{log}"\n'
            'if [[ "$*" == "exec -- gitleaks version" ]]; then\n'
            + (
                '  echo "8.30.1"\n'
                if gitleaks_ok
                else '  echo "stub: gitleaks missing" >&2\n  exit 1\n'
            )
            + "fi\n"
            'if [[ "$*" == "exec -- just pre-commit" ]]; then\n'
            + (
                "  exit 0\n"
                if checks_ok
                else '  echo "stub: checks failed" >&2\n  exit 1\n'
            )
            + "fi\n"
            "exit 0\n"
        )
        stub.chmod(0o755)
        return log

    def head_exists(self) -> bool:
        return self.git("rev-parse", "--verify", "-q", "HEAD").returncode == 0

    def test_refuses_commit_when_mise_is_missing(self) -> None:
        result = self.git("commit", "-q", "-m", "x")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mise not found", result.stderr)
        self.assertIn("commit refused", result.stderr)
        self.assertFalse(self.head_exists(), "no commit must have been created")

    def test_refusal_does_not_suggest_no_verify_to_agents(self) -> None:
        # Agents read this message: the bypass is for the user in an emergency only.
        for stub in (False, True):
            if stub:
                self.write_stub_mise(self.bin, gitleaks_ok=False)
            result = self.git("commit", "-q", "-m", "x")
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("--no-verify", result.stderr)
            self.assertIn("user only", result.stderr)

    def test_refuses_commit_when_gitleaks_is_missing(self) -> None:
        log = self.write_stub_mise(self.bin, gitleaks_ok=False)
        result = self.git("commit", "-q", "-m", "x")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gitleaks is not available", result.stderr)
        self.assertIn("stub: gitleaks missing", result.stderr)
        self.assertFalse(self.head_exists())
        # The checks recipe must not even have been started.
        self.assertNotIn("just pre-commit", log.read_text())

    def test_accepts_commit_and_runs_just_pre_commit_via_mise(self) -> None:
        log = self.write_stub_mise(self.bin, gitleaks_ok=True)
        result = self.git("commit", "-q", "-m", "x")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.head_exists())
        self.assertEqual(
            log.read_text().splitlines(),
            ["exec -- gitleaks version", "exec -- just pre-commit"],
        )

    def test_falls_back_to_local_bin_mise(self) -> None:
        log = self.write_stub_mise(self.home / ".local" / "bin", gitleaks_ok=True)
        result = self.git("commit", "-q", "-m", "x")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("exec -- just pre-commit", log.read_text())

    def test_failing_checks_block_the_commit(self) -> None:
        # A mise whose `just pre-commit` fails stands for a detected secret.
        log = self.write_stub_mise(self.bin, gitleaks_ok=True, checks_ok=False)
        result = self.git("commit", "-q", "-m", "x")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.head_exists())
        # The hook got past the gitleaks check and really ran the failing recipe.
        self.assertIn("exec -- just pre-commit", log.read_text().splitlines())
        self.assertIn("stub: checks failed", result.stderr)

    def test_no_verify_bypasses_the_hook(self) -> None:
        result = self.git("commit", "-q", "--no-verify", "-m", "x")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.head_exists())


if __name__ == "__main__":
    unittest.main()
