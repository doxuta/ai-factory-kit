---
name: ponytail
description: >
  Lazy-senior-dev code style — the simplest thing that actually works. Seven-rung ladder from
  YAGNI down to minimal new code; deliberate shortcuts carry a marked ceiling and upgrade
  path; never collapses constitution-mandated abstractions. Use on any coding task and any
  library choice. Adapted from DietrichGebert/ponytail (MIT).
---
<!-- WHO READS ME: an agent about to write, refactor, or review code. I POINT TO:
     ../../../constitution/constitution-template.md (Article VII — my boundary) ·
     ../caveman/SKILL.md (my pair — I compress code, it compresses talk) ·
     ../plan-and-tdd/SKILL.md (the loop I run inside). -->

# Ponytail — the best code is code never written

Lazy means efficient, not careless. The ladder runs AFTER understanding the problem: read the
task and the code it touches, trace the real flow end-to-end, then climb. The smallest diff in
the wrong place is not lazy — it is a second bug.

## The ladder — stop at the first rung that holds

1. **Does this need to exist at all?** Speculative need = skip it, say so in one line. (YAGNI)
2. **Already in this codebase?** Reuse the helper/pattern three files away — look before
   writing; re-implementing the neighbor is the most common slop.
3. **Stdlib does it?** Use it.
4. **Native platform covers it?** [EXAMPLE: `<input type="date">` over a date-picker library,
   CSS over JS, a database constraint over app-level validation.]
5. **Already-installed dependency solves it?** Use it. Never add a dep for what a few lines do.
6. **One line?** One line.
7. **Only then**: the minimum new code that works.

Two rungs both hold → take the higher one and move on. Two stdlib options the same size →
take the edge-case-correct one: lazy means less code, not the flimsier algorithm.

## Rules

- No unrequested abstractions: no interface with one implementation, no factory for one
  product, no config knob for a value that never changes.
- Deletion over addition. Boring over clever (clever = what someone decodes at 3am). Fewest
  files; shortest working diff wins.
- **Bug fix = root cause.** Grep every caller of the function you touch; one guard in the
  shared function beats a guard in each caller — and patching only the reported path leaves
  the sibling callers broken.
- **Mark deliberate shortcuts** with the project's marker comment — `shortcut:` per the
  [constitution template](../../../constitution/constitution-template.md); upstream uses
  `ponytail:`; pick ONE per project so it stays greppable — carrying the ceiling and the
  upgrade path. [EXAMPLE: `// shortcut: O(n) scan — add an index past ~10k rows`.]

## BOUNDARY — the constitution outranks laziness

Some abstractions are mandated, not optional: the layer separation, the data-isolation
filters, the metadata indirection, the migration discipline — whatever the project's
constitution Articles I–III name. **Those are not over-engineering, and ponytail never
collapses them for brevity.** Measured on a production repo: the tempting collapses (inline
the query "to skip a layer", hardcode the dynamic field "to save an indirection", drop the
isolation filter "for a cleaner query") are each a constitution violation, not a
simplification. Ponytail operates INSIDE a layer — don't bloat a service, don't add a dep the
installed one covers, don't rewrite the existing helper — never ACROSS the boundaries the
constitution draws. When laziness and the constitution conflict, **the constitution wins**:
[constitution-template Article VII](../../../constitution/constitution-template.md) encodes
exactly this rule.

## Never lazy about

Understanding the problem · input validation at trust boundaries · error handling that
prevents data loss · security and isolation · accessibility · anything explicitly requested ·
one runnable check for any non-trivial logic (TDD stays — ponytail kills surplus fixtures,
not tests).

Off: "stop ponytail" / "normal mode".
