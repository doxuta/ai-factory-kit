#!/usr/bin/env bash
# Scenario test for bin/adopt.py and bin/check-links.py.
#
# WHY THIS FILE EXISTS: adopt.py is the one step every adoption runs, and each earlier version
# of it failed on a layout nobody tested: a Spec Kit project (refused), a project that had once
# clicked "don't ask again" (refused), a re-run (refused), a CRLF checkout (a hook that blocks
# every tool call), a plain clone (an embedded repo that teammates receive empty). Each scenario
# below is one of those layouts, run in its own temp dir, in both directions where a direction
# exists: it must do the thing, and it must refuse or warn when it should.
#
# Most scenarios adopt a small FIXTURE kit built below, so they test adopt.py's mechanics and
# do not break while the real harness is being edited. Two scenarios use the real kit: "live
# kit" (a fresh adoption of this working tree must be clean) and "v1.3.2 upgrade" (a real old
# adoption, upgraded by this adopt.py). The latter needs v1.3.2 in this clone's history: in a
# shallow clone it prints SKIP, which is a visible gap, not a pass.
#
# Run: bash bin/adopt.test.sh       Exit 0 = all green.   PYTHON=python3.8 picks an interpreter.

set -u
KIT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
PASS=0; FAIL=0; SKIP=0
TMP="$(mktemp -d 2>/dev/null || mktemp -d -t adopttest)"
trap 'rm -rf "$TMP"' EXIT

# Isolate git from the caller's config (a global core.hooksPath would change the answers).
export HOME="$TMP/home"; mkdir -p "$HOME"
export GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.invalid
export GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.invalid
git config --global init.defaultBranch main
git config --global protocol.file.allow always
export PYTHONIOENCODING=utf-8

OUT="$TMP/out"; RC=0

pass() { PASS=$((PASS+1)); }
fail() {
  FAIL=$((FAIL+1)); printf '  FAIL  %s\n' "$1"
  if [ -n "${2:-}" ] && [ -f "$2" ]; then sed -n '1,40p' "$2" | sed 's/^/        /'; fi
}
# t <label> <command...>: passes when the command exits 0.
t() {
  local label="$1"; shift
  if "$@" >"$TMP/t.out" 2>&1; then pass; else fail "$label" "$TMP/t.out"; fi
}
# adopt <project> <kit-dir-in-project> [args...]: runs that kit's adopt.py from the project root.
adopt() {
  local p="$1" k="$2"; shift 2
  (cd "$p" && "$PY" "$k/bin/adopt.py" "$@") >"$OUT" 2>&1; RC=$?
}
rc()   { if [ "$RC" = "$1" ]; then pass; else fail "$2 (want exit $1, got $RC)" "$OUT"; fi; }
has()  { if grep -q -- "$2" "$OUT"; then pass; else fail "$1: output lacks '$2'" "$OUT"; fi; }
hasnt() { if grep -q -- "$2" "$OUT"; then fail "$1: output has '$2'" "$OUT"; else pass; fi; }
links() { (cd "$1" && shift && "$PY" "$KIT/bin/check-links.py" "$@"); }
newfiles() {
  find "$1" -path "$1/factory" -prune -o -path "$1/.git" -prune -o -name '*.factory-new' -print
}
nonew() { local f; f="$(newfiles "$2")"; if [ -z "$f" ]; then pass; else fail "$1: unexpected $f"; fi; }
nocr() {
  if grep -rl "$(printf '\r')" "$@" >"$TMP/cr.out" 2>/dev/null; then fail "CR found" "$TMP/cr.out"
  else pass; fi
}
same() { if cmp -s "$2" "$3"; then pass; else fail "$1: $2 differs from $3"; fi; }
exe()  { if [ -x "$2" ]; then pass; else fail "$1: $2 is not executable"; fi; }
absent() { if [ -e "$2" ]; then fail "$1: $2 exists"; else pass; fi; }
present() { if [ -e "$2" ]; then pass; else fail "$1: $2 missing"; fi; }
# contains/lacks match a fixed string (grep -F), so link syntax needs no escaping.
contains() { if grep -qF -- "$3" "$2" 2>/dev/null; then pass; else fail "$1: $2 lacks '$3'"; fi; }
lacks() { if grep -qF -- "$3" "$2" 2>/dev/null; then fail "$1: $2 has '$3'"; else pass; fi; }

# ---------------------------------------------------------------- the fixture kit
# Small, but shaped like the real one: every install mapping and every link rewrite adopt.py
# performs has at least one link here that exercises it.
mkfixture() {
  local k="$1"
  mkdir -p "$k/bin" "$k/harness/agents" "$k/harness/rules" "$k/harness/skills/careful/hooks" \
    "$k/harness/skills/spec-first" "$k/gates/hooks" "$k/gates/ci" "$k/constitution" \
    "$k/speckit/overrides" "$k/model"
  cp "$KIT/bin/adopt.py" "$KIT/bin/check-links.py" "$k/bin/"
  echo "9.9.9" > "$k/VERSION"
  cat > "$k/harness/CLAUDE.md.template" <<'EOF'
# [PROJECT] - always-loaded context
Constitution: [the ratified constitution](../constitution/constitution-template.md).
Rules: [`architecture`](rules/architecture.md) · [`data`](rules/data.md) ·
[`api-conventions`](rules/api-conventions.md) · [`workflow`](rules/workflow.md).
Gates: [GATES](../gates/GATES.md) and [the chain runner](../gates/run-chain.sh).
Flow: [SPEC-FLOW §3](../model/SPEC-FLOW.md#3-plan). Guard: [careful](skills/careful/SKILL.md).
EOF
  cat > "$k/harness/HARNESS.md" <<'EOF'
<!-- WHO READS ME: fixture. I POINT TO: skills/ -->
# Harness
Skills in [`skills/`](skills/), agents in [`agents/`](agents/), the [kit root](../).
The [hooks dir](skills/careful/hooks/) and [settings](settings.json.template).
`[not a link](nowhere.md)` stays as it is.
EOF
  cat > "$k/harness/settings.json.template" <<'EOF'
{
  "_comment": ["fixture template"],
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash|PowerShell",
        "hooks": [ { "type": "command", "timeout": 10,
          "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/check-careful.sh\" || exit 2" } ] },
      { "matcher": "Write|Edit|MultiEdit|NotebookEdit",
        "hooks": [ { "type": "command", "timeout": 10,
          "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/check-careful.sh\" || exit 2" } ] }
    ]
  }
}
EOF
  cat > "$k/harness/agents/tester.md" <<'EOF'
---
name: tester
description: Fixture agent. Use when a feature needs third-person acceptance.
---
<!-- WHO READS ME: fixture -->
Acceptance per [GATES §3](../../gates/GATES.md); data rules in [data](../rules/data.md).
EOF
  local r
  for r in architecture data api-conventions workflow; do
    cat > "$k/harness/rules/$r.md" <<EOF
---
paths:
  - "src/**"
---
<!-- WHO READS ME: fixture rule $r -->
# $r
EOF
  done
  local rl="$k/harness/rules"
  echo 'See [`api-conventions.md`](api-conventions.md).' >> "$rl/architecture.md"
  echo 'Checklist: [data.md](data.md), [api](api-conventions.md), [arch](architecture.md).' \
    >> "$rl/workflow.md"
  echo 'Authority: [constitution](../../constitution/constitution-template.md).' >> "$rl/data.md"
  cat > "$k/harness/skills/careful/SKILL.md" <<'EOF'
---
name: careful
description: Fixture guard skill.
---
The matcher is [check-careful.py](hooks/check-careful.py); config in
[careful.json](hooks/careful.json); wiring in [the template](../../settings.json.template).
Gate doctrine: [GATES §6](../../../gates/GATES.md).
EOF
  cat > "$k/harness/skills/spec-first/SKILL.md" <<'EOF'
---
name: spec-first
description: Fixture skill.
---
The [constitution](../../../constitution/constitution-template.md) Article IV.
EOF
  local hk="$k/harness/skills/careful/hooks"
  printf '#!/usr/bin/env bash\ncat >/dev/null\necho "{}"\n' > "$hk/check-careful.sh"
  printf '#!/usr/bin/env python3\nprint("{}")\n' > "$hk/check-careful.py"
  printf '#!/usr/bin/env bash\necho ok\n' > "$hk/check-careful.test.sh"
  printf '{\n  "protected_branches": [],\n  "extra_ask": []\n}\n' > "$hk/careful.json"
  printf '# GATES\n' > "$k/gates/GATES.md"
  printf '#!/usr/bin/env bash\nset -euo pipefail\necho "nothing to check yet"\n' \
    > "$k/gates/check-plan-sync.sh"
  printf '#!/usr/bin/env bash\necho ok\n' > "$k/gates/check-plan-sync.test.sh"
  printf '#!/usr/bin/env bash\nset -euo pipefail\necho chain\n' > "$k/gates/run-chain.sh"
  printf '# slots\nformat: TODO\ndoc-sync: ./gates/check-plan-sync.sh\n' > "$k/gates/chain.conf.example"
  printf '#!/usr/bin/env bash\nexec ./gates/run-chain.sh\n' > "$k/gates/hooks/pre-commit"
  printf 'name: factory-gates\non: [push]\n' > "$k/gates/ci/github-actions.yml"
  cat > "$k/constitution/constitution-template.md" <<'EOF'
<!-- WHO READS ME: fixture -->
# [PROJECT] Constitution
Flow: [SPEC-FLOW](../model/SPEC-FLOW.md). Review: [tester](../harness/agents/tester.md).
Data: [data rule](../harness/rules/data.md). Harness: [HARNESS §3](../harness/HARNESS.md).
EOF
  cat > "$k/speckit/overrides/spec-template.md" <<'EOF'
---
feature: [NNN-name]
status: draft
epic: [epic]
---
# Feature Specification
EOF
  printf '# SPEC-FLOW\n## 3 Plan\n' > "$k/model/SPEC-FLOW.md"
  chmod +x "$k"/harness/skills/careful/hooks/*.sh "$k"/harness/skills/careful/hooks/*.py \
    "$k"/gates/*.sh "$k/gates/hooks/pre-commit"
}

# gitkit <dir>: turn a kit dir into a committed git repo (a submodule source).
gitkit() { (cd "$1" && git init -q && git add -A && git commit -qm fixture); }
# vendor <kit> <project> [name]: plain copy of a kit into a project, no .git.
vendor() {
  mkdir -p "$2/${3:-factory}"
  (cd "$1" && tar --exclude=.git -cf - .) | (cd "$2/${3:-factory}" && tar -xf -)
}

# crlf <file> / lf <file>: rewrite line endings (crlf is what core.autocrlf=true does on checkout).
eol() {
  "$PY" -c 'import sys
p, to = sys.argv[1], sys.argv[2].encode()
d = open(p, "rb").read().replace(b"\r\n", b"\n")
open(p, "wb").write(d.replace(b"\n", b"\r\n") if to == b"crlf" else d)' "$1" "$2"
}
crlf() { eol "$1" crlf; }
lf()   { eol "$1" lf; }

FX="$TMP/fixture"; mkfixture "$FX"; gitkit "$FX"

echo "== usage =="
adopt "$KIT" . --help; rc 0 "--help exits 0"
has "--help" "--register-guard"; has "--help" "cli .*api-conventions, data"
p="$TMP/u"; mkdir -p "$p"; vendor "$FX" "$p"
adopt "$p" factory --profile nope; rc 2 "unknown profile is a usage error"
adopt "$p" factory --without nosuchrule; rc 2 "unknown --without rule is a usage error"
adopt "$p" factory --check --upgrade; rc 2 "--check takes no other option"
mkdir -p "$p/sub"; adopt "$p/sub" ../factory; rc 2 "run from a subdirectory: kit is outside"
has "subdirectory" "must live inside the project"
absent "subdirectory writes nothing" "$p/sub/.claude"

echo "== fresh git repo + submodule =="
p="$TMP/sub"; git init -q "$p"
(cd "$p" && git submodule add -q "file://$FX" factory) >/dev/null 2>&1
adopt "$p" factory; rc 0 "submodule adoption"
hasnt "submodule" "embedded"
exe "hook installed" "$p/.claude/hooks/check-careful.sh"
exe "hook installed" "$p/.claude/hooks/check-careful.py"
present "careful.json installed" "$p/.claude/hooks/careful.json"
absent "no second copy of the guard" "$p/.claude/skills/careful/hooks"
present "CLAUDE.md from the template" "$p/.claude/CLAUDE.md"
absent "template not installed under its own name" "$p/.claude/CLAUDE.md.template"
present "manifest" "$p/.claude/.factory-manifest.json"
same "chain.conf seeded from the example" "$p/gates/chain.conf" "$FX/gates/chain.conf.example"
exe "gate installed" "$p/gates/run-chain.sh"
absent "GATES.md stays in the kit" "$p/gates/GATES.md"
absent "pre-commit only with --install-git-hook" "$p/gates/hooks/pre-commit"
absent "CI only with --ci" "$p/.github"
present "spec override" "$p/.specify/templates/overrides/spec-template.md"
present "constitution override" "$p/.specify/templates/overrides/constitution-template.md"
present "constitution seeded" "$p/.specify/memory/constitution.md"
t "0 dead links after adoption" links "$p" .claude gates .specify
C="$p/.claude"; M="$C/.factory-manifest.json"; K="$p/.specify/memory/constitution.md"
contains "harness link to the constitution -> the project's" "$C/skills/spec-first/SKILL.md" \
  "](../../../.specify/memory/constitution.md)"
contains "CLAUDE.md constitution link" "$C/CLAUDE.md" "](../.specify/memory/constitution.md)"
contains "rule link to the constitution" "$C/rules/data.md" "](../../.specify/memory/constitution.md)"
contains "skill link to a hook -> .claude/hooks" "$C/skills/careful/SKILL.md" \
  "](../../hooks/check-careful.py)"
contains "skill link to a kit doc -> factory/" "$C/skills/careful/SKILL.md" \
  "](../../../factory/gates/GATES.md)"
contains "link to an installed gate stays local" "$C/CLAUDE.md" "](../gates/run-chain.sh)"
contains "fragment kept" "$C/CLAUDE.md" "](../factory/model/SPEC-FLOW.md#3-plan)"
contains "dir link to the hooks" "$C/HARNESS.md" "](hooks/)"
contains "link to the kit root" "$C/HARNESS.md" "](../factory/)"
contains "code span untouched" "$C/HARNESS.md" '`[not a link](nowhere.md)`'
contains "seeded constitution -> kit doc" "$K" "](../../factory/model/SPEC-FLOW.md)"
contains "seeded constitution -> installed agent" "$K" "](../../.claude/agents/tester.md)"
contains "manifest records kit version" "$M" '"kit_version": "9.9.9"'
contains "manifest: CLAUDE.md is adopter-filled" "$M" '"adopter-filled"'
contains "manifest records the kit commit" "$M" "\"kit_commit\": \"$(git -C "$FX" rev-parse HEAD)\""
contains ".gitattributes pins hooks" "$p/.gitattributes" '.claude/hooks/*.sh text eol=lf'
contains ".gitattributes pins gates" "$p/.gitattributes" 'gates/*.sh text eol=lf'
contains ".gitattributes pins the git hook" "$p/.gitattributes" 'gates/hooks/pre-commit text eol=lf'
lacks ".gitattributes never pins a whole tree (binaries)" "$p/.gitattributes" 'gates/** text'
lacks ".gitattributes never pins a whole directory (review 2)" "$p/.gitattributes" 'gates/hooks/* text'
absent "settings template not installed (register-guard reads the kit's)" \
  "$p/.claude/settings.json.template"
contains "careful skill links the kit's template" "$C/skills/careful/SKILL.md" \
  "](../../../factory/harness/settings.json.template)"
contains "constitution override: links written for .specify/memory/" \
  "$p/.specify/templates/overrides/constitution-template.md" "](../../factory/model/SPEC-FLOW.md)"
same "override and seed are one text (what /speckit-constitution copies)" \
  "$p/.specify/templates/overrides/constitution-template.md" "$K"
adopt "$p" factory --check; rc 0 "--check after a clean adoption"
t "the submodule stays clean (no __pycache__, no edits)" \
  test -z "$(git -C "$p/factory" status --porcelain)"

echo "== re-run is idempotent =="
cp "$p/.claude/.factory-manifest.json" "$TMP/m1"; cp "$p/.gitattributes" "$TMP/g1"
adopt "$p" factory; rc 0 "second run"
has "second run" "installed   0"
nonew "second run" "$p"
same "manifest unchanged" "$TMP/m1" "$p/.claude/.factory-manifest.json"
same ".gitattributes unchanged" "$TMP/g1" "$p/.gitattributes"
echo "filled by the adopter" >> "$p/.claude/CLAUDE.md"
awk '/^format:/ { print "format: npx prettier --check ."; next } { print }' \
  "$p/gates/chain.conf" > "$TMP/cc" && cat "$TMP/cc" > "$p/gates/chain.conf"
adopt "$p" factory; rc 0 "re-run after the adopter filled files"
nonew "adopter-filled files are not re-offered" "$p"
contains "CLAUDE.md kept" "$p/.claude/CLAUDE.md" "filled by the adopter"
adopt "$p" factory --check; rc 0 "--check with filled adopter files"

echo "== plain vendored copy =="
p="$TMP/vend"; git init -q "$p"; vendor "$FX" "$p"
adopt "$p" factory; rc 0 "vendored adoption"; hasnt "vendored" "embedded"
contains "no kit commit without factory/.git" "$p/.claude/.factory-manifest.json" \
  '"kit_commit": null'

echo "== non-git directory =="
p="$TMP/nogit"; mkdir -p "$p"; vendor "$FX" "$p"
adopt "$p" factory; rc 0 "non-git adoption"
t "0 dead links" links "$p" .claude gates .specify

echo "== kit vendored under another name =="
p="$TMP/other"; mkdir -p "$p/vendor"; vendor "$FX" "$p" vendor/ai-factory-kit
adopt "$p" vendor/ai-factory-kit; rc 0 "kit at vendor/ai-factory-kit"
contains "links point at the real kit dir" "$p/.claude/skills/careful/SKILL.md" \
  "](../../../vendor/ai-factory-kit/gates/GATES.md)"
t "0 dead links" links "$p" .claude gates .specify

echo "== pre-existing .claude/settings.local.json =="
p="$TMP/local"; mkdir -p "$p/.claude"; vendor "$FX" "$p"
printf '{"permissions":{"allow":["Bash(npm test)"]}}\n' > "$p/.claude/settings.local.json"
cp "$p/.claude/settings.local.json" "$TMP/sl"
adopt "$p" factory; rc 0 "adopt next to settings.local.json"
same "settings.local.json untouched" "$TMP/sl" "$p/.claude/settings.local.json"
nonew "no .factory-new" "$p"
absent "settings.json not created" "$p/.claude/settings.json"

echo "== Spec Kit first =="
p="$TMP/speckit"; vendor "$FX" "$p"
mkdir -p "$p/.claude/skills/speckit-x" "$p/.specify/templates" "$p/.specify/memory"
printf '%s\n' '---' 'name: speckit-x' 'description: x' '---' \
  'See [plan](../../../.specify/templates/plan.md).' > "$p/.claude/skills/speckit-x/SKILL.md"
printf '# [PROJECT_NAME] Constitution\n' > "$p/.specify/templates/constitution-template.md"
cp "$p/.specify/templates/constitution-template.md" "$p/.specify/memory/constitution.md"
cp "$p/.claude/skills/speckit-x/SKILL.md" "$TMP/sk"
adopt "$p" factory; rc 0 "adopt after specify init"
same "speckit skill untouched" "$TMP/sk" "$p/.claude/skills/speckit-x/SKILL.md"
has "speckit" "unfilled constitution scaffold"
contains "scaffold replaced by the kit seed" "$p/.specify/memory/constitution.md" "SPEC-FLOW"
nonew "no .factory-new" "$p"
has "a foreign file's dead link is a warning" "WARN .*speckit-x/SKILL.md"
p="$TMP/speckit2"; mkdir -p "$p/.specify/memory"; vendor "$FX" "$p"
printf '# Ratified - ours\n' > "$p/.specify/memory/constitution.md"
adopt "$p" factory; rc 0 "adopt next to a filled constitution"
contains "filled constitution kept" "$p/.specify/memory/constitution.md" "Ratified - ours"
present "kit seed offered" "$p/.specify/memory/constitution.md.factory-new"

echo "== collision -> .factory-new (and gates/ is not overwritten) =="
p="$TMP/coll"; mkdir -p "$p/.claude/agents" "$p/gates"; vendor "$FX" "$p"
printf '%s\n' '---' 'name: tester' 'description: ours' '---' 'OUR AGENT' > "$p/.claude/agents/tester.md"
printf '#!/usr/bin/env bash\necho MY-OWN-GATE\n' > "$p/gates/check-plan-sync.sh"
adopt "$p" factory; rc 0 "collision is not a failure"
has "collision" "REVIEW  2 file"
has "a colliding name gets the rename hint" "rename yours to keep both"
contains "our agent kept" "$p/.claude/agents/tester.md" "OUR AGENT"
contains "our gate kept" "$p/gates/check-plan-sync.sh" "MY-OWN-GATE"
present "kit agent offered" "$p/.claude/agents/tester.md.factory-new"
present "kit gate offered" "$p/gates/check-plan-sync.sh.factory-new"
adopt "$p" factory; rc 0 "re-run with pending reviews"
hasnt "re-run does not re-list reviewed-once files" "REVIEW"
adopt "$p" factory --check; rc 1 "--check fails while .factory-new awaits review"
has "--check" "awaiting review"
exe "a script's .factory-new keeps the execute bit" "$p/gates/check-plan-sync.sh.factory-new"
rm "$p/.claude/agents/tester.md.factory-new" "$p/gates/check-plan-sync.sh.factory-new"
adopt "$p" factory --check; rc 1 "keeping your own gate under a kit gate's name fails --check"
has "enforcement drift is a FAIL" "FAIL  gates/check-plan-sync.sh: differs from the kit's copy"
hasnt "an agent is adopter-filled: its fill is not 'modified locally'" "tester.md: kit-owned"
mv "$p/gates/check-plan-sync.sh" "$p/gates/check-my-sync.sh"
adopt "$p" factory; rc 0 "after renaming ours, adopt.py restores the kit's gate"
contains "kit gate back" "$p/gates/check-plan-sync.sh" "nothing to check yet"
contains "ours kept under its own name" "$p/gates/check-my-sync.sh" "MY-OWN-GATE"
chmod +x "$p/gates/check-my-sync.sh"
adopt "$p" factory --check; rc 0 "--check after the adopter decided"

echo "== profiles drop the right rules and leave no dead link =="
for prof in full backend frontend cli library data embedded iac llm; do
  case "$prof" in
    frontend) drop="data" ;; data) drop="api-conventions" ;;
    cli|library|embedded|iac) drop="api-conventions data" ;; *) drop="" ;;
  esac
  p="$TMP/prof-$prof"; mkdir -p "$p"; vendor "$FX" "$p"
  adopt "$p" factory --profile "$prof"; rc 0 "profile $prof"
  for r in architecture data api-conventions workflow; do
    case " $drop " in
      *" $r "*) absent "$prof drops $r" "$p/.claude/rules/$r.md" ;;
      *) present "$prof keeps $r" "$p/.claude/rules/$r.md" ;;
    esac
  done
  t "profile $prof: 0 dead links" links "$p" .claude gates .specify
done
contains "dropped rule link becomes text" "$TMP/prof-cli/.claude/CLAUDE.md" \
  '[`architecture`](rules/architecture.md) · `data` ·'
contains "profile recorded" "$TMP/prof-cli/.claude/.factory-manifest.json" '"profile": "cli"'
p="$TMP/prof-cli"
adopt "$p" factory; rc 0 "re-run with no flags keeps the recorded profile"
absent "dropped rule not re-added" "$p/.claude/rules/data.md"
nonew "no .factory-new" "$p"
adopt "$p" factory --profile cli --without workflow; rc 0 "--without adds to the profile"
present "workflow left on disk (never deleted)" "$p/.claude/rules/workflow.md"
has "--without on a re-run" "the profile drops this rule but it is on disk"
p="$TMP/prof-w"; mkdir -p "$p"; vendor "$FX" "$p"
adopt "$p" factory --without workflow,data; rc 0 "--without only"
absent "--without workflow" "$p/.claude/rules/workflow.md"
absent "--without data" "$p/.claude/rules/data.md"
t "--without: 0 dead links" links "$p" .claude gates .specify
p="$TMP/prof-full"; rm "$p/.claude/rules/architecture.md"
adopt "$p" factory; rc 0 "a rule the adopter deleted"
absent "deleted rule not re-created" "$p/.claude/rules/architecture.md"
has "deleted rule" "rule architecture was deleted after install"
adopt "$p" factory --check; rc 1 "--check finds links to the deleted rule"
has "--check names the dead link" "dead link -> rules/architecture.md"

echo "== CRLF source -> LF installed =="
p="$TMP/crlf"; mkdir -p "$p"; vendor "$FX" "$p"
find "$p/factory" -type f ! -path '*/factory/bin/*' | while read -r f; do crlf "$f"; done
t "fixture really is CRLF" \
  grep -q "$(printf '\r')" "$p/factory/harness/skills/careful/hooks/check-careful.sh"
adopt "$p" factory; rc 0 "adopt a CRLF kit"
nocr "$p/.claude" "$p/gates" "$p/.specify"
t "installed hook runs" sh -c "echo '{}' | bash '$p/.claude/hooks/check-careful.sh'"
t "0 dead links" links "$p" .claude gates .specify
p="$TMP/crlf2"; mkdir -p "$p"; vendor "$FX" "$p"
printf '#!/usr/bin/env bash\necho a\recho b\n' > "$p/factory/gates/run-chain.sh"
adopt "$p" factory; rc 1 "a lone CR in a script is refused"
has "lone CR" "carriage return"
absent "refusal writes nothing" "$p/.claude"

echo "== frontmatter at byte 0 is asserted =="
p="$TMP/fm1"; mkdir -p "$p"; vendor "$FX" "$p"
printf '<!-- WHO READS ME -->\n---\nname: tester\ndescription: x\n---\n' \
  > "$p/factory/harness/agents/tester.md"
adopt "$p" factory; rc 1 "agent with a comment before its frontmatter"
has "agent" "treats it as documentation"; absent "nothing written" "$p/.claude"
p="$TMP/fm2"; mkdir -p "$p"; vendor "$FX" "$p"
printf '%s\n' '---' 'name: tester' '---' 'body' > "$p/factory/harness/agents/tester.md"
adopt "$p" factory; rc 1 "agent without description"; has "agent" "lacks description"
p="$TMP/fm3"; mkdir -p "$p"; vendor "$FX" "$p"
printf '<!-- header -->\n\n---\npaths:\n  - "x"\n---\n' > "$p/factory/harness/rules/data.md"
adopt "$p" factory; rc 1 "rule with its paths: below a comment"
has "rule" "loads in every session"
adopt "$p" factory --profile cli; rc 0 "the same kit with that rule dropped by the profile"
p="$TMP/fm4"; mkdir -p "$p"; vendor "$FX" "$p"
printf '# no frontmatter\n' > "$p/factory/harness/skills/spec-first/SKILL.md"
adopt "$p" factory; rc 1 "skill without frontmatter"
p="$TMP/fm5"; mkdir -p "$p"; vendor "$FX" "$p"
printf '%s\n' '---' '# the fence is three dashes: ---' 'paths:' '  - "x"' '---' 'body' \
  > "$p/factory/harness/rules/data.md"
adopt "$p" factory; rc 1 "three dashes inside a rule's frontmatter (Claude Code ends it there)"
has "dashes" "three dashes inside the frontmatter (line 2)"; absent "nothing written" "$p/.claude"

echo "== --check exit codes =="
p="$TMP/chk"; mkdir -p "$p"; vendor "$FX" "$p"
adopt "$p" factory --check; rc 1 "--check on a project never adopted"
has "not adopted" "not adopted"
adopt "$p" factory; adopt "$p" factory --check; rc 0 "--check clean"
cp "$p/.claude/hooks/check-careful.py" "$TMP/hk"; rm "$p/.claude/hooks/check-careful.py"
adopt "$p" factory --check; rc 1 "--check: a hook is missing"; has "missing hook" "now missing"
adopt "$p" factory; rc 0 "adopt restores it"
same "restored" "$TMP/hk" "$p/.claude/hooks/check-careful.py"
printf '#!/usr/bin/env bash\r\necho x\r\n' > "$p/gates/my-gate.sh"
adopt "$p" factory --check; rc 0 "CR in a file the kit did not write is a warning"
has "CR warning" "WARN .*my-gate.sh"
crlf "$p/gates/run-chain.sh"
adopt "$p" factory --check; rc 1 "--check: CR in an installed gate"; has "CR" "carriage return"
rm "$p/gates/my-gate.sh"; lf "$p/gates/run-chain.sh"
adopt "$p" factory --check; rc 0 "--check after the CR is fixed"
cp "$p/.claude/HARNESS.md" "$TMP/harness.md"; echo "[dead](nope.md)" >> "$p/.claude/HARNESS.md"
adopt "$p" factory --check; rc 1 "--check: a dead link in an installed doc"
has "dead link" "dead link -> nope.md"
has "a local edit to a kit-owned file" "modified locally"
adopt "$p" factory --upgrade; rc 1 "--upgrade keeps the local edit, and its check still fails"
contains "local edit kept" "$p/.claude/HARNESS.md" "[dead](nope.md)"
cp "$TMP/harness.md" "$p/.claude/HARNESS.md"
adopt "$p" factory --check; rc 0 "--check after the edit is undone"
echo "kit moved on" >> "$p/factory/model/SPEC-FLOW.md"
echo "# kit moved on" >> "$p/factory/harness/HARNESS.md"
adopt "$p" factory --check; rc 1 "--check: the kit changed since install"; has "stale" "stale"
adopt "$p" factory; rc 0 "default re-run does not replace"
has "outdated" "run --upgrade to replace"
lacks "not replaced by a plain re-run" "$p/.claude/HARNESS.md" "kit moved on"
adopt "$p" factory --upgrade; rc 0 "--upgrade replaces the unmodified kit-owned file"
contains "replaced" "$p/.claude/HARNESS.md" "kit moved on"
absent "stale .factory-new cleaned up" "$p/.claude/HARNESS.md.factory-new"
rm "$p/.claude/.factory-manifest.json"
adopt "$p" factory --check; rc 1 "--check without a manifest"; has "no manifest" "pre-1.4.0"

echo "== --upgrade with a manifest =="
p="$TMP/up"; mkdir -p "$p"; vendor "$FX" "$p"
adopt "$p" factory; rc 0 "install before upgrade"
echo "local tweak" >> "$p/.claude/agents/tester.md"
echo "filled" >> "$p/.claude/CLAUDE.md"
printf '#!/usr/bin/env python3\nprint("{}")  # v2\n' \
  > "$p/factory/harness/skills/careful/hooks/check-careful.py"
echo "Kit v2 line." >> "$p/factory/harness/agents/tester.md"
echo "Kit v2 template line." >> "$p/factory/harness/CLAUDE.md.template"
printf '#!/usr/bin/env bash\necho new\n' > "$p/factory/gates/check-spec-numbers.sh"
chmod +x "$p/factory/gates/check-spec-numbers.sh"
rm "$p/factory/gates/check-plan-sync.test.sh"
adopt "$p" factory --upgrade; rc 1 "upgrade with reviews pending exits 1"
contains "unmodified hook replaced" "$p/.claude/hooks/check-careful.py" "v2"
has "hook change reminds the test table and the live probes" \
  "run bash .claude/hooks/check-careful.test.sh, then the careful skill's"
contains "modified kit-owned file kept" "$p/.claude/agents/tester.md" "local tweak"
contains "its kit version offered" "$p/.claude/agents/tester.md.factory-new" "Kit v2 line."
contains "adopter-filled kept" "$p/.claude/CLAUDE.md" "filled"
contains "adopter-filled offered" "$p/.claude/CLAUDE.md.factory-new" "Kit v2 template line."
exe "new gate installed" "$p/gates/check-spec-numbers.sh"
absent "gate the kit no longer ships is removed" "$p/gates/check-plan-sync.test.sh"
has "upgrade" "REVIEW  2 file"
adopt "$p" factory --upgrade; rc 1 "second upgrade: still pending"
hasnt "second upgrade offers nothing new" "REVIEW"
rm "$p/.claude/agents/tester.md.factory-new" "$p/.claude/CLAUDE.md.factory-new"
adopt "$p" factory --upgrade; rc 0 "upgrade after the reviews"

echo "== legacy adoption (no manifest) =="
p="$TMP/legacy"; mkdir -p "$p"; vendor "$FX" "$p"
adopt "$p" factory; rm "$p/.claude/.factory-manifest.json"
D="$p/.claude/skills/careful/hooks"   # where v1.3.x left its second copy of the guard
mkdir -p "$D"; cp "$p/.claude/hooks/"* "$D/"
echo "old" >> "$p/.claude/hooks/check-careful.sh"; cp "$p/.claude/hooks/check-careful.sh" "$D/"
adopt "$p" factory --check; rc 1 "--check flags the duplicate guard"
has "duplicate" "unregistered second copy"
adopt "$p" factory --upgrade; rc 1 "legacy upgrade leaves a review"
has "legacy" "pre-1.4.0 adoption"
contains "differing hook not replaced" "$p/.claude/hooks/check-careful.sh" "old"
present "differing hook offered" "$p/.claude/hooks/check-careful.sh.factory-new"
absent "duplicate guard removed" "$p/.claude/skills/careful/hooks"
present "manifest written" "$p/.claude/.factory-manifest.json"

echo "== --register-guard =="
p="$TMP/rg"; mkdir -p "$p/.claude"; vendor "$FX" "$p"
cat > "$p/.claude/settings.json" <<'EOF'
{
  "permissions": {"allow": ["Bash(npm test)"]},
  "hooks": {"PreToolUse": [
    {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo other-hook"}]},
    {"matcher": "Bash", "hooks": [{"type": "command",
      "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/check-careful.sh\""}]}
  ]}
}
EOF
adopt "$p" factory --register-guard; rc 0 "--register-guard"
cp "$p/.claude/settings.json" "$TMP/s1"
t "settings: other keys kept, old guard entry upgraded" "$PY" - "$p/.claude/settings.json" <<'EOF'
import json, sys
s = json.load(open(sys.argv[1]))
assert s["permissions"] == {"allow": ["Bash(npm test)"]}, s
g = s["hooks"]["PreToolUse"]
assert any(h["command"] == "echo other-hook" for x in g for h in x["hooks"]), g
ours = [x for x in g if any("check-careful" in h["command"] for h in x["hooks"])]
assert [x["matcher"] for x in ours] == \
    ["Bash|PowerShell", "Write|Edit|MultiEdit|NotebookEdit"], ours
assert "_comment" not in json.dumps(s), s
EOF
adopt "$p" factory --register-guard; rc 0 "second --register-guard"
same "--register-guard is idempotent" "$TMP/s1" "$p/.claude/settings.json"
has "second --register-guard" "already registered"
adopt "$p" factory --check; rc 0 "--check with a current registration"
"$PY" - "$p/factory/harness/settings.json.template" <<'EOF'
import sys
p = sys.argv[1]
s = open(p).read().replace('"timeout": 10', '"timeout": 20', 1)
open(p, "w").write(s)
EOF
adopt "$p" factory --check; rc 1 "--check: the registered wiring is older than the template"
has "stale registration" "older wiring"
adopt "$p" factory --upgrade --register-guard; rc 0 "upgrade and re-register"
adopt "$p" factory --check; rc 0 "--check after re-registering"
p="$TMP/rg2"; mkdir -p "$p"; vendor "$FX" "$p"
adopt "$p" factory --register-guard; rc 0 "--register-guard creates settings.json"
contains "created" "$p/.claude/settings.json" "check-careful"
p="$TMP/rg3"; mkdir -p "$p"; vendor "$FX" "$p"
printf '#!/usr/bin/env bash\nexit 1\n' > "$p/factory/harness/skills/careful/hooks/check-careful.sh"
adopt "$p" factory --register-guard; rc 1 "a broken hook is not registered"
has "broken hook" "NOT registered"; absent "no settings.json written" "$p/.claude/settings.json"
p="$TMP/rg5"; mkdir -p "$p"; vendor "$FX" "$p"
"$PY" - "$p/factory/harness/settings.json.template" <<'EOF'
import json, sys
p = sys.argv[1]; t = json.load(open(p)); del t["hooks"]["PreToolUse"][1]
json.dump(t, open(p, "w"))
EOF
adopt "$p" factory --register-guard; rc 1 "a template that lost a matcher is refused"
has "weakened template" "does not register the careful hook for Write"
absent "nothing registered" "$p/.claude/settings.json"
p="$TMP/rg4"; mkdir -p "$p/.claude"; vendor "$FX" "$p"
printf '{ nope' > "$p/.claude/settings.json"
adopt "$p" factory --register-guard; rc 1 "invalid settings.json is left alone"
contains "untouched" "$p/.claude/settings.json" "{ nope"

echo "== --install-git-hook =="
p="$TMP/gh"; git init -q "$p"; vendor "$FX" "$p"
adopt "$p" factory --install-git-hook; rc 0 "--install-git-hook in a fresh repo"
exe "pre-commit installed" "$p/gates/hooks/pre-commit"
t "core.hooksPath set" test "$(git -C "$p" config core.hooksPath)" = "gates/hooks"
adopt "$p" factory; rc 0 "re-run keeps the hook"
present "still installed" "$p/gates/hooks/pre-commit"
adopt "$p" factory --install-git-hook; rc 0 "idempotent"; has "idempotent" "already gates/hooks"
p="$TMP/gh2"; git init -q "$p"; vendor "$FX" "$p"; git -C "$p" config core.hooksPath .husky
adopt "$p" factory --install-git-hook; rc 1 "existing core.hooksPath is not displaced"
has "hooksPath" "NOT installed"
t "hooksPath unchanged" test "$(git -C "$p" config core.hooksPath)" = ".husky"
p="$TMP/gh3"; git init -q "$p"; vendor "$FX" "$p"
printf '#!/bin/sh\nexit 0\n' > "$p/.git/hooks/pre-commit"; chmod +x "$p/.git/hooks/pre-commit"
adopt "$p" factory --install-git-hook; rc 1 "an existing .git/hooks hook is not displaced"
has "existing hook" "pre-commit"
t "hooksPath still unset" sh -c "! git -C '$p' config core.hooksPath"
p="$TMP/gh4"; mkdir -p "$p"; vendor "$FX" "$p"
adopt "$p" factory --install-git-hook; rc 1 "--install-git-hook outside git"

echo "== --ci github =="
p="$TMP/ci"; git init -q "$p"; vendor "$FX" "$p"
adopt "$p" factory --ci github; rc 0 "--ci github"
same "workflow installed" "$FX/gates/ci/github-actions.yml" "$p/.github/workflows/factory-gates.yml"
adopt "$p" factory; rc 0 "re-run keeps it"; present "kept" "$p/.github/workflows/factory-gates.yml"
rm "$p/.github/workflows/factory-gates.yml"
adopt "$p" factory; rc 0 "re-run after the adopter deleted it"
absent "a deleted flag-installed file is not re-created" "$p/.github/workflows/factory-gates.yml"
adopt "$p" factory --check; rc 1 "--check fails: CI no longer runs the chain (review 2)"
has "names the gap" "CI no longer runs the gate chain"
printf 'on: push\njobs:\n  g:\n    runs-on: ubuntu-latest\n    steps:\n      - run: ./gates/run-chain.sh\n' > "$p/.github/workflows/ci.yml"
adopt "$p" factory --check; rc 0 "another workflow that runs the chain replaces it"
has "the replacement is named" "ci.yml runs the gate chain in its place"
p="$TMP/ci2"; mkdir -p "$p/.github/workflows"; vendor "$FX" "$p"
echo "ours: true" > "$p/.github/workflows/factory-gates.yml"
adopt "$p" factory --ci github; rc 0 "--ci github next to an existing workflow"
contains "never overwritten" "$p/.github/workflows/factory-gates.yml" "ours: true"
present "offered instead" "$p/.github/workflows/factory-gates.yml.factory-new"

echo "== embedded repo warning =="
p="$TMP/emb"; git init -q "$p"; git clone -q "$FX" "$p/factory"
adopt "$p" factory; rc 0 "embedded clone still adopts"
has "embedded" "embedded git repository"; has "fix" "git submodule add"
(cd "$p" && git add -A) >/dev/null 2>&1
adopt "$p" factory; has "staged gitlink needs git rm --cached" "git rm --cached -f -q factory"
( cd "$p" && git rm --cached -f -q factory \
  && git submodule add -q "$(git -C factory remote get-url origin)" factory ) >/dev/null 2>&1
adopt "$p" factory; rc 0 "after the printed fix"; hasnt "fixed" "embedded"

echo "== output survives a non-UTF-8 console, and AGENTS.md is flagged =="
p="$TMP/dự-án"; mkdir -p "$p"; vendor "$FX" "$p" "khung-dự-án"
echo "# agents" > "$p/AGENTS.md"
(cd "$p" && PYTHONIOENCODING=ascii "$PY" "khung-dự-án/bin/adopt.py") >"$OUT" 2>&1; RC=$?
rc 0 "ascii console, non-ASCII kit and project paths"
has "non-ASCII path printed" "khung-d"; hasnt "no encoding crash" "UnicodeEncodeError"
has "AGENTS.md" "@../AGENTS.md"

echo "== check-links.py =="
p="$TMP/cl"; mkdir -p "$p/d"; echo "# a" > "$p/d/a.md"
printf '[ok](d/a.md) [dead](d/b.md)\n`[code](x.md)`\n```\n[fence](y.md)\n```\n' > "$p/x.md"
(cd "$p" && "$PY" "$KIT/bin/check-links.py" .) >"$OUT" 2>&1; RC=$?
rc 1 "a dead link fails"; has "dead link reported" "x.md:1: dead link -> d/b.md"
hasnt "code span skipped" "-> x.md"; hasnt "fence skipped" "-> y.md"
printf '%s\n' '---' 'description: see [a](fm-nope.md)' '---' '[b](fm-dead.md)' > "$p/f.md"
(cd "$p" && "$PY" "$KIT/bin/check-links.py" f.md) >"$OUT" 2>&1; RC=$?
rc 1 "a link below the frontmatter is checked"; has "below frontmatter" "f.md:4: dead link"
hasnt "frontmatter is data, not a link" "fm-nope"
(cd "$p" && "$PY" "$KIT/bin/check-links.py" d) >"$OUT" 2>&1; RC=$?
rc 0 "clean tree passes"
(cd "$p" && "$PY" "$KIT/bin/check-links.py" nope) >"$OUT" 2>&1; RC=$?
rc 2 "missing root is a usage error"

echo "== a stale kit checkout is behind the manifest (review 2026-09-29) =="
# A teammate's plain `git pull` leaves factory/ on the old commit. --check used to say "stale -
# run --upgrade", and --upgrade put the older guard back with a green --check.
FXN="$TMP/fixture-newer"; mkdir -p "$FXN"; (cd "$FX" && tar --exclude=.git -cf - .) | (cd "$FXN" && tar -xf -)
echo "9.9.10" > "$FXN/VERSION"
printf '#!/usr/bin/env python3\nprint("{}")  # newer guard\n' > "$FXN/harness/skills/careful/hooks/check-careful.py"
p="$TMP/behind"; mkdir -p "$p"; vendor "$FXN" "$p"
adopt "$p" factory; rc 0 "adopt the newer kit"
rm -rf "$p/factory"; vendor "$FX" "$p"                     # the stale checkout
adopt "$p" factory --check; rc 1 "--check: factory/ is behind what the project installed"
has "behind" "older than the 9.9.10"; has "behind: the fix" "git submodule update --init"
hasnt "behind: never 'run --upgrade' per file" "stale - "
adopt "$p" factory --upgrade; rc 1 "--upgrade refuses to downgrade"
contains "newer guard kept" "$p/.claude/hooks/check-careful.py" "newer guard"
adopt "$p" factory; rc 1 "a plain run refuses too (it would rewrite the manifest)"
contains "manifest still records the newer kit" "$p/.claude/.factory-manifest.json" '"9.9.10"'
adopt "$p" factory --allow-downgrade; rc 2 "--allow-downgrade only with --upgrade"
adopt "$p" factory --upgrade --allow-downgrade; rc 0 "a deliberate rollback"
lacks "rolled back" "$p/.claude/hooks/check-careful.py" "newer guard"
rm -rf "$p/factory"; vendor "$FXN" "$p"
adopt "$p" factory --check; rc 1 "forward again: an ordinary upgrade is due"; has "forward" "run --upgrade"

echo "== guard and gate drift fail --check; execute bits are checked (review 2026-09-29) =="
p="$TMP/drift"; git init -q "$p"; vendor "$FX" "$p"
adopt "$p" factory; rc 0 "adopt"
cp "$p/.claude/hooks/check-careful.sh" "$TMP/shim"; : > "$p/.claude/hooks/check-careful.sh"
adopt "$p" factory --check; rc 1 "an emptied shim fails --check"
has "emptied shim" "check-careful.sh: differs from the kit's copy, so the guard may be off"
cat "$TMP/shim" > "$p/.claude/hooks/check-careful.sh"
adopt "$p" factory --check; rc 0 "restored shim"
echo "# local tweak" >> "$p/.claude/HARNESS.md"
adopt "$p" factory --check; rc 0 "a doc edit stays a warning"; has "doc edit" "HARNESS.md: kit-owned but modified locally"
chmod -x "$p/gates/run-chain.sh"
adopt "$p" factory --check; rc 1 "a script without its execute bit"; has "chmod" "not executable"
chmod +x "$p/gates/run-chain.sh"
(cd "$p" && git add -A && git update-index --chmod=-x gates/run-chain.sh) >/dev/null 2>&1
adopt "$p" factory --check; rc 1 "a script committed as 100644"; has "index mode" "git update-index --chmod=+x gates/run-chain.sh"
(cd "$p" && git update-index --chmod=+x gates/run-chain.sh)
adopt "$p" factory --check; rc 0 "index mode fixed"

echo "== --check never runs a run-chain.sh the kit did not write (review 2026-09-29) =="
p="$TMP/foreign"; mkdir -p "$p/gates"; vendor "$FX" "$p"
printf '#!/usr/bin/env bash\necho "RAN $*" >> "%s/ran.log"\n' "$p" > "$p/gates/run-chain.sh"
chmod +x "$p/gates/run-chain.sh"
adopt "$p" factory; rc 0 "adopt beside a project runner"
rm "$p/gates/run-chain.sh.factory-new"
adopt "$p" factory --check; rc 1 "--check (the runner is not the kit's)"
absent "--check executed nothing" "$p/ran.log"

echo "== .gitattributes pins by extension; a binary under gates/ is untouched (review 2026-09-29) =="
p="$TMP/bin"; git init -q "$p"; vendor "$FX" "$p"
printf '%s\n' "# ai-factory-kit: installed scripts stay LF - a CRLF checkout makes bash exit 2, and a" \
  "# PreToolUse hook that exits 2 blocks every tool call." ".claude/hooks/** text eol=lf" \
  "gates/** text eol=lf" > "$p/.gitattributes"
adopt "$p" factory; rc 0 "adopt over a pre-release .gitattributes block"
has "migrated" "replaced an earlier block"
lacks "old tree rule gone" "$p/.gitattributes" "gates/** text"
mkdir -p "$p/gates/visual"; printf '\211PNG\r\n\032\n\000\000\000\rIHDR' > "$p/gates/visual/baseline.png"
(cd "$p" && git add -A) >/dev/null 2>&1
t "the PNG is committed byte for byte" sh -c "cd '$p' && git show :gates/visual/baseline.png | cmp -s - gates/visual/baseline.png"
adopt "$p" factory --check; hasnt "a binary is not a CRLF script" "baseline.png"
# review 2: the next pre-release block pinned `gates/hooks/*`, which rewrote a binary there too
p="$TMP/bin2"; git init -q "$p"; vendor "$FX" "$p"
printf '%s\n' "# ai-factory-kit: installed scripts stay LF - a CRLF checkout makes bash exit 2, and a" \
  "# PreToolUse hook that exits 2 blocks every tool call. Pinned by extension, so a binary" \
  "# under gates/ is never touched." ".claude/hooks/*.sh text eol=lf" "gates/*.sh text eol=lf" \
  "gates/hooks/* text eol=lf" > "$p/.gitattributes"
t "before: the old block makes a binary under gates/hooks/ text" \
  sh -c "cd '$p' && git check-attr text -- gates/hooks/logo.png | grep -q 'text: set'"
adopt "$p" factory; rc 0 "adopt over the round-1 .gitattributes block"
has "migrated (round 1)" "replaced an earlier block"
lacks "gates/hooks/* rule gone" "$p/.gitattributes" "gates/hooks/* text"
t "one kit comment block, not two" test "$(grep -c '^# ai-factory-kit:' "$p/.gitattributes")" = 1
mkdir -p "$p/gates/hooks"; printf '\211PNG\r\n\032\n\000\000\000\rIHDR' > "$p/gates/hooks/logo.png"
(cd "$p" && git add -A) >/dev/null 2>&1
t "a PNG under gates/hooks/ is committed byte for byte" sh -c "cd '$p' && git show :gates/hooks/logo.png | cmp -s - gates/hooks/logo.png"
t "the hook itself is still pinned LF" \
  sh -c "cd '$p' && git check-attr eol -- gates/hooks/pre-commit | grep -q 'eol: lf'"

echo "== flag-installed files and the per-clone hook are audited (review 2026-09-29) =="
p="$TMP/flags"; git init -q "$p"; vendor "$FX" "$p"
adopt "$p" factory --install-git-hook --ci github; rc 0 "hook and CI"
contains "CI is adopter-filled (toolchain steps)" "$p/.claude/.factory-manifest.json" \
  '".github/workflows/factory-gates.yml": {'
git -C "$p" config --unset core.hooksPath
adopt "$p" factory --check; rc 0 "an unwired clone is a warning"
has "per clone" "does not run it (core.hooksPath is unset)"; has "per clone: fix" "--install-git-hook once in every clone"
adopt "$p" factory --install-git-hook; rc 0 "wire this clone"
adopt "$p" factory --check; hasnt "wired" "does not run it"
rm "$p/.github/workflows/factory-gates.yml"
adopt "$p" factory; rc 0 "re-run after the CI job was deleted"
adopt "$p" factory --check; rc 1 "a deleted CI job is a failure, not a warning (review 2)"
has "deleted CI" "factory-gates.yml: installed by adopt.py --ci github, now deleted"

echo "== next steps never mark the live probes done (review 2026-09-29) =="
p="$TMP/probes"; mkdir -p "$p"; vendor "$FX" "$p"
adopt "$p" factory --register-guard; rc 0 "register"
has "registration is done" '\[done\] adapt .claude/hooks/careful.json'
hasnt "the probes are not" '\[done\] the careful skill'
has "the probes are listed" "the careful skill's two live probes"
has "footer: per-clone hook" "each clone runs python3 factory/bin/adopt.py --install-git-hook once"

echo "== unfilled placeholders are reported (review 2026-09-29) =="
p="$TMP/ph"; mkdir -p "$p"; vendor "$FX" "$p"
adopt "$p" factory; adopt "$p" factory --check; rc 0 "placeholders are warnings"
has "placeholder" "WARN  .claude/CLAUDE.md: 1 unfilled placeholder"
"$PY" - "$p/.claude/CLAUDE.md" <<'EOF'
import sys
p = sys.argv[1]; s = open(p).read().replace("[PROJECT]", "Budget"); open(p, "w").write(s)
EOF
adopt "$p" factory --check; hasnt "filled" "WARN  .claude/CLAUDE.md: 1 unfilled"

echo "== pre-1.4.0 constitution links get a hint (review 2026-09-29) =="
printf '# C\nFlow: [SPEC-FLOW](../model/SPEC-FLOW.md).\n' > "$p/.specify/memory/constitution.md"
adopt "$p" factory --check; rc 1 "a v1.3.x constitution link is dead"
has "hint" "written for factory/constitution/"; has "hint: the new target" "../../factory/model/SPEC-FLOW.md"

echo "== a rule with no frontmatter is valid; a misplaced one is not (review 2026-09-29) =="
p="$TMP/nofm"; mkdir -p "$p/.claude/rules"; vendor "$FX" "$p"
printf '# Our workflow\nAlways rebase.\n' > "$p/.claude/rules/workflow.md"
printf '# Security\nNo secrets.\n' > "$p/.claude/rules/security.md"
adopt "$p" factory; rc 0 "adopt beside rules without frontmatter"
rm "$p/.claude/rules/workflow.md.factory-new"
adopt "$p" factory --check; rc 0 "--check accepts them"; hasnt "no frontmatter" "must open at byte 0"
printf '<!-- x -->\n---\npaths:\n  - "src/**"\n---\n' > "$p/.claude/rules/security.md"
adopt "$p" factory --check; has "a misplaced frontmatter still warns" "security.md: rule: YAML frontmatter must open at byte 0"

echo "== a project below the repository root (review 2026-09-29) =="
top="$TMP/mono"; git init -q "$top"; p="$top/services/api"; mkdir -p "$p"; vendor "$FX" "$p"
adopt "$p" factory; rc 0 "adopt in a sub-directory"; has "nested" "not the git repository's root"
adopt "$p" factory --ci github; rc 1 "--ci github refuses where GitHub would never read it"
has "nested ci" "GitHub reads workflows only from the repository root"
absent "nothing written" "$p/.github"

echo "== a profile change or a deleted rule is not a kit change (review 2026-09-29) =="
p="$TMP/reprof"; mkdir -p "$p"; vendor "$FX" "$p"
adopt "$p" factory; echo "filled" >> "$p/.claude/CLAUDE.md"
adopt "$p" factory --profile cli; rc 0 "narrow the profile"
has "rendering, not the kit" "its links changed with the profile"; hasnt "not the kit's fault" "the kit's template changed"
rm "$p/.claude/CLAUDE.md.factory-new"
p="$TMP/delrule"; mkdir -p "$p"; vendor "$FX" "$p"
adopt "$p" factory; rm "$p/.claude/rules/architecture.md"
adopt "$p" factory --check; rc 1 "--check after deleting a rule"
has "plain adopt.py" "run python3 factory/bin/adopt.py, not --upgrade"; hasnt "not stale" "stale - "

echo "== adopt.py takes no abbreviated options (review 2026-09-29) =="
p="$TMP/abbr"; mkdir -p "$p"; vendor "$FX" "$p"; adopt "$p" factory
adopt "$p" factory --upg; rc 2 "--upg is not --upgrade"
adopt "$p" factory --che; rc 2 "--che is not --check"

echo "== a pristine older duplicate of the guard is removed (review 2026-09-29) =="
FXH="$TMP/fixture-hist"; mkdir -p "$FXH"; (cd "$FX" && tar --exclude=.git -cf - .) | (cd "$FXH" && tar -xf -)
gitkit "$FXH"
printf '#!/usr/bin/env bash\ncat >/dev/null\necho "{}"  # v2\n' > "$FXH/harness/skills/careful/hooks/check-careful.sh"
(cd "$FXH" && git commit -qam v2)
p="$TMP/dup"; git init -q "$p"; git clone -q "$FXH" "$p/factory"
adopt "$p" factory; rm "$p/.claude/.factory-manifest.json"
mkdir -p "$p/.claude/skills/careful/hooks"
git -C "$FXH" show HEAD~1:harness/skills/careful/hooks/check-careful.sh > "$p/.claude/skills/careful/hooks/check-careful.sh"
echo "# our live edit" >> "$p/.claude/hooks/check-careful.sh"
adopt "$p" factory --upgrade
absent "a copy equal to an OLDER kit version is removed" "$p/.claude/skills/careful/hooks"
has "legacy guard review line" "port any local rule to .claude/hooks/careful.json"

echo "== live kit: a fresh adoption of this working tree =="
p="$TMP/live"; git init -q "$p"; vendor "$KIT" "$p"
adopt "$p" factory; rc 0 "live kit adopts cleanly"
t "live kit: 0 dead links" links "$p" .claude gates .specify
adopt "$p" factory --check; rc 0 "live kit: --check clean"
# --check reads gates/chain.conf through the real runner's --list (exit 2 = malformed), so a
# chain.conf that would stop every commit with a config error is caught before the first commit.
cp "$p/gates/chain.conf" "$TMP/live-cc"
echo "format: npx prettier --check ." >> "$p/gates/chain.conf"
adopt "$p" factory --check; rc 1 "live kit: --check on a chain.conf that declares a slot twice"
has "malformed chain.conf named" "gates/chain.conf: run-chain.sh rejects it"
cat "$TMP/live-cc" > "$p/gates/chain.conf"
adopt "$p" factory --check; rc 0 "live kit: --check once the duplicate slot is gone"
# /speckit-constitution drafts the constitution from the override, links and all (review
# 2026-09-29: 18 dead links). The override's text must be valid where it lands.
cp "$p/.specify/memory/constitution.md" "$TMP/live-const"
cp "$p/.specify/templates/overrides/constitution-template.md" "$p/.specify/memory/constitution.md"
adopt "$p" factory --check; rc 0 "live kit: the override written into memory/ has no dead link"
cat "$TMP/live-const" > "$p/.specify/memory/constitution.md"
t "live kit: a direct check-links run agrees" links "$p" .specify
# PHASE-0 §3: the vision is saved from the template beside the constitution.
cp "$p/factory/constitution/vision-template.md" "$p/.specify/memory/vision.md"
adopt "$p" factory --check; rc 0 "live kit: vision.md saved from the template"
hasnt "live kit: no dead link in vision.md" "vision.md: line"
rm "$p/.specify/memory/vision.md"
# AI-ONBOARDING §2.2 step 7: the Safety invariants bullets, copied verbatim into each agent.
"$PY" - "$p/.claude/CLAUDE.md" "$p"/.claude/agents/*.md <<'EOF' || fail "live kit: copying the invariants into the agents"
import re, sys
src = open(sys.argv[1], encoding="utf-8").read()
start = src.index("- **I —")
end = src.index("\n\n", start)
bullets = src[start:end].strip() + "\n"
pat = re.compile(r"- \*\*I — \[DOMAIN INVARIANT\]\*\*: \[copy from CLAUDE\.md\]\n(?:- .*\n){3}")
for a in sys.argv[2:]:
    t = open(a, encoding="utf-8").read()
    t2 = pat.sub(lambda m: bullets, t, count=1)
    assert t2 != t, a
    open(a, "w", encoding="utf-8").write(t2)
EOF
adopt "$p" factory --check; rc 0 "live kit: invariants copied verbatim into the agents"
hasnt "live kit: no dead link in an agent" "agents/.*dead link"
hasnt "live kit: a filled agent is not 'modified locally'" "agents/.*modified locally"

echo "== v1.3.2 adoption upgraded by this adopt.py =="
# v1.3.2 is tag v1.3.2 = commit af7f324 (git ls-remote --tags origin). The commit is the fallback
# for a clone that has the history but not the tags.
V132=""; V132_SHA=af7f324691bbaa8bc96a9682aa56f401e0d1d557
if git -C "$KIT" rev-parse -q --verify "refs/tags/v1.3.2^{commit}" >/dev/null 2>&1; then
  V132="v1.3.2"
elif git -C "$KIT" cat-file -e "$V132_SHA^{commit}" 2>/dev/null; then
  V132="$V132_SHA"
fi
if [ -n "$V132" ]; then
  old="$TMP/kit-v132"; git clone -q "$KIT" "$old" 2>/dev/null && git -C "$old" checkout -q "$V132"
  p="$TMP/v132"; git init -q "$p"; vendor "$old" "$p"
  (cd "$p" && "$PY" factory/bin/adopt.py) >"$OUT" 2>&1; RC=$?; rc 0 "v1.3.2 adopt.py"
  echo "## Project: filled by the adopter" >> "$p/.claude/CLAUDE.md"
  echo "filled rule" >> "$p/.claude/rules/data.md"
  mkdir -p "$p/.specify/memory"
  printf '# Ratified constitution\n' > "$p/.specify/memory/constitution.md"
  FILLED=".claude/CLAUDE.md .claude/rules/data.md .specify/memory/constitution.md"
  for f in $FILLED; do cp "$p/$f" "$TMP/keep.$(basename "$f")"; done
  rm -rf "$p/factory"; vendor "$KIT" "$p"
  adopt "$p" factory --upgrade
  if [ "$RC" = 0 ] || [ "$RC" = 1 ]; then pass; else fail "v1.3.2 upgrade exit $RC" "$OUT"; fi
  has "v1.3.2 upgrade" "pre-1.4.0 adoption"
  has "review list printed" "REVIEW"
  has "CLAUDE.md listed for review" ".claude/CLAUDE.md "
  for f in $FILLED; do
    same "adopter-filled $f not overwritten" "$TMP/keep.$(basename "$f")" "$p/$f"
  done
  absent "v1.3.x duplicate guard removed" "$p/.claude/skills/careful/hooks"
  present "manifest written" "$p/.claude/.factory-manifest.json"
  for f in $(newfiles "$p"); do cp "$f" "${f%.factory-new}"; rm "$f"; done
  adopt "$p" factory --check; rc 0 "after taking every .factory-new, --check is clean"
else
  SKIP=$((SKIP+1))
  echo "  SKIP  v1.3.2 is not in this clone's history (shallow?) - fetch it to run this"
fi

echo
echo "passed $PASS, failed $FAIL, skipped $SKIP"
[ "$FAIL" -eq 0 ]
