---
# ⚠️ LOADING TRAP (measured on a production repo — HARNESS.md §3): Claude Code parses this
# block only when its opening fence is the file's first line, and reads only the `paths` key
# from it. This rule deliberately has NO `paths:` — committing does not require reading a
# matching file, so the commit ritual loads in every session. Never type three dashes inside
# this block: Claude Code 2.1.284 ends the frontmatter at the first three dashes it meets,
# even mid-line. Claude Code strips the block before loading the rule. Other hosts:
# HARNESS.md §7.
---
<!-- WHO READS ME: any agent about to commit — the commit ritual. APPLIES TO: every archetype;
     no adopt.py profile drops it.
     I POINT TO (kit paths; factory/... once adopted): gates/GATES.md (§1 the chain this ritual
     runs · §3 acceptance · §10 commit trailers) · model/SPEC-FLOW.md (where tasks come from) ·
     model/ARCHETYPES.md (which rules a profile installs) · harness/rules/architecture.md,
     data.md, api-conventions.md (what the checklist greps for, where installed). -->

# Workflow — the commit ritual

## Before every commit: the gate chain

```bash
./gates/run-chain.sh          # the slots in gates/chain.conf, in order; stops at the first red
```

Slots: format → static → test → build → orphan-endpoints → acceptance → doc-sync →
spec-approval → spec-numbers. No commit on red. Fix or explicitly revert
([GATES §1](../../gates/GATES.md)). A `TODO` slot is red, not skipped; `git commit --no-verify`
is not a way round it (the careful guard asks before an agent does that, and CI runs the same
chain). Two traps the chain does not catch by itself:

- **Vacuous green** — a test filter matching zero tests exits 0; assert your `-run`/`--grep`
  pattern matches ≥1 real test name.
- **Self-graded acceptance** — the builder never accepts their own feature. The per-feature
  run is someone else's, recorded in `specs/<id>/acceptance.md`; where the product has an
  authorization boundary it runs as a non-privileged account, because privileged accounts
  bypass the walls being tested ([GATES §3](../../gates/GATES.md)).

## Commits

Conventional commits: `type(scope): description`. Small, one concern each. No secrets, no
generated artifacts. A commit that implements, fixes or amends a spec ends with git trailers
([GATES §10](../../gates/GATES.md)) — they are what `metrics.py` counts:

```text
feat(payments): QR checkout confirms before charging

Spec: 012-payment-qr
Task: T014
```

`Bug-class: escaped-joint` goes on the fix for a bug of the joint-nobody-wired class that got
past the gates.

| Type | Use |
|---|---|
| `feat` / `fix` | new behavior / corrected behavior |
| `refactor` | no behavior change |
| `test` / `docs` / `chore` | tests · docs · plumbing |
| `migration` | schema or data change, where the product has one |

## Branch model

`[BRANCH_MODEL — EXAMPLE: main-only, commit straight to main but only on a green chain; or
short-lived branches, squash-merged the same week]`. Whatever the model, the constant holds:
**red gates never land.**

## Review checklist (run against your own diff first)

- [ ] **"Who will CALL this?"** — every new capability reachable through the product's real
      entry point (constitution Article V), or the gap is a named task in `tasks.md`
      ([GATES §4](../../gates/GATES.md))
- [ ] Tests written first; the test filter matches real test names (no vacuous green)
- [ ] Errors handled at every layer, wrapped with origin — no swallowed errors
      ([architecture.md](architecture.md))
- [ ] Constitution Article II (the safety invariant) holds on every touched path — for a
      multi-tenant product, the scoping key on every query ([data.md](data.md), where
      installed); authorization checked before business logic
- [ ] Anything that builds a query, a command line or a prompt from input builds it
      parameterized — zero string-concatenated query or shell text
- [ ] Data change: the discipline in the constitution's Platform Constraints (EXAMPLE: up + down,
      next sequential number)
- [ ] One contract shape on any touched public surface — for an HTTP API one envelope, casing
      and timestamp format ([api-conventions.md](api-conventions.md), where installed); for a
      CLI, flags and exit codes; for a library, the public API diff
- [ ] Spec / plan / tasks updated in the SAME commit — the doc-sync gate is green, not "will fix
      later" ([SPEC-FLOW](../../model/SPEC-FLOW.md) converge)
- [ ] `Spec: <id>` trailer on the commit
