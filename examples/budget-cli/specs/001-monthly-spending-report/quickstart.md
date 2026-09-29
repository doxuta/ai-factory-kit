<!-- WHO READS ME: whoever accepts budget-cli feature 001 — someone who did not build it, or
     tester-e2e in a fresh context. This is the runnable acceptance script, not documentation
     garnish. I POINT TO: spec.md (what each step proves) · contracts/cli.md (the exact output
     and exit codes) · acceptance.md (where the result is recorded) ·
     ../../../../gates/GATES.md §3 (why the acceptor is not the builder). -->

# Quickstart 001 — acceptance script

> **Who runs this**: someone other than the builder (constitution Article VI), from a fresh
> clone and a fresh virtual environment — never the builder's checkout or its editable
> install, which can hide a file left out of the package or a console script that was never
> wired. There are no accounts in this product, so there is no least-privilege account to
> choose.

## Setup — fresh clone, fresh environment, the built wheel

```sh
git clone <repository> /tmp/budget-acc && cd /tmp/budget-acc
python3 -m venv /tmp/budget-acc-venv && . /tmp/budget-acc-venv/bin/activate
python -m pip wheel -q --no-deps -w /tmp/budget-acc-dist .
python -m pip install -q /tmp/budget-acc-dist/budget_cli-0.1.0-py3-none-any.whl
command -v budget
# expect: /tmp/budget-acc-venv/bin/budget — the installed command, not the source tree
```

## Steps — the expected result is on every line

**1. The command lists the subcommand** (Article V, SC-003)

```sh
budget --help
# expect: usage: budget [-h] {report} ...   and "report" listed with its one-line help
```

**2. Monthly totals** (FR-001, FR-002, FR-003, FR-005, SC-001)

```sh
budget report tests/fixtures/jan_feb.csv; echo "exit=$?"
# expect exactly:
# 2026-01  1350000.50
# 2026-02  200000
# TOTAL  1550000.50
# rows: read=4 accepted=4 rejected=0
# exit=0
```

The fixture has three debits and one salary credit; January's two debits are 50,000.50 and
1,300,000, February's is 200,000. The credit counts toward nothing.

**3. Unreadable rows are reported, not dropped** (FR-004, SC-002)

```sh
budget report tests/fixtures/bad_rows.csv; echo "exit=$?"
# expect stdout:  2026-01  50000 / TOTAL  50000 / rows: read=3 accepted=1 rejected=2
# expect stderr:  line 3: unreadable date / line 4: unreadable amount
# expect: exit=0 — a report was printed
```

**4. A spreadsheet export with a byte-order mark** (SC-003, task T019)

```sh
budget report tests/fixtures/bom.csv
# expect: 2026-01  1 / TOTAL  1 / rows: read=1 accepted=1 rejected=0
```

**5. Empty and header-only files** (spec Edge Cases, task T020)

```sh
budget report tests/fixtures/empty.csv; budget report tests/fixtures/header_only.csv
# expect, twice: TOTAL  0 / rows: read=0 accepted=0 rejected=0
```

**6. A file that does not exist** (spec Edge Cases)

```sh
budget report nope.csv; echo "exit=$?"
# expect: stderr "budget: no such file: nope.csv", nothing on stdout, exit=2
```

FR-006 (no network connection) is not provable by running the command once; the `privacy`
slot of the gate chain checks it on every commit.

## Pass condition

Every `expect` held, run from the fresh clone and the fresh environment. Record the run in
[`acceptance.md`](acceptance.md) — who ran it, when, as whom, `result: pass`, and the output —
then set the spec's `status: accepted` in the same commit. A claim without the output is
testimony, not evidence ([GATES §2](../../../../gates/GATES.md)).
