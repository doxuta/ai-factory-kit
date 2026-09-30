<!-- WHO READS ME: an adopter (AI or human) who wants to see the kit applied end to end to a
     multi-tenant web product — the kit's home archetype. For a product without a UI or
     accounts, read ../budget-cli/ as well. I POINT TO: constitution.md · CLAUDE.example.md ·
     gates/ · specs/001-walking-skeleton/ · specs/002-task-crud/ · GATE-RUN.md ·
     ../../model/SPEC-FLOW.md · ../../gates/GATES.md · ../../speckit/README.md. -->

# Worked example — Team Todo (web)

A fictional multi-workspace todo service for small teams: FastAPI and SQLite behind a plain
JavaScript web client. It shows the kit on its home archetype — accounts, an HTTP API, SQL and
a UI — with every artifact in the shape Spec Kit 1.0.12 and the kit's gates expect: a filled
constitution, feature 001 (the walking skeleton) accepted, and feature 002 in the middle of
implementation, plus a gate run that goes red twice before it goes green. Imitate the shapes;
don't copy the content.

Names are fictional: Hà leads the team and approves specs, Linh accepted feature 001, Claude
Code sessions build. The gate transcripts are real runs ([GATE-RUN.md](GATE-RUN.md) says how);
feature 001's acceptance record is an illustration of the format, and says so.

## Read order

| # | File | Shows |
|---|---|---|
| 1 | [`constitution.md`](constitution.md) | The [template](../../constitution/constitution-template.md) filled for multi-tenant SaaS: Article V's entry point is the web client, Article VI's least-privilege clause applies |
| 2 | [`CLAUDE.example.md`](CLAUDE.example.md) | What the project's `.claude/CLAUDE.md` holds: the mirror of Articles I, II, III, VI, and the commands |
| 3 | [`gates/chain.conf`](gates/chain.conf), [`gates/orphan-endpoints.conf`](gates/orphan-endpoints.conf) | All nine slots wired; the orphan gate configured for FastAPI routes and the web client |
| 4 | [`specs/001-walking-skeleton/`](specs/001-walking-skeleton/spec.md) | A small feature kept small: data model and contract folded into [`plan.md`](specs/001-walking-skeleton/plan.md), every task done, [`acceptance.md`](specs/001-walking-skeleton/acceptance.md), `status: accepted` |
| 5 | [`specs/002-task-crud/spec.md`](specs/002-task-crud/spec.md) | Frontmatter at line 1 with the approval; two prioritized stories; a dated clarification written back into the spec |
| 6 | [`plan.md`](specs/002-task-crud/plan.md), [`research.md`](specs/002-task-crud/research.md), [`data-model.md`](specs/002-task-crud/data-model.md), [`contracts/tasks-api.md`](specs/002-task-crud/contracts/tasks-api.md) | Spec Kit's plan artifacts, split out; Technical Context points at Platform Constraints; a Constitution Check per article |
| 7 | [`tasks.md`](specs/002-task-crud/tasks.md) | `- [x] T001` checklist, test tasks first in each story, mid-flight: User Story 1 landed, User Story 2 open |
| 8 | [`quickstart.md`](specs/002-task-crud/quickstart.md) | The acceptance script: the web client as two plain members, plus `curl` probes of the wall |
| 9 | [`GATE-RUN.md`](GATE-RUN.md) | The chain refusing a route nobody calls, then a cross-workspace leak, then green |

## Choices worth noticing

1. **Feature 001 is the walking skeleton.** Sign-in and one route, crossing every layer, plus
   the gate chain, the hook and CI ([PHASE-0 §7](../../model/PHASE-0.md)). Feature 002 starts
   with the chain already guarding every commit.
2. **Two specs, two sizes.** 001 folds its data model and contract into `plan.md` because they
   fit one screen; 002 splits them out the way `/speckit-plan` writes them. Both are allowed
   ([PHASE-0 §10](../../model/PHASE-0.md)).
3. **Status lives in one place.** Each `spec.md` opens with the frontmatter the kit's
   [spec-template override](../../speckit/README.md) puts there; there is no second
   `**Status**:` line in the body. `approved_by` and `approved_on` are what the
   `spec-approval` gate reads.
4. **The isolation wall is checked twice.** Per commit by the `acceptance` slot
   (`tests/isolation`), per feature by a teammate signed in as a plain member of a second
   workspace (`quickstart.md`). GATE-RUN.md shows the first catching a real leak.
5. **This file set replaced the pre-1.4.0 example.** That one used an ✅/⬜ milestone table
   instead of Spec Kit's `- [ ] T001` tasks, folded everything into one plan, fenced its
   frontmatter in a code block, and kept its context file at `.claude/CLAUDE.md`, where Claude
   Code loaded it into adopters' sessions as project instructions.

## What "done" means here

For 001, done: the chain green, every task ticked, `acceptance.md` recorded, `status:
accepted`. For 002, not yet: T009–T013 (completing a task) and T014 (the acceptance run) are
open, so it stays `approved` — and `check-plan-sync.sh` would turn red if anyone set it to
`accepted` before they are done.
