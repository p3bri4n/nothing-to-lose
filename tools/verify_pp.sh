#!/usr/bin/env bash
# PP verification entry point. Subcommands are added as the PP steps land.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat >&2 <<USAGE
Usage: tools/verify_pp.sh <subcommand> [args...]

Subcommands:
  versions   Check installed tool versions against mise.toml
  format     Check the PostToolUse formatting hook (C2, automatic part)
  secrets    Check the Git pre-commit hook and gitleaks in a temporary repository (C1)
  merge-barrier [--agents-account NAME] [--repo OWNER/REPO]
             Read-only check of the server-side merge barrier (E10b, decision 0021):
             the ruleset requires an approval and the owner bypasses by pull request only;
             NAME (or AGENTS_ACCOUNT) has the write role. Run by the user; needs gh and a token.
USAGE
}

cmd_versions() {
  python3 "$root/tools/check_tool_versions.py" "$@"
}

# Configuration files the hook refuses to format with while they differ from HEAD
# (keep in sync with GUARDED_CONFIG_FILES in tools/hooks/format_on_edit.py).
guarded_config_files=(mise.toml mise.local.toml .prettierrc.json rust-toolchain.toml)

# C2 (automatic part): the format-on-edit hook reformats a badly formatted file,
# leaves Markdown and disabled runs alone, refuses to format while the tool
# configuration differs from HEAD, and exits 0 on absurd input.
# The scratch directory is created inside the project (the hook ignores anything
# outside it, and anything ignored by Git) and removed on exit.
cmd_format() {
  local hook="$root/tools/hooks/format_on_edit.py"
  local fixtures="$root/tools/tests/fixtures/format"
  local status=0 name file out code dirty

  # The hook formats nothing while the configuration differs from HEAD, so the
  # checks below could not succeed: skip, loudly, instead of failing.
  dirty="$(git -C "$root" --no-optional-locks status --porcelain --ignored=matching \
    --untracked-files=all -- "${guarded_config_files[@]}")"
  if [[ -n $dirty ]]; then
    echo "SKIP C2 (automatic part): the tool configuration differs from HEAD" >&2
    echo "     (commit or discard these changes, then rerun):" >&2
    echo "$dirty" >&2
    return 0
  fi

  # Globals on purpose: the EXIT trap runs after the function has returned.
  scratch="$(mktemp -d "$root/.verify-pp-format.XXXXXX")"
  guard_probe=""
  trap 'rm -rf "$scratch"; [[ -z $guard_probe ]] || rm -f "$guard_probe"' EXIT

  # JSON of a simulated PostToolUse event for the file $1.
  payload_for() {
    python3 -c 'import json, sys; print(json.dumps({"tool_name": "Write", "tool_input": {"file_path": sys.argv[1]}}))' "$1"
  }

  # Run the hook on a simulated PostToolUse payload for $1; sets $out and $code.
  run_hook() {
    local payload
    payload="$(payload_for "$1")"
    code=0
    out="$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$root" python3 "$hook")" || code=$?
  }

  for name in bad.py bad.toml bad.tf bad.sh bad.yaml bad.json bad.rs; do
    file="$scratch/$name"
    cp "$fixtures/$name" "$file"
    if python3 "$root/tools/fmt.py" --check "$file" >/dev/null 2>&1; then
      echo "FAIL $name: the fixture is already formatted (nothing to prove)" >&2
      status=1
      continue
    fi
    run_hook "$file"
    if [[ $code -ne 0 || -n $out ]]; then
      echo "FAIL $name: hook exit $code, stdout '$out'" >&2
      status=1
    elif ! python3 "$root/tools/fmt.py" --check "$file" >/dev/null 2>&1; then
      echo "FAIL $name: not formatted after the hook" >&2
      status=1
    else
      echo "ok   $name reformatted"
    fi
  done

  # Markdown is never touched.
  file="$scratch/note.md"
  printf '#  Title\n\n*  item   with  spaces\n' >"$file"
  cp "$file" "$scratch/note.md.orig"
  run_hook "$file"
  if [[ $code -ne 0 ]] || ! cmp -s "$file" "$scratch/note.md.orig"; then
    echo "FAIL note.md: changed or hook exit $code" >&2
    status=1
  else
    echo "ok   note.md unchanged"
  fi

  # NTL_FORMAT_HOOK=off leaves a badly formatted file alone.
  file="$scratch/off.py"
  cp "$fixtures/bad.py" "$file"
  cp "$file" "$scratch/off.py.orig"
  code=0
  payload_for "$file" |
    NTL_FORMAT_HOOK=off CLAUDE_PROJECT_DIR="$root" python3 "$hook" || code=$?
  if [[ $code -ne 0 ]] || ! cmp -s "$file" "$scratch/off.py.orig"; then
    echo "FAIL NTL_FORMAT_HOOK=off: file changed or hook exit $code" >&2
    status=1
  else
    echo "ok   NTL_FORMAT_HOOK=off respected"
  fi

  # An untracked mise.local.toml (ignored by Git, but present) makes the hook refuse
  # to format, and say so in its log. The empty file is inert for mise and removed
  # on exit.
  local log="$root/.cache/hooks/format.log" lines_before=0
  if [[ -e $root/mise.local.toml ]]; then
    echo "FAIL guard: mise.local.toml exists (should have been caught above)" >&2
    status=1
  else
    file="$scratch/guard.py"
    cp "$fixtures/bad.py" "$file"
    cp "$file" "$scratch/guard.py.orig"
    [[ ! -f $log ]] || lines_before="$(wc -l <"$log")"
    guard_probe="$root/mise.local.toml"
    : >"$guard_probe"
    run_hook "$file"
    rm -f "$guard_probe"
    guard_probe=""
    if [[ $code -ne 0 ]] || ! cmp -s "$file" "$scratch/guard.py.orig"; then
      echo "FAIL guard: file changed or hook exit $code with mise.local.toml present" >&2
      status=1
    elif ! tail -n +"$((lines_before + 1))" "$log" 2>/dev/null | grep -q "formatting refused.*mise.local.toml"; then
      echo "FAIL guard: no 'formatting refused' line in $log" >&2
      status=1
    else
      echo "ok   configuration guard: nothing formatted while mise.local.toml is present"
    fi
  fi

  # Absurd input: always exit 0 and print nothing.
  for payload in '' 'not json' '{' '[]' '{"tool_input":{"file_path":123}}' '{"tool_input":{"file_path":"/nonexistent/a.py"}}'; do
    code=0
    out="$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$root" python3 "$hook")" || code=$?
    if [[ $code -ne 0 || -n $out ]]; then
      echo "FAIL absurd input '$payload': exit $code, stdout '$out'" >&2
      status=1
    fi
  done
  [[ $status -eq 0 ]] && echo "ok   absurd inputs: exit 0, no output"

  if [[ $status -eq 0 ]]; then
    echo "OK C2 (automatic part)"
  else
    echo "FAILED C2 (automatic part)" >&2
  fi
  return "$status"
}

# C1 (E7): the Git pre-commit hook blocks a commit that contains a secret or a broken
# documentation link, accepts a clean one, and `just secrets-scan` finds a secret that
# slipped in with --no-verify. Everything happens in a temporary repository (mktemp -d)
# holding copies of .githooks/, .gitleaks.toml, justfile, mise.toml and tools/.
# The fake token is generated here, at run time: it is written only inside the
# temporary repository (deleted on exit by the trap), never in the real repository,
# never printed, never pushed.
cmd_secrets() {
  local status=0 mise_bin repo token head out code partial=0
  local gitenv=(env GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
    GIT_AUTHOR_NAME=verify GIT_AUTHOR_EMAIL=verify@example.invalid
    GIT_COMMITTER_NAME=verify GIT_COMMITTER_EMAIL=verify@example.invalid)

  if command -v mise >/dev/null 2>&1; then
    mise_bin="$(command -v mise)"
  elif [[ -x ${HOME:-}/.local/bin/mise ]]; then
    mise_bin="$HOME/.local/bin/mise"
  else
    echo "FAILED C1: mise not found" >&2
    return 1
  fi

  # `tmp` is global on purpose: the EXIT trap runs after the function has returned.
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  # A space in the path checks the quoting of the hook and of the recipes.
  repo="$tmp/repo with space"
  # MISE_TRUSTED_CONFIG_PATHS is a ':'-separated list: a path containing ':' cannot be trusted.
  if [[ $repo == *:* ]]; then
    echo "FAILED C1: the temporary path contains ':' (set TMPDIR to a path without ':')" >&2
    return 1
  fi
  mkdir -p "$repo/docs"
  cp -R "$root/.githooks" "$root/tools" "$repo/"
  cp "$root/.gitleaks.toml" "$root/justfile" "$root/mise.toml" "$repo/"
  rm -rf "$repo/tools/__pycache__" "$repo/tools/hooks/__pycache__" "$repo/tools/tests/__pycache__"
  printf '# Docs\n\nNo link here.\n' >"$repo/docs/README.md"
  export MISE_TRUSTED_CONFIG_PATHS="$repo"

  git_repo() { "${gitenv[@]}" git -C "$repo" "$@"; }
  in_repo() { (cd "$repo" && "${gitenv[@]}" "$@"); }

  # Token: provider prefix followed by random alphanumerics (36, like a GitHub PAT).
  token="ghp_$(python3 -c 'import secrets, string; print("".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(36)))')"

  git_repo init -q
  git_repo config core.hooksPath .githooks

  # Run `git commit` in the temporary repository; sets $out (stdout and stderr) and $code.
  try_commit() {
    code=0
    out="$(git_repo commit -q "$@" 2>&1)" || code=$?
  }
  # No leaked token in what the tools printed.
  no_token_in_output() {
    if [[ $out == *"$token"* ]]; then
      echo "FAIL $1: the token appears in the output (--redact not effective)" >&2
      status=1
    fi
  }

  # 0. Baseline commit: the hook accepts a clean repository (and runs on 'mise exec').
  git_repo add -A
  try_commit -m "baseline"
  if [[ $code -ne 0 ]]; then
    echo "FAIL baseline: the clean commit was refused (exit $code): $out" >&2
    echo "FAILED C1" >&2
    return 1
  fi
  echo "ok   baseline commit accepted by the hook"

  # 1. Clean history: secrets-scan passes.
  code=0
  out="$(in_repo "$mise_bin" exec -- just secrets-scan 2>&1)" || code=$?
  if [[ $code -ne 0 ]]; then
    echo "FAIL secrets-scan on a clean history: exit $code: $out" >&2
    status=1
  else
    echo "ok   secrets-scan passes on a clean history"
  fi

  # 2. A commit containing the token is blocked.
  head="$(git_repo rev-parse HEAD)"
  printf 'token = "%s"\n' "$token" >"$repo/leak.txt"
  git_repo add leak.txt
  try_commit -m "leak"
  if [[ $code -eq 0 || "$(git_repo rev-parse HEAD)" != "$head" ]]; then
    echo "FAIL leak: the commit containing a secret was not blocked" >&2
    status=1
  elif [[ $out != *"leaks found"* ]]; then
    echo "FAIL leak: refused, but not by gitleaks: $out" >&2
    status=1
  else
    echo "ok   commit with a secret blocked"
  fi
  no_token_in_output "leak"

  # 3. Witness commit: without the secret, the commit is accepted.
  git_repo rm -q --cached leak.txt
  rm -f "$repo/leak.txt"
  printf 'hello\n' >"$repo/witness.txt"
  git_repo add witness.txt
  try_commit -m "witness"
  if [[ $code -ne 0 ]]; then
    echo "FAIL witness: a clean commit was refused (exit $code): $out" >&2
    status=1
  else
    echo "ok   witness commit accepted"
  fi

  # 4. A broken documentation link blocks the commit.
  head="$(git_repo rev-parse HEAD)"
  printf '[broken](does-not-exist.md)\n' >"$repo/docs/broken.md"
  git_repo add docs/broken.md
  try_commit -m "broken link"
  if [[ $code -eq 0 || "$(git_repo rev-parse HEAD)" != "$head" ]]; then
    echo "FAIL broken link: the commit was not blocked" >&2
    status=1
  elif [[ $out != *"does-not-exist.md"* ]]; then
    echo "FAIL broken link: refused, but not because of the link: $out" >&2
    status=1
  else
    echo "ok   commit with a broken link blocked"
  fi
  git_repo rm -q --cached docs/broken.md
  rm -f "$repo/docs/broken.md"

  # 5. Closed by default: without mise (empty HOME, minimal PATH), the commit is refused.
  if PATH=/usr/bin:/bin command -v mise >/dev/null 2>&1; then
    echo "SKIP closed by default: mise is in /usr/bin or /bin on this machine" >&2
    partial=1
  else
    head="$(git_repo rev-parse HEAD)"
    printf 'another\n' >"$repo/another.txt"
    git_repo add another.txt
    code=0
    out="$(HOME="$tmp/empty-home" PATH=/usr/bin:/bin "${gitenv[@]}" git -C "$repo" commit -q -m "no mise" 2>&1)" || code=$?
    if [[ $code -eq 0 || "$(git_repo rev-parse HEAD)" != "$head" ]]; then
      echo "FAIL closed by default: the commit passed without mise" >&2
      status=1
    elif [[ $out != *"mise not found"* ]]; then
      echo "FAIL closed by default: refused, but without the expected message: $out" >&2
      status=1
    else
      echo "ok   closed by default: commit refused when mise is missing"
    fi
    git_repo rm -q --cached another.txt
    rm -f "$repo/another.txt"
  fi

  # 6. --no-verify lets the secret in; secrets-scan then detects it.
  printf 'token = "%s"\n' "$token" >"$repo/leak.txt"
  git_repo add leak.txt
  try_commit --no-verify -m "leak, bypassing the hook"
  if [[ $code -ne 0 ]]; then
    echo "FAIL --no-verify: the commit failed (exit $code): $out" >&2
    status=1
  else
    code=0
    out="$(in_repo "$mise_bin" exec -- just secrets-scan 2>&1)" || code=$?
    if [[ $code -eq 0 ]]; then
      echo "FAIL secrets-scan: the secret committed with --no-verify was not detected" >&2
      status=1
    else
      echo "ok   --no-verify bypasses the hook, secrets-scan detects the secret"
    fi
    no_token_in_output "secrets-scan"
  fi

  if [[ $status -eq 0 && $partial -eq 1 ]]; then
    echo "OK C1 (partial: closed-by-default check skipped)"
  elif [[ $status -eq 0 ]]; then
    echo "OK C1"
  else
    echo "FAILED C1" >&2
  fi
  return "$status"
}

# E10b: read-only check of the merge barrier through the GitHub API (GET requests only).
# Never merges, approves or writes anything. Exit codes: see tools/check_merge_barrier.py.
cmd_merge_barrier() {
  python3 "$root/tools/check_merge_barrier.py" "$@"
}

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

sub="$1"
shift
case "$sub" in
  versions) cmd_versions "$@" ;;
  format) cmd_format "$@" ;;
  secrets) cmd_secrets "$@" ;;
  merge-barrier) cmd_merge_barrier "$@" ;;
  *)
    echo "verify_pp.sh: unknown subcommand '$sub'" >&2
    usage
    exit 2
    ;;
esac
