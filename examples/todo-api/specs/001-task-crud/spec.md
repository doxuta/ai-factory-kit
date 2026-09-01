<!-- WHO READS ME: anyone implementing or reviewing feature 001 — the WHAT/WHY. This file is
     the feature's technical document (one source). I POINT TO: plan.md (HOW) · tasks.md
     (execution) · quickstart.md (acceptance) · ../../constitution.md (Articles I, II, V)
     · ../../../../model/SPEC-FLOW.md (the flow that produced me). -->

```yaml
feature: 001-task-crud
status: approved        # draft | approved | shipped | superseded
epic: core              # label only — the atom is this directory
```

# Spec 001 — Task CRUD

## Why
A team's tasks live in its workspace and nowhere else (constitution
[Article I](../../constitution.md)). This feature delivers the minimum loop a team needs:
create a task, see the team's tasks, mark one done — with workspace isolation proven, not
assumed.

## User stories (prioritized; each independently testable)

### P1 — Create and list own tasks (viable MVP alone)
- **Given** a signed-in member of workspace *acme*,
  **When** they create a task with title "Ship the report",
  **Then** the task is stored in *acme* and appears in their next list read.
- **Given** members of two different workspaces each with existing tasks,
  **When** either member lists tasks,
  **Then** the response contains only their own workspace's tasks — never the other's.

### P2 — Complete a task
- **Given** an open task in the member's workspace,
  **When** the member marks it complete,
  **Then** the task shows as done in the next list read.
- **Given** a task that is already complete,
  **When** the member marks it complete again,
  **Then** the call succeeds and the task state is unchanged (idempotent).

## Functional requirements

| ID | Requirement |
|---|---|
| FR-001 | A workspace member can create a task with a title of 1–200 characters; the task is bound to the member's workspace at creation and the binding never changes. |
| FR-002 | Listing tasks returns only tasks of the caller's workspace, newest first. |
| FR-003 | A member can mark a task in their workspace complete; completing an already-complete task succeeds without changing state (idempotent). |
| FR-004 | Any operation addressing a task outside the caller's workspace responds as if the task does not exist (not-found semantics — see Clarifications). |
| FR-005 | An empty or over-length title is rejected with a validation error in the standard envelope; nothing is persisted. |

## Success criteria (measurable, technology-agnostic)

- SC-1: A created task is visible in the creator's list on the immediately following read —
  100% of attempts.
- SC-2: Zero cross-workspace rows in any list response, verified by the two-workspace probe
  in [quickstart.md](quickstart.md) (step 3).
- SC-3: A cross-workspace access probe cannot distinguish "task exists elsewhere" from "task
  does not exist" by status code or body (quickstart step 4).
- SC-4: Completing a task twice yields identical final state and a success response both
  times.

## Out of scope
Editing titles · deleting tasks · assignees · due dates · pagination beyond a fixed page
size. Each is a future `specs/NNN-*/`, not a silent extension of this one.

## Clarifications

- **2026-09-01 — Q:** When a member addresses a task belonging to another workspace, do we
  return 403 (forbidden) or 404 (not found)?
  **A:** **404.** A 403 confirms the task exists, leaking existence across the isolation
  boundary. Cross-workspace addressing is indistinguishable from a nonexistent id (FR-004);
  the acceptance probe in [quickstart.md](quickstart.md) asserts this exact behavior.
