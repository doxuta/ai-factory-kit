<!-- WHO READS ME: the implementer of feature 001 — the HOW. Small feature, so data-model and
     contracts live inline here; they split into data-model.md + contracts/ when they outgrow
     one screen (../../../../model/SPEC-FLOW.md step 3). I POINT TO: spec.md (WHAT) ·
     tasks.md (execution order) · quickstart.md (acceptance) · ../../constitution.md
     (Articles II, III bind every choice below). -->

# Plan 001 — Task CRUD

## Approach
Three endpoints through the mandated layering (handler → service → store,
[Article III](../../constitution.md)). Stack: **[any HTTP framework] + [any SQL DB]** — all
contracts below are transport-level and survive any stack choice. Isolation is enforced at
the store layer (every query carries the workspace predicate, [Article II](../../constitution.md))
and double-checked by schema (`workspace_id NOT NULL` + FK, [Article I](../../constitution.md)).
The caller's workspace comes from the authenticated session, never from request input.

## Data model

```
tasks
  id            unique id (server-generated)
  workspace_id  NOT NULL, FK -> workspaces.id, indexed   -- Article I: binding at birth
  title         text, length 1..200 enforced at both validation and schema level
  done          boolean, default false
  created_at    timestamp UTC
  updated_at    timestamp UTC

index: (workspace_id, created_at desc)   -- the list query's exact shape
migration: one numbered pair, up + down  -- constitution Platform Constraints
```

## Contracts

Envelope (all responses): `{"data": <payload> | null, "error": <error> | null}` — exactly one
side non-null. Error shape: `{"code": "<MACHINE_CODE>", "message": "<human text>"}`.

### POST /tasks — create (FR-001, FR-005)
- Request: `{"title": "Ship the report"}`
- 201: `{"data": {"id": "…", "title": "…", "done": false, "createdAt": "…"}, "error": null}`
- 422 `VALIDATION`: empty or >200-char title; nothing persisted.
- 401 `UNAUTHENTICATED`: no session.

### GET /tasks — list own workspace (FR-002)
- 200: `{"data": {"tasks": [ …newest first… ]}, "error": null}` — only the caller's
  workspace, fixed page size 50 (pagination beyond this is out of scope per spec).
- 401 `UNAUTHENTICATED`.

### PATCH /tasks/:id/complete — mark done (FR-003, FR-004)
- 200: `{"data": {"id": "…", "done": true, "updatedAt": "…"}, "error": null}` — idempotent:
  an already-done task returns 200 with unchanged state.
- 404 `NOT_FOUND`: id nonexistent **or** belongs to another workspace — identical response
  either way (spec Clarification 2026-09-01: no existence leak).
- 401 `UNAUTHENTICATED`.

### Error code table (this feature)
| Code | HTTP | When |
|---|---|---|
| `VALIDATION` | 422 | title empty or >200 chars |
| `NOT_FOUND` | 404 | id nonexistent or cross-workspace (indistinguishable) |
| `UNAUTHENTICATED` | 401 | missing/invalid session |

## Layer responsibilities (pseudo, stack-neutral)

```
handler.create   parse+validate title -> service.create(session.workspace, title) -> 201 envelope
service.create   business rules (none yet beyond validation) -> store.insert
store.insert     INSERT … (workspace_id, title) VALUES (?, ?)          -- parameterized
store.list       SELECT … WHERE workspace_id = ? ORDER BY created_at DESC LIMIT 50
store.complete   UPDATE tasks SET done = true, updated_at = now()
                 WHERE id = ? AND workspace_id = ?                     -- 0 rows -> NOT_FOUND
```

`store.complete` returning zero affected rows is the single code path behind both "not there"
and "not yours" — the 404 indistinguishability falls out of the query shape rather than being
bolted on. [EXAMPLE: in a Go + MySQL stack this is `RowsAffected() == 0` after a prepared
`UPDATE`; any stack has the equivalent.]

## Test intent (full ordering in [tasks.md](tasks.md))
Unit: title validation edges (0, 1, 200, 201 chars) · idempotent complete. Integration: the
two-workspace isolation probe — create in A, list from B must not leak (SC-2), cross-workspace
complete must 404 (SC-3). Acceptance: [quickstart.md](quickstart.md) run by a non-privileged
member ([GATES §3](../../../../gates/GATES.md)). Beware the vacuous green: a test filter
matching zero tests exits 0 ([GATES §1](../../../../gates/GATES.md)).
