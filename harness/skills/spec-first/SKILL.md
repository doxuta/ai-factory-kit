---
name: spec-first
description: >
  HARD-GATE discipline for any new feature or behavior change: clarify the request, present
  2-3 design options, get explicit approval — only then write code. Use BEFORE creating any
  feature/endpoint/schema change, and especially when a task "looks too simple to need it".
  Adapted from obra/superpowers brainstorming (MIT).
---
<!-- WHO READS ME: an agent about to build something new — before any code exists.
     I POINT TO: ../../../model/SPEC-FLOW.md (the full Level-1 loop) ·
     ../../../constitution/constitution-template.md (Article IV mandates this gate) ·
     ../plan-and-tdd/SKILL.md (the step after approval). -->

# Spec-first — no code before an approved design

The [constitution](../../../constitution/constitution-template.md) Article IV makes this a
HARD-GATE: implementation waits for spec approval. This skill is the procedure that carries a
raw request to that approval. Artifact shapes: [SPEC-FLOW](../../../model/SPEC-FLOW.md).

## The procedure

1. **Read before asking.** The code the request touches, prior specs, recent history. Half of
   all clarifying questions are already answered by the repo.
2. **Challenge the premise before solving it.** Is this the right problem? What happens if
   nothing is built — real pain or assumption? What existing capability already covers part of
   it? Put the premises to the human as agree/disagree statements.
3. **Clarify one question at a time**, multiple-choice where possible. Answers are written
   back into `spec.md` (SPEC-FLOW step 2) — never into a side file.
4. **Present 2–3 options — mandatory, even when one clearly wins**: minimum-viable (smallest
   diff) · architectural-ideal · one lateral. Each with effort, risk, and what it reuses.
   **Take a stance** and name what evidence would change it. "Either works, up to you" is
   banned — that is sycophancy wearing a neutrality costume.
5. **Get explicit approval** on the chosen option. Silence is not approval.
6. **Hand off** to [`plan-and-tdd`](../plan-and-tdd/SKILL.md).

## The "too simple to need approval" anti-pattern

The gate exists MOST for the tasks that look exempt from it. Three recurring shapes, each
measured on a production repo:

| The claim | What it actually was | Where the spec catches it |
|---|---|---|
| "Just rename this field" | The name lived in four places — schema, API contract, UI label, validation rule; renaming one silently broke two | Option step: listing everything the change touches |
| "One-line bug fix" | A symptom patch on one caller; the root cause sat in a shared function with sibling callers still broken | Premise step: "is this the right problem?" |
| "Just add an endpoint" | Backend landed, no caller ever written — every gate green, feature unreachable | Clarify step: "who will CALL this?" ([GATES §4](../../../gates/GATES.md)) |

Rule of thumb: when the spec feels like overkill, it costs ten minutes — cheap insurance.
When it drags past that, the task was never simple, and the gate just earned its keep.

## Scope control

- Request spans multiple subsystems → split first, spec each part separately.
- The problem dissolves mid-clarify ("nothing to build") → a valid outcome; record it in the
  spec directory and stop. A prevented feature is the cheapest feature.
- In an existing codebase: follow its current patterns; improve only what the change directly
  touches — wandering refactors are a different spec.
