<!-- WHO READS ME: the spec-approval gate (gates/check-spec-approval.sh reads the heading and
     the four key lines) and anyone asking who accepted feature 001, as whom, and when.
     I POINT TO: quickstart.md · spec.md · ../../../../gates/GATES.md §3 (the format). -->

# Acceptance — 001-walking-skeleton
accepted_on: 2026-09-04
accepted_by: Linh (teammate; did not build this feature)
run_as: linh-test, a plain member of workspace beta — no operator access
result: pass

**Illustration.** Team Todo is fictional and was never deployed: no browser run took place,
and the lines below show what a filled record looks like, not output anyone saw. For a record
whose output was really printed, see the budget-cli example's
[acceptance.md](../../../budget-cli/specs/001-monthly-spending-report/acceptance.md).

Ran [quickstart.md](quickstart.md) steps 1–4 against the test server at commit `<sha>`.

1. Signed in with B's token: the page showed "Signed in as linh-test · workspace beta".
2. A token with one character changed: "Not signed in".
3. `curl` to `/me` without a token: the `UNAUTHENTICATED` envelope, status 401.
4. Hà ran `./gates/run-chain.sh` on the same commit: green; the hook refused an unformatted
   `src/todo/app.py`, naming `format`.
