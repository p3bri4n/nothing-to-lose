#!/usr/bin/env python3
"""PreToolUse hook (matcher ``Bash``): refuse the commands that bypass the Git circuit.

Reads the hook JSON on stdin (``tool_input.command``) and refuses, with exit code 2 and
an explanation in French on stderr (nothing on stdout), the commands listed in
``docs/technique/garde-fous-bash.md``:

* ``git commit --no-verify`` / ``-n`` (also inside a combined flag such as ``-an``),
  ``--no-verify`` of ``git push``, ``merge`` and ``rebase``;
* ``git push`` with a forced or destructive form (``--force``, ``-f``,
  ``--force-with-lease``, ``--force-if-includes``, ``+refspec``, ``--mirror``,
  ``--delete``, ``-d``, ``--prune``, ``:branch``, ``--all``, ``--branches``) or aiming
  at ``main`` / ``master`` (explicit refspec, ``HEAD`` or a push without refspec from
  that branch or whose configured target is that branch);
* a ``git`` configuration key that disables the Git hooks or redirects a push or a
  command (``core.hooksPath``, ``alias.*``, ``include.path``, ``includeIf.*``,
  ``remote.*.push``, ``remote.*.mirror``, ``push.default``), given by ``git -c``,
  ``--config-env``, ``GIT_CONFIG_*`` or written by ``git config``;
* ``gh pr merge`` (every variant), ``gh repo delete|edit|archive|...``,
  ``gh secret|variable set|delete``, ``gh alias set|import`` and the ``gh api`` calls
  that merge a pull request or change refs, contents, rulesets, branch protection or
  the settings of the repository; a ``gh api`` call too opaque to be judged (GraphQL
  query read from a file or computed, write to an unknown endpoint) is refused too;
* the agents' GitHub credentials: ``gh auth token|login|logout|switch|refresh``,
  ``gh auth status --show-token``, assigning ``GH_TOKEN``, ``GITHUB_TOKEN``,
  ``GH_ENTERPRISE_TOKEN`` or ``GITHUB_ENTERPRISE_TOKEN`` (before a command, after
  ``env``, in ``export`` / ``declare``) and removing them (``unset``, ``env -u``,
  ``export -n``). Reading them (``echo "${GH_TOKEN:+set}"``), ``gh auth status`` and
  ``gh auth setup-git`` stay allowed. This is a partial palliative (decision 0021,
  review of E10b): ``curl``, reading ``~/.config/gh`` or a file are not seen.

How: the command is parsed by a small shell tokenizer (quotes, ``;``, ``&&``, ``||``,
``|``, newlines, ``$(...)``, backticks, heredocs, redirections), so that a command is
looked at wherever it is in the line, and a text that merely *contains* ``--no-verify``
(``echo``, ``grep``, a commit message) is not a command. Wrappers (``env``, ``sudo``,
``time``, ``command``, ``xargs``, ``nohup``, ``timeout``, ``coproc``...), ``bash -c``,
``sh -c``, ``eval``, ``git rebase --exec`` and shell scripts fed on stdin are followed.
A sensitive command written in a form the guard does not understand is refused.

Failure (decision U2): if the guard itself fails (invalid JSON, no command, exception),
it refuses with exit code 2 when the raw input contains ``git`` or ``gh`` as a word, and
otherwise lets the command through; both leave a ``hook error`` line in
``.cache/hooks/guard.log`` (same convention as ``format.log``), which the SessionStart
hook counts. Blocks are logged too. There is deliberately no environment switch that
turns the guard off.

Limits: this is a textual analysis. It cannot see a script, an alias, a variable or a
program (``python -c``, ``curl``) that runs the forbidden command. The GitHub token of
the agents and the ruleset of ``main`` are the real defence (see the documentation).
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

HOOKS_DIR = pathlib.Path(__file__).resolve().parent

LOG_RELATIVE_PATH = pathlib.PurePosixPath(".cache/hooks/guard.log")
# The log is rotated to ``guard.log.1`` (the previous one is replaced) beyond this.
LOG_MAX_BYTES = 1_000_000
# Longest command copied to the log or echoed in the refusal message.
MAX_LOGGED_COMMAND = 300
# Longest single ``git`` read (branch, push target).
GIT_TIMEOUT_SECONDS = 3
# Total time allowed to all the ``git`` reads of one run; past it the branch is unknown
# and a push without explicit target is refused. Must stay well below the ``timeout`` of
# the hook in .claude/settings.json (10 s); a test checks it.
GIT_BUDGET_SECONDS = 6
# Deepest nesting followed ($(...), bash -c, eval...). Deeper is refused: no real
# command looks like that.
MAX_DEPTH = 12
# Branches nobody pushes to directly (the user merges the pull requests).
PROTECTED_BRANCHES = frozenset({"main", "master"})
# Stands for the unknown value of a command substitution inside a word.
PLACEHOLDER = "\x00"
# Raw input of a failing guard: refused when it mentions git or gh as a word (U2).
GIT_OR_GH = re.compile(r"\b(git|gh)\b")

ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Environment variables that carry the GitHub identity of ``gh`` and ``git`` (HTTPS helper).
TOKEN_VARIABLES = frozenset(
    {"GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"}
)
# ``gh auth`` actions that read, replace or drop the stored credentials.
GH_AUTH_FORBIDDEN = frozenset({"token", "login", "logout", "switch", "refresh"})
SHELL_KEYWORDS = frozenset(
    {"!", "{", "}", "if", "then", "else", "elif", "do", "while", "until"}
)
SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh", "ash"})
HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


# --- Verdicts ----------------------------------------------------------------------


@dataclass(frozen=True)
class Violation:
    """A forbidden command: a stable rule name and the explanation (French)."""

    rule: str
    reason: str


NO_VERIFY = Violation(
    "no-verify",
    "Contourner les hooks Git (--no-verify, -n) est interdit : le hook pre-commit "
    "(gitleaks, liens de la documentation) doit toujours s'exécuter. Corrigez la "
    "cause de l'échec du hook au lieu de le contourner.",
)
PUSH_FORCE = Violation(
    "push-force",
    "Un push forcé (--force, -f, --force-with-lease, --force-if-includes, +refspec) "
    "est interdit : il peut écraser l'historique distant. Poussez un nouveau commit "
    "ou demandez à l'utilisateur.",
)
PUSH_MIRROR = Violation(
    "push-mirror",
    "git push --mirror est interdit : il remplace tout le dépôt distant par le dépôt "
    "local.",
)
PUSH_DELETE = Violation(
    "push-delete",
    "Supprimer une branche ou une référence distante (--delete, -d, --prune, "
    ":branche) est interdit pour les agents. Demandez à l'utilisateur (la branche "
    "d'une PR fusionnée est supprimée à la fusion).",
)
PUSH_ALL = Violation(
    "push-all",
    "git push --all pousse aussi main : interdit. Poussez la branche de travail "
    "explicitement (git push -u origin HEAD).",
)
PUSH_MAIN = Violation(
    "push-main",
    "Pousser vers main ou master est interdit : passez par une branche et une pull "
    "request (git push -u origin HEAD depuis la branche de travail, puis gh pr "
    "create). L'utilisateur fusionne seul.",
)
PUSH_UNKNOWN = Violation(
    "push-unknown-branch",
    "Impossible de déterminer la branche visée par ce push (branche courante illisible "
    "ou cible calculée) : un push sans cible explicite connue est refusé par "
    "prudence. Nommez la branche de travail : git push -u origin <branche>.",
)
HOOKS_PATH = Violation(
    "hooks-path",
    "Modifier core.hooksPath désactiverait les hooks Git du dépôt : interdit. "
    "L'activation se fait par 'just hooks-install' (action de l'utilisateur).",
)
GIT_CONFIG = Violation(
    "git-config",
    "Cette clé de configuration Git (alias, include, includeIf, remote.*.push, "
    "remote.*.mirror, push.default) permettrait de contourner les règles du circuit "
    "Git (commande masquée, cible de push redirigée) : interdit pour les agents.",
)
PR_MERGE = Violation(
    "gh-pr-merge",
    "gh pr merge est interdit (toutes variantes, y compris --auto et --admin) : "
    "l'utilisateur fusionne seul (squash). Prévenez-le quand 'gh pr checks' est vert.",
)
GH_ADMIN = Violation(
    "gh-admin",
    "Cette commande gh modifie ou supprime la configuration du dépôt GitHub : "
    "interdit pour les agents. La configuration GitHub passe par Terraform "
    "(infra/terraform/) et son application est réservée à l'utilisateur.",
)
GH_API = Violation(
    "gh-api",
    "Cet appel d'API GitHub fusionne une pull request ou une branche, écrit des "
    "fichiers ou des commits, modifie des références, des rulesets, la protection de "
    "branche ou la configuration du dépôt : interdit pour les agents (fusion par "
    "l'utilisateur, configuration par Terraform).",
)
GH_API_OPAQUE = Violation(
    "gh-api-opaque",
    "Cet appel gh api ne peut pas être jugé : requête GraphQL lue dans un fichier "
    "(-F query=@…, --input) ou calculée par une substitution, ou écriture vers un "
    "endpoint calculé. Mettez la requête en ligne (-f query='…') et l'endpoint en "
    "clair dans la commande.",
)
GH_AUTH = Violation(
    "gh-auth",
    "gh auth token|login|logout|switch|refresh et gh auth status --show-token sont "
    "interdits pour les agents : ils manipuleraient ou afficheraient les identifiants "
    "GitHub. Le compte machine est fourni par l'environnement (GH_TOKEN) ; 'gh auth "
    "status' (sans --show-token) reste permis. Voir docs/technique/garde-fous-bash.md.",
)
GH_TOKEN_ENV = Violation(
    "gh-token-env",
    "Affecter ou retirer GH_TOKEN, GITHUB_TOKEN, GH_ENTERPRISE_TOKEN ou "
    "GITHUB_ENTERPRISE_TOKEN (devant une commande, après env, dans export/declare, "
    "unset, env -u) est interdit pour les agents : cela ferait agir gh avec un autre "
    "compte que le compte machine. Lire la variable reste permis. Voir "
    "docs/technique/garde-fous-bash.md.",
)
TOO_COMPLEX = Violation(
    "too-complex",
    "Commande trop imbriquée pour être analysée en sûreté ; simplifiez-la.",
)


# --- Shell tokenizer ----------------------------------------------------------------


class TooComplex(Exception):
    """The command is nested deeper than ``MAX_DEPTH``."""


@dataclass
class Command:
    """One simple command: its words (quotes removed) and the texts fed on stdin."""

    words: list[str] = field(default_factory=list)
    stdin: list[str] = field(default_factory=list)


_SIMPLE_ESCAPES = {
    "a": "\a",
    "b": "\b",
    "e": "\x1b",
    "E": "\x1b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
    "\\": "\\",
    "'": "'",
    '"': '"',
    "?": "?",
}
_ESCAPE_HEX_DIGITS = {"x": 2, "u": 4, "U": 8}


def _decode_escape(text: str, pos: int) -> tuple[str, int]:
    """Decode the ANSI-C escape whose letter is at ``text[pos]`` (after the backslash).

    Returns the decoded text and the position after the escape. An unknown escape stays
    as written (backslash included), like bash does.
    """
    ch = text[pos]
    if ch in _SIMPLE_ESCAPES:
        return _SIMPLE_ESCAPES[ch], pos + 1
    if ch in "01234567":  # \NNN, one to three octal digits
        end = pos
        while end < len(text) and end - pos < 3 and text[end] in "01234567":
            end += 1
        return chr(int(text[pos:end], 8) & 0xFF), end
    if ch in _ESCAPE_HEX_DIGITS:  # \xHH, \uHHHH, \UHHHHHHHH
        limit = _ESCAPE_HEX_DIGITS[ch]
        end = pos + 1
        while end < len(text) and end - pos - 1 < limit and text[end] in HEX_DIGITS:
            end += 1
        digits = text[pos + 1 : end]
        if not digits:
            return "\\" + ch, pos + 1
        try:
            return chr(int(digits, 16)), end
        except ValueError:  # beyond the Unicode range
            return "\\" + ch + digits, end
    if ch == "c" and pos + 1 < len(text):  # \cx, a control character
        return chr(ord(text[pos + 1]) & 0x1F), pos + 2
    return "\\" + ch, pos + 1


class _Parser:
    """Lenient shell parser: flattens a script into its simple commands.

    It never raises on malformed input (an unterminated quote ends at the end of the
    text). A command substitution inside a word is parsed as commands of its own and
    stands for ``PLACEHOLDER`` in the word. Single-quoted text is never parsed.
    """

    def __init__(self, text: str, depth: int) -> None:
        self.text = text
        self.pos = 0
        self.depth = depth
        self.commands: list[Command] = []
        # (delimiter, delimiter was quoted, strip leading tabs, owning command)
        self.pending: list[tuple[str, bool, bool, Command]] = []
        self.last_word_end = -1

    def _end(self, current: Command) -> Command:
        if current.words:
            self.commands.append(current)
        return Command()

    def parse_list(self, in_substitution: bool) -> None:
        """Parse commands up to the end of the text, or to the ``)`` closing ``$(``."""
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise TooComplex
        text = self.text
        size = len(text)
        current = Command()
        groups = 0
        while self.pos < size:
            ch = text[self.pos]
            if ch in " \t\r":
                self.pos += 1
            elif ch == "\\" and text.startswith("\n", self.pos + 1):
                self.pos += 2
            elif ch == "\n":
                self.pos += 1
                current = self._end(current)
                self._read_heredoc_bodies()
            elif ch == "#":
                newline = text.find("\n", self.pos)
                self.pos = size if newline < 0 else newline
            elif ch in ";|":
                self.pos += 1
                current = self._end(current)
            elif ch == "&":
                if text.startswith("&>", self.pos):
                    self._redirect(current)
                else:
                    self.pos += 1
                    current = self._end(current)
            elif ch == "(":
                self.pos += 1
                current = self._end(current)
                groups += 1
            elif ch == ")":
                self.pos += 1
                current = self._end(current)
                if groups:
                    groups -= 1
                elif in_substitution:
                    self.depth -= 1
                    return
            elif ch in "<>":
                self._redirect(current)
            else:
                word, _ = self._read_word()
                current.words.append(word)
        self._end(current)
        self.depth -= 1

    def _redirect(self, current: Command) -> None:
        text = self.text
        start = self.pos
        # A file descriptor written right before the operator (2>&1) is not a word.
        if (
            current.words
            and self.last_word_end == start
            and current.words[-1].isdigit()
        ):
            current.words.pop()
        kind = "file"
        strip_tabs = False
        if text.startswith("<<<", start):
            self.pos += 3
            kind = "here-string"
        elif text.startswith("<<", start):
            self.pos += 2
            kind = "heredoc"
            strip_tabs = text.startswith("-", self.pos)
            if strip_tabs:
                self.pos += 1
        elif text[start] in "<>" and text.startswith("(", start + 1):
            self.pos += 2  # process substitution: <(...) or >(...)
            self.parse_list(True)
            return
        elif text.startswith("&>>", start):
            self.pos += 3
        elif text.startswith("&>", start):
            self.pos += 2
        else:
            self.pos += 1
            if self.pos < len(text) and text[self.pos] in "<>&|":
                self.pos += 1
        while self.pos < len(text) and text[self.pos] in " \t":
            self.pos += 1
        if self.pos >= len(text) or text[self.pos] in ";|&()\n":
            return
        target, quoted = self._read_word()
        if kind == "heredoc":
            self.pending.append((target, quoted, strip_tabs, current))
        elif kind == "here-string":
            current.stdin.append(target)

    def _read_word(self) -> tuple[str, bool]:
        """Read one word; returns its value and whether any part of it was quoted."""
        text = self.text
        size = len(text)
        parts: list[str] = []
        quoted = False
        while self.pos < size:
            ch = text[self.pos]
            if ch in " \t\r\n;|&()<>":
                break
            if ch == "\\":
                following = text[self.pos + 1 : self.pos + 2]
                if following == "\n":
                    self.pos += 2
                elif following:
                    parts.append(following)
                    self.pos += 2
                    quoted = True
                else:
                    self.pos += 1
            elif ch == "'":
                end = text.find("'", self.pos + 1)
                if end < 0:
                    end = size
                parts.append(text[self.pos + 1 : end])
                self.pos = end + 1
                quoted = True
            elif ch == '"':
                self.pos += 1
                parts.append(self._read_double_quoted(True))
                quoted = True
            elif ch == "$" and text.startswith("(", self.pos + 1):
                self.pos += 2
                self.parse_list(True)
                parts.append(PLACEHOLDER)
            elif ch == "$" and text.startswith("'", self.pos + 1):
                self.pos += 2
                parts.append(self._read_ansi_c())
                quoted = True
            elif ch == "$" and text.startswith('"', self.pos + 1):
                self.pos += 2
                parts.append(self._read_double_quoted(True))
                quoted = True
            elif ch == "`":
                self.pos += 1
                self._read_backtick()
                parts.append(PLACEHOLDER)
            else:
                parts.append(ch)
                self.pos += 1
        self.last_word_end = self.pos
        return "".join(parts), quoted

    def _read_double_quoted(self, stop_at_quote: bool) -> str:
        """Content of a double-quoted string (or of a heredoc body when not stopping).

        Only ``$(...)`` and backticks are parsed inside: they run.
        """
        text = self.text
        size = len(text)
        out: list[str] = []
        while self.pos < size:
            ch = text[self.pos]
            if ch == '"' and stop_at_quote:
                self.pos += 1
                return "".join(out)
            if ch == "\\":
                following = text[self.pos + 1 : self.pos + 2]
                if following and following in '$`"\\':
                    out.append(following)
                    self.pos += 2
                elif following == "\n":
                    self.pos += 2
                else:
                    out.append(ch)
                    self.pos += 1
            elif ch == "$" and text.startswith("(", self.pos + 1):
                self.pos += 2
                self.parse_list(True)
                out.append(PLACEHOLDER)
            elif ch == "`":
                self.pos += 1
                self._read_backtick()
                out.append(PLACEHOLDER)
            else:
                out.append(ch)
                self.pos += 1
        return "".join(out)

    def _read_ansi_c(self) -> str:
        """Content of ``$'...'`` with its escapes decoded (``\\x67``, ``\\147``, ``\\u0067``)."""
        text = self.text
        size = len(text)
        out: list[str] = []
        while self.pos < size:
            ch = text[self.pos]
            if ch == "'":
                self.pos += 1
                break
            if ch == "\\" and self.pos + 1 < size:
                decoded, self.pos = _decode_escape(text, self.pos + 1)
                out.append(decoded)
            else:
                out.append(ch)
                self.pos += 1
        # Like bash, the value stops at the first NUL (also keeps PLACEHOLDER unique).
        return "".join(out).split("\x00", 1)[0]

    def _read_backtick(self) -> None:
        """Parse a backtick command substitution (the opening one is consumed)."""
        text = self.text
        size = len(text)
        inner: list[str] = []
        while self.pos < size:
            ch = text[self.pos]
            if ch == "`":
                break
            if ch == "\\" and self.pos + 1 < size and text[self.pos + 1] in "`\\$":
                inner.append(text[self.pos + 1])
                self.pos += 2
            else:
                inner.append(ch)
                self.pos += 1
        self.pos += 1
        sub = _Parser("".join(inner), self.depth)
        sub.parse_list(False)
        self.commands.extend(sub.commands)

    def _read_heredoc_bodies(self) -> None:
        """Consume the bodies of the heredocs announced on the line that just ended."""
        text = self.text
        size = len(text)
        pending, self.pending = self.pending, []
        for delimiter, quoted, strip_tabs, owner in pending:
            lines: list[str] = []
            while self.pos < size:
                newline = text.find("\n", self.pos)
                end = size if newline < 0 else newline
                line = text[self.pos : end]
                self.pos = size if newline < 0 else newline + 1
                candidate = line.lstrip("\t") if strip_tabs else line
                if candidate == delimiter:
                    break
                lines.append(line)
            body = "\n".join(lines)
            owner.stdin.append(body)
            if not quoted:  # an unquoted heredoc expands $(...) and backticks
                sub = _Parser(body, self.depth)
                sub._read_double_quoted(False)
                self.commands.extend(sub.commands)


def parse_script(script: str, depth: int = 0) -> list[Command]:
    """Simple commands of a shell script (nested substitutions included)."""
    parser = _Parser(script, depth)
    parser.parse_list(False)
    return parser.commands


# --- Rules --------------------------------------------------------------------------


def _is_abbreviation(name: str, full: str, min_length: int) -> bool:
    """True if ``name`` is ``full`` or an accepted abbreviation of that long option."""
    return len(name) >= min_length and name.startswith("--") and full.startswith(name)


def _forbidden_config_key(key: str) -> Violation | None:
    """The violation for a Git configuration key an agent must not set, else None.

    Single source of truth for ``git -c``, ``--config-env``, ``GIT_CONFIG_*`` and the
    writes of ``git config``. Forbidden: ``core.hooksPath`` (disables the Git hooks),
    ``alias.*`` (hides a command from the textual analysis), ``include.path`` and
    ``includeIf.*`` (load another file with such keys), ``remote.*.push`` and
    ``remote.*.mirror`` (redirect or widen a push), ``push.default`` (changes what a
    bare ``git push`` sends). Keys that make Git start a program (``core.editor``,
    ``core.sshCommand``, ``core.pager``, ``core.fsmonitor``...) are NOT covered: the
    program is unknown to this guard (see the documentation, "Limites connues").
    """
    lowered = key.strip().lower()
    if lowered == "core.hookspath":
        return HOOKS_PATH
    if (
        lowered in ("include.path", "push.default")
        or lowered.startswith(("alias.", "includeif."))
        or (lowered.startswith("remote.") and lowered.endswith((".push", ".mirror")))
    ):
        return GIT_CONFIG
    return None


def _check_assignment(word: str) -> Violation | None:
    """``GIT_CONFIG_*=...`` naming a forbidden key acts like ``git -c`` does.

    Assigning one of the ``TOKEN_VARIABLES`` is refused too, whatever the value.
    """
    name, _, value = word.partition("=")
    if name in TOKEN_VARIABLES:
        return GH_TOKEN_ENV
    if not name.startswith("GIT_CONFIG"):
        return None
    # ``GIT_CONFIG_KEY_n`` holds a key, ``GIT_CONFIG_PARAMETERS`` quoted ``'key'='value'``.
    for token in re.findall(r"[A-Za-z0-9_.*-]+", value):
        violation = _forbidden_config_key(token)
        if violation is not None:
            return violation
    return None


def _check_config_pair(pair: str) -> Violation | None:
    """A ``name=value`` given to ``git -c`` or ``--config-env``."""
    return _forbidden_config_key(pair.split("=", 1)[0])


# ``git commit`` options that take a value (the next word when not attached).
COMMIT_VALUE_SHORT = frozenset("mFCct")
# ``-S`` and ``-u`` only take an attached value: the rest of the cluster is that value.
COMMIT_OPTIONAL_VALUE_SHORT = frozenset("Su")
COMMIT_VALUE_LONG = frozenset(
    {
        "--message",
        "--file",
        "--reuse-message",
        "--reedit-message",
        "--fixup",
        "--squash",
        "--template",
        "--author",
        "--date",
        "--cleanup",
        "--pathspec-from-file",
        "--trailer",
    }
)


def _check_commit(args: list[str]) -> Violation | None:
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            break
        if arg.startswith("--"):
            name = arg.split("=", 1)[0]
            if _is_abbreviation(name, "--no-verify", 6):
                return NO_VERIFY
            if "=" not in arg and name in COMMIT_VALUE_LONG:
                index += 1  # the value is the next word
        elif arg.startswith("-") and len(arg) > 1:
            for position, flag in enumerate(arg[1:], start=1):
                if flag == "n":
                    return NO_VERIFY
                if flag in COMMIT_VALUE_SHORT:
                    if position == len(arg) - 1:
                        index += 1  # the value is the next word
                    break
                if flag in COMMIT_OPTIONAL_VALUE_SHORT:
                    break
        index += 1
    return None


# Short options of merge / rebase that take a value (their value is not an option).
MERGE_REBASE_VALUE_SHORT = frozenset({"-m", "-F", "-s", "-X", "-x", "-C"})


def _check_long_no_verify(args: list[str]) -> Violation | None:
    """``--no-verify`` of ``git merge`` / ``git rebase`` (``-n`` means --no-stat there)."""
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            break
        if arg.startswith("--") and _is_abbreviation(
            arg.split("=", 1)[0], "--no-verify", 6
        ):
            return NO_VERIFY
        if arg in MERGE_REBASE_VALUE_SHORT:
            index += 1
        index += 1
    return None


# Short options of ``git rebase`` that take a value (``-x`` is the one we want).
REBASE_VALUE_SHORT = frozenset("sXx")


def _rebase_exec_scripts(args: list[str]) -> list[str]:
    """The commands given to ``git rebase -x`` / ``--exec`` (they are run by a shell)."""
    scripts: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            break
        if arg.startswith("--"):
            name, equals, value = arg.partition("=")
            if _is_abbreviation(name, "--exec", 4):
                if equals:
                    scripts.append(value)
                elif index + 1 < len(args):
                    scripts.append(args[index + 1])
                    index += 1
            elif not equals and name in ("--strategy", "--strategy-option", "--onto"):
                index += 1
        elif arg.startswith("-") and len(arg) > 1:
            for position, flag in enumerate(arg[1:], start=1):
                if flag in REBASE_VALUE_SHORT:
                    attached = arg[position + 1 :]
                    if not attached:  # the value is the next word
                        index += 1
                    if flag == "x":
                        if attached:
                            scripts.append(attached)
                        elif index < len(args):
                            scripts.append(args[index])
                    break
        index += 1
    return scripts


CONFIG_WRITE_FLAGS = frozenset(
    {
        "--unset",
        "--unset-all",
        "--add",
        "--replace-all",
        "--rename-section",
        "--remove-section",
        "--edit",
        "-e",
    }
)
CONFIG_SECTION_FLAGS = frozenset({"--rename-section", "--remove-section"})
CONFIG_READ_FLAGS = frozenset(
    {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--get-colorbool"}
    | {"--list", "-l"}
)
# ``git config <subcommand>`` forms (Git 2.46+): the first positional word.
CONFIG_WRITE_SUBCOMMANDS = frozenset(
    {"set", "unset", "edit", "rename-section", "remove-section"}
)
CONFIG_SECTION_SUBCOMMANDS = frozenset({"rename-section", "remove-section"})
CONFIG_READ_SUBCOMMANDS = frozenset({"get", "list"})
# Options of ``git config`` that take a value (the next word).
CONFIG_VALUE_OPTIONS = frozenset(
    {"-f", "--file", "--blob", "--type", "--default", "--comment"}
)


def _check_config(args: list[str]) -> Violation | None:
    """``git config`` writing a forbidden key (reading any key is allowed)."""
    positionals: list[str] = []
    flags: set[str] = set()
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            positionals.extend(args[index + 1 :])
            break
        if arg.lower() in CONFIG_VALUE_OPTIONS:
            flags.add(arg.lower())
            index += 1  # skip the value too
        elif arg.startswith("-") and len(arg) > 1:
            flags.add(arg.lower())
        else:
            positionals.append(arg)
        index += 1
    subcommand = positionals[0].lower() if positionals else ""
    if flags & CONFIG_WRITE_FLAGS or subcommand in CONFIG_WRITE_SUBCOMMANDS:
        written = True
    elif flags & CONFIG_READ_FLAGS or subcommand in CONFIG_READ_SUBCOMMANDS:
        return None
    else:
        written = len(positionals) >= 2  # ``git config <key> <value>``
    if not written:
        return None  # ``git config [--get] core.hooksPath`` only reads the value
    if subcommand in CONFIG_WRITE_SUBCOMMANDS | CONFIG_READ_SUBCOMMANDS:
        positionals = positionals[1:]
    if flags & CONFIG_SECTION_FLAGS or subcommand in CONFIG_SECTION_SUBCOMMANDS:
        # the words are section names
        keys = [name + "." for name in positionals]
    else:
        keys = positionals[:1]  # the key; later words are values or patterns
    for key in keys:
        violation = _forbidden_config_key(key)
        if violation is not None:
            return violation
    return None


# Options of ``git push`` that take a value (the next word unless written ``--x=v``).
PUSH_VALUE_LONG = frozenset(
    {"--repo", "--receive-pack", "--exec", "--push-option", "--recurse-submodules"}
)
# Global options of ``git`` that take a value as the next word.
GIT_GLOBAL_VALUE_OPTIONS = frozenset(
    {"--git-dir", "--work-tree", "--namespace", "--super-prefix", "--attr-source"}
)
CHECKOUT_NEW_BRANCH_OPTIONS = frozenset(
    {"-b", "-B", "-c", "-C", "--create", "--force-create", "--orphan"}
)


BranchLookup = Callable[[tuple[str, ...]], "str | None"]
PushLookup = Callable[[tuple[str, ...], str], "str | None"]
# The remote-tracking ref of main / master, as ``%(push)`` prints it.
PROTECTED_PUSH_REF = re.compile(
    r"^refs/remotes/(?:[^/]+/)+(?:" + "|".join(sorted(PROTECTED_BRANCHES)) + ")$"
)
# Marks a branch the command line switched to by a computed name.
UNKNOWN_BRANCH = "\x00unknown"


def _is_unknown_value(word: str) -> bool:
    """A word whose value the guard cannot know (substitution, shell variable)."""
    return PLACEHOLDER in word or word.startswith("$")


class Analyzer:
    """Applies the rules to a command line; ``check`` returns the first violation."""

    def __init__(
        self,
        branch_lookup: BranchLookup | None = None,
        push_lookup: PushLookup | None = None,
    ) -> None:
        self._branch_lookup = branch_lookup
        self._push_lookup = push_lookup
        self._branches: dict[tuple[str, ...], str | None] = {}
        self._push_targets: dict[tuple[tuple[str, ...], str], str | None] = {}
        # Set when the command line itself switches branch before a push
        # (``UNKNOWN_BRANCH`` when the branch it switches to is computed).
        self._assumed_branch: str | None = None
        self.notes: list[str] = []

    # -- entry points --

    def check(self, script: str, depth: int = 0) -> Violation | None:
        try:
            commands = parse_script(script, depth)
        except TooComplex:
            return TOO_COMPLEX
        for command in commands:
            violation = self._check_command(command, depth)
            if violation is not None:
                return violation
        return None

    def _check_command(self, command: Command, depth: int) -> Violation | None:
        words = list(command.words)
        for _ in range(2 * MAX_DEPTH):
            while words:
                if words[0] in SHELL_KEYWORDS:
                    words.pop(0)
                elif ASSIGNMENT.match(words[0]):
                    violation = _check_assignment(words.pop(0))
                    if violation is not None:
                        return violation
                else:
                    break
            if not words:
                return None
            name = os.path.basename(words[0])
            args = words[1:]
            if name == "git":
                return self._check_git(args, depth)
            if name == "gh":
                return self._check_gh(args)
            if name in SHELLS:
                return self._check_shell(args, command, depth)
            if name == "eval":
                return self.check(" ".join(args), depth + 1)
            if name == "function":  # ``function NAME { ...; }``: drop both words
                words = args[1:]
                continue
            if name in ("export", "declare", "typeset", "readonly", "local"):
                for arg in args:
                    violation = _check_assignment(arg)
                    if violation is not None:
                        return violation
                if any(arg in ("-n", "+x") for arg in args) and any(
                    arg in TOKEN_VARIABLES for arg in args
                ):  # ``export -n GH_TOKEN``: drops the variable from the environment
                    return GH_TOKEN_ENV
                return None
            if name == "unset":
                if any(arg in TOKEN_VARIABLES for arg in args):
                    return GH_TOKEN_ENV
                return None
            if name in WRAPPERS:
                unwrapped = self._unwrap(name, args, depth)
                if unwrapped is None or isinstance(unwrapped, Violation):
                    return unwrapped
                words = unwrapped
                continue
            return None
        return TOO_COMPLEX

    # -- wrappers and shells --

    def _unwrap(
        self, name: str, args: list[str], depth: int
    ) -> list[str] | Violation | None:
        """The command wrapped by ``name`` (None: nothing to analyze)."""
        if name == "mise":
            if args and args[0] in ("exec", "x") and "--" in args:
                return args[args.index("--") + 1 :]
            return None
        if name == "coproc":  # ``coproc [NAME] command``; NAME only before ``{``
            return args[2:] if len(args) >= 2 and args[1] == "{" else args
        if name == "command":
            for arg in args:
                if not arg.startswith("-"):
                    break
                if "v" in arg[1:] or "V" in arg[1:]:  # only describes the command
                    return None
        if name == "env":
            if _env_unsets_token(args):
                return GH_TOKEN_ENV
            for index, arg in enumerate(args):
                if arg in ("-S", "--split-string"):
                    return self.check(" ".join(args[index + 1 :]), depth + 1)
                if arg.startswith("--split-string="):
                    script = " ".join([arg.split("=", 1)[1], *args[index + 1 :]])
                    return self.check(script, depth + 1)
                if not arg.startswith("-") and not ASSIGNMENT.match(arg):
                    break
        rest, assignments = _skip_options(
            args,
            WRAPPER_VALUE_OPTIONS.get(name, frozenset()),
            WRAPPER_POSITIONALS.get(name, 0),
            skip_assignments=(name == "env"),
        )
        for assignment in assignments:
            violation = _check_assignment(assignment)
            if violation is not None:
                return violation
        return rest

    def _check_shell(
        self, args: list[str], command: Command, depth: int
    ) -> Violation | None:
        """``bash -c '...'``, or a shell reading a script from stdin (heredoc...)."""
        script: str | None = None
        script_file = False
        index = 0
        while index < len(args):
            arg = args[index]
            if arg == "--":
                script_file = index + 1 < len(args)
                break
            if arg.startswith("--"):
                index += 2 if arg in ("--rcfile", "--init-file") else 1
            elif len(arg) > 1 and arg[0] in "-+":
                if arg[0] == "-" and "c" in arg[1:]:
                    for following in args[index + 1 :]:
                        if not following.startswith(("-", "+")):
                            script = following
                            break
                    break
                index += 2 if arg[1:].endswith("o") else 1
            else:
                script_file = True
                break
        if script is not None:
            return self.check(script, depth + 1)
        if not script_file:
            for text in command.stdin:
                violation = self.check(text, depth + 1)
                if violation is not None:
                    return violation
        return None

    # -- git --

    def _check_git(self, args: list[str], depth: int = 0) -> Violation | None:
        git_dirs: list[str] = []
        index = 0
        while index < len(args) and args[index].startswith("-"):
            arg = args[index]
            following = args[index + 1] if index + 1 < len(args) else ""
            if arg == "-c" or arg == "--config-env":
                violation = _check_config_pair(following)
                if violation is not None:
                    return violation
                index += 2
            elif arg.startswith("--config-env="):
                violation = _check_config_pair(arg.split("=", 1)[1])
                if violation is not None:
                    return violation
                index += 1
            elif arg == "-C":
                git_dirs.append(following)
                index += 2
            elif arg in GIT_GLOBAL_VALUE_OPTIONS:
                index += 2
            else:
                index += 1
        if index >= len(args):
            return None
        subcommand, rest = args[index], args[index + 1 :]
        if subcommand == "commit":
            return _check_commit(rest)
        if subcommand == "push":
            return self._check_push(rest, tuple(git_dirs))
        if subcommand == "merge":
            return _check_long_no_verify(rest)
        if subcommand == "rebase":
            violation = _check_long_no_verify(rest)
            if violation is not None:
                return violation
            for script in _rebase_exec_scripts(rest):  # run by a shell
                violation = self.check(script, depth + 1)
                if violation is not None:
                    return violation
            return None
        if subcommand == "config":
            return _check_config(rest)
        if subcommand in ("switch", "checkout"):
            self._track_branch_switch(subcommand, rest)
        return None

    def _track_branch_switch(self, subcommand: str, args: list[str]) -> None:
        """Remember a branch switch made earlier on the same command line."""
        created: str | None = None
        target: str | None = None
        index = 0
        while index < len(args):
            arg = args[index]
            if arg == "--":
                break
            if arg in CHECKOUT_NEW_BRANCH_OPTIONS and index + 1 < len(args):
                created = args[index + 1]
                index += 1
            elif not arg.startswith("-") and target is None:
                target = arg
            index += 1
        switched = created or target
        if switched is not None and _is_unknown_value(switched):
            self._assumed_branch = UNKNOWN_BRANCH  # computed: nobody knows where we are
        elif created is not None:
            self._assumed_branch = created
        elif subcommand == "switch" and target not in (None, "-"):
            self._assumed_branch = target
        elif subcommand == "checkout" and target in PROTECTED_BRANCHES:
            self._assumed_branch = target

    def _current_branch(self, git_dirs: tuple[str, ...]) -> str | None:
        """The branch pushes start from; "" if detached, None if unknown."""
        if self._assumed_branch == UNKNOWN_BRANCH:
            return None
        if self._assumed_branch is not None:
            return self._assumed_branch
        if self._branch_lookup is None:
            return None
        if git_dirs not in self._branches:
            self._branches[git_dirs] = self._branch_lookup(git_dirs)
        branch = self._branches[git_dirs]
        if branch is None:
            self.notes.append("current branch unknown (push without target refused)")
        return branch

    def _push_target_is_protected(
        self, git_dirs: tuple[str, ...], branch: str
    ) -> bool | None:
        """Does a bare ``git push`` from ``branch`` land on main/master? None: unknown.

        The lookup returns the remote-tracking ref(s) the push updates
        (``refs/remotes/origin/main``): what ``%(push)`` prints.
        """
        if self._push_lookup is None:
            return False
        key = (git_dirs, branch)
        if key not in self._push_targets:
            self._push_targets[key] = self._push_lookup(git_dirs, branch)
        refs = self._push_targets[key]
        if refs is None:
            self.notes.append("push target unknown (push without target refused)")
            return None
        return any(PROTECTED_PUSH_REF.match(line.strip()) for line in refs.splitlines())

    def _guard_current_branch(
        self, git_dirs: tuple[str, ...], bare_push: bool = False
    ) -> Violation | None:
        """Refuse a push that starts from main/master, or whose branch is unknown.

        ``bare_push``: no refspec at all, so Git also uses the configured push target
        (``push.default``, upstream), which is read too.
        """
        branch = self._current_branch(git_dirs)
        if branch is None:
            return PUSH_UNKNOWN
        if branch in PROTECTED_BRANCHES:
            return PUSH_MAIN
        if bare_push and branch:
            protected = self._push_target_is_protected(git_dirs, branch)
            if protected is None:
                return PUSH_UNKNOWN
            if protected:
                return PUSH_MAIN
        return None

    def _check_push(
        self, args: list[str], git_dirs: tuple[str, ...]
    ) -> Violation | None:
        positionals: list[str] = []
        repo_option = False
        tags = False
        index = 0
        while index < len(args):
            arg = args[index]
            if arg == "--":
                positionals.extend(args[index + 1 :])
                break
            if arg.startswith("--"):
                name = arg.split("=", 1)[0]
                if name.startswith("--force") or _is_abbreviation(name, "--force", 5):
                    return PUSH_FORCE
                if _is_abbreviation(name, "--no-verify", 6):
                    return NO_VERIFY
                if _is_abbreviation(name, "--mirror", 4):
                    return PUSH_MIRROR
                if _is_abbreviation(name, "--delete", 4) or _is_abbreviation(
                    name, "--prune", 5
                ):
                    return PUSH_DELETE
                # ``--branches`` is a synonym of ``--all`` (Git 2.41).
                if _is_abbreviation(name, "--all", 4) or _is_abbreviation(
                    name, "--branches", 3
                ):
                    return PUSH_ALL
                tags = tags or name == "--tags"
                repo_option = repo_option or name == "--repo"
                if "=" not in arg and name in PUSH_VALUE_LONG:
                    index += 1
            elif arg.startswith("-") and len(arg) > 1:
                for position, flag in enumerate(arg[1:], start=1):
                    if flag == "f":
                        return PUSH_FORCE
                    if flag == "d":
                        return PUSH_DELETE
                    if flag == "o":
                        if position == len(arg) - 1:
                            index += 1  # the push option is the next word
                        break
            else:
                positionals.append(arg)
            index += 1
        refspecs = positionals if repo_option else positionals[1:]
        if not refspecs:
            if tags:  # ``git push --tags`` pushes tags only
                return None
            return self._guard_current_branch(git_dirs, bare_push=True)
        for refspec in refspecs:
            violation = self._check_refspec(refspec, git_dirs)
            if violation is not None:
                return violation
        return None

    def _check_refspec(
        self, refspec: str, git_dirs: tuple[str, ...]
    ) -> Violation | None:
        if refspec.startswith("+"):
            return PUSH_FORCE
        source, colon, destination = refspec.partition(":")
        if colon and not source:
            return PUSH_DELETE
        target = destination if colon else source
        if not target:
            return None
        if "*" in target:  # a wildcard refspec can reach main
            return PUSH_MAIN
        if target in ("HEAD", "@") or _is_unknown_value(target):
            # A computed target is judged like HEAD: from the current branch.
            return self._guard_current_branch(git_dirs)
        name = target.removeprefix("refs/heads/").removeprefix("heads/")
        if name in PROTECTED_BRANCHES:
            return PUSH_MAIN
        return None

    # -- gh --

    def _check_gh(self, args: list[str]) -> Violation | None:
        positions: list[int] = []  # indexes of the group and of the action
        index = 0
        while index < len(args) and len(positions) < 2:
            arg = args[index]
            if arg in ("-R", "--repo", "--hostname"):
                index += 1  # skip the value too
            elif not arg.startswith("-"):
                positions.append(index)
            index += 1
        words = [args[position] for position in positions]
        group = words[0] if words else ""
        action = words[1] if len(words) > 1 else ""
        if group == "pr" and action == "merge":
            return None if _asks_for_help(args) else PR_MERGE
        if (group, action) in GH_FORBIDDEN or (group == "repo" and action in GH_REPO):
            return GH_ADMIN
        if group == "api":
            return _check_gh_api(args[positions[0] + 1 :])
        if group == "auth":
            # ``-h`` is ``--hostname`` here, not help: only ``--help`` runs nothing.
            if "--help" in args:
                return None
            auth_words = [a for a in args[positions[0] + 1 :] if not a.startswith("-")]
            if any(word in GH_AUTH_FORBIDDEN for word in auth_words):
                return GH_AUTH
            if "status" in auth_words and _shows_token(args[positions[0] + 1 :]):
                return GH_AUTH
        return None


GH_REPO = frozenset(
    {"delete", "edit", "archive", "unarchive", "rename", "deploy-key", "autolink"}
)
GH_FORBIDDEN = frozenset(
    {
        ("secret", "set"),
        ("secret", "delete"),
        ("secret", "remove"),
        ("variable", "set"),
        ("variable", "delete"),
        ("variable", "remove"),
        ("alias", "set"),
        ("alias", "import"),
    }
)
# Options of ``gh`` whose value is the next word (a ``--help`` there is not a help).
GH_VALUE_OPTIONS = frozenset(
    {"-R", "--repo", "--hostname", "-A", "--author-email", "-b", "--body"}
    | {"-F", "--body-file", "--match-head-commit", "-t", "--subject"}
)


def _shows_token(args: list[str]) -> bool:
    """``--show-token`` or ``-t`` (alone or in a cluster such as ``-at``) of ``gh auth status``."""
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--show-token" or arg.startswith("--show-token="):
            return True
        if arg in ("-h", "--hostname", "-q", "--jq", "--json"):
            index += 1  # the next word is a value, whatever it looks like
        elif arg.startswith("-") and not arg.startswith("--") and "t" in arg[1:]:
            return True
        index += 1
    return False


def _env_unsets_token(args: list[str]) -> bool:
    """``env -u NAME`` / ``-uNAME`` / ``--unset NAME`` / ``--unset=NAME`` for a token variable."""
    index = 0
    while index < len(args):
        arg = args[index]
        following = args[index + 1] if index + 1 < len(args) else ""
        if arg == "--":
            return False
        if arg in ("-u", "--unset"):
            if following in TOKEN_VARIABLES:
                return True
            index += 1
        elif arg.startswith("--unset=") or (
            arg.startswith("-u") and not arg.startswith("--")
        ):
            if arg.partition("=")[2] in TOKEN_VARIABLES or arg[2:] in TOKEN_VARIABLES:
                return True
        elif arg in ("-C", "--chdir"):
            index += 1
        elif not arg.startswith("-") and not ASSIGNMENT.match(arg):
            return False  # the wrapped command starts here
        index += 1
    return False


def _asks_for_help(args: list[str]) -> bool:
    """``--help`` / ``-h`` as an option of its own: ``gh`` prints help and runs nothing."""
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ("-h", "--help"):
            return True
        if arg in GH_VALUE_OPTIONS:
            index += 1  # the next word is a value, whatever it looks like
        index += 1
    return False


# ``gh api`` options that take a value.
GH_API_VALUE_SHORT = frozenset("HqtpR")
GH_API_VALUE_LONG = frozenset(
    {"--header", "--jq", "--template", "--cache", "--hostname", "--preview", "--repo"}
)
GH_API_FIELD_LONG = frozenset({"--field", "--raw-field", "--input"})
# GraphQL mutations an agent must not run (merge, refs, commits, protection, repository).
GRAPHQL_FORBIDDEN = (
    "mergepullrequest",
    "enablepullrequestautomerge",
    "enqueuepullrequest",
    "mergebranch",
    "createcommitonbranch",
    "deleteref",
    "updateref",
    "deleterepository",
    "archiverepository",
    "updaterepository",
    "createbranchprotectionrule",
    "updatebranchprotectionrule",
    "deletebranchprotectionrule",
    "createrepositoryruleset",
    "updaterepositoryruleset",
    "deleterepositoryruleset",
)
_REPO = r"repos/[^/]+/[^/]+"
API_MERGE = re.compile(rf"^{_REPO}/pulls/[^/]+/merge$", re.IGNORECASE)
# Merging a branch into another and writing files on a branch bypass the pull request.
API_COMMITS = re.compile(rf"^{_REPO}/(merges|contents(/.*)?)$", re.IGNORECASE)
API_REFS = re.compile(rf"^{_REPO}/git/refs(/.*)?$", re.IGNORECASE)
API_SETTINGS = re.compile(
    rf"^({_REPO}|(repos/[^/]+/[^/]+|orgs/[^/]+)/rulesets(/.*)?"
    rf"|{_REPO}/branches/.+/(protection|rename)(/.*)?"
    rf"|{_REPO}/(actions/(secrets|variables|permissions)|environments)(/.*)?)$",
    re.IGNORECASE,
)


def _api_endpoint(raw: str) -> str:
    """``repos/o/r/...`` from ``/repos/o/r/...``, a full URL or a query string."""
    endpoint = re.sub(r"^https?://[^/]+/", "", raw.strip())
    return endpoint.split("?", 1)[0].strip("/")


def _check_gh_api(args: list[str]) -> Violation | None:
    method: str | None = None
    has_body = False
    has_input = False
    endpoint: str | None = None
    values: list[str] = []
    typed_fields: list[str] = []  # -F / --field: a value starting with @ reads a file
    index = 0
    while index < len(args):
        arg = args[index]
        following = args[index + 1] if index + 1 < len(args) else ""
        if arg.startswith("--"):
            name, equals, value = arg.partition("=")
            takes_value = name in GH_API_VALUE_LONG or name in GH_API_FIELD_LONG
            if name == "--method":
                method = value if equals else following
                takes_value = True
            has_body = has_body or name in GH_API_FIELD_LONG
            has_input = has_input or name == "--input"
            if takes_value:
                values.append(value if equals else following)
                if name == "--field":
                    typed_fields.append(values[-1])
                if not equals:
                    index += 1
        elif arg.startswith("-") and len(arg) > 1:
            flag, attached = arg[1], arg[2:].removeprefix("=")
            if flag == "X":
                method = attached or following
            if flag in "XfF" or flag in GH_API_VALUE_SHORT:
                has_body = has_body or flag in "fF"
                values.append(attached or following)
                if flag == "F":
                    typed_fields.append(values[-1])
                if not attached:
                    index += 1
        elif endpoint is None:
            endpoint = _api_endpoint(arg)
        index += 1
    if endpoint is None:
        return None
    verb = (method or ("POST" if has_body else "GET")).upper()
    if endpoint.lower() == "graphql":
        # A query read from a file or computed cannot be judged: ask for it inline.
        if (
            has_input
            or any(PLACEHOLDER in value for value in values)
            or any(value.partition("=")[2].startswith("@") for value in typed_fields)
        ):
            return GH_API_OPAQUE
        text = " ".join(values).lower()
        if any(name in text for name in GRAPHQL_FORBIDDEN):
            return GH_API
        return None
    if verb in ("GET", "HEAD"):
        return None
    if PLACEHOLDER in endpoint or endpoint.startswith("$"):
        return GH_API_OPAQUE  # a write to an endpoint nobody can read
    if API_MERGE.match(endpoint) or API_COMMITS.match(endpoint):
        return GH_API
    if verb in ("DELETE", "PUT", "PATCH") and API_REFS.match(endpoint):
        return GH_API
    if API_SETTINGS.match(endpoint):
        return GH_API
    return None


# --- Wrappers (commands that run another command) ---------------------------------

WRAPPER_VALUE_OPTIONS: dict[str, frozenset[str]] = {
    "env": frozenset({"-u", "--unset", "-C", "--chdir"}),
    "sudo": frozenset(
        {"-u", "--user", "-g", "--group", "-h", "--host", "-p", "--prompt"}
        | {"-C", "-D", "--chdir", "-r", "--role", "-t", "--type", "-T", "-U"}
    ),
    "doas": frozenset({"-u", "-C"}),
    "time": frozenset({"-f", "--format", "-o", "--output"}),
    "nice": frozenset({"-n", "--adjustment"}),
    "ionice": frozenset({"-c", "-n", "-p", "-P", "-u"}),
    "timeout": frozenset({"-s", "--signal", "-k", "--kill-after"}),
    "stdbuf": frozenset({"-i", "-o", "-e", "--input", "--output", "--error"}),
    "exec": frozenset({"-a"}),
    "xargs": frozenset(
        {"-I", "-n", "-P", "-L", "-s", "-d", "-E", "-a", "--max-args", "--max-procs"}
        | {"--max-lines", "--max-chars", "--delimiter", "--arg-file", "--eof"}
    ),
}
# Positional words between the options and the wrapped command (``timeout 10 cmd``).
WRAPPER_POSITIONALS = {"timeout": 1}
WRAPPERS = frozenset(
    {
        "env",
        "sudo",
        "doas",
        "time",
        "command",
        "builtin",
        "exec",
        "nohup",
        "nice",
        "ionice",
        "timeout",
        "setsid",
        "stdbuf",
        "xargs",
        "chronic",
        "coproc",
        "mise",
    }
)


def _skip_options(
    args: list[str],
    value_options: frozenset[str],
    positional_count: int = 0,
    skip_assignments: bool = False,
) -> tuple[list[str], list[str]]:
    """Drop the leading options of a wrapper; returns (wrapped command, assignments)."""
    assignments: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            index += 1
            break
        if skip_assignments and ASSIGNMENT.match(arg):
            assignments.append(arg)
            index += 1
        elif arg.startswith("--"):
            takes_value = "=" not in arg and arg in value_options
            index += 2 if takes_value else 1
        elif arg.startswith("-") and len(arg) > 1:
            index += 2 if arg in value_options else 1
        else:
            break
    index += positional_count
    return args[index:], assignments


# --- Execution ------------------------------------------------------------------------


def extract_command(payload: object) -> str | None:
    """``tool_input.command`` of a hook payload, or None if absent or not a string."""
    if not isinstance(payload, dict):
        return None
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    command = tool_input.get("command")
    return command if isinstance(command, str) else None


def project_root(env: Mapping[str, str]) -> pathlib.Path:
    """``$CLAUDE_PROJECT_DIR`` (resolved), else the repository holding this script."""
    configured = env.get("CLAUDE_PROJECT_DIR")
    if configured:
        return pathlib.Path(configured).resolve()
    return HOOKS_DIR.parent.parent


def log_line(root: pathlib.Path, message: str) -> None:
    """Append one dated line to the log; a failure to log is silently ignored.

    The log is bounded: beyond ``LOG_MAX_BYTES`` it is moved to ``guard.log.1``.
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


def shorten(command: str) -> str:
    """The command on one line, cut to ``MAX_LOGGED_COMMAND`` characters."""
    single_line = " ".join(command.split())
    if len(single_line) > MAX_LOGGED_COMMAND:
        return single_line[:MAX_LOGGED_COMMAND] + "..."
    return single_line


class GitReader:
    """The few read-only ``git`` calls of the guard, under one time budget.

    Every call is limited to ``GIT_TIMEOUT_SECONDS`` and all of them together to
    ``budget`` seconds (``GIT_BUDGET_SECONDS``): once it is spent nothing is run and the
    answer is None (unknown), which refuses a push without explicit target.
    """

    def __init__(
        self,
        base: pathlib.Path,
        budget: float = GIT_BUDGET_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._base = base
        self._clock = clock
        self._deadline = clock() + budget

    def _read(self, git_dirs: tuple[str, ...], *args: str) -> str | None:
        remaining = self._deadline - self._clock()
        if remaining <= 0:
            return None
        directory = self._base
        for part in git_dirs:
            directory = directory / part  # an absolute part replaces the base
        try:
            proc = subprocess.run(
                ["git", "-C", str(directory), *args],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=min(GIT_TIMEOUT_SECONDS, remaining),
                check=False,
            )
        except Exception:
            return None
        if proc.returncode != 0:
            return None
        return proc.stdout.strip()

    def branch(self, git_dirs: tuple[str, ...]) -> str | None:
        """Current branch; "" if HEAD is detached; None if it cannot be read."""
        return self._read(git_dirs, "branch", "--show-current")

    def push_tracking_ref(self, git_dirs: tuple[str, ...], branch: str) -> str | None:
        """Remote-tracking ref(s) a bare ``git push`` of ``branch`` updates.

        ``%(push)`` follows ``push.default``, the upstream and ``remote.pushDefault``; it
        is empty when Git would refuse or has no target. (``%(push:remoteref)`` prints
        nothing in every case tried with Git 2.53.0, so it is not used.)
        """
        return self._read(
            git_dirs, "for-each-ref", "--format=%(push)", f"refs/heads/{branch}"
        )


def make_branch_lookup(base: pathlib.Path) -> BranchLookup:
    """Reads ``git branch --show-current`` in ``base`` (plus the ``git -C`` folders)."""
    return GitReader(base).branch


def refusal_message(violation: Violation, command: str) -> str:
    return (
        f"Commande bloquée par le garde-fou Bash (règle {violation.rule}).\n"
        f"{violation.reason}\n"
        "Détails et limites : docs/technique/garde-fous-bash.md.\n"
        f"Commande analysée : {shorten(command)}\n"
    )


def failure_refusal_message(what: str) -> str:
    return (
        "Commande bloquée par le garde-fou Bash (règle garde-fou-en-erreur).\n"
        "garde-fou en erreur, commande git/gh refusée par prudence, prévenez "
        "l'utilisateur.\n"
        f"Cause : {shorten(what)}\n"
        "Détails : docs/technique/garde-fous-bash.md ; journal : "
        ".cache/hooks/guard.log (lignes « hook error »).\n"
    )


def handle_failure(root: pathlib.Path, raw_text: str, what: str, stderr=None) -> int:
    """The guard itself failed (decision U2): fail closed for git/gh, open otherwise.

    ``raw_text`` is the unparsed input: if it contains ``git`` or ``gh`` as a word the
    command is refused (exit 2); otherwise it is allowed (exit 0). Both are logged on a
    ``hook error`` line, which the SessionStart hook counts. Never raises.
    """
    try:
        refuse = GIT_OR_GH.search(raw_text) is not None
    except Exception:
        refuse = True
    verdict = "refused (git/gh)" if refuse else "allowed"
    log_line(root, f"hook error: {what}, command {verdict}")
    if not refuse:
        return 0
    try:
        (stderr or sys.stderr).write(failure_refusal_message(what))
    except Exception:
        pass
    return 2


def run(
    stdin_text: str,
    env: Mapping[str, str],
    branch_lookup: BranchLookup | None = None,
    stderr=None,
    push_lookup: PushLookup | None = None,
) -> int:
    """Entry point without side effects on the process: returns 0 (allow) or 2 (block).

    A failure of the guard itself (invalid JSON, no command, exception) is judged by
    ``handle_failure``. ``branch_lookup`` and ``push_lookup`` replace the ``git`` reads
    (tests); when ``branch_lookup`` is given and ``push_lookup`` is not, the target a
    bare push is configured for is not read.
    """
    root = project_root(env)
    try:
        payload = json.loads(stdin_text)
    except Exception as exc:
        return handle_failure(
            root, stdin_text, f"invalid JSON on stdin ({exc!r})", stderr
        )
    command: str | None = None
    try:
        command = extract_command(payload)
        if command is None:
            return handle_failure(
                root, stdin_text, "no tool_input.command in the payload", stderr
            )
        if branch_lookup is None:
            cwd = payload.get("cwd") if isinstance(payload, dict) else None
            base = pathlib.Path(cwd) if isinstance(cwd, str) and cwd else root
            reader = GitReader(base if base.is_dir() else root)
            branch_lookup, push_lookup = reader.branch, reader.push_tracking_ref
        analyzer = Analyzer(branch_lookup, push_lookup)
        violation = analyzer.check(command)
        for note in analyzer.notes:
            log_line(root, f"{note}: {shorten(command)}")
        if violation is None:
            return 0
        log_line(root, f"BLOCKED rule={violation.rule} command={shorten(command)}")
    except Exception as exc:  # a guard that crashes must not stop all the work
        return handle_failure(root, f"{stdin_text}\n{command or ''}", repr(exc), stderr)
    try:
        (stderr or sys.stderr).write(refusal_message(violation, command))
    except Exception:
        pass
    return 2


def main() -> int:
    root = project_root(os.environ)
    try:
        stdin_text = sys.stdin.buffer.read().decode("utf-8", "replace")
    except Exception as exc:
        log_line(root, f"hook error: cannot read stdin ({exc!r}), command allowed")
        return 0
    try:
        return run(stdin_text, os.environ)
    except Exception as exc:
        return handle_failure(root, stdin_text, repr(exc))


if __name__ == "__main__":
    sys.exit(main())
