#!/usr/bin/env bash
# check-careful.sh — pre-execution guardrail (AI Factory Kit reference hook). Thin shim.
#
# The matcher lives in check-careful.py next to this file; adopter rules live in careful.json
# next to it. This shim exists so the host's hook config can invoke one shell command, and so
# that a missing or broken Python degrades to ASK rather than to a silent pass.
#
# Installed copy: .claude/hooks/ (adopt.py puts it there; it is the only copy that runs).
# Wiring: harness/settings.json.template — registered by `python3 factory/bin/adopt.py
# --register-guard`, which wraps this shim so that a MISSING or BROKEN shim blocks (exit 2)
# instead of failing open. Do not hand-copy a wiring snippet from here: the v1.3.0 snippet in
# this header registered the Bash matcher alone and left the guard-file tier unreachable.
#
# Matcher logic after gstack /careful (MIT, github.com/garrytan/gstack); telemetry dropped,
# stack patterns are examples. Read ../SKILL.md before enabling this on a new host.
#
# Test: bash check-careful.test.sh

# Whole stdin through a bash builtin, so nothing on PATH is needed to get this far.
IFS= read -r -d '' INPUT || true

# Nothing on stdin: nothing to inspect, pass.
if [ -z "$INPUT" ]; then echo '{}'; exit 0; fi

DIR=${BASH_SOURCE[0]%/*}
[ "$DIR" = "${BASH_SOURCE[0]}" ] && DIR=.
DIR=$(cd "$DIR" && pwd)

# python3 first; `python` for hosts (Windows) where that is the Python 3 on PATH.
for PY in python3 python; do
  OUT=$(printf '%s' "$INPUT" | "$PY" "$DIR/check-careful.py" 2>/dev/null)
  RC=$?
  if [ $RC -eq 0 ] && [ -n "$OUT" ]; then
    printf '%s\n' "$OUT"
    exit 0
  fi
done

# The matcher could not run (no Python 3, syntax error, crash). ASK — never pass silently.
# A guard that disappears with its interpreter is the failure this file was rewritten to end.
printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"[careful] the guardrail could not run (check-careful.py failed or Python 3 is missing) — asking instead of allowing."}}'
exit 0
