<!-- WHO READS ME: an AI (with the owner) starting a product from an idea, before any code
     exists — sent here by ../AI-ONBOARDING.md §2. Also the owner, for §8 (what only they
     decide). I POINT TO: ../constitution/vision-template.md (what the interview fills) ·
     ../constitution/constitution-template.md (what ratification approves) · ARCHETYPES.md (the
     archetype → profile, slots, chain) · SPEC-FLOW.md (the loop feature 001 runs) ·
     NON-FEATURE-WORK.md (the spike lane) · ../gates/GATES.md (the chain 001 wires) ·
     ../harness/skills/careful/SKILL.md (the guard and its probes) · ../harness/HARNESS.md §7
     (hosts and platforms). -->

# Phase 0 — starting from an idea

Everything else in this kit assumes a constitution, a stack and a gate chain already exist.
With only an idea, none of them do. Phase 0 produces them, in an order where each step has
what it needs, and it puts the one thing that looks exempt — scaffolding — under the same
HARD-GATE as every other line of code.

What paid for this file (the 2026-09 readiness audit, simulated from-idea runs): asked for the
stack, the owner said "I don't know, pick something cheap", and the AI chose one with no kit
guidance and no record of the alternatives. All five dev commands were written into
`CLAUDE.md` before any of them existed; one named a script that did not exist until task T002.
The gate chain was written from scratch, and the kit adaptation came to 228 lines against 204
lines of product code and tests. None of that was wrong work — it had no place to happen.

**Phase 0 is done when** the constitution is ratified (1.0.0) with its vision, the harness is
adopted and the careful guard registered and probed, and feature 001 — the walking skeleton —
is `accepted`, with every chain slot wired or `NA: <reason>`, the pre-commit hook and CI
installed, and `./gates/run-chain.sh` green. From then on every feature follows
[SPEC-FLOW](SPEC-FLOW.md) and every other change its lane in
[NON-FEATURE-WORK](NON-FEATURE-WORK.md).

## 1. Prerequisites

| Tool | Why | Check |
|---|---|---|
| git ≥ 2.28 | the repository; `git init -b` needs 2.28 | `git --version` |
| python3 ≥ 3.8 | `adopt.py`, the spec gates, `metrics.py`; standard library only | `python3 --version` |
| bash (3.2 is enough) | the gate scripts and the guard's shim; on Windows, Git Bash | `bash --version` |
| uv | installs Spec Kit | `uv --version` |
| Python ≥ 3.11, for Spec Kit only | specify-cli 1.0.12 declares `Requires-Python >=3.11` | if uv picks an older one: `uv python install 3.11`, then add `--python 3.11` to the install below |
| Claude Code | the harness (`.claude/`) and the careful guard target it | `claude --version` |
| a git host with CI (optional until feature 001) | the remote (§9) and the CI half of the chain; the kit ships a GitHub Actions job | — |

Supported envelope: Claude Code on Linux, macOS and WSL (Linux filesystem); what has actually
run on each is in [HARNESS §7](../harness/HARNESS.md). Native Windows, with
Claude Code running hooks under Git Bash, is best-effort. On other AI hosts the model, the
specs, the Spec Kit flow and the gates carry over; the harness and the guard need porting by
hand ([HARNESS §7](../harness/HARNESS.md)).

## 2. The command order

Each step names who acts. Steps 1–5 are commands; step 6 is conversation; nothing in steps 1–8
is product code.

```bash
# 1. AI: a repository
mkdir my-product && cd my-product
git init -b main

# 2. AI: the kit, vendored as a submodule and pinned to a release tag
git submodule add https://github.com/doxuta/ai-factory-kit factory
git -C factory checkout v1.4.0          # the release you pin; list them: git -C factory tag
git add .gitmodules factory

# 3. AI: harness, careful hooks, gates and Spec Kit template overrides, for the archetype
python3 factory/bin/adopt.py --profile <profile>     # profiles: ARCHETYPES.md; default: full

# 4. AI: Spec Kit, pinned to the version this kit release was tested with
uv tool install specify-cli==1.0.12
specify init --here --force --non-interactive --integration claude
#   add --ignore-agent-tools if the claude CLI is not on PATH
```

5. **AI**: confirm what step 4 left alone — `python3 factory/bin/adopt.py --check` exits 0.
   Checked with specify-cli 1.0.12 after `adopt.py`: `specify init --here --force` kept
   `.specify/memory/constitution.md`, `.specify/memory/vision.md` and
   `.specify/templates/overrides/`, and `resolve-template.sh constitution-template` then
   returned the kit's template. Without `--force` it stops in a non-empty directory, and an
   agent's shell has no terminal to answer it; without `--non-interactive`, under a
   pseudo-terminal it waits at "Choose script type" until killed (measured); without
   `--ignore-agent-tools` it exits 1 when `claude` is not on PATH. `specify` lands in uv's tool bin directory; if the shell cannot
   find it, `uv tool update-shell`. Init also prints *"Consider adding .claude/ … to
   .gitignore"* — do not: `.claude/` holds the harness and the guard, and they are versioned.
6. **Owner and AI**: the vision interview (§3), the archetype (§4), the stack (§5), the
   constitution (§6). Ratification is the HARD-GATE: nothing below starts before the owner
   approves the constitution.
7. **AI**: fill `.claude/CLAUDE.md` — the safety mirror of Articles I, II, III and VI, and dev
   commands written as `TBD — wired by specs/001-<name>` (they do not exist yet). Fill each
   `.claude/rules/*.md`, or delete one that does not apply and re-run `adopt.py`: it records
   the rule as dropped, re-renders the kit's own files that linked to it, and offers a
   `.factory-new` for each file you fill that did (checked on this release). Merge those, then
   `adopt.py --check`. Its placeholder warnings list what is still unfilled — in the agents'
   INVARIANTS blocks too.
8. **AI, owner approves**: adapt `.claude/hooks/careful.json` for the archetype
   ([ARCHETYPES](ARCHETYPES.md)) and check it with
   `python3 .claude/hooks/check-careful.py --check-config`. First commit: everything so far.
   **Owner**: create an empty repository on the git host (§9). **AI**:
   `git remote add origin <url>`, `git push -u origin main`, then
   `python3 factory/bin/adopt.py --register-guard`, then the two live probes in
   [careful](../harness/skills/careful/SKILL.md) ("Verification"). Commit
   `.claude/settings.json`.
9. **Owner and AI**: feature 001, the walking skeleton (§7). Its last tasks run
   `python3 factory/bin/adopt.py --install-git-hook --ci github`.
10. From then on: no commit on red.

**Choosing the profile at step 3.** When the idea already says what kind of product it is ("a
CLI that…"), pass that profile. When it does not, install with the default `full`, which drops
nothing, and narrow it after step 6 with `adopt.py --profile <p>`: it lists the rule files the
profile drops, for you to delete, re-renders the kit's own files that link to them, and offers a
`.factory-new` for each file you fill that does (checked on this release). While those files are
still unfilled, accepting a `.factory-new` is a plain `mv` (a script's `.factory-new` keeps its
execute bit).

**Teammates and CI** clone with `git clone --recurse-submodules`, or run
`git submodule update --init` after a plain clone. An empty `factory/` leaves every link into
it dead and every `adopt.py` command missing. Once feature 001 has installed the hook, each
clone runs `python3 factory/bin/adopt.py --install-git-hook` once: `core.hooksPath` is local to
a clone, and a clone without it refuses no red commit (`adopt.py --check` warns there).

## 3. The vision interview

The constitution distills what the owner already believes; with only an idea, the owner has
not said it yet. The interview gets it said, in the owner's words, into
`.specify/memory/vision.md` from [the template](../constitution/vision-template.md). A small
project may put the first three answers on the constitution's `Vision` line instead.

Rules: one question at a time, multiple choice where it helps. The AI asks and writes; it does
not answer for the owner. "I don't know" is an answer: record it as
`(assumption — check by <date or signal>)`, or, when a wrong guess would be expensive, turn it
into a spike ([NON-FEATURE-WORK](NON-FEATURE-WORK.md)). Ask all twelve; the last ones are the
ones owners skip and later wish they had not.

| # | Question | Writes to |
|---|---|---|
| 1 | Who has the problem? A real person or role, not a market. | Problem, Users |
| 2 | What do they do about it today, and what does that cost them — time, money, mistakes? | Problem |
| 3 | What changes for them when this works? | Value |
| 4 | Who else touches it — payer, admin, operator? Whose needs win when they conflict? | Users |
| 5 | Who pays, and for what? Or: internal tool, open source, personal use. | Business model |
| 6 | What will it deliberately not do, or not be? | Non-goals → constitution Non-goals |
| 7 | How will we know it works? Two or three signals, and who checks each one, when. | Success signals |
| 8 | How does the user reach it — browser, phone, terminal, an import in their code, a scheduled job, a device, a conversation with an agent? | Archetype → §4 |
| 9 | What does it store or touch that would hurt someone if it leaked, was lost or was wrong? | Data and risk → Article II |
| 10 | Where does it run, and who keeps it running? | Platform Constraints; the release lane |
| 11 | What is already fixed — a language the team knows, a monthly cost ceiling, a deadline, a platform the company mandates? | the stack options in §5 |
| 12 | Who approves specs, and who can run acceptance without having built the feature? | Governance `[OWNER]`; Article VI acceptor |

The owner reads the drafted `vision.md` and corrects it. It is amended like the constitution
afterwards: the owner approves, the date moves.

**Optional — test the idea before building it.** Spec Kit ships an `assess` extension:
`specify extension add assess` installed `/speckit-assess-intake`, `-research`, `-define`,
`-shape` and `-decide` (checked with 1.0.12). It works with no code, writes under
`.specify/assessments/<slug>/`, and a `go` hands off to `/speckit-specify`; a `kill` is a
valid, cheap outcome. Treat its files as working notes: what survives lands in `vision.md`,
the constitution or a spec, and the assessment is at most pointed to.

## 4. Choosing the archetype

Question 8 usually answers it. The AI proposes one archetype from
[ARCHETYPES](ARCHETYPES.md) with a one-line reason; the owner confirms. It decides the
`adopt.py` profile, the constitution's slot choices (Article V's entry point, Article VI's
acceptor, whether least-privilege acceptance applies), the chain slots and their N/A reasons,
the `careful.json` additions and the release gate. A product with two entry points (a mobile
app and its API, a SaaS with a CLI) picks the archetype of the entry point its primary user
touches, notes the other, and takes the profile that drops fewer rules.

## 5. Choosing the stack

The AI presents **two or three options**, in the format of
[spec-first](../harness/skills/spec-first/SKILL.md) step 4 — the smallest that works, the one
that fits growth, one lateral — each with: language and version, framework, storage, where it
runs and what that costs per month, what the owner or team already knows, how each chain slot
would be wired (formatter, linter, test runner — and whether that runner exits green with zero
tests, [ARCHETYPES](ARCHETYPES.md) §"Stack stanzas"), and what would be hard to undo. The AI
takes a stance and names the evidence that would change it. The owner chooses.

"Pick something cheap" is not a choice: it is permission for the AI to choose, and the AI
still presents the options, recommends one, and records that the owner approved the
recommendation. The decision goes into the constitution's **Platform Constraints** as
decision, date, owner, rationale and the alternatives considered — the one home of the stack.
`plan.md`'s Technical Context points there, and a line that feature 001 will settle (an exact
minor version, the hosting account) reads `TBD — settled by specs/001-<name>` until it does.
When an option's feasibility is unknown ("can this library read these files?"), spike it
first, time-boxed, and write the finding into the rationale.

## 6. Ratifying the constitution — the first HARD-GATE

`adopt.py` seeded `.specify/memory/constitution.md` from the kit template and installed the
same template as `.specify/templates/overrides/constitution-template.md`, so
`/speckit-constitution` fills and later amends the kit's seven articles, not Spec Kit's
five-principle scaffold. The AI fills it from the vision, the archetype and the stack —
through `/speckit-constitution` or by hand — and applies the template's **Adapting at
ratification** block: which parts are fixed, which are slots, which may be reworded, and how
a part is marked N/A (kept, with its reason and date; never deleted, never renumbered).

The owner reads the whole document and approves it. That approval is the ratification:
version 1.0.0 and today's date on the Version line. Choices made before it are ratification;
every later change is an amendment under Governance. Until it happens, no spec is written —
spec 001's plan runs a Constitution Check against it.

## 7. Feature 001 — the walking skeleton

**Is scaffolding code? Yes.** The project skeleton, the formatter and linter configuration,
the test runner, the gate wiring, the CI job and the environment and secrets handling are code,
so they go through a spec like any other code: spec 001, approved before its first task is
ticked (the `spec-approval` gate is red otherwise).

Spec 001 describes the thinnest real capability that crosses every layer of Article III and
reaches the user through Article V's entry point — a walking skeleton: small in function,
complete in path. Two stories, both P1: the thin capability itself (a CLI's one subcommand on
an empty input; a web app's sign-in and an empty list), and "the owner can run
`./gates/run-chain.sh` and see every slot green or N/A with its reason". Success criteria
include the chain proving it bites: a deliberate red, such as an unformatted file, is refused
by the hook.

Its tasks, in Spec Kit's phases:

| Phase | Tasks |
|---|---|
| 1 Setup | scaffold the project per Platform Constraints and Article III · formatter and linter config, then wire `format` and `static` in `gates/chain.conf` · the test runner and a first test, red then green, then wire `test` with a zero-test guard if the runner needs one · wire `build` |
| 2 Foundational | `orphan-endpoints`: a `gates/orphan-endpoints.conf`, or `NA: <reason>` · `acceptance`: the automated isolation or acceptance tests, or `NA: <reason>` · environments and secrets: what exists where, where secrets live (never in the repository), how CI gets them · settle the `TBD` lines in Platform Constraints and `CLAUDE.md` |
| 3 Story | the thin capability, test first |
| Final | `adopt.py --install-git-hook --ci github`, plus the toolchain steps the CI job needs · prove the hook refuses a red commit · `quickstart.md` run by the acceptor, recorded in `acceptance.md` · status `accepted` |

**The chain while 001 is being built.** Until every slot is wired, `run-chain.sh` is red by
construction, and the kit does not install the hook or CI before then because they would refuse
every commit. Those commits fall under the one exception to "no commit on red", which
[GATES §1](../gates/GATES.md) defines: the chain may be red **only at a `TODO` slot** — its
output says `not wired (TODO)` — never at a wired one; and the three spec gates, which sit after
the `TODO` slots, are run directly (`./gates/check-spec-approval.sh`,
`./gates/check-spec-numbers.sh`, `./gates/check-plan-sync.sh`). Once the last `TODO` is gone,
install the hook and CI with `python3 factory/bin/adopt.py --install-git-hook --ci github` —
never a hand-written hook, installer or workflow — and the ordinary rule starts: no commit on
red.

**The guard during 001.** Feature 001 runs after the guard is registered (§2 step 8), so the
guard asks before every edit of `gates/chain.conf`, `gates/*.conf` and
`gates/orphan-allowlist.txt`: the owner answering those asks is the review of what "green" will
mean. A project gate of your own may be created as `gates/check-<name>.sh` (the guard asks);
once it exists it is guarded like the kit's, and a change to it is a human's edit. So keep the
script generic and put what grows with each feature — expected outputs, a consumer program,
the list of exported names — in a data file or test module outside `gates/`, which review
reads; otherwise every feature needs the owner to edit the gate by hand.

After 001, the format, static, test and build rows in `CLAUDE.md` and the same slots in
`gates/chain.conf` name the same commands; a change to one changes the other in the same commit.

## 8. Who decides what — the owner's checklist

The AI proposes; the owner decides. A decision below that was not the owner's is a defect in
Phase 0, however good it was.

| Decision | AI proposes | Owner decides | Recorded in |
|---|---|---|---|
| Who it is for, what it is worth, what it will not do | questions, a draft | the answers | `vision.md` |
| Archetype | one, with its reason | confirms or changes | constitution header; `adopt.py --profile` |
| Stack | 2–3 options and a stance | chooses | Platform Constraints |
| Each article's slot, each N/A | a draft per slot | approves the whole constitution | the constitution (1.0.0) |
| Who approves specs; who may accept | — | names them | Governance; Article VI |
| Protected branches and extra guard rules | a `careful.json` draft | approves | `.claude/hooks/careful.json` |
| The remote | the moment (§9) | creates it on the host, with their account | `origin` |
| Spec 001 | the draft spec | approves (`approved_by`, `approved_on`) | `specs/001-*/spec.md` |
| What counts as released, and who performs the step | the release gate for the archetype | approves; performs or delegates the irreversible step | [NON-FEATURE-WORK](NON-FEATURE-WORK.md) release lane |

## 9. When to create the remote

Before the first run in which the agent works with nobody watching — at step 8 at the latest,
and before `--register-guard`. Until a remote exists, `.git` is the only copy of the history:
the guard denies a recursive delete of `.git` or `.specify` in a repository with no remote, but
it only *asks* on the recoverable-but-costly shapes (`reset --hard`, `branch -D`), and an ask
nobody answers is not a wall. CI needs the remote too. Creating the repository on the host is
the owner's act, because it is their account and their visibility setting.

## 10. Sizing — the same gates, different ceremony

Three things do not scale down, because each exists for the case where nobody is looking:
**the spec is approved before its first task is ticked** (`spec-approval`); **the chain is
green before a commit lands**, with the hook and CI installed; **acceptance is run by someone
other than the builder and recorded** (`acceptance.md`). The careful guard stays registered.
Everything else scales with the project.

| | Solo or prototype | Small team | Regulated or high-stakes |
|---|---|---|---|
| Vision | three lines on the constitution's Vision line | `vision.md` | `vision.md`, reviewed when the constitution is amended |
| Spec | one P1 story, its requirements, 2–3 success criteria | full template | full template, plus `/speckit-checklist` for requirement quality |
| Clarify | when the spec has open markers | always before approval | always; questions and answers dated |
| Plan artifacts | `data-model.md` and `contracts/` folded into `plan.md` while they fit one screen | split out | split out; contracts versioned |
| `/speckit-analyze` | features with more than one story, or touching a risky surface | before every implement | before every implement; CRITICAL findings block |
| Adversarial review | risky surfaces only (Development Workflow 3) | risky surfaces; a second human on spec approval | every change to a risky surface, by someone who did not build it |
| Parallel dispatch | none — sequential is simpler | file-disjoint work only | file-disjoint work only |
| Acceptor | the owner, or `tester-e2e` in a fresh context | a teammate who did not build it | a named person with the role; least-privilege account wherever there is a boundary |
| Spec numbering | sequential | timestamp once two branches create specs at once ([SPEC-FLOW](SPEC-FLOW.md)) | timestamp |
| Approvals | the owner, in frontmatter | the spec's owner and a reviewer, in frontmatter and the pull request | frontmatter plus a record the host keeps (a protected branch's required review) |
| Metrics | occasionally | weekly, `metrics.py` | every release; `Spec:` trailers on every feat and fix |

The concessions that already existed, now in one place: a small project may keep its vision on
the constitution's Vision line; `data-model.md` and `contracts/` fold into `plan.md` while
small (the todo-api example's walking skeleton does; its feature 002 splits them out); `analyze` is for work that is not small; adversarial review
is for risky surfaces; parallel dispatch only for file-disjoint work. The kit does not make a
product compliant with any regulation. What it gives a regulated project is traceability an
auditor can read: who approved which spec when, who accepted it as whom, and which commits
served it.

## 11. What Phase 0 does not cover yet

- **Hosts other than Claude Code.** The command order is Claude Code's; elsewhere, port the
  harness and the guard by hand ([HARNESS §7](../harness/HARNESS.md)).
- **CI other than GitHub Actions.** The job is two steps — check out with submodules, run
  `./gates/run-chain.sh`; port [`../gates/ci/github-actions.yml`](../gates/ci/github-actions.yml)
  by hand.
- **Decision records beyond the stack.** Platform Constraints records the stack decision and its
  alternatives; later decisions live in the owning spec's `research.md`. There is no separate
  decision-record directory, deliberately — it would be a second home.
- **A product with no git host.** The hook still refuses red commits locally, and nothing
  checks what `--no-verify` let through.
- These steps were run on Linux against this release's `adopt.py` and specify-cli 1.0.12, up to
  and including the hook and CI install. No full from-idea run on macOS or on Windows has been
  recorded.
