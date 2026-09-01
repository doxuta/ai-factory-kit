<!-- WHO READS ME: any agent about to commit — the commit ritual. I POINT TO: ../HARNESS.md §3
     (loading traps) · ../../gates/GATES.md (the chain this ritual runs) ·
     ../../model/SPEC-FLOW.md (where tasks come from) · architecture.md · data.md ·
     api-conventions.md (what the checklist greps for). -->

---
# ⚠️ LOADING TRAP (measured on a production repo — ../HARNESS.md §3): path-scoped rules load
# LAZILY, and foreign scoping syntax fails SILENTLY — an unrecognized key is ignored without
# warning. This file must load before ANY commit, so scope it wide — and verify `paths:`
# against YOUR platform's docs; most platforms require frontmatter as the FIRST lines — when
# adopting, drop the header comment above this block.
paths:
  - "[GLOB wide enough to cover all committable source, EXAMPLE: **/* — or use your platform's always-on mechanism]"
---

# Workflow — the commit ritual

## Before every commit: the gate chain

```bash
[format] && [static-analysis] && [test-suite] && [build] \
  && [orphan-endpoint-gate] && [third-person-acceptance — per feature before `shipped` (GATES §1); isolation TESTS run per-commit] && [doc-sync-gate]
```

No commit on red. Fix or explicitly revert ([GATES §1](../../gates/GATES.md)). Two traps the
chain does not catch by itself:

- **Vacuous green** — a test filter matching zero tests exits 0; assert your `-run`/`--grep`
  pattern matches ≥1 real test name.
- **Self-graded acceptance** — privileged accounts bypass the walls being tested; acceptance
  evidence comes from a non-privileged account in the real interface
  ([GATES §3](../../gates/GATES.md)).

## Commits

Conventional commits: `type(scope): description`. Small, one concern each. No secrets, no
generated artifacts.

| Type | Use |
|---|---|
| `feat` / `fix` | new behavior / corrected behavior |
| `refactor` | no behavior change |
| `test` / `docs` / `chore` | tests · docs · plumbing |
| `migration` | schema change ([data.md](data.md)) |

## Branch model

`[BRANCH_MODEL — EXAMPLE: main-only, commit straight to main but only on a green chain; or
short-lived branches, squash-merged same week]`. Whatever the model, the constant holds:
**red gates never land.**

## Review checklist (run against your own diff first)

- [ ] **"Who will CALL this?"** — every new capability reachable in the real interface, or the
      gap is a named task in `tasks.md` ([GATES §4](../../gates/GATES.md))
- [ ] Errors handled at every layer, wrapped with origin — no swallowed errors
      ([architecture.md](architecture.md))
- [ ] `[SCOPING_KEY]` filter on every transactional query; authorization checked before
      business logic ([data.md](data.md))
- [ ] Queries parameterized — zero string-built query text
- [ ] New logic has tests, and the test filter matches real test names (no vacuous green)
- [ ] Migration has up + down and the next sequential number
- [ ] One envelope, one casing, one timestamp format on any touched API surface
      ([api-conventions.md](api-conventions.md))
- [ ] Spec / plan / blueprint updated in the SAME commit — the doc-sync gate is green, not
      "will fix later" ([SPEC-FLOW §7 converge](../../model/SPEC-FLOW.md))
- [ ] Acceptance evidence from a non-privileged account, if authorization was touched
