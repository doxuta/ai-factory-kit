#!/usr/bin/env bash
# check-careful.sh — pre-execution guardrail (AI Factory Kit reference hook). Thin shim.
#
# The matcher lives in check-careful.py next to this file. This shim exists so the host's
# hook config can keep invoking a shell command, and so that a missing or broken python3
# degrades to ASK rather than to silent allow.
#
# Ported from gstack /careful (MIT, github.com/garrytan/gstack); telemetry dropped,
# stack patterns are examples. See ../SKILL.md — read the enforcement section BEFORE
# enabling this on a new host.
#
# Wire (Claude Code example — check your host's own contract):
#   "hooks": { "PreToolUse": [ { "matcher": "Bash",
#       "hooks": [ { "type": "command",
#         "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/check-careful.sh\"" } ] } ] }
#
# Test: bash check-careful.test.sh

INPUT=$(cat 2>/dev/null || true)

# Nothing on stdin: nothing to inspect, allow.
if [ -z "$INPUT" ]; then echo '{}'; exit 0; fi

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OUT=$(printf '%s' "$INPUT" | python3 "$DIR/check-careful.py" 2>/dev/null)
RC=$?

if [ $RC -eq 0 ] && [ -n "$OUT" ]; then
  printf '%s\n' "$OUT"
  exit 0
fi

# The matcher could not run (no python3, syntax error, crash). ASK — do NOT allow.
# A guard that silently disappears when its interpreter is missing is the failure mode
# this file was rewritten to end.
printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"[careful] the guardrail could not run (check-careful.py failed or python3 is missing) — asking instead of allowing."}}'
exit 0
