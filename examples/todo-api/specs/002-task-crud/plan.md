<!-- WHO READS ME: the implementer of feature 002 — the HOW. Filled from Spec Kit's plan
     template (the kit ships no plan override). I POINT TO: spec.md (WHAT) · research.md ·
     data-model.md · contracts/tasks-api.md · quickstart.md · tasks.md ·
     ../../constitution.md (Articles I–III bind every choice below). -->

# Implementation Plan: Task CRUD — create, list and complete a team's tasks

**Branch**: `002-task-crud` (trunk-based) | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-task-crud/spec.md`

## Summary

Three routes through the mandated layering (handler → service → store), a `tasks` table whose
schema enforces the workspace binding, and the web client's form, list and "done" control.
Isolation is enforced in the store — every statement carries `workspace_id = ?` — and proven
on every commit by the `acceptance` slot's two-workspace tests.

## Technical Context

The stack is the constitution's [Platform Constraints](../../constitution.md#platform-constraints),
already running since feature 001. This feature adds:

**Language/Version**: Python 3.11 (no change)

**Primary Dependencies**: none new

**Storage**: SQLite — migration `0002_tasks` ([data-model.md](data-model.md))

**Testing**: pytest — `tests/unit` (validation, migrations), `tests/contract` (the routes'
contract), `tests/isolation` (the cross-workspace wall; the chain's `acceptance` slot)

**Target Platform**: Linux server, browsers for the web client

**Project Type**: web service with a static web client

**Performance Goals**: a list of 50 tasks in under 100 ms on the test server

**Constraints**: every `tasks` statement parameterized and workspace-filtered (Article II)

**Scale/Scope**: a few teams, thousands of tasks

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Re-checked after
Phase 1: unchanged.

| Article | What this plan does | Status |
|---|---|---|
| I Every task belongs to a workspace | `tasks.workspace_id NOT NULL` + FK; set once from the credential | PASS |
| II Every query filters workspace_id | every store statement on `tasks` carries `workspace_id = ?`; parameterized; tested by `tests/isolation` on every commit | PASS |
| III handler → service → store | `api/tasks.py` → `service` (validation) → `store` (SQL) | PASS |
| IV Spec before code | approved 2026-09-06 by Hà | PASS |
| V Reachability | each route has a web-client caller task (T008, T013); the `orphan-endpoints` slot checks it | PASS |
| VI Gates and independent acceptance | test tasks first in both stories; acceptance by a teammate as a plain member of a second workspace (T014) | PASS |
| VII Deliberate simplicity | no new dependency; one query shape per route | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/002-task-crud/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── tasks-api.md
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
src/todo/migrations/0002_tasks.{up,down}.sql
src/todo/store.py        insert_task · list_tasks · complete_task
src/todo/service.py      create_task (validation) · list_tasks · complete_task
src/todo/api/tasks.py    POST /tasks · GET /tasks · PATCH /tasks/{task_id}/complete
src/todo/web/            the form, the list, the "done" control
tests/unit/test_validation.py · tests/contract/test_tasks_api.py
tests/isolation/test_cross_workspace.py
```

**Structure Decision**: extends feature 001's layout; nothing new at the top level.

## Complexity Tracking

None — no Constitution Check violation.

## Release

The first deploy happens after this feature is accepted, in the
[release lane](../../../../model/NON-FEATURE-WORK.md) with the web-service gate
([GATES §9](../../../../gates/GATES.md)): staging deploy, smoke, rollback rehearsed.
Migration `0002_tasks` only adds a table, so it runs before the deploy; rolling back the code
leaves an unused table, and the down migration drops it once nothing reads it.
