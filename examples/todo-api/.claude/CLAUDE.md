<!-- WHO READS ME: the always-loaded context of the EXAMPLE project — demonstrating the
     constitution's mirror rule (see ../constitution.md §Governance and the kit's
     ../../../harness/HARNESS.md §3). -->

# Team Todo API — always-loaded context

Todo API for small teams; every todo belongs to a workspace. Constitution (authoritative):
`.specify/memory/constitution.md` — in this example: [`../constitution.md`](../constitution.md).

## Mirrored safety invariants (constitution I, II, III, VI — the mirror rule)

- **I. Workspace-scoped**: every todo/list/comment belongs to exactly one workspace.
- **II. Isolation (NON-NEGOTIABLE)**: every query filters `workspace_id`; parameterized only.
- **III. Layers**: handler → service → store; no SQL in handlers, no HTTP in services.
- **VI. Gates over claims**: done = gate chain green (`make gate`); acceptance by a
  NON-privileged account per the feature's `quickstart.md`.

## Flow

New feature → `specs/NNN-*/` (spec approved BEFORE code) → TDD → `make gate` → review → commit.
