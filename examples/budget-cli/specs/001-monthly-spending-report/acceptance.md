<!-- WHO READS ME: the spec-approval gate (gates/check-spec-approval.sh reads the heading and the
     four key lines below) and anyone asking "who said this feature works, as whom, when?".
     I POINT TO: quickstart.md (the script that was run) · spec.md (status: accepted) ·
     ../../../../gates/GATES.md §3 (the record's format). -->

# Acceptance — 001-monthly-spending-report
accepted_on: 2026-09-29
accepted_by: Minh (Lan's colleague; did not build the feature, which Claude Code sessions built)
run_as: n/a — single-user tool with no authorization boundary (constitution Article VI)
result: pass

Ran [quickstart.md](quickstart.md) steps 1–6 from a fresh clone of commit `f716104` (T020
landed, chain green), in a new virtual environment, with the wheel built from that clone and
installed — not the builder's editable install. Python 3.11.15, pip 24.0. Every `expect`
held. Output as printed; the run used a scratch directory, shown here under the paths the
script names.

```console
$ command -v budget
/tmp/budget-acc-venv/bin/budget

$ budget --help
usage: budget [-h] {report} ...

positional arguments:
  {report}
    report    monthly spending report for one statement CSV

options:
  -h, --help  show this help message and exit

$ budget report tests/fixtures/jan_feb.csv; echo "exit=$?"
2026-01  1350000.50
2026-02  200000
TOTAL  1550000.50
rows: read=4 accepted=4 rejected=0
exit=0

$ budget report tests/fixtures/bad_rows.csv; echo "exit=$?"
line 3: unreadable date
line 4: unreadable amount
2026-01  50000
TOTAL  50000
rows: read=3 accepted=1 rejected=2
exit=0

$ budget report tests/fixtures/bom.csv
2026-01  1
TOTAL  1
rows: read=1 accepted=1 rejected=0

$ budget report tests/fixtures/empty.csv; budget report tests/fixtures/header_only.csv
TOTAL  0
rows: read=0 accepted=0 rejected=0
TOTAL  0
rows: read=0 accepted=0 rejected=0

$ budget report nope.csv; echo "exit=$?"
budget: no such file: nope.csv
exit=2
```

In step 3 the two `line N:` lines are stderr; the terminal shows them first because `cli`
writes the rejections before the report. FR-006 (no network) is outside what one run can
show; the chain's `privacy` slot checks it on every commit.
