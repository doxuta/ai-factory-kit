#!/usr/bin/env bash
# Two-direction test for run-chain.sh and gates/hooks/pre-commit.
# GATES.md §6: a gate proven in only one direction is decoration — and when a gate hands its
# verdict to someone else, test the CONSUMER. The consumer of the hook is git, so the last
# section makes real commits through core.hooksPath and checks that git refused or accepted.
#
# Run: bash gates/run-chain.test.sh      Exit 0 = all green.

HERE="$(cd "$(dirname "$0")" && pwd)"
PASS=0; FAIL=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.invalid
export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.invalid

STD="format static test build orphan-endpoints acceptance doc-sync spec-approval spec-numbers"

# project <dir>: a project root with the real runner, hook and shipped gates copied in
project() {
  mkdir -p "$1/gates/hooks"
  cp "$HERE/run-chain.sh" "$HERE/check-plan-sync.sh" "$HERE/check-spec-approval.sh" \
     "$HERE/check-spec-numbers.sh" "$HERE/check-specs.py" "$HERE/chain.conf.example" "$1/gates/"
  chmod +x "$1/gates/"*.sh
  if [ -f "$HERE/hooks/pre-commit" ]; then
    cp "$HERE/hooks/pre-commit" "$1/gates/hooks/" && chmod +x "$1/gates/hooks/pre-commit"
  fi
}
# conf <dir> <line>...: chain.conf from the given lines
conf() { local d="$1"; shift; printf '%s\n' "$@" > "$d/gates/chain.conf"; }
# all_true <dir> [override lines...]: every standard slot "true" unless overridden by name
all_true() {
  local d="$1" s line out=""
  shift
  for s in $STD; do
    line="$s: true"
    for o in "$@"; do case "$o" in "$s:"*) line="$o" ;; esac; done
    out="$out$line
"
  done
  printf '%s' "$out" > "$d/gates/chain.conf"
}
run() { # run <want-exit> <label> <project-dir> [args] — run from an unrelated cwd
  local want="$1" label="$2" dir="$3" got
  shift 3
  ( cd "$TMP" && bash "$dir/gates/run-chain.sh" ${1+"$@"} ) >"$TMP/out" 2>&1 </dev/null
  got=$?
  if [ "$got" = "$want" ]; then PASS=$((PASS+1)); else
    FAIL=$((FAIL+1)); printf '  FAIL  want exit %s, got %s — %s\n' "$want" "$got" "$label"
    sed 's/^/        /' "$TMP/out"; fi
}
said() {
  if grep -qF -- "$2" "$TMP/out"; then PASS=$((PASS+1)); else
    FAIL=$((FAIL+1)); printf '  FAIL  output lacks %s — %s\n' "$2" "$1"; sed 's/^/        /' "$TMP/out"; fi
}
check() { # check <label> <command...>: a plain assertion
  local label="$1"; shift
  if "$@"; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); printf '  FAIL  %s\n' "$label"; fi
}

echo "== GREEN: a wired chain must pass =="
project "$TMP/g-all"
all_true "$TMP/g-all"
run 0 "nine slots, all green" "$TMP/g-all"
said "summary" "GATE GREEN - 9 ran, 0 N/A"

project "$TMP/g-na"
all_true "$TMP/g-na" "orphan-endpoints: NA: single-user CLI, no routes" "acceptance: NA: no authorization boundary"
run 0 "NA slots with reasons" "$TMP/g-na"
said "reason printed" "orphan-endpoints: N/A - single-user CLI, no routes"
said "summary" "GATE GREEN - 7 ran, 2 N/A"

project "$TMP/g-order"
{ echo "# a comment"; echo; for s in $STD; do echo "$s: echo $s >> order.txt"; done
  echo "eval: echo eval >> order.txt"; } > "$TMP/g-order/gates/chain.conf"
run 0 "an extra slot is allowed and slots run in file order" "$TMP/g-order"
check "order.txt lists the ten slots in file order" \
  test "$(tr '\n' ' ' < "$TMP/g-order/order.txt")" = "$(printf '%s ' $STD eval)"

project "$TMP/g-root"
all_true "$TMP/g-root" "test: pwd > where.txt"
run 0 "commands run from the project root, whatever the caller's cwd" "$TMP/g-root"
check "where.txt is the project root" test "$(cat "$TMP/g-root/where.txt")" = "$(cd "$TMP/g-root" && pwd)"

project "$TMP/g-crlf"
all_true "$TMP/g-crlf"
awk '{ printf "%s\r\n", $0 }' "$TMP/g-crlf/gates/chain.conf" > "$TMP/x" && mv "$TMP/x" "$TMP/g-crlf/gates/chain.conf"
run 0 "a CRLF chain.conf (Windows checkout) parses the same" "$TMP/g-crlf"

project "$TMP/g-stdin"
all_true "$TMP/g-stdin" "test: cat > stdin.txt"
( cd "$TMP" && echo LEAKED | bash "$TMP/g-stdin/gates/run-chain.sh" ) > "$TMP/out" 2>&1
check "a slot reads /dev/null, not the caller's stdin (a prompt cannot hang a hook)" \
  test ! -s "$TMP/g-stdin/stdin.txt"

project "$TMP/g-env"
all_true "$TMP/g-env" 'test: test -z "${GIT_DIR:-}${GIT_INDEX_FILE:-}${GIT_WORK_TREE:-}"'
( cd "$TMP" && GIT_DIR=/nonexistent GIT_INDEX_FILE=/nonexistent/index GIT_WORK_TREE=/ \
    bash "$TMP/g-env/gates/run-chain.sh" ) > "$TMP/out" 2>&1
check "GIT_DIR / GIT_INDEX_FILE / GIT_WORK_TREE do not reach the slots" test "$?" = 0

project "$TMP/g-list"
cp "$TMP/g-list/gates/chain.conf.example" "$TMP/g-list/gates/chain.conf"
run 0 "--list on the shipped example: config valid, nothing run" "$TMP/g-list" --list
said "list summary" "9 slots - 3 wired, 0 N/A, 6 not wired"
said "list row" "doc-sync           run      ./gates/check-plan-sync.sh"

project "$TMP/g-bootstrap"
cp "$TMP/g-bootstrap/gates/chain.conf.example" "$TMP/g-bootstrap/gates/chain.conf"
sed -e 's/^format: TODO$/format: NA: nothing to format yet/' -e 's/^static: TODO$/static: true/' \
    -e 's/^test: TODO$/test: true/' -e 's/^build: TODO$/build: true/' \
    -e 's/^orphan-endpoints: TODO$/orphan-endpoints: NA: no routes yet/' \
    -e 's/^acceptance: TODO$/acceptance: NA: no authorization boundary/' \
    "$TMP/g-bootstrap/gates/chain.conf" > "$TMP/x" && mv "$TMP/x" "$TMP/g-bootstrap/gates/chain.conf"
run 0 "the shipped example with its TODOs wired: the real spec gates run on a fresh project" "$TMP/g-bootstrap"
said "doc-sync ran" "nothing to check yet (no specs/ or docs/)"
said "spec-numbers ran" "[9/9] spec-numbers: ok"

echo "== RED: it must actually bite =="
project "$TMP/r-example"
cp "$TMP/r-example/gates/chain.conf.example" "$TMP/r-example/gates/chain.conf"
run 1 "the shipped example as installed: honestly red until feature 001 wires it" "$TMP/r-example"
said "not wired" "[1/9] format: RED - not wired (TODO)"

project "$TMP/r-fail"
all_true "$TMP/r-fail" "test: echo ran-test > test.ran; exit 3" "build: echo ran-build > build.ran"
run 1 "a failing slot" "$TMP/r-fail"
said "which slot" "GATE RED at 'test'"
said "later slots listed" "not run: build orphan-endpoints"
check "the red slot ran" test -f "$TMP/r-fail/test.ran"
check "nothing after the first red ran" test ! -f "$TMP/r-fail/build.ran"

project "$TMP/r-pipe"
all_true "$TMP/r-pipe" "test: false | cat"
run 1 "pipefail: a failing command piped into cat is still red" "$TMP/r-pipe"

project "$TMP/r-126"
printf 'echo hi\n' > "$TMP/r-126/gates/no-exec.sh"
all_true "$TMP/r-126" "static: ./gates/no-exec.sh"
run 1 "a script without its execute bit (exit 126) says why" "$TMP/r-126"
said "hint" "not executable?"

project "$TMP/r-realgate"
all_true "$TMP/r-realgate" "doc-sync: ./gates/check-plan-sync.sh" "spec-approval: ./gates/check-spec-approval.sh"
mkdir -p "$TMP/r-realgate/specs/001-a"
printf -- '---\nfeature: 001-a\nstatus: draft\nepic: core\n---\n' > "$TMP/r-realgate/specs/001-a/spec.md"
printf -- '- [x] T001 built before approval\n' > "$TMP/r-realgate/specs/001-a/tasks.md"
run 1 "a real shipped gate going red stops the chain (checked task on a draft spec)" "$TMP/r-realgate"
said "which slot" "GATE RED at 'spec-approval'"

echo "== config errors (exit 2): a broken chain.conf must not look like a verdict =="
project "$TMP/c-none"
run 2 "no gates/chain.conf" "$TMP/c-none"
said "reason" "not found"

project "$TMP/c-missing"
all_true "$TMP/c-missing"
grep -v '^acceptance:' "$TMP/c-missing/gates/chain.conf" > "$TMP/x" && mv "$TMP/x" "$TMP/c-missing/gates/chain.conf"
run 2 "a standard slot deleted from chain.conf" "$TMP/c-missing"
said "reason" "not declared: acceptance"

project "$TMP/c-dup"
all_true "$TMP/c-dup"
echo "test: false" >> "$TMP/c-dup/gates/chain.conf"
run 2 "a slot declared twice" "$TMP/c-dup"
said "reason" "declared twice"

for bad in "NA:" "NA:   " "N/A: no routes" "NA no routes" "na: no routes"; do
  project "$TMP/c-na"
  all_true "$TMP/c-na" "orphan-endpoints: $bad"
  run 2 "orphan-endpoints: '$bad'" "$TMP/c-na"
  rm -rf "$TMP/c-na"
done

project "$TMP/c-empty"
all_true "$TMP/c-empty" "build:"
run 2 "an empty slot" "$TMP/c-empty"

project "$TMP/c-garbage"
all_true "$TMP/c-garbage"
echo "run the tests please" >> "$TMP/c-garbage/gates/chain.conf"
run 2 "a line that is not '<slot>: ...'" "$TMP/c-garbage"
project "$TMP/c-upper"
all_true "$TMP/c-upper"
echo "Eval: true" >> "$TMP/c-upper/gates/chain.conf"
run 2 "an upper-case slot name" "$TMP/c-upper"

project "$TMP/c-allna"
: > "$TMP/c-allna/gates/chain.conf"
for s in $STD; do echo "$s: NA: nothing here" >> "$TMP/c-allna/gates/chain.conf"; done
run 2 "every slot N/A: a chain that checks nothing is not green" "$TMP/c-allna"
said "reason" "checks nothing"

run 0 "--help" "$TMP/g-all" --help
run 2 "unknown argument" "$TMP/g-all" --bogus

echo "== the CONSUMER: git itself refuses and accepts commits through gates/hooks/pre-commit =="
if ! command -v git >/dev/null 2>&1; then
  echo "  (git not installed: hook section skipped)"
elif [ ! -f "$HERE/hooks/pre-commit" ]; then
  # adopt.py installs this test into a project's gates/ always, the hook only with
  # --install-git-hook. In the kit itself the hook is always there, so this never skips in CI.
  echo "  (gates/hooks/pre-commit not installed here - hook section skipped;"
  echo "   adopt.py --install-git-hook installs it)"
else
  P="$TMP/repo"
  project "$P"
  all_true "$P" "test: test ! -f RED"
  git -C "$P" init -q
  git -C "$P" config core.hooksPath gates/hooks
  echo one > "$P/a.txt"
  touch "$P/RED"
  git -C "$P" add a.txt gates
  ( cd "$P" && git commit -q -m "should be refused" ) > "$TMP/out" 2>&1
  check "git commit refused while a slot is red" test "$?" -ne 0
  said "the refusal names its source" "commit REFUSED by gates/hooks/pre-commit"
  check "no commit was created" test -z "$(git -C "$P" rev-list --all 2>/dev/null)"
  rm "$P/RED"
  ( cd "$P" && git commit -q -m "should land" ) > "$TMP/out" 2>&1
  check "git commit accepted once the chain is green" test "$(git -C "$P" rev-list --count HEAD 2>/dev/null)" = 1

  # A test suite that builds its own scratch repository must not write into this one, even
  # from a linked worktree, where git hands the hook GIT_DIR and GIT_INDEX_FILE (measured).
  W="$TMP/wt"
  git -C "$P" worktree add -q "$W" -b side 2>/dev/null
  cat > "$W/gates/chain.conf" <<'CONF'
format: true
static: true
test: d="$(mktemp -d)" && cd "$d" && git init -q && echo x > scratch.txt && git add scratch.txt && git commit -q -m scratch && test "$(git rev-list --count HEAD)" = 1
build: true
orphan-endpoints: true
acceptance: true
doc-sync: true
spec-approval: true
spec-numbers: true
CONF
  echo two > "$W/b.txt"
  git -C "$W" add b.txt gates/chain.conf
  ( cd "$W" && git commit -q -m "worktree commit" ) > "$TMP/out" 2>&1
  check "worktree commit through the hook succeeds" test "$?" = 0
  check "the scratch repo's file never entered this repository" \
    test -z "$(git -C "$W" log --all --format=%H -- scratch.txt)"

  rm "$P/gates/run-chain.sh"
  echo three > "$P/c.txt"; git -C "$P" add c.txt
  ( cd "$P" && git commit -q -m "no runner" ) > "$TMP/out" 2>&1
  check "a missing run-chain.sh refuses the commit (fails closed)" test "$?" -ne 0
  said "says why" "is missing - commit REFUSED"
fi

echo
echo "passed $PASS, failed $FAIL"
[ "$FAIL" -eq 0 ]
