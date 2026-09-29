<!-- WHO READS ME: the AI and the owner filling this in at Phase 0, then every agent on every
     feature. adopt.py installs this file twice: as .specify/templates/overrides/
     constitution-template.md, so /speckit-constitution amends against THIS structure and not
     Spec Kit's five-principle scaffold, and as the seed of .specify/memory/constitution.md, the
     project's constitution (written only when absent or still Spec Kit's unfilled scaffold;
     a filled one is never replaced).
     I POINT TO (kit paths; factory/... once adopted): constitution/vision-template.md (the why
     above these rules) · model/PHASE-0.md (the interview that fills me) · model/ARCHETYPES.md
     (slot choices per kind of product) · gates/GATES.md (Article VI delegates to it) ·
     model/SPEC-FLOW.md (Article IV) · model/NON-FEATURE-WORK.md (work that is not a feature) ·
     harness/HARNESS.md §3 (the mirror rule in Governance).
     Worked examples: examples/todo-api/constitution.md (multi-tenant web app) ·
     examples/budget-cli/constitution.md (single-user CLI). -->

# [PROJECT_NAME] Constitution

> This document is the project's **set of invariants**: violating one is a defect to fix, not a
> style choice. It has seven articles, numbered I–VII. Keep the numbering even where an article
> is marked N/A: `CLAUDE.md`, the agent definitions and the gates cite articles by number.
> Distill from what the owner already believes, the vision, and the kind of product; do not
> invent.

**Vision**: [`.specify/memory/vision.md`, or three lines for a small project: who it is for ·
the problem · what success looks like] ([template](vision-template.md))
**Archetype**: [ARCHETYPE: multi-tenant SaaS · backend/API service · mobile + backend ·
frontend-only/static · CLI · library/SDK · data/ML pipeline · embedded/firmware · game ·
IaC/DevOps · LLM/agent app · monorepo — or another, with the owner's reason] — the slot choices
below follow it ([ARCHETYPES](../model/ARCHETYPES.md)).

## Adapting at ratification

The articles were first written for a multi-tenant web product. A CLI, a library or a firmware
image that keeps that wording verbatim starts out violating its own constitution:
`/speckit-plan`'s Constitution Check fails on it, and `/speckit-analyze` treats every
constitution conflict as CRITICAL and may not reinterpret a principle. So before the first
ratification, the owner decides, article by article:

- **Fixed — never reworded away**: the core of Article IV (spec before code, the HARD-GATE at
  approval), the three "always" clauses of Article VI (gates decide done; tests first;
  acceptance by someone other than the builder), and the mirror rule in Governance.
- **Slots — fill them for this product**: every `[BRACKET]` — Articles I, II, III, the entry
  point in Article V, the acceptor in Article VI, Platform Constraints, Non-goals, the risky
  surfaces in Development Workflow. [ARCHETYPES](../model/ARCHETYPES.md) gives each kind of
  product's usual choice; a choice it does not list needs the owner's reason.
- **May be reworded**: examples, and the wording of Article VII and of Development Workflow,
  as long as the rule survives.
- **May be marked N/A**: Article II when the product holds nothing whose exposure is a breach
  (rare — ask twice); the least-privilege clause of Article VI when the product has no
  authorization boundary; a Platform Constraints line that does not apply. How: keep the
  heading, replace the body with `N/A — <reason> (decided YYYY-MM-DD by <owner>)`. Never delete
  an article or renumber the rest; a silent deletion reads as an oversight to the next agent.

Choices made before the first ratified version (1.0.0) are ratification, not amendments; the
owner approves the whole document once. Every later change is an amendment under Governance.
Delete this section when the owner ratifies: its decisions now live in the articles themselves,
as filled slots and dated N/A lines. It is the one heading an amendment through
`/speckit-constitution` must not bring back.

## Core Principles

### I. [DOMAIN INVARIANT — the one rule that IS the product]
<!-- The principle that, if broken, means you built a different product. Examples from real
constitutions: "Metadata-first: business objects are registered in metadata and read at runtime —
never hardcoded as structs" · "Local-first: every feature works offline" · "One source of truth
per fact". Other kinds of product: a library — "the public API is the contract: nothing
exported changes without a MAJOR version"; a data pipeline — "every published number traces to
its source rows". Mark NON-NEGOTIABLE if nothing may override it. -->

### II. [SAFETY INVARIANT — the rule whose violation is a breach, not a bug]
<!-- Data isolation, tenancy, privacy, money, safety of the device. Examples: multi-tenant web —
"every transactional query filters tenant_id, no exceptions, admin included; dynamic SQL is
parameterized, never concatenated"; a CLI reading bank exports — "reads only the files it is
given, writes only under the output directory, never sends data over the network"; firmware —
"an update that fails boots the previous image"; IaC — "nothing is applied without a plan a
human has read"; an LLM app — "model output never reaches a tool, a shell or a query without
validation". State it so a reviewer can grep for violations. -->

### III. [ARCHITECTURE SHAPE — the layering that every change respects]
<!-- Examples: web service — "handler → service → repository → entity; no SQL in handlers, no
HTTP in services; every error wrapped with its origin"; CLI — "argument parsing → command →
pure core → I/O adapters; the core never touches files or the terminal"; library — "public
API → internal modules; nothing internal is re-exported by accident"; data pipeline — "extract
→ validate → transform → load; nothing transforms unvalidated input". Name the layers the
chosen stack uses (Platform Constraints records the stack). -->

### IV. Spec before code
Every feature flows through `specs/<id>/`: spec → plan → tasks → implement
([SPEC-FLOW](../model/SPEC-FLOW.md)). No implementation before the spec is approved
(**HARD-GATE**): the spec's frontmatter says `status: approved` with `approved_by` and
`approved_on`, and the `spec-approval` gate is red for a ticked task on a draft spec.
`specs/<id>` is the **single unit of work**; roadmaps and backlogs are views that point into
specs, never a second home for content. The spec corpus is a reusable asset: specs regenerate
products, documents, and upgrades. Work that is not a feature — a bug in shipped behaviour, a
hotfix, a refactor or dependency bump, a spike, a release — follows its lane in
[NON-FEATURE-WORK](../model/NON-FEATURE-WORK.md).

*RETRO-FIT mode* (name it — don't leave brownfield implicit): work shipped BEFORE this
constitution is spec'd with a `spec.md` **verified against current code** (never transcribed
from old docs) plus runnable Success Criteria; `plan.md`/`tasks.md` are optional, but
`/speckit-converge` (specify-cli 1.0.12) stops without them, so a retro-fitted spec that must
converge gets a short pair first ([RETROFIT-PLAYBOOK §2b](../model/RETROFIT-PLAYBOOK.md)). The
[deletion condition](../model/RETROFIT-PLAYBOOK.md) for legacy docs stays unchanged.

### V. [REACHABILITY — how a capability reaches its user]
<!-- Fill the entry point for this product. Web app or SaaS: "operable in the real UI — API-only
≠ done". HTTP API as the product: "reachable through the public gateway with real
authentication, and documented in the published contract". CLI: "reachable from the installed
command and listed in its --help; a function no subcommand calls ≠ done". Library/SDK:
"exported from the public API, documented, and exercised by a test that imports it the way a
user would". Data pipeline: "the job is scheduled and a named consumer reads its output".
Embedded: "reachable on the device through its real input". LLM agent: "the tool is registered
with the agent and exercised by an eval". -->
A capability is unfinished until its user can reach it through [REAL_ENTRY_POINT — the
product's real interface; EXAMPLE (web): "the real UI — API-only ≠ done"], or the gap is a
named task in the feature's `tasks.md`. Before believing a slice is finished, answer: **"who
will CALL this?"** (the deadliest bug class is the joint nobody wired —
[GATES §4](../gates/GATES.md)).

### VI. Executable gates and independent acceptance
Always:
- **Gates decide done.** "Done" = the [gate chain](../gates/GATES.md) (`./gates/run-chain.sh`)
  is green — never a claim, yours included. A subagent's numbers are testimony; the
  orchestrator re-runs the gates itself.
- **Tests first.** Behaviour changes start with a failing test (red → green → refactor), and
  every `tasks.md` carries test tasks ahead of the code they prove. Spec Kit's `/speckit-tasks`
  treats tests as optional unless asked; this article asks. Where behaviour is judged rather
  than computed (model output), the test is an eval against a recorded baseline
  ([GATES §8](../gates/GATES.md)).
- **Acceptance by someone other than the builder.** Per feature, [ACCEPTOR — who may run
  acceptance: a named person, or an agent in a fresh context that did not build the feature
  ([tester-e2e](../harness/agents/tester-e2e.md))] runs `quickstart.md` through the entry point
  of Article V and records `specs/<id>/acceptance.md` before the spec becomes `accepted`
  ([GATES §3](../gates/GATES.md)).

Where the product has an authorization boundary (accounts, roles, tenants, OS users, cloud
permissions) — otherwise `N/A — <reason>`:
- **Least-privilege acceptance.** The acceptance run uses a non-privileged account, because
  privileged accounts bypass the walls being tested. Analogues: a non-admin user, a non-root OS
  user, a least-privilege CI role, a fresh device or profile.

### VII. Deliberate simplicity
Within a layer: reuse before stdlib, stdlib before dependency, dependency before new code;
mark intentional shortcuts with a `shortcut:` comment carrying the ceiling and upgrade path.
But the abstractions Articles I–III mandate are **not** over-engineering — never collapse them
for brevity. When simplicity and the constitution conflict, the constitution wins.

## Platform Constraints
<!-- The ONE home for the stack. plan.md's Technical Context points here rather than restating
it, and .claude/CLAUDE.md holds the commands, not the stack. The stack is decided in Phase 0
from 2–3 options the owner approves (model/PHASE-0.md); lines that feature 001, the walking
skeleton, settles may read "TBD — settled by specs/001-<name>" until then. -->
- **Stack**: [LANGUAGE+VERSION · FRAMEWORK · STORAGE · RUNTIME/HOSTING]. Decided [YYYY-MM-DD]
  by [OWNER]; rationale: [WHY]; alternatives considered: [THE OTHER OPTIONS].
- **Spec Kit**: specify-cli [VERSION — kit 1.4.0 was tested with 1.0.12], integration
  [claude | …]; spec numbering [sequential NNN | timestamp YYYYMMDD-HHMMSS — timestamp when more
  than one branch creates specs at once]; extensions adopted: [NONE | names].
- **Models** (LLM/ML products; otherwise N/A): [EXACT MODEL IDS — a pinned version, never an
  alias that moves]; eval baseline at [PATH].
- **Conventions**: [API casing, timestamps, status codes · CLI flags and exit codes · public-API
  versioning — whichever the product has].
- **Data changes**: [migration discipline, EXAMPLE: up+down, sequential, never edit an applied
  one · or N/A].
- **Environments and release**: [ENVIRONMENTS, EXAMPLE: local · staging · production]; secrets
  live in [WHERE — never in the repository]; a broken release shows as [SIGNAL — an alert, a
  smoke check, a dashboard someone watches]. May read "TBD — before the first release" until
  then ([NON-FEATURE-WORK](../model/NON-FEATURE-WORK.md), release lane).
- **Branch model and commits**: [BRANCH_MODEL]; Conventional Commits with a `Spec: <id>` trailer
  ([GATES §10](../gates/GATES.md)).

## Non-goals (doctrine)
<!-- What this project deliberately does NOT do — as protected as the principles. Real examples:
"not self-service SaaS; customers never see the builder" · "no source handover by default" ·
"AI is an optional internal accelerator, never a mandatory per-customer cost". -->

## Development Workflow
1. New feature: the [Level-1 flow](../model/SPEC-FLOW.md), HARD-GATE at spec approval.
2. Every commit: the [gate chain](../gates/GATES.md) green; the pre-commit hook and CI run the
   same chain once feature 001 has wired them.
3. Risky surfaces ([RISKY_SURFACES — EXAMPLE (web): data, authorization, money; a CLI: file
   writes and deletes; IaC: state and permissions]): adversarial review
   ([tech-lead-review](../harness/agents/tech-lead-review.md)) before commit — findings are
   fixed or explicitly refuted, never shelved.
4. Acceptance: as Article VI says — through the real entry point, recorded in
   `acceptance.md`, as a non-privileged account where there is an authorization boundary.
5. Work that is not a feature: its lane in [NON-FEATURE-WORK](../model/NON-FEATURE-WORK.md).
   Owner review of a hotfix within [HOTFIX_WINDOW — default: two working days].
6. Docs: the spec IS the feature's technical document. When code and spec disagree, find out
   which one moved. If the spec states intended behaviour the code does not deliver, the code
   is wrong: record a new task (converge). If the code reflects a deliberate, owner-approved
   change the spec never recorded, fix the spec with the correction marked (≠old) and a dated
   Clarifications entry. If you cannot tell, ask the owner. Deleting a legacy doc follows the
   [retro-fit deletion condition](../model/RETROFIT-PLAYBOOK.md).

## Governance
- This constitution outranks every other process document; conflicts resolve in its favor.
- **Amendments**: only [OWNER] approves. Each bump follows semver (MAJOR remove/redefine a
  principle · MINOR add/expand · PATCH clarify), updates the dates, and says what changed and
  why in the commit that makes it. `/speckit-constitution` amends this file against the kit's
  template override (installed by adopt.py) — keep the headings and the article numbers — and
  drafts a Sync Impact Report comment for the owner's review, which Spec Kit 1.0.12 expects to
  be removed before the commit.
- ⚠️ **The mirror rule** (a measured trap — [HARNESS §3](../harness/HARNESS.md)): configuration
  scoped to file paths loads **lazily**; safety invariants (I, II, III, VI) must ALSO live in the
  always-loaded context file (`.claude/CLAUDE.md`) and in the INVARIANTS block of each agent
  definition (`.claude/agents/*.md`), and dispatch prompts restate them. The constitution is
  the *authoritative* copy, not the *only* copy — amending it means syncing the mirrors in the
  same commit.
- Compliance is checked by runnable gates and review checklists, not by memory.

**Version**: [X.Y.Z] | **Ratified**: [YYYY-MM-DD] | **Last Amended**: [YYYY-MM-DD]
