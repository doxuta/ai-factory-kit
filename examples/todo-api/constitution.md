<!-- WHO READS ME: anyone studying how the kit's constitution is filled for a multi-tenant web
     product — every agent of the fictional Team Todo project would read it first. This is
     ../../constitution/constitution-template.md filled; in the project it lives at
     .specify/memory/constitution.md. I POINT TO: ../../model/ARCHETYPES.md (the SaaS slot
     choices) · ../../gates/GATES.md (Article VI delegates there) · ../../model/SPEC-FLOW.md
     (Article IV) · ../../harness/HARNESS.md §3 (the mirror rule) · CLAUDE.example.md (the
     mirror) · specs/ (where features live). -->

# Team Todo Constitution

> Invariants for a multi-workspace todo service for small teams. Violating one is a defect to
> fix, not a style choice. Seven articles, numbered I–VII.

**Vision**: for small teams who share one task list · the problem: a team's tasks live in
chat threads and nobody can see what is open · success: a team keeps its tasks in one place,
and no team ever sees another team's tasks.
**Archetype**: multi-tenant SaaS — the slot choices below follow
[ARCHETYPES](../../model/ARCHETYPES.md#multi-tenant-saas).

## Core Principles

### I. Every task belongs to a workspace (NON-NEGOTIABLE)
The workspace is the unit of ownership. A task without a `workspace_id` cannot exist —
enforced by the schema (NOT NULL + foreign key), not by application discipline. There are no
global tasks, no orphan tasks, no personal tasks outside a workspace. A feature that seems to
need one is respecified; the invariant is not.

### II. Every query filters workspace_id
Every read and write on a workspace's data carries a `workspace_id = ?` predicate — no
exceptions, operator tools included — and every SQL statement is parameterized, never
concatenated. The caller's workspace comes from their credential, never from request input.
Stated so a reviewer can grep: a store-layer statement on `tasks` without the predicate is a
breach, not a bug. Two walls check it: the `acceptance` slot's cross-workspace tests on every
commit, and each feature's `quickstart.md` run by a member of a second workspace.

### III. handler → service → store
Handlers parse the request and shape the response envelope; services hold the business
rules; the store owns every SQL statement. No SQL in handlers or services, no HTTP types in
services or the store, no business rules in the store.

### IV. Spec before code
Every feature flows through `specs/<id>/`: spec → plan → tasks → implement
([SPEC-FLOW](../../model/SPEC-FLOW.md)). No implementation before the spec is approved
(**HARD-GATE**): the spec's frontmatter says `status: approved` with `approved_by` and
`approved_on`, and the `spec-approval` gate is red for a ticked task on a draft spec.
`specs/<id>` is the single unit of work; roadmaps are views that point into specs. Work that
is not a feature follows its lane in [NON-FEATURE-WORK](../../model/NON-FEATURE-WORK.md).

### V. Reachability — a capability is done when a member can use it in the web client
A capability is unfinished until a workspace member can operate it in the web client — the
real UI — or the gap is a named task in the feature's `tasks.md`. *API-only ≠ done.* Before
believing a slice is finished, answer: **"who will CALL this?"** The `orphan-endpoints` slot
checks that every route has a caller in the web client ([GATES §4](../../gates/GATES.md)).

### VI. Executable gates and independent acceptance
Always:
- **Gates decide done.** "Done" = the [gate chain](../../gates/GATES.md)
  (`./gates/run-chain.sh`) is green — never a claim, yours included. A subagent's numbers are
  testimony; the orchestrator re-runs the gates itself.
- **Tests first.** Behaviour changes start with a failing test (red → green → refactor), and
  every `tasks.md` carries test tasks ahead of the code they prove.
- **Acceptance by someone other than the builder.** Per feature, a teammate who did not build
  it runs `quickstart.md` in the web client and records `specs/<id>/acceptance.md` before the
  spec becomes `accepted` ([GATES §3](../../gates/GATES.md)).

Where the product has an authorization boundary — it does: workspaces and members:
- **Least-privilege acceptance.** The acceptance run signs in as a plain member of a second
  workspace, never with an operator token, because an operator walks through the wall the run
  exists to test.

### VII. Deliberate simplicity
Within a layer: reuse before stdlib, stdlib before dependency, dependency before new code;
mark intentional shortcuts with a `shortcut:` comment carrying the ceiling and upgrade path.
The layering of Article III and the schema guarantees of Articles I–II are **not**
over-engineering — never collapse them for brevity. When simplicity and the constitution
conflict, the constitution wins.

## Platform Constraints
- **Stack**: Python ≥ 3.11 · FastAPI · SQLite through the standard library's `sqlite3`, foreign
  keys on · web client: static HTML and plain JavaScript served by the application, no build
  step · uvicorn behind a reverse proxy. Decided 2026-09-01 by Hà; rationale: a handful of
  teams on one server, one language for the team; alternatives considered: PostgreSQL
  (deferred, `shortcut:` — one more service to run while the product serves a few teams;
  Articles I–II port unchanged, and the move is its own spec once one database file is the
  bottleneck), a TypeScript single-page app (deferred: a build toolchain for three screens).
- **Dev tools**: pytest and httpx2 (FastAPI's test client), ruff (excluding `factory`, `gates`,
  `.claude`, `.specify`), Node for `node --check` on the web client, uv for `uv build`.
- **Spec Kit**: specify-cli 1.0.12, integration claude; spec numbering sequential `NNN` (specs
  are created on main); extensions adopted: none.
- **Models**: N/A — no LLM or ML component.
- **Conventions**: JSON envelope `{"data": …, "error": …}` with camelCase keys, exactly one side
  non-null · error `{"code": "<MACHINE_CODE>", "message": "…"}` · timestamps ISO 8601 UTC ·
  status codes 200/201/401/404/422.
- **Data changes**: migrations in numbered pairs (`NNNN_name.up.sql` + `.down.sql`) under
  `src/todo/migrations/`; an applied migration is never edited.
- **Environments and release**: TBD — before the first release (a production environment,
  where its secrets live outside the repository, and the post-deploy smoke check that says a
  release is broken); only local development exists while 002 is in flight.
- **Branch model and commits**: trunk-based on `main`; Conventional Commits with a
  `Spec: <id>` trailer ([GATES §10](../../gates/GATES.md)).

## Non-goals (doctrine)
- No cross-workspace sharing and no public tasks — isolation is the product.
- No realtime sync in v1; a reload is acceptable.
- No admin UI in v1; operator actions go through `todo-admin` and migrations, gated the same
  way.

## Development Workflow
1. New feature: the [Level-1 flow](../../model/SPEC-FLOW.md), HARD-GATE at spec approval.
2. Every commit: the [gate chain](../../gates/GATES.md) green; the pre-commit hook and CI run
   the same chain (wired by spec 001, the walking skeleton).
3. Risky surfaces (workspace isolation, authentication, migrations): adversarial review
   ([tech-lead-review](../../harness/agents/tech-lead-review.md)) before commit — findings are
   fixed or explicitly refuted, never shelved.
4. Acceptance: as Article VI says — in the web client, signed in as a plain member of a
   second workspace, recorded in `acceptance.md`.
5. Work that is not a feature: its lane in [NON-FEATURE-WORK](../../model/NON-FEATURE-WORK.md).
6. Docs: the spec IS the feature's technical document. When code and spec disagree, find out
   which one moved. If the spec states intended behaviour the code does not deliver, the code
   is wrong: record a new task (converge). If the code reflects a deliberate, owner-approved
   change the spec never recorded, fix the spec with the correction marked (≠old) and a dated
   Clarifications entry. If you cannot tell, ask the owner.

## Governance
- This constitution outranks every other process document; conflicts resolve in its favor.
- **Amendments**: only Hà, the team lead, approves. Each bump follows semver (MAJOR remove or
  redefine a principle · MINOR add/expand · PATCH clarify), updates the dates, and says what
  changed and why in the commit that makes it.
- ⚠️ **The mirror rule** ([HARNESS §3](../../harness/HARNESS.md) — measured on a production
  repo): path-scoped configuration loads lazily, so Articles I, II, III and VI are mirrored
  into the always-loaded `.claude/CLAUDE.md` (in this example
  [`CLAUDE.example.md`](CLAUDE.example.md)) and into the INVARIANTS block of each agent
  definition. This file is the authoritative copy, not the only copy — amending it means
  syncing the mirrors in the same commit.
- Compliance is checked by runnable gates and review checklists, not by memory.

**Version**: 1.0.0 | **Ratified**: 2026-09-01 | **Last Amended**: 2026-09-01
