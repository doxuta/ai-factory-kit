<!-- WHO READS ME: an adopter (AI or human) whose product is not a web app — a CLI, a library, a
     script — and wants to see the kit applied end to end to one. Read after
     ../todo-api/README.md or instead of it. I POINT TO: constitution.md · CLAUDE.example.md ·
     gates/chain.conf · specs/001-monthly-spending-report/ · GATE-RUN.md ·
     ../../model/ARCHETYPES.md (the CLI entry) · ../../model/PHASE-0.md (feature 001). -->

# Worked example — budget-cli

A fictional single-user command-line tool: it reads a bank-statement CSV and prints how much
was spent in each month. It shows the kit on a product with **no UI, no accounts, no HTTP
API and no database** — one feature, 001, taken from approval to `accepted`, which is also
the walking skeleton that wires the gate chain. Imitate the shapes; don't copy the content.

It is based on the CLI simulation run for the kit's 2026-09 readiness audit, which reached a
green chain only after improvising thirteen times where the kit said nothing. This version
uses the 1.4.0 answers to those gaps. Names are fictional (Lan owns the project, Minh ran the
acceptance, Claude Code sessions built it); every command output shown was printed by a real
run ([GATE-RUN.md](GATE-RUN.md) says how).

## Read order

| # | File | Shows |
|---|---|---|
| 1 | [`constitution.md`](constitution.md) | The [template](../../constitution/constitution-template.md) filled for a CLI: Article V's entry point is the installed command, Article VI's least-privilege clause is N/A with its reason |
| 2 | [`CLAUDE.example.md`](CLAUDE.example.md) | The always-loaded context the project's `.claude/CLAUDE.md` would hold: the mirror of I, II, III, VI and the commands |
| 3 | [`gates/chain.conf`](gates/chain.conf) | Every slot wired or N/A with a reason, plus an extra `privacy` slot |
| 4 | [`specs/001-…/spec.md`](specs/001-monthly-spending-report/spec.md) | Frontmatter at line 1 (the kit's [spec override](../../speckit/overrides/spec-template.md)); three stories, one of them the walking skeleton |
| 5 | [`plan.md`](specs/001-monthly-spending-report/plan.md), [`research.md`](specs/001-monthly-spending-report/research.md), [`data-model.md`](specs/001-monthly-spending-report/data-model.md), [`contracts/cli.md`](specs/001-monthly-spending-report/contracts/cli.md) | Spec Kit's plan artifacts; the contract is the command's output and exit codes |
| 6 | [`tasks.md`](specs/001-monthly-spending-report/tasks.md) | `- [x] T001` tasks, tests first in every story, `test-exempt` reasons, a Convergence phase appended by `/speckit-converge` |
| 7 | [`quickstart.md`](specs/001-monthly-spending-report/quickstart.md) → [`acceptance.md`](specs/001-monthly-spending-report/acceptance.md) | The acceptance script, and the record of someone else running it |
| 8 | [`GATE-RUN.md`](GATE-RUN.md) | Real transcripts: the hook refusing a red commit, a converge finding fixed test-first, `accepted` refused twice before it was true |

## What differs from the web example, and why

| | [todo-api](../todo-api/) (multi-tenant web) | budget-cli (single-user CLI) | Why |
|---|---|---|---|
| `adopt.py --profile` | `full` | `cli` — `rules/api-conventions.md` and `rules/data.md` not installed | no API, nothing stored ([ARCHETYPES](../../model/ARCHETYPES.md#cli)) |
| Article V — the real entry point | the web client, operated by a workspace member | the installed `budget` command, listed in `--help` | "who will CALL this?" has a different answer per product |
| Article VI — least-privilege acceptance | applies: a non-admin member of a second workspace | N/A — no accounts; the reason and the date are in the constitution | the independent acceptor stays; only the account rule has no referent |
| The acceptor's "third person" | another person, signed in as a plain member | another person, from a fresh clone and a fresh virtual environment, installing the built wheel | a fresh environment is what catches a file left out of the package |
| `orphan-endpoints` slot | `./gates/check-orphan-endpoints.sh` with a config | `NA:` with the reason | no routes; the e2e tests run the command itself |
| `acceptance` slot (per commit) | cross-workspace isolation tests | the installed command run as a subprocess on fixture files | the wall worth guarding differs: tenancy there, exact counts here |
| Extra slot | — | `privacy`: no `float(`, no network import (Article II) | an invariant a grep can check belongs in the chain |
| `acceptance.md` `run_as` | the member account used | `n/a — …` with its reason | the gate refuses a bare `n/a` |

What did **not** change: spec before code with the approval in the frontmatter, tests before
code, the gate chain deciding done, acceptance by someone who did not build it, one spec
directory as the unit of work.

**careful.json** for this project would add the CLI release patterns from
[ARCHETYPES](../../model/ARCHETYPES.md#cli) (pushing a version tag, `gh release create`);
the example does not ship a `.claude/` directory, so it is not shown.

## Why the example ships documents only

The transcripts came from a scratch repository holding about 240 lines of Python under
`src/budget/` and `tests/`. They are not in the kit: the kit lives inside every adopter's
repository as `factory/`, and a plain `pytest -q` at an adopter's root collected a `tests/`
directory placed there and stopped with a collection error (checked with pytest 9.1.1). The
three spec gates run on this directory as it is
([GATE-RUN.md — Reproduce](GATE-RUN.md#reproduce)).

## What "done" meant here

All of: `./gates/run-chain.sh` green (GATE-RUN.md, scene 3) · every task in `tasks.md` ticked
· a converge pass whose two findings became tasks T019 and T020 and were done · Minh's run of
`quickstart.md` recorded in `acceptance.md` · `status: accepted`. Releasing 0.1.0 is a
separate lane (the plan's `## Release` section).
