<!-- WHO READS ME: an AI (or human) learning the kit's structure — 3rd in the reading order.
     I POINT TO: ../constitution/ (Level 0: constitution and vision templates) · PHASE-0.md
     (how Level 0 gets written) · ARCHETYPES.md (what varies per kind of product) · SPEC-FLOW.md
     (Level 1) · NON-FEATURE-WORK.md (work that is not a feature) · ../harness/agents/ (Level 2)
     · ../harness/HARNESS.md §7 (hosts and platforms) · ../gates/GATES.md (the floor under all
     three) · ../bin/metrics.py (the measures). -->

# The Three-Level Model

## Level 0 — Constitution (per project; changes rarely, by amendment)

The files that outrank everything, written once in [Phase 0](PHASE-0.md) and amended
deliberately:

| File | Holds | Anti-pattern it kills |
|---|---|---|
| `.specify/memory/constitution.md` | seven articles, I–VII, of **invariants**, plus Platform Constraints, non-goals and governance ([template](../constitution/constitution-template.md)) | Rules scattered across 7 config files, some lazily loaded |
| Vision — `.specify/memory/vision.md` ([template](../constitution/vision-template.md)), or three lines on the constitution's Vision line for a small project | what is being built, for whom, the business model, the success signals | AI optimizing for the wrong customer |
| Archetype — a line in the constitution's header ([ARCHETYPES](ARCHETYPES.md)) | the kind of product: which slot fills, rules, chain slots and release gate apply | A web-shaped constitution on a CLI, violated on day one |
| Platform constraints (**one owner**: the constitution's `Platform Constraints` section; one `platform.md` per package in a monorepo) | the stack, decided with its alternatives | Two homes for the same fact |
| [`../gates/GATES.md`](../gates/GATES.md) and `gates/chain.conf` | definition-of-done as **runnable scripts** | "When-task-done" prose an agent can talk its way past |

**What varies per project, and what does not.** Two things vary: the **archetype**, which picks
the constitution's slot fills, the rules `adopt.py` installs, the chain slots that are
`NA: <reason>` and the release gate ([ARCHETYPES](ARCHETYPES.md)); and the **stack**, which
fills Platform Constraints and the chain's commands. The flow, the gates' logic, the roles and
the governance are the same for every project. Where that is not yet true — reachability
checks for anything but HTTP routes, for one — ARCHETYPES says so under "Known gaps". (Before
v1.4.0 this row claimed the stack was the only per-project content; the 2026-09 audit's CLI
simulation had to reword two articles on day one to make that true.)

Two hard rules learned by measurement:

- **A "business rules" catch-all file is a trap.** Global *invariants* go in the constitution;
  per-domain rules go in that feature's `spec.md`. A single bucket file bloats, then rots.
- **A memory file nobody updates is worse than no memory.** Every Level-0 file needs an owner —
  a named person — and an update trigger: the event that makes them change it (a principle
  that no longer holds, a new business model, a stack decision reversed). Without both it
  becomes a confident liar. The kit's own version of this is its
  [daily sync](../sync/DAILY-SYNC.md).

## Level 1 — Feature flow (per feature; the daily loop)

**`specs/<id>/` is the single atom of work** — `<id>` is `NNN-<name>`, or
`YYYYMMDD-HHMMSS-<name>` when several branches create specs at once. Full walkthrough:
[`SPEC-FLOW.md`](SPEC-FLOW.md). Work that is not a feature has a lane in
[`NON-FEATURE-WORK.md`](NON-FEATURE-WORK.md); each lane that changes behaviour records into a
spec, while a refactor, a chore, docs or a spike, which change none, need no spec.

If your project already runs on epics / milestones / slices / tickets, map them — don't stack a
seventh vocabulary on top:

| Legacy unit | Becomes |
|---|---|
| Epic / theme | A **label** in spec frontmatter (`epic:`) + a roadmap *view* |
| Milestone | A prioritized **user story** (P1/P2/P3) inside `spec.md` |
| Slice / ticket | A **task** in `tasks.md` |
| Bug report | A **task** in the spec whose behaviour it breaks, landed with its regression test |
| Release | A **status** (`released`) on each spec it ships, and a tag |
| Wave / sprint | Dies. Scheduling is not a unit of work. |
| Backlog item | A pointer to a spec's task — the backlog file holds **no content** |

## Level 2 — Automation (per organization; agents + verification)

Four roles, each a file in [`../harness/agents/`](../harness/agents/):

| Role | Duty | Feeds |
|---|---|---|
| [`requirement-researcher`](../harness/agents/requirement-researcher.md) | Raw request + prior specs + repo knowledge → an 80%-clean draft spec | `/speckit-specify` |
| [`task-orchestra`](../harness/agents/task-orchestra.md) | Decompose, dispatch file-disjoint workers, own the merge | `/speckit-implement` |
| [`tester-e2e`](../harness/agents/tester-e2e.md) | Run the feature's `quickstart.md` through the product's real entry point, having not built it — as a **non-privileged** account wherever the product has an authorization boundary | `acceptance.md` |
| [`tech-lead-review`](../harness/agents/tech-lead-review.md) | Adversarial multi-lens review; findings must be refuted-or-fixed, never shelved | the commit gate |

Level-2 law: **verification is adversarial and independent.** The agent that built a thing never
graduates it; reviewers are prompted to *refute*, not to appreciate. And the orchestrator re-runs
gates itself — a subagent's numbers are testimony, not evidence.

## Level 3 — Other hosts and executors (deliberately deferred)

Running the same model across more executors (other agent CLIs, CI robots, k8s runners)
multiplies failure modes before it multiplies value for a small team, so the kit targets one
host and says exactly how far it carries:

- **Supported** — Claude Code on Linux, macOS and WSL (with the project on the Linux
  filesystem); what has actually run on each is in [HARNESS §7](../harness/HARNESS.md).
- **Best-effort** — native Windows, where Claude Code runs hooks under Git Bash.
- **Other AI hosts** (Codex, Gemini CLI, Copilot, Cursor, …) — the model, the specs, the Spec
  Kit flow and the gates carry over: they are Markdown, shell and git. The harness — the
  `.claude/` layout, the agents, the rules — and the careful guard need porting by hand; until
  then, count the guard as absent there.

Details per host: [HARNESS §7](../harness/HARNESS.md). (Before v1.4.0 this section said the kit
"stays portable through the skill format and stack-neutral templates". Only the skills were
portable: the rules' `paths:` key, the agents, the hook envelope and `$CLAUDE_PROJECT_DIR` are
Claude Code's, and on one other host the guard's ask tier fails open.) Revisit when more than
one executor genuinely carries daily work.

## The measure that matters

Not "% of code written by AI" — on a mature setup that hits ~100% and stops being informative.
Track instead:

1. **First-pass land rate** — work that lands without a correction.
2. **Escaped joints** — bugs of the class *"both ends correct, connection missing"* that got past
   the gates ([GATES §4](../gates/GATES.md)).
3. **Owner review time** — how long the human needs to *trust* a change. Gates shrink it; prose
   doesn't.

`python3 factory/bin/metrics.py` (from the project root; `--json` for machines) computes what
git can honestly supply, from the commit trailers in [GATES §10](../gates/GATES.md) (`Spec:`,
`Bug-class:`) and the specs' frontmatter:

| Measure | What `metrics.py` prints | What it cannot see |
|---|---|---|
| — | **trailer coverage** — non-merge commits carrying `Spec:`; read it first | chores and docs legitimately carry none, so coverage below 100% is normal; a `feat` or `fix` without one is not |
| First-pass land rate | `feat` commits for a spec not followed, within the next N commits (default 10), by a `fix` or revert for the same spec | corrections without the trailer — so the rate *rises* as discipline falls; squashed or rewritten history; corrections typed `refactor` or `chore`; a fix 11 commits later |
| Escaped joints | `fix` commits carrying `Bug-class: escaped-joint`, per spec | bugs nobody classified: zero means none reported, not none happened |
| Owner review time | **approval latency** — days from the commit that added a spec to its `approved_on` | the reading itself: the number includes waiting, weekends and batching; a spec committed after approval is not measurable |

It is a report, not a gate: it exits 0 whatever the numbers. Its BLIND TO block, in the script,
matters more than its output.
