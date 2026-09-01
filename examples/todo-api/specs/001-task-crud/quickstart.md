<!-- WHO READS ME: tester-e2e (or a human) executing acceptance for feature 001 — this is the
     runnable script, not documentation garnish. I POINT TO: spec.md (the criteria each step
     proves) · plan.md (envelope + error codes asserted below) ·
     ../../../../gates/GATES.md §3 (why the account below must be non-privileged) ·
     ../../../../harness/agents/tester-e2e.md (who runs me). -->

# Quickstart 001 — acceptance script

> ⚠️ **Third-person rule** ([GATES §3](../../../../gates/GATES.md)): run every step as a
> plain workspace **member** account. Privileged/operator accounts bypass isolation **by
> construction** — an admin walks through the wall this script exists to test, and every
> step below would pass even if the wall were never built.

## Setup

Two workspaces, one non-privileged member each (fixtures or your seed path):

```sh
API=<base url>                      # [EXAMPLE: http://localhost:8080]
TOKEN_ALICE=<member of workspace acme>   # NOT an operator token
TOKEN_BOB=<member of workspace beta>     # NOT an operator token
```

## Steps — expected result on every line

**1. Alice creates a task** (FR-001, SC-1)

```sh
curl -s -X POST $API/tasks -H "Authorization: Bearer $TOKEN_ALICE" \
  -H 'Content-Type: application/json' -d '{"title":"Ship the report"}'
# expect: 201  {"data":{"id":"<TASK_ID>","title":"Ship the report","done":false,...},"error":null}
# save <TASK_ID> for steps 4–5
```

**2. Alice lists — her task is there** (FR-002, SC-1)

```sh
curl -s $API/tasks -H "Authorization: Bearer $TOKEN_ALICE"
# expect: 200, data.tasks contains <TASK_ID>, newest first
```

**3. Bob lists — Alice's task is NOT there** (FR-002, SC-2)

```sh
curl -s $API/tasks -H "Authorization: Bearer $TOKEN_BOB"
# expect: 200, data.tasks contains ZERO acme rows — grep the body for <TASK_ID>: no match.
# This step is the whole reason the third-person rule exists: run it with an operator
# token and it proves nothing.
```

**4. Bob attacks across the workspace boundary** (FR-004, SC-3)

```sh
curl -s -o /dev/null -w '%{http_code}\n' -X PATCH \
  $API/tasks/<TASK_ID>/complete -H "Authorization: Bearer $TOKEN_BOB"
# expect: 404 — NOT 403. Per spec Clarification 2026-09-01 a 403 would confirm the task
# exists; the body must be byte-identical to a nonexistent id:
curl -s -X PATCH $API/tasks/does-not-exist/complete -H "Authorization: Bearer $TOKEN_BOB"
# expect: same status, same body shape: {"data":null,"error":{"code":"NOT_FOUND",...}}
```

**5. Alice completes — then completes again** (FR-003, SC-4)

```sh
curl -s -X PATCH $API/tasks/<TASK_ID>/complete -H "Authorization: Bearer $TOKEN_ALICE"
# expect: 200, data.done == true
curl -s -X PATCH $API/tasks/<TASK_ID>/complete -H "Authorization: Bearer $TOKEN_ALICE"
# expect: 200 again, state unchanged — idempotent, no error
```

**6. Validation wall** (FR-005)

```sh
curl -s -X POST $API/tasks -H "Authorization: Bearer $TOKEN_ALICE" \
  -H 'Content-Type: application/json' -d '{"title":""}'
# expect: 422 {"data":null,"error":{"code":"VALIDATION",...}} — and step 2 re-run shows
# nothing new was persisted
```

## Pass condition

Every `expect` line held, executed with member tokens only. Paste the transcript into the
commit/PR body — a claim without the transcript is testimony, not evidence
([GATES §2](../../../../gates/GATES.md)). Then flip `M3-T1` in [tasks.md](tasks.md).
