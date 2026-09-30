<!-- WHO READS ME: the implementing agent and whoever checks progress; the gates read the
     checkboxes. Every task is done: this spec is accepted. I POINT TO: plan.md · spec.md ·
     acceptance.md · ../../gates/chain.conf (what Phases 1–2 wired). -->

# Tasks: Walking skeleton — sign in and see your workspace

**Input**: Design documents from `/specs/001-walking-skeleton/`

**Prerequisites**: plan.md, spec.md

**Tests**: REQUIRED - the project works test-first (constitution Article VI). Each user story
phase lists its test tasks first. A task that changes no testable behaviour says so on its own
line: `(test-exempt: <reason>)`.

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Create pyproject.toml (hatchling, src layout, FastAPI and uvicorn, console script `todo-admin`, ruff `extend-exclude = ["factory", "gates", ".claude", ".specify"]`, pytest `testpaths = ["tests"]`) and the package skeleton under src/todo/ (test-exempt: packaging only; T008 exercises it)
- [x] T002 [P] Wire `format: ruff format --check .` and `static: ruff check . && node --check src/todo/web/app.js` in gates/chain.conf and the same commands in .claude/CLAUDE.md (test-exempt: gate wiring; T013 proves the chain bites)
- [x] T003 Wire `test: pytest -q tests/unit tests/contract` once T007's first test was seen red, then green (test-exempt: gate wiring)
- [x] T004 [P] Wire `build: uv build` (test-exempt: gate wiring)

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T005 Migration pair 0001_members (workspaces, members with `workspace_id NOT NULL` + FK, token hash) in src/todo/migrations/ and the runner in src/todo/db.py; test in tests/unit/test_migrations.py: up, down, up applies clean
- [x] T006 Wire `orphan-endpoints: ./gates/check-orphan-endpoints.sh` with gates/orphan-endpoints.conf and `acceptance: pytest -q tests/isolation`; settle the TBD lines in Platform Constraints and .claude/CLAUDE.md (test-exempt: gate wiring; T013 proves the chain bites)

## Phase 3: User Story 1 - Sign in and see my workspace (Priority: P1) 🎯 MVP

### Tests for User Story 1 (REQUIRED - write them first, watch them fail) ⚠️

- [x] T007 [P] [US1] Failing contract tests: `GET /me` returns the member and workspace; no token gives 401 UNAUTHENTICATED, in tests/contract/test_me_api.py
- [x] T008 [P] [US1] Failing isolation test: each member's token resolves to their own workspace, in tests/isolation/test_identity.py

### Implementation for User Story 1

- [x] T009 [US1] store.member_by_token and store.add_member in src/todo/store.py; service.authenticate and service.whoami in src/todo/service.py
- [x] T010 [US1] `GET /me` in src/todo/api/me.py, the envelope and current_member in src/todo/api/deps.py, wiring in src/todo/app.py
- [x] T011 [US1] Sign-in page calling `GET /me` in src/todo/web/index.html and src/todo/web/app.js (Article V)
- [x] T012 [US1] `todo-admin add-member` in src/todo/admin.py (test-exempt: operator command; quickstart setup runs it)

## Phase 4: User Story 2 - The gate chain guards every commit (Priority: P1)

- [x] T013 [US2] `python3 factory/bin/adopt.py --install-git-hook --ci github`, the CI job's toolchain steps (Python 3.11, Node, uv, `pip install -e . pytest httpx2 ruff`), then prove the hook refuses a deliberately unformatted file (test-exempt: the refusal is the test)

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T014 Acceptance: someone other than the builder runs quickstart.md in the web client, signed in as a plain member of a second workspace, and records specs/001-walking-skeleton/acceptance.md
