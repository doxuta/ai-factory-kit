<!-- WHO READS ME: any agent editing source in the layers scoped below — lazy-loaded detail
     behind the Article-III mirror in ../CLAUDE.md.template. I POINT TO: ../HARNESS.md §3
     (loading traps) · ../../constitution/constitution-template.md (Article III, authoritative)
     · ../../gates/GATES.md §5 (adversarial review) · api-conventions.md (error envelope). -->

---
# ⚠️ LOADING TRAP (measured on a production repo — ../HARNESS.md §3): path-scoped rules load
# LAZILY — this file is read only when a matching file is touched — and a scoping key your
# platform doesn't recognize is ignored SILENTLY (one repo shipped 84KB of "scoped" rules
# every session for months because the frontmatter used another tool's syntax). Verify
# `paths:` against YOUR platform's docs. Most platforms require frontmatter as the FIRST
# lines — when adopting, drop the header comment above this block.
paths:
  - "[GLOB matching your source layers, EXAMPLE: src/**/*.EXT]"
---

# Architecture — the layering contract

Authoritative copy: constitution **Article III**. Always-loaded mirror: `CLAUDE.md`. This file
is the lazy-loaded detail — where it contradicts either of those, this file is the bug.

## The chain

```
[TRANSPORT LAYER]  →  [BUSINESS LAYER]  →  [PERSISTENCE LAYER]  →  [DOMAIN MODEL]
 parses/validates      decides              reads/writes            plain data + rules
```

[EXAMPLE: handler → service → repository → entity in a Go service; controller → use-case →
gateway → entity in a TypeScript backend.]

Dependencies point one way: a layer calls the next layer down — never upward, never skipping.

## Forbidden couplings (state them so a reviewer can grep)

| Never | Because |
|---|---|
| [persistence concern, EXAMPLE: SQL] in the [TRANSPORT LAYER] | untestable, unauditable |
| [transport concern, EXAMPLE: HTTP codes/request types] in the [BUSINESS LAYER] | business logic married to a protocol |
| [BUSINESS LAYER] importing [TRANSPORT LAYER] types | inverted dependency |
| [DOMAIN MODEL] importing anything above it | the domain must stand alone |

## Error discipline

- Every layer wraps errors with their origin before passing them up:
  `[package.method]: <underlying>` [EXAMPLE: Go — `fmt.Errorf("svc.CreateOrder: %w", err)`].
- No swallowed errors — `[_ = err or your language's equivalent]` is a defect, not a style.
- Only the transport layer turns errors into protocol responses; the envelope lives in
  [`api-conventions.md`](api-conventions.md).

## The exception that is not one

Deliberate-simplicity pressure (constitution Article VII) never collapses these layers: the
abstractions Article III mandates are not over-engineering. Simplify **within** a layer, never
across a boundary. Reviews check this adversarially ([GATES §5](../../gates/GATES.md)).
