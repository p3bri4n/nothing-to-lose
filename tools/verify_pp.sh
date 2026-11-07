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

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

sub="$1"
shift
case "$sub" in
  versions) cmd_versions "$@" ;;
  format) cmd_format "$@" ;;
  *)
    echo "verify_pp.sh: unknown subcommand '$sub'" >&2
    usage
    exit 2
    ;;
esac
