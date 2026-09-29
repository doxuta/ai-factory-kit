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
  - "[GLOB for transport-layer code, EXAMPLE: src/api/**]"
  - "[GLOB for feature contracts, EXAMPLE: specs/**/contracts/**]"
---
<!-- WHO READS ME: any agent adding or changing an HTTP/RPC API surface — lazy-loaded detail
     for the transport layer. APPLIES TO: products that serve a network API (web service/SaaS,
     HTTP API, a frontend's backend contract, an LLM app behind an API). The adopt.py profiles
     cli, library, data, embedded and iac do not install it (model/ARCHETYPES.md); a library's
     public-API rules and a CLI's flag and exit-code rules belong in the constitution's
     Platform Constraints instead.
     I POINT TO (kit paths; factory/... once adopted): gates/GATES.md §4 (the joint nobody
     wired) · harness/rules/architecture.md (who owns the error mapping) · model/SPEC-FLOW.md
     (contracts/ per feature) · harness/HARNESS.md §3 (loading traps). -->

# API conventions

One casing, one timestamp shape, one error envelope — decided once here, then boring forever.
Per-feature contracts live in that feature's `contracts/`
([SPEC-FLOW](../../model/SPEC-FLOW.md), the plan step); this file holds only the project-wide
constants.

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
| Missing (or hidden by the isolation boundary of constitution Article II) | `[404]` |
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
**"who will CALL this?"** ([GATES §4](../../gates/GATES.md)). The `orphan-endpoints` slot runs
`gates/check-orphan-endpoints.sh` once `gates/orphan-endpoints.conf` names your route pattern
and your server and client files; its header states what it is blind to (methods, paths built
by concatenation), so a green run is never over-trusted.
