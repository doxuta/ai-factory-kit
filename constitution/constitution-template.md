<!-- WHO READS ME: an AI filling this in for a new project (with the human), then every agent
     on every feature. I POINT TO: ../gates/GATES.md (Article VI delegates to it) ·
     ../model/SPEC-FLOW.md (Article IV) · ../harness/HARNESS.md §3 (the mirror rule in Governance).
     Worked example: ../examples/todo-api/constitution.md -->

# [PROJECT_NAME] Constitution

> This document is the project's **set of invariants**: violating one is a defect to fix, not a
> style choice. Keep it to 5–7 principles — a constitution that tries to say everything protects
> nothing. Distill from what the human already believes and what the stack demands; do not invent.

## Core Principles

### I. [DOMAIN INVARIANT — the one rule that IS the product]
<!-- The principle that, if broken, means you built a different product. Examples from real
constitutions: "Metadata-first: business objects are registered in metadata and read at runtime —
never hardcoded as structs" · "Local-first: every feature works offline" · "One source of truth
per fact". Mark NON-NEGOTIABLE if nothing may override it. -->

### II. [SAFETY INVARIANT — the rule whose violation is a breach, not a bug]
<!-- Data isolation, tenancy, privacy, money. Example: "Every transactional query filters
tenant_id — no exceptions, admin included; dynamic SQL is parameterized, never concatenated."
State it so a reviewer can grep for violations. -->

### III. [ARCHITECTURE SHAPE — the layering that every change respects]
<!-- Example: "handler → service → repository → entity; no SQL in handlers, no HTTP in services;
every error wrapped with its origin". Name the layers YOUR stack uses. -->

### IV. Spec trước code — Spec before code
Every feature flows through `specs/NNN-<name>/`: spec → plan → tasks → implement
([SPEC-FLOW](../model/SPEC-FLOW.md)). No implementation before the spec is approved
(**HARD-GATE**). `specs/NNN` is the **single unit of work**; roadmaps and backlogs are views
that point into specs, never a second home for content. The spec corpus is a reusable asset:
specs regenerate products, documents, and upgrades.

*RETRO-FIT mode* (name it — don't leave brownfield implicit): work shipped BEFORE this
constitution is spec'd with a `spec.md` **verified against current code** (never transcribed
from old docs) plus runnable Success Criteria; `plan.md`/`tasks.md` are optional — `converge`
generates tasks when code↔spec drift appears. The [deletion condition](../model/RETROFIT-PLAYBOOK.md)
for legacy docs stays unchanged.

### V. Reachability — a capability is not done until someone can reach it
A backend capability is unfinished until it is operable in the real interface, or the gap is a
named task in the feature's `tasks.md`. *API-only ≠ done.* Before believing a slice is finished,
answer: **"who will CALL this?"** (the deadliest bug class is the joint nobody wired —
[GATES §4](../gates/GATES.md)).

### VI. Executable gates over claims
"Done" = the [gate chain](../gates/GATES.md) is green — never a claim, yours included.
Acceptance is proven by a **third person**: a non-privileged account, because privileged
accounts bypass the walls being tested. A subagent's numbers are testimony; the orchestrator
re-runs the gates itself.

### VII. Deliberate simplicity
Within a layer: reuse before stdlib, stdlib before dependency, dependency before new code;
mark intentional shortcuts with a `shortcut:` comment carrying the ceiling and upgrade path.
But the abstractions Articles I–III mandate are **not** over-engineering — never collapse them
for brevity. When simplicity and the constitution conflict, the constitution wins.

## Platform Constraints
<!-- The ONLY stack-specific section. Language+version, framework, database, API conventions
(casing, timestamps, status codes), migration discipline (up+down, sequential, never edit
applied), branch model, commit convention. -->

## Non-goals (doctrine)
<!-- What this project deliberately does NOT do — as protected as the principles. Real examples:
"not self-service SaaS; customers never see the builder" · "no source handover by default" ·
"AI is an optional internal accelerator, never a mandatory per-customer cost". -->

## Development Workflow
1. New feature: the [Level-1 flow](../model/SPEC-FLOW.md), HARD-GATE at spec approval.
2. Every commit: the [gate chain](../gates/GATES.md).
3. Risky surfaces (data, authorization, money): adversarial review
   ([tech-lead-review](../harness/agents/tech-lead-review.md)) before commit — findings are
   fixed or explicitly refuted, never shelved.
4. Acceptance: real interface, non-privileged account, per the feature's `quickstart.md`.
5. Docs: the spec IS the feature's technical document. Deleting a legacy doc follows the
   [retro-fit deletion condition](../model/RETROFIT-PLAYBOOK.md).

## Governance
- This constitution outranks every other process document; conflicts resolve in its favor.
- **Amendments**: only [OWNER] approves. Each bump follows semver (MAJOR remove/redefine a
  principle · MINOR add/expand · PATCH clarify), updates the dates, and prepends a Sync Impact
  Report comment.
- ⚠️ **The mirror rule** (a measured trap — [HARNESS §3](../harness/HARNESS.md)): configuration
  scoped to file paths loads **lazily**; safety invariants (I, II, III, VI) must ALSO live in the
  always-loaded context file and inside each agent definition. The constitution is the
  *authoritative* copy, not the *only* copy — amending it means syncing the mirrors in the same
  commit.
- Compliance is checked by runnable gates and review checklists, not by memory.

**Version**: [X.Y.Z] | **Ratified**: [YYYY-MM-DD] | **Last Amended**: [YYYY-MM-DD]
