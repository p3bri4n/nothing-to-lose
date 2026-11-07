#!/usr/bin/env python3
"""Check that the checklist of a pull request description is fully ticked.

The pull request body is read from the ``PR_BODY`` environment variable, never from
an argument and never interpolated into a shell command (injection, see plan PP R10).
The author is read from ``PR_AUTHOR``; pull requests of ``dependabot[bot]`` are exempt.

The checklist is the section titled exactly ``## Liste de contrôle``. It ends at the
next ``## `` heading or at the end of the body. HTML comments are ignored.

Usage: PR_BODY="$(cat body.md)" python3 tools/check_pr_checklist.py
Exit code 0: checklist complete (or exempt author). Exit code 1: incomplete, missing
or empty section.
"""

from __future__ import annotations

import os
import re
import sys

SECTION_TITLE = "Liste de contrôle"
EXEMPT_AUTHORS = frozenset({"dependabot[bot]"})

HEADING = re.compile(r"^##[ \t]+(.*?)[ \t]*$")
CHECKBOX = re.compile(r"^[ \t]*[-*+][ \t]+\[([ xX])\](.*)$")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def extract_section(body: str) -> list[str] | None:
    """Return the lines of the checklist section, or None if it is absent."""
    lines = HTML_COMMENT.sub("", body).splitlines()  # splitlines() handles CRLF
    section: list[str] | None = None
    for line in lines:
        heading = HEADING.match(line)
        if section is None:
            if heading and heading.group(1) == SECTION_TITLE:
                section = []
        elif line.startswith("## "):
            break
        else:
            section.append(line)
    return section


def parse_checkboxes(section: list[str]) -> list[tuple[bool, str]]:
    """Return ``(checked, label)`` for each checkbox line of the section."""
    boxes = []
    for line in section:
        match = CHECKBOX.match(line)
        if match:
            boxes.append((match.group(1) in "xX", match.group(2).strip()))
    return boxes


def check_body(body: str) -> tuple[int, list[str]]:
    """Pure check of a pull request body: return ``(exit_code, messages)``."""
    section = extract_section(body)
    if section is None:
        return 1, [f"Section « {SECTION_TITLE} » absente de la description de la PR."]
    boxes = parse_checkboxes(section)
    if not boxes:
        return 1, [f"Section « {SECTION_TITLE} » vide : aucune case à cocher trouvée."]
    unchecked = [label for checked, label in boxes if not checked]
    if unchecked:
        messages = ["Liste de contrôle incomplète : cases non cochées :"]
        messages += [f"- [ ] {label}" for label in unchecked]
        return 1, messages
    return 0, [f"Liste de contrôle complète ({len(boxes)} case(s) cochée(s))."]


def check_pull_request(body: str, author: str) -> tuple[int, list[str]]:
    """Check a pull request given its body and its author login."""
    if author in EXEMPT_AUTHORS:
        return 0, [f"PR de {author} : liste de contrôle non exigée."]
    return check_body(body)


def main() -> int:
    code, messages = check_pull_request(
        os.environ.get("PR_BODY", ""), os.environ.get("PR_AUTHOR", "")
    )
    for message in messages:
        print(message)
    return code


if __name__ == "__main__":
    sys.exit(main())
