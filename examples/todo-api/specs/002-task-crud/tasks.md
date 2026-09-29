<!-- WHO READS ME: the implementing agent (top to bottom, dependency order) and whoever checks
     progress — the gates read the checkboxes. Shown mid-flight: User Story 1 has landed
     (GATE-RUN.md is the commit that landed T002–T008), User Story 2 has not started. Shaped by
     the kit's tasks-template override (../../../../speckit/overrides/tasks-template.md).
     I POINT TO: plan.md · spec.md · quickstart.md (T014 runs it) · ../../GATE-RUN.md. -->

# Tasks: Task CRUD — create, list and complete a team's tasks

**Input**: Design documents from `/specs/002-task-crud/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/tasks-api.md

**Tests**: REQUIRED - the project works test-first (constitution Article VI). Each user story
phase lists its test tasks first; each test is written and seen to FAIL before the
implementation task that makes it pass. A task that changes no testable behaviour says so on
its own line: `(test-exempt: <reason>)`.

**Organization**: Tasks are grouped by user story. There is no Setup phase: feature 001, the
walking skeleton, set the project and the gate chain up.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

## Phase 1: Foundational (Blocking Prerequisites)

- [x] T001 Migration pair 0002_tasks per data-model.md — `workspace_id TEXT NOT NULL REFERENCES workspaces(id)`, `title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 200)`, index `(workspace_id, created_at DESC)` — in src/todo/migrations/; tests/unit/test_migrations.py (up, down, up applies clean) covers it

**Checkpoint**: the schema exists; the stories can start.

---

## Phase 2: User Story 1 - Create and list my team's tasks (Priority: P1) 🎯 MVP

**Goal**: a member adds tasks in the web client and sees only their workspace's list.

**Independent Test**: acme's task is listed for acme and absent for beta.

### Tests for User Story 1 (REQUIRED - write them first, watch them fail) ⚠️

- [x] T002 [P] [US1] Failing unit tests: title length 0, 1, 200, 201 — only 1 and 200 reach the store, in tests/unit/test_validation.py
- [x] T003 [P] [US1] Failing contract tests: `POST /tasks` returns the 201 envelope; `GET /tasks` is newest first; an empty title is 422 `VALIDATION` and nothing is stored; no token is 401, in tests/contract/test_tasks_api.py
- [x] T004 [P] [US1] Failing isolation test: a task created in acme never appears in beta's list, in tests/isolation/test_cross_workspace.py

### Implementation for User Story 1

- [x] T005 [US1] store.insert_task and store.list_tasks — every statement on `tasks` carries `workspace_id = ?` — in src/todo/store.py
- [x] T006 [US1] service.create_task (title 1–200, timestamps) and service.list_tasks in src/todo/service.py
- [x] T007 [US1] `POST /tasks` and `GET /tasks` in src/todo/api/tasks.py; include the router in src/todo/app.py
- [x] T008 [US1] Web client: the new-task form and the list, calling `POST /tasks` and `GET /tasks`, in src/todo/web/index.html and src/todo/web/app.js (Article V: who will CALL this?)

**Checkpoint**: User Story 1 works on its own in the web client.

---

## Phase 3: User Story 2 - Complete a task (Priority: P2)

**Goal**: a member marks a task done; doing it twice changes nothing.

**Independent Test**: complete twice, both 200, final state done.

### Tests for User Story 2 (REQUIRED - write them first, watch them fail) ⚠️

- [ ] T009 [P] [US2] Failing contract tests: `PATCH /tasks/{task_id}/complete` returns 200 with `done: true`; a second call returns 200 and the same state, in tests/contract/test_tasks_api.py
- [ ] T010 [P] [US2] Failing isolation test: completing another workspace's task and completing a nonexistent id return the same 404 `NOT_FOUND` body, in tests/isolation/test_cross_workspace.py

### Implementation for User Story 2

- [ ] T011 [US2] store.complete_task — `UPDATE tasks SET done = 1, updated_at = ? WHERE id = ? AND workspace_id = ?`, zero rows means not found — in src/todo/store.py, and service.complete_task in src/todo/service.py
- [ ] T012 [US2] `PATCH /tasks/{task_id}/complete` in src/todo/api/tasks.py, mapping not found to 404 `NOT_FOUND`
- [ ] T013 [US2] Web client: a "done" control on each task calling `PATCH /tasks/{id}/complete`, in src/todo/web/app.js (Article V)

---

## Phase 4: Polish & Cross-Cutting Concerns

- [ ] T014 Acceptance: someone other than the builder runs quickstart.md in the web client, signed in as a plain member of a second workspace, and records specs/002-task-crud/acceptance.md

---

## Dependencies & Execution Order

- T001 before both stories. US2 builds on US1's routes and list.
- Within each story: tests, then store → service → handler → web client.
- The [P] test tasks of a story touch different files and can be written in parallel; the
  implementation tasks touch shared files (store.py, service.py) and stay sequential.

## Notes

- A task is ticked in the commit that lands it, with the gate chain green. A test task and the
  code that turns it green land in the same commit: a failing test alone would be a commit on
  red.
- A task moved out of this feature stays listed, unticked, marked `(deferred → <spec id>)`.
