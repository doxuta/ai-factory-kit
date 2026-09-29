---
# ⚠️ LOADING TRAP (measured on a production repo — HARNESS.md §3): path-scoped rules load
# LAZILY — this file is read only when Claude opens a file matching `paths` — and a scoping key
# the host doesn't recognize is ignored SILENTLY. Claude Code parses this block only when its
# opening fence is the file's first line (before v1.4.0 a comment sat above it, so by Claude
# Code's docs every rule loaded in every session), and reads only `paths` from it. An
# unfilled "[GLOB …]" is not a usable pattern (a glob reads `[` as a bracket expression):
# fill both lines, or delete this rule. Never type three dashes inside this block: Claude
# Code 2.1.284 ends the frontmatter at the first three dashes it meets, even mid-line.
# Other hosts: HARNESS.md §7.
paths:
  - "[GLOB for migrations, EXAMPLE: migrations/**]"
  - "[GLOB for persistence-layer code, EXAMPLE: src/persistence/**]"
---
<!-- WHO READS ME: any agent touching schema, migrations, or persistence code — lazy-loaded
     detail behind the Article-II mirror in .claude/CLAUDE.md. APPLIES TO: products that own
     a database or a store of record (web service/SaaS, HTTP API, data pipeline, LLM app with
     state). The adopt.py profiles frontend, cli, library, embedded and iac do not install it
     (model/ARCHETYPES.md); delete it by hand if it still does not fit.
     I POINT TO (kit paths; factory/... once adopted): constitution/constitution-template.md
     (Article II, authoritative) · gates/GATES.md §6 (repair path → migration) ·
     harness/rules/workflow.md (review checklist) · harness/HARNESS.md §3 (loading traps). -->

# Data — storage rules

Authoritative copy: constitution **Article II** (the safety invariant). Always-loaded mirror:
`CLAUDE.md`. This file carries the mechanics.

## Mandatory columns/fields (every transactional table or collection)

| Field | Why |
|---|---|
| `[SCOPING_KEY]` | the isolation boundary [EXAMPLE: `tenant_id` in a multi-tenant schema; `N/A — single-user store` where Article II says so]. Every read AND write filters on it — no exceptions, privileged accounts included |
| `[CREATED_AT]` / `[UPDATED_AT]` | audit floor; one timestamp convention project-wide (the constitution's Platform Constraints) |
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
- Running a migration against production is a release step, not a commit step: it belongs to
  the release lane ([NON-FEATURE-WORK](../../model/NON-FEATURE-WORK.md)), where a human runs or
  approves it.

## Schema changes are spec work

A schema delta belongs in the owning feature's `data-model.md`
([SPEC-FLOW](../../model/SPEC-FLOW.md), the plan step) before it lands in a migration — code and
spec diverging silently is the drift `converge` exists to catch.
