#!/usr/bin/env python3
"""PostToolUse hook: format the file Claude Code has just written or edited.

Reads the hook JSON on stdin, takes ``tool_input.file_path`` and, when the file is
worth formatting, runs ``tools/fmt.py --write <file>`` (argument list, no shell).

Never blocks: the exit code is always 0, even on invalid JSON or an unexpected
exception. Nothing is printed on stdout (it would pollute the session). A missing
formatter or a formatting error is logged, one dated line each, in
``.cache/hooks/format.log``.

Skipped: paths outside ``$CLAUDE_PROJECT_DIR`` (symlinks and ``..`` resolved), paths
ignored by Git, anything under ``.git``, generated directories, missing files,
extensions without a formatter (Markdown included) and the badly formatted fixtures of
``tools/tests/fixtures/format/``.

Security: the formatters run tools whose configuration can execute code (mise
``mise.toml``, prettier configuration, ``rust-toolchain.toml``). The hook therefore
refuses to format (and logs why) while one of ``GUARDED_CONFIG_FILES`` differs from
``HEAD``: modified, deleted, untracked or ignored-but-present. A file absent from both
``HEAD`` and the disk is normal. The formatter runs in its own process group, killed on
timeout, with ``MISE_EXEC_AUTO_INSTALL=false`` (no tool download).

Disabled with ``NTL_FORMAT_HOOK=off``.
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
from collections.abc import Mapping
from types import ModuleType

HOOKS_DIR = pathlib.Path(__file__).resolve().parent
FMT_PATH = HOOKS_DIR.parent / "fmt.py"


def load_fmt(path: pathlib.Path = FMT_PATH) -> ModuleType | None:
    """Load ``tools/fmt.py`` (single source of the extension -> formatter mapping).

    Loaded by file path, without touching ``sys.path`` (nothing else can be imported
    by accident). Returns None if it cannot be loaded: a broken fmt.py must not make
    the hook fail (``skip_reason`` then raises, and ``run`` logs ``hook error``).
    """
    name = "ntl_fmt"
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        previous = sys.modules.get(name)
        sys.modules[name] = module  # dataclasses look their module up here
        try:
            spec.loader.exec_module(module)
        except BaseException:
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
            raise
        return module
    except Exception:
        return None


fmt = load_fmt()

# Worst case of one run: git check-ignore + git status (guard) + formatter + reaping
# a killed formatter. Must stay below the ``timeout`` of the hook in
# .claude/settings.json (30 s); a test checks it.
FORMAT_TIMEOUT_SECONDS = 20
GIT_TIMEOUT_SECONDS = 3
REAP_TIMEOUT_SECONDS = 2
# A formatting slower than this is logged (it is a sign that something is wrong).
SLOW_FORMAT_SECONDS = 5
LOG_RELATIVE_PATH = pathlib.PurePosixPath(".cache/hooks/format.log")
# The log is rotated to ``format.log.1`` (the previous one is replaced) beyond this.
LOG_MAX_BYTES = 1_000_000
# Directory names skipped at any depth / only at the top level of the project.
GENERATED_ANYWHERE = frozenset({"target", "node_modules", ".cache"})
GENERATED_TOP_LEVEL = frozenset({"runs", "shots"})
# Path components that are never formatted, whatever their depth.
NEVER_TOUCH = frozenset({".git"})
# Files that make a formatter run code (or choose which tool it runs). While one of
# them differs from HEAD, nothing is formatted. Root-relative POSIX paths.
GUARDED_CONFIG_FILES = (
    "mise.toml",
    "mise.local.toml",
    ".prettierrc.json",
    "rust-toolchain.toml",
)
# Never let mise download and install a missing tool while formatting.
FORMATTER_ENV_OVERRIDES = {"MISE_EXEC_AUTO_INSTALL": "false"}
MAX_LOGGED_OUTPUT = 300


# --- Pure functions (no I/O): the decision to skip a path ------------------------


def is_disabled(env: Mapping[str, str]) -> bool:
    """True if the hook is switched off by ``NTL_FORMAT_HOOK=off``."""
    return env.get("NTL_FORMAT_HOOK", "").strip().lower() == "off"


def extract_file_path(payload: object) -> str | None:
    """``tool_input.file_path`` of a hook payload, or None if absent or invalid."""
    if not isinstance(payload, dict):
        return None
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    file_path = tool_input.get("file_path")
    if isinstance(file_path, str) and file_path.strip() and "\0" not in file_path:
        return file_path
    return None


def skip_reason(relative_path: str) -> str | None:
    """Why a project-relative POSIX path must not be formatted (None: format it)."""
    if fmt is None:
        raise RuntimeError("tools/fmt.py cannot be imported")
    parts = pathlib.PurePosixPath(relative_path).parts
    if any(part in NEVER_TOUCH for part in parts):
        return "never touched"
    directories = parts[:-1]
    if any(part in GENERATED_ANYWHERE for part in directories):
        return "generated directory"
    if directories and directories[0] in GENERATED_TOP_LEVEL:
        return "generated directory"
    if fmt.is_excluded(relative_path):
        return "formatter fixture"
    if fmt.formatter_for(relative_path) is None:
        return "extension not handled"
    return None


def format_command(root: pathlib.Path, path: pathlib.Path) -> list[str]:
    """The command that formats one file (argument list, never a shell string)."""
    return [sys.executable, str(root / "tools" / "fmt.py"), "--write", str(path)]


# --- Execution -------------------------------------------------------------------


def project_root(env: Mapping[str, str]) -> pathlib.Path:
    """``$CLAUDE_PROJECT_DIR`` (resolved), else the repository holding this script."""
    configured = env.get("CLAUDE_PROJECT_DIR")
    if configured:
        return pathlib.Path(configured).resolve()
    return HOOKS_DIR.parent.parent


def resolve_in_project(raw: str, root: pathlib.Path) -> pathlib.Path | None:
    """Existing file inside the project (symlinks and ``..`` resolved), else None."""
    path = pathlib.Path(raw)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved if resolved.is_file() else None


def is_git_ignored(root: pathlib.Path, relative_path: str) -> bool | None:
    """True if Git ignores the path, False if not, None if Git cannot tell."""
    proc = subprocess.run(
        ["git", "check-ignore", "-q", "--", relative_path],
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
    )
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    return None


def config_guard_problem(root: pathlib.Path) -> str | None:
    """Why the configuration files cannot be trusted (None: they match HEAD).

    One ``git status`` call on ``GUARDED_CONFIG_FILES``: any output means a file is
    modified, staged, deleted, untracked or ignored-but-present (``mise.local.toml``).
    A file absent from both HEAD and the disk prints nothing. Git failing (no HEAD,
    timeout...) is a refusal too: when in doubt, nothing runs.
    """
    command = [
        "git",
        "--no-optional-locks",
        "status",
        "--porcelain=v1",
        "-z",
        "--no-renames",
        "--ignored=matching",
        "--untracked-files=all",
        "--",
        *GUARDED_CONFIG_FILES,
    ]
    try:
        proc = subprocess.run(
            command,
            cwd=root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except Exception as exc:
        return f"cannot compare the configuration files with HEAD ({exc!r})"
    if proc.returncode != 0:
        return (
            "cannot compare the configuration files with HEAD "
            f"(git exit {proc.returncode})"
        )
    entries = [entry for entry in proc.stdout.split("\0") if entry]
    if entries:
        names = ", ".join(entry[3:] for entry in entries)
        return f"configuration differs from HEAD ({names})"
    return None


def log_line(root: pathlib.Path, message: str) -> None:
    """Append one dated line to the log; a failure to log is silently ignored.

    The log is bounded: beyond ``LOG_MAX_BYTES`` it is moved to ``format.log.1``.
    """
    try:
        log_file = root / LOG_RELATIVE_PATH
        log_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            if log_file.stat().st_size > LOG_MAX_BYTES:
                os.replace(log_file, log_file.with_name(log_file.name + ".1"))
        except FileNotFoundError:
            pass
        stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        single_line = " ".join(message.split())
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {single_line}\n")
    except Exception:
        pass


def formatter_env(env: Mapping[str, str]) -> dict[str, str]:
    """Environment of the formatter: the current one, plus the safety overrides."""
    return {**os.environ, **env, **FORMATTER_ENV_OVERRIDES}


def kill_process_group(proc: subprocess.Popen) -> None:
    """SIGKILL the whole process group of a formatter and reap it; never raises."""
    try:
        if hasattr(os, "killpg"):
            os.killpg(proc.pid, signal.SIGKILL)
        else:  # pragma: no cover - no process groups on this platform
            proc.kill()
    except OSError:  # already gone
        pass
    try:
        proc.communicate(timeout=REAP_TIMEOUT_SECONDS)
    except Exception:
        pass


def format_file(
    root: pathlib.Path,
    path: pathlib.Path,
    relative_path: str,
    env: Mapping[str, str] | None = None,
) -> None:
    """Run the formatter on one file; log any failure, never raise.

    The formatter leads its own process group (``start_new_session``), so that on
    timeout the formatter and everything it started (mise, the tool...) is killed.
    """
    started = time.monotonic()
    try:
        proc = subprocess.Popen(
            format_command(root, path),
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=formatter_env(env or {}),
            start_new_session=True,
        )
    except Exception as exc:
        log_line(root, f"{relative_path}: cannot run formatter ({exc!r})")
        return
    try:
        stdout, stderr = proc.communicate(timeout=FORMAT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        kill_process_group(proc)
        log_line(
            root,
            f"{relative_path}: formatter timed out after {FORMAT_TIMEOUT_SECONDS}s, "
            "process group killed",
        )
        return
    except Exception as exc:
        kill_process_group(proc)
        log_line(root, f"{relative_path}: cannot run formatter ({exc!r})")
        return
    elapsed = time.monotonic() - started
    if proc.returncode != 0:
        detail = (stderr or stdout or "").strip()[-MAX_LOGGED_OUTPUT:]
        log_line(
            root,
            f"{relative_path}: formatter failed (exit {proc.returncode}) {detail}",
        )
    if elapsed > SLOW_FORMAT_SECONDS:
        log_line(root, f"{relative_path}: slow formatting ({elapsed:.1f}s)")


def process(payload: object, env: Mapping[str, str]) -> None:
    """Decide whether to format the file named by the payload, and do it."""
    if is_disabled(env):
        return
    raw = extract_file_path(payload)
    if raw is None:
        return
    root = project_root(env)
    path = resolve_in_project(raw, root)
    if path is None:
        return
    relative_path = path.relative_to(root).as_posix()
    if skip_reason(relative_path) is not None:
        return
    ignored = is_git_ignored(root, relative_path)
    if ignored is None:
        log_line(root, f"{relative_path}: git check-ignore failed, file skipped")
        return
    if ignored:
        return
    problem = config_guard_problem(root)
    if problem is not None:
        log_line(root, f"{relative_path}: formatting refused, {problem}")
        return
    format_file(root, path, relative_path, env)


def run(stdin_text: str, env: Mapping[str, str]) -> int:
    """Entry point without side effects on the process: always returns 0."""
    try:
        process(json.loads(stdin_text), env)
    except Exception as exc:  # never block the session
        try:
            log_line(project_root(env), f"hook error: {exc!r}")
        except Exception:
            pass
    return 0


def main() -> int:
    try:
        stdin_text = sys.stdin.read()
    except Exception:
        stdin_text = ""
    return run(stdin_text, os.environ)


if __name__ == "__main__":
    sys.exit(main())
