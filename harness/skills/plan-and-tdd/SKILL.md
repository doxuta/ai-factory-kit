---
name: plan-and-tdd
description: >
  Turn an approved spec into small verifiable tasks, then implement each by TDD — failing
  test first, minimum code to green, refactor, gates, commit. One concern per commit. Use
  AFTER spec-first approval, never before it. Adapted from obra/superpowers writing-plans +
  test-driven-development (MIT).
---
<!-- WHO READS ME: an agent implementing a feature whose spec is approved.
     I POINT TO: ../spec-first/SKILL.md (the gate before me) · ../../../gates/GATES.md (the
     chain every commit runs) · ../../../model/SPEC-FLOW.md (steps 4-7, which I execute). -->

# Plan → TDD — from approved spec to landed commits

Entry condition: an approved spec ([`spec-first`](../spec-first/SKILL.md)). No spec, or spec
not approved → stop and go get one. This is the constitution's HARD-GATE, not a preference.

## Plan (SPEC-FLOW step 4)

- Break into tasks **small enough that each is independently verifiable** — every task
  carries a measurable "done = …" line.
- Dependency-order them. One task ≈ one commit ≈ one concern. A task you cannot name in one
  clause is two tasks.
- Flag every task touching data isolation, schema, authorization, or money — those get
  adversarial review before commit (constitution workflow rule 3), not just the normal pass.

## The loop, per task

1. **Red** — write the failing test first, and *watch it fail*. A test that passes before the
   code exists proves nothing. **Vacuous-green check**: confirm the test filter matches ≥1
   real test name — a filter matching zero tests exits green
   ([GATES §1](../../../gates/GATES.md)).
2. **Green** — the minimum code that passes. No gold-plating; the
   [`ponytail`](../ponytail/SKILL.md) ladder applies inside the layer.
3. **Refactor** — clean up with the tests staying green.
4. **Gates** — run the full [gate chain](../../../gates/GATES.md). Red = fix, never proceed.
   [EXAMPLE: on a Go stack, `go vet ./... && go test ./... && go build ./...` plus the
   project's orphan-endpoint and doc-sync scripts.]
5. **Review** — an independent reviewer; adversarial lenses for the flagged tasks. Findings
   are fixed or refuted with evidence, never shelved (GATES §2).
6. **Commit** — `type(scope): description`, one concern. Doc-sync (plan checkmarks, blueprint
   status) lands **in the same commit** — deferred sync is how maps start lying.

## Stop rules

- The design turns out wrong mid-task → stop, return to
  [`spec-first`](../spec-first/SKILL.md). Pushing through a broken design is how one
  correction commit becomes five.
- A task still resists after two honest attempts → the task is mis-cut; re-plan it.
- Never race a milestone by dropping tests or review — a green lie costs more than a red
  truth, because the lie compounds.
