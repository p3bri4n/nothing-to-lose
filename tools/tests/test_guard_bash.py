"""Tests for tools/hooks/guard_bash.py.

Hermetic: the current branch is given by a fake lookup (no ``git`` call) and every log
goes to a temporary project. A few tests use the real ``git`` in a throw-away
repository (branch lookup) and run the script as a subprocess (exit code, stdout and
stderr); they are skipped when ``git`` is missing.

Run with: ``python3 -m unittest discover -s tools/tests`` (or ``just tools-test``).
"""

from __future__ import annotations

import io
import json
import os
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "hooks"))

import guard_bash as guard

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "tools" / "hooks" / "guard_bash.py"
GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


def rule_of(command: str, branch: str | None = "feature") -> str | None:
    """Rule that refuses ``command`` (None: allowed), the current branch being fake."""
    violation = guard.Analyzer(lambda _dirs: branch).check(command)
    return violation.rule if violation else None


# (command, expected rule). The branch is "feature" unless the test says otherwise.
BLOCKED = [
    # --- git commit --no-verify / -n, in every position -------------------------------
    ("git commit --no-verify", "no-verify"),
    ("git commit -m x --no-verify", "no-verify"),
    ("git commit --no-verify -m x", "no-verify"),
    ("git commit --no-verif -m x", "no-verify"),
    ("git commit --no-v -m x", "no-verify"),
    ("git commit -n", "no-verify"),
    ("git commit -an", "no-verify"),
    ("git commit -na", "no-verify"),
    ("git commit -nm x", "no-verify"),
    ('git commit -nm "x"', "no-verify"),
    ('git commit -am "x" -n', "no-verify"),
    ('git commit -m "x" -sn', "no-verify"),
    ("git commit -S -n", "no-verify"),
    ("git commit --amend -n", "no-verify"),
    ("git -c x=y commit --no-verify", "no-verify"),
    ("git -c user.name=a -c user.email=b commit -n", "no-verify"),
    ("git -C /tmp commit -n", "no-verify"),
    ('git -C "/tmp/a b: c" commit --no-verify', "no-verify"),
    ("git --git-dir=.git commit -n", "no-verify"),
    ("git --git-dir .git --work-tree . commit -n", "no-verify"),
    ("git --no-pager commit -n", "no-verify"),
    ("git merge --no-verify x", "no-verify"),
    ("git rebase --no-verify main", "no-verify"),
    ("git push --no-verify origin HEAD", "no-verify"),
    # --- positions in the command line ---------------------------------------------------
    ("cd x && git commit -n -m y", "no-verify"),
    ("true; git commit -n", "no-verify"),
    ("false || git commit -n", "no-verify"),
    ("echo a | git commit -n", "no-verify"),
    ("sleep 1 & git commit -n", "no-verify"),
    ("(git commit -n)", "no-verify"),
    ("{ git commit -n; }", "no-verify"),
    ("echo $(git commit -n)", "no-verify"),
    ("echo `git commit -n`", "no-verify"),
    ('echo "$(git commit -n)"', "no-verify"),
    ('echo "a `git commit -n` b"', "no-verify"),
    ("diff <(git commit -n) x", "no-verify"),
    ("git commit -m ok\ngit commit -n", "no-verify"),
    ("git commit -m ok &&\\\n git commit -n", "no-verify"),
    ("if true; then git commit -n; fi", "no-verify"),
    ("for f in a b; do git commit -n; done", "no-verify"),
    ("while true; do git commit -n; done", "no-verify"),
    ("! git commit -n", "no-verify"),
    ('git commit -m "a" # ok\ngit commit -n', "no-verify"),
    ('git commit -n "abc', "no-verify"),  # unterminated quote: still seen
    ("cd '/run/media/a b: c' && git commit -n -m x", "no-verify"),
    # --- wrappers, shells, eval -----------------------------------------------------------
    ("bash -c 'git commit -n'", "no-verify"),
    ('sh -c "git commit --no-verify"', "no-verify"),
    ('bash -lc "git commit -n"', "no-verify"),
    ("bash -e -c 'git commit -n'", "no-verify"),
    ("bash -o pipefail -c 'git commit -n'", "no-verify"),
    ("zsh -c 'cd x; git commit -n'", "no-verify"),
    ("bash -c \"bash -c 'git commit -n'\"", "no-verify"),
    ("env git commit -n", "no-verify"),
    ("env FOO=bar git commit -n", "no-verify"),
    ("env -i FOO=bar git commit -n", "no-verify"),
    ("env -u HOME git commit -n", "no-verify"),
    ('env -S "git commit -n"', "no-verify"),
    ("sudo git commit -n", "no-verify"),
    ("sudo -u bob git commit -n", "no-verify"),
    ("sudo -E -- git commit -n", "no-verify"),
    ("time git commit -n", "no-verify"),
    ("time -p git commit -n", "no-verify"),
    ("command git commit -n", "no-verify"),
    ("command -p git commit -n", "no-verify"),
    ("exec git commit -n", "no-verify"),
    ("nohup git commit -n", "no-verify"),
    ("nice -n 5 git commit -n", "no-verify"),
    ("timeout 10 git commit -n", "no-verify"),
    ("timeout -s KILL 10 git commit -n", "no-verify"),
    ("xargs git commit -n", "no-verify"),
    ("xargs -n1 -I{} git commit -n {}", "no-verify"),
    ("mise exec -- git commit -n", "no-verify"),
    ("mise x node@22 -- git commit --no-verify", "no-verify"),
    ("eval git commit -n", "no-verify"),
    ('eval "git commit -n"', "no-verify"),
    ("sudo env FOO=1 bash -c 'git commit -n'", "no-verify"),
    ("/usr/bin/git commit -n", "no-verify"),
    ("\\git commit -n", "no-verify"),
    ('"git" commit -n', "no-verify"),
    ("'git' 'commit' '-n'", "no-verify"),
    ("GIT_AUTHOR_NAME=x git commit -n", "no-verify"),
    ("bash <<EOF\ngit commit -n\nEOF", "no-verify"),
    ("bash <<'EOF'\ngit commit -n\nEOF", "no-verify"),
    ('bash <<< "git commit -n"', "no-verify"),
    ("sh -s <<EOF\nls\ngit commit -n\nEOF", "no-verify"),
    ("git commit -m \"$(cat <<'EOF'\nmsg\nEOF\n)\" --no-verify", "no-verify"),
    ("cat <<EOF\n$(git commit -n)\nEOF", "no-verify"),
    # --- git push: force, delete, mirror ---------------------------------------------------
    ("git push --force", "push-force"),
    ("git push -f", "push-force"),
    ("git push origin feature --force", "push-force"),
    ("git push -f origin feature", "push-force"),
    ("git push -fu origin feature", "push-force"),
    ("git push -uf origin feature", "push-force"),
    ("git push --force-with-lease", "push-force"),
    ("git push --force-with-lease=feature origin feature", "push-force"),
    ("git push --force-if-includes", "push-force"),
    ("git push --forc origin feature", "push-force"),
    ("git push origin +feature", "push-force"),
    ("git push origin +HEAD:feature", "push-force"),
    ("git push --mirror", "push-mirror"),
    ("git push --mirror origin", "push-mirror"),
    ("git push --delete origin feature", "push-delete"),
    ("git push origin --delete feature", "push-delete"),
    ("git push -d origin feature", "push-delete"),
    ("git push origin :feature", "push-delete"),
    ("git push --prune origin", "push-delete"),
    ("git push --all", "push-all"),
    ("git push --all origin", "push-all"),
    ("git -c x=y push --force", "push-force"),
    ("bash -c 'git push --force'", "push-force"),
    ('bash -c "git push --force"', "push-force"),
    ("env sudo git push -f", "push-force"),
    ("xargs git push --force", "push-force"),
    ("cd x && git push -f && echo done", "push-force"),
    # --- git push: main / master -----------------------------------------------------------
    ("git push origin main", "push-main"),
    ("git push origin master", "push-main"),
    ("git push -u origin main", "push-main"),
    ("git push origin HEAD:main", "push-main"),
    ("git push origin HEAD:master", "push-main"),
    ("git push origin HEAD:refs/heads/main", "push-main"),
    ("git push origin refs/heads/main", "push-main"),
    ("git push origin feature:main", "push-main"),
    ("git push origin feature main", "push-main"),
    ("git push --repo origin main", "push-main"),
    ("git push --repo=origin main", "push-main"),
    ("git push origin 'refs/heads/*:refs/heads/*'", "push-main"),
    ("git -C ../x push origin HEAD:main", "push-main"),
    ("git push https://example.invalid/r.git HEAD:main", "push-main"),
    ("git switch main && git push origin HEAD", "push-main"),
    ("git checkout main && git push", "push-main"),
    ("git switch main; git push -u origin HEAD", "push-main"),
    # --- hooks disabled ---------------------------------------------------------------------
    ("git config core.hooksPath /dev/null", "hooks-path"),
    ("git config core.hookspath /dev/null", "hooks-path"),
    ("git config --global core.hooksPath /dev/null", "hooks-path"),
    ("git config --local core.hooksPath .githooks", "hooks-path"),
    ("git config --unset core.hooksPath", "hooks-path"),
    ("git config --unset-all core.hooksPath", "hooks-path"),
    ("git config --global --unset core.hooksPath", "hooks-path"),
    ("git config --replace-all core.hooksPath x", "hooks-path"),
    ("git config set core.hooksPath x", "hooks-path"),
    ("git config unset core.hooksPath", "hooks-path"),
    ("git -c core.hooksPath=/dev/null commit -m x", "hooks-path"),
    ("git -c core.hookspath=/dev/null commit -m x", "hooks-path"),
    ("git --config-env=core.hooksPath=HP commit -m x", "hooks-path"),
    (
        "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath git commit -m x",
        "hooks-path",
    ),
    ("env GIT_CONFIG_KEY_0=core.hooksPath git commit -m x", "hooks-path"),
    ("export GIT_CONFIG_KEY_0=core.hooksPath", "hooks-path"),
    ("bash -c 'git config core.hooksPath /dev/null'", "hooks-path"),
    # --- gh pr merge ---------------------------------------------------------------------------
    ("gh pr merge", "gh-pr-merge"),
    ("gh pr merge 7", "gh-pr-merge"),
    ("gh pr merge 7 --squash", "gh-pr-merge"),
    ("gh pr merge --auto", "gh-pr-merge"),
    ("gh pr merge --auto --squash 12", "gh-pr-merge"),
    ("gh pr merge --admin", "gh-pr-merge"),
    ("gh pr merge --rebase --delete-branch", "gh-pr-merge"),
    ("gh -R o/r pr merge 3", "gh-pr-merge"),
    ("gh --repo o/r pr merge 3", "gh-pr-merge"),
    ("gh pr --repo o/r merge 3", "gh-pr-merge"),
    ("cd x && gh pr merge", "gh-pr-merge"),
    ("echo ok; gh pr merge", "gh-pr-merge"),
    ("gh pr checks --watch && gh pr merge --auto", "gh-pr-merge"),
    ('bash -c "gh pr merge 1"', "gh-pr-merge"),
    ("sudo gh pr merge", "gh-pr-merge"),
    ("echo $(gh pr merge 3)", "gh-pr-merge"),
    ("cat <<EOF\n$(gh pr merge)\nEOF", "gh-pr-merge"),
    ("/usr/local/bin/gh pr merge", "gh-pr-merge"),
    ("GH_TOKEN=x gh pr merge", "gh-token-env"),
    # --- gh: repository administration -----------------------------------------------------------
    ("gh repo delete o/r --yes", "gh-admin"),
    ("gh repo delete", "gh-admin"),
    ("gh repo edit --default-branch dev", "gh-admin"),
    ("gh repo edit --enable-auto-merge", "gh-admin"),
    ("gh repo archive o/r", "gh-admin"),
    ("gh repo rename new", "gh-admin"),
    ("gh secret set X", "gh-admin"),
    ("gh secret delete X", "gh-admin"),
    ("gh variable set X --body 1", "gh-admin"),
    ("gh variable delete X", "gh-admin"),
    ("gh alias set m 'pr merge'", "gh-admin"),
    ("gh alias import f.yml", "gh-admin"),
    # --- gh api --------------------------------------------------------------------------------------
    ("gh api -X PUT repos/o/r/pulls/7/merge", "gh-api"),
    ("gh api -XPUT repos/o/r/pulls/7/merge", "gh-api"),
    ("gh api --method PUT repos/o/r/pulls/7/merge", "gh-api"),
    ("gh api --method=PUT repos/o/r/pulls/7/merge", "gh-api"),
    ("gh api -X put repos/o/r/pulls/7/merge", "gh-api"),
    ("gh api repos/o/r/pulls/7/merge -X PUT -f merge_method=squash", "gh-api"),
    ("gh api repos/o/r/pulls/7/merge -f merge_method=squash", "gh-api"),
    ("gh api /repos/o/r/pulls/7/merge -X PUT", "gh-api"),
    ("gh api https://api.github.com/repos/o/r/pulls/7/merge -X PUT", "gh-api"),
    ("gh api -X PUT repos/{owner}/{repo}/pulls/7/merge", "gh-api"),
    ("gh api -X DELETE repos/o/r/git/refs/heads/x", "gh-api"),
    ("gh api -X PATCH repos/o/r/git/refs/heads/main -f sha=abc", "gh-api"),
    ("gh api -X PUT repos/o/r/git/refs/heads/x", "gh-api"),
    ("gh api -X POST repos/o/r/rulesets -f name=x", "gh-api"),
    ("gh api -X PUT repos/o/r/rulesets/1", "gh-api"),
    ("gh api -X DELETE repos/o/r/rulesets/1", "gh-api"),
    ("gh api -X PUT repos/o/r/branches/main/protection", "gh-api"),
    ("gh api -X DELETE repos/o/r/branches/main/protection", "gh-api"),
    ("gh api -X POST repos/o/r/branches/main/rename -f new_name=x", "gh-api"),
    ("gh api -X PATCH repos/o/r -f default_branch=x", "gh-api"),
    ("gh api -X DELETE repos/o/r", "gh-api"),
    ("gh api -X PUT repos/o/r/actions/secrets/X", "gh-api"),
    ("gh api -X PUT repos/o/r/environments/production", "gh-api"),
    (
        "gh api graphql -f query='mutation { mergePullRequest(input: {}) { __typename } }'",
        "gh-api",
    ),
    (
        "gh api graphql -f query='mutation{enablePullRequestAutoMerge(input:{})}'",
        "gh-api",
    ),
    # --- review E10 (H2): gh api graphql that cannot be read ----------------------------------------------
    ("gh api graphql -F query=@q.graphql", "gh-api-opaque"),
    ("gh api graphql --field query=@q.graphql", "gh-api-opaque"),
    ("gh api graphql -Fquery=@q.graphql", "gh-api-opaque"),
    ("gh api graphql --input q.json", "gh-api-opaque"),
    ('gh api graphql -f query="$(cat q.graphql)"', "gh-api-opaque"),
    ("gh api graphql -f query=`cat q.graphql`", "gh-api-opaque"),
    ("gh api graphql -f query='query { viewer { login } }' -F n=@f", "gh-api-opaque"),
    # --- (H3): write to an endpoint that is computed -------------------------------------------------------
    ('gh api -X POST "$URL" -f a=b', "gh-api-opaque"),
    ("gh api -X PUT $URL", "gh-api-opaque"),
    ("gh api -X PUT $(echo repos/o/r/pulls/7/merge)", "gh-api-opaque"),
    ("gh api -XDELETE repos/o/r/git/refs/$(echo heads/x)", "gh-api-opaque"),
    ("gh api repos/o/r/$(echo x) -f a=b", "gh-api-opaque"),
    # --- (L7, L8): more REST and GraphQL writes, -X=VERB ---------------------------------------------------
    ("gh api -X POST repos/o/r/merges -f base=main -f head=x", "gh-api"),
    ("gh api -X PUT repos/o/r/contents/README.md -f message=x", "gh-api"),
    ("gh api -X DELETE repos/o/r/contents/a/b.md", "gh-api"),
    ("gh api repos/o/r/contents/f.md -f message=x -f content=eA==", "gh-api"),
    ("gh api -X=DELETE repos/o/r/git/refs/heads/x", "gh-api"),
    ("gh api -X=PUT repos/o/r/pulls/7/merge", "gh-api"),
    ("gh api graphql -f query='mutation{createCommitOnBranch(input:{})}'", "gh-api"),
    ("gh api graphql -f query='mutation{mergeBranch(input:{})}'", "gh-api"),
    ("gh pr merge --body --help", "gh-pr-merge"),  # --help is the body here
    # --- (M1, M2): heads/main, --branches ---------------------------------------------------------------------
    ("git push origin heads/main", "push-main"),
    ("git push origin HEAD:heads/main", "push-main"),
    ("git push origin HEAD:heads/master", "push-main"),
    ("git push origin refs/heads/master", "push-main"),
    ("git push --branches", "push-all"),
    ("git push --branches origin", "push-all"),
    ("git push --bran origin", "push-all"),
    ("git push --b", "push-all"),
    # --- (M3): configuration keys, in every channel ------------------------------------------------------------
    ("git -c alias.ci=commit status", "git-config"),
    ("git -c push.default=matching push", "git-config"),
    ("git -c include.path=/tmp/x status", "git-config"),
    ("git -c includeIf.gitdir:/a/.path=/tmp/x status", "git-config"),
    ("git -c remote.origin.push=refs/heads/*:refs/heads/main status", "git-config"),
    ("git -c remote.origin.mirror=true status", "git-config"),
    ("git -c Remote.Origin.Push=x status", "git-config"),
    ("git --config-env=alias.x=VAR status", "git-config"),
    ("git --config-env push.default=VAR push", "git-config"),
    ("git config alias.ci 'commit -n'", "git-config"),
    ("git config --global alias.ci x", "git-config"),
    ("git config --add include.path /tmp/x", "git-config"),
    ("git config --unset alias.ci", "git-config"),
    ("git config --replace-all push.default current", "git-config"),
    ("git config set push.default current", "git-config"),
    ("git config set remote.origin.push x", "git-config"),
    ("git config --rename-section foo alias", "git-config"),
    ("git config rename-section foo alias", "git-config"),
    ("git config rename-section foo includeIf", "git-config"),
    ("git config --file .git/config alias.ci x", "git-config"),
    ("GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x git status", "git-config"),
    ("""GIT_CONFIG_PARAMETERS="'push.default'='matching'" git push""", "git-config"),
    ("export GIT_CONFIG_KEY_0=include.path", "git-config"),
    ("env GIT_CONFIG_KEY_0=remote.origin.mirror git status", "git-config"),
    # --- (M4): the target of a push is computed -------------------------------------------------------------------
    ("git switch $B && git push", "push-unknown-branch"),
    ("git checkout -b $B && git push -u origin HEAD", "push-unknown-branch"),
    # --- (M6): $'...' escapes --------------------------------------------------------------------------------------
    ("$'\\x67it' commit -n", "no-verify"),
    ("$'\\x67\\x69\\x74' commit -n", "no-verify"),
    ("$'\\147it' commit -n", "no-verify"),
    ("$'\\u0067it' commit -n", "no-verify"),
    ("$'\\U00000067it' commit -n", "no-verify"),
    ("git commit $'-\\x6e'", "no-verify"),
    ("git commit $'\\055n'", "no-verify"),
    ("git push $'--for\\x63e'", "push-force"),
    ("git $'commit' $'--no-verify'", "no-verify"),
    ("gh $'pr' $'merge'", "gh-pr-merge"),
    # --- (M7): coproc, function ----------------------------------------------------------------------------------------
    ("coproc git commit -n", "no-verify"),
    ("coproc NAME { git commit -n; }", "no-verify"),
    ("coproc NAME { gh pr merge; }", "gh-pr-merge"),
    ("function f { git push --force; }", "push-force"),
    ("function f { git commit -n; } ; f", "no-verify"),
    ("function git_x git push -f", "push-force"),
    # --- (M9): git rebase --exec ---------------------------------------------------------------------------------------
    ("git rebase -x 'git push --force' main", "push-force"),
    ("git rebase --exec 'git commit -n' main", "no-verify"),
    ("git rebase --exec='git push -f' main", "push-force"),
    ("git rebase -i -x'gh pr merge' main", "gh-pr-merge"),
    ("git rebase -ix 'git commit -n' main", "no-verify"),
    ("git rebase --ex 'gh pr merge' main", "gh-pr-merge"),
    ("git rebase -s ours -x 'git push -f' main", "push-force"),
    ("git rebase -x 'bash -c \"git push -f\"' main", "push-force"),
    # --- too nested ----------------------------------------------------------------------------------------
    ("echo " + "$(" * 30 + "ls" + ")" * 30, "too-complex"),
    # --- E10b review: GitHub credentials ------------------------------------------------------
    ("gh auth token", "gh-auth"),
    ("gh auth login", "gh-auth"),
    ("gh auth login --with-token < f", "gh-auth"),
    ("gh auth logout", "gh-auth"),
    ("gh auth switch", "gh-auth"),
    ("gh auth refresh -s workflow", "gh-auth"),
    ("gh auth token --hostname github.com", "gh-auth"),
    ("gh --hostname github.com auth token", "gh-auth"),
    ("gh auth status --show-token", "gh-auth"),
    ("gh auth status -t", "gh-auth"),
    ("gh auth status -at", "gh-auth"),
    ("gh auth status -h github.com -t", "gh-auth"),
    ("gh auth status --show-token --hostname github.com", "gh-auth"),
    ("bash -c 'gh auth token'", "gh-auth"),
    ("echo $(gh auth token)", "gh-auth"),
    ("env gh auth token", "gh-auth"),
    ("GH_TOKEN=x gh pr list", "gh-token-env"),
    ("GITHUB_TOKEN=x gh pr list", "gh-token-env"),
    ("GH_ENTERPRISE_TOKEN=x gh pr list", "gh-token-env"),
    ("GITHUB_ENTERPRISE_TOKEN=x gh pr list", "gh-token-env"),
    ("GH_TOKEN= gh pr list", "gh-token-env"),
    ("GH_TOKEN=$OTHER gh pr list", "gh-token-env"),
    ("GH_TOKEN=x", "gh-token-env"),
    ("FOO=1 GH_TOKEN=x gh pr list", "gh-token-env"),
    ("env GH_TOKEN=x gh pr list", "gh-token-env"),
    ("env -i GH_TOKEN=x gh pr list", "gh-token-env"),
    ("env FOO=1 GITHUB_TOKEN=x gh pr list", "gh-token-env"),
    ("sudo env GH_TOKEN=x gh pr list", "gh-token-env"),
    ("export GH_TOKEN=x", "gh-token-env"),
    ("export FOO=1 GITHUB_TOKEN=x", "gh-token-env"),
    ("declare -x GH_TOKEN=x", "gh-token-env"),
    ("typeset -x GITHUB_ENTERPRISE_TOKEN=x", "gh-token-env"),
    ("readonly GH_TOKEN=x", "gh-token-env"),
    ("export -n GH_TOKEN", "gh-token-env"),
    ("unset GH_TOKEN", "gh-token-env"),
    ("unset -v GITHUB_TOKEN", "gh-token-env"),
    ("unset FOO GH_ENTERPRISE_TOKEN", "gh-token-env"),
    ("env -u GH_TOKEN", "gh-token-env"),
    ("env -u GH_TOKEN gh pr list", "gh-token-env"),
    ("env -uGH_TOKEN gh pr list", "gh-token-env"),
    ("env --unset GH_TOKEN gh pr list", "gh-token-env"),
    ("env --unset=GITHUB_TOKEN gh pr list", "gh-token-env"),
    ("env -i -u GH_TOKEN gh pr list", "gh-token-env"),
    ("env -C /tmp -u GH_TOKEN gh pr list", "gh-token-env"),
    ("bash -c 'GH_TOKEN=x gh pr list'", "gh-token-env"),
    ("bash -c 'unset GH_TOKEN; gh pr list'", "gh-token-env"),
    ("sh -c 'export GITHUB_TOKEN=x'", "gh-token-env"),
    ("eval 'GH_TOKEN=x gh pr list'", "gh-token-env"),
    ("echo ok && GH_TOKEN=x gh pr list", "gh-token-env"),
    ("echo $(GH_TOKEN=x gh pr list)", "gh-token-env"),
    ("env -S 'GH_TOKEN=x gh pr list'", "gh-token-env"),
]

ALLOWED = [
    # --- git commit --------------------------------------------------------------------------------------------
    "git commit",
    'git commit -m "msg"',
    "git commit -m 'msg avec --no-verify'",
    'git commit -m "fix -n option"',
    'git commit -m "msg" -m "second -n"',
    "git commit -mn",  # the message is "n"
    'git commit -m"x -n"',
    'git commit --message="x -n"',
    'git commit --message "x -n"',
    "git commit --message -n",  # -n is the message here
    "git commit -m x -- -n",  # after -- only paths
    "git commit --amend",
    "git commit --amend --no-edit",
    "git commit --amend -m x",
    "git commit -S -m x",
    "git commit -SABCDEF -m x",
    "git commit --gpg-sign -m x",
    "git commit --signoff -m x",
    "git commit -s -m x",
    "git commit --no-gpg-sign -m x",
    "git commit -am x",
    "git commit -a -m x",
    "git commit -F msgfile",
    "git commit -C HEAD",
    "git commit --fixup HEAD~1",
    "git commit --fixup=amend:HEAD~1",
    'git commit --author="A <a@example.invalid>" -m x',
    "git commit --dry-run",
    "git commit --verify -m x",
    "git commit -m \"$(cat <<'EOF'\nTexte avec git push --force et gh pr merge\nEOF\n)\"",
    "git commit -m \"$(cat <<'EOF'\nUne ligne -n\ngit commit --no-verify\nEOF\n)\"",
    "git commit -F - <<EOF\ngit commit -n gh pr merge\nEOF",
    "git -C \"/run/media/pa th: x/dir\" commit -m 'x'",
    "git -c user.name=x commit -m y",
    'cd "/run/media/pebrian/Data/Projects/Guide Or Fade : Your command" && git commit -m x',
    'git commit -m "abc',  # unterminated quote
    # --- git push (current branch is feature) ----------------------------------------------------------------------
    "git push",
    "git push origin",
    "git push -u origin HEAD",
    "git push --set-upstream origin HEAD",
    "git push origin HEAD --set-upstream",
    "git push origin e10-circuit-git-agents",
    "git push -u origin e10-circuit-git-agents",
    "git push origin HEAD:feature",
    "git push origin feature:feature",
    "git push origin feature",
    "git push origin refs/heads/feature",
    "git push --tags",
    "git push origin refs/tags/v1",
    "git push --dry-run",
    "git push -n origin HEAD",
    "git push -v origin HEAD",
    "git push --follow-tags origin HEAD",
    'git push -o "ci.skip" origin HEAD',
    "git push --no-thin origin HEAD",
    "git switch -c feature && git push -u origin HEAD",
    "git switch main && git switch feature && git push -u origin HEAD",
    "git pull origin main",
    "git fetch origin main",
    "git checkout main",
    "git switch main",
    "git merge main",
    "git rebase origin/main",
    "git merge -m 'x --no-verify' main",
    # --- git: other subcommands and reading the configuration ----------------------------------------------------
    "git status",
    "git log --grep=--no-verify",
    "git diff -n",
    "git branch -D old",
    "git reset --hard origin/main",  # not in the scope of the guard
    "git clean -fdx",  # not in the scope of the guard
    "git config user.name x",
    "git config --list",
    "git config core.hooksPath",
    "git config --get core.hooksPath",
    "git config --global --get core.hooksPath",
    "git config get core.hooksPath",
    "git -c user.name=a commit -m b",
    "git add -n .",
    # --- gh --------------------------------------------------------------------------------------------------------------
    'gh pr create --title "x" --body-file f',
    'gh pr create --title "gh pr merge" --body "git commit --no-verify"',
    "gh pr checks --watch",
    "gh pr checks --watch --required",
    "gh pr view",
    "gh pr view 7 --json state",
    "gh pr list",
    "gh pr comment 7 -b 'gh pr merge'",
    "gh pr ready 7",
    "gh pr close 7",
    "gh run view 5",
    "gh run list",
    "gh repo view",
    "gh auth status",
    "gh secret list",
    "gh variable list",
    "gh alias list",
    "gh api repos/o/r/pulls/7/merge",  # GET: is it merged?
    "gh api repos/o/r/pulls/7 --jq .state",
    "gh api repos/o/r/git/refs/heads/x",
    "gh api repos/o/r/rulesets",
    "gh api repos/o/r/branches/main/protection",
    "gh api repos/o/r",
    "gh api -X GET repos/o/r/pulls/7/merge",
    "gh api -X POST repos/o/r/git/refs -f ref=refs/heads/x -f sha=abc",
    "gh api -X POST repos/o/r/issues/7/comments -f body='gh pr merge'",
    "gh api graphql -f query='query { viewer { login } }'",
    "gh api user",
    # --- text that only mentions a forbidden command --------------------------------------------------------------
    'echo "git commit --no-verify"',
    "echo 'gh pr merge'",
    "echo git commit -n",
    "echo gh pr merge --auto",
    'printf "%s\\n" "git push --force"',
    'grep -rn -- "--no-verify" docs/',
    "grep -n 'gh pr merge' docs/technique/ci-cd.md",
    'cat docs/x.md | grep "gh pr merge"',
    'rg "git push --force"',
    "cat <<EOF\ngit commit -n\ngh pr merge\nEOF",
    "cat > f.md <<'EOF'\ngit push --force\ngh pr merge --auto\nEOF",
    "cat > f.md <<-EOF\n\tgit commit -n\n\tEOF",
    "echo a # git commit -n",
    "# git commit -n",
    "command -v git",
    "command -v gh",
    "type git",
    "which gh",
    "bash -c 'echo gh pr merge'",
    'sh -c "echo git commit -n"',
    "bash script.sh",
    "bash -c 'echo hi'",
    "bash ./check.sh --no-verify",
    "ssh host 'git commit -n'",  # remote command, not analysed
    "xargs -n1 echo",
    "env",
    "sudo ls",
    "time ls",
    "timeout 5 sleep 1",
    "nice -n 5 ls",
    # --- review E10: forms that must stay allowed ---------------------------------------------------------------------
    "gh pr merge --help",
    "gh pr merge -h",
    "gh pr merge 7 --help",
    "gh -R o/r pr merge --help",
    "gh api graphql -f query='query { viewer { login } }' -F owner=foo",
    "gh api -X POST repos/o/r/issues/$N/comments -f body=x",
    "gh api -X POST repos/o/r/issues/${N}/comments -f body=x",
    "gh api $URL",
    'gh api "$URL" --jq .state',
    "gh api repos/o/r/contents/README.md",
    "gh api -X GET repos/o/r/contents/README.md",
    "gh api -X=GET repos/o/r/pulls/7/merge",
    "git push origin heads/feature",
    "git push origin HEAD:heads/feature",
    "git push origin feature-main",
    "git push origin mainline",
    "git config alias.ci",
    "git config --get alias.ci",
    "git config --get-all remote.origin.push",
    "git config --get-regexp '^alias[.]'",
    "git config get push.default",
    "git config list",
    "git config --get-colorbool color.ui",
    "git config remove-section foo",
    "git config remote.origin.url https://example.invalid/r.git",
    "git config user.name list",
    "git config --global user.email a@example.invalid",
    "git config --file x.cfg --get alias.ci",
    "git -c core.pager=cat log",  # a key that starts a program: documented limit
    "git -c color.ui=always status",
    "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=user.name GIT_CONFIG_VALUE_0=x git status",
    "echo $'\\x67it commit -n'",
    "echo $'\\u0067h pr merge'",
    "$'\\x65cho' hi",
    "coproc sleep 1",
    "coproc NAME { echo hi; }",
    "function f { echo hi; }",
    "git rebase -x 'make test' main",
    "git rebase --exec 'npm test' main",
    "git rebase -s ours main",
    "git rebase -X theirs main",
    "git rebase --onto main a b",
    "git rebase -i main",
    # --- other commands -----------------------------------------------------------------------------------------------------------
    "ls -la",
    "python3 -m unittest discover -s tools/tests",
    "just check",
    "just tools-test",
    "just hooks-install",
    "terraform plan",
    "",
    "   ",
    "\n",
    ";",
    "&&",
    "(",
    ")",
    "'",
    '"',
    "$(",
    "`",
    "<<",
    "git",
    "gh",
    "git -c",
    "git -C",
    "git commit -m",
    "gh pr",
    "gh api",
    "gh api -X",
    "bash -c",
    # --- E10b review: GitHub credentials, forms that must stay allowed ---------------------
    "gh auth status",
    "gh auth status --hostname github.com",
    "gh auth status --active",
    "gh auth status -h github.com",
    "gh auth status --json hosts",
    "gh auth setup-git",
    "gh auth token --help",
    "gh auth --help",
    'echo "${GH_TOKEN:+set}"',
    'echo "${GITHUB_TOKEN:-unset}"',
    'test -n "$GH_TOKEN" && echo set',
    '[ -z "${GITHUB_TOKEN-}" ] && echo clean',
    "printenv GH_TOKEN >/dev/null && echo set",
    "env | grep -c GH_TOKEN",
    "env -u OTHER gh pr list",
    "env -u GH_TOKEN_NOT gh pr list",
    "env FOO=1 gh pr list",
    "export FOO=1",
    "export PATH=$PATH:/x",
    "unset FOO",
    "unset GH_HOST",
    "GH_HOST=github.com gh pr list",
    "GH_REPO=o/r gh pr list",
    "echo GH_TOKEN=x",
    "grep -rn 'GH_TOKEN=' docs/",
    "git log --grep='GH_TOKEN=x'",
    "echo 'gh auth token'",
    "git commit -m 'gh auth login; export GH_TOKEN=x'",
    "bash -c 'echo \"${GH_TOKEN:+set}\"'",
    "gh pr create --title 'unset GH_TOKEN' --body 'GH_TOKEN=x'",
]


class RuleTableTest(unittest.TestCase):
    def test_blocked_commands(self) -> None:
        for command, expected in BLOCKED:
            with self.subTest(command=command):
                self.assertEqual(rule_of(command), expected)

    def test_allowed_commands(self) -> None:
        for command in ALLOWED:
            with self.subTest(command=command):
                self.assertIsNone(rule_of(command))

    def test_every_rule_has_a_french_explanation(self) -> None:
        rules = {rule for _, rule in BLOCKED}
        for violation in (
            guard.NO_VERIFY,
            guard.PUSH_FORCE,
            guard.PUSH_MIRROR,
            guard.PUSH_DELETE,
            guard.PUSH_ALL,
            guard.PUSH_MAIN,
            guard.PUSH_UNKNOWN,
            guard.HOOKS_PATH,
            guard.GIT_CONFIG,
            guard.PR_MERGE,
            guard.GH_ADMIN,
            guard.GH_API,
            guard.GH_API_OPAQUE,
            guard.GH_AUTH,
            guard.GH_TOKEN_ENV,
            guard.TOO_COMPLEX,
        ):
            self.assertIn(violation.rule, rules)
            self.assertGreater(len(violation.reason), 30)


class CurrentBranchTest(unittest.TestCase):
    """A push with no explicit target is judged on the current branch."""

    def test_push_from_main_without_refspec(self) -> None:
        for command in (
            "git push",
            "git push origin",
            "git push -u origin HEAD",
            "git push origin HEAD",
            "git push origin @",
            "git push --follow-tags",
            "git push -v",
        ):
            with self.subTest(command=command):
                self.assertEqual(rule_of(command, "main"), "push-main")
                self.assertEqual(rule_of(command, "master"), "push-main")
                self.assertIsNone(rule_of(command, "feature"))

    def test_push_with_an_explicit_branch_ignores_the_current_one(self) -> None:
        self.assertIsNone(rule_of("git push origin feature", "main"))
        self.assertIsNone(rule_of("git push origin HEAD:feature", "main"))

    def test_tags_only_push_is_fine_on_main(self) -> None:
        self.assertIsNone(rule_of("git push --tags", "main"))
        self.assertIsNone(rule_of("git push origin --tags", "main"))

    def test_unknown_branch_refuses_a_push_without_explicit_target(self) -> None:
        analyzer = guard.Analyzer(lambda _dirs: None)
        self.assertEqual(analyzer.check("git push").rule, "push-unknown-branch")
        self.assertEqual(len(analyzer.notes), 1)  # read once, noted once
        for command in ("git push -u origin HEAD", "git push origin @", "git push"):
            with self.subTest(command=command):
                self.assertEqual(rule_of(command, None), "push-unknown-branch")

    def test_unknown_branch_does_not_matter_with_an_explicit_target(self) -> None:
        for command in (
            "git push origin feature",
            "git push -u origin e10-circuit-git-agents",
            "git push origin HEAD:feature",
            "git push --tags",
            "git push --dry-run origin feature",
        ):
            with self.subTest(command=command):
                self.assertIsNone(rule_of(command, None))
        self.assertEqual(rule_of("git push origin main", None), "push-main")

    def test_no_lookup_at_all_is_unknown(self) -> None:
        self.assertEqual(guard.Analyzer().check("git push").rule, "push-unknown-branch")

    def test_detached_head_is_not_unknown(self) -> None:
        # ``git branch --show-current`` prints nothing: git itself refuses such a push.
        self.assertIsNone(rule_of("git push", ""))
        self.assertIsNone(rule_of("git push origin HEAD", ""))

    def test_computed_target_is_judged_like_head(self) -> None:
        for command in (
            'git push origin "$BRANCH"',
            "git push origin $BRANCH",
            "git push origin HEAD:$BRANCH",
            "git push -u origin $(git branch --show-current)",
            "git push origin ref-$(date +%s)",
            "git push origin `echo x`",
        ):
            with self.subTest(command=command):
                self.assertIsNone(rule_of(command, "feature"))
                self.assertEqual(rule_of(command, "main"), "push-main")
                self.assertEqual(rule_of(command, None), "push-unknown-branch")

    def test_a_computed_branch_switch_makes_the_branch_unknown(self) -> None:
        self.assertEqual(
            rule_of("git switch $B && git push", "feature"), "push-unknown-branch"
        )
        self.assertEqual(
            rule_of("git switch $B && git switch work && git push", "main"), None
        )
        self.assertEqual(
            rule_of("B=x; git checkout $B; git push origin feature", "x"), None
        )


class PushTargetTest(unittest.TestCase):
    """A bare push also follows the configured target (``%(push:remoteref)``)."""

    def check(self, command: str, remoteref: str | None, branch: str = "feature"):
        calls: list[tuple[tuple[str, ...], str]] = []

        def push_lookup(dirs: tuple[str, ...], name: str) -> str | None:
            calls.append((dirs, name))
            return remoteref

        analyzer = guard.Analyzer(lambda _dirs: branch, push_lookup)
        violation = analyzer.check(command)
        return (violation.rule if violation else None), calls

    def test_bare_push_whose_target_is_main_is_refused(self) -> None:
        for command in ("git push", "git push origin", "git push -u origin"):
            with self.subTest(command=command):
                for ref in ("refs/remotes/origin/main", "refs/remotes/up/master"):
                    self.assertEqual(self.check(command, ref)[0], "push-main")

    def test_bare_push_with_another_or_no_target_is_allowed(self) -> None:
        for ref in ("", "refs/remotes/origin/feature", "refs/remotes/origin/mainline"):
            self.assertEqual(self.check("git push", ref)[0], None)

    def test_unreadable_target_is_unknown_branch(self) -> None:
        rule, _ = self.check("git push", None)
        self.assertEqual(rule, "push-unknown-branch")

    def test_several_refs_are_all_looked_at(self) -> None:
        self.assertEqual(
            self.check("git push", "refs/remotes/o/a\nrefs/remotes/o/main")[0],
            "push-main",
        )

    def test_it_is_read_for_the_current_branch_in_the_right_folder(self) -> None:
        _, calls = self.check("git -C sub push", "")
        self.assertEqual(calls, [(("sub",), "feature")])

    def test_explicit_targets_do_not_read_it(self) -> None:
        for command in (
            "git push origin feature",
            "git push origin HEAD",
            "git push --tags",
        ):
            with self.subTest(command=command):
                rule, calls = self.check(command, "refs/remotes/origin/main")
                self.assertIsNone(rule)
                self.assertEqual(calls, [])

    def test_main_as_current_branch_does_not_need_the_read(self) -> None:
        rule, calls = self.check("git push", "", "main")
        self.assertEqual((rule, calls), ("push-main", []))

    def test_branch_is_read_once_per_directory_list(self) -> None:
        calls: list[tuple[str, ...]] = []

        def lookup(dirs: tuple[str, ...]) -> str:
            calls.append(dirs)
            return "feature"

        guard.Analyzer(lookup).check("git push && git push && git -C ../x push")
        self.assertEqual(calls, [(), ("../x",)])

    def test_dash_c_folders_are_given_to_the_lookup(self) -> None:
        seen: list[tuple[str, ...]] = []

        def lookup(dirs: tuple[str, ...]) -> str:
            seen.append(dirs)
            return "main"

        violation = guard.Analyzer(lookup).check("git -C ../other -C sub push")
        self.assertEqual(violation.rule, "push-main")
        self.assertEqual(seen, [("../other", "sub")])

    def test_switching_to_a_branch_on_the_same_line(self) -> None:
        # Real branch is main, but the line moves to a work branch before pushing.
        self.assertIsNone(
            rule_of("git switch -c work && git push -u origin HEAD", "main")
        )
        self.assertIsNone(rule_of("git checkout -b work; git push", "main"))
        self.assertEqual(rule_of("git switch main && git push", "feature"), "push-main")


class TokenizerTest(unittest.TestCase):
    def words(self, script: str) -> list[list[str]]:
        return [command.words for command in guard.parse_script(script)]

    def test_quotes_and_escapes(self) -> None:
        self.assertEqual(
            self.words("git commit -m 'a b' \"c d\" e\\ f"),
            [["git", "commit", "-m", "a b", "c d", "e f"]],
        )

    def test_operators_split_commands(self) -> None:
        self.assertEqual(
            self.words("a && b || c; d | e & f\ng"),
            [["a"], ["b"], ["c"], ["d"], ["e"], ["f"], ["g"]],
        )

    def test_operators_inside_quotes_do_not_split(self) -> None:
        self.assertEqual(self.words('echo "a && b; c"'), [["echo", "a && b; c"]])
        self.assertEqual(self.words("echo 'a | b'"), [["echo", "a | b"]])

    def test_redirections_are_not_words(self) -> None:
        self.assertEqual(self.words("cmd 2>&1 >out.txt <in.txt a"), [["cmd", "a"]])
        self.assertEqual(self.words("cmd &> log"), [["cmd"]])
        self.assertEqual(self.words("cmd 2 > f"), [["cmd", "2"]])

    def test_comment_only_at_the_start_of_a_word(self) -> None:
        self.assertEqual(self.words("echo a#b #c\nls"), [["echo", "a#b"], ["ls"]])

    def test_substitution_becomes_a_placeholder_and_its_own_command(self) -> None:
        commands = self.words("echo $(date) x")
        self.assertIn(["date"], commands)
        self.assertIn(["echo", guard.PLACEHOLDER, "x"], commands)

    def test_single_quotes_hide_substitutions(self) -> None:
        self.assertEqual(
            self.words("echo '$(git commit -n)'"), [["echo", "$(git commit -n)"]]
        )

    def test_heredoc_body_is_not_parsed_unless_expanded(self) -> None:
        commands = guard.parse_script("cat <<'EOF'\n$(ls)\nEOF\nnext")
        self.assertEqual([c.words for c in commands], [["cat"], ["next"]])
        self.assertEqual(commands[0].stdin, ["$(ls)"])
        expanded = guard.parse_script("cat <<EOF\n$(ls)\nEOF\nnext")
        self.assertIn(["ls"], [c.words for c in expanded])

    def test_heredoc_with_tab_stripping_and_missing_terminator(self) -> None:
        commands = guard.parse_script("cat <<-X\n\ta\n\tX\nnext")
        self.assertEqual([c.words for c in commands], [["cat"], ["next"]])
        unfinished = guard.parse_script("cat <<X\na\nb")
        self.assertEqual(unfinished[0].stdin, ["a\nb"])

    def test_never_raises_on_malformed_input(self) -> None:
        for script in (
            "'",
            '"',
            "$(",
            "`",
            "((",
            "))",
            "<<",
            "\\",
            "$'",
            "a\\",
            "<(",
            "&>",
        ):
            with self.subTest(script=script):
                guard.parse_script(script)

    def test_depth_limit(self) -> None:
        with self.assertRaises(guard.TooComplex):
            guard.parse_script("$(" * (guard.MAX_DEPTH + 2))


class WrapperTest(unittest.TestCase):
    def test_wrapper_options_with_values_are_skipped(self) -> None:
        self.assertEqual(rule_of("sudo -u root -g wheel git push -f"), "push-force")
        self.assertEqual(rule_of("ionice -c 2 -n 4 git push -f"), "push-force")
        self.assertEqual(rule_of("stdbuf -oL git push -f"), "push-force")

    def test_wrapped_harmless_command_is_allowed(self) -> None:
        self.assertIsNone(rule_of("sudo -u root ls -n"))
        self.assertIsNone(rule_of("xargs -I{} echo git commit -n {}"))
        self.assertIsNone(rule_of("env FOO=1 echo git commit -n"))

    def test_command_dash_v_only_describes(self) -> None:
        self.assertIsNone(rule_of("command -v git commit -n"))


class ConfigKeyTest(unittest.TestCase):
    """One function decides which Git configuration keys an agent may not set."""

    def test_forbidden_keys(self) -> None:
        for key in (
            "core.hooksPath",
            " CORE.HOOKSPATH ",
            "alias.ci",
            "Alias.Ci",
            "include.path",
            "includeIf.gitdir:/x/.path",
            "remote.origin.push",
            "remote.my.remote.push",
            "remote.origin.mirror",
            "push.default",
        ):
            with self.subTest(key=key):
                self.assertIsNotNone(guard._forbidden_config_key(key))
        self.assertEqual(
            guard._forbidden_config_key("core.hooksPath"), guard.HOOKS_PATH
        )
        self.assertEqual(guard._forbidden_config_key("alias.x"), guard.GIT_CONFIG)

    def test_other_keys_are_fine(self) -> None:
        for key in (
            "user.name",
            "remote.origin.url",
            "remote.origin.fetch",
            "remote.pushDefault",
            "push.followTags",
            "core.editor",  # starts a program: documented limit
            "core.sshCommand",
            "core.pager",
            "aliases.x",
            "include",
            "",
        ):
            with self.subTest(key=key):
                self.assertIsNone(guard._forbidden_config_key(key))

    def test_every_channel_uses_it(self) -> None:
        # git -c, --config-env (both spellings), GIT_CONFIG_*, git config.
        for command in (
            "git -c alias.x=y status",
            "git --config-env=alias.x=V status",
            "git --config-env alias.x=V status",
            "GIT_CONFIG_KEY_0=alias.x git status",
            "git config alias.x y",
        ):
            with self.subTest(command=command):
                self.assertEqual(rule_of(command), "git-config")


class AnsiCQuotingTest(unittest.TestCase):
    def word(self, quoted: str) -> str:
        (command,) = guard.parse_script("echo " + quoted)
        return command.words[1]

    def test_escapes_are_decoded(self) -> None:
        cases = {
            "$'\\x67it'": "git",
            "$'\\x6'": "\x06",
            "$'\\147'": "g",
            "$'\\1'": "\x01",
            "$'\\u0067'": "g",
            "$'\\U00000067'": "g",
            "$'a\\nb\\tc'": "a\nb\tc",
            "$'\\a\\b\\e\\E\\f\\r\\v'": "\a\b\x1b\x1b\f\r\v",
            "$'it\\'s'": "it's",
            "$'\\\\n'": "\\n",
            "$'\\\"'": '"',
            "$'\\cA'": "\x01",
            "$'\\q'": "\\q",
            "$'\\xzz'": "\\xzz",
            "$'a\\x41b'": "aAb",
        }
        for quoted, expected in cases.items():
            with self.subTest(quoted=quoted):
                self.assertEqual(self.word(quoted), expected)

    def test_nul_ends_the_value_like_bash(self) -> None:
        self.assertEqual(self.word("$'ab\\0cd'"), "ab")
        self.assertEqual(self.word("$'ab\\x00cd'"), "ab")
        self.assertNotIn(guard.PLACEHOLDER, self.word("$'\\x00'") + "x")

    def test_out_of_range_and_unterminated_do_not_raise(self) -> None:
        for script in ("$'\\U99999999'", "$'\\x", "$'\\", "$'\\u", "$'\\c", "$'a"):
            with self.subTest(script=script):
                guard.parse_script("echo " + script)

    def test_the_word_continues_after_the_quote(self) -> None:
        self.assertEqual(self.word("$'\\x67'it"), "git")
        self.assertEqual(self.word("a$'\\x62'c"), "abc")


class GitReaderTest(unittest.TestCase):
    """The ``git`` reads share one time budget."""

    class Clock:
        def __init__(self) -> None:
            self.now = 100.0

        def __call__(self) -> float:
            return self.now

    def reader(self, budget: float = 6.0):
        clock = self.Clock()
        return guard.GitReader(pathlib.Path("."), budget, clock), clock

    def fake_run(self, clock, spent: float, stdout: str = "feature\n"):
        calls: list[dict] = []

        def run(cmd, **kwargs):
            calls.append({"cmd": cmd, **kwargs})
            clock.now += spent
            return subprocess.CompletedProcess(cmd, 0, stdout, "")

        return run, calls

    def test_each_call_is_limited_to_the_remaining_budget(self) -> None:
        reader, clock = self.reader(budget=6)
        run, calls = self.fake_run(clock, spent=2.5)
        with mock.patch.object(guard.subprocess, "run", run):
            self.assertEqual(reader.branch(()), "feature")
            self.assertEqual(reader.branch(("a",)), "feature")
            self.assertEqual(reader.branch(("b",)), "feature")  # 1 s left
            self.assertIsNone(reader.branch(("c",)))  # spent: nothing is run
        self.assertEqual(len(calls), 3)
        self.assertEqual(
            [call["timeout"] for call in calls],
            [guard.GIT_TIMEOUT_SECONDS, guard.GIT_TIMEOUT_SECONDS, 1.0],
        )

    def test_budget_is_shared_by_branch_and_push_target(self) -> None:
        reader, clock = self.reader(budget=2)
        run, calls = self.fake_run(clock, spent=2.5)
        with mock.patch.object(guard.subprocess, "run", run):
            self.assertEqual(reader.branch(()), "feature")
            self.assertIsNone(reader.push_tracking_ref((), "feature"))
        self.assertEqual(len(calls), 1)

    def test_spent_budget_refuses_a_push_without_target(self) -> None:
        reader, clock = self.reader(budget=0)
        analyzer = guard.Analyzer(reader.branch, reader.push_tracking_ref)
        with mock.patch.object(guard.subprocess, "run") as run:
            self.assertEqual(analyzer.check("git push").rule, "push-unknown-branch")
            self.assertIsNone(analyzer.check("git push origin feature"))
        run.assert_not_called()

    def test_timeout_and_failure_are_unknown(self) -> None:
        reader, _ = self.reader()
        with mock.patch.object(
            guard.subprocess, "run", side_effect=subprocess.TimeoutExpired("git", 3)
        ):
            self.assertIsNone(reader.branch(()))
        with mock.patch.object(
            guard.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 128, "", "fatal"),
        ):
            self.assertIsNone(reader.push_tracking_ref((), "feature"))

    def test_push_tracking_ref_command(self) -> None:
        reader, clock = self.reader()
        run, calls = self.fake_run(clock, spent=0.1, stdout="refs/remotes/o/main\n")
        with mock.patch.object(guard.subprocess, "run", run):
            self.assertEqual(
                reader.push_tracking_ref(("sub",), "work"), "refs/remotes/o/main"
            )
        self.assertEqual(
            calls[0]["cmd"][-3:],
            ["for-each-ref", "--format=%(push)", "refs/heads/work"],
        )
        self.assertTrue(calls[0]["cmd"][2].endswith("sub"))

    def test_budget_fits_in_the_hook_timeout(self) -> None:
        self.assertLessEqual(guard.GIT_TIMEOUT_SECONDS, guard.GIT_BUDGET_SECONDS)


class RobustnessTest(unittest.TestCase):
    """Random concatenations of shell tokens: never an exception, always terminates."""

    TOKENS = [
        "git",
        "gh",
        "push",
        "commit",
        "pr",
        "merge",
        "api",
        "config",
        "rebase",
        "-n",
        "--no-verify",
        "-f",
        "--force",
        "--all",
        "--branches",
        "main",
        "HEAD",
        "-c",
        "-C",
        "-x",
        "--exec",
        "-X",
        "PUT",
        "graphql",
        "-F",
        "query=@f",
        "repos/o/r/merges",
        "alias.x=y",
        "core.hooksPath",
        "origin",
        "'",
        '"',
        "`",
        "$(",
        "$'",
        "$'\\x67'",
        "\\",
        "\n",
        ";",
        "&&",
        "||",
        "|",
        "&",
        "(",
        ")",
        "{",
        "}",
        "<<EOF",
        "EOF",
        "<<<",
        "<(",
        ">",
        "2>&1",
        "#",
        "$",
        "${",
        "$((",
        "))",
        " ",
        " ",
        " ",
        "bash -c",
        "eval",
        "env",
        "sudo",
        "xargs",
        "coproc",
        "function",
        "export",
        "GIT_CONFIG_KEY_0=",
        "-c",
        "mise exec --",
        "time",
        "command",
        "\u00e9",
        "\x00",
        "\t",
    ]

    def test_random_commands_never_raise(self) -> None:
        rng = random.Random(20261107)
        started = time.monotonic()
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        env = {"CLAUDE_PROJECT_DIR": root.name}
        for _ in range(3000):
            command = "".join(
                rng.choice(self.TOKENS) for _ in range(rng.randint(1, 25))
            )
            branch = rng.choice(["main", "feature", "", None])
            analyzer = guard.Analyzer(lambda _dirs, b=branch: b, lambda _d, _n: "")
            try:
                analyzer.check(command)
            except Exception as exc:  # pragma: no cover - the failure message
                self.fail(f"{type(exc).__name__} on {command!r}: {exc}")
            payload = json.dumps({"tool_input": {"command": command}})
            code = guard.run(payload, env, lambda _d: "x", io.StringIO())
            self.assertIn(code, (0, 2))
        self.assertLess(time.monotonic() - started, 60)

    def test_random_raw_input_never_raises(self) -> None:
        rng = random.Random(7)
        with tempfile.TemporaryDirectory() as root:
            env = {"CLAUDE_PROJECT_DIR": root}
            for _ in range(500):
                text = "".join(
                    rng.choice(self.TOKENS) for _ in range(rng.randint(0, 10))
                )
                code = guard.run(text, env, lambda _d: "x", io.StringIO())
                self.assertIn(code, (0, 2))

    def test_long_inputs_terminate(self) -> None:
        for command in (
            "git " * 5000,
            "(" * 5000,
            "$(" * 5000,
            "'" * 5001,
            "a|" * 5000,
            "bash -c '" * 200,
            "git push " + "x " * 20000,
            "echo " + "\\" * 10001,
        ):
            started = time.monotonic()
            guard.Analyzer(lambda _d: "feature").check(command)
            self.assertLess(time.monotonic() - started, 10)


class HelpTest(unittest.TestCase):
    def test_help_of_pr_merge_is_allowed_but_not_a_value_that_looks_like_it(
        self,
    ) -> None:
        self.assertIsNone(rule_of("gh pr merge --help"))
        self.assertIsNone(rule_of("gh pr merge -h 7"))
        self.assertEqual(rule_of("gh pr merge -b -h"), "gh-pr-merge")
        self.assertEqual(rule_of("gh pr merge --subject --help 7"), "gh-pr-merge")
        self.assertEqual(rule_of("gh pr merge --body=--help"), "gh-pr-merge")


class LogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.env = {"CLAUDE_PROJECT_DIR": str(self.root)}
        self.log = self.root / ".cache" / "hooks" / "guard.log"

    def hook(self, command, branch: str | None = "feature") -> tuple[int, str]:
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
        return self.run_raw(payload, branch)

    def run_raw(self, text: str, branch: str | None = "feature") -> tuple[int, str]:
        stderr = io.StringIO()
        code = guard.run(text, self.env, lambda _dirs: branch, stderr)
        return code, stderr.getvalue()

    def log_lines(self) -> list[str]:
        return (
            self.log.read_text(encoding="utf-8").splitlines()
            if self.log.exists()
            else []
        )

    def test_allowed_command_leaves_no_trace(self) -> None:
        self.assertEqual(self.hook("ls -la"), (0, ""))
        self.assertEqual(self.log_lines(), [])

    def test_blocked_command_exits_2_explains_in_french_and_is_logged(self) -> None:
        code, message = self.hook("git commit --no-verify -m x")
        self.assertEqual(code, 2)
        self.assertIn("Commande bloquée", message)
        self.assertIn("no-verify", message)
        self.assertIn("garde-fous-bash.md", message)
        self.assertIn("git commit --no-verify -m x", message)
        (line,) = self.log_lines()
        self.assertRegex(line, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d BLOCKED ")
        self.assertIn("rule=no-verify", line)

    def test_long_command_is_truncated_in_log_and_message(self) -> None:
        command = "git commit -n -m " + "x" * 5000
        code, message = self.hook(command)
        self.assertEqual(code, 2)
        self.assertLess(len(message), 1500)
        self.assertLess(len(self.log_lines()[0]), 600)

    def test_multiline_command_is_one_log_line(self) -> None:
        self.hook("echo a\ngit commit -n\necho b")
        self.assertEqual(len(self.log_lines()), 1)

    def test_invalid_json_is_allowed_and_logged(self) -> None:
        for text in ("", "not json", "{", '{"tool_input": '):
            with self.subTest(text=text):
                self.assertEqual(self.run_raw(text), (0, ""))
        self.assertEqual(len(self.log_lines()), 4)
        self.assertTrue(
            all("hook error: invalid JSON" in line for line in self.log_lines())
        )

    def test_missing_or_odd_command_is_allowed_and_logged(self) -> None:
        texts = (
            "{}",
            "[]",
            "null",
            '"ls"',
            '{"tool_input": {}}',
            '{"tool_input": []}',
            '{"tool_input": {"command": 42}}',
            '{"tool_input": {"command": null}}',
        )
        for text in texts:
            with self.subTest(text=text):
                self.assertEqual(self.run_raw(text), (0, ""))
        self.assertEqual(len(self.log_lines()), len(texts))
        self.assertTrue(
            all(
                "hook error: no tool_input.command" in line for line in self.log_lines()
            )
        )

    def test_empty_command_is_allowed_silently(self) -> None:
        self.assertEqual(self.hook(""), (0, ""))
        self.assertEqual(self.log_lines(), [])

    def test_internal_exception_on_a_plain_command_allows_and_is_logged(self) -> None:
        with mock.patch.object(
            guard.Analyzer, "check", side_effect=RuntimeError("boom")
        ):
            self.assertEqual(self.hook("ls -la"), (0, ""))
        (line,) = self.log_lines()
        self.assertIn("hook error", line)
        self.assertIn("boom", line)
        self.assertTrue(line.endswith("command allowed"))

    def test_internal_exception_on_a_git_or_gh_command_refuses(self) -> None:
        for command in ("git status", "cd x && gh pr view", "echo a | git log"):
            with self.subTest(command=command):
                with mock.patch.object(
                    guard.Analyzer, "check", side_effect=RuntimeError("boom")
                ):
                    code, message = self.hook(command)
                self.assertEqual(code, 2)
                self.assertIn("garde-fou en erreur", message)
                self.assertIn("commande git/gh refusée par prudence", message)
                self.assertIn("prévenez l'utilisateur", message)
        self.assertTrue(
            all("hook error" in line and "refused" in line for line in self.log_lines())
        )

    def test_exception_in_the_branch_lookup_refuses_a_git_command(self) -> None:
        def lookup(_dirs):
            raise OSError("no git")

        stderr = io.StringIO()
        code = guard.run(
            json.dumps({"tool_input": {"command": "git push"}}),
            self.env,
            lookup,
            stderr,
        )
        self.assertEqual(code, 2)
        self.assertIn("garde-fou en erreur", stderr.getvalue())
        self.assertIn("hook error", self.log_lines()[0])

    def test_recursion_error_is_an_internal_error_not_a_crash(self) -> None:
        with mock.patch.object(guard, "parse_script", side_effect=RecursionError()):
            self.assertEqual(self.hook("ls"), (0, ""))
            self.assertEqual(self.hook("git commit -n")[0], 2)
        self.assertEqual(len(self.log_lines()), 2)
        self.assertTrue(all("hook error" in line for line in self.log_lines()))

    def test_invalid_json_mentioning_git_or_gh_is_refused(self) -> None:
        for text in (
            '{"tool_input": {"command": "git push --force"',
            "git push --force",
            '{"tool_input": {"command": "gh pr merge 7"}} trailing',
            '{"tool_input": {"command": "x"}, git}',
        ):
            with self.subTest(text=text):
                code, message = self.run_raw(text)
                self.assertEqual(code, 2)
                self.assertIn("garde-fou en erreur", message)
        self.assertEqual(len(self.log_lines()), 4)
        self.assertTrue(
            all(
                "hook error: invalid JSON" in l and "refused" in l
                for l in self.log_lines()
            )
        )

    def test_invalid_json_without_git_or_gh_is_allowed(self) -> None:
        # ``github``, ``digit``, ``gitlab`` are not the words git / gh.
        for text in ('{"tool_input": {"command": "ls', "echo github digit gh_x", "{"):
            with self.subTest(text=text):
                self.assertEqual(self.run_raw(text), (0, ""))
        self.assertTrue(
            all(line.endswith("command allowed") for line in self.log_lines())
        )

    def test_payload_without_command_mentioning_git_is_refused(self) -> None:
        for text in ('"git commit -n"', '{"tool_input": {"cmd": "git push -f"}}'):
            with self.subTest(text=text):
                self.assertEqual(self.run_raw(text)[0], 2)
        self.assertEqual(self.run_raw('{"tool_input": {"command": 42}}'), (0, ""))

    def test_unwritable_stderr_still_blocks(self) -> None:
        class Broken:
            def write(self, _text):
                raise OSError("closed")

        code = guard.run(
            json.dumps({"tool_input": {"command": "gh pr merge"}}),
            self.env,
            None,
            Broken(),
        )
        self.assertEqual(code, 2)

    def test_log_failure_is_ignored(self) -> None:
        (self.root / ".cache").write_text("a file, not a directory", encoding="utf-8")
        self.assertEqual(self.run_raw("not json"), (0, ""))
        self.assertEqual(self.run_raw("git not json")[0], 2)
        self.assertEqual(self.hook("gh pr merge")[0], 2)

    def test_log_is_rotated_beyond_the_limit(self) -> None:
        self.log.parent.mkdir(parents=True)
        self.log.write_text("x" * (guard.LOG_MAX_BYTES + 1), encoding="utf-8")
        guard.log_line(self.root, "new line")
        rotated = self.log.with_name("guard.log.1")
        self.assertTrue(rotated.exists())
        self.assertEqual(len(self.log_lines()), 1)
        self.assertIn("new line", self.log_lines()[0])

    def test_log_line_is_single_line(self) -> None:
        guard.log_line(self.root, "a\nb\r\nc")
        self.assertEqual(len(self.log_lines()), 1)
        self.assertTrue(self.log_lines()[0].endswith("a b c"))

    def test_project_root_defaults_to_the_repository(self) -> None:
        self.assertEqual(guard.project_root({}), REPO_ROOT)
        self.assertEqual(guard.project_root(self.env), self.root.resolve())


@unittest.skipUnless(shutil.which("git"), "git is not installed")
class RealGitTest(unittest.TestCase):
    """Branch lookup with the real git, in a throw-away repository."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = pathlib.Path(self.tmp.name) / "a repo: with space"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("commit", "-q", "--allow-empty", "-m", "init")

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", *args], cwd=self.repo, env=GIT_ENV, check=True, capture_output=True
        )

    def test_lookup_reads_the_current_branch(self) -> None:
        lookup = guard.make_branch_lookup(self.repo)
        self.assertEqual(lookup(()), "main")
        self.git("switch", "-q", "-c", "feature")
        self.assertEqual(lookup(()), "feature")

    def test_lookup_follows_git_dash_c_folders(self) -> None:
        sub = self.repo / "sub"
        sub.mkdir()
        lookup = guard.make_branch_lookup(self.repo.parent)
        self.assertEqual(lookup((str(self.repo),)), "main")
        self.assertEqual(lookup((self.repo.name, "sub")), "main")

    def test_lookup_outside_a_repository_is_none_and_detached_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            self.assertIsNone(guard.make_branch_lookup(pathlib.Path(outside))(()))
        self.git("checkout", "-q", "--detach")
        self.assertEqual(guard.make_branch_lookup(self.repo)(()), "")

    def test_lookup_survives_a_missing_directory(self) -> None:
        lookup = guard.make_branch_lookup(self.repo / "missing")
        self.assertIsNone(lookup(()))

    def add_remote(self) -> pathlib.Path:
        remote = pathlib.Path(self.tmp.name) / "remote.git"
        subprocess.run(
            ["git", "init", "-q", "--bare", str(remote)],
            env=GIT_ENV,
            check=True,
            capture_output=True,
        )
        self.git("remote", "add", "origin", str(remote))
        return remote

    def test_push_tracking_ref_follows_the_configuration(self) -> None:
        self.add_remote()
        reader = guard.GitReader(self.repo)
        self.git("switch", "-q", "-c", "feature")
        self.git("config", "push.default", "current")
        self.git("config", "remote.pushDefault", "origin")
        self.assertEqual(
            reader.push_tracking_ref((), "feature"), "refs/remotes/origin/feature"
        )
        self.git("config", "branch.feature.remote", "origin")
        self.git("config", "branch.feature.merge", "refs/heads/main")
        self.git("config", "push.default", "upstream")
        self.assertEqual(
            reader.push_tracking_ref((), "feature"), "refs/remotes/origin/main"
        )

    def test_push_tracking_ref_without_remote_or_branch_is_empty(self) -> None:
        reader = guard.GitReader(self.repo)
        self.assertEqual(reader.push_tracking_ref((), "main"), "")
        self.assertEqual(reader.push_tracking_ref((), "missing"), "")

    def test_bare_push_to_main_through_upstream_is_refused(self) -> None:
        self.add_remote()
        self.git("switch", "-q", "-c", "feature")
        self.git("config", "branch.feature.remote", "origin")
        self.git("config", "branch.feature.merge", "refs/heads/main")
        self.git("config", "push.default", "upstream")
        payload = {"cwd": str(self.repo), "tool_input": {"command": "git push"}}
        env = {"CLAUDE_PROJECT_DIR": self.tmp.name}
        with mock.patch.dict(os.environ, GIT_ENV):
            self.assertEqual(
                guard.run(json.dumps(payload), env, None, io.StringIO()), 2
            )
            self.git("config", "push.default", "current")
            self.assertEqual(
                guard.run(json.dumps(payload), env, None, io.StringIO()), 0
            )

    def test_run_uses_the_cwd_of_the_payload(self) -> None:
        env = {"CLAUDE_PROJECT_DIR": self.tmp.name}
        payload = {"cwd": str(self.repo), "tool_input": {"command": "git push"}}
        with mock.patch.dict(os.environ, GIT_ENV):
            self.assertEqual(
                guard.run(json.dumps(payload), env, None, io.StringIO()), 2
            )
            self.git("switch", "-q", "-c", "feature")
            self.assertEqual(
                guard.run(json.dumps(payload), env, None, io.StringIO()), 0
            )


class ScriptProcessTest(unittest.TestCase):
    """The script as Claude Code starts it: exit code, nothing on stdout."""

    def run_script(self, stdin: str, root: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=stdin,
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_PROJECT_DIR": root},
            timeout=20,
            check=False,
        )

    def test_blocked_command(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            payload = {
                "tool_name": "Bash",
                "tool_input": {"command": "gh pr merge --auto"},
            }
            result = self.run_script(json.dumps(payload), root)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("Commande bloquée", result.stderr)
            self.assertIn("gh-pr-merge", result.stderr)
            self.assertIn(
                "BLOCKED", (pathlib.Path(root) / ".cache/hooks/guard.log").read_text()
            )

    def test_allowed_command(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            payload = {"tool_input": {"command": 'echo "gh pr merge" && ls'}}
            result = self.run_script(json.dumps(payload), root)
            self.assertEqual(
                (result.returncode, result.stdout, result.stderr), (0, "", "")
            )

    def test_invalid_json_and_empty_stdin(self) -> None:
        for text in ("", "{ not json", "\xff"):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as root:
                result = self.run_script(text, root)
                self.assertEqual(
                    (result.returncode, result.stdout, result.stderr), (0, "", "")
                )
                self.assertTrue(
                    (pathlib.Path(root) / ".cache/hooks/guard.log").exists()
                )

    def test_invalid_json_with_git_is_refused_with_exit_2(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            result = self.run_script('{"tool_input": {"command": "git push -f"', root)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("garde-fou en erreur", result.stderr)
            self.assertIn("prévenez l'utilisateur", result.stderr)
            log = (pathlib.Path(root) / ".cache/hooks/guard.log").read_text()
            self.assertIn("hook error", log)

    def test_utf8_command_with_accents(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            payload = {"tool_input": {"command": "git commit -m 'été « ok »' -n"}}
            result = self.run_script(json.dumps(payload, ensure_ascii=False), root)
            self.assertEqual(result.returncode, 2)


class SettingsTest(unittest.TestCase):
    ORIGINAL_DENY = (
        "Bash(terraform apply:*)",
        "Bash(terraform destroy:*)",
        "Bash(terraform import:*)",
        "Bash(terraform state:*)",
        "Bash(just tf-apply:*)",
        "Read(**/*.tfvars)",
        "Read(**/*.tfstate)",
    )
    NEW_DENY = (
        "Bash(git commit --no-verify:*)",
        "Bash(git commit -n:*)",
        "Bash(git push --force:*)",
        "Bash(git push -f:*)",
        "Bash(gh pr merge:*)",
        "Bash(gh repo delete:*)",
    )
    # E10 review (E-a): pushes to main / master. Textual patterns, not a security
    # boundary (``git -C . push origin main`` slips through); the hook is the check.
    MAIN_PUSH_DENY = (
        "Bash(git push origin main)",
        "Bash(git push origin master)",
        "Bash(git push -u origin main)",
        "Bash(git push -u origin master)",
        "Bash(git push origin HEAD:main)",
        "Bash(git push origin HEAD:master)",
        "Bash(git push * main)",
        "Bash(git push * master)",
        "Bash(git push * HEAD:main)",
        "Bash(git push * HEAD:master)",
        "Bash(git push * refs/heads/main)",
        "Bash(git push * refs/heads/master)",
        "Bash(git push * *:main)",
        "Bash(git push * *:master)",
        "Bash(git push * *:refs/heads/main)",
        "Bash(git push * *:refs/heads/master)",
    )

    def setUp(self) -> None:
        self.settings = json.loads(
            (REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")
        )

    def commands(self, event: str) -> list[dict]:
        return [
            {**hook, "matcher": group.get("matcher")}
            for group in self.settings["hooks"].get(event, [])
            for hook in group["hooks"]
        ]

    def test_pre_tool_use_hook_runs_the_guard_on_bash(self) -> None:
        (entry,) = self.commands("PreToolUse")
        self.assertEqual(entry["matcher"], "Bash")
        self.assertEqual(entry["type"], "command")
        self.assertEqual(
            entry["command"], 'python3 "$CLAUDE_PROJECT_DIR/tools/hooks/guard_bash.py"'
        )
        self.assertTrue((REPO_ROOT / "tools" / "hooks" / "guard_bash.py").is_file())

    def test_guard_can_block(self) -> None:
        (entry,) = self.commands("PreToolUse")
        # Exit code 2 must reach Claude Code: no "|| true" and not asynchronous.
        self.assertNotIn("||", entry["command"])
        self.assertNotIn("async", entry)

    def test_timeout_covers_the_branch_lookup(self) -> None:
        (entry,) = self.commands("PreToolUse")
        self.assertLessEqual(entry["timeout"], 30)
        # The whole budget of git reads, plus margin for the analysis and the start.
        self.assertGreaterEqual(entry["timeout"], guard.GIT_BUDGET_SECONDS + 2)

    def test_other_hooks_are_kept(self) -> None:
        post = self.commands("PostToolUse")
        self.assertEqual(len(post), 1)
        self.assertEqual(post[0]["matcher"], "Write|Edit|MultiEdit")
        self.assertIn("format_on_edit.py", post[0]["command"])
        start = self.commands("SessionStart")
        self.assertEqual(sorted(e["matcher"] for e in start), ["resume", "startup"])
        for entry in start:
            self.assertIn("session_start.py", entry["command"])

    def test_original_deny_rules_are_kept_and_new_ones_added(self) -> None:
        deny = self.settings["permissions"]["deny"]
        for rule in self.ORIGINAL_DENY + self.NEW_DENY + self.MAIN_PUSH_DENY:
            self.assertIn(rule, deny)
        self.assertEqual(len(deny), len(set(deny)))

    def test_no_deny_rule_blocks_every_push(self) -> None:
        # ``Bash(git push *)`` would also forbid the legitimate push of the work branch.
        deny = self.settings["permissions"]["deny"]
        for rule in (
            "Bash(git push *)",
            "Bash(git push:*)",
            "Bash(git *)",
            "Bash(git:*)",
        ):
            self.assertNotIn(rule, deny)

    def test_model_setting_is_kept(self) -> None:
        self.assertEqual(self.settings["model"], "opusplan")


if __name__ == "__main__":
    unittest.main()
