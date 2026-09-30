#!/usr/bin/env bash
# Test for bin/metrics.py on a scripted history whose right answers are known by construction.
# metrics.py is a report, not a gate, but a wrong number is worse than none: each assertion
# below names the commit that makes it true.
#
# Run: bash bin/metrics.test.sh      Exit 0 = all green.

METRICS="$(cd "$(dirname "$0")" && pwd)/metrics.py"
PASS=0; FAIL=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.invalid
export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.invalid

check() { # check <label> <python expression over j (the --json result)>
  if python3 -c "import json,sys; j=json.load(open(sys.argv[1])); sys.exit(0 if ($2) else 1)" "$TMP/out.json"; then
    PASS=$((PASS+1))
  else
    FAIL=$((FAIL+1)); printf '  FAIL  %s\n        %s\n' "$1" "$2"
  fi
}
R="$TMP/repo"
n=0
commit() { # commit <iso-date> <message>  (message may hold \n; trailers go in the last paragraph)
  n=$((n+1)); echo "$n" > "$R/file.txt"; git -C "$R" add -A
  GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git -C "$R" commit -q --no-verify -m "$(printf '%b' "$2")"
}
spec() { # spec <id> <approved_on>
  mkdir -p "$R/specs/$1"
  printf -- '---\nfeature: %s\nstatus: approved\nepic: core\napproved_by: Owner\napproved_on: %s  # date\n---\n' "$1" "$2" > "$R/specs/$1/spec.md"
}

mkdir -p "$R" && git -C "$R" init -q
commit 2026-09-01T09:00:00+00:00 "chore: init"                                           # 1
spec 001-a 2026-09-04
commit 2026-09-01T10:00:00+00:00 "docs(spec): 001-a\n\nSpec: 001-a"                      # 2
commit 2026-09-05T10:00:00+00:00 "feat(a): first cut\n\nWhy it matters.\n\nSpec: 001-a\nTask: T001"  # 3 landing A
commit 2026-09-05T11:00:00+00:00 "test: more cases"                                      # 4
commit 2026-09-05T12:00:00+00:00 "fix(a): wire the caller\n\nSpec: 001-a\nBug-class: escaped-joint"  # 5 corrects 3 (+2)
spec 002-b 2026-08-30
commit 2026-09-06T10:00:00+00:00 "feat(b): export\n\nSpec: 002-b"                        # 6 landing B, never corrected
commit 2026-09-07T10:00:00+00:00 "feat(a): second cut\n\nSpec: 001-a"                    # 7 landing C
commit 2026-09-07T11:00:00+00:00 "feat(c): experiment\n\nSpec: 003-c"                    # 8 landing D
commit 2026-09-07T12:00:00+00:00 "Revert \"feat(c): experiment\"\n\nSpec: 003-c"         # 9 corrects 8 (+1)
commit 2026-09-07T13:00:00+00:00 "feat(b): no trailer here, Spec: 002-b is in the subject" # 10 not a landing
commit 2026-09-07T14:00:00+00:00 "fix(b): trailer not in the last paragraph\n\nSpec: 002-b\n\nA closing remark." # 11
for i in 1 2 3 4 5 6 7; do commit "2026-09-08T0$i:00:00+00:00" "chore: filler $i"; done   # 12-18
commit 2026-09-09T10:00:00+00:00 "fix(a): late\n\nSpec: 001-a"                           # 19: 12 after 7
git -C "$R" checkout -q -b side
commit 2026-09-10T10:00:00+00:00 "chore: on a branch"                                    # 20
git -C "$R" checkout -q -
GIT_AUTHOR_DATE=2026-09-10T11:00:00+00:00 GIT_COMMITTER_DATE=2026-09-10T11:00:00+00:00 \
  git -C "$R" merge -q --no-ff --no-edit side -m "$(printf 'Merge side\n\nSpec: 001-a')"  # merge: skipped

( cd "$R" && python3 "$METRICS" --json ) > "$TMP/out.json" 2>"$TMP/err"
check "exit 0 and JSON out" "True"
check "20 non-merge commits; the merge is skipped" "j['commits'] == 20"
check "Spec: trailer in the last paragraph only: 8 commits (2,3,5,6,7,8,9,19; not 10, not 11)" "j['commits_with_spec'] == 8"
check "four feat landings with a trailer (3, 6, 7, 8)" "j['feat_landings'] == 4"
check "two corrected within 10: 3 by fix 5 (+2), 8 by revert 9 (+1)" \
  "sorted((c['spec'], c['distance']) for c in j['corrected']) == [('001-a', 2), ('003-c', 1)]"
check "land rate 2/4" "j['first_pass_land_rate'] == 0.5"
check "one escaped joint, on 001-a" "j['escaped_joints'] == {'001-a': 1}"
check "approval latency: 001-a added 09-01, approved 09-04 = 3 days" \
  "[r['days'] for r in j['approval_latency'] if r['spec'] == '001-a'] == [3]"
check "002-b approved before its first commit: not measurable, not negative" \
  "[r['days'] for r in j['approval_latency'] if r['spec'] == '002-b'] == [None]"
check "median over measurable specs only" "j['approval_latency_median_days'] == 3"

( cd "$R" && python3 "$METRICS" --json --window 20 ) > "$TMP/out.json" 2>"$TMP/err"
check "--window 20 also counts fix 19 against landing 7 (+12)" \
  "sorted((c['spec'], c['distance']) for c in j['corrected']) == [('001-a', 2), ('001-a', 12), ('003-c', 1)]"

( cd "$R" && python3 "$METRICS" ) > "$TMP/out.txt" 2>&1
if grep -q "^Trailer coverage      8/20 (40%)" "$TMP/out.txt" && grep -q "^First-pass land rate  2/4 (50%)" "$TMP/out.txt"; then
  PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "  FAIL  text report"; sed 's/^/        /' "$TMP/out.txt"; fi

mkdir -p "$TMP/notgit"
( cd "$TMP/notgit" && python3 "$METRICS" ) >/dev/null 2>&1
if [ $? = 2 ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "  FAIL  outside a git repository: want exit 2"; fi

echo
echo "passed $PASS, failed $FAIL"
[ "$FAIL" -eq 0 ]
