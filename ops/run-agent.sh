#!/usr/bin/env bash
#
# run-agent.sh — invoke a Claude agent headlessly on the VPS.
#
# Usage:  ./run-agent.sh <agent>
#   where <agent> matches a prompt file in ops/prompts/<agent>.md
#   e.g.  ./run-agent.sh research      ./run-agent.sh ops-monitor
#
# Reads configuration from ops.env (see ops.env.example). Designed to be run
# by the systemd timers in ops/systemd/, but works standalone for testing.
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Load config ---
ENV_FILE="${OPS_ENV_FILE:-$HERE/ops.env}"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
fi

AGENT="${1:-}"
if [[ -z "$AGENT" ]]; then
  echo "usage: run-agent.sh <agent>  (prompt file: ops/prompts/<agent>.md)" >&2
  exit 2
fi

PROMPT_FILE="$HERE/prompts/${AGENT}.md"
if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "no prompt file for agent '$AGENT' at $PROMPT_FILE" >&2
  exit 2
fi

# claude binary + flags. Autonomy flag differs by claude-code version; set
# CLAUDE_ARGS in ops.env. A common full-auto (no human approval) invocation is:
#   CLAUDE_ARGS="--permission-mode bypassPermissions"
# Run `claude --help` on the box to confirm the flag for your version.
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CLAUDE_ARGS="${CLAUDE_ARGS:---permission-mode acceptEdits}"

# Where the agent operates (repos should be cloned under here).
WORKDIR="${OPS_WORKDIR:-$HOME}"
cd "$WORKDIR"

TS() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "$(TS) [run-agent:$AGENT] $*"; }

log "starting agent '$AGENT' in $WORKDIR"

# Sanity: fail fast with a clear message if auth is missing.
if [[ -z "${ANTHROPIC_API_KEY:-}" && ! -d "${HOME}/.claude" && ! -d "${XDG_CONFIG_HOME:-$HOME/.config}/claude" ]]; then
  log "ERROR: no ANTHROPIC_API_KEY and no claude-code login found. See ops/README.md."
  exit 1
fi

set +e
# shellcheck disable=SC2086
"$CLAUDE_BIN" -p "$(cat "$PROMPT_FILE")" $CLAUDE_ARGS
CODE=$?
set -e

if [[ $CODE -eq 0 ]]; then
  log "agent '$AGENT' finished OK"
else
  log "agent '$AGENT' exited non-zero ($CODE)"
fi
exit $CODE
