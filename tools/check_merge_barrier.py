#!/usr/bin/env python3
"""Read-only check of the server-side merge barrier (decision 0021, step E10b).

Run by the user (``just verify-pp merge-barrier``), never by an agent. It only issues
``GET`` requests through ``gh api``: it never merges, approves or writes anything.

Checks (on every active ruleset targeting the default branch whose ``pull_request``
rule requires at least one approving review):
  1. at least one approving review is required;
  2. stale approvals do not survive a push (``dismiss_stale_reviews_on_push`` or
     ``require_last_push_approval``);
  3. the review must come from a code owner (``require_code_owner_review``), and
     ``.github/CODEOWNERS`` exists;
  4. the bypass list is a strict whitelist: only the repository admin role
     (``RepositoryRole`` 5) in ``pull_request`` mode; any other actor, and the
     ``always`` and ``exempt`` modes, fail;
  5. if an agents account is given (``--agents-account`` or ``AGENTS_ACCOUNT``), its
     role on the repository is ``write`` (permission ``push``), not ``admin`` or
     ``maintain``.

Exit code 0: every check passed. 1: at least one check failed. 2: usage error.
3: nothing failed but at least one check could not be made (token lacks the rights,
network error, missing field): the barrier is NOT verified.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import pathlib
import re
import subprocess
import sys
from collections.abc import Callable
from typing import Any

OK, FAIL, SKIP, INFO = "ok", "FAIL", "SKIP", "info"

# Repository role id of "admin" in the ruleset bypass list (see infra/terraform/ruleset.tf).
ADMIN_ROLE_ID = 5
ADMIN_ACTOR_TYPE = "RepositoryRole"
ADMIN_BYPASS_MODE = "pull_request"

CODEOWNERS_PATH = (
    pathlib.Path(__file__).resolve().parent.parent / ".github" / "CODEOWNERS"
)

# Same shape as the Terraform validation of ``agents_account``.
GITHUB_LOGIN = re.compile(r"^[A-Za-z0-9]+(-[A-Za-z0-9]+)*$")
# OWNER/REPO: no ``.`` or ``..`` segment, no ``..`` anywhere (path traversal in the endpoint).
GITHUB_REPO = re.compile(
    r"^(?!.*\.\.)[A-Za-z0-9]+(-[A-Za-z0-9]+)*/(?!\.{1,2}$)[A-Za-z0-9_.-]{1,100}$"
)

HTTP_STATUS = re.compile(r"\(HTTP (\d{3})\)")


@dataclasses.dataclass(frozen=True)
class Check:
    name: str
    status: str  # OK, FAIL, SKIP (could not check) or INFO (not counted)
    detail: str


@dataclasses.dataclass(frozen=True)
class ApiResult:
    """Outcome of one ``gh api`` call. ``status`` is None if no HTTP status is known."""

    ok: bool
    status: int | None
    data: Any
    error: str


GhApi = Callable[[str], ApiResult]


def run_gh_api(endpoint: str) -> ApiResult:
    """GET ``endpoint`` with the GitHub CLI. Never raises."""
    try:
        proc = subprocess.run(
            ["gh", "api", "-X", "GET", endpoint],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        return ApiResult(False, None, None, "gh not found")
    except subprocess.TimeoutExpired:
        return ApiResult(False, None, None, "gh api timed out")
    return parse_gh_output(proc.returncode, proc.stdout, proc.stderr)


def parse_gh_output(returncode: int, stdout: str, stderr: str) -> ApiResult:
    """Turn the outcome of ``gh api`` into an ApiResult (pure, testable)."""
    try:
        data = json.loads(stdout) if stdout.strip() else None
    except json.JSONDecodeError:
        data = None
    if returncode == 0:
        return ApiResult(True, 200, data, "")
    match = HTTP_STATUS.search(stderr) or HTTP_STATUS.search(stdout)
    status = int(match.group(1)) if match else None
    message = ""
    if isinstance(data, dict) and isinstance(data.get("message"), str):
        message = data["message"]
    elif stderr.strip():
        message = stderr.strip().splitlines()[-1]
    return ApiResult(False, status, data, message)


def access_problem(result: ApiResult) -> str:
    """Explain a failed call in one line (rights, authentication, network)."""
    if result.status in (401, 403):
        return f"accès refusé (HTTP {result.status}) : le jeton n'a pas les droits de lecture nécessaires"
    if result.status == 404:
        return "introuvable (HTTP 404) : dépôt inconnu, ou jeton sans droit de lecture sur cette ressource"
    if result.status is None:
        return f"appel impossible : {result.error or 'erreur inconnue'}"
    return f"HTTP {result.status} : {result.error}"


def ref_includes_default_branch(ruleset: dict[str, Any], default_branch: str) -> bool:
    ref_name = (ruleset.get("conditions") or {}).get("ref_name") or {}
    includes = ref_name.get("include") or []
    excludes = ref_name.get("exclude") or []
    names = {"~DEFAULT_BRANCH", "~ALL", f"refs/heads/{default_branch}"}
    return any(i in names for i in includes) and not any(e in names for e in excludes)


def pull_request_rule(ruleset: dict[str, Any]) -> dict[str, Any] | None:
    for rule in ruleset.get("rules") or []:
        if isinstance(rule, dict) and rule.get("type") == "pull_request":
            return rule.get("parameters") or {}
    return None


def approval_count(params: dict[str, Any] | None) -> int:
    """Required approvals of a ``pull_request`` rule; a missing or null value counts as 0."""
    value = (params or {}).get("required_approving_review_count")
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def describe_actor(actor: dict[str, Any]) -> str:
    return (
        f"{actor.get('actor_type')} {actor.get('actor_id')} "
        f"({actor.get('bypass_mode')})"
    )


def is_whitelisted_actor(actor: dict[str, Any]) -> bool:
    return (
        actor.get("actor_type") == ADMIN_ACTOR_TYPE
        and actor.get("actor_id") == ADMIN_ROLE_ID
        and actor.get("bypass_mode") == ADMIN_BYPASS_MODE
    )


def evaluate_bypass(approving: list[dict[str, Any]]) -> list[Check]:
    """Bypass checks on the rulesets requiring an approval (pure).

    Strict whitelist: the only accepted actor is the admin role in ``pull_request``
    mode. ``exempt`` is as permissive as ``always`` (the actor skips the rule
    entirely), so it is reported as such.
    """
    if not all("bypass_actors" in r for r in approving):
        return [
            Check(
                "contournement du propriétaire",
                SKIP,
                "bypass_actors absent de la réponse : jeton sans droit d'administration, non vérifiable",
            )
        ]
    actors = [
        a
        for r in approving
        for a in (r.get("bypass_actors") or [])
        if isinstance(a, dict)
    ]
    checks: list[Check] = []
    if any(is_whitelisted_actor(a) for a in actors):
        checks.append(
            Check(
                "contournement du propriétaire",
                OK,
                "rôle admin : bypass_mode = pull_request",
            )
        )
    else:
        checks.append(
            Check(
                "contournement du propriétaire",
                FAIL,
                f"pas de contournement pull_request pour le rôle admin (actor_id {ADMIN_ROLE_ID})",
            )
        )
    unexpected = [a for a in actors if not is_whitelisted_actor(a)]
    if unexpected:
        permanent = [
            a for a in unexpected if a.get("bypass_mode") in ("always", "exempt")
        ]
        suffix = (
            " ; les modes always et exempt permettent un push direct sur la branche par défaut"
            if permanent
            else ""
        )
        checks.append(
            Check(
                "aucun autre acteur de contournement",
                FAIL,
                "acteur(s) hors liste blanche : "
                + ", ".join(describe_actor(a) for a in unexpected)
                + suffix,
            )
        )
    else:
        checks.append(
            Check(
                "aucun autre acteur de contournement",
                OK,
                "liste blanche respectée (rôle admin en mode pull_request seulement)",
            )
        )
    return checks


def evaluate_rulesets(
    rulesets: list[dict[str, Any]], default_branch: str
) -> list[Check]:
    """Ruleset checks on the detailed rulesets of the repository (pure)."""
    targeted = [
        r
        for r in rulesets
        if r.get("target") == "branch"
        and r.get("enforcement") == "active"
        and ref_includes_default_branch(r, default_branch)
    ]
    if not targeted:
        detail = (
            f"aucun ruleset actif ne cible la branche par défaut ({default_branch})"
        )
        return [
            Check("approbations requises", FAIL, detail),
            Check("contournement du propriétaire", FAIL, detail),
        ]

    with_pr = [(r, pull_request_rule(r)) for r in targeted]
    if not any(p is not None for _, p in with_pr):
        return [
            Check(
                "approbations requises",
                FAIL,
                "aucune règle pull_request sur la branche par défaut",
            )
        ]
    approving = [(r, p) for r, p in with_pr if p is not None and approval_count(p) >= 1]
    if not approving:
        counts = [approval_count(p) for _, p in with_pr if p is not None]
        return [
            Check(
                "approbations requises",
                FAIL,
                f"required_approving_review_count = {max(counts)} (au moins 1 attendu)",
            )
        ]

    # Everything below is checked on the rulesets that really require an approval:
    # a laxer ruleset next to a strict one would not weaken the barrier by itself,
    # but a bypass or a missing option on the strict one would.
    params = [p for _, p in approving]
    checks: list[Check] = [
        Check(
            "approbations requises",
            OK,
            f"required_approving_review_count = {max(approval_count(p) for p in params)}",
        )
    ]

    if any(
        p.get("dismiss_stale_reviews_on_push") or p.get("require_last_push_approval")
        for p in params
    ):
        checks.append(
            Check(
                "approbations périmées écartées",
                OK,
                "dismiss_stale_reviews_on_push ou require_last_push_approval actif",
            )
        )
    else:
        checks.append(
            Check(
                "approbations périmées écartées",
                FAIL,
                "ni dismiss_stale_reviews_on_push ni require_last_push_approval : "
                "un push après approbation resterait approuvé",
            )
        )

    if any(p.get("require_code_owner_review") for p in params):
        checks.append(
            Check(
                "revue du propriétaire du code", OK, "require_code_owner_review = true"
            )
        )
    else:
        checks.append(
            Check(
                "revue du propriétaire du code",
                FAIL,
                "require_code_owner_review n'est pas actif : tout compte Write pourrait approuver",
            )
        )

    checks.extend(evaluate_bypass([r for r, _ in approving]))
    return checks


def evaluate_codeowners(path: pathlib.Path) -> Check:
    """``.github/CODEOWNERS`` exists and holds at least one rule (pure, reads one file)."""
    name = "fichier CODEOWNERS"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return Check(
            name,
            FAIL,
            f"{path.name} introuvable (.github/CODEOWNERS) : la revue du propriétaire du code ne pourrait rien exiger",
        )
    rules = [
        line
        for line in (raw.strip() for raw in text.splitlines())
        if line and not line.startswith("#")
    ]
    if not rules:
        return Check(name, FAIL, ".github/CODEOWNERS ne contient aucune règle")
    return Check(name, OK, f".github/CODEOWNERS présent ({len(rules)} règle(s))")


def evaluate_agents_permission(account: str, result: ApiResult) -> Check:
    """Check 3 on the response of ``collaborators/{account}/permission`` (pure)."""
    name = f"rôle du compte {account}"
    if not result.ok:
        if result.status == 404:
            return Check(
                name,
                FAIL,
                "pas collaborateur du dépôt (invitation non acceptée ? compte inconnu ? "
                "`just tf-apply` fait ?)",
            )
        return Check(name, SKIP, access_problem(result))
    data = result.data if isinstance(result.data, dict) else {}
    role = data.get("role_name")
    permission = data.get("permission")
    if role == "write":
        return Check(name, OK, "rôle write (permission push)")
    if role is None and permission == "write":
        return Check(
            name, SKIP, "permission write, mais role_name absent : maintain non exclu"
        )
    if role in ("admin", "maintain") or permission == "admin":
        return Check(
            name, FAIL, f"rôle {role or permission} : trop de droits, write attendu"
        )
    shown = role or permission or "inconnu"
    if shown in ("read", "none"):
        return Check(
            name,
            FAIL,
            f"rôle {shown} : write attendu (invitation non acceptée ? "
            "voir docs/technique/compte-machine-agents.md, étape (d))",
        )
    return Check(name, FAIL, f"rôle {shown} : write attendu")


def verify(
    repo: str | None,
    agents_account: str | None,
    gh_api: GhApi = run_gh_api,
    codeowners_path: pathlib.Path = CODEOWNERS_PATH,
) -> list[Check]:
    """Run every check. ``repo`` is ``OWNER/REPO`` or None (the repository of the cwd)."""
    base = f"repos/{repo}" if repo else "repos/{owner}/{repo}"

    info = gh_api(base)
    if not info.ok or not isinstance(info.data, dict):
        return [Check("lecture du dépôt", SKIP, access_problem(info))]
    default_branch = str(info.data.get("default_branch") or "main")
    full_name = str(info.data.get("full_name") or repo or "")
    base = f"repos/{full_name}" if full_name else base

    checks: list[Check] = [
        Check(
            "lecture du dépôt",
            OK,
            f"{full_name}, branche par défaut : {default_branch}",
        )
    ]

    checks.append(evaluate_codeowners(codeowners_path))

    listing = gh_api(f"{base}/rulesets?includes_parents=false")
    if not listing.ok or not isinstance(listing.data, list):
        checks.append(Check("lecture des rulesets", SKIP, access_problem(listing)))
    else:
        details: list[dict[str, Any]] = []
        problem: str | None = None
        for summary in listing.data:
            if not isinstance(summary, dict) or "id" not in summary:
                continue
            one = gh_api(f"{base}/rulesets/{int(summary['id'])}")
            if one.ok and isinstance(one.data, dict):
                details.append(one.data)
            else:
                problem = access_problem(one)
                break
        if problem is not None:
            checks.append(Check("lecture des rulesets", SKIP, problem))
        else:
            checks.extend(evaluate_rulesets(details, default_branch))

    if agents_account:
        checks.append(
            evaluate_agents_permission(
                agents_account,
                gh_api(f"{base}/collaborators/{agents_account}/permission"),
            )
        )
    else:
        checks.append(
            Check(
                "rôle du compte machine",
                INFO,
                "non vérifié : AGENTS_ACCOUNT non fourni",
            )
        )
    return checks


def exit_code(checks: list[Check]) -> int:
    if any(c.status == FAIL for c in checks):
        return 1
    if any(c.status == SKIP for c in checks):
        return 3
    return 0


def main(argv: list[str] | None = None, gh_api: GhApi = run_gh_api) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--agents-account", default=os.environ.get("AGENTS_ACCOUNT", "")
    )
    parser.add_argument(
        "--repo",
        default="",
        help="OWNER/REPO (default: the repository of the current directory)",
    )
    args = parser.parse_args(argv)

    account = args.agents_account.strip()
    if account and not (len(account) <= 39 and GITHUB_LOGIN.match(account)):
        print(
            f"merge-barrier: identifiant GitHub invalide : {account!r}", file=sys.stderr
        )
        return 2
    repo = args.repo.strip()
    if repo and not GITHUB_REPO.match(repo):
        print(
            f"merge-barrier: dépôt invalide (attendu OWNER/REPO) : {repo!r}",
            file=sys.stderr,
        )
        return 2

    checks = verify(repo or None, account or None, gh_api)
    for c in checks:
        print(f"{c.status:<4} {c.name} : {c.detail}")
    code = exit_code(checks)
    if code == 0:
        print("OK merge-barrier")
    elif code == 1:
        print("FAILED merge-barrier", file=sys.stderr)
    else:
        print(
            "NON VERIFIE merge-barrier : au moins un contrôle n'a pas pu être fait "
            "(voir les lignes SKIP ; un jeton d'administration en lecture est nécessaire pour les rulesets)",
            file=sys.stderr,
        )
    return code


if __name__ == "__main__":
    sys.exit(main())
