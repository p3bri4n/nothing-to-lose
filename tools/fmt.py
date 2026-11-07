#!/usr/bin/env python3
"""Format (or check the formatting of) the repository files.

Usage: python3 tools/fmt.py (--write | --check) [paths...]  (from anywhere)

- This file is the single source of the mapping "extension -> formatter"
  (``FORMATTERS`` and ``EXTENSIONS`` below). Markdown is deliberately excluded
  (decision 0012).
- Without paths, every file tracked by Git is processed, except the deliberately
  badly formatted fixtures in ``tools/tests/fixtures/format/``. With explicit
  paths, exactly those files are processed (no exclusion; files with an unknown
  extension are skipped).
- Formatters run through ``mise exec --`` from the repository root, so that the
  versions pinned in ``mise.toml`` and the configuration files at the root
  (``ruff.toml``, ``taplo.toml``, ``.prettierrc.json``, ``rustfmt.toml``,
  ``.editorconfig``) apply. Commands are argument lists, never shell strings.
- prettier always receives ``--config <root>/.prettierrc.json``: this disables its
  upward search for configuration files, so a ``prettier.config.js`` (which prettier
  would execute) sitting next to a formatted file is never loaded.
- ``--write`` rewrites the files in place; ``--check`` only reports.

Exit code 1 if a file is not formatted (``--check``), if a formatter fails or is
missing, or if a given path does not exist; 2 for a usage error.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Seconds allowed for one formatter invocation (all its files at once).
TIMEOUT_SECONDS = 600

# Tracked files under these directories (relative to the root) are skipped when
# no explicit path is given: fixtures are badly formatted on purpose.
EXCLUDED_DIRS: tuple[str, ...] = ("tools/tests/fixtures/format",)


@dataclasses.dataclass(frozen=True)
class Formatter:
    """How to run one formatter on a list of files."""

    name: str
    # Command prefixes (the files are appended). Verified on the pinned versions.
    write: tuple[str, ...]
    check: tuple[str, ...]
    # Root-relative configuration file always passed with ``--config`` (None: the
    # formatter finds its own configuration).
    config_file: str | None = None


FORMATTERS: dict[str, Formatter] = {
    f.name: f
    for f in (
        # rustfmt works per file (it follows ``mod`` declarations itself).
        Formatter("rustfmt", ("rustfmt",), ("rustfmt", "--check")),
        Formatter("ruff", ("ruff", "format"), ("ruff", "format", "--check")),
        Formatter("taplo", ("taplo", "fmt"), ("taplo", "fmt", "--check")),
        Formatter(
            "terraform",
            ("terraform", "fmt"),
            ("terraform", "fmt", "-check", "-diff"),
        ),
        # Explicit style (2 spaces, indented case), same as .editorconfig [*.sh].
        Formatter(
            "shfmt",
            ("shfmt", "-i", "2", "-ci", "-w"),
            ("shfmt", "-i", "2", "-ci", "-d"),
        ),
        # prettier is installed by mise (no package.json at the root).
        # ``--config`` is mandatory: see the module docstring (no config search).
        Formatter(
            "prettier",
            ("prettier", "--write"),
            ("prettier", "--check"),
            config_file=".prettierrc.json",
        ),
    )
}

# Lower-case extension (with the dot) -> formatter name. No Markdown.
EXTENSIONS: dict[str, str] = {
    ".rs": "rustfmt",
    ".py": "ruff",
    ".toml": "taplo",
    ".tf": "terraform",
    ".sh": "shfmt",
    ".json": "prettier",
    ".yaml": "prettier",
    ".yml": "prettier",  # same language as .yaml (the workflows use .yml)
    ".js": "prettier",
    ".ts": "prettier",
    ".html": "prettier",
    ".css": "prettier",
}


# --- Pure functions (no I/O): selection and command construction ---------------


def formatter_for(path: str) -> Formatter | None:
    """Return the formatter for a path, or None if the extension is not handled."""
    suffix = pathlib.PurePosixPath(path.replace("\\", "/")).suffix.lower()
    name = EXTENSIONS.get(suffix)
    return FORMATTERS[name] if name else None


def is_excluded(path: str, excluded_dirs: tuple[str, ...] = EXCLUDED_DIRS) -> bool:
    """True if a root-relative POSIX path lies in one of the excluded directories."""
    return any(path == d or path.startswith(d + "/") for d in excluded_dirs)


def filter_paths(
    paths: list[str], excluded_dirs: tuple[str, ...] = EXCLUDED_DIRS
) -> list[str]:
    """Drop the excluded paths and the ones without a formatter; keep the order."""
    return [p for p in paths if not is_excluded(p, excluded_dirs) and formatter_for(p)]


def group_by_formatter(paths: list[str]) -> dict[str, list[str]]:
    """Group paths by formatter name, in the order of ``FORMATTERS``."""
    groups: dict[str, list[str]] = {name: [] for name in FORMATTERS}
    for path in paths:
        formatter = formatter_for(path)
        if formatter:
            groups[formatter.name].append(path)
    return {name: files for name, files in groups.items() if files}


def protect_arg(path: str) -> str:
    """Make a path safe as a command-line argument (never read as an option)."""
    return "./" + path if path.startswith("-") else path


def build_command(
    formatter: Formatter,
    mode: str,
    files: list[str],
    root: pathlib.Path = REPO_ROOT,
) -> list[str]:
    """The full command (through mise) for one formatter. ``mode``: write|check."""
    if mode not in ("write", "check"):
        raise ValueError(f"unknown mode {mode!r}")
    prefix = formatter.write if mode == "write" else formatter.check
    config = (
        ["--config", str(root / formatter.config_file)] if formatter.config_file else []
    )
    return ["mise", "exec", "--", *prefix, *config, *(protect_arg(f) for f in files)]


def display_path(path: pathlib.Path, root: pathlib.Path) -> str:
    """Root-relative POSIX path if the file is inside the root, else absolute."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


# --- Execution -----------------------------------------------------------------


def tracked_files(root: pathlib.Path) -> list[str]:
    """Files tracked by Git (root-relative POSIX paths) that still exist on disk."""
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    names = [n for n in proc.stdout.split("\0") if n]
    return [n for n in names if (root / n).is_file()]


def resolve_explicit(raw: list[str], root: pathlib.Path) -> tuple[list[str], list[str]]:
    """Resolve user paths (relative to the current directory) -> (paths, errors)."""
    paths: list[str] = []
    errors: list[str] = []
    for item in raw:
        resolved = pathlib.Path(item).resolve()
        if not resolved.is_file():
            errors.append(f"error: not a file: {item}")
            continue
        paths.append(display_path(resolved, root))
    return paths, errors


def run_formatter(
    formatter: Formatter, mode: str, files: list[str], root: pathlib.Path
) -> bool:
    """Run one formatter on its files; True on success."""
    command = build_command(formatter, mode, files)
    try:
        proc = subprocess.run(command, cwd=root, timeout=TIMEOUT_SECONDS, check=False)
    except FileNotFoundError:
        print(f"error: cannot run {command[0]!r} (not in PATH)", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print(
            f"error: {formatter.name} timed out after {TIMEOUT_SECONDS}s",
            file=sys.stderr,
        )
        return False
    except OSError as exc:
        print(
            f"error: cannot run {formatter.name} ({exc.__class__.__name__})",
            file=sys.stderr,
        )
        return False
    if proc.returncode != 0:
        verb = "needs formatting" if mode == "check" else "failed"
        print(
            f"error: {formatter.name} {verb} (exit {proc.returncode}, "
            f"{len(files)} file(s))",
            file=sys.stderr,
        )
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="rewrite files in place")
    mode.add_argument("--check", action="store_true", help="report unformatted files")
    parser.add_argument(
        "paths", nargs="*", help="files to process (default: files tracked by Git)"
    )
    args = parser.parse_args(argv)
    run_mode = "write" if args.write else "check"

    if args.paths:
        candidates, errors = resolve_explicit(args.paths, REPO_ROOT)
        selected = [p for p in candidates if formatter_for(p)]
    else:
        try:
            candidates, errors = tracked_files(REPO_ROOT), []
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"error: cannot list Git files: {exc}", file=sys.stderr)
            return 1
        selected = filter_paths(candidates)
    for message in errors:
        print(message, file=sys.stderr)

    ok = not errors
    groups = group_by_formatter(selected)
    for name, files in groups.items():
        ok = run_formatter(FORMATTERS[name], run_mode, files, REPO_ROOT) and ok
    print(
        f"fmt {run_mode}: {len(selected)} file(s), "
        f"{len(groups)} formatter(s), {'ok' if ok else 'FAILED'}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
