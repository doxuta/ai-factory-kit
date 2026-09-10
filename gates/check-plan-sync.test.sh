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
    for i in $(seq 1 "$tdone");   do echo "| ✅ | M1-T$i |"; done
    for i in $(seq $((tdone+1)) "$ttotal"); do echo "| ⬜ | M1-T$i |"; done
  } > "$dir/demo-plan.md"
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

echo
echo "passed $PASS, failed $FAIL"
[ "$FAIL" -eq 0 ]
