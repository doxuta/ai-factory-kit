<!-- WHO READS ME: the implementing agent (top to bottom) and whoever checks progress — the
     gates read the checkboxes (check-plan-sync.sh: no open task once the spec is accepted;
     check-spec-approval.sh: no ticked task while it is draft). Shaped by the kit's
     tasks-template override (../../../../speckit/overrides/tasks-template.md): test tasks
     first in every story. I POINT TO: plan.md · spec.md · quickstart.md · acceptance.md ·
     ../../gates/chain.conf (what Phases 1–2 wired). -->

# Tasks: Monthly spending report from one statement CSV

**Input**: Design documents from `/specs/001-monthly-spending-report/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md

**Tests**: REQUIRED - the project works test-first (constitution Article VI). Each user story
phase lists its test tasks first; each test is written and seen to FAIL before the
implementation task that makes it pass. A task that changes no testable behaviour says so on
its own line: `(test-exempt: <reason>)`.

**Organization**: Tasks are grouped by user story. Feature 001 is the walking skeleton, so
Phases 1–2 wire the gate chain ([PHASE-0 §7](../../../../model/PHASE-0.md)).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Create pyproject.toml (hatchling build backend, src layout, console script `budget = "budget.cli:main"`, ruff `extend-exclude = ["factory", "gates", ".claude", ".specify"]`, pytest `testpaths = ["tests"]`) and src/budget/__init__.py (test-exempt: packaging only; T008 runs the installed command)
- [x] T002 [P] Wire `format: ruff format --check .` and `static: ruff check .` in gates/chain.conf and the same commands in .claude/CLAUDE.md (test-exempt: gate wiring; T014 proves the chain bites)
- [x] T003 Wire `test: pytest -q tests/unit` in gates/chain.conf after T006's first test was seen red, then green (test-exempt: gate wiring; pytest exits 5 when it collects no test, so no zero-test guard is needed)
- [x] T004 [P] Wire `build: uv build` in gates/chain.conf (test-exempt: gate wiring)

---

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T005 In gates/chain.conf declare `orphan-endpoints: NA: <reason>`, wire `acceptance: pytest -q tests/e2e` and the extra `privacy` slot (Article II); replace the TBD lines in Platform Constraints and .claude/CLAUDE.md (test-exempt: gate wiring; T014 proves the chain bites)

**Checkpoint**: every slot is a command or N/A; stories can start.

---

## Phase 3: User Story 1 - See how much I spent each month (Priority: P1) 🎯 MVP

**Goal**: `budget report FILE` prints monthly spending, a total and the row counts.

**Independent Test**: the installed command on tests/fixtures/jan_feb.csv prints the
hand-computed totals.

### Tests for User Story 1 (REQUIRED - write them first, watch them fail) ⚠️

- [x] T006 [P] [US1] Failing tests: valid rows parse to exact `Decimal` amounts, thousands separators included, in tests/unit/test_parse.py
- [x] T007 [P] [US1] Failing tests: only negative amounts count, one total per month, oldest first; no transactions gives no months and a total of 0, in tests/unit/test_report.py
- [x] T008 [P] [US1] Failing end-to-end tests: the installed `budget report tests/fixtures/jan_feb.csv` prints the four contract lines and exits 0, and `budget --help` lists `report`, in tests/e2e/test_cli.py

### Implementation for User Story 1

- [x] T009 [US1] `Transaction` and `parse_file` in src/budget/parse.py (makes T006 pass)
- [x] T010 [US1] `monthly_spending` in src/budget/report.py (makes T007 pass)
- [x] T011 [US1] `render` in src/budget/render.py and the `report` subcommand in src/budget/cli.py (makes T008 pass)

**Checkpoint**: User Story 1 works on its own through the installed command.

---

## Phase 4: User Story 2 - The gate chain guards every commit (Priority: P1)

**Goal**: one command decides "done", and a red commit is refused locally and in CI.

**Independent Test**: `./gates/run-chain.sh` is green; a deliberately unformatted file is
refused at commit.

- [x] T012 [US2] `python3 factory/bin/adopt.py --install-git-hook --ci github`, then add the job's toolchain steps (set up Python 3.11, install uv, `pip install -e . pytest ruff`) before "Gate chain" in .github/workflows/factory-gates.yml (test-exempt: its test is T014)
- [x] T013 [US2] `./gates/run-chain.sh --list` shows every slot as run or N/A and none as TODO, and `./gates/run-chain.sh` exits 0 (test-exempt: the check is the chain itself)
- [x] T014 [US2] Prove the chain bites: commit a deliberately unformatted file, see the pre-commit hook refuse it with `format` named, then revert the file (GATE-RUN.md, scene 1)

---

## Phase 5: User Story 3 - Trust the numbers (Priority: P2)

**Goal**: unreadable rows are reported by line number, and the counts reconcile.

**Independent Test**: tests/fixtures/bad_rows.csv reports lines 3 and 4 as rejected and
`read=3 accepted=1 rejected=2`.

### Tests for User Story 3 (REQUIRED - write them first, watch them fail) ⚠️

- [x] T015 [P] [US3] Failing tests: a malformed date and a malformed amount are rejected with their line numbers (3 and 4 in tests/fixtures/bad_rows.csv), and accepted + rejected = read, in tests/unit/test_parse.py
- [x] T016 [P] [US3] Failing end-to-end tests: bad_rows.csv prints `rows: read=3 accepted=1 rejected=2`, one `line N: reason` per rejected row on stderr, exit 0; a missing file exits 2 with nothing on stdout, in tests/e2e/test_cli.py

### Implementation for User Story 3

- [x] T017 [US3] Rejection path in src/budget/parse.py; stderr lines, the missing-file exit 2 and the Article I assertion (accepted + rejected = read) in src/budget/cli.py (makes T015 and T016 pass)

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T018 Acceptance: someone other than the builder runs quickstart.md through the installed command, from a fresh clone and a fresh virtual environment, and records specs/001-monthly-spending-report/acceptance.md

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → stories. US1 before US2 (the chain needs code to check) and before US3
  (US3 extends US1's parser and command).
- Within each story, tests before implementation; every test seen red first.
- Parallel: the [P] test tasks of a story touch different files. The project was built by one
  agent session at a time, so nothing was dispatched in parallel
  ([PHASE-0 §10](../../../../model/PHASE-0.md): sequential is simpler for a solo project).

## Notes

- A task is ticked in the commit that lands it, with the gate chain green. T001–T005 landed
  while the chain was being wired, so their commits were red at the `TODO` slots still ahead
  and at no wired one, with the spec gates run directly: the bootstrap exception
  ([GATES §1](../../../../gates/GATES.md)).
- A task moved out of this feature stays listed, unticked, marked `(deferred → <spec id>)`.

## Phase 7: Convergence

- [x] T019 Read statement files that start with a UTF-8 byte-order mark, as spreadsheet exports often do — every row of such a file was rejected as `unreadable date`; test first in tests/unit/test_parse.py with tests/fixtures/bom.csv, fix in src/budget/parse.py, per SC-003 (partial)
- [x] T020 Test the edge cases the spec lists: an empty file and a header-only file report `rows: read=0 accepted=0 rejected=0`, no months, `TOTAL  0`, exit 0 — tests/e2e/test_cli.py with tests/fixtures/empty.csv and tests/fixtures/header_only.csv, per spec Edge Cases (missing)
