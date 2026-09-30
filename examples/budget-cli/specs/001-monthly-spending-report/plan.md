<!-- WHO READS ME: the implementer of budget-cli feature 001 — the HOW. Filled from Spec Kit's
     plan template (no kit override: its Constitution Check is derived from the constitution).
     I POINT TO: spec.md (WHAT) · research.md · data-model.md · contracts/cli.md ·
     quickstart.md · tasks.md · ../../constitution.md (Platform Constraints hold the stack). -->

# Implementation Plan: Monthly spending report from one statement CSV

**Branch**: `001-monthly-spending-report` (no git branch; main-only) | **Date**: 2026-09-28 |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-monthly-spending-report/spec.md`

## Summary

A standard-library Python command, `budget report FILE`, parses a three-column statement CSV
into exact `Decimal` transactions, sums the negative amounts per calendar month, and prints a
text table with the row counts. As feature 001 it also wires the gate chain, the pre-commit
hook and CI (the walking skeleton).

## Technical Context

The stack is the constitution's [Platform Constraints](../../constitution.md#platform-constraints)
— Python ≥ 3.11, standard library only at runtime, src layout, hatchling, console script
`budget`, pytest and ruff for development. This feature adds:

**Language/Version**: Python 3.11 (the lowest version Platform Constraints allows)

**Primary Dependencies**: none at runtime (`csv`, `decimal`, `argparse`, `datetime`)

**Storage**: N/A — reads one file, writes nothing

**Testing**: pytest — `tests/unit` (parse, report) and `tests/e2e` (the installed command as a
subprocess)

**Target Platform**: any OS with Python 3.11 or later

**Project Type**: single CLI

**Performance Goals**: a 100,000-row statement in under 2 seconds on a laptop

**Constraints**: offline; exact decimals; one file per run

**Scale/Scope**: one user; statements up to about 10 MB

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Re-checked after
Phase 1: unchanged.

| Article | What this plan does | Status |
|---|---|---|
| I Every row counted exactly once | `ParseResult` keeps `read`, `accepted`, `rejected`; `cli` asserts accepted + rejected = read before printing; the counts line is always printed | PASS |
| II Money exact, statement local | `Decimal` from the amount string; no network module, no file writes, no row logged; the `privacy` chain slot greps for `float(` and network imports | PASS |
| III cli → parse → report → render | four modules, imports one way; `report` is pure; only `cli` prints | PASS |
| IV Spec before code | spec approved 2026-09-28 by Lan, recorded in its frontmatter | PASS |
| V Reachability | the only entry point is the `budget` console script declared in `pyproject.toml`; `tests/e2e` runs it as a subprocess and checks `budget --help` lists `report` | PASS |
| VI Gates and independent acceptance | the chain is wired by this feature (tasks T002–T005, T012–T014); tests first in every story; acceptance from a fresh clone and virtual environment by someone other than the builder (T018); least-privilege clause N/A per the constitution | PASS |
| VII Deliberate simplicity | standard library only; one subcommand | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/001-monthly-spending-report/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/cli.md     # Phase 1 output (/speckit-plan command)
├── tasks.md             # Phase 2 output (/speckit-tasks command)
└── acceptance.md        # the acceptance record (kit convention, GATES §3)
```

### Source Code (repository root)

```text
pyproject.toml
src/budget/
├── __init__.py
├── cli.py          # argparse, exit codes, stdout/stderr — the only module that prints
├── parse.py        # CSV → Transaction / Rejected
├── report.py       # pure aggregation
└── render.py       # Report → text
tests/
├── unit/           # test_parse.py, test_report.py
├── e2e/            # test_cli.py — runs the installed `budget` command
└── fixtures/       # jan_feb.csv, bad_rows.csv, bom.csv, empty.csv, header_only.csv
gates/chain.conf    # wired by this feature
```

**Structure Decision**: one package in a src layout. The src layout keeps tests from importing
the package from the working tree by accident, so `tests/e2e` exercises what `pip install`
put on PATH.

## Complexity Tracking

None — no Constitution Check violation.

## Release

Not part of this feature: `accepted` is where it stops. When the owner decides to publish
0.1.0, the [release lane](../../../../model/NON-FEATURE-WORK.md) applies with the CLI release
gate ([GATES §9](../../../../gates/GATES.md)): build the wheel, install it from the artifact
into a clean environment, run `quickstart.md` there, then tag `v0.1.0`. Rollback for a
command-line tool that nobody installs from an index yet: delete the tag and the wheel.
