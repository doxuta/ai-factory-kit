<!-- WHO READS ME: any agent touching schema, migrations, or persistence code — lazy-loaded
     detail behind the Article-II mirror in ../CLAUDE.md.template. I POINT TO: ../HARNESS.md §3
     (loading traps) · ../../constitution/constitution-template.md (Article II, authoritative)
     · ../../gates/GATES.md §6 (repair-path → migration) · workflow.md (review checklist). -->

---
# ⚠️ LOADING TRAP (measured on a production repo — ../HARNESS.md §3): path-scoped rules load
# LAZILY, and foreign scoping syntax fails SILENTLY — an unrecognized key is ignored without
# warning. Verify `paths:` against YOUR platform's docs; most platforms require frontmatter
# as the FIRST lines — when adopting, drop the header comment above this block.
paths:
  - "[GLOB for migrations, EXAMPLE: migrations/**]"
  - "[GLOB for persistence-layer code, EXAMPLE: src/persistence/**]"
---

# Data — storage rules

Authoritative copy: constitution **Article II** (the safety invariant). Always-loaded mirror:
`CLAUDE.md`. This file carries the mechanics.

## Mandatory columns/fields (every transactional table or collection)

| Field | Why |
|---|---|
| `[SCOPING_KEY]` | the isolation boundary [EXAMPLE: `tenant_id` in a multi-tenant schema]. Every read AND write filters on it — no exceptions, privileged accounts included |
| `[CREATED_AT]` / `[UPDATED_AT]` | audit floor; one timestamp convention project-wide ([api-conventions](api-conventions.md)) |
| `[ID_STRATEGY]` | one ID shape everywhere [EXAMPLE: UUIDv7, or DB auto-increment — pick once] |

Let the database enforce what the database can enforce: constraints, uniqueness, foreign keys,
generated columns — before application code re-implements them worse.

## Queries

- **Parameterized only.** Concatenating values into query text is a defect regardless of how
  trusted the caller looks [EXAMPLE: placeholders/prepared statements, never string-format].
- The `[SCOPING_KEY]` filter is part of the query's correctness, not an optimization — a
  reviewer greps for its absence ([workflow.md](workflow.md) checklist).

## Migrations

- Every migration ships **up AND down**, in the same change.
- **Sequential, globally numbered.** One ordering for the whole project — per-module numbering
  merges into ambiguity.
- **Never edit an applied migration.** Reality moved; write the next number. Applied migrations
  keep their historical doc citations too
  ([RETROFIT-PLAYBOOK §5](../../model/RETROFIT-PLAYBOOK.md)).
- A fix that turns out to be needed on every install is a **numbered migration**, not a repair
  script — reconcilers don't replace versioned baselines ([GATES §6](../../gates/GATES.md)).

## Schema changes are spec work

A schema delta belongs in the owning feature's `data-model.md`
([SPEC-FLOW §3](../../model/SPEC-FLOW.md)) before it lands in a migration — code and spec
diverging silently is the drift `converge` exists to catch.
