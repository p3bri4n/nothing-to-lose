#!/usr/bin/env bash
# PP verification entry point. Subcommands are added as the PP steps land.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat >&2 <<USAGE
Usage: tools/verify_pp.sh <subcommand> [args...]

Subcommands:
  versions   Check installed tool versions against mise.toml
USAGE
}

cmd_versions() {
  python "$root/tools/check_tool_versions.py" "$@"
}

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

sub="$1"
shift
case "$sub" in
  versions) cmd_versions "$@" ;;
  *)
    echo "verify_pp.sh: unknown subcommand '$sub'" >&2
    usage
    exit 2
    ;;
esac
