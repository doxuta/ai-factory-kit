---
name: spec-first
description: >-
  The discipline to apply INSIDE /speckit-specify and /speckit-clarify (Spec Kit) for a new
  feature or behavior change: read the repo first, challenge the premise, clarify one question
  at a time, weigh 2-3 options with a stance, and get the owner's explicit approval before any
  code (the HARD-GATE). Not an entry point: a feature starts with /speckit-specify; use this
  while running it, and whenever a change looks "too simple to need a spec". Adapted from
  obra/superpowers brainstorming (MIT).
---
<!-- WHO READS ME: an agent about to build something new — before any code exists.
     I POINT TO (kit paths; factory/... once adopted): model/SPEC-FLOW.md (the full Level-1
     loop) · the project's constitution (Article IV mandates this gate) ·
     harness/agents/requirement-researcher.md (who drafts the input for a vague request) ·
     model/NON-FEATURE-WORK.md (lanes for work that is not a feature) ·
     harness/skills/plan-and-tdd/SKILL.md (the discipline inside /speckit-implement). -->

# Spec-first — no code before an approved spec

The [constitution](../../../constitution/constitution-template.md) Article IV makes this a
HARD-GATE: implementation waits for spec approval. Spec Kit's commands produce the artifacts;
this skill is how you conduct them so that the approval means something. It is never a second
way in: if no `specs/<id>/` exists for the request, the next action is `/speckit-specify`.
Artifact shapes and the order of commands: [SPEC-FLOW](../../../model/SPEC-FLOW.md).

## The procedure

1. **Read before asking.** The code the request touches, prior specs, recent history. Half of
   all clarifying questions are already answered by the repo. For a vague or large request,
   dispatch [`requirement-researcher`](../../agents/requirement-researcher.md) and give its
   draft to `/speckit-specify` as the argument.
2. **Challenge the premise before solving it.** Is this the right problem? What happens if
   nothing is built — real pain or assumption? What existing capability already covers part of
   it? Put the premises to the owner as agree/disagree statements. Is it a feature at all? A
   bug in shipped behaviour, a refactor, a spike or a release has its own lane
   ([NON-FEATURE-WORK](../../../model/NON-FEATURE-WORK.md)).
3. **Run `/speckit-specify`, then clarify one question at a time.** Specify keeps at most three
   `[NEEDS CLARIFICATION]` markers and asks the owner about them; `/speckit-clarify` asks up to
   five more, one at a time, multiple-choice where possible. Answers are written back into
   `spec.md` (its `Clarifications` section) — never into a side file.
4. **Present 2–3 options — mandatory, even when one clearly wins**: minimum-viable (smallest
   slice) · fuller · one lateral. Scope options belong in the spec, before approval; technical
   options come back in `/speckit-plan`'s `research.md` (Decision · Rationale · Alternatives
   considered). Each option with effort, risk, and what it reuses. **Take a stance** and name
   what evidence would change it. "Either works, up to you" is banned — that is sycophancy
   wearing a neutrality costume.
5. **Get explicit approval** on the spec. Silence is not approval. Record it in the spec's
   frontmatter — `status: approved`, `approved_by: <owner>`, `approved_on: <YYYY-MM-DD>` — the
   `spec-approval` gate reads exactly that, and it is red for a ticked task on a draft spec.
6. **Hand off**: `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`,
   with [`plan-and-tdd`](../plan-and-tdd/SKILL.md) as the discipline inside the last one.

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
