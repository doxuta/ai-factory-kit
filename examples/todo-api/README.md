<!-- WHO READS ME: an adopter (AI or human) who wants to see the kit applied end-to-end — 9th
     in the kit's reading order. I POINT TO: constitution.md · specs/001-task-crud/{spec,plan,
     tasks,quickstart}.md · GATE-RUN.md · ../../model/SPEC-FLOW.md · ../../gates/GATES.md
     · ../../gates/check-plan-sync.sh -->

# Worked example — Team Todo API

A tiny fictional project that adopted the kit: a multi-workspace todo service for small teams.
It exists to show **one full Level-1 cycle** with every artifact in its final shape — filled
constitution, spec with clarifications written back in, plan with contracts, dependency-ordered
tasks mid-progress, a runnable acceptance script, and a gate-chain transcript that goes red
before it goes green. Imitate these shapes; don't copy the content.

## Read order

| # | File | Shows |
|---|---|---|
| 1 | [`constitution.md`](constitution.md) | The [template](../../constitution/constitution-template.md) filled: 7 concrete principles, generic stack |
| 2 | [`specs/001-task-crud/spec.md`](specs/001-task-crud/spec.md) | WHAT/WHY: 2 prioritized stories, FR-001..005, measurable criteria, one dated clarification |
| 3 | [`specs/001-task-crud/plan.md`](specs/001-task-crud/plan.md) | HOW: data model + API contracts, stack-neutral |
| 4 | [`specs/001-task-crud/tasks.md`](specs/001-task-crud/tasks.md) | 8 ordered tasks, 2 done — the progress format [`check-plan-sync.sh`](../../gates/check-plan-sync.sh) parses |
| 5 | [`specs/001-task-crud/quickstart.md`](specs/001-task-crud/quickstart.md) | Acceptance as a runnable script, third-person account |
| 6 | [`GATE-RUN.md`](GATE-RUN.md) | The gate chain catching a real bug class, the fix, the green — *no commit on red* |

## Three deliberate choices worth noticing

1. **`tasks.md` is named so the plan-sync glob does NOT match it.**
   [`check-plan-sync.sh`](../../gates/check-plan-sync.sh) self-globs `*-plan.md` in your docs
   dir ([GATES §6](../../gates/GATES.md) — gates must never hard-point at a deletable file).
   The tasks file *demonstrates* the header↔table format; a roadmap **view** (e.g.
   `docs/core-plan.md`) opts into gate coverage by carrying that format under a matching name.
   The atom of work stays `specs/001-task-crud/` either way
   ([LEVELS](../../model/LEVELS.md)).
2. **`data-model.md` and `contracts/` are folded into `plan.md`.** The feature is small; the
   [spec flow](../../model/SPEC-FLOW.md) splits them out when they stop fitting on one screen.
   `quickstart.md` is never folded in — it is what
   [`tester-e2e`](../../harness/agents/tester-e2e.md) executes.
3. **The failure shown in `GATE-RUN.md` is not decorative.** A list query missing its
   workspace filter is the exact bug class Principle II exists for — the same class was
   measured (and paid for) on the production repo this kit is distilled from. The transcript
   shows the discipline: gate red → fix at the store layer → gate green → *then* commit.

## What "done" means here

All of: gate chain green ([GATE-RUN.md](GATE-RUN.md)) · `quickstart.md` executed by a
**non-privileged** member account ([GATES §3](../../gates/GATES.md)) · every task in
`tasks.md` ✅ or explicitly moved · a `converge` pass confirming code ↔ spec agree
([SPEC-FLOW](../../model/SPEC-FLOW.md) step 7).
