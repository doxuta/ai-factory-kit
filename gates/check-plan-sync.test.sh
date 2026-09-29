#!/usr/bin/env bash
# Two-direction test for check-plan-sync.sh.
#
# WHY THIS FILE EXISTS: GATES.md §6 says "a gate proven in only one direction is decoration",
# and until 2026-09-11 the kit shipped this gate with NO test at all — while CHANGELOG.md
# called it "two-direction-tested". The kit's other executable artifact, the careful hook,
# turned out to be inert for 2.5 months for a closely related reason. Green is not evidence;
# red-when-it-should-be-red is half the evidence, and green-when-it-should-be-green is the
# other half.
#
# Run: bash gates/check-plan-sync.test.sh
# Exit 0 = all green.

GATE="$(cd "$(dirname "$0")" && pwd)/check-plan-sync.sh"
PASS=0; FAIL=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# expect <want-exit> <label> <docs-dir>
expect() {
  local want="$1" label="$2" dir="$3" got
  bash "$GATE" "$dir" >"$TMP/out" 2>&1
  got=$?
  if [ "$got" = "$want" ]; then
    PASS=$((PASS+1))
  else
    FAIL=$((FAIL+1))
    printf '  FAIL  want exit %s, got %s — %s\n' "$want" "$got" "$label"
    sed 's/^/        /' "$TMP/out"
  fi
}

plan() { # plan <dir> <header-done>/<header-total> <table-rows-done> <table-rows-total>
  local dir="$1" hdone="$2" htotal="$3" tdone="$4" ttotal="$5" i
  mkdir -p "$dir"
  { echo "# Demo plan"
    echo
    # The header bar must start the line — `^(M\d+)\s*\[...\]` in the gate. An indented
    # or prefixed bar parses as ABSENT, which fails for the wrong reason: the first draft of
    # this fixture wrote "📍 Tiến độ: M1 [...]" and made all three RED cases pass without ever
    # exercising the drift comparison they exist to test.
    echo "M1 [✅] ${hdone}/${htotal}"
    echo
    echo "| done | task |"
    echo "|---|---|"
    # A counter, not `seq`: BSD seq counts DOWN when first > last, so on macOS `seq 5 4`
    # printed two phantom ⬜ rows for every all-done plan (4/4 became 4/6) — measured on the
    # macOS CI runner, where "blueprint agrees" went red and "blueprint still marks M1 ⬜"
    # stayed red for the wrong reason. GNU seq prints nothing, so Linux never saw it.
    i=1; while [ "$i" -le "$tdone" ]; do echo "| ✅ | M1-T$i |"; i=$((i+1)); done
    while [ "$i" -le "$ttotal" ]; do echo "| ⬜ | M1-T$i |"; i=$((i+1)); done
  } > "$dir/demo-plan.md"
  # Guard the fixture itself: a wrong row count makes every case after it test the wrong thing.
  local rows; rows=$(grep -c '| M1-T[0-9]' "$dir/demo-plan.md" || true)
  [ "$rows" -eq "$ttotal" ] || { echo "FIXTURE BUG: $dir has $rows rows, want $ttotal" >&2; exit 2; }
}

echo "== GREEN direction: it must not cry wolf =="
plan "$TMP/in-sync" 2 4 2 4
expect 0 "header 2/4 matches table 2 of 4" "$TMP/in-sync"

mkdir -p "$TMP/empty-dir"
expect 0 "dir exists, holds no plan at all" "$TMP/empty-dir"

mkdir -p "$TMP/unformatted"
printf '# just prose\n\nno progress bars here\n' > "$TMP/unformatted/notes-plan.md"
expect 0 "plan without the progress format is skipped, not failed" "$TMP/unformatted"

echo "== RED direction: it must actually bite =="
plan "$TMP/overstate" 4 4 2 4
expect 1 "header claims 4/4 while the table shows 2 done" "$TMP/overstate"

plan "$TMP/understate" 1 4 3 4
expect 1 "header claims 1/4 while the table shows 3 done" "$TMP/understate"

plan "$TMP/wrong-total" 2 9 2 4
expect 1 "header total 9 does not match the table's 4 rows" "$TMP/wrong-total"

echo "== wiring errors must not look like a clean bill of health =="
expect 1 "docs dir does not exist (mistyped or moved)" "$TMP/no-such-dir"
expect 1 "docs dir is a file, not a directory" "$GATE"

# ---------------------------------------------------------------------------------------
# 1.4.0: the default invocation, spec-corpus mode, and the optional blueprint check.
# Measured before 1.4.0: on a Spec Kit project the bare gate was red (no docs/), and
# `check-plan-sync.sh specs` printed "0 plans in format" and exited 0 over a spec marked
# shipped with an unfinished task. Every row below runs the real gate from a project root.
# ---------------------------------------------------------------------------------------

# run_in <want-exit> <label> <project-dir> [gate args...]; output kept in $TMP/out
run_in() {
  local want="$1" label="$2" dir="$3" got
  shift 3
  ( cd "$dir" && bash "$GATE" ${1+"$@"} ) >"$TMP/out" 2>&1
  got=$?
  if [ "$got" = "$want" ]; then
    PASS=$((PASS+1))
  else
    FAIL=$((FAIL+1))
    printf '  FAIL  want exit %s, got %s — %s\n' "$want" "$got" "$label"
    sed 's/^/        /' "$TMP/out"
  fi
}
# said <label> <text>: the last run's output contains <text>
said() {
  if grep -qF -- "$2" "$TMP/out"; then PASS=$((PASS+1)); else
    FAIL=$((FAIL+1)); printf '  FAIL  output lacks %s — %s\n' "$2" "$1"; sed 's/^/        /' "$TMP/out"; fi
}
# never_said <label> <text>: the last run's output does NOT contain <text>
never_said() {
  if grep -qF -- "$2" "$TMP/out"; then
    FAIL=$((FAIL+1)); printf '  FAIL  output contains %s — %s\n' "$2" "$1"; sed 's/^/        /' "$TMP/out"
  else PASS=$((PASS+1)); fi
}

# spec <project> <id> <status> [extra frontmatter line]...  — a C4 spec.md
spec() {
  local proj="$1" id="$2" status="$3" line
  shift 3
  mkdir -p "$proj/specs/$id"
  { echo "---"
    echo "feature: $id"
    echo "status: $status"
    echo "epic: core"
    if [ "$status" != draft ]; then echo "approved_by: Owner"; echo "approved_on: 2026-09-01"; fi
    for line in ${1+"$@"}; do echo "$line"; done
    echo "---"
    echo
    echo "# Feature Specification: $id"
  } > "$proj/specs/$id/spec.md"
}
# tasks <project> <id> <line>...  — a Spec Kit tasks.md
tasks() {
  local proj="$1" id="$2" line
  shift 2
  mkdir -p "$proj/specs/$id"
  { echo "# Tasks: $id"; echo; for line in "$@"; do echo "$line"; done; } > "$proj/specs/$id/tasks.md"
}
# thirteen <project> <id> <status> <T013-box>  — the audit's budget-cli shape: 12 done + T013
thirteen() {
  local i lines=()
  for i in 01 02 03 04 05 06 07 08 09 10 11 12; do lines+=("- [x] T0$i task $i"); done
  lines+=("- [$4] T013 [US2] Reject a CSV with an empty header row in tests/test_cli.py")
  spec "$1" "$2" "$3"
  tasks "$1" "$2" "${lines[@]}"
}

echo "== default invocation: nothing there yet is said out loud, never a bare green =="
mkdir -p "$TMP/p-empty"
run_in 0 "fresh project, no specs/ or docs/" "$TMP/p-empty"
said "fresh project" "nothing to check yet (no specs/ or docs/)"

mkdir -p "$TMP/p-docs-prose/docs"
printf '# prose\n' > "$TMP/p-docs-prose/docs/readme-plan.md"
cp "$GATE" "$TMP/p-docs-prose/docs/not-a-plan.sh"
run_in 0 "docs/ with no formatted plan and no specs/" "$TMP/p-docs-prose"
said "docs/ without plans" "nothing to check yet"
never_said "docs/ without plans" "0 plans in format"

mkdir -p "$TMP/p-sk-copy/docs"
{ echo "# Tasks"; echo "- [x] T001 Create project structure"; echo "- [ ] T002 Build it"; } > "$TMP/p-sk-copy/docs/booking-plan.md"
run_in 0 "docs/booking-plan.md in Spec Kit checkbox format (audit repro) is not a plan in format" "$TMP/p-sk-copy"
never_said "Spec Kit tasks copied into docs/" "0 plans in format"

plan "$TMP/p-docs-ok/docs" 2 4 2 4
run_in 0 "docs/ with an in-sync plan (docs mode through auto-detect)" "$TMP/p-docs-ok"
said "docs auto" "Docs in sync — demo-plan.md 2/4"

mkdir -p "$TMP/p-specs-empty/specs"
run_in 0 "specs/ exists but holds no feature dir yet" "$TMP/p-specs-empty"
said "empty specs/" "nothing to check yet"

echo "== spec-corpus mode, GREEN: legitimate states must pass =="
spec "$TMP/g-draft" 001-alpha draft
run_in 0 "one draft spec, no tasks yet" "$TMP/g-draft"
said "corpus summary" "Specs in sync"

thirteen "$TMP/g-budget" 001-budget-cli shipped x
run_in 0 "budget-cli: status shipped, all 13 tasks checked (a ticked box is a claim — BLIND TO)" "$TMP/g-budget"

spec "$TMP/g-deferred" 001-alpha accepted
tasks "$TMP/g-deferred" 001-alpha "- [x] T001 done" "- [ ] T002 export to PDF (deferred → 004-pdf-export)" "- [ ] T003 dark mode (deferred -> backlog)"
run_in 0 "accepted with open tasks marked (deferred → / ->)" "$TMP/g-deferred"
said "deferred counted" "2 deferred"

spec "$TMP/g-upper" 001-alpha accepted
tasks "$TMP/g-upper" 001-alpha "- [X] T001 implement marks [X], upper case" "* [x] T002 star bullet"
run_in 0 "[X] (what /speckit-implement writes) counts as checked" "$TMP/g-upper"

mkdir -p "$TMP/g-comments/specs/007-quoted"
printf -- '---\nfeature: "007-quoted"   # the directory name\nstatus: draft # not yet approved\nepic: \x27payments\x27\ntags:\n  - money\n  - qr\n---\n# Spec\n' > "$TMP/g-comments/specs/007-quoted/spec.md"
run_in 0 "frontmatter with quotes, inline # comments and a nested list" "$TMP/g-comments"

spec "$TMP/g-fenced" 001-alpha accepted
tasks "$TMP/g-fenced" 001-alpha "<!-- template note:" "- [ ] T999 example inside a comment" "-->" "- [x] T001 real task" '```text' "- [ ] T001 the format, shown in a fence" '```'
run_in 0 "unchecked boxes inside an HTML comment or a code fence are not tasks" "$TMP/g-fenced"

spec "$TMP/g-crlf" 001-alpha accepted
tasks "$TMP/g-crlf" 001-alpha "- [x] T001 done"
for f in "$TMP/g-crlf/specs/001-alpha/spec.md" "$TMP/g-crlf/specs/001-alpha/tasks.md"; do
  awk '{ printf "%s\r\n", $0 }' "$f" > "$f.crlf" && mv "$f.crlf" "$f"
done
run_in 0 "CRLF line endings (a Windows checkout) parse the same" "$TMP/g-crlf"

spec "$TMP/g-warn" 001-alpha approved
tasks "$TMP/g-warn" 001-alpha "- [x] T001 done" "- [x] T002 done"
run_in 0 "all tasks checked but status approved: a warning, not red" "$TMP/g-warn"
said "warn" "set status: accepted"

spec "$TMP/g-bom" 001-alpha draft
{ printf '\357\273\277'; cat "$TMP/g-bom/specs/001-alpha/spec.md"; } > "$TMP/x" && mv "$TMP/x" "$TMP/g-bom/specs/001-alpha/spec.md"
run_in 0 "a UTF-8 BOM before the frontmatter warns, it does not fail" "$TMP/g-bom"
said "BOM warning" "byte-order mark"

spec "$TMP/g-defer-only" 001-alpha approved
tasks "$TMP/g-defer-only" 001-alpha "- [ ] T001 later (deferred → 002-beta)"
run_in 0 "approved, only a deferred task: no 'every task is checked' warning" "$TMP/g-defer-only"
never_said "no false warning" "every task is checked"

spec "$TMP/g-super" 001-alpha superseded "superseded_by: 002-beta"
spec "$TMP/g-super" 002-beta draft
run_in 0 "superseded, pointing at an existing spec" "$TMP/g-super"

spec "$TMP/g-ts" 20260929-101500-alpha draft
run_in 0 "timestamp-numbered directory" "$TMP/g-ts"

spec "$TMP/g-explicit/product" 001-alpha draft
run_in 0 "--specs <dir> for a monorepo package" "$TMP/g-explicit" --specs product/specs

echo "== spec-corpus mode, RED: it must actually bite =="
thirteen "$TMP/r-budget" 001-budget-cli shipped " "
run_in 1 "budget-cli: status shipped while T013 is unchecked (the audit's repro)" "$TMP/r-budget"
said "names the task" "T013"

spec "$TMP/r-accepted" 001-alpha accepted
tasks "$TMP/r-accepted" 001-alpha "- [x] T001 done" "- [ ] T002 not done"
run_in 1 "status accepted with an open task" "$TMP/r-accepted"
said "reason" "status is accepted but 1 task is still open (T002)"

spec "$TMP/r-released" 001-alpha released
tasks "$TMP/r-released" 001-alpha "- [x] T001 done" "- [ ] T002 deferred without the arrow (deferred)"
run_in 1 "status released; '(deferred)' without an arrow still blocks" "$TMP/r-released"
said "reason" "status is released but 1 task is still open"

mkdir -p "$TMP/r-nofm/specs/001-alpha"
printf '# Feature Specification: alpha\n\n**Status**: Draft\n' > "$TMP/r-nofm/specs/001-alpha/spec.md"
run_in 1 "no frontmatter (raw Spec Kit spec-template output)" "$TMP/r-nofm"
said "reason" "no frontmatter"

mkdir -p "$TMP/r-fenced-fm/specs/001-alpha"
printf '<!-- WHO READS ME -->\n\n```yaml\nfeature: 001-alpha\nstatus: approved\nepic: core\n```\n' > "$TMP/r-fenced-fm/specs/001-alpha/spec.md"
run_in 1 "frontmatter in a yaml fence after a comment (the pre-1.4.0 example shape)" "$TMP/r-fenced-fm"
said "misplaced" "not at line 1"

mkdir -p "$TMP/r-open-fm/specs/001-alpha"
printf -- '---\nfeature: 001-alpha\nstatus: draft\nepic: core\n# Spec\n' > "$TMP/r-open-fm/specs/001-alpha/spec.md"
run_in 1 "frontmatter never closed" "$TMP/r-open-fm"
said "reason" "never closed"

mkdir -p "$TMP/r-noepic/specs/001-alpha"
printf -- '---\nfeature: 001-alpha\nstatus: draft\n---\n' > "$TMP/r-noepic/specs/001-alpha/spec.md"
run_in 1 "epic: missing" "$TMP/r-noepic"
said "reason" "frontmatter has no epic:"

mkdir -p "$TMP/r-epic-ph/specs/001-alpha"
printf -- '---\nfeature: 001-alpha\nstatus: draft\nepic: [EPIC]\n---\n' > "$TMP/r-epic-ph/specs/001-alpha/spec.md"
run_in 1 "epic: left as the template placeholder [EPIC]" "$TMP/r-epic-ph"
said "reason" "epic: is still a placeholder"

mkdir -p "$TMP/r-emptyval/specs/001-alpha"
printf -- '---\nfeature: 001-alpha\nstatus:   # TODO\nepic: core\n---\n' > "$TMP/r-emptyval/specs/001-alpha/spec.md"
run_in 1 "status: present but empty after its comment" "$TMP/r-emptyval"
said "reason" "frontmatter has no status:"

spec "$TMP/r-status" 001-alpha "done"
run_in 1 "unknown status 'done'" "$TMP/r-status"
said "reason" "unknown status 'done'"
spec "$TMP/r-case" 001-alpha Draft
run_in 1 "status 'Draft' (case matters; the hint says so)" "$TMP/r-case"
said "case hint" "lowercase: draft"
spec "$TMP/r-template" 001-alpha "draft | approved"
run_in 1 "status left as the template's alternatives" "$TMP/r-template"
said "reason" "unknown status 'draft | approved'"

spec "$TMP/r-feature" 002-beta draft
sed 's/^feature: 002-beta$/feature: 001-alpha/' "$TMP/r-feature/specs/002-beta/spec.md" > "$TMP/x" && mv "$TMP/x" "$TMP/r-feature/specs/002-beta/spec.md"
run_in 1 "feature: does not match the directory name (renumbered dir)" "$TMP/r-feature"
said "reason" "does not match the directory name 002-beta"

mkdir -p "$TMP/r-nospec/specs/001-alpha"
tasks "$TMP/r-nospec" 001-alpha "- [x] T001 done"
run_in 1 "feature dir with tasks.md but no spec.md" "$TMP/r-nospec"
said "reason" "001-alpha/: no spec.md"

mkdir -p "$TMP/r-dup/specs/001-alpha"
printf -- '---\nfeature: 001-alpha\nstatus: draft\nepic: core\nstatus: accepted\n---\n' > "$TMP/r-dup/specs/001-alpha/spec.md"
run_in 1 "duplicate status: key (which one is true?)" "$TMP/r-dup"
said "reason" "duplicate key 'status'"

mkdir -p "$TMP/r-nospace/specs/001-alpha"
printf -- '---\nfeature: 001-alpha\nstatus:draft\nepic: core\n---\n' > "$TMP/r-nospace/specs/001-alpha/spec.md"
run_in 1 "status:draft without a space is not a YAML key" "$TMP/r-nospace"
said "reason" "needs a space after the colon"

spec "$TMP/r-super" 001-alpha superseded
run_in 1 "superseded without superseded_by" "$TMP/r-super"
said "reason" "no superseded_by"
spec "$TMP/r-super2" 001-alpha superseded "superseded_by: 009-gone"
run_in 1 "superseded_by names no spec dir" "$TMP/r-super2"
said "reason" "009-gone names no directory"

spec "$TMP/r-both" 001-alpha draft
plan "$TMP/r-both/docs" 4 4 2 4
run_in 1 "specs/ fine but docs/ plan drifted: both are checked" "$TMP/r-both"
said "reason" "header says 4/4 but the table counts 2/4"

mkdir -p "$TMP/r-explicit"
run_in 1 "--specs names a dir that does not exist" "$TMP/r-explicit" --specs product/specs
said "reason" "specs dir not found"

spec "$TMP/r-specs-as-docs" 001-alpha shipped
tasks "$TMP/r-specs-as-docs" 001-alpha "- [ ] T001 never done"
run_in 1 "a specs dir passed as the docs argument (audit: '0 plans in format', exit 0)" "$TMP/r-specs-as-docs" specs
said "reason" "docs mode would check nothing here"
never_said "specs as docs" "Docs in sync"

echo "== docs mode details =="
mkdir -p "$TMP/total"
{ echo "M1 [✅] 1/2"; echo "Total: 2/8"; echo "| ✅ | M1-T1 |"; echo "| ⬜ | M1-T2 |"; } > "$TMP/total/core-plan.md"
expect 1 "grand total drift" "$TMP/total"
said "the label the file uses is printed" "core-plan.md Total: header says 2/8"

plan "$TMP/blue-red" 4 4 4 4
printf '| Milestone | State |\n|---|---|\n| M1 ⬜ | open |\n' > "$TMP/blue-red/ARCHITECTURE.md"
expect 1 "blueprint still marks M1 ⬜ while the plan reports 4/4" "$TMP/blue-red"
plan "$TMP/blue-ok" 4 4 4 4
printf '| Milestone | State |\n|---|---|\n| M1 ✅ | done |\n' > "$TMP/blue-ok/ARCHITECTURE.md"
expect 0 "blueprint agrees with the plan" "$TMP/blue-ok"
said "blueprint ran" "blueprint checks ran"

echo "== a legacy code page must not turn green red (Windows pipes; audit finding F8) =="
# Measured on v1.3.2: PYTHONIOENCODING=cp1252 made the green line raise UnicodeEncodeError on
# the check mark, exit 1 — the chain was red on every green run.
PYTHONIOENCODING=cp1252 expect 0 "docs mode, green, cp1252 stdout" "$TMP/in-sync"
( cd "$TMP/g-draft" && PYTHONIOENCODING=cp1252 bash "$GATE" ) >"$TMP/out" 2>&1
if [ $? = 0 ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "  FAIL  spec-corpus mode, green, cp1252 stdout"; sed 's/^/        /' "$TMP/out"; fi

run_in 0 "--help" "$TMP" --help
run_in 2 "unknown option" "$TMP" --bogus

echo
echo "passed $PASS, failed $FAIL"
[ "$FAIL" -eq 0 ]
