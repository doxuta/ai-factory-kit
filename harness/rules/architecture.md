---
# ⚠️ LOADING TRAP (measured on a production repo — HARNESS.md §3): path-scoped rules load
# LAZILY — this file is read only when Claude opens a file matching `paths` — and a scoping key
# the host doesn't recognize is ignored SILENTLY (one repo shipped 84KB of "scoped" rules
# every session for months because the frontmatter used another tool's syntax). Claude Code
# parses this block only when its opening fence is the file's first line (before v1.4.0 a
# comment sat above it, so by Claude Code's docs every rule loaded in every session), and
# reads only `paths` from it. An unfilled "[GLOB …]" is not a usable pattern (a glob reads
# `[` as a bracket expression): fill it, or delete this rule. Never type three dashes inside
# this block: Claude Code 2.1.284 ends the frontmatter at the first three dashes it meets,
# even mid-line. Other hosts: HARNESS.md §7.
paths:
  - "[GLOB matching your source layers, EXAMPLE: src/**/*.EXT]"
---
<!-- WHO READS ME: any agent editing source in the layers scoped above — lazy-loaded detail
     behind the Article-III mirror in .claude/CLAUDE.md. APPLIES TO: every archetype; no
     adopt.py profile drops it — fill the layer names for the product (model/ARCHETYPES.md).
     I POINT TO (kit paths; factory/... once adopted): constitution/constitution-template.md
     (Article III, authoritative) · gates/GATES.md §5 (adversarial review) ·
     harness/rules/api-conventions.md (the HTTP error envelope, where installed) ·
     harness/HARNESS.md §3 (loading traps). -->

# Architecture — the layering contract

Authoritative copy: constitution **Article III**. Always-loaded mirror: `CLAUDE.md`. This file
is the lazy-loaded detail — where it contradicts either of those, this file is the bug.

## The chain

```
[ENTRY LAYER]  →  [CORE / BUSINESS LAYER]  →  [ADAPTERS: persistence, I/O]  →  [DOMAIN MODEL]
 parses/validates      decides                    reads/writes                 plain data + rules
```

[EXAMPLE: web service — handler → service → repository → entity in Go, or controller →
use-case → gateway → entity in TypeScript; CLI — argument parsing → command → pure core → file
and terminal adapters; library — public API → internal modules; data pipeline — extract →
validate → transform → load.]

Dependencies point one way: a layer calls the next layer down — never upward, never skipping.

## Forbidden couplings (state them so a reviewer can grep)

| Never | Because |
|---|---|
| [persistence or I/O concern, EXAMPLE: SQL, file writes] in the [ENTRY LAYER] | untestable, unauditable |
| [entry concern, EXAMPLE: HTTP codes, argv, terminal output] in the [CORE] | business logic married to one interface |
| [CORE] importing [ENTRY LAYER] types | inverted dependency |
| [DOMAIN MODEL] importing anything above it | the domain must stand alone |

## Error discipline

- Every layer wraps errors with their origin before passing them up:
  `[package.method]: <underlying>` [EXAMPLE: Go — `fmt.Errorf("svc.CreateOrder: %w", err)`].
- No swallowed errors — `[_ = err or your language's equivalent]` is a defect, not a style.
- Only the entry layer turns errors into what the user sees: for an HTTP API the envelope in
  [`api-conventions.md`](api-conventions.md) where the profile installed it; for a CLI the
  exit code and one stderr line; for a library the documented exception or error type.

## The exception that is not one

Deliberate-simplicity pressure (constitution Article VII) never collapses these layers: the
abstractions Article III mandates are not over-engineering. Simplify **within** a layer, never
across a boundary. Reviews check this adversarially ([GATES §5](../../gates/GATES.md)).
