<!-- WHO READS ME: any agent adding or changing an API surface — lazy-loaded detail for the
     transport layer. I POINT TO: ../HARNESS.md §3 (loading traps) · ../../gates/GATES.md §4
     (the joint nobody wired) · architecture.md (who owns the error mapping) ·
     ../../model/SPEC-FLOW.md (contracts/ per feature). -->

---
# ⚠️ LOADING TRAP (measured on a production repo — ../HARNESS.md §3): path-scoped rules load
# LAZILY, and foreign scoping syntax fails SILENTLY — an unrecognized key is ignored without
# warning. Verify `paths:` against YOUR platform's docs; most platforms require frontmatter
# as the FIRST lines — when adopting, drop the header comment above this block.
paths:
  - "[GLOB for transport-layer code, EXAMPLE: src/api/**]"
  - "[GLOB for feature contracts, EXAMPLE: specs/**/contracts/**]"
---

# API conventions

One casing, one timestamp shape, one error envelope — decided once here, then boring forever.
Per-feature contracts live in that feature's `contracts/`
([SPEC-FLOW §3](../../model/SPEC-FLOW.md)); this file holds only the project-wide constants.

## Casing

| Surface | Convention |
|---|---|
| Payload keys | `[CASING — EXAMPLE: camelCase JSON]` |
| Storage/schema | `[CASING — EXAMPLE: snake_case]` — the boundary translates, never leaks |
| URL paths | `[SHAPE — EXAMPLE: /api/v1/orders/{id}: kebab-case, plural nouns]` |

## Timestamps

All timestamps on the wire: `[FORMAT — EXAMPLE: ISO 8601 UTC, 2026-01-31T09:00:00Z]`, inbound
and outbound. No local time, no second format "just for this endpoint".

## Status codes (pick one meaning per situation, record it, enforce it)

| Situation | Code |
|---|---|
| Read OK · created · deleted-no-body | `[200 · 201 · 204]` |
| Malformed request · valid-but-unprocessable | `[400 · 422 — decide the split ONCE]` |
| Not authenticated · not authorized | `[401 · 403 — different walls, never conflated]` |
| Missing (or hidden by `[SCOPING_KEY]`) | `[404]` |
| Rate limited · server fault | `[429 · 500]` |

## Error envelope (one shape, everywhere)

```json
{ "code": "[MACHINE_READABLE_CODE]", "message": "[one human sentence]", "details": "[OPTIONAL]" }
```

- `code` values come from ONE registry file: `[PATH/TO/error-code-registry]` — kept out of
  always-loaded context deliberately; look it up when needed.
- Only the transport layer maps errors to this envelope
  ([architecture.md](architecture.md)); business errors carry meaning, not protocol codes.

## The reachability rule, per endpoint

A new route is unfinished until a real caller exists or the gap is a named task — ask
**"who will CALL this?"** ([GATES §4](../../gates/GATES.md)). The orphan-endpoint gate
enforces this mechanically; write what the gate is *blind* to (method-blind?
response-key-blind?) in the gate's own docstring, so a green run is never over-trusted.
