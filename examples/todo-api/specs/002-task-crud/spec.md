---
feature: 002-task-crud
status: approved
epic: core
owner: Hà
approved_by: Hà
approved_on: 2026-09-06
---
<!-- WHO READS ME: anyone implementing, reviewing or accepting feature 002 — the WHAT/WHY, and
     the feature's technical document (one source). Generated from the kit's spec-template
     override (../../../../speckit/overrides/spec-template.md), so the frontmatter above opens
     at line 1 and holds the only status. I POINT TO: plan.md (HOW) · tasks.md (progress) ·
     quickstart.md (acceptance) · ../../constitution.md (Articles I, II, V). -->

# Feature Specification: Task CRUD — create, list and complete a team's tasks

**Feature Branch**: `002-task-crud` (no git branch: trunk-based on main)

**Created**: 2026-09-05

**Input**: User description: "Members of a workspace can create tasks, see their team's
tasks, and mark one done — and never see another team's."

## User Scenarios & Testing *(mandatory)*

**Tests**: required. This project works test-first (constitution Article VI): every user
story below gets test tasks, written and seen to fail before the code that makes them pass.

### User Story 1 - Create and list my team's tasks (Priority: P1)

As a member of a workspace, I add a task in the web client and see it in my team's list, and
I never see another team's tasks.

**Why this priority**: The minimum loop a team needs; alone it is a usable product.

**Independent Test**: A member of *acme* creates a task and sees it listed; a member of
*beta* lists and does not see it.

**Acceptance Scenarios**:

1. **Given** a signed-in member of workspace *acme*, **When** they create a task titled "Ship
   the report", **Then** it is stored in *acme* and appears at the top of their next list.
2. **Given** members of two workspaces, each with tasks, **When** either lists tasks, **Then**
   the list holds only their own workspace's tasks.

---

### User Story 2 - Complete a task (Priority: P2)

As a member, I mark a task done in the web client and it shows as done.

**Why this priority**: Without it the list only grows, but creating and seeing tasks already
has value.

**Independent Test**: Complete a task twice: both succeed and the task ends done.

**Acceptance Scenarios**:

1. **Given** an open task in my workspace, **When** I mark it done, **Then** it shows as done in
   the next list.
2. **Given** a task that is already done, **When** I mark it done again, **Then** the call
   succeeds and nothing changes (idempotent).

### Edge Cases

- A title that is empty or longer than 200 characters → rejected with a validation error;
  nothing is stored.
- A task id from another workspace → answered exactly as an id that does not exist (see
  Clarifications).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A member MUST be able to create a task with a title of 1–200 characters; the task
  is bound to the member's workspace when it is created, and the binding never changes.
- **FR-002**: Listing tasks MUST return only tasks of the caller's workspace, newest first.
- **FR-003**: A member MUST be able to mark a task of their workspace done; marking a done task
  done again succeeds without changing it.
- **FR-004**: Any operation on a task outside the caller's workspace MUST respond as if the task
  did not exist (not-found semantics, see Clarifications).
- **FR-005**: An empty or over-long title MUST be rejected with a validation error in the
  standard envelope, and nothing is stored.
- **FR-006**: Each capability MUST be operable in the web client (constitution Article V).

### Key Entities

- **Task**: a title, a done flag and creation time; belongs to exactly one workspace.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A created task is in the creator's next list — 100% of attempts.
- **SC-002**: Zero rows from another workspace in any list, checked by the two-workspace probe
  in [quickstart.md](quickstart.md) and on every commit by the `acceptance` slot.
- **SC-003**: A cross-workspace probe cannot tell "exists elsewhere" from "does not exist" by
  status code or body.
- **SC-004**: Completing a task twice gives the same final state and a success response both
  times.

## Assumptions

- Editing titles, deleting tasks, assignees, due dates and pagination beyond a fixed page of 50
  are out of scope; each is a later `specs/NNN-*/`, not a silent extension of this one.

## Clarifications

### Session 2026-09-05

- Q: When a member addresses a task of another workspace, 403 or 404? → A: 404. A 403 confirms
  that the task exists and leaks that across the isolation boundary; addressing another
  workspace's task must be indistinguishable from a nonexistent id (FR-004). (Hà)
