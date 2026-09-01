<!-- WHO READS ME: an AI (or human) learning the kit's structure — 3rd in the reading order.
     I POINT TO: constitution/ (Level 0) · SPEC-FLOW.md (Level 1) · ../harness/agents/ (Level 2)
     · ../gates/GATES.md (the floor under all three). -->

# The Three-Level Model

## Level 0 — Constitution (per project; changes rarely, by amendment)

The files that outrank everything, written once and amended deliberately:

| File | Holds | Anti-pattern it kills |
|---|---|---|
| `constitution.md` | 5–7 **invariants** + non-goals + governance ([template](../constitution/constitution-template.md)) | Rules scattered across 7 config files, some lazily loaded |
| Vision (a `vision.md`, or the constitution's preamble for small projects) | What is being built, for whom, the business model | AI optimizing for the wrong customer |
| Platform constraints (**one owner**: the constitution's `Platform Constraints` section; split out a `platform.md` only when it outgrows that) | The stack — the ONLY per-project content in a portable kit | Two homes for the same fact |
| [`../gates/GATES.md`](../gates/GATES.md) | Definition-of-done as **runnable scripts** | "When-task-done" prose an agent can talk its way past |

Two hard rules learned by measurement:

- **A "business rules" catch-all file is a trap.** Global *invariants* go in the constitution;
  per-domain rules go in that feature's `spec.md`. A single bucket file bloats, then rots.
- **A memory file nobody updates is worse than no memory.** Every Level-0 file needs an owner
  and an update trigger (see [`../sync/DAILY-SYNC.md`](../sync/DAILY-SYNC.md)), or it becomes a
  confident liar.

## Level 1 — Feature flow (per feature; the daily loop)

**`specs/NNN-<feature>/` is the single atom of work.** Full walkthrough:
[`SPEC-FLOW.md`](SPEC-FLOW.md).

If your project already runs on epics / milestones / slices / tickets, map them — don't stack a
seventh vocabulary on top:

| Legacy unit | Becomes |
|---|---|
| Epic / theme | A **label** in spec frontmatter + a roadmap *view* |
| Milestone | A prioritized **user story** (P1/P2/P3) inside `spec.md` |
| Slice / ticket | A **task** in `tasks.md` |
| Wave / sprint | Dies. Scheduling is not a unit of work. |
| Backlog item | A pointer to a spec's task — the backlog file holds **no content** |

## Level 2 — Automation (per organization; agents + verification)

Four roles, each a file in [`../harness/agents/`](../harness/agents/):

| Role | Duty | Feeds |
|---|---|---|
| [`requirement-researcher`](../harness/agents/requirement-researcher.md) | Raw request + prior specs + repo knowledge → an 80%-clean draft spec | `/speckit-specify` |
| [`task-orchestra`](../harness/agents/task-orchestra.md) | Decompose, dispatch file-disjoint workers, own the merge | `implement` |
| [`tester-e2e`](../harness/agents/tester-e2e.md) | Drive the feature's `quickstart.md` in a real environment, as a **non-privileged** user | acceptance |
| [`tech-lead-review`](../harness/agents/tech-lead-review.md) | Adversarial multi-lens review; findings must be refuted-or-fixed, never shelved | the commit gate |

Level-2 law: **verification is adversarial and independent.** The agent that built a thing never
graduates it; reviewers are prompted to *refute*, not to appreciate. And the orchestrator re-runs
gates itself — a subagent's numbers are testimony, not evidence.

## Level 3 — Multi-platform execution (deliberately deferred)

Running the same model across additional executors (other agent CLIs, CI robots, k8s runners)
multiplies failure modes before it multiplies value for a small team. The kit stays portable
through the **skill format** ([agentskills.io](https://agentskills.io)) and stack-neutral
templates instead. Revisit when more than one executor genuinely carries daily work.

## The measure that matters

Not "% of code written by AI" — on a mature setup that hits ~100% and stops being informative.
Track instead:

1. **First-pass land rate** — slices that merge without a correction commit.
2. **Escaped joints** — bugs of the class *"both ends correct, connection missing"* that got past
   the gates (see [`../gates/GATES.md`](../gates/GATES.md) §4).
3. **Owner review time** — how long the human needs to *trust* a slice. Gates shrink it; prose doesn't.
