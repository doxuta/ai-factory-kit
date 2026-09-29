---
name: plan-and-tdd
description: >-
  The per-task discipline to apply INSIDE /speckit-implement (Spec Kit), once the spec is
  approved and /speckit-plan, /speckit-tasks and /speckit-analyze have run: check that tasks.md
  carries test tasks, then for each task write the failing test first, the minimum code to
  green, refactor, run ./gates/run-chain.sh, get review, and commit one concern with its
  Spec: trailer and the task ticked. Not an entry point and never before approval. Adapted
  from obra/superpowers writing-plans + test-driven-development (MIT).
---
<!-- WHO READS ME: an agent implementing a feature whose spec is approved.
     I POINT TO (kit paths; factory/... once adopted): harness/skills/spec-first/SKILL.md (the
     discipline before approval) · gates/GATES.md (the chain every commit runs; §10 commit
     trailers) · model/SPEC-FLOW.md (the implement step, which I conduct) ·
     harness/agents/task-orchestra.md (when the tasks split into parallel parcels). -->

# Plan → TDD — from approved tasks to landed commits

Entry condition: `specs/<id>/spec.md` says `status: approved` with `approved_by` and
`approved_on`, and `plan.md`, `quickstart.md` and `tasks.md` exist
([`spec-first`](../spec-first/SKILL.md) gets you there). Anything missing → stop and run the
Spec Kit command that makes it (`/speckit-specify`, `/speckit-plan`, `/speckit-tasks`). This
is the constitution's HARD-GATE, not a preference. This skill writes no plan and no tasks of
its own — one plan, one task list, both Spec Kit's — and when the tasks split into
file-disjoint parcels, [`task-orchestra`](../../agents/task-orchestra.md) runs them in parallel,
each worker following this loop. Work that is not a feature — a bug in accepted behaviour, a
hotfix, a refactor, a chore — runs the same per-task loop under its own lane's entry condition
instead (an accepted spec for a bug, no spec for a refactor):
[NON-FEATURE-WORK](../../../model/NON-FEATURE-WORK.md).

## Check tasks.md before the first line of code

`/speckit-tasks` wrote it; you check it (the step of [SPEC-FLOW](../../../model/SPEC-FLOW.md)
that `/speckit-analyze` also reads):

- **Test tasks are there**, each ahead of the code it proves. Spec Kit's `/speckit-tasks`
  generates tests only when asked; constitution Article VI asks. Missing? Re-run
  `/speckit-tasks` with "tests first for every behaviour change" as its argument.
- **Every task is independently verifiable** and carries a measurable "done = …". One task ≈
  one commit ≈ one concern; a task you cannot name in one clause is two tasks.
- **Risky tasks are flagged** — anything on the surfaces the constitution's Development
  Workflow names (for a web product: data isolation, schema, authorization, money). Those get
  adversarial review before commit, not just the normal pass.
- Tasks use Spec Kit's checklist format, `- [ ] T001 …`; a task deliberately moved out of this
  feature reads `(deferred → <where>)`, so it does not hold the spec back.

## The loop, per task

1. **Red** — write the failing test first, and *watch it fail*. A test that passes before the
   code exists proves nothing. **Vacuous-green check**: confirm the test filter matches ≥1
   real test name — a filter matching zero tests exits green
   ([GATES §1](../../../gates/GATES.md)).
2. **Green** — the minimum code that passes. No gold-plating; the
   [`ponytail`](../ponytail/SKILL.md) ladder applies inside the layer.
3. **Refactor** — clean up with the tests staying green.
4. **Gates** — `./gates/run-chain.sh`. Red = fix, never proceed; a `TODO` slot is red too. A
   new route, command or exported surface needs its caller in the same task or a named task —
   the `orphan-endpoints` slot (`gates/check-orphan-endpoints.sh`, configured by
   `gates/orphan-endpoints.conf`; unconfigured it is red, "not wired") checks routes.
5. **Review** — an independent reviewer; adversarial lenses
   ([tech-lead-review](../../agents/tech-lead-review.md)) for the flagged tasks. Findings are
   fixed or refuted with evidence, never shelved (GATES §2).
6. **Commit** — `type(scope): description`, one concern, with a `Spec: <id>` trailer
   ([GATES §10](../../../gates/GATES.md)). The task's checkbox (`- [x] T00n`) and any spec or
   plan correction land **in the same commit** — deferred sync is how maps start lying.

When every task is ticked, the chain is green and review has passed, the feature is built, not
accepted: someone other than the builder runs `quickstart.md` and records
`specs/<id>/acceptance.md` before the status moves to `accepted` (GATES §3).

## Stop rules

- The design turns out wrong mid-task → stop, return to the spec
  ([`spec-first`](../spec-first/SKILL.md)); a changed requirement goes back to the owner for
  approval. Pushing through a broken design is how one correction commit becomes five.
- A task still resists after two honest attempts → the task is mis-cut; re-plan it.
- Never race a milestone by dropping tests or review — a green lie costs more than a red
  truth, because the lie compounds.
