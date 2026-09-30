<!-- WHO READS ME: whoever implements, tests or calls the task routes — the contract the
     contract tests (tests/contract/) and quickstart.md assert. I POINT TO: ../spec.md
     (FR-001–FR-005) · ../data-model.md · ../quickstart.md. -->

# Contract: task routes

Every response is the envelope `{"data": <payload> | null, "error": <error> | null}` with
exactly one side non-null; an error is `{"code": "<MACHINE_CODE>", "message": "<text>"}`.
Every route needs `Authorization: Bearer <token>`; the workspace comes from the token.

## `POST /tasks` — create (FR-001, FR-005)

- Request: `{"title": "Ship the report"}`
- `201`: `{"data": {"id": "…", "title": "Ship the report", "done": false, "createdAt": "…"}, "error": null}`
- `422 VALIDATION`: title empty or longer than 200 characters, or a body without `title`;
  nothing stored.
- `401 UNAUTHENTICATED`.

## `GET /tasks` — list the caller's workspace (FR-002)

- `200`: `{"data": {"tasks": [ … newest first, at most 50 … ]}, "error": null}` — only the
  caller's workspace.
- `401 UNAUTHENTICATED`.

## `PATCH /tasks/{task_id}/complete` — mark done (FR-003, FR-004)

- `200`: `{"data": {"id": "…", "done": true, "updatedAt": "…"}, "error": null}`; an already
  done task returns 200 with its state unchanged.
- `404 NOT_FOUND`: the id does not exist **or** belongs to another workspace — the same status
  and the same body either way (Clarifications 2026-09-05).
- `401 UNAUTHENTICATED`.

## Error codes (this feature)

| Code | HTTP | When |
|---|---|---|
| `VALIDATION` | 422 | bad or missing title |
| `NOT_FOUND` | 404 | id nonexistent or in another workspace — indistinguishable |
| `UNAUTHENTICATED` | 401 | missing or unknown token |
