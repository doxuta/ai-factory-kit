<!-- WHO READS ME: anyone who wants to see what "no commit on red" looks like in practice —
     read after the spec files. I POINT TO: gates/chain.conf and gates/orphan-endpoints.conf
     (the slots run below) · specs/002-task-crud/tasks.md (T002–T008, the tasks being landed) ·
     ../../gates/run-chain.sh, ../../gates/check-orphan-endpoints.sh,
     ../../gates/hooks/pre-commit (what printed this) · constitution.md (Articles II and V,
     which the two reds enforce). -->

# Gate run — landing User Story 1 of 002-task-crud, red twice, then green

Every line in the transcripts below was printed by a real run on 2026-09-29. The run replayed
the landing of tasks T002–T008 in a scratch git repository: this kit (1.4.0) adopted with
`adopt.py --profile full`, specify-cli 1.0.12, this directory's documents copied in, and a
small implementation of the plan (FastAPI, SQLite, a plain JavaScript client — about 470
lines of Python, SQL, HTML and JavaScript under `src/todo/` and `tests/`). Tools: Python
3.11.15, fastapi 0.141.1, starlette 1.7.0, httpx2 2.13.1, pytest 9.1.1, ruff 0.16.9, uv
0.8.17, Node 22.22.2. Commit hashes and object addresses are the replay's.

The source is not shipped with the kit — a `tests/` directory inside `factory/` is collected
by an adopter's plain `pytest -q` ([measured](../budget-cli/GATE-RUN.md)) — but the spec
slots can be re-run on this directory as it is ([Reproduce](#reproduce)).

## The chain

```console
$ ./gates/run-chain.sh --list
gates/chain.conf: 9 slots - 9 wired, 0 N/A, 0 not wired
  format             run      ruff format --check .
  static             run      ruff check . && node --check src/todo/web/app.js
  test               run      pytest -q tests/unit tests/contract
  build              run      uv build
  orphan-endpoints   run      ./gates/check-orphan-endpoints.sh
  acceptance         run      pytest -q tests/isolation
  doc-sync           run      ./gates/check-plan-sync.sh
  spec-approval      run      ./gates/check-spec-approval.sh
  spec-numbers       run      ./gates/check-spec-numbers.sh
```

Wired by feature 001, the walking skeleton, which also installed the pre-commit hook. Every
commit below goes through it.

## Attempt 1 — red at `orphan-endpoints`: the joint nobody wired

The builder wrote the tests (T002–T004) and the store, service and handlers (T005–T007), saw
the unit and contract tests go green, and committed before the web client called the new
routes.

```console
$ git commit -m "feat(tasks): create and list tasks" -m "Spec: 002-task-crud" -m "Task: T002-T007"
gate chain: 9 slots from gates/chain.conf (9 wired, 0 N/A, 0 not wired)
[1/9] format: $ ruff format --check .
33 files already formatted
[1/9] format: ok
[2/9] static: $ ruff check . && node --check src/todo/web/app.js
All checks passed!
[2/9] static: ok
[3/9] test: $ pytest -q tests/unit tests/contract
...........                                                              [100%]
11 passed in 0.19s
[3/9] test: ok
[4/9] build: $ uv build
Building source distribution...
Building wheel from source distribution...
Successfully built dist/team_todo-0.1.0.tar.gz
Successfully built dist/team_todo-0.1.0-py3-none-any.whl
[4/9] build: ok
[5/9] orphan-endpoints: $ ./gates/check-orphan-endpoints.sh
❌ ORPHAN ENDPOINTS - 1 of 2 route(s) have no caller in the client files (server 4 file(s), client 1 file(s)):
   • /tasks   defined at src/todo/api/tasks.py:20, src/todo/api/tasks.py:28
   Who will CALL this? Wire the caller, or add '<route> <reason>' to gates/orphan-allowlist.txt.
[5/9] orphan-endpoints: RED - exit 1
      not run: acceptance doc-sync spec-approval spec-numbers
GATE RED at 'orphan-endpoints' - no commit on red. Fix it, or explicitly revert (GATES.md section 1).
pre-commit: commit REFUSED by gates/hooks/pre-commit - gates/run-chain.sh exited 1.
pre-commit: fix the red slot or explicitly revert; do not --no-verify (GATES.md section 1).
exit=1
```

Every test was green and the feature was unreachable: a member cannot use an API the web
client never calls (Article V, *API-only ≠ done*). The fix is task T008 — the form and the
list in `src/todo/web/`.

## Attempt 2 — red at `acceptance`: the wall

With the client wired, the orphan gate passes and the chain reaches the cross-workspace tests.
Slots 1–4 printed as in attempt 1; from slot 5 on, as printed:

```console
$ git commit -m "feat(tasks): create and list tasks in the web client" -m "Spec: 002-task-crud" -m "Task: T002-T008"
[5/9] orphan-endpoints: $ ./gates/check-orphan-endpoints.sh
✅ orphan endpoints - 2 route(s): 2 called, 0 allow-listed (server 4 file(s), client 1 file(s))
[5/9] orphan-endpoints: ok
[6/9] acceptance: $ pytest -q tests/isolation
F.                                                                       [100%]
=================================== FAILURES ===================================
________________ test_list_never_shows_another_workspaces_tasks ________________

api = <starlette.testclient.TestClient object at 0x7f8097fe2090>

    def test_list_never_shows_another_workspaces_tasks(api):
        api.post("/tasks", json={"title": "acme only"}, headers=auth("alice-token"))
        beta = api.get("/tasks", headers=auth("bob-token")).json()["data"]["tasks"]
>       assert [t["title"] for t in beta] == [], "beta's list leaked acme's task"
E       AssertionError: beta's list leaked acme's task
E       assert ['acme only'] == []
E         
E         Left contains one more item: 'acme only'
E         Use -v to get more diff

tests/isolation/test_cross_workspace.py:9: AssertionError
=========================== short test summary info ============================
FAILED tests/isolation/test_cross_workspace.py::test_list_never_shows_another_workspaces_tasks
1 failed, 1 passed in 0.09s
[6/9] acceptance: RED - exit 1
      not run: doc-sync spec-approval spec-numbers
GATE RED at 'acceptance' - no commit on red. Fix it, or explicitly revert (GATES.md section 1).
pre-commit: commit REFUSED by gates/hooks/pre-commit - gates/run-chain.sh exited 1.
pre-commit: fix the red slot or explicitly revert; do not --no-verify (GATES.md section 1).
exit=1
```

The contract tests had passed because they use one workspace. The list query shipped without
its `workspace_id = ?` predicate — the exact class [Article II](constitution.md) exists for,
and the class the production repository this kit is distilled from paid for.

## The fix — in the store, nowhere else

One change, in the layer that owns SQL (Article III). No filter bolted into the handler "to be
safe": that would hide the missing predicate instead of restoring it.

```diff
 def list_tasks(conn: sqlite3.Connection, workspace_id: str, limit: int = 50):
     rows = conn.execute(
-        "SELECT id, title, done, created_at FROM tasks"
+        "SELECT id, title, done, created_at FROM tasks WHERE workspace_id = ?"
         " ORDER BY created_at DESC LIMIT ?",
-        (limit,),
+        (workspace_id, limit),
     ).fetchall()
```

## Attempt 3 — green

T002–T008 are ticked in the same commit. Slots 1–4 printed as in attempt 1; from slot 5 on:

```console
$ git commit -m "feat(tasks): create and list tasks in the web client" -m "Spec: 002-task-crud" -m "Task: T002-T008"
[5/9] orphan-endpoints: $ ./gates/check-orphan-endpoints.sh
✅ orphan endpoints - 2 route(s): 2 called, 0 allow-listed (server 4 file(s), client 1 file(s))
[5/9] orphan-endpoints: ok
[6/9] acceptance: $ pytest -q tests/isolation
..                                                                       [100%]
2 passed in 0.08s
[6/9] acceptance: ok
[7/9] doc-sync: $ ./gates/check-plan-sync.sh
✅ Specs in sync - 2 specs (approved 1, accepted 1); 22/28 tasks checked
[7/9] doc-sync: ok
[8/9] spec-approval: $ ./gates/check-spec-approval.sh
✅ Spec approvals recorded - 2 specs: 0 draft, 1 approved, 1 accepted/released with acceptance.md, 0 superseded
[8/9] spec-approval: ok
[9/9] spec-numbers: $ ./gates/check-spec-numbers.sh
✅ Spec numbers unique - 2 spec directories (2 sequential, 0 timestamp)
[9/9] spec-numbers: ok
GATE GREEN - 9 ran, 0 N/A
[main dbbee17] feat(tasks): create and list tasks in the web client
 10 files changed, 166 insertions(+), 8 deletions(-)
 create mode 100644 src/todo/api/tasks.py
 create mode 100644 tests/contract/test_tasks_api.py
 create mode 100644 tests/isolation/test_cross_workspace.py
 create mode 100644 tests/unit/test_validation.py
exit=0
```

What the orphan gate matched, after the commit:

```console
$ ./gates/check-orphan-endpoints.sh --list
  /me                                      called at src/todo/web/app.js:14  (defined src/todo/api/me.py:13)
  /tasks                                   called at src/todo/web/app.js:21  (defined src/todo/api/tasks.py:20, src/todo/api/tasks.py:28)
✅ orphan endpoints - 2 route(s): 2 called, 0 allow-listed (server 4 file(s), client 1 file(s))
```

## What to notice

1. **The two reds are the kit's two signature bug classes.** Attempt 1: both ends of nothing
   — routes correct, tests green, no caller ([GATES §4](../../gates/GATES.md)). Attempt 2: a
   wall that a single-workspace test cannot see. Neither is a style problem; both would have
   shipped on a chain of format, lint, tests and build alone.
2. **The red blocked the commit, and the story stayed honest.** Nothing was amended into "it
   always worked"; the commit that landed carries the tests, the fix and the ticked tasks
   together, because a failing test committed alone would itself be a commit on red.
3. **Read the orphan gate's BLIND TO block before trusting its green.** It compares paths, not
   methods: `POST /tasks` and `GET /tasks` are one route to it, and the `--list` output above
   shows both definitions answered by a single call site. That call site happens to be the
   `GET`; the `POST` call exists too (line 41), but the gate would be green without it. The
   contract tests and the quickstart cover what the gate cannot.
4. **The per-commit wall and the per-feature acceptance check the same thing from two sides.**
   `tests/isolation` runs on every commit; `quickstart.md` step 2 is a teammate, signed in as
   a plain member of a second workspace, looking at the real page. User Story 2 (T009–T013) and
   that acceptance run (T014) are still open, so `002-task-crud` stays `approved`.

## Reproduce

The three spec slots read only `specs/`, so they run on this directory from the kit root:

```console
$ ./gates/check-plan-sync.sh --specs examples/todo-api/specs
✅ Specs in sync - 2 specs (approved 1, accepted 1); 22/28 tasks checked
$ ./gates/check-spec-approval.sh examples/todo-api/specs
✅ Spec approvals recorded - 2 specs: 0 draft, 1 approved, 1 accepted/released with acceptance.md, 0 superseded
$ ./gates/check-spec-numbers.sh examples/todo-api/specs
✅ Spec numbers unique - 2 spec directories (2 sequential, 0 timestamp)
```

The other slots need the implementation, which the kit does not ship.
