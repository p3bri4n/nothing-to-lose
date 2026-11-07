#!/usr/bin/env python3
"""Check that relative links in Markdown files point to existing files.

Usage: python3 tools/check_links.py  (from the repository root)
Exit code 1 if at least one link is broken.
"""

import pathlib
import re
import sys

LINK = re.compile(r"\]\(([^)\s]+)\)")
SKIP_DIRS = {".git", "node_modules", "target", ".terraform", "runs", "shots"}


def main() -> int:
    root = pathlib.Path(".").resolve()
    broken = []
    for md in root.rglob("*.md"):
        if any(part in SKIP_DIRS for part in md.relative_to(root).parts):
            continue
        text = md.read_text(encoding="utf-8")
        # Ignore links inside fenced code blocks.
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        # Ignore inline code.
        text = re.sub(r"`[^`\n]*`", "", text)
        for target in LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path = target.split("#", 1)[0]
            if not path:
                continue
            if not (md.parent / path).exists():
                broken.append(f"{md.relative_to(root)}: {target}")
    for line in broken:
        print(f"Lien cassé : {line}")
    print(f"{len(broken)} lien(s) cassé(s).")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
