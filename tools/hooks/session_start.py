#!/usr/bin/env python3
"""SessionStart hook: tell the user where the project stands.

Reads the latest development journal entry (docs/journal/), the last commit and
the Git state, then prints a JSON object on stdout:
  - systemMessage: shown to the user at session start (next steps only);
  - hookSpecificOutput.additionalContext: injected in the model context (also open issues).
It also warns when the Bash guard (guard_bash.py) logged failures: the number of
``hook error`` lines of ``.cache/hooks/guard.log`` (decision U2: a failing guard refuses
git/gh commands, so the user must hear about it).
It also warns, without ever printing a value, when the GitHub identity of the session is not
the agents machine account: ``GITHUB_TOKEN`` (the owner's administration token) present, or
``GH_TOKEN`` absent (docs/technique/compte-machine-agents.md).
Never fails: any error yields a short message and exit code 0.
"""

import json
import os
import pathlib
import re
import subprocess
import sys
from collections.abc import Mapping


def git(root: pathlib.Path, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=5
        )
        return out.stdout.strip()
    except Exception:
        return ""


GUARD_LOG = pathlib.Path(".cache") / "hooks" / "guard.log"
GUARD_ERROR_MARKER = "hook error"


def guard_error_count(root: pathlib.Path) -> int:
    """Number of ``hook error`` lines in the Bash guard log (0 if absent or unreadable)."""
    try:
        text = (root / GUARD_LOG).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return 0
    return sum(1 for line in text.splitlines() if GUARD_ERROR_MARKER in line)


def token_warning(environ: Mapping[str, str]) -> str | None:
    """Warning about the GitHub credentials of the session, or None. Never shows a value."""
    problems = []
    if environ.get("GITHUB_TOKEN"):
        problems.append(
            "GITHUB_TOKEN est présent (jeton d'administration du propriétaire ?) : "
            "il ne doit pas être dans l'environnement des agents"
        )
    if not environ.get("GH_TOKEN"):
        problems.append(
            "GH_TOKEN est absent : gh et git n'utilisent pas le compte machine des agents"
        )
    if not problems:
        return None
    return (
        "Identité GitHub : "
        + " ; ".join(problems)
        + ". Lancer Claude Code comme décrit dans docs/technique/compte-machine-agents.md "
        "(étape (f)), ou prévenir l'utilisateur."
    )


def latest_journal(root: pathlib.Path):
    entries = [
        p
        for p in (root / "docs" / "journal").glob("20*.md")
        if re.match(r"\d{4}-\d{2}-\d{2}", p.name)
    ]
    if not entries:
        return None
    return max(entries, key=lambda p: (p.name[:10], p.stat().st_mtime))


def section(text: str, title: str) -> str:
    match = re.search(
        rf"^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M
    )
    return match.group(1).strip() if match else ""


def build(
    root: pathlib.Path, full: bool, environ: Mapping[str, str] | None = None
) -> str:
    lines = ["Nothing To Lose — où on en est"]
    journal = latest_journal(root)
    if journal:
        text = journal.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip() if text else journal.name
        lines.append(f"Dernier journal : {journal.name} — {title}")
        names = (
            ("Prochaines étapes", "Problèmes et points ouverts")
            if full
            else ("Prochaines étapes",)
        )
        for name in names:
            body = section(text, name)
            if body:
                lines += ["", f"{name} :", body]
    else:
        lines.append("Aucune entrée de journal trouvée dans docs/journal/.")
    branch = git(root, "branch", "--show-current")
    last = git(root, "log", "-1", "--format=%h %s")
    status = git(root, "status", "--short")
    changed = len(status.splitlines()) if status else 0
    lines += [
        "",
        f"Git : branche {branch or '?'}, dernier commit {last or '?'}",
        f"Fichiers modifiés non commités : {changed}",
    ]
    remotes = git(root, "remote")
    if not remotes:
        lines.append("Aucun remote configuré (premier push pas encore fait).")
    errors = guard_error_count(root)
    if errors > 0:
        lines.append(
            f"Garde-fou Bash : {errors} ligne(s) « hook error » dans "
            f"{GUARD_LOG.as_posix()} (le garde-fou a échoué ; les commandes git/gh sont "
            "refusées dans ce cas). Voir docs/technique/garde-fous-bash.md ; prévenir "
            "l'utilisateur."
        )
    warning = token_warning(os.environ if environ is None else environ)
    if warning:
        lines.append(warning)
    return "\n".join(lines)


def main() -> int:
    try:
        root = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()
        message = build(root, full=False)
        context = build(root, full=True)
    except Exception as exc:  # never block a session start
        message = context = f"Résumé de session indisponible ({exc})."
    message, context = message[:9000], context[:9000]
    json.dump(
        {
            "systemMessage": message,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            },
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
