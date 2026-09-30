<!-- WHO READS ME: the teammate who accepts the walking skeleton (or tester-e2e in a fresh
     context). I POINT TO: spec.md (what each step proves) · acceptance.md (where the result is
     recorded) · ../../../../gates/GATES.md §3 (why the account below is a plain member). -->

# Quickstart 001 — acceptance script

> **Who runs this**: a teammate who did not build the feature, signed in as a **plain member
> of a second workspace** — never with an operator's access (constitution Article VI).

## Setup (the operator, on the test server)

```sh
todo-admin add-member --db /srv/todo/todo.db --workspace acme --name alice-test   # prints A's token
todo-admin add-member --db /srv/todo/todo.db --workspace beta --name linh-test    # prints B's token
```

The acceptor receives only B's token.

## Steps

1. Open the web client, paste B's token, sign in.
   Expect: "Signed in as linh-test · workspace beta". (FR-001, FR-002, SC-001)
2. Sign in again with a wrong token (change one character).
   Expect: "Not signed in". (FR-003)
3. From a terminal, call the route the page uses, without a token:
   `curl -s -w ' %{http_code}\n' https://<test-server>/me`
   Expect: `{"data":null,"error":{"code":"UNAUTHENTICATED","message":"sign in first"}} 401`.
   (FR-003)
4. Ask the team lead to run `./gates/run-chain.sh` on the accepted commit and to show the hook
   refusing an unformatted file. Expect: green; then a refusal naming `format`. (US2, SC-002)

## Pass condition

Every expectation held, signed in only as B. Record the run in `acceptance.md` and set
`status: accepted` in the same commit.
