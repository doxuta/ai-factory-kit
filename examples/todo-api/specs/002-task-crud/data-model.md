<!-- WHO READS ME: the implementer of feature 002 — the schema delta and its invariants.
     I POINT TO: plan.md · research.md · contracts/tasks-api.md · ../../constitution.md
     (Articles I and II). -->

# Data Model: Task CRUD

## Migration `0002_tasks` (up + down, `src/todo/migrations/`)

```sql
CREATE TABLE tasks (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id),
  title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
  done INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX tasks_workspace_created ON tasks (workspace_id, created_at DESC);
```

The down migration drops the index, then the table.

| Field | Rule |
|---|---|
| `id` | server-generated (UUID hex); never taken from input |
| `workspace_id` | set once, from the creator's credential; NOT NULL + FK — Article I at the schema |
| `title` | 1–200 characters, checked by the service and again by the schema |
| `done` | 0 or 1; completing is idempotent |
| `created_at`, `updated_at` | ISO 8601 UTC, microseconds, set by the service |

## In the envelope (camelCase, Platform Constraints)

`{"id": "…", "title": "…", "done": false, "createdAt": "2026-09-06T08:15:02.123456+00:00"}`
— `workspaceId` is never returned: a member has one workspace, and echoing it invites clients
to send it back.
