#!/usr/bin/env python3
"""Check that installed tools match the exact versions pinned in mise.toml.

Usage: python tools/check_tool_versions.py [--print] [--ci]  (from anywhere)

- Reads ``mise.toml`` (``[tools]``) and ``rust-toolchain.toml`` at the repository
  root; the toolchain channel must equal the ``rust`` version of ``mise.toml``.
- Runs ``<binary> --version`` through the real ``PATH`` and extracts the version
  with a per-tool regular expression (``TOOLS`` below).
- Prints one line per tool: ``tool expected found status``.
- ``--ci`` skips tools flagged ``local_only`` (e.g. Claude Code).
- ``--print`` prints the normalised list (binary, expected version) and exits
  without running anything.

Exit code 1 if a tool is missing, has the wrong version, or if the configuration
is inconsistent.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import re
import subprocess
import sys
import tomllib

# Seconds allowed for each ``--version`` call.
TIMEOUT_SECONDS = 20

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


@dataclasses.dataclass(frozen=True)
class ToolSpec:
    """How to query one tool and parse its version output."""

    binary: str
    # Must expose exactly one group: the bare version number (no leading "v").
    pattern: str
    args: tuple[str, ...] = ("--version",)
    local_only: bool = False


# Keyed by the last segment of the mise key ("aqua:cli/cli" -> "cli").
# Pattern details were taken from the real outputs of the pinned versions.
TOOLS: dict[str, ToolSpec] = {
    "node": ToolSpec("node", r"^v(\d+\.\d+\.\d+)"),
    "python": ToolSpec("python", r"^Python (\d+\.\d+\.\d+)"),
    "rust": ToolSpec("rustc", r"^rustc (\d+\.\d+\.\d+)"),
    "uv": ToolSpec("uv", r"^uv (\d+\.\d+\.\d+)"),
    "just": ToolSpec("just", r"^just (\d+\.\d+\.\d+)"),
    "terraform": ToolSpec("terraform", r"^Terraform v(\d+\.\d+\.\d+)"),
    "gitleaks": ToolSpec("gitleaks", r"^gitleaks version (\d+\.\d+\.\d+)"),
    "actionlint": ToolSpec("actionlint", r"^(\d+\.\d+\.\d+)"),
    "ruff": ToolSpec("ruff", r"^ruff (\d+\.\d+\.\d+)"),
    "taplo": ToolSpec("taplo", r"^taplo (\d+\.\d+\.\d+)"),
    "prettier": ToolSpec("prettier", r"^(\d+\.\d+\.\d+)"),
    "sh": ToolSpec("shfmt", r"^v(\d+\.\d+\.\d+)"),
    "shellcheck": ToolSpec("shellcheck", r"^version: (\d+\.\d+\.\d+)"),
    "cli": ToolSpec("gh", r"^gh version (\d+\.\d+\.\d+)"),
    "claude-code": ToolSpec(
        "claude", r"^(\d+\.\d+\.\d+) \(Claude Code\)", local_only=True
    ),
}


# --- Pure functions (no I/O): parsing and comparison --------------------------


def tool_key(mise_key: str) -> str:
    """Normalise a mise key: ``"aqua:astral-sh/uv"`` -> ``"uv"``, ``"npm:prettier"`` -> ``"prettier"``."""
    name = mise_key.split(":", 1)[-1]
    return name.rsplit("/", 1)[-1]


def expected_version(value: str | dict) -> str:
    """Return the pinned version from a mise tool entry (string or table)."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("version"), str):
        return value["version"]
    raise ValueError(f"cannot read a version from {value!r}")


def parse_version(output: str, pattern: str) -> str | None:
    """Extract the version from the output of ``<tool> --version``; None if no match."""
    match = re.search(pattern, output, flags=re.MULTILINE)
    return match.group(1) if match else None


def compare(expected: str, found: str | None) -> str:
    """Return the status: ``ok``, ``missing`` or ``mismatch``."""
    if found is None:
        return "missing"
    return "ok" if found == expected else "mismatch"


def format_line(name: str, expected: str, found: str | None, status: str) -> str:
    """One report line: ``tool expected found status``."""
    return f"{name:<11} {expected:<9} {found or '-':<9} {status}"


def check_rust_toolchain(mise_rust: str, toolchain: dict) -> str | None:
    """Return an error message if rust-toolchain.toml disagrees with mise.toml, else None."""
    channel = toolchain.get("toolchain", {}).get("channel")
    if channel != mise_rust:
        return f"rust-toolchain.toml channel {channel!r} differs from mise.toml rust {mise_rust!r}"
    return None


# --- Execution -----------------------------------------------------------------


def run_version(spec: ToolSpec) -> tuple[str | None, str]:
    """Run the tool through the real PATH; return (version or None, status detail)."""
    try:
        proc = subprocess.run(
            [spec.binary, *spec.args],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return None, "not found in PATH"
    except subprocess.TimeoutExpired:
        return None, f"timeout after {TIMEOUT_SECONDS}s"
    except OSError as exc:  # e.g. PermissionError on a non-executable file in PATH
        return None, f"cannot run ({exc.__class__.__name__})"
    output = proc.stdout + proc.stderr
    version = parse_version(output, spec.pattern)
    if version is None:
        return None, "unparseable output"
    return version, ""


def load_config(root: pathlib.Path) -> tuple[dict[str, str], dict]:
    """Load the pinned versions (keyed by tool key) and the rust-toolchain data."""
    with open(root / "mise.toml", "rb") as f:
        mise = tomllib.load(f)
    with open(root / "rust-toolchain.toml", "rb") as f:
        toolchain = tomllib.load(f)
    pinned: dict[str, str] = {}
    for name, value in mise.get("tools", {}).items():
        key = tool_key(name)
        if key in pinned:
            raise ValueError(f"mise.toml: several entries map to tool {key!r}")
        pinned[key] = expected_version(value)
    return pinned, toolchain


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--ci", action="store_true", help="skip local-only tools")
    parser.add_argument(
        "--print",
        action="store_true",
        dest="print_only",
        help="print the normalised list and exit",
    )
    args = parser.parse_args(argv)

    try:
        pinned, toolchain = load_config(REPO_ROOT)
    except (OSError, tomllib.TOMLDecodeError, ValueError) as exc:
        print(f"error: cannot load configuration: {exc}", file=sys.stderr)
        return 1
    failed = False

    unknown = sorted(set(pinned) - set(TOOLS))
    for key in unknown:
        print(
            f"error: tool {key!r} in mise.toml has no entry in TOOLS", file=sys.stderr
        )
        failed = True

    error = check_rust_toolchain(pinned.get("rust", ""), toolchain)
    if error:
        print(f"error: {error}", file=sys.stderr)
        failed = True

    selected = [(key, TOOLS[key]) for key in pinned if key in TOOLS]
    if args.ci:
        selected = [(k, s) for k, s in selected if not s.local_only]

    if args.print_only:
        for key, spec in selected:
            print(f"{spec.binary} {pinned[key]}")
        return 1 if failed else 0

    for key, spec in selected:
        expected = pinned[key]
        found, detail = run_version(spec)
        status = compare(expected, found)
        print(
            format_line(
                spec.binary,
                expected,
                found,
                status + (f" ({detail})" if detail else ""),
            )
        )
        failed = failed or status != "ok"
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
