<!-- WHO READS ME: the implementing agent (top-to-bottom, dependency order) and the human
     checking progress at a glance. I POINT TO: plan.md (each task implements a piece of it) ·
     quickstart.md (M3 runs it) · ../../../../gates/check-plan-sync.sh (whose header↔table
     format this file demonstrates) · ../../README.md (why this file is NOT *-plan.md). -->

# Tasks 001 — Task CRUD

> **Progress format note.** The header bars and the ✅/⬜ status column below are the exact
> format [`check-plan-sync.sh`](../../../../gates/check-plan-sync.sh) parses — header says
> `2/3`, table must count `2/3`, or the gate exits red. This file is deliberately named
> `tasks.md` (the atom's task list), which the gate's `*-plan.md` glob does **not** match:
> gate coverage is opted into by roadmap *views* named `docs/<epic>-plan.md` carrying this
> same format. See [`../../README.md`](../../README.md), deliberate choice 1.

## 📍 Progress

M1 [✅✅⬜] 2/3 — schema + create/list
M2 [⬜⬜⬜] 0/3 — complete + isolation
M3 [⬜⬜] 0/2 — acceptance + converge

Total: 2/8 *(grand total — the shipped gate accepts `Tổng:` or `Total:`)*

## M1 — Schema + create/list (P1)

| Status | Task | What + verify |
|---|---|---|
| ✅ | M1-T1 | Migration pair: `tasks` table per [plan.md](plan.md) data model — `workspace_id NOT NULL` + FK + index. Verify: `up` then `down` then `up` applies clean. |
| ✅ | M1-T2 | `POST /tasks` through handler → service → store; title validation edges (0/1/200/201 chars) red → green first. Verify: unit tests + 201/422 envelope shapes. |
| ⬜ | M1-T3 | `GET /tasks` list, workspace-filtered, newest first, page 50. Verify: two-workspace isolation probe (create in A, list from B — zero leaks). **Depends: M1-T1, M1-T2** (needs rows to leak). |

## M2 — Complete + isolation (P2)

| Status | Task | What + verify |
|---|---|---|
| ⬜ | M2-T1 | `PATCH /tasks/:id/complete`, idempotent via the zero-rows-affected shape in [plan.md](plan.md). Verify: done→done twice, identical state. **Depends: M1-T3.** |
| ⬜ | M2-T2 | Cross-workspace 404 semantics on complete (spec Clarification 2026-09-01): nonexistent id and other-workspace id return byte-identical responses. Verify: integration test asserts both. **Depends: M2-T1.** |
| ⬜ | M2-T3 | Wire the client call for complete (constitution [Article V](../../constitution.md): *who will CALL this?*). Verify: orphan-endpoint gate lists 0 unexplained routes. **Depends: M2-T1.** |

## M3 — Acceptance + converge

| Status | Task | What + verify |
|---|---|---|
| ⬜ | M3-T1 | Run [quickstart.md](quickstart.md) end-to-end as a **non-privileged member** ([GATES §3](../../../../gates/GATES.md)); paste transcript into the PR/commit body. **Depends: all M2.** |
| ⬜ | M3-T2 | `converge` pass: code ↔ [spec.md](spec.md) drift check; differences become new tasks here, never silent edits. Flip spec `status: shipped`. **Depends: M3-T1.** |

## Conventions demonstrated

- A task flips ⬜→✅ **and** its milestone header bar updates **in the same commit** — that
  atomicity is exactly what the sync gate enforces on `*-plan.md` views.
- Every task names its verify step; "done" without a verify line is not a task, it's a hope.
- Dependencies are explicit so a [task-orchestra](../../../../harness/agents/task-orchestra.md)
  dispatch can parallelize only what is truly file-disjoint (here: nothing — small feature,
  sequential is simpler; [Article VII](../../constitution.md)).
