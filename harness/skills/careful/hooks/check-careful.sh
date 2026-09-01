#!/usr/bin/env bash
# check-careful.sh — PreToolUse(Bash) guardrail (AI Factory Kit reference hook).
#
# Ported from gstack /careful (MIT, github.com/garrytan/gstack) — the destructive-pattern
# matcher + safe-allowlist + fail-open logic are verbatim-solid; the ~/.gstack telemetry block
# was DROPPED; stack-specific patterns below are examples — extend for your stack.
#
# Reads the tool-call JSON from stdin, inspects the Bash command, and emits a PreToolUse
# decision: {"permissionDecision":"ask","message":"[careful] …"} to require human confirmation
# on a destructive command, or {} to allow. It only ever asks (warns) — it NEVER hard-denies —
# and it FAILS OPEN: on any extraction/parse problem it allows, so it can never lock the agent
# out of Bash. The value is a deterministic last-line stop before irreversible commands, even
# when an unattended Hermes SOUL forgets to be careful.
#
# Enable (opt-in) by adding to .claude/settings.json:
#   "hooks": { "PreToolUse": [ { "matcher": "Bash",
#       "hooks": [ { "type": "command",
#         "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/check-careful.sh\"" } ] } ] }

# Deliberately NOT using `set -e`: a stray non-zero must never abort before we emit {} (fail-open).
INPUT=$(cat 2>/dev/null || true)

# Extract tool_input.command. Python JSON parse is PRIMARY (correctly handles escaped quotes
# inside the command, e.g. `mysql -e "DELETE FROM t"` — the grep fast-path truncates at the
# first \" and would let a quoted DELETE/DROP evade the SQL guards below). Grep is the fallback
# for the rare host without python3. Either way, a failure leaves CMD empty → allow (fail open).
CMD=$(printf '%s' "$INPUT" | python3 -c 'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("command",""))' 2>/dev/null || true)
if [ -z "$CMD" ]; then
  CMD=$(printf '%s' "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:[[:space:]]*"//;s/"$//' 2>/dev/null || true)
fi
# Could not extract a command → allow (fail open).
if [ -z "$CMD" ]; then echo '{}'; exit 0; fi

CMD_LOWER=$(printf '%s' "$CMD" | tr '[:upper:]' '[:lower:]' 2>/dev/null || true)

# --- Safe exception: rm -r/-rf whose every target is a throwaway build/dep dir → allow ---
if printf '%s' "$CMD" | grep -qE 'rm\s+(-[a-zA-Z]*r[a-zA-Z]*\s+|--recursive\s+)' 2>/dev/null; then
  SAFE_ONLY=true
  RM_ARGS=$(printf '%s' "$CMD" | sed -E 's/.*rm[[:space:]]+(-[a-zA-Z]+[[:space:]]+)*//;s/--recursive[[:space:]]*//' 2>/dev/null || true)
  for target in $RM_ARGS; do
    case "$target" in
      */node_modules|node_modules|*/\.next|\.next|*/dist|dist|*/__pycache__|__pycache__|*/\.cache|\.cache|*/build|build|*/\.turbo|\.turbo|*/coverage|coverage|*/bin|bin|*/tmp|tmp) ;;
      -*) ;; # flag, skip
      *) SAFE_ONLY=false; break ;;
    esac
  done
  if [ "$SAFE_ONLY" = true ]; then echo '{}'; exit 0; fi
fi

WARN=""

# rm -r / rm -rf / rm --recursive (non-allowlisted target)
if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'rm\s+(-[a-zA-Z]*r|--recursive)' 2>/dev/null; then
  WARN="recursive delete (rm -r) — permanently removes files."
fi
# SQL DROP TABLE / DATABASE
if [ -z "$WARN" ] && printf '%s' "$CMD_LOWER" | grep -qE 'drop\s+(table|database|schema)' 2>/dev/null; then
  WARN="SQL DROP — permanently deletes database objects."
fi
# SQL TRUNCATE
if [ -z "$WARN" ] && printf '%s' "$CMD_LOWER" | grep -qE '\btruncate\b' 2>/dev/null; then
  WARN="SQL TRUNCATE — deletes all rows from a table."
fi
# SQL DELETE / UPDATE without a WHERE clause (Nexus: tenant data safety)
if [ -z "$WARN" ] && printf '%s' "$CMD_LOWER" | grep -qE '\b(delete\s+from|update)\b' 2>/dev/null && ! printf '%s' "$CMD_LOWER" | grep -qE '\bwhere\b' 2>/dev/null; then
  WARN="SQL DELETE/UPDATE without WHERE — affects every row (no tenant_id filter)."
fi
# golang-migrate destructive: down / force / drop
if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'migrate\b.*\b(down|force|drop)\b' 2>/dev/null; then
  WARN="golang-migrate down/force/drop — can roll a schema past a destructive step (data loss)."
fi
# docker compose down -v / docker volume rm — nukes mysql_data/redis_data persistent volumes
if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE '(docker(\s+compose|-compose)\s+down\s+.*(-v|--volumes))|(docker\s+volume\s+rm)' 2>/dev/null; then
  WARN="docker compose down -v / volume rm — destroys MySQL/Redis data volumes."
fi
# git force-push
if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'git\s+push\s+.*(-f\b|--force)' 2>/dev/null; then
  WARN="git force-push — rewrites remote history; collaborators may lose work."
fi
# git reset --hard
if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'git\s+reset\s+--hard' 2>/dev/null; then
  WARN="git reset --hard — discards all uncommitted changes."
fi
# git checkout . / git restore .
if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'git\s+(checkout|restore)\s+\.' 2>/dev/null; then
  WARN="git checkout/restore . — discards all uncommitted working-tree changes."
fi
# kubectl delete
if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'kubectl\s+delete' 2>/dev/null; then
  WARN="kubectl delete — removes Kubernetes resources; may impact production."
fi
# docker force-remove / system prune
if [ -z "$WARN" ] && printf '%s' "$CMD" | grep -qE 'docker\s+(rm\s+-f|system\s+prune)' 2>/dev/null; then
  WARN="docker force-remove / prune — may delete running containers or cached images."
fi

if [ -n "$WARN" ]; then
  WARN_ESCAPED=$(printf '%s' "$WARN" | sed 's/\\/\\\\/g;s/"/\\"/g' 2>/dev/null || printf '%s' "$WARN")
  printf '{"permissionDecision":"ask","message":"[careful] Destructive: %s"}\n' "$WARN_ESCAPED"
else
  echo '{}'
fi
exit 0
