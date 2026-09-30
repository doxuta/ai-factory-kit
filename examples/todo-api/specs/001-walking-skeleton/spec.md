---
feature: 001-walking-skeleton
status: accepted
epic: platform
owner: Hà
approved_by: Hà
approved_on: 2026-09-02
---
<!-- WHO READS ME: anyone looking at Team Todo's first feature — the walking skeleton that
     every later feature stands on. Kept short on purpose: a small feature gets a small spec
     (../../../../model/PHASE-0.md §7 and §10). I POINT TO: plan.md · tasks.md · quickstart.md
     · acceptance.md · ../002-task-crud/ (the first feature built on it). -->

# Feature Specification: Walking skeleton — sign in and see your workspace

**Feature Branch**: `001-walking-skeleton` (no git branch: trunk-based on main)

**Created**: 2026-09-02

**Input**: User description: "Set the project up: a member can sign in and see which
workspace they are in, and every commit goes through the gate chain."

## User Scenarios & Testing *(mandatory)*

**Tests**: required. This project works test-first (constitution Article VI): every user
story below gets test tasks, written and seen to fail before the code that makes them pass.

### User Story 1 - Sign in and see my workspace (Priority: P1)

As a member invited to a workspace, I open the web client, sign in with my invitation token,
and see my name and my workspace, so I know I am in the right place.

**Why this priority**: The thinnest capability that crosses every layer — web client,
handler, service, store, schema — and reaches a member through the real UI.

**Independent Test**: With two members in two workspaces, each signs in and sees their own
name and workspace; a wrong token shows "Not signed in".

**Acceptance Scenarios**:

1. **Given** a member of workspace *beta*, **When** they sign in with their token, **Then** the
   page shows their name and *beta*.
2. **Given** a wrong token, **When** someone signs in with it, **Then** the page shows "Not
   signed in" and no workspace.

---

### User Story 2 - The gate chain guards every commit (Priority: P1)

As the team lead, I run one command and see every gate slot green, and a commit with a red
slot is refused locally and in CI.

**Why this priority**: Every later feature relies on "done" meaning the same thing.

**Independent Test**: `./gates/run-chain.sh --list` shows no `not wired` slot; an unformatted
file is refused at commit.

**Acceptance Scenarios**:

1. **Given** the finished feature, **When** the team lead runs `./gates/run-chain.sh`, **Then**
   every slot is green.
2. **Given** an unformatted source file, **When** anyone commits, **Then** the commit is
   refused and the red slot is named.

### Edge Cases

- No `Authorization` header, or a header that is not `Bearer <token>` → 401 with the error
  envelope.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A member MUST be able to sign in with the token an operator issued for them
  (`todo-admin add-member`).
- **FR-002**: The web client MUST show the signed-in member's name and workspace.
- **FR-003**: A request without a valid token MUST get 401 `UNAUTHENTICATED` in the standard
  envelope.
- **FR-004**: The member's workspace MUST come from their token, never from request input.
- **FR-005**: Every commit MUST pass the gate chain; a commit on red MUST be refused locally
  and in CI.

### Key Entities

- **Workspace**: the unit of ownership; has an id and a name.
- **Member**: belongs to exactly one workspace; signs in with a token stored only as a hash.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Two members of two workspaces each see only their own workspace name — 100% of
  sign-ins.
- **SC-002**: The chain is green with every slot wired, and a deliberately red commit is
  refused every time.

## Assumptions

- Invitation tokens are issued by an operator on the server; self-service sign-up is a later
  spec.
