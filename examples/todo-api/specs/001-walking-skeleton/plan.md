<!-- WHO READS ME: the implementer of Team Todo's walking skeleton — the HOW. Small feature, so
     the data model and the one contract are folded in here while they fit one screen
     (../../../../model/PHASE-0.md §10); feature 002 shows them split out. I POINT TO: spec.md ·
     tasks.md · quickstart.md · ../../constitution.md (Platform Constraints hold the stack). -->

# Implementation Plan: Walking skeleton — sign in and see your workspace

**Branch**: `001-walking-skeleton` (trunk-based) | **Date**: 2026-09-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-walking-skeleton/spec.md`

## Summary

The project skeleton in the constitution's layering, one route (`GET /me`), a sign-in page in
the web client, the `members` and `workspaces` tables, an operator command to issue tokens,
and every slot of the gate chain wired, with the hook and CI installed last.

## Technical Context

The stack is the constitution's [Platform Constraints](../../constitution.md#platform-constraints).
This feature adds:

**Language/Version**: Python 3.11 · **Primary Dependencies**: FastAPI, uvicorn ·
**Storage**: SQLite, migration `0001_members` · **Testing**: pytest with FastAPI's test client
(httpx2) · **Target Platform**: Linux server · **Project Type**: web service with a static web
client · **Performance Goals**: none yet · **Constraints**: tokens stored only as SHA-256
hashes · **Scale/Scope**: a few teams

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Re-checked: unchanged.

| Article | What this plan does | Status |
|---|---|---|
| I | `members.workspace_id NOT NULL` + FK to `workspaces` | PASS |
| II | the workspace comes from the token (`current_member`), never from input; the store's one statement is parameterized | PASS |
| III | `api/me.py` → `service.whoami` / `service.authenticate` → `store.member_by_token` | PASS |
| IV | spec approved 2026-09-02 by Hà | PASS |
| V | `GET /me` is called by the web client's sign-in page; `orphan-endpoints` is wired in this feature | PASS |
| VI | chain wired (T001–T006), tests first, acceptance by a teammate as a member of a second workspace | PASS |
| VII | no dependency beyond FastAPI and uvicorn | PASS |

## Data model (folded)

```text
workspaces  id TEXT PK · name TEXT NOT NULL
members     id TEXT PK · workspace_id TEXT NOT NULL → workspaces.id · name TEXT NOT NULL
            · token_sha256 TEXT NOT NULL UNIQUE
migration   src/todo/migrations/0001_members.up.sql + .down.sql
```

## Contract (folded): `GET /me`

- `200 {"data": {"name": "alice", "workspace": "acme"}, "error": null}`
- `401 {"data": null, "error": {"code": "UNAUTHENTICATED", "message": "sign in first"}}` —
  no header, a scheme other than `Bearer`, or an unknown token.

## Project Structure

```text
pyproject.toml                 console script todo-admin
src/todo/app.py                routers, the error envelope, the web client mount
src/todo/api/deps.py           envelope, current_member, get_conn
src/todo/api/me.py             GET /me
src/todo/service.py · store.py · db.py · admin.py
src/todo/migrations/0001_members.{up,down}.sql
src/todo/web/index.html · app.js
tests/unit/ · tests/contract/ · tests/isolation/
gates/chain.conf · gates/orphan-endpoints.conf
```

**Structure Decision**: one package in a src layout; the web client ships inside it so the
wheel serves it.

## Complexity Tracking

None.

## Release

Out of scope for this feature: nothing is deployed yet. The first deploy is a release-lane
decision once feature 002 is accepted.
