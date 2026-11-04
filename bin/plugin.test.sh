#!/usr/bin/env bash
# Test for the Claude Code plugin install: the manifests in harness/.claude-plugin/ and
# .claude-plugin/, and harness/hooks/hooks.json. The wiring is run for real, under sh, because
# a green manifest proves nothing about a guard that does not fire: a plain `bash <missing file>`
# exits 127, which the host treats as a non-blocking error.
#
# `claude plugin validate` runs when `claude` is on PATH, and is reported as skipped otherwise
# (CI has no Claude Code).
#
# Run: bash bin/plugin.test.sh      Exit 0 = all green.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0; FAIL=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ok()   { PASS=$((PASS+1)); }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL  %s\n' "$1"; }
same() { if [ "$2" = "$3" ]; then ok; else bad "$1: want [$2], got [$3]"; fi; } # same <label> <want> <got>

json() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(eval(sys.argv[2]))" "$1" "$2"; }

echo "== manifests =="
PJ="$ROOT/harness/.claude-plugin/plugin.json"
MJ="$ROOT/.claude-plugin/marketplace.json"
same "plugin.json version is VERSION" "$(cat "$ROOT/VERSION")" "$(json "$PJ" 'd["version"]')"
same "marketplace lists one plugin" 1 "$(json "$MJ" 'len(d["plugins"])')"
same "marketplace plugin name" "$(json "$PJ" 'd["name"]')" "$(json "$MJ" 'd["plugins"][0]["name"]')"
same "marketplace source" ./harness "$(json "$MJ" 'd["plugins"][0]["source"]')"

echo "== hooks.json is the template's wiring, pointed at the plugin's copy =="
python3 - "$ROOT" <<'PY' || FAIL=$((FAIL+1))
import json, os, sys
root = sys.argv[1]
t = json.load(open(os.path.join(root, "harness/settings.json.template")))["hooks"]["PreToolUse"]
p = json.load(open(os.path.join(root, "harness/hooks/hooks.json")))["hooks"]["PreToolUse"]
def path_free(cmd):
    # Only the shim's path and the wording of the repair hint may differ.
    return cmd.split('"${CLAUDE_PLUGIN_ROOT}/skills/careful/hooks/check-careful.sh"')[-1].split(
        '"$CLAUDE_PROJECT_DIR/.claude/hooks/check-careful.sh"')[-1].split("[careful] BLOCKED")[0]
want = [(e["matcher"], h["timeout"], path_free(h["command"])) for e in t for h in e["hooks"]]
got = [(e["matcher"], h["timeout"], path_free(h["command"])) for e in p for h in e["hooks"]]
sys.exit(0 if want == got and len(p) == 2 else print("  FAIL  hooks.json drifted from the template:", got))
PY

echo "== the registered command, run as the host runs it =="
CMD="$(json "$ROOT/harness/hooks/hooks.json" 'd["hooks"]["PreToolUse"][0]["hooks"][0]["command"]')"
run() { # run <plugin root> <payload>: prints "<exit> <decision>"
  out=$(printf '%s' "$2" | CLAUDE_PLUGIN_ROOT="$1" sh -c "$CMD" 2>/dev/null); rc=$?
  printf '%s %s' "$rc" "$(printf '%s' "$out" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("hookSpecificOutput",{}).get("permissionDecision","pass"))
except Exception: print("none")')"
}
payload() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]}))' "$1" "$TMP"; }
same "rm -rf ~ is denied"        "0 deny" "$(run "$ROOT/harness" "$(payload 'rm -rf ~' )")"
same "force-push main is denied" "0 deny" "$(run "$ROOT/harness" "$(payload 'git push --force origin main')")"
same "ls passes"                 "0 pass" "$(run "$ROOT/harness" "$(payload 'ls')")"
same "disabling the plugin is denied" "0 deny" "$(run "$ROOT/harness" "$(payload 'claude plugin disable ai-factory-kit')")"
same "missing shim blocks"       "2 none" "$(run "$TMP/no-such-plugin" "$(payload 'ls')")"
mkdir -p "$TMP/empty/skills/careful/hooks"; : > "$TMP/empty/skills/careful/hooks/check-careful.sh"
same "empty shim blocks"         "2 none" "$(run "$TMP/empty" "$(payload 'ls')")"

echo "== claude plugin validate =="
if command -v claude >/dev/null 2>&1; then
  claude plugin validate "$ROOT/harness" >"$TMP/v1" 2>&1 && ok || { bad "validate harness"; cat "$TMP/v1"; }
  claude plugin validate "$ROOT" >"$TMP/v2" 2>&1 && ok || { bad "validate marketplace"; cat "$TMP/v2"; }
else
  echo "  skipped: no claude on PATH"
fi

echo
echo "passed $PASS, failed $FAIL"
[ "$FAIL" -eq 0 ]
