<!-- WHO READS ME: the implementer and reviewer of feature 002 — the decisions behind
     plan.md. I POINT TO: plan.md · spec.md (Clarifications) · ../../constitution.md
     (Articles I–III decide most of these). -->

# Research: Task CRUD

## Where isolation is enforced

- **Decision**: in the store — every statement on `tasks` carries `workspace_id = ?` — with
  the schema as the second line (`workspace_id NOT NULL` + FK). The workspace comes from
  `current_member`, never from the request.
- **Rationale**: constitution Article II; one place to grep, one place to review.
- **Alternatives considered**: filtering in the handler (rejected: every new handler must
  remember it, and a handler that forgets leaks); SQLite has no row-level security, so there
  is no database-side option.

## Not found versus forbidden

- **Decision**: completing a task runs `UPDATE … WHERE id = ? AND workspace_id = ?`; zero rows
  updated means `404 NOT_FOUND`, whether the id does not exist or belongs to another workspace.
- **Rationale**: the 2026-09-05 clarification — one code path makes the two cases identical by
  construction instead of by a check someone could forget.
- **Alternatives considered**: look the task up, then compare workspaces (rejected: two paths,
  and the comparison is where 403 creeps back in).

## Ordering and page size

- **Decision**: newest first by `created_at` (ISO 8601 UTC with microseconds); a fixed page of
  50; index `(workspace_id, created_at DESC)`, which is the list query's exact shape.
- **Rationale**: the spec's out-of-scope line defers pagination; the index keeps the one
  query cheap.

## Web client calls

- **Decision**: the page calls the same routes with `fetch` and literal paths (`"/tasks"`,
  `` `/tasks/${id}/complete` ``).
- **Rationale**: the `orphan-endpoints` gate matches literal paths; a path assembled from
  pieces would read as an orphan (the gate's BLIND TO block).
