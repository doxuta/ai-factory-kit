#!/usr/bin/env bash
# Two-direction test for check-spec-approval.sh (and the approval half of check-specs.py).
# GATES.md §6: a gate proven in only one direction is decoration. Every RED row also pins the
# reason, because a fixture that fails for the wrong reason proves nothing (this kit's
# check-plan-sync test once passed all its red rows without exercising the comparison).
#
# Run: bash gates/check-spec-approval.test.sh      Exit 0 = all green.

GATE="$(cd "$(dirname "$0")" && pwd)/check-spec-approval.sh"
PASS=0; FAIL=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# run_in <want-exit> <label> <project-dir> [gate args...]
run_in() {
  local want="$1" label="$2" dir="$3" got
  shift 3
  ( cd "$dir" && bash "$GATE" ${1+"$@"} ) >"$TMP/out" 2>&1
  got=$?
  if [ "$got" = "$want" ]; then PASS=$((PASS+1)); else
    FAIL=$((FAIL+1)); printf '  FAIL  want exit %s, got %s — %s\n' "$want" "$got" "$label"
    sed 's/^/        /' "$TMP/out"; fi
}
said() {
  if grep -qF -- "$2" "$TMP/out"; then PASS=$((PASS+1)); else
    FAIL=$((FAIL+1)); printf '  FAIL  output lacks %s — %s\n' "$2" "$1"; sed 's/^/        /' "$TMP/out"; fi
}

# spec <project> <id> <status> [frontmatter line]...  — no approval lines unless given
spec() {
  local proj="$1" id="$2" status="$3" line
  shift 3
  mkdir -p "$proj/specs/$id"
  { echo "---"; echo "feature: $id"; echo "status: $status"; echo "epic: core"
    for line in ${1+"$@"}; do echo "$line"; done
    echo "---"; echo; echo "# Feature Specification: $id"; } > "$proj/specs/$id/spec.md"
}
approved() { # approved <project> <id> <status> [extra line]...
  local proj="$1" id="$2" status="$3"
  shift 3
  spec "$proj" "$id" "$status" "approved_by: Owner Name" "approved_on: 2026-09-01" ${1+"$@"}
}
tasks() { # tasks <project> <id> <line>...
  local proj="$1" id="$2" line
  shift 2
  { echo "# Tasks: $id"; for line in "$@"; do echo "$line"; done; } > "$proj/specs/$id/tasks.md"
}
# acceptance <project> <id> [override lines replace the defaults: pass them as key: value]
acceptance() {
  local proj="$1" id="$2"
  shift 2
  if [ "$#" -eq 0 ]; then
    set -- "accepted_on: 2026-09-03" "accepted_by: Lan (QA)" "run_as: member account, not admin" "result: pass"
  fi
  { echo "# Acceptance — $id"; local l; for l in "$@"; do echo "$l"; done
    echo; echo "Ran quickstart.md steps 1-5; output below."; } > "$proj/specs/$id/acceptance.md"
}

echo "== GREEN: legitimate states must pass =="
mkdir -p "$TMP/g-none"
run_in 0 "no specs/ yet (a fresh project)" "$TMP/g-none"
said "attributed" "nothing to check yet"

spec "$TMP/g-draft" 001-alpha draft
tasks "$TMP/g-draft" 001-alpha "- [ ] T001 not started" "- [ ] T002 not started"
run_in 0 "draft spec with only unchecked tasks" "$TMP/g-draft"

approved "$TMP/g-approved" 001-alpha approved
tasks "$TMP/g-approved" 001-alpha "- [x] T001 done" "- [ ] T002 next"
run_in 0 "approved (by + on recorded), work under way" "$TMP/g-approved"

approved "$TMP/g-accepted" 001-alpha accepted
tasks "$TMP/g-accepted" 001-alpha "- [x] T001 done"
acceptance "$TMP/g-accepted" 001-alpha
run_in 0 "accepted with a valid acceptance.md" "$TMP/g-accepted"
said "summary" "Spec approvals recorded"

approved "$TMP/g-released" 001-alpha released
acceptance "$TMP/g-released" 001-alpha "accepted_on: 2026-09-01" "accepted_by: Lan" "run_as: n/a — no authorization boundary" "result: pass"
run_in 0 "released; run_as n/a WITH its reason; accepted the day it was approved" "$TMP/g-released"

approved "$TMP/g-shipped" 001-alpha shipped
acceptance "$TMP/g-shipped" 001-alpha
run_in 0 "legacy status shipped with acceptance.md" "$TMP/g-shipped"

approved "$TMP/g-super" 001-alpha superseded "superseded_by: 002-beta"
approved "$TMP/g-super" 002-beta approved
run_in 0 "superseded needs its approval record, not an acceptance run" "$TMP/g-super"

approved "$TMP/g-shape" 001-alpha accepted
{ printf '<!-- WHO READS ME: the owner. -->\r\n\r\n# Acceptance - 001-alpha\r\n'
  printf 'accepted_on: 2026-09-05\r\naccepted_by: Lan\r\nrun_as: viewer role\r\nresult: pass\r\n'
  printf '\r\n```console\r\n$ curl ...\r\nresult: fail   <- an old run, inside a fence\r\n```\r\n'; } > "$TMP/g-shape/specs/001-alpha/acceptance.md"
run_in 0 "acceptance.md with a header comment, CRLF, '-' heading, a fenced transcript" "$TMP/g-shape"

mkdir -p "$TMP/g-quoted/specs/002-q"
printf -- '---\nfeature: 002-q\nstatus: approved  # since the review\nepic: core\napproved_by: "Tai Nguyen"   # owner\napproved_on: 2026-09-02 # YYYY-MM-DD\n---\n' > "$TMP/g-quoted/specs/002-q/spec.md"
run_in 0 "quoted approver and inline comments" "$TMP/g-quoted"

echo "== RED: it must actually bite =="
spec "$TMP/r-draft" 001-alpha draft
tasks "$TMP/r-draft" 001-alpha "- [x] T001 built before approval" "- [ ] T002"
run_in 1 "a checked task while status is draft (the HARD-GATE)" "$TMP/r-draft"
said "reason" "1 task checked while status is draft"

spec "$TMP/r-draft-X" 001-alpha draft
tasks "$TMP/r-draft-X" 001-alpha "- [X] T001 implement wrote [X]"
run_in 1 "[X] counts as checked on a draft too" "$TMP/r-draft-X"

spec "$TMP/r-draft-ol" 001-alpha draft
tasks "$TMP/r-draft-ol" 001-alpha "1. [x] T001 an ordered-list checkbox is still a checkbox"
run_in 1 "an ordered-list '1. [x]' task on a draft" "$TMP/r-draft-ol"

spec "$TMP/r-noby" 001-alpha approved "approved_on: 2026-09-01"
run_in 1 "approved without approved_by" "$TMP/r-noby"
said "reason" "approved_by is missing"

spec "$TMP/r-ph" 001-alpha approved "approved_by: <name>" "approved_on: 2026-09-01"
run_in 1 "approved_by left as the template placeholder <name>" "$TMP/r-ph"
said "reason" "a placeholder"
spec "$TMP/r-ph2" 001-alpha approved "approved_by: [OWNER]" "approved_on: 2026-09-01"
run_in 1 "approved_by [OWNER]" "$TMP/r-ph2"

spec "$TMP/r-noon" 001-alpha approved "approved_by: Owner"
run_in 1 "approved without approved_on" "$TMP/r-noon"
said "reason" "approved_on is missing"
spec "$TMP/r-baddate" 001-alpha approved "approved_by: Owner" "approved_on: yesterday"
run_in 1 "approved_on is not a date" "$TMP/r-baddate"
said "reason" "not a YYYY-MM-DD date"
spec "$TMP/r-feb30" 001-alpha approved "approved_by: Owner" "approved_on: 2026-02-30"
run_in 1 "approved_on 2026-02-30 does not exist" "$TMP/r-feb30"

approved "$TMP/r-noacc" 001-alpha accepted
tasks "$TMP/r-noacc" 001-alpha "- [x] T001 done"
run_in 1 "accepted without acceptance.md" "$TMP/r-noacc"
said "reason" "acceptance.md: missing"
approved "$TMP/r-noacc-shipped" 001-alpha shipped
run_in 1 "legacy shipped without acceptance.md" "$TMP/r-noacc-shipped"

approved "$TMP/r-fail" 001-alpha accepted
acceptance "$TMP/r-fail" 001-alpha "accepted_on: 2026-09-03" "accepted_by: Lan" "run_as: member" "result: fail"
run_in 1 "result: fail" "$TMP/r-fail"
said "reason" "not pass"

approved "$TMP/r-norunas" 001-alpha released
acceptance "$TMP/r-norunas" 001-alpha "accepted_on: 2026-09-03" "accepted_by: Lan" "result: pass"
run_in 1 "run_as missing" "$TMP/r-norunas"
said "reason" "no run_as: line"

approved "$TMP/r-na" 001-alpha accepted
acceptance "$TMP/r-na" 001-alpha "accepted_on: 2026-09-03" "accepted_by: Lan" "run_as: n/a" "result: pass"
run_in 1 "run_as n/a without its reason" "$TMP/r-na"
said "reason" "needs its reason"

approved "$TMP/r-accby" 001-alpha accepted
acceptance "$TMP/r-accby" 001-alpha "accepted_on: 2026-09-03" "accepted_by: <who ran quickstart.md — never the builder>" "run_as: member" "result: pass"
run_in 1 "accepted_by left as the template placeholder" "$TMP/r-accby"
said "reason" "accepted_by is empty or a placeholder"

approved "$TMP/r-heading" 001-alpha accepted
acceptance "$TMP/r-heading" 001-alpha
sed 's/^# Acceptance — 001-alpha$/# Acceptance — 002-beta/' "$TMP/r-heading/specs/001-alpha/acceptance.md" > "$TMP/x"
mv "$TMP/x" "$TMP/r-heading/specs/001-alpha/acceptance.md"
run_in 1 "acceptance.md copied from another spec (heading names 002-beta)" "$TMP/r-heading"
said "reason" "copied from another spec"

approved "$TMP/r-early" 001-alpha accepted
acceptance "$TMP/r-early" 001-alpha "accepted_on: 2026-08-15" "accepted_by: Lan" "run_as: member" "result: pass"
run_in 1 "accepted_on before approved_on" "$TMP/r-early"
said "reason" "is before approved_on 2026-09-01"

approved "$TMP/r-dup" 001-alpha accepted
acceptance "$TMP/r-dup" 001-alpha "accepted_on: 2026-09-03" "accepted_by: Lan" "run_as: member" "result: fail" "result: pass"
run_in 1 "two result: lines (which one is true?)" "$TMP/r-dup"
said "reason" "duplicate result:"

approved "$TMP/r-fenced" 001-alpha accepted
{ echo "# Acceptance — 001-alpha"; echo '```'; echo "accepted_on: 2026-09-03"; echo "accepted_by: Lan"
  echo "run_as: member"; echo "result: pass"; echo '```'; } > "$TMP/r-fenced/specs/001-alpha/acceptance.md"
run_in 1 "the record only inside a code fence (an example, not a record)" "$TMP/r-fenced"
said "reason" "no accepted_on: line"

mkdir -p "$TMP/r-nofm/specs/001-alpha"
printf '# Spec\n\n**Status**: Draft\n' > "$TMP/r-nofm/specs/001-alpha/spec.md"
tasks "$TMP/r-nofm" 001-alpha "- [x] T001 done"
run_in 1 "no frontmatter: the gate cannot read the status, so it does not guess" "$TMP/r-nofm"
said "reason" "cannot read the status"

mkdir -p "$TMP/r-nospec/specs/001-alpha"
tasks "$TMP/r-nospec" 001-alpha "- [x] T001 done"
run_in 1 "tasks.md with no spec.md (deleting the spec must not open the gate)" "$TMP/r-nospec"
said "reason" "no spec.md"

mkdir -p "$TMP/r-dupstatus/specs/001-alpha"
printf -- '---\nfeature: 001-alpha\nstatus: approved\nepic: core\napproved_by: Owner\napproved_on: 2026-09-01\nstatus: draft\n---\n' > "$TMP/r-dupstatus/specs/001-alpha/spec.md"
tasks "$TMP/r-dupstatus" 001-alpha "- [x] T001 done"
run_in 1 "two status: lines - the gate does not pick one and hope" "$TMP/r-dupstatus"
said "reason" "duplicate key 'status'"

spec "$TMP/r-badtasks" 001-alpha draft
printf -- '- [x] T001 done \377\n' > "$TMP/r-badtasks/specs/001-alpha/tasks.md"
run_in 1 "tasks.md that is not UTF-8 cannot hide a checked task on a draft" "$TMP/r-badtasks"
said "reason" "tasks.md: not valid UTF-8"

spec "$TMP/r-unknown" 001-alpha "done" "approved_by: Owner" "approved_on: 2026-09-01"
run_in 1 "unknown status" "$TMP/r-unknown"

mkdir -p "$TMP/r-arg"
run_in 1 "a specs dir you name that does not exist" "$TMP/r-arg" product/specs
said "reason" "specs dir not found"

echo "== open clarifications and 1.3.x rows (review 2026-09-29) =="
approved "$TMP/c-open" 001-alpha approved
echo "- **FR-009**: [NEEDS CLARIFICATION: timezone?]" >> "$TMP/c-open/specs/001-alpha/spec.md"
run_in 1 "approved with an open [NEEDS CLARIFICATION]" "$TMP/c-open"
said "reason" "1 [NEEDS CLARIFICATION] marker is still open (line 10)"
approved "$TMP/c-acc" 001-alpha accepted
printf '%s\n' "- a [NEEDS CLARIFICATION: x]" "- b [NEEDS CLARIFICATION: y]" >> "$TMP/c-acc/specs/001-alpha/spec.md"
acceptance "$TMP/c-acc" 001-alpha
run_in 1 "accepted with two open markers" "$TMP/c-acc"
said "count" "2 [NEEDS CLARIFICATION] markers are still open"
spec "$TMP/c-draft" 001-alpha draft
echo "- **FR-009**: [NEEDS CLARIFICATION: timezone?]" >> "$TMP/c-draft/specs/001-alpha/spec.md"
run_in 0 "a draft may hold open questions" "$TMP/c-draft"
approved "$TMP/c-quoted" 001-alpha approved
printf '%s\n' '<!-- mark gaps as [NEEDS CLARIFICATION: q] -->' 'Markers look like `[NEEDS CLARIFICATION: q]`.' \
  '```' '[NEEDS CLARIFICATION: in a fence]' '```' >> "$TMP/c-quoted/specs/001-alpha/spec.md"
run_in 0 "a marker quoted in a comment, a code span or a fence is not open" "$TMP/c-quoted"
spec "$TMP/m-draft" 001-alpha draft
tasks "$TMP/m-draft" 001-alpha "| ✅ | M1-T1 | done before approval |"
run_in 1 "a ticked 1.3.x row on a draft spec" "$TMP/m-draft"
said "reason" "1 task checked while status is draft"

run_in 0 "--help" "$TMP" --help
run_in 2 "unknown option" "$TMP" --bogus

echo
echo "passed $PASS, failed $FAIL"
[ "$FAIL" -eq 0 ]
