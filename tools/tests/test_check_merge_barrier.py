"""Tests for tools/check_merge_barrier.py.

Hermetic: no network and no real ``gh`` call; the GitHub API responses are mocked.
Run with: ``python -m unittest discover -s tools/tests`` (or ``just tools-test``).
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

TOOLS_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS_DIR))

import check_merge_barrier as cmb

REPO = {"full_name": "owner/nothing-to-lose", "default_branch": "main"}

ADMIN_BYPASS = {
    "actor_id": 5,
    "actor_type": "RepositoryRole",
    "bypass_mode": "pull_request",
}


def ruleset(
    *,
    approvals: int | None = 1,
    last_push: bool = True,
    dismiss_stale: bool = False,
    code_owner: bool = True,
    null_count: bool = False,
    bypass: list[dict] | None = None,
    include: list[str] | None = None,
    enforcement: str = "active",
    target: str = "branch",
    omit_bypass: bool = False,
) -> dict:
    rules: list[dict] = [{"type": "deletion"}]
    if approvals is not None:
        rules.append(
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": None
                    if null_count
                    else approvals,
                    "dismiss_stale_reviews_on_push": dismiss_stale,
                    "require_last_push_approval": last_push,
                    "require_code_owner_review": code_owner,
                },
            }
        )
    data = {
        "id": 1,
        "name": "branche-principale",
        "target": target,
        "enforcement": enforcement,
        "conditions": {
            "ref_name": {"include": include or ["~DEFAULT_BRANCH"], "exclude": []}
        },
        "rules": rules,
    }
    if not omit_bypass:
        data["bypass_actors"] = [ADMIN_BYPASS] if bypass is None else bypass
    return data


def ok(data) -> cmb.ApiResult:
    return cmb.ApiResult(True, 200, data, "")


def err(status: int | None, message: str = "") -> cmb.ApiResult:
    return cmb.ApiResult(False, status, None, message)


def by_name(checks: list[cmb.Check]) -> dict[str, cmb.Check]:
    return {c.name: c for c in checks}


class FakeGh:
    """Maps endpoints to results; records every endpoint requested."""

    def __init__(self, routes: dict[str, cmb.ApiResult]):
        self.routes = routes
        self.calls: list[str] = []

    def __call__(self, endpoint: str) -> cmb.ApiResult:
        self.calls.append(endpoint)
        return self.routes.get(endpoint, err(404, "Not Found"))


def routes(
    rs: dict | None, permission: cmb.ApiResult | None = None, account: str = "bot"
) -> dict:
    base = "repos/owner/nothing-to-lose"
    r = {
        "repos/{owner}/{repo}": ok(REPO),
        f"{base}/rulesets?includes_parents=false": ok([{"id": 1}] if rs else []),
    }
    if rs:
        r[f"{base}/rulesets/1"] = ok(rs)
    if permission is not None:
        r[f"{base}/collaborators/{account}/permission"] = permission
    return r


class ParseGhOutputTests(unittest.TestCase):
    def test_success(self):
        r = cmb.parse_gh_output(0, '{"a": 1}', "")
        self.assertTrue(r.ok)
        self.assertEqual(r.data, {"a": 1})

    def test_forbidden(self):
        r = cmb.parse_gh_output(
            1,
            '{"message":"Resource not accessible by personal access token","status":"403"}',
            "gh: Resource not accessible by personal access token (HTTP 403)",
        )
        self.assertFalse(r.ok)
        self.assertEqual(r.status, 403)
        self.assertIn("not accessible", r.error)
        self.assertIn("droits de lecture", cmb.access_problem(r))

    def test_not_found(self):
        r = cmb.parse_gh_output(
            1, '{"message":"Not Found"}', "gh: Not Found (HTTP 404)"
        )
        self.assertEqual(r.status, 404)

    def test_not_authenticated_has_no_status(self):
        r = cmb.parse_gh_output(
            4, "", "To get started with GitHub CLI, please run:  gh auth login"
        )
        self.assertIsNone(r.status)
        self.assertIn("gh auth login", cmb.access_problem(r))

    def test_garbage_output_never_raises(self):
        r = cmb.parse_gh_output(0, "not json", "")
        self.assertTrue(r.ok)
        self.assertIsNone(r.data)


class EvaluateRulesetsTests(unittest.TestCase):
    def test_nominal(self):
        c = by_name(cmb.evaluate_rulesets([ruleset()], "main"))
        self.assertEqual(c["approbations requises"].status, cmb.OK)
        self.assertEqual(c["approbations périmées écartées"].status, cmb.OK)
        self.assertEqual(c["revue du propriétaire du code"].status, cmb.OK)
        self.assertEqual(c["contournement du propriétaire"].status, cmb.OK)
        self.assertEqual(c["aucun autre acteur de contournement"].status, cmb.OK)
        self.assertNotIn(cmb.FAIL, [x.status for x in c.values()])

    def test_zero_approvals_fails(self):
        c = by_name(cmb.evaluate_rulesets([ruleset(approvals=0)], "main"))
        self.assertEqual(c["approbations requises"].status, cmb.FAIL)

    def test_null_approval_count_does_not_crash(self):
        c = by_name(cmb.evaluate_rulesets([ruleset(null_count=True)], "main"))
        self.assertEqual(c["approbations requises"].status, cmb.FAIL)

    def test_no_pull_request_rule_fails(self):
        c = by_name(cmb.evaluate_rulesets([ruleset(approvals=None)], "main"))
        self.assertEqual(c["approbations requises"].status, cmb.FAIL)

    def test_no_ruleset_fails_both(self):
        checks = cmb.evaluate_rulesets([], "main")
        self.assertEqual([c.status for c in checks], [cmb.FAIL, cmb.FAIL])

    def test_inactive_or_other_target_ignored(self):
        for rs in (
            ruleset(enforcement="disabled"),
            ruleset(target="tag"),
            ruleset(include=["refs/heads/dev"]),
        ):
            with self.subTest(rs=rs["enforcement"] + rs["target"]):
                self.assertTrue(
                    all(
                        c.status == cmb.FAIL
                        for c in cmb.evaluate_rulesets([rs], "main")
                    )
                )

    def test_explicit_default_branch_ref_matches(self):
        c = by_name(
            cmb.evaluate_rulesets([ruleset(include=["refs/heads/trunk"])], "trunk")
        )
        self.assertEqual(c["approbations requises"].status, cmb.OK)

    # (c) stale approvals
    def test_stale_approvals_neither_option_fails(self):
        c = by_name(
            cmb.evaluate_rulesets(
                [ruleset(last_push=False, dismiss_stale=False)], "main"
            )
        )
        self.assertEqual(c["approbations périmées écartées"].status, cmb.FAIL)

    def test_stale_approvals_either_option_is_enough(self):
        for kwargs in (
            {"last_push": True, "dismiss_stale": False},
            {"last_push": False, "dismiss_stale": True},
        ):
            with self.subTest(**kwargs):
                c = by_name(cmb.evaluate_rulesets([ruleset(**kwargs)], "main"))
                self.assertEqual(c["approbations périmées écartées"].status, cmb.OK)

    # (d) code owner review
    def test_code_owner_review_required(self):
        c = by_name(cmb.evaluate_rulesets([ruleset(code_owner=False)], "main"))
        self.assertEqual(c["revue du propriétaire du code"].status, cmb.FAIL)

    # (a) strict whitelist
    def test_bypass_wrong_mode_fails(self):
        wrong = [{**ADMIN_BYPASS, "bypass_mode": "always"}]
        c = by_name(cmb.evaluate_rulesets([ruleset(bypass=wrong)], "main"))
        self.assertEqual(c["contournement du propriétaire"].status, cmb.FAIL)
        self.assertEqual(c["aucun autre acteur de contournement"].status, cmb.FAIL)

    def test_bypass_other_role_fails(self):
        other = [{**ADMIN_BYPASS, "actor_id": 4}]
        c = by_name(cmb.evaluate_rulesets([ruleset(bypass=other)], "main"))
        self.assertEqual(c["contournement du propriétaire"].status, cmb.FAIL)
        self.assertEqual(c["aucun autre acteur de contournement"].status, cmb.FAIL)

    def test_empty_bypass_fails(self):
        c = by_name(cmb.evaluate_rulesets([ruleset(bypass=[])], "main"))
        self.assertEqual(c["contournement du propriétaire"].status, cmb.FAIL)

    def test_missing_bypass_field_is_unverifiable_not_failed(self):
        c = by_name(cmb.evaluate_rulesets([ruleset(omit_bypass=True)], "main"))
        self.assertEqual(c["contournement du propriétaire"].status, cmb.SKIP)

    def test_extra_actor_in_any_mode_fails(self):
        for actor in (
            {"actor_id": 99, "actor_type": "Team", "bypass_mode": "always"},
            {"actor_id": 99, "actor_type": "Team", "bypass_mode": "pull_request"},
            {
                "actor_id": 99,
                "actor_type": "Integration",
                "bypass_mode": "pull_request",
            },
            {
                "actor_id": 99,
                "actor_type": "OrganizationAdmin",
                "bypass_mode": "pull_request",
            },
            {
                "actor_id": 4,
                "actor_type": "RepositoryRole",
                "bypass_mode": "pull_request",
            },
        ):
            with self.subTest(actor=actor):
                c = by_name(
                    cmb.evaluate_rulesets(
                        [ruleset(bypass=[ADMIN_BYPASS, actor])], "main"
                    )
                )
                self.assertEqual(c["contournement du propriétaire"].status, cmb.OK)
                self.assertEqual(
                    c["aucun autre acteur de contournement"].status, cmb.FAIL
                )

    # (b) exempt is as permissive as always
    def test_exempt_mode_is_treated_as_always(self):
        for actors in (
            [ADMIN_BYPASS, {**ADMIN_BYPASS, "actor_id": 7, "bypass_mode": "exempt"}],
            [{**ADMIN_BYPASS, "bypass_mode": "exempt"}],
        ):
            with self.subTest(actors=actors):
                c = by_name(cmb.evaluate_rulesets([ruleset(bypass=actors)], "main"))
                other = c["aucun autre acteur de contournement"]
                self.assertEqual(other.status, cmb.FAIL)
                self.assertIn("exempt", other.detail)

    # (e) every ruleset requiring an approval is checked
    def test_bypass_is_checked_in_every_approving_ruleset(self):
        second = ruleset()
        second["id"] = 2
        second["bypass_actors"] = [
            ADMIN_BYPASS,
            {"actor_id": 1, "actor_type": "Team", "bypass_mode": "always"},
        ]
        c = by_name(cmb.evaluate_rulesets([ruleset(), second], "main"))
        self.assertEqual(c["aucun autre acteur de contournement"].status, cmb.FAIL)

    def test_missing_bypass_field_in_second_ruleset_is_unverifiable(self):
        second = ruleset(omit_bypass=True)
        second["id"] = 2
        c = by_name(cmb.evaluate_rulesets([ruleset(), second], "main"))
        self.assertEqual(c["contournement du propriétaire"].status, cmb.SKIP)

    def test_lax_ruleset_does_not_hide_the_strict_one(self):
        lax = ruleset(
            approvals=0,
            bypass=[{"actor_id": 1, "actor_type": "Team", "bypass_mode": "always"}],
        )
        lax["id"] = 2
        c = by_name(cmb.evaluate_rulesets([ruleset(), lax], "main"))
        # The lax ruleset requires no approval: it is not part of the barrier.
        self.assertEqual(c["aucun autre acteur de contournement"].status, cmb.OK)

    def test_options_come_from_the_approving_ruleset(self):
        lax = ruleset(approvals=0, code_owner=True)
        lax["id"] = 2
        c = by_name(cmb.evaluate_rulesets([ruleset(code_owner=False), lax], "main"))
        self.assertEqual(c["revue du propriétaire du code"].status, cmb.FAIL)


class CodeownersFileTests(unittest.TestCase):
    def check(self, content: str | None) -> cmb.Check:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "CODEOWNERS"
            if content is not None:
                path.write_text(content, encoding="utf-8")
            return cmb.evaluate_codeowners(path)

    def test_present(self):
        self.assertEqual(self.check("# c\n* @owner\n").status, cmb.OK)

    def test_missing(self):
        self.assertEqual(self.check(None).status, cmb.FAIL)

    def test_only_comments(self):
        self.assertEqual(self.check("# nothing\n\n").status, cmb.FAIL)

    def test_repository_file_is_valid(self):
        self.assertEqual(cmb.evaluate_codeowners(cmb.CODEOWNERS_PATH).status, cmb.OK)


class AgentsPermissionTests(unittest.TestCase):
    def test_write(self):
        c = cmb.evaluate_agents_permission(
            "bot", ok({"permission": "write", "role_name": "write"})
        )
        self.assertEqual(c.status, cmb.OK)

    def test_maintain_fails(self):
        # The legacy "permission" field says write for maintain: role_name tells the truth.
        c = cmb.evaluate_agents_permission(
            "bot", ok({"permission": "write", "role_name": "maintain"})
        )
        self.assertEqual(c.status, cmb.FAIL)

    def test_admin_fails(self):
        c = cmb.evaluate_agents_permission(
            "bot", ok({"permission": "admin", "role_name": "admin"})
        )
        self.assertEqual(c.status, cmb.FAIL)

    def test_read_fails_with_invitation_hint(self):
        c = cmb.evaluate_agents_permission(
            "bot", ok({"permission": "read", "role_name": "read"})
        )
        self.assertEqual(c.status, cmb.FAIL)
        self.assertIn("invitation non acceptée", c.detail)

    def test_none_fails_with_invitation_hint(self):
        c = cmb.evaluate_agents_permission(
            "bot", ok({"permission": "none", "role_name": "none"})
        )
        self.assertEqual(c.status, cmb.FAIL)
        self.assertIn("invitation non acceptée", c.detail)

    def test_triage_has_no_invitation_hint(self):
        c = cmb.evaluate_agents_permission(
            "bot", ok({"permission": "read", "role_name": "triage"})
        )
        self.assertEqual(c.status, cmb.FAIL)
        self.assertNotIn("invitation", c.detail)

    def test_role_name_absent_cannot_exclude_maintain(self):
        c = cmb.evaluate_agents_permission("bot", ok({"permission": "write"}))
        self.assertEqual(c.status, cmb.SKIP)

    def test_not_a_collaborator(self):
        c = cmb.evaluate_agents_permission("bot", err(404, "Not Found"))
        self.assertEqual(c.status, cmb.FAIL)
        self.assertIn("invitation", c.detail)

    def test_forbidden_is_unverifiable(self):
        c = cmb.evaluate_agents_permission("bot", err(403))
        self.assertEqual(c.status, cmb.SKIP)

    def test_unexpected_payload_does_not_raise(self):
        for payload in (None, [], "x", {}):
            with self.subTest(payload=payload):
                c = cmb.evaluate_agents_permission("bot", ok(payload))
                self.assertIn(c.status, (cmb.FAIL, cmb.SKIP))


class VerifyTests(unittest.TestCase):
    def test_all_ok(self):
        perm = ok({"permission": "write", "role_name": "write"})
        gh = FakeGh(routes(ruleset(), perm))
        checks = cmb.verify(None, "bot", gh, cmb.CODEOWNERS_PATH)
        self.assertEqual(cmb.exit_code(checks), 0)

    def test_only_get_style_endpoints_are_requested(self):
        perm = ok({"permission": "write", "role_name": "write"})
        gh = FakeGh(routes(ruleset(), perm))
        cmb.verify(None, "bot", gh, cmb.CODEOWNERS_PATH)
        self.assertEqual(
            gh.calls,
            [
                "repos/{owner}/{repo}",
                "repos/owner/nothing-to-lose/rulesets?includes_parents=false",
                "repos/owner/nothing-to-lose/rulesets/1",
                "repos/owner/nothing-to-lose/collaborators/bot/permission",
            ],
        )

    def test_no_account_is_informational(self):
        checks = cmb.verify(None, None, FakeGh(routes(ruleset())))
        self.assertEqual(cmb.exit_code(checks), 0)
        self.assertEqual(by_name(checks)["rôle du compte machine"].status, cmb.INFO)

    def test_explicit_repo_is_used(self):
        gh = FakeGh(
            {
                "repos/owner/nothing-to-lose": ok(REPO),
                **{
                    k: v
                    for k, v in routes(ruleset()).items()
                    if k != "repos/{owner}/{repo}"
                },
            }
        )
        checks = cmb.verify("owner/nothing-to-lose", None, gh)
        self.assertEqual(cmb.exit_code(checks), 0)
        self.assertEqual(gh.calls[0], "repos/owner/nothing-to-lose")

    def test_token_without_read_rights(self):
        gh = FakeGh({"repos/{owner}/{repo}": err(403, "Resource not accessible")})
        checks = cmb.verify(None, "bot", gh, cmb.CODEOWNERS_PATH)
        self.assertEqual(cmb.exit_code(checks), 3)
        self.assertEqual(len(checks), 1)

    def test_rulesets_listing_forbidden(self):
        r = routes(ruleset(), ok({"permission": "write", "role_name": "write"}))
        r["repos/owner/nothing-to-lose/rulesets?includes_parents=false"] = err(403)
        checks = cmb.verify(None, "bot", FakeGh(r))
        self.assertEqual(by_name(checks)["lecture des rulesets"].status, cmb.SKIP)
        self.assertEqual(cmb.exit_code(checks), 3)

    def test_missing_codeowners_file_fails_verify(self):
        gh = FakeGh(routes(ruleset()))
        with tempfile.TemporaryDirectory() as tmp:
            checks = cmb.verify(None, None, gh, pathlib.Path(tmp) / "CODEOWNERS")
        self.assertEqual(by_name(checks)["fichier CODEOWNERS"].status, cmb.FAIL)
        self.assertEqual(cmb.exit_code(checks), 1)

    def test_failure_wins_over_unverifiable(self):
        r = routes(ruleset(approvals=0, omit_bypass=True))
        checks = cmb.verify(None, None, FakeGh(r))
        self.assertEqual(cmb.exit_code(checks), 1)


class MainTests(unittest.TestCase):
    def run_main(self, argv, gh=None):
        out, err_ = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err_):
            code = cmb.main(argv, gh or FakeGh({}))
        return code, out.getvalue(), err_.getvalue()

    def test_invalid_account_is_refused_before_any_call(self):
        gh = FakeGh({})
        for bad in ("a b", "-x", "x-", "a--b", "../x", "a/b", "x" * 40):
            with self.subTest(bad=bad):
                code, _, stderr = self.run_main([f"--agents-account={bad}"], gh)
                self.assertEqual(code, 2)
                self.assertIn("invalide", stderr)
        self.assertEqual(gh.calls, [])

    def test_invalid_repo_is_refused(self):
        gh = FakeGh({})
        for bad in (
            "a/b/c",
            "a/..",
            "../b",
            "a/b..c",
            "a/.",
            "..",
            "a b/c",
            "-a/b",
            "a/b?x=1",
            "a/b#",
        ):
            with self.subTest(bad=bad):
                code, _, _ = self.run_main([f"--repo={bad}"], gh)
                self.assertEqual(code, 2)
        self.assertEqual(gh.calls, [])

    def test_valid_repo_shapes_are_accepted(self):
        for good in ("owner/nothing-to-lose", "o/r.js", "o/.github", "o/a_b-c.d"):
            with self.subTest(good=good):
                self.assertTrue(cmb.GITHUB_REPO.match(good))

    def test_account_from_environment(self):
        perm = ok({"permission": "write", "role_name": "write"})
        with mock.patch.dict(os.environ, {"AGENTS_ACCOUNT": "bot"}):
            code, stdout, _ = self.run_main([], FakeGh(routes(ruleset(), perm)))
        self.assertEqual(code, 0)
        self.assertIn("OK merge-barrier", stdout)

    def test_failure_output(self):
        code, stdout, stderr = self.run_main(
            ["--agents-account", "bot"], FakeGh(routes(ruleset(approvals=0), err(404)))
        )
        self.assertEqual(code, 1)
        self.assertIn("FAIL approbations requises", stdout)
        self.assertIn("FAILED merge-barrier", stderr)

    def test_unverifiable_output(self):
        code, _, stderr = self.run_main([], FakeGh({"repos/{owner}/{repo}": err(401)}))
        self.assertEqual(code, 3)
        self.assertIn("NON VERIFIE", stderr)


class RunGhApiTests(unittest.TestCase):
    """The only subprocess call is a read-only ``gh api -X GET``."""

    def test_argv_is_a_plain_get(self):
        completed = subprocess.CompletedProcess([], 0, stdout="{}", stderr="")
        with mock.patch.object(cmb.subprocess, "run", return_value=completed) as run:
            cmb.run_gh_api("repos/owner/repo/rulesets?includes_parents=false")
        argv = run.call_args.args[0]
        self.assertEqual(argv[:2], ["gh", "api"])
        self.assertIn("-X", argv)
        self.assertEqual(argv[argv.index("-X") + 1], "GET")
        for forbidden in ("-f", "-F", "--input", "--field", "--raw-field"):
            self.assertNotIn(forbidden, argv)
        for arg in argv:
            self.assertFalse(arg.startswith(("--input=", "--field=", "--raw-field=")))
        self.assertEqual(argv.count("-X"), 1)
        self.assertNotIn("--method", argv)
        self.assertEqual(argv[-1], "repos/owner/repo/rulesets?includes_parents=false")
        # No shell, no token on the command line.
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_missing_gh_never_raises(self):
        with mock.patch.object(cmb.subprocess, "run", side_effect=FileNotFoundError):
            self.assertFalse(cmb.run_gh_api("repos/x/y").ok)

    def test_timeout_never_raises(self):
        with mock.patch.object(
            cmb.subprocess, "run", side_effect=subprocess.TimeoutExpired("gh", 30)
        ):
            self.assertFalse(cmb.run_gh_api("repos/x/y").ok)


if __name__ == "__main__":
    unittest.main()
