<!-- WHO READS ME: an AI absorbing a legacy doc corpus into specs/ — brownfield projects only.
     I POINT TO: SPEC-FLOW.md (the target shape: frontmatter, statuses, the code-vs-spec rule)
     · ../gates/GATES.md (gates must stay green through every deletion; §3 the acceptance
     record) · ../gates/check-plan-sync.sh (the self-globbing doc-sync gate). Proven on 3
     retro-fit batches (3 legacy docs → 8 specs, ~120 code anchors) on a production repo. -->

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

A FALSE is not yet a verdict on which side is right. Apply the kit's rule
([SPEC-FLOW](SPEC-FLOW.md), "When code and spec disagree") claim by claim: when code and spec
disagree, find out which one moved. If the spec states intended behaviour the code does not
deliver, the code is wrong: record a new task (converge). If the code reflects a deliberate,
owner-approved change the spec never recorded, fix the spec with the correction marked (≠old)
and a dated Clarifications entry. If you cannot tell, ask the owner. In a retro-fit the doc is
the old spec: most FALSEs are the second case — git log shows the later decision — but the
unpaid mandates in §1b are the first, and transcribing the code there would bury a bug.

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

## 1c. Re-measure every number the doc states (scale-creep debts)

Docs record quantified debts ("1,774 unstyled cases", "N TODO sites") at freeze time. During the
retro-fit, **re-measure each number against today's tree**. Observed twice on one production
corpus: a deferred debt had GROWN ~30% between freeze and retro-fit — and nothing was watching.
A grown debt escalates: file it as its own task/chip **in the same wave** (with both numbers, so
the growth rate is visible), and where cheap, add a gate that blocks NEW instances so the debt
can only shrink.

## 2. Write the spec with anchor-stable geometry

Code comments cite `docs/foo.md §4` or `§"#7" MUST-FIX 2`. Keep those tokens meaningful:

- **Preserve section numbers and item numbering** from the old doc for every section the code
  cites (`§2 schema, §3 API, §4 flow, §5 security` stay `§2–§5`).
- **Preserve verbatim phrases that comments quote** (grep the anchors for quoted strings; keep
  those sentences in the new spec, or hand-edit the comment).
- Mark every place the doc was wrong: a `(≠old-doc)` tag + a dated `Clarifications` entry.
  Where the code moved deliberately, the spec states **current code truth**, with the
  correction visible; where the code falls short of what was intended, the spec states the
  intent and the gap is a task (§1).

## 2b. Frontmatter and status for a retro-fitted spec

A retro-fitted spec gets the same frontmatter as any other, at line 1
([SPEC-FLOW](SPEC-FLOW.md)); the gates do not know it is a retro-fit.

- **`status: approved`** once the owner has read it and confirmed it describes the product as
  intended, with `approved_by` and `approved_on`. The work shipped long ago; the spec is new,
  and approving it is what the owner does now.
- **`released`** only after someone who wrote neither the spec nor the code has run its
  runnable Success Criteria against the live code and written `acceptance.md`
  ([GATES §3](../gates/GATES.md)). The code is already with its users, so the status skips
  straight from `approved` to `released`. Where the evidence exists already — a pull request,
  a recorded run — the record says so and is dated when it happened. Until one of the two
  exists, the honest status is `approved`; the `spec-approval` gate is red for `released`
  without a valid record.
- **`plan.md` and `tasks.md` stay optional** (the constitution's RETRO-FIT mode), with one
  catch: in specify-cli 1.0.12, `/speckit-converge`'s instructions stop it when either file is
  missing.
  To converge a retro-fitted spec, give it a short `plan.md` (where the code lives, the stack)
  and a `tasks.md` in the `- [x] T001 …` format holding the retro-fit's own work. An open task
  on a `released` spec is red in `doc-sync`, so converge's new tasks land with their fixes
  (the bug lane, [NON-FEATURE-WORK](NON-FEATURE-WORK.md)) or the spec returns to `approved`
  until they do.

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
6. Run the full gate chain, `./gates/run-chain.sh`. Its `doc-sync` slot is
   [`../gates/check-plan-sync.sh`](../gates/check-plan-sync.sh), and it is **self-globbing**:
   with no argument it checks the whole `specs/` corpus, and with a docs directory argument
   the `*-plan.md` views in it — it never names a single doc. A gate hard-pointing at a
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
