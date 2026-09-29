#!/usr/bin/env bash
# Two-direction test for check-spec-numbers.sh. GATES.md §6: a gate proven in only one
# direction is decoration; every RED row also pins its reason.
#
# Run: bash gates/check-spec-numbers.test.sh      Exit 0 = all green.

GATE="$(cd "$(dirname "$0")" && pwd)/check-spec-numbers.sh"
PASS=0; FAIL=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

run_in() { # run_in <want-exit> <label> <project-dir> [gate args...]
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
dirs() { # dirs <project> <name>...
  local proj="$1" d
  shift
  mkdir -p "$proj/specs"
  for d in "$@"; do mkdir -p "$proj/specs/$d"; done
}

echo "== GREEN: legitimate layouts must pass =="
mkdir -p "$TMP/g-none"
run_in 0 "no specs/ yet" "$TMP/g-none"
said "attributed" "nothing to check yet"

dirs "$TMP/g-seq" 001-base 002-login-page 003-payment-export 1000-big
run_in 0 "sequential, including a 4-digit number" "$TMP/g-seq"
said "summary" "4 spec directories (4 sequential, 0 timestamp)"

dirs "$TMP/g-ts" 20260929-101500-login-page 20260929-101501-payment-export
run_in 0 "timestamp prefixes one second apart" "$TMP/g-ts"

dirs "$TMP/g-mixed" 001-base 002-login 20260929-101500-export
run_in 0 "sequential and timestamp together (numbering switched midway)" "$TMP/g-mixed"

dirs "$TMP/g-ignored" 001-base .obsidian
printf 'notes\n' > "$TMP/g-ignored/specs/README.md"
run_in 0 "hidden dirs and plain files in specs/ are ignored" "$TMP/g-ignored"

dirs "$TMP/g-ts-vs-seq" 20260929-101500-a 002-b
run_in 0 "a timestamp dir never collides with a sequential number" "$TMP/g-ts-vs-seq"

echo "== RED: it must actually bite =="
dirs "$TMP/r-merge" 001-base 002-login-page 002-payment-export
run_in 1 "two branches both took 002 and git merged both (the audit's repro)" "$TMP/r-merge"
said "reason" "number 002 is used by 002-login-page and 002-payment-export"

dirs "$TMP/r-pad" 007-a 0007-b
run_in 1 "007 and 0007 are the same number" "$TMP/r-pad"
said "reason" "number 007 is used by 0007-b and 007-a"

dirs "$TMP/r-ts" 20260929-101500-a 20260929-101500-b
run_in 1 "same timestamp twice" "$TMP/r-ts"
said "reason" "timestamp 20260929-101500 is used by"

dirs "$TMP/r-name" 001-base login-page
run_in 1 "a directory with no number" "$TMP/r-name"
said "reason" "login-page: not an NNN-<name>"

dirs "$TMP/r-short" 01-base
run_in 1 "a 2-digit prefix is not Spec Kit's 3+ digits" "$TMP/r-short"

mkdir -p "$TMP/r-arg"
run_in 1 "a specs dir you name that does not exist" "$TMP/r-arg" product/specs
said "reason" "specs dir not found"

run_in 0 "--help" "$TMP" --help
run_in 2 "unknown option" "$TMP" --bogus

echo
echo "passed $PASS, failed $FAIL"
[ "$FAIL" -eq 0 ]
