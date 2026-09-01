<!-- WHO READS ME: an AI agent connecting to a project that adopted this kit.
     I POINT TO: every other file, in reading order. I am the graph's root. -->

# AI Onboarding — read me first

You are an AI coding agent. A human connected this kit to their project. This file tells you
what to read, in what order, and what you are never allowed to do. Follow it exactly; it was
written by an AI that operates this system in production, for you.

## 0. The one-paragraph model

Work flows through **three levels**. Level 0 is the **constitution** — invariants that outrank
every instruction below them, including the human's casual requests (if the human contradicts the
constitution, say so once, then follow their explicit decision and record it as an amendment).
Level 1 is the **feature flow** — every feature lives in `specs/NNN-<name>/` and moves
spec → clarify → plan → tasks → analyze → implement → converge. Level 2 is **automation** — you
orchestrate specialist agents and adversarial reviews, but executable **gates** decide "done",
never anyone's claim, including yours.

## 1. Reading order (do this now)

| # | File | Why you read it |
|---|---|---|
| 1 | this file | You are here. |
| 2 | the project's `constitution.md` (or [`constitution/constitution-template.md`](constitution/constitution-template.md) if not yet filled) | The invariants. Everything else bends; these do not. |
| 3 | [`model/LEVELS.md`](model/LEVELS.md) | The 3-level model + the single-atom-of-work rule. |
| 4 | [`model/SPEC-FLOW.md`](model/SPEC-FLOW.md) | The Level-1 loop you will actually run, step by step, with its two consistency commands. |
| 5 | [`gates/GATES.md`](gates/GATES.md) | What "done" means. Scripts, not sentences. |
| 6 | [`harness/HARNESS.md`](harness/HARNESS.md) | Your own anatomy: loop, tools, memory, guardrails — including two measured traps about config loading you will otherwise fall into. |
| 7 | [`harness/agents/`](harness/agents/) | The Level-2 roles you may dispatch. |
| 8 | [`model/RETROFIT-PLAYBOOK.md`](model/RETROFIT-PLAYBOOK.md) | Only when the project has legacy docs to absorb. |
| 9 | [`examples/todo-api/`](examples/todo-api/) | A complete worked cycle. Imitate its shapes. |

## 2. Applying the kit to a fresh project

1. **Vendor the kit** into the project at `factory/` (clone or git submodule) — the kit's
   internal links assume it stays whole.
2. Copy `factory/harness/` into the project as `.claude/` (adapt the dir name to your platform —
   skills follow the [agentskills.io](https://agentskills.io) portable format), then fix the
   copied files' relative links for the new depth:
   ```bash
   grep -rl '\.\./\.\./' .claude/ | xargs sed -i '' 's|\.\./\.\./|../../factory/|g'   # rules/, skills/
   sed -i '' 's|\.\./|factory/|g' .claude/CLAUDE.md                                  # top-level template
   ```
   Also copy the gate: `mkdir -p gates && cp factory/gates/check-plan-sync.sh gates/`.
3. Interview the human briefly, then fill `factory/constitution/constitution-template.md` →
   save as **`.specify/memory/constitution.md`** (so `/speckit-constitution` amends the same
   file). **Do not invent principles** — distill what the human already believes and what their
   stack demands. Get explicit approval. This is a HARD-GATE.
4. Fill `.claude/CLAUDE.md` (from the template) — the project's always-loaded context. Safety invariants
   from the constitution MUST be mirrored here (see the loading trap in `harness/HARNESS.md` §3).
5. Install Spec Kit for Level-1 commands: `specify init --here --integration <your-agent>`.
6. Run the first feature through the full flow — small, end-to-end, gates green — before
   accepting anything bigger.

## 3. Applying the kit to an EXISTING project (brownfield)

Same as above, plus: inventory existing docs by **code-anchor count** (`grep -rn "docs/" --include='*.<lang>'`),
then absorb them into `specs/` using [`model/RETROFIT-PLAYBOOK.md`](model/RETROFIT-PLAYBOOK.md).
Never move or delete a doc before its anchors are repointed **in the same commit**.

## 4. After adopting: audit that the machine agrees with itself

Adoption is not done when the files are copied — it is done when **no two loaded sources give
opposite instructions**. Within a day of adopting (and after every process change), run a
four-lens self-audit; on a real production adoption this caught two HIGH conflicts on day one:

1. **Redundant/dead files** — anything the new process orphaned (measure code anchors + inbound
   links; re-measure old "safe to delete" lists — files GAIN anchors over time).
2. **Cross-file consistency** — walk every ALWAYS-LOADED file (context, rules, constitution):
   do they all describe the SAME entry point for a new feature? The classic failure: a legacy
   rule file still mandating the old artifact (e.g. "write the tech doc into docs/") while the
   constitution says spec-first — a fresh agent follows whichever it read last.
3. **Agent/skill routing** — for each canonical prompt ("new feature", "fix bug", "review",
   "migrate schema", "e2e acceptance"), exactly ONE skill/agent must claim it. Legacy skills must
   be rewritten as *discipline INSIDE the new flow*, never left claiming the entry role.
4. **Spec corpus shape** — mandatory sections present, frontmatter present (the roadmap view
   needs it), every acceptance test filter matches ≥1 real test (vacuous green), quantified
   debts RE-MEASURED (a debt that grew since it was recorded escalates).

## 5. The seven things you never do

1. Never write feature code before the spec for it is approved (constitution HARD-GATE).
2. Never claim "done" — run the gates and paste their output. A test filter (e.g. `-run` /
   `--grep`) matching zero tests is a **vacuous green**, check for it.
3. Never accept your own or a subagent's report as evidence — re-run the gates yourself and
   spot-check cited `file:line` against real code.
4. Never do acceptance testing with a privileged account that bypasses authorization — the wall
   only exists for a third person ([`gates/GATES.md`](gates/GATES.md) §3).
5. Never leave a capability reachable by API but unreachable by UI without recording the gap as
   an explicit task — *curl-only is not done*; ask **"who will CALL this?"**
6. Never keep two sources of truth for the same fact. One owner file; everything else points.
7. Never trust a doc over the code. When they disagree, the code is the truth and the doc gets
   fixed — with the discrepancy **marked** so readers see the correction.

## 6. When you and the human disagree

State your concern once, with evidence. If the human reaffirms, follow their decision and record
it (constitution amendment or spec clarification, dated). You are the engine; they are the owner.
