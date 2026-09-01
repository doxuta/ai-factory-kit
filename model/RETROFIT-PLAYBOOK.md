<!-- WHO READS ME: an AI absorbing a legacy doc corpus into specs/ — brownfield projects only.
     I POINT TO: SPEC-FLOW.md (the target shape) · ../gates/GATES.md (gates must stay green
     through every deletion). Proven on 3 retro-fit batches (3 legacy docs → 8 specs, ~120 code anchors) on a production repo. -->

# The Retro-fit Playbook — absorbing legacy docs into specs/

Brownfield projects have a doc corpus the code grew up with: design briefs, build logs, API
notes. You cannot just rewrite them into specs — **docs lie about evolved code**, and code
comments **anchor** into doc paths and section numbers. This is the proven procedure.

## 0. Inventory by anchor count (decide order by physics, not vibes)

```bash
# who in the CODE points at which doc? (adapt --include to your languages)
grep -rhoE 'docs/[A-Za-z0-9_.-]+\.md' --include='*.go' --include='*.ts' -r src/ \
  | sort | uniq -c | sort -rn
```

- Docs **with** code anchors: retro-fit first — deleting them un-absorbed breaks real traceability.
- Docs with **zero** anchors and zero inbound links: safe to absorb any time.
- Also find **runtime** dependents (scripts that *parse* a doc, UI strings naming it) — those
  break louder than comments.

## 1. Verify, don't transcribe

The doc froze on its ship date; the code kept moving. For every normative claim, fan out
independent verification agents (one per subsystem) that must return
**TRUE / FALSE / PARTIAL with `file:line` evidence** from the *executing code* — comments don't
count. Add a **both-direction critic**: (a) what's in the doc that no claim covered, (b) what's
in the code that the doc never knew (post-freeze features, changed gates, renamed builders).

> Real yields from production runs of this step: an inverted rule (a "forbidden" combination
> had become legal), a closed gap still documented as open, an auth surface whose gate tier
> changed after the doc froze, and a UI string pointing at the doc scheduled for deletion.
> **A retro-fit that finds no drift probably didn't look.**

## 1b. Two more places docs lie (both bit on production retro-fits)

- **The doc's own status table vs git log.** Docs freeze MID-DELIVERY: one shipped doc marked
  three phases "remaining" that git showed landing the same evening it froze. Always diff the
  doc's status claims against `git log --oneline --since=<doc date>` before writing the spec.
- **Unpaid mandates inside the doc.** If the source doc mandates something it never received
  ("adversarial review REQUIRED", "integration test required") — **pay that debt during the
  retro-fit**, don't just copy the mandate forward. On a real run the owed review, paid two
  months late, found a HIGH: a validation probe wired into one branch of a function but not its
  twin. The joint-nobody-wired class hides exactly where mandates went unpaid.

## 2. Write the spec with anchor-stable geometry

Code comments cite `docs/foo.md §4` or `§"#7" MUST-FIX 2`. Keep those tokens meaningful:

- **Preserve section numbers and item numbering** from the old doc for every section the code
  cites (`§2 schema, §3 API, §4 flow, §5 security` stay `§2–§5`).
- **Preserve verbatim phrases that comments quote** (grep the anchors for quoted strings; keep
  those sentences in the new spec, or hand-edit the comment).
- Mark every place the doc was wrong: a `(≠old-doc)` tag + a dated `Clarifications` entry.
  The spec states **current code truth**, with the correction visible.

## 3. Adversarial review before the swap

Independent lenses, each prompted to *refute*: **accuracy-vs-code** (spot-check ≥12 citations;
verify every test command actually matches real test names — zero-match filters exit green),
**fidelity-vs-source** (what normative content got lost?), **anchor-safety** (walk every citing
comment; would it mislead after the swap?). Fix or explicitly refute every finding.

## 4. The swap — one commit, atomically

In the SAME commit:

1. Rewrite every code anchor `docs/old.md …` → `specs/NNN-*/spec.md …` (per-token when one doc
   splits into several specs; longest-match-first; assert **zero residuals** by grep).
2. Retarget live markdown links; update index/README rows.
3. Fix runtime dependents (parsing scripts → static or repointed; UI strings).
4. Fix code comments that *contradict their own code* — you just proved they exist; leaving
   them is knowingly shipping lies.
5. `git rm` the old doc.
6. Run the full gate chain. Then re-run your doc-consistency gate — it must be **self-globbing**
   ([`../gates/check-plan-sync.sh`](../gates/check-plan-sync.sh)): a gate hard-pointing at a
   deletable doc turns every future deletion into a red-gate hostage.

## 5. What deliberately stays behind

- **Applied DB migrations** keep their historical doc citations — never edit applied migrations;
  `git log -- path/to/old-doc.md` resolves them.
- **Historical snapshots** (archived audits, old planning logs) keep prose mentions — they
  describe the past truthfully. Mark the corpus "historical, not guidance" once, at its README.

## The deletion condition (the whole playbook in one sentence)

> A doc may be deleted **only when** its normative content lives in a spec *verified against
> current code*, every live anchor was repointed in the same commit, and the gates are green —
> deletion is the *last* step of absorption, never a cleanup shortcut.
