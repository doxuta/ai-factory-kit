<!-- WHO READS ME: anyone who wants to see what the 1.4.0 gate chain prints on a project that is
     not a web app — read after the spec files. I POINT TO: gates/chain.conf (the slots run
     below) · specs/001-monthly-spending-report/tasks.md (T014, T019, T020, T018) ·
     ../../gates/run-chain.sh and ../../gates/hooks/pre-commit (what printed this) ·
     ../../gates/GATES.md (the doctrine) · constitution.md (Articles I, II, V, VI). -->

# Gate run — budget-cli feature 001, from walking skeleton to accepted

Every line in the transcripts below was printed by a real run on 2026-09-29. The run replayed
feature 001's history in a scratch git repository: this kit (1.4.0) adopted with
`adopt.py --profile cli`, specify-cli 1.0.12, this directory's documents copied in, and
about 240 lines of Python under `src/budget/` and `tests/`. Tools: Python 3.11.15,
ruff 0.16.9, pytest 9.1.1, uv 0.8.17. Commit hashes are the replay's.

The source is not shipped with the kit, which sits inside every adopter's repository as
`factory/`: with a `tests/` directory under `factory/examples/budget-cli/`, a plain
`pytest -q` at an adopter's root collected it and stopped with `1 error during collection`
(pytest 9.1.1, no `testpaths` configured). The spec slots can be re-run on this directory as
it is — see [Reproduce](#reproduce).

## The chain

```console
$ ./gates/run-chain.sh --list
gates/chain.conf: 10 slots - 9 wired, 1 N/A, 0 not wired
  format             run      ruff format --check .
  static             run      ruff check .
  privacy            run      grep -rnE '(^|[^[:alnum:]_])float\(|^[[:space:]]*(import|from)[[:space:]]+(socket|ssl|http|urllib|requests|httpx|ftplib|smtplib)([.[:space:],]|$)' src/budget; [ $? -eq 1 ]
  test               run      pytest -q tests/unit
  build              run      uv build
  orphan-endpoints   N/A      no network routes; the product's only entry point is the budget command, and tests/e2e runs every subcommand through it
  acceptance         run      pytest -q tests/e2e
  doc-sync           run      ./gates/check-plan-sync.sh
  spec-approval      run      ./gates/check-spec-approval.sh
  spec-numbers       run      ./gates/check-spec-numbers.sh
```

Nine standard slots plus `privacy`, an extra slot for Article II. The web example has an
orphan-endpoint gate here; a CLI has no routes, so the slot says N/A and why, on every run.

## Scene 1 — the hook refuses a red commit (T014)

The walking skeleton's last proof: with the pre-commit hook installed
(`adopt.py --install-git-hook --ci github`, T012), a deliberately unformatted line in
`src/budget/render.py` must not get in.

```console
$ git commit -m "test(gates): an unformatted file must be refused"
gate chain: 10 slots from gates/chain.conf (9 wired, 1 N/A, 0 not wired)
[1/10] format: $ ruff format --check .
unformatted: File would be reformatted
 --> src/budget/render.py:5:32
  |
4 | def render(report, read, accepted, rejected) -> str:
  -     lines = [f"{m}  {v}" for m,v in report.months]
5 +     lines = [f"{m}  {v}" for m, v in report.months]
6 |     lines.append(f"TOTAL  {report.total}")
  |

1 file would be reformatted, 14 files already formatted
[1/10] format: RED - exit 1
      not run: static privacy test build orphan-endpoints acceptance doc-sync spec-approval spec-numbers
GATE RED at 'format' - no commit on red. Fix it, or explicitly revert (GATES.md section 1).
pre-commit: commit REFUSED by gates/hooks/pre-commit - gates/run-chain.sh exited 1.
pre-commit: fix the red slot or explicitly revert; do not --no-verify (GATES.md section 1).
exit=1
```

The file was reverted and T014 ticked in its own commit.

## Scene 2 — converge finds a real bug; the test comes first (T019)

`/speckit-converge` compared the code with the spec and appended two tasks. T019: a statement
exported from a spreadsheet starts with a UTF-8 byte-order mark, and the parser, which opened
the file as `utf-8`, then saw a first column named `﻿date` and rejected every row as
`unreadable date` — SC-003 ("a report from an exported file") was only partly delivered. The
spec was right and the code was wrong, so the spec did not change; a task was recorded. The
test went in first:

```console
$ ./gates/run-chain.sh
gate chain: 10 slots from gates/chain.conf (9 wired, 1 N/A, 0 not wired)
[1/10] format: $ ruff format --check .
15 files already formatted
[1/10] format: ok
[2/10] static: $ ruff check .
All checks passed!
[2/10] static: ok
[3/10] privacy: $ grep -rnE '(^|[^[:alnum:]_])float\(|^[[:space:]]*(import|from)[[:space:]]+(socket|ssl|http|urllib|requests|httpx|ftplib|smtplib)([.[:space:],]|$)' src/budget; [ $? -eq 1 ]
[3/10] privacy: ok
[4/10] test: $ pytest -q tests/unit
..F..                                                                    [100%]
=================================== FAILURES ===================================
____________________ test_file_with_byte_order_mark_is_read ____________________

    def test_file_with_byte_order_mark_is_read():
        # Spreadsheet exports often start with a UTF-8 byte-order mark (T019).
        res = parse_file(FIX / "bom.csv")
>       assert res.rejected == []
E       AssertionError: assert [Rejected(lin...adable date')] == []
E         
E         Left contains one more item: Rejected(line=2, reason='unreadable date')
E         Use -v to get more diff

tests/unit/test_parse.py:35: AssertionError
=========================== short test summary info ============================
FAILED tests/unit/test_parse.py::test_file_with_byte_order_mark_is_read - Ass...
1 failed, 4 passed in 0.03s
[4/10] test: RED - exit 1
      not run: build orphan-endpoints acceptance doc-sync spec-approval spec-numbers
GATE RED at 'test' - no commit on red. Fix it, or explicitly revert (GATES.md section 1).
exit=1
```

The fix is one argument, in the layer that owns reading files (Article III):

```diff
-    with open(path, newline="", encoding="utf-8") as fh:
+    with open(path, newline="", encoding="utf-8-sig") as fh:
```

`utf-8-sig` strips a leading byte-order mark and reads a file without one unchanged. T019 is
ticked in the same commit, and the hook runs the whole chain:

```console
$ git commit -m "fix(parse): read statements that start with a UTF-8 byte-order mark" \
             -m "Spec: 001-monthly-spending-report" -m "Task: T019"
gate chain: 10 slots from gates/chain.conf (9 wired, 1 N/A, 0 not wired)
[1/10] format: $ ruff format --check .
15 files already formatted
[1/10] format: ok
[2/10] static: $ ruff check .
All checks passed!
[2/10] static: ok
[3/10] privacy: $ grep -rnE '(^|[^[:alnum:]_])float\(|^[[:space:]]*(import|from)[[:space:]]+(socket|ssl|http|urllib|requests|httpx|ftplib|smtplib)([.[:space:],]|$)' src/budget; [ $? -eq 1 ]
[3/10] privacy: ok
[4/10] test: $ pytest -q tests/unit
.....                                                                    [100%]
5 passed in 0.02s
[4/10] test: ok
[5/10] build: $ uv build
Building source distribution...
Building wheel from source distribution...
Successfully built dist/budget_cli-0.1.0.tar.gz
Successfully built dist/budget_cli-0.1.0-py3-none-any.whl
[5/10] build: ok
[6/10] orphan-endpoints: N/A - no network routes; the product's only entry point is the budget command, and tests/e2e runs every subcommand through it
[7/10] acceptance: $ pytest -q tests/e2e
....                                                                     [100%]
4 passed in 0.32s
[7/10] acceptance: ok
[8/10] doc-sync: $ ./gates/check-plan-sync.sh
✅ Specs in sync - 1 spec (approved 1); 18/20 tasks checked
[8/10] doc-sync: ok
[9/10] spec-approval: $ ./gates/check-spec-approval.sh
✅ Spec approvals recorded - 1 spec: 0 draft, 1 approved, 0 accepted/released with acceptance.md, 0 superseded
[9/10] spec-approval: ok
[10/10] spec-numbers: $ ./gates/check-spec-numbers.sh
✅ Spec numbers unique - 1 spec directory (1 sequential, 0 timestamp)
[10/10] spec-numbers: ok
GATE GREEN - 9 ran, 1 N/A
[main 54968ae] fix(parse): read statements that start with a UTF-8 byte-order mark
 4 files changed, 11 insertions(+), 2 deletions(-)
 create mode 100644 tests/fixtures/bom.csv
exit=0
```

## Scene 3 — "accepted" before it is true

Two tasks were still open: T020 (tests for the empty and header-only edge cases) and T018
(the acceptance run). The builder set `status: accepted` anyway. Slots 1–7 were green in
this run and the next; the transcripts below start at slot 8 and are otherwise as printed.

```console
$ git commit -m "docs(spec): 001 accepted" -m "Spec: 001-monthly-spending-report"
[8/10] doc-sync: $ ./gates/check-plan-sync.sh
❌ SPEC DRIFT - the specs disagree with their own tasks and names:
   • 001-monthly-spending-report/tasks.md: status is accepted but 2 tasks are still open (T018, T020) - finish it, mark it '(deferred -> <where>)', or set status back to approved
[8/10] doc-sync: RED - exit 1
      not run: spec-approval spec-numbers
GATE RED at 'doc-sync' - no commit on red. Fix it, or explicitly revert (GATES.md section 1).
pre-commit: commit REFUSED by gates/hooks/pre-commit - gates/run-chain.sh exited 1.
pre-commit: fix the red slot or explicitly revert; do not --no-verify (GATES.md section 1).
exit=1
```

Status went back to `approved`; T020's tests landed (commit `f716104`). Then the builder ticked
T018 itself and set `accepted` again — self-grading, with no one else's run on record:

```console
$ git commit -m "docs(spec): 001 accepted" -m "Spec: 001-monthly-spending-report" -m "Task: T018"
[8/10] doc-sync: $ ./gates/check-plan-sync.sh
✅ Specs in sync - 1 spec (accepted 1); 20/20 tasks checked
[8/10] doc-sync: ok
[9/10] spec-approval: $ ./gates/check-spec-approval.sh
❌ SPEC APPROVAL - work ran ahead of its approval or acceptance record:
   • 001-monthly-spending-report/acceptance.md: missing - status accepted needs the record of an acceptance run by someone other than the builder (GATES.md section 3)
[9/10] spec-approval: RED - exit 1
      not run: spec-numbers
GATE RED at 'spec-approval' - no commit on red. Fix it, or explicitly revert (GATES.md section 1).
pre-commit: commit REFUSED by gates/hooks/pre-commit - gates/run-chain.sh exited 1.
pre-commit: fix the red slot or explicitly revert; do not --no-verify (GATES.md section 1).
exit=1
```

Minh, who had not built it, then ran
[quickstart.md](specs/001-monthly-spending-report/quickstart.md) from a fresh clone of
`f716104` in a new virtual environment and wrote
[acceptance.md](specs/001-monthly-spending-report/acceptance.md):

```console
$ git commit -m "docs(spec): 001 accepted - acceptance run by Minh" -m "Spec: 001-monthly-spending-report" -m "Task: T018"
[8/10] doc-sync: $ ./gates/check-plan-sync.sh
✅ Specs in sync - 1 spec (accepted 1); 20/20 tasks checked
[8/10] doc-sync: ok
[9/10] spec-approval: $ ./gates/check-spec-approval.sh
✅ Spec approvals recorded - 1 spec: 0 draft, 0 approved, 1 accepted/released with acceptance.md, 0 superseded
[9/10] spec-approval: ok
[10/10] spec-numbers: $ ./gates/check-spec-numbers.sh
✅ Spec numbers unique - 1 spec directory (1 sequential, 0 timestamp)
[10/10] spec-numbers: ok
GATE GREEN - 9 ran, 1 N/A
[main 986c2bb] docs(spec): 001 accepted - acceptance run by Minh
 3 files changed, 67 insertions(+), 2 deletions(-)
 create mode 100644 specs/001-monthly-spending-report/acceptance.md
exit=0
```

## What to notice

1. **Every red names its slot, and nothing after it runs.** The output lists what was
   skipped, so a red at `format` is never mistaken for a pass on the rest.
2. **The spec gates close the gap the audit found — and only that gap.** In the 2026-09 audit's
   simulation of this project, every task was ticked (T013 of that run, whose tests were never
   written) and the spec set to `shipped`, and the chain printed GATE GREEN. With 1.4.0 an
   open task under `accepted` is red (scene 3a), and so is `accepted` with no acceptance
   record (scene 3b). A box ticked over work nobody did still passes: the gates read
   checkboxes, not code (the BLIND TO block of
   [`check-plan-sync.sh`](../../gates/check-plan-sync.sh)). Converge and review catch that.
3. **The gate cannot tell who ran the acceptance.** Scene 3b was refused because no record
   existed, not because the builder ticked T018. A builder who writes `acceptance.md` itself
   passes the gate; `accepted_by` is a name someone typed. That is a rule for people, and
   review reads the record.
4. **T020's tests passed on their first run.** The behaviour existed; the tests did not —
   converge flagged the gap as `(missing)`. A test never seen failing proves less than one
   that has, so it was made to fail once on purpose: with `render` changed to omit the
   `TOTAL` line when there are no months, `pytest -q tests/e2e` printed
   `1 failed, 4 passed`; with the change undone, `5 passed`.
5. **ruff 0.16.9's formatter also checks Python code blocks in Markdown.** The file count
   above includes the spec's `.md` files. A ```` ```python ```` block in a spec or
   quickstart that is not formatted turns the `format` slot red (measured: `x=[1,2]` in a
   Markdown code block, exit 1). Keep code blocks formatted, or give them another language
   tag.

## Reproduce

The three spec slots read only `specs/`, so they run on this directory from the kit root:

```console
$ ./gates/check-plan-sync.sh --specs examples/budget-cli/specs
✅ Specs in sync - 1 spec (accepted 1); 20/20 tasks checked
$ ./gates/check-spec-approval.sh examples/budget-cli/specs
✅ Spec approvals recorded - 1 spec: 0 draft, 0 approved, 1 accepted/released with acceptance.md, 0 superseded
$ ./gates/check-spec-numbers.sh examples/budget-cli/specs
✅ Spec numbers unique - 1 spec directory (1 sequential, 0 timestamp)
```

The other slots need the source, which the kit does not ship.
