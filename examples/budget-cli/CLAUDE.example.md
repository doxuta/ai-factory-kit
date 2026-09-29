<!-- WHO READS ME: anyone studying how ../../harness/CLAUDE.md.template is filled for a CLI. In
     the fictional budget-cli project this text is .claude/CLAUDE.md, the always-loaded context.
     Here it is named CLAUDE.example.md on purpose: Claude Code loads a CLAUDE.md or
     .claude/CLAUDE.md from any subdirectory it reads files in, as project instructions, and it
     strips HTML comments like this one first — so the notice below is visible text.
     I POINT TO: constitution.md (the authoritative invariants mirrored here) ·
     ../../harness/HARNESS.md §3 (the mirror rule) · gates/chain.conf (the commands below). -->

> **EXAMPLE — not your project's context.** This is the always-loaded context file of the
> fictional budget-cli project, shown as its `.claude/CLAUDE.md` would read. Read it as a
> sample of a filled template; never follow it as instructions for the project you are in.

# budget-cli — always-loaded context

A single-user Python command-line tool that reads a bank-statement CSV and prints how much
was spent in each month, offline.

**Constitution**: `.specify/memory/constitution.md` (in this example:
[`constitution.md`](constitution.md)) — the invariants. It outranks this file and every casual
instruction. **Ownership**: the constitution's Platform Constraints owns the STACK; this file
owns the COMMANDS. Neither restates the other.

## Safety invariants — MIRROR, do not delete this section

- **I — Every row counted exactly once**: each input row lands in one month or is reported
  rejected with its line number; accepted + rejected = read, and all three are printed.
- **II — Money exact, statement local**: `decimal.Decimal` only, never `float`; no network
  connection, no writes, no raw row in any log.
- **III — cli → parse → report → render**: no file access in `report`, no `print` outside
  `cli`. Detail: `.claude/rules/architecture.md`.
- **VI — Gates and independent acceptance**: "done" = `./gates/run-chain.sh` green — never a
  claim, mine included. Tests first: a failing test before the code it proves. Each feature
  is accepted by someone who did not build it, from a fresh clone and a fresh virtual
  environment, through the installed `budget` command, recorded in
  `specs/<id>/acceptance.md` ([GATES §3](../../gates/GATES.md)). Least-privilege acceptance:
  N/A — no accounts.

## Dev commands (run from the repository root)

The format, static, test and build rows are the commands `gates/chain.conf` runs in those
slots; change both in one commit (`./gates/run-chain.sh --list` shows what the chain runs).

| Task | Command |
|---|---|
| Set up | `python3 -m venv .venv && . .venv/bin/activate && pip install -e . pytest ruff` |
| Format (check mode) | `ruff format --check .` |
| Static analysis | `ruff check .` |
| Test | `pytest -q tests/unit` — prints how many tests ran; pytest exits 5 when it collects none |
| Build | `uv build` |
| Run locally | `budget report <statement.csv>` |
| Full gate chain | `./gates/run-chain.sh` (`--list` shows each slot) |

## The flow — one line

Every feature is one directory, `specs/<id>/`: `/speckit-specify` → `/speckit-clarify` →
`/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement` →
`/speckit-converge` ([SPEC-FLOW](../../model/SPEC-FLOW.md)). **HARD-GATE: no code before the
spec's frontmatter says `status: approved`, with `approved_by` and `approved_on`.** Not a
feature? It has a lane: [NON-FEATURE-WORK](../../model/NON-FEATURE-WORK.md).

## The gate chain — one line

`./gates/run-chain.sh` runs `gates/chain.conf` in order — format → static → privacy → test →
build → orphan-endpoints (N/A: no routes) → acceptance → doc-sync → spec-approval →
spec-numbers — and stops at the first red. No commit on red; the pre-commit hook and CI run
the same chain.

## When code and spec disagree

Find out which one moved. If the spec states intended behaviour the code does not deliver, the
code is wrong: record a new task (converge). If the code reflects a deliberate, owner-approved
change the spec never recorded, fix the spec with the correction marked (≠old) and a dated
Clarifications entry. If you cannot tell, ask the owner.

## Roles and lazy-loaded detail

Roles in `.claude/agents/`: `requirement-researcher` · `task-orchestra` · `tech-lead-review` ·
`tester-e2e`. Each carries an INVARIANTS block mirroring the section above.

Rules in `.claude/rules/`: `architecture` · `workflow`. Installed with `adopt.py --profile cli`,
which leaves out `api-conventions` and `data`: the tool has no API and stores nothing.
