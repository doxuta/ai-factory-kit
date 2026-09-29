<!-- WHO READS ME: anyone studying how the kit's constitution is filled for a product that is not
     a web app — every agent of the fictional budget-cli project would read it first. This is
     ../../constitution/constitution-template.md filled for the CLI archetype; in the project it
     lives at .specify/memory/constitution.md. I POINT TO: ../../model/ARCHETYPES.md (the CLI
     slot choices) · ../../gates/GATES.md (Article VI) · ../../model/SPEC-FLOW.md (Article IV) ·
     ../../harness/HARNESS.md §3 (the mirror rule) · CLAUDE.example.md (the mirror) · specs/. -->

# budget-cli Constitution

> Invariants for a single-user command-line tool that turns a bank-statement export into a
> monthly spending report. Violating one is a defect to fix, not a style choice. Seven
> articles, numbered I–VII; the clause marked N/A keeps its place.

**Vision**: for one person who exports their bank statement as CSV · the problem: knowing what
they spent each month takes a spreadsheet session every month · success: one command gives
exact monthly totals, and no row is ever silently lost.
**Archetype**: CLI — the slot choices below follow [ARCHETYPES](../../model/ARCHETYPES.md#cli).

## Core Principles

### I. Every row is counted exactly once (NON-NEGOTIABLE)
Every data row of the input lands in exactly one month or is reported as rejected with its
line number and reason. Accepted + rejected = rows read, and the report prints all three
counts. A report that silently drops or double-counts a row is a different, wrong product —
worse than no report, because the user trusts it.

### II. Money stays exact and the statement stays on the machine
Amounts are exact decimals (`decimal.Decimal`), never binary floats; an amount that does not
parse is a rejection, never a guess. The tool reads only the files it is given, writes
nothing, makes no network connection, and never logs a raw row. Stated so a reviewer can grep:
`float(` or a network module imported under `src/` is a breach, not a bug.

### III. cli → parse → report → render
`cli` handles arguments, exit codes and the terminal; `parse` turns a CSV file into
`Transaction` records (one adapter per bank format); `report` aggregates records with pure
functions and no I/O; `render` formats a report as text. Imports point one way. No file access
in `report`, no `print` outside `cli`.

### IV. Spec before code
Every feature flows through `specs/<id>/`: spec → plan → tasks → implement
([SPEC-FLOW](../../model/SPEC-FLOW.md)). No implementation before the spec is approved
(**HARD-GATE**): the spec's frontmatter says `status: approved` with `approved_by` and
`approved_on`, and the `spec-approval` gate is red for a ticked task on a draft spec.
`specs/<id>` is the single unit of work; roadmaps are views that point into specs. Work that
is not a feature follows its lane in [NON-FEATURE-WORK](../../model/NON-FEATURE-WORK.md).

### V. Reachability — the installed command is the only way in
A capability is unfinished until its user can reach it through the installed `budget` command
and `budget --help` lists it, or the gap is a named task in the feature's `tasks.md`. A
function no subcommand calls ≠ done. Before believing a slice is finished, answer: **"who will
CALL this?"** ([GATES §4](../../gates/GATES.md)).

### VI. Executable gates and independent acceptance
Always:
- **Gates decide done.** "Done" = the [gate chain](../../gates/GATES.md)
  (`./gates/run-chain.sh`) is green — never a claim, yours included. A subagent's numbers are
  testimony; the orchestrator re-runs the gates itself.
- **Tests first.** Behaviour changes start with a failing test (red → green → refactor), and
  every `tasks.md` carries test tasks ahead of the code they prove.
- **Acceptance by someone other than the builder.** Per feature, a person who did not build it
  — or `tester-e2e` in a fresh context — clones the repository afresh, builds the wheel,
  installs it into a new virtual environment, runs `quickstart.md` through the installed
  `budget` command, and records `specs/<id>/acceptance.md` before the spec becomes `accepted`
  ([GATES §3](../../gates/GATES.md)). A fresh clone and a fresh environment are this product's
  "third person": they catch what the builder's editable install hides.

Where the product has an authorization boundary:
- **Least-privilege acceptance.** N/A — a single-user tool with no accounts, roles or tenants;
  it runs as the user who starts it and needs no privilege beyond reading the file it is
  given (decided 2026-09-28 by Lan). If a later feature writes outside the working directory
  or needs elevated rights, this clause returns as an amendment.

### VII. Deliberate simplicity
Within a layer: reuse before stdlib, stdlib before dependency, dependency before new code;
mark intentional shortcuts with a `shortcut:` comment carrying the ceiling and upgrade path.
The layering of Article III and the exactness of Articles I–II are **not** over-engineering —
never collapse them for brevity. When simplicity and the constitution conflict, the
constitution wins.

## Platform Constraints
- **Stack**: Python ≥ 3.11 · standard library only at runtime (`csv`, `decimal`, `argparse`,
  `datetime`) · no storage · src layout, hatchling build backend, console script `budget`.
  Decided 2026-09-28 by Lan; rationale: exact decimals and CSV parsing are in the standard
  library, so nothing needs installing beyond the tool; alternatives considered: a Go single
  binary (rejected: no one on the project reads Go), Python with pandas (rejected: a large
  runtime dependency for work the standard library does exactly).
- **Dev tools**: pytest and ruff in the development virtual environment, uv for `uv build`;
  ruff excludes `factory`, `gates`, `.claude` and `.specify` (`extend-exclude` in
  `pyproject.toml`), so the kit's files never turn the chain red.
- **Spec Kit**: specify-cli 1.0.12, integration claude; spec numbering sequential `NNN` (one
  person creates specs); extensions adopted: none.
- **Models**: N/A — no LLM or ML component.
- **Conventions**: data on stdout, diagnostics on stderr; exit 0 when a report is printed
  (rejected rows included), 2 for a usage error or an unreadable input file; amounts printed
  exactly as summed, never rounded.
- **Data changes**: N/A — the tool stores nothing.
- **Environments and release**: one environment, the user's machine, installed from the built
  wheel; secrets N/A — the tool reads local files and holds no credentials (decided 2026-09-28
  by Lan); a broken release shows as `quickstart.md` failing against the wheel installed from
  the release artefact.
- **Branch model and commits**: main only; Conventional Commits with a `Spec: <id>` trailer
  ([GATES §10](../../gates/GATES.md)).

## Non-goals (doctrine)
- No network access, no cloud sync, no accounts, no database.
- No GUI or web UI.
- No budgeting advice or prediction — the tool reports what happened.
- No bank-specific layouts in the first slice; each one is a later spec with its own `parse`
  adapter.

## Development Workflow
1. New feature: the [Level-1 flow](../../model/SPEC-FLOW.md), HARD-GATE at spec approval.
2. Every commit: the [gate chain](../../gates/GATES.md) green; the pre-commit hook and CI run
   the same chain (wired by spec 001).
3. Risky surfaces (money arithmetic, parsing untrusted CSV, anything that could send or log
   statement data): adversarial review
   ([tech-lead-review](../../harness/agents/tech-lead-review.md)) before commit — findings are
   fixed or explicitly refuted, never shelved.
4. Acceptance: as Article VI says — fresh clone, fresh environment, the installed command,
   recorded in `acceptance.md`.
5. Work that is not a feature: its lane in [NON-FEATURE-WORK](../../model/NON-FEATURE-WORK.md).
6. Docs: the spec IS the feature's technical document. When code and spec disagree, find out
   which one moved. If the spec states intended behaviour the code does not deliver, the code
   is wrong: record a new task (converge). If the code reflects a deliberate, owner-approved
   change the spec never recorded, fix the spec with the correction marked (≠old) and a dated
   Clarifications entry. If you cannot tell, ask the owner.

## Governance
- This constitution outranks every other process document; conflicts resolve in its favor.
- **Amendments**: only Lan (the owner) approves. Each bump follows semver (MAJOR remove or
  redefine a principle · MINOR add/expand · PATCH clarify), updates the dates, and says what
  changed and why in the commit that makes it.
- ⚠️ **The mirror rule** ([HARNESS §3](../../harness/HARNESS.md)): Articles I, II, III and VI
  are mirrored into the always-loaded `.claude/CLAUDE.md` (in this example
  [`CLAUDE.example.md`](CLAUDE.example.md)) and into the INVARIANTS block of each agent
  definition. This file is the authoritative copy, not the only copy — amending it means
  syncing the mirrors in the same commit.
- Compliance is checked by runnable gates and review checklists, not by memory.

**Version**: 1.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-09-28
