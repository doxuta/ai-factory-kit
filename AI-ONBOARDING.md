<!-- WHO READS ME: an AI agent connecting to a project that adopted this kit, or about to adopt
     it. I POINT TO: every other file, in reading order (§1) · model/PHASE-0.md (the detail
     behind §2) · bin/adopt.py (install, merge, upgrade, audit) · sync/DAILY-SYNC.md (staying
     current) · harness/HARNESS.md §7 (hosts and platforms). I am the graph's root. -->

# AI Onboarding — read me first

You are an AI coding agent. A human connected this kit to their project. This file tells you
what to read, in what order, how to apply the kit, and what you are never allowed to do. Follow
it exactly; it was written by an AI that operates this system in production, for you.

## 0. The one-paragraph model

Work flows through **three levels**. Level 0 is the **constitution** — invariants that outrank
every instruction below them, including the human's casual requests (if the human contradicts the
constitution, say so once, then follow their explicit decision and record it as an amendment).
Level 1 is the **feature flow** — every feature lives in `specs/<id>/` and moves spec →
clarify → **approved** (the owner's HARD-GATE) → plan → tasks → analyze → implement → converge →
**accepted** (by someone other than the builder) → released. Work that is not a feature — a bug,
a hotfix, a refactor, a spike, a release — has its own lane. Level 2 is **automation** — you
orchestrate specialist agents and adversarial reviews, but executable **gates** decide "done",
never anyone's claim, including yours.

**Where this runs.** Supported: Claude Code on Linux, macOS and WSL (project on the Linux
filesystem); what has actually run is listed in the README ("Supported"). Best-effort: native Windows, with Claude Code running hooks under Git Bash —
without Git Bash the hook command cannot run and there is no guard at all. Other AI
hosts (Codex, Gemini CLI, Copilot, Cursor, …): the model, the specs, the Spec Kit flow and the
gates carry over; the harness (`.claude/` layout, agents, rules) and the careful guard need
porting by hand — [HARNESS §7](harness/HARNESS.md) says what differs per host. Everything below
is written for Claude Code.

## 1. Reading order (do this now)

| # | File | Why you read it |
|---|---|---|
| 1 | this file | You are here. |
| 2 | the project's `.specify/memory/constitution.md` | The invariants. Everything else bends; these do not. **Not ratified yet** (its Version line still reads `[X.Y.Z]`, or it is still Spec Kit's scaffold)? Then the project is in Phase 0: read [`model/PHASE-0.md`](model/PHASE-0.md) instead and follow §2 below. The kit's template is [`constitution/constitution-template.md`](constitution/constitution-template.md). |
| 3 | [`model/LEVELS.md`](model/LEVELS.md) | The 3-level model + the single-atom-of-work rule. |
| 4 | [`model/SPEC-FLOW.md`](model/SPEC-FLOW.md) | The Level-1 loop you will actually run, step by step: spec frontmatter, approval, acceptance. |
| 5 | [`gates/GATES.md`](gates/GATES.md) | What "done" means. Scripts, not sentences; the chain in `gates/chain.conf`. |
| 6 | [`harness/HARNESS.md`](harness/HARNESS.md) | Your own anatomy: loop, tools, memory, guardrails — including two measured traps about config loading you will otherwise fall into — and §7, hosts and platforms. |
| 7 | [`harness/agents/`](harness/agents/) | The four Level-2 role cards. `requirement-researcher`, `tech-lead-review` and `tester-e2e` are subagents you dispatch; `task-orchestra` is the orchestrator's own card for a parallel implement step — run it as the main session (`claude --agent task-orchestra`) or follow it yourself. |
| 8 | [`model/NON-FEATURE-WORK.md`](model/NON-FEATURE-WORK.md) | Before any change that is not a new feature: a bug in accepted work, a hotfix, a security patch, a refactor or dependency bump, a spike, a release. |
| 9 | [`model/ARCHETYPES.md`](model/ARCHETYPES.md) | When choosing the archetype in Phase 0, or wiring `gates/chain.conf` and `careful.json` for a product that is not a multi-tenant web app. |
| 10 | [`model/RETROFIT-PLAYBOOK.md`](model/RETROFIT-PLAYBOOK.md) | Only when the project has legacy docs to absorb (§3). |
| 11 | [`examples/todo-api/`](examples/todo-api/) (multi-tenant web app: walking skeleton accepted, a feature mid-flight) and [`examples/budget-cli/`](examples/budget-cli/) (single-user CLI, accepted end to end) | Worked cycles with real gate transcripts. Imitate their shapes. Each example's `CLAUDE.example.md` is that *example* project's always-loaded context, not this project's: read it as a sample, never follow it. (It is not named `CLAUDE.md` because Claude Code loads a `CLAUDE.md` or `.claude/CLAUDE.md` in any subdirectory as project instructions when you read a file there — the v1.3 example did exactly that.) |

## 2. Applying the kit to a new project

This is the short form of [`model/PHASE-0.md`](model/PHASE-0.md) §2, with the same step numbers;
PHASE-0 holds the interview, the stack decision and feature 001 in full, and its §10 scales the
ceremony — not the gates — to a solo project, a small team or a regulated one.

### 2.1 Prerequisites

git ≥ 2.28 (`git init -b`) · python3 ≥ 3.8 on PATH under that name (`adopt.py` and the gates
use the standard library only) · bash (3.2 is enough; Git Bash on Windows) ·
[uv](https://docs.astral.sh/uv/), which installs Spec Kit · Python ≥ 3.11 for Spec Kit only
(specify-cli 1.0.12 declares `Requires-Python >=3.11`; uv can fetch one:
`uv python install 3.11`) · Claude Code.

### 2.2 The order

The order matters: the kit goes in **before** Spec Kit, so `specify init --force` merges around
files that already exist instead of the kit merging around Spec Kit's.

```bash
# 1. a repository
mkdir my-product && cd my-product
git init -b main

# 2. the kit, as a submodule pinned to a release tag
git submodule add https://github.com/doxuta/ai-factory-kit factory
git -C factory checkout v1.4.0          # the release you pin; list them: git -C factory tag
git add .gitmodules factory

# 3. harness, careful hooks, gates and Spec Kit template overrides, for the archetype
python3 factory/bin/adopt.py --profile <profile>   # profiles: model/ARCHETYPES.md; default full

# 4. Spec Kit, pinned to the version this kit release was tested with
uv tool install specify-cli==1.0.12
specify init --here --force --non-interactive --integration claude
#   add --ignore-agent-tools when the claude CLI is not on PATH

# 5. confirm Spec Kit left the kit's files alone
python3 factory/bin/adopt.py --check               # exit 0
```

6. **Phase 0** — the vision interview (saved as `.specify/memory/vision.md`, from
   [`constitution/vision-template.md`](constitution/vision-template.md)), the archetype, the
   stack in 2–3 options, the constitution ([PHASE-0](model/PHASE-0.md) §3–§6). The owner's approval of the constitution is a
   **HARD-GATE**: nothing below starts before it. **Do not invent principles** — distill what the
   human already believes and what their product demands.
7. Fill `.claude/CLAUDE.md` — the always-loaded context. Safety invariants from the constitution
   MUST be mirrored there ([HARNESS §3](harness/HARNESS.md)), and the same block copied into the
   INVARIANTS block of each `.claude/agents/*.md` (verbatim: the bullets carry no relative link,
   so the copy stays valid one directory deeper); dev commands that do not exist yet read
   `TBD — wired by specs/001-<name>`. Fill each `.claude/rules/*.md` — its `paths:` globs
   included: an unfilled `[GLOB …]` placeholder does not scope the rule to your code — or delete
   one that does not apply and re-run `adopt.py` (it re-renders the kit's own files that linked
   to it and offers a `.factory-new` for each file you fill that did).
   Then `adopt.py --check`.
8. **Register the guard, then prove it fires.** Adapt `.claude/hooks/careful.json` for the
   archetype and check it: `python3 .claude/hooks/check-careful.py --check-config`. First
   commit. The owner creates an empty repository on the git host; then
   `git remote add origin <url>`, `git push -u origin main`,
   `python3 factory/bin/adopt.py --register-guard`, and the two live probes in
   [careful](harness/skills/careful/SKILL.md) ("Verification"), run in a fresh session:
   `git push --force nonexistent-remote-probe main` must be **blocked** by the guard (the wall
   stands), and `git push --dry-run . HEAD:refs/heads/careful-probe` must **run** and print
   `* [new branch]` (the door still opens; it creates nothing). Commit `.claude/settings.json`. A green `check-careful.test.sh`
   is **not** evidence your host enforces anything — that mistake is why this guard shipped inert
   for 2.5 months. After registration `careful.json` is guarded: adapt it *before* this step.
9. **Feature 001, the walking skeleton** ([PHASE-0](model/PHASE-0.md) §7): the thinnest real
   capability through every layer, under an approved spec like any other code. Its tasks wire
   every slot in `gates/chain.conf` (a command, or `NA: <reason>`), and its last tasks run
   `python3 factory/bin/adopt.py --install-git-hook --ci github`.
10. From then on: **no commit on red.**

### 2.3 What each step leaves, checked on this release

- **Step 1 before step 2.** `git submodule add` outside a repository fails with
  `fatal: not a git repository`.
- **Step 2: a submodule, or a copy without `.git` — never a clone left as it is.**
  `git clone … factory` inside the project makes `factory/` an embedded repository: `git add`
  records a pointer with no `.gitmodules` entry, every other clone gets an empty `factory/`, and
  `git submodule update --init` cannot repair it. `adopt.py` warns and prints both fixes. The
  one alternative to a submodule is a **vendored copy** with no `.git` inside it, e.g.
  `git clone --depth 1 --branch v1.4.0 <kit-url> factory && rm -rf factory/.git`; you then
  upgrade by replacing the directory.
- **Step 4.** Without `--force`, `specify init --here` stops in a non-empty directory to ask for
  confirmation, and with no terminal to answer it exits 1. Under a terminal it also asks for the
  script type and waits (it hung until killed under a pseudo-terminal); `--non-interactive`
  takes the default, `sh`. Without `--ignore-agent-tools` it exits 1 when `claude` is not on
  PATH (desktop or IDE-only users), `--non-interactive` or not.
  With `--force` after `adopt.py`, specify-cli 1.0.12 changed none of the files `adopt.py` had
  written — `.specify/memory/constitution.md` ("existing file preserved"), `.claude/CLAUDE.md`,
  the rules, hooks and gates, and `.specify/templates/overrides/` — and only added its own
  (`.claude/skills/speckit-*`, `.specify/scripts/`, `.specify/templates/`). It also prints
  *"Consider adding .claude/ (or parts of it) to .gitignore"*: **do not** — `.claude/` holds the
  harness and the guard, and they are versioned. `specify` lands in uv's tool directory; if the
  shell cannot find it, `uv tool update-shell`.
- **Step 8.** Until a remote exists, `.git` is the only copy of the history. Both live probes
  work in a repository with no remote, so a remote is not needed to run them — it is needed
  before the agent works unwatched ([PHASE-0](model/PHASE-0.md) §9).

### 2.4 Teammates, CI and worktrees

A plain `git clone` of the project does not fetch submodules: `factory/` is empty, every link
from `.claude/` into it is dead (about half of all the links in `.claude/`, in a `cli`-profile
adoption), and `adopt.py` is missing. Clone with
`git clone --recurse-submodules <url>`, or run `git submodule update --init` after a plain clone.
`git config submodule.recurse true` makes a later `git pull` move `factory/` to the commit the
project records; without it, a pull that brings a kit upgrade leaves `factory/` on the old
commit, shown as ` M factory` — commit that and you have undone the upgrade. (That setting does
not apply to `git clone`.) A `git worktree add` checkout — Claude Code's `--worktree` sessions
create theirs under `.claude/worktrees/` — starts with an empty `factory/` too: run
`git submodule update --init` in it. CI checks out with submodules: the job `adopt.py --ci
github` installs does (`submodules: recursive`).

**The pre-commit gate is per clone.** `adopt.py --install-git-hook` sets `core.hooksPath`,
which git keeps in the clone's own `.git/config`, never in the repository. Every clone and
every worktree's first session, once feature 001 has installed the hook, runs
`python3 factory/bin/adopt.py --install-git-hook` once; until then `git config core.hooksPath`
prints nothing and the clone commits on red unrefused (CI still runs the chain).
`adopt.py --check` warns in a clone where the hook is installed but not wired.

### 2.5 Upgrading the kit later

```bash
git -C factory fetch --tags
git -C factory checkout v1.4.1                   # the tag you move to; read its CHANGELOG entry
python3 factory/bin/adopt.py --upgrade           # a human runs this, or approves the guard's ask
```

`--upgrade` replaces kit-owned files you have not modified. Where the kit's source changed, it
writes `<file>.factory-new` beside a kit-owned file you modified and beside every adopter-filled
file (`.claude/CLAUDE.md`, `.claude/rules/*.md`, `.claude/agents/*.md`, the constitution,
`gates/chain.conf`, `careful.json`, `.github/workflows/factory-gates.yml`); it never replaces
those. Then it runs `--check`, which stays non-zero until every `.factory-new` is reviewed:
`diff -u <file> <file>.factory-new`, merge what applies, delete the `.factory-new`. A project
adopted before 1.4.0 has no manifest, so every differing file gets a `.factory-new` and a
printed review list ([DAILY-SYNC](sync/DAILY-SYNC.md) Part B lists what to check on that first
upgrade). If the guard changed, run `bash .claude/hooks/check-careful.test.sh` and the careful
live probes; then commit everything `git status` shows except `*.factory-new`, `factory` pointer
included. If `--check` says `factory/` is *behind* what the project installed, the upgrade was
someone else's and your submodule is stale: `git submodule update --init`, never `--upgrade`. It is a human's step because it replaces the
guard itself: the guard asks when an agent runs it, and denies an agent's file edits to
`.claude/hooks/`. A vendored copy: replace `factory/` with the new release, then `--upgrade`.
Staying current, and upgrading Spec Kit: [`sync/DAILY-SYNC.md`](sync/DAILY-SYNC.md).

## 3. Applying the kit to an EXISTING project (brownfield)

Since 1.4.0 `adopt.py` merges into an existing `.claude/` (1.3.x refused to). The order:

1. **Start from a clean working tree** — commit or stash your own changes. `adopt.py` never
   overwrites a file you wrote, so afterwards `git status` lists exactly what adoption added:
   new files, `.factory-new` siblings, `.gitattributes` (created, or appended with LF rules for
   the installed scripts and gate config, by extension), and one replacement — Spec Kit's
   unfilled constitution scaffold, if `.specify/memory/constitution.md` was still that, becomes
   the kit's seed (`M .specify/memory/constitution.md`). To back out, remove what that list
   shows — delete the new files, restore an appended `.gitattributes`, and
   `git checkout -- .specify/memory/constitution.md` for the scaffold. Do not delete by the
   manifest (`.claude/.factory-manifest.json`): it also lists your pre-existing files that
   adoption kept.
2. **Vendor the kit and adopt** — §2.2 steps 2 and 3. Per file: a missing file is installed; an
   identical one is left alone; a differing one stays yours, with the kit's version beside it as
   `<file>.factory-new`. `.claude/settings.json`, `.claude/settings.local.json` and Spec Kit's
   `.claude/skills/speckit-*` are never touched. A filled `.specify/memory/constitution.md` is
   kept (the kit's seed is offered as a `.factory-new`); Spec Kit's unfilled scaffold is replaced.
3. **Spec Kit.** Not installed yet: §2.2 step 4. Already installed: do not re-run init; if its
   `.specify/init-options.json` shows a version other than 1.0.12, follow the Spec Kit upgrade in
   [DAILY-SYNC](sync/DAILY-SYNC.md).
4. **Resolve every `.factory-new`** (`diff -u`, merge, delete). `adopt.py --check` is red until
   none remain.
5. **One always-loaded context.** A root `CLAUDE.md` and `.claude/CLAUDE.md` are both project
   instructions, and Claude Code concatenates them — two files that can disagree. Merge the root
   one into `.claude/CLAUDE.md` and delete it. A root `AGENTS.md` stops loading once any
   `CLAUDE.md` exists; `adopt.py` warns, and the comment at the top of `.claude/CLAUDE.md` says
   how to import it.
6. **Constitution** — Phase 0 §6 applies, but the interview is about what the team already
   believes and what the code already enforces; the product exists.
7. **Legacy docs** — inventory by **code-anchor count**
   (`grep -rn "docs/" --include='*.<lang>'`), then absorb them into `specs/` using
   [`model/RETROFIT-PLAYBOOK.md`](model/RETROFIT-PLAYBOOK.md). Never move or delete a doc before
   its anchors are repointed **in the same commit**. Existing `specs/` need the frontmatter at
   line 1 ([SPEC-FLOW](model/SPEC-FLOW.md)) before the spec gates go green; GATES §7 "Upgrading
   from 1.3.x" covers the migration.
8. **Guard and chain** — §2.2 step 8, then the first spec wires `gates/chain.conf` to the
   commands the project already has and installs the hook and CI, as feature 001 does.

A project that adopted 1.3.x is an upgrade, not a brownfield adoption: §2.5.

## 4. After adopting: audit that the machine agrees with itself

Adoption is not done when the files are copied — it is done when **no two loaded sources give
opposite instructions**. Within a day of adopting (and after every process change), start with
`python3 factory/bin/adopt.py --check` — manifest drift, dead links, frontmatter position, line
endings; it writes nothing — then run a four-lens self-audit; on a real production adoption this
caught two HIGH conflicts on day one:

1. **Redundant/dead files** — anything the new process orphaned (measure code anchors + inbound
   links; re-measure old "safe to delete" lists — files GAIN anchors over time).
2. **Cross-file consistency** — walk every ALWAYS-LOADED file (context, rules, constitution):
   do they all describe the SAME entry point for a new feature? The classic failure: a legacy
   rule file still mandating the old artifact (e.g. "write the tech doc into docs/") while the
   constitution says spec-first — a fresh agent follows whichever it read last.
3. **Agent/skill routing** — for each canonical prompt ("new feature", "fix bug", "review",
   "migrate schema", "e2e acceptance"), exactly ONE skill/agent must claim it; the kit's own
   answer is the "Who claims each canonical prompt" paragraph in
   [NON-FEATURE-WORK](model/NON-FEATURE-WORK.md). Legacy skills must be rewritten as
   *discipline INSIDE the new flow*, never left claiming the entry role.
4. **Spec corpus shape** — mandatory sections present, frontmatter at line 1 (the roadmap view
   and three gates read it: `check-plan-sync.sh`, `check-spec-approval.sh`,
   `check-spec-numbers.sh`), every acceptance test filter matches ≥1 real test (vacuous green),
   quantified debts RE-MEASURED (a debt that grew since it was recorded escalates).

## 5. The seven things you never do

1. Never write code — scaffolding included — before its spec is approved (`status: approved`,
   `approved_by`, `approved_on`; the constitution's HARD-GATE).
2. Never claim "done" — run `./gates/run-chain.sh` and paste its output. A test filter (e.g.
   `-run` / `--grep`) matching zero tests is a **vacuous green**, check for it.
3. Never accept your own or a subagent's report as evidence — re-run the gates yourself and
   spot-check cited `file:line` against real code.
4. Never accept your own work, and never accept with a privileged account that bypasses
   authorization wherever the product has an authorization boundary — acceptance is someone
   other than the builder, recorded in `acceptance.md` ([`gates/GATES.md`](gates/GATES.md) §3).
5. Never call a capability done when its user cannot reach it through the product's real entry
   point (the constitution's Article V: the real UI, the installed command, the public API) —
   record the gap as an explicit task; ask **"who will CALL this?"**
6. Never keep two sources of truth for the same fact. One owner file; everything else points.
7. Never settle a code-vs-spec disagreement by assumption. When code and spec disagree, find out
   which one moved. If the spec states intended behaviour the code does not deliver, the code is
   wrong: record a new task (converge). If the code reflects a deliberate, owner-approved change
   the spec never recorded, fix the spec with the correction marked (≠old) and a dated
   Clarifications entry. If you cannot tell, ask the owner.

## 6. When you and the human disagree

State your concern once, with evidence. If the human reaffirms, follow their decision and record
it (constitution amendment or spec clarification, dated). You are the engine; they are the owner.
