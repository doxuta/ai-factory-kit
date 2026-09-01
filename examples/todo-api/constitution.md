<!-- WHO READS ME: every agent working on Team Todo API, before anything else — this is the
     filled version of ../../constitution/constitution-template.md. I POINT TO:
     ../../gates/GATES.md (Article VI delegates there) · ../../model/SPEC-FLOW.md (Article IV)
     · ../../harness/HARNESS.md §3 (the mirror rule) · specs/ (where features live). -->

# Team Todo API Constitution

> Invariants for a multi-workspace todo service. Violating one is a defect to fix, not a
> style choice.

## Core Principles

### I. Every todo belongs to a workspace (NON-NEGOTIABLE)
The workspace is the unit of ownership. A task row without a `workspace_id` cannot exist —
enforced at the schema level (NOT NULL + foreign key), not by application discipline. There
are no global tasks, no orphan tasks, no "personal" tasks outside a workspace. If a feature
seems to need one, the feature is respecified, not the invariant.

### II. Every query filters workspace_id
Every read and write on transactional tables carries a `workspace_id = ?` predicate — no
exceptions, privileged accounts included — and all dynamic SQL is parameterized, never
concatenated. Stated so a reviewer can grep for violations: any store-layer query on `tasks`
lacking the predicate is a breach, not a bug. The acceptance probe for this lives in
[`specs/001-task-crud/quickstart.md`](specs/001-task-crud/quickstart.md) step 3.

### III. handler → service → store
Handlers parse/validate transport and shape responses; services hold business rules; stores
own persistence. No SQL in handlers, no HTTP types in services, no business rules in stores.
Every error is wrapped with its origin (`layer.method: cause`) on the way up.

### IV. Spec before code
Every feature flows through `specs/NNN-<name>/`: spec → clarify → plan → tasks → implement →
converge ([SPEC-FLOW](../../model/SPEC-FLOW.md)). No implementation before the spec is
approved (**HARD-GATE**). `specs/NNN` is the single unit of work; roadmaps and backlogs are
views that point into specs, never a second home for content.

### V. Reachability — a capability is not done until someone can reach it
An endpoint no client calls is unfinished until the call is wired or the gap is a named task
in the feature's `tasks.md`. *API-only ≠ done.* Before believing a slice finished, answer:
**"who will CALL this?"** ([GATES §4](../../gates/GATES.md)).

### VI. Executable gates over claims
"Done" = the [gate chain](../../gates/GATES.md) is green — never a claim, yours included.
Acceptance runs as a **third person**: a plain workspace member, never an operator account,
because privileged accounts bypass the walls being tested ([GATES §3](../../gates/GATES.md)).
A subagent's numbers are testimony; the orchestrator re-runs the gates itself.

### VII. Deliberate simplicity
Within a layer: reuse before stdlib, stdlib before dependency, dependency before new code.
Mark intentional shortcuts with a `shortcut:` comment carrying the ceiling and upgrade path.
The layering of Article III and the schema guarantees of Articles I–II are **not**
over-engineering — never collapse them for brevity. When simplicity and this constitution
conflict, the constitution wins.

## Platform Constraints
Stack: **[any HTTP framework] + [any SQL DB]** — this example is deliberately generic; a real
project names language+version, framework, and database here, and nowhere else.
Conventions regardless of stack: JSON envelope `{"data": …, "error": …}` with camelCase keys ·
timestamps ISO 8601 UTC · standard REST status codes (`201/200/401/404/422`) · migrations in
sequentially numbered pairs (`up` + `down`), applied migrations never edited · trunk-based on
`main`, conventional commits (`type(scope): description`), no commit on a red gate.

## Non-goals (doctrine)
- No cross-workspace sharing or "public" tasks — isolation is the product.
- No realtime sync in v1; polling reads are acceptable.
- No admin UI in v1; operator actions go through migrations and scripts, gated the same way.

## Development Workflow
1. New feature: the [Level-1 flow](../../model/SPEC-FLOW.md), HARD-GATE at spec approval.
2. Every commit: the [gate chain](../../gates/GATES.md) — see [`GATE-RUN.md`](GATE-RUN.md)
   for a real transcript.
3. Anything touching isolation or authorization: adversarial review
   ([tech-lead-review](../../harness/agents/tech-lead-review.md)) before commit — findings
   fixed or refuted with evidence, never shelved.
4. Acceptance: real interface, non-privileged member account, per the feature's
   `quickstart.md`.
5. The spec IS the feature's technical document — one source, corrections marked.

## Governance
- This constitution outranks every other process document; conflicts resolve in its favor.
- **Amendments**: only the team lead approves. Semver per bump (MAJOR remove/redefine ·
  MINOR add/expand · PATCH clarify), dates updated, Sync Impact Report comment prepended.
- ⚠️ **The mirror rule** ([HARNESS §3](../../harness/HARNESS.md) — measured on a production
  repo): path-scoped config loads lazily, so Articles I, II, III, VI are mirrored into the
  always-loaded context file and into each agent definition. This file is the *authoritative*
  copy, not the *only* copy — amending it means syncing the mirrors in the same commit.
- Compliance is checked by runnable gates and review checklists, not by memory.

**Version**: 1.0.0 | **Ratified**: 2026-09-01 | **Last Amended**: 2026-09-01
