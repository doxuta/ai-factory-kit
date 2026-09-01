<!-- WHO READS ME: anyone who wants to see what "no commit on red" looks like in practice —
     read after the spec cycle files. I POINT TO: ../../gates/GATES.md (the doctrine this
     transcript obeys) · ../../gates/check-plan-sync.sh (gate 6 below) ·
     specs/001-task-crud/tasks.md (the task being landed) · constitution.md (Article II,
     which the red catches). -->

# Gate run — landing M1-T3, red then green

A real-shaped transcript of the [gate chain](../../gates/GATES.md) while landing `M1-T3`
(the workspace-filtered list). `make gate` here wraps the chain in the constitution's
Platform Constraints: format → static analysis → tests → build → orphan-endpoints →
doc-sync. Commands are placeholders; the **shape** is the contract.

## Attempt 1 — red

```console
$ make gate
[1/6] format ......................... ok
[2/6] static analysis ................ ok (0 warnings)
[3/6] tests .......................... FAIL
  --- FAIL: cross_workspace_isolation (store/task_store)
        list(workspace=beta) returned 3 rows, want 2
        leaked row: task 7c9e11 belongs to workspace acme
        hint: list query has no workspace predicate — constitution Article II
  42 passed, 1 failed
GATE RED — no commit. Fix or revert.

$ git commit -m "feat(tasks): workspace-filtered list endpoint"
  REFUSED: gate is red (tests). No commit on red — gates/GATES.md §1.
```

The failure is the exact class [Article II](constitution.md) exists for: the store's list
query shipped without its `workspace_id = ?` predicate. Handler correct, service correct,
one missing predicate — the same bug class was measured on the production repo this kit is
distilled from, which is why the isolation probe is a *required* test in
[tasks.md](specs/001-task-crud/tasks.md) (M1-T3), not an optional nicety.

## The fix — at the store layer, nowhere else

One change, in the layer that owns persistence (no compensating filter bolted into the
handler "to be safe" — that hides the root cause instead of fixing it):

```
store.list:  SELECT … FROM tasks WHERE workspace_id = ?      <- the missing predicate
             ORDER BY created_at DESC LIMIT 50               (parameterized, per Article II)
```

## Attempt 2 — green

```console
$ make gate
[1/6] format ......................... ok
[2/6] static analysis ................ ok (0 warnings)
[3/6] tests .......................... ok
      43 passed, 0 failed, 0 skipped
      filter check: pattern matched 43 tests (≥1 — not a vacuous green)
[4/6] build .......................... ok (artifact built)
[5/6] orphan endpoints ............... ok (3 routes, 3 callers, 0 unexplained)
[6/6] doc-sync ....................... ✅ Docs in sync — 0 plans in format (blueprint checks still ran)
GATE GREEN

$ git commit -m "feat(tasks): workspace-filtered list endpoint (fix: store query filters workspace_id, Article II)"
[main 4f2a9c1] feat(tasks): workspace-filtered list endpoint (fix: store query filters workspace_id, Article II)
```

## What to notice

1. **The red blocked the commit** — the first commit attempt was refused, the fix landed as
   its own honest `fix(…)` commit. No amending the story into "it always worked".
2. **Gate 3 prints its match count.** A test filter matching zero tests exits 0 — the
   *vacuous green* ([GATES §1](../../gates/GATES.md)). A green you can't count is not a green.
3. **Gate 6 is the shipped [`check-plan-sync.sh`](../../gates/check-plan-sync.sh)** and its
   output line is verbatim: this repo has no `*-plan.md` views yet, so it reports
   `0 plans in format` and still runs — self-globbing, never hostage to a missing file
   ([GATES §6](../../gates/GATES.md)).
4. **Green ≠ done.** The chain proves mechanics; acceptance still requires
   [quickstart.md](specs/001-task-crud/quickstart.md) run by a non-privileged member
   ([GATES §3](../../gates/GATES.md)) — gate 3's isolation test and quickstart step 3 check
   the same wall from two independent directions, which is the point.
