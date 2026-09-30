<!-- WHO READS ME: the teammate (or tester-e2e in a fresh context) who accepts feature 002 —
     the runnable acceptance script, not documentation garnish. I POINT TO: spec.md (the
     criteria each step proves) · contracts/tasks-api.md (the envelope and error codes) ·
     ../../../../gates/GATES.md §3 (why the account below is a plain member). -->

# Quickstart 002 — acceptance script

> ⚠️ **Least-privilege rule** ([GATES §3](../../../../gates/GATES.md)): run every step as a
> plain workspace **member**. An operator's access walks through the isolation wall this
> script exists to test, so every step would pass even if the wall were never built.

## Setup (the operator, on the test server)

```sh
TOKEN_A=$(todo-admin add-member --db /srv/todo/todo.db --workspace acme --name alice-test)
TOKEN_B=$(todo-admin add-member --db /srv/todo/todo.db --workspace beta --name linh-test)
API=https://<test-server>
```

The acceptor signs in to the web client with `TOKEN_B` in one browser profile and
`TOKEN_A` in another. The `curl` steps probe the wall the way someone bypassing the web client
would.

## Steps — the expected result is on every line

**1. A creates a task in the web client** (FR-001, FR-006, SC-001) — as A, add "Ship the
report". Expect: it appears at the top of A's list.

**2. B's list does not show it** (FR-002, SC-002) — as B, reload. Expect: "Ship the report" is
not there. This is the step the least-privilege rule exists for.

**3. The same wall, without the web client** (FR-002)

```sh
curl -s $API/tasks -H "Authorization: Bearer $TOKEN_B"
# expect: 200 and no task titled "Ship the report" in data.tasks
```

**4. B addresses A's task directly** (FR-004, SC-003) — take the task id from A's list:

```sh
curl -s -w ' %{http_code}\n' -X PATCH $API/tasks/<TASK_ID>/complete -H "Authorization: Bearer $TOKEN_B"
curl -s -w ' %{http_code}\n' -X PATCH $API/tasks/does-not-exist/complete -H "Authorization: Bearer $TOKEN_B"
# expect: both print {"data":null,"error":{"code":"NOT_FOUND",...}} 404 — the same body,
# the same status. A 403 would confirm the task exists (Clarifications 2026-09-05).
```

**5. A completes the task twice in the web client** (FR-003, SC-004) — expect: it shows as
done after the first click, and the second click changes nothing and shows no error.

**6. The validation wall** (FR-005) — as A, submit an empty title. Expect: the validation
message, and step 1's list unchanged.

## Pass condition

Every expectation held, signed in only as the two plain members. Record the run in
`acceptance.md` — who ran it, as whom, when, `result: pass`, with the `curl` output — and set
the spec's `status: accepted` in the same commit. A claim without the output is testimony, not
evidence ([GATES §2](../../../../gates/GATES.md)).
