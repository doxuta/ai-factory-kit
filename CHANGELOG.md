# Changelog

All kit updates land here via the [daily-ship sync](sync/DAILY-SYNC.md) — one entry per sync,
newest first.

## 2026-09-29 — v1.4.0 (from an idea, for more than one kind of product — and the gates ship)

A readiness assessment asked one question of v1.3.2: *can this kit take any project from an
idea to shipped?* **87 agents** — six thematic dimensions, two end-to-end simulations from an
empty directory (a clinic-booking web app and a Python CLI over bank CSVs), one completeness
critic — with every finding put to independent verifiers (two for each major or blocker, a
tie-breaker on disagreement). **48 findings, none refuted outright**; filed as 2 blockers, 25
majors, 21 minors, and after verification **0 blockers**, 22 majors, 26 minors: the CRLF
blocker (F1) did not reproduce under the MSYS2-patched bash Git for Windows runs hooks with. The
verdict: *every project* — `not-ready`; *from an idea* — `usable-with-gaps`. Both simulations
reached GATE GREEN, but the kit had packaged one archetype (multi-tenant web SaaS) as if it
were universal, shipped one of the seven gates it describes, and had no upgrade path: the CLI
run needed **228 lines of kit adaptation for 204 lines of product**. This release answers all
48, built by seven file-disjoint workstreams against one written contract, then integrated.

- **The gate chain is a program now, not a paragraph.** `gates/run-chain.sh` runs the slots of
  `gates/chain.conf` in order — format, static, test, build, orphan-endpoints, acceptance,
  doc-sync, spec-approval, spec-numbers — stops at the first red, and exits 2 on a malformed
  file. `TODO` is red and prints "not wired"; `NA: <reason>` needs its reason and prints it
  every run; an all-N/A chain is refused. New gates, each with a BLIND TO block and a test in
  both directions: `check-spec-approval.sh` (a ticked task on a draft spec; `approved` without
  `approved_by`/`approved_on`; `accepted` without an acceptance record), `check-spec-numbers.sh`
  (two specs with one number — reproduced with real Spec Kit 1.0.12 on two merged branches),
  both reading specs through the same parser as doc-sync, and a stack-neutral
  `check-orphan-endpoints.sh` configured per project.
  `check-plan-sync.sh` gains spec-corpus mode as its no-argument default; before, it was red on
  a fresh project or green without checking anything. `hooks/pre-commit` and a CI job enforce
  the chain once feature 001 has wired it. One lesson paid for on the way, now in GATES §6: a
  pre-commit hook in a linked worktree receives `GIT_DIR` and `GIT_INDEX_FILE`, and a slot whose
  tests built a scratch repository committed into the outer one and set `core.bare=true` on it.
- **Specs carry a record the gates can read.** Real YAML frontmatter at line 1 (`feature`,
  `status`, `epic`, `approved_by`, `approved_on`); the lifecycle draft → approved → accepted →
  released, plus superseded; and `specs/<id>/acceptance.md`, written by someone other than the
  builder. Spec Kit template overrides (`speckit/overrides/`) put the frontmatter and required
  test tasks into what `/speckit-specify` and `/speckit-tasks` generate — before, Spec Kit's
  defaults won and specs had no frontmatter at all. In an adopted project the resolver returns
  the override byte for byte; one live run of each command kept both.
- **`bin/adopt.py` rewritten: merge, upgrade, audit.** It merges into an existing `.claude/`
  (1.3.x refused one) and never overwrites a differing file (`<file>.factory-new` instead); a
  manifest separates kit-owned from adopter-filled files, so `--upgrade` replaces only what you
  never touched; `--check` audits drift, links, frontmatter, line endings and — added in
  integration — `chain.conf` syntax; nine archetype profiles drop the rules that do not apply;
  `--register-guard`, `--install-git-hook` and `--ci github` do the wiring. (The agents'
  INVARIANTS blocks and the installed CI job, which the adopter fills, count as adopter-filled
  since the review round below.) It refuses to
  install an agent, rule or skill whose frontmatter is not at byte 0: in v1.3.x all four agents
  loaded as documentation, not subagents, and every rule loaded in every session. Integration
  also made it emulate Claude Code 2.1.284's frontmatter parser, which ends the block at the
  first `---` anywhere — the first draft of this release's rules had one in a comment.
- **The careful guard was rebuilt, because v1.3.2's deny tier had holes.** Tested before the
  rewrite, `rm -rf /` returned `{}` (allow) inside `if … then … fi`, a subshell, a function
  body, `$(…)`, a heredoc fed to `bash`, and `echo "…" | sh`; a 129-character `base64` line took
  69 s against a 10 s hook timeout, and a timed-out hook blocks nothing. The regex matcher is
  replaced by a lexer for bash and one for PowerShell. Deny now covers every tool and shell form
  of writing, moving or deleting the guard's files, the gate scripts and Claude Code's managed
  settings, after path normalisation; raw block-device writes and eFuse burns; and recursive
  delete of `.git` or `.specify` in a repository with no remote. New asks: cloud and IaC
  teardown, warehouse SQL, ORM resets, publish, `--no-verify`, `core.hooksPath`, `adopt.py
  --upgrade`. `careful.json` adds project rules and can remove none, and a typo in it turns
  every pass into an ask instead of quietly dropping a rule. The registered command fails
  closed. Integration closed one more hole: `harness/settings.json.template` was editable while
  `adopt.py --register-guard` is allowed, so one edit plus one allowed command could rewrite the
  guarded `settings.json`; the template is now guarded (5 rows; removing the rule fails 3). The
  test table grew from 142 to **722 rows** (550 at integration, 63 added in the first review
  round and 109 in the second), hermetic (it builds its own repos, so it passes on any branch or
  detached `HEAD`), plus 1,680 generated variants that must stay deny, 480 of them with
  abbreviated long options — the generator's first run found three escapes, fixed. Its
  false-positive corpus: **395 ordinary commands, 0 interrupted**. Replaying the 2,002 unique
  shell commands from the sessions that built this release (measured before the review rounds):
  v1.3.2 interrupted 165 (8.2%), v1.4.0 interrupts 89 (4.4%), every one by a designed rule. The
  cost: about 75 ms per call, up from 48.
- **The kit stops assuming one kind of product.** The constitution template keeps Articles
  I–VII but gains an "Adapting at ratification" block (what is fixed, what is a slot, what may
  be N/A with a dated reason — never deleted), Article V becomes the product's real entry point,
  and Article VI splits into three always-clauses (gates decide done, tests first, acceptance by
  a non-builder) and a conditional one (least privilege, where there is an authorization
  boundary). New: `constitution/vision-template.md`; `model/PHASE-0.md`, from an idea to feature
  001, the walking skeleton that wires the chain; `model/ARCHETYPES.md`, 12 archetypes, each
  with its profile, slot choices, chain N/A reasons, `careful.json` additions and release gate;
  `model/NON-FEATURE-WORK.md`, lanes for bugs, hotfixes, security, refactors and chores,
  spikes, and releases. A second worked example, `examples/budget-cli/` (a single-user CLI,
  accepted from a fresh clone); `examples/todo-api/` regenerated in Spec Kit's real formats, its
  context file renamed `CLAUDE.example.md` — as `.claude/CLAUDE.md` Claude Code loaded it into
  the adopter's session as project instructions.
- **Doctrine made consistent.** One wording for code-vs-spec disagreements, verbatim in 10
  files (the kit gave opposite remedies before); SPEC-FLOW's claim that Spec Kit's pipeline
  pauses for approval corrected (only under `specify workflow run`; otherwise the spec-approval
  gate enforces it); HARNESS §7 states which hosts and platforms are tested and what each other
  host needs ported.
- **Hygiene.** `.gitattributes` pins LF (an `autocrlf=true` clone now yields a working hook
  shim; the v1.3.2 control exits 2); a kit CI runs every test, the link check and the examples'
  spec gates on Linux and macOS, as checked out and detached — its first macOS run (072be93)
  failed: BSD `seq 5 4` counts down where GNU prints nothing, so a plan-sync fixture grew two
  phantom rows, which the Linux build of bash 3.2 had not caught; fixed in db0d296, after which
  all four jobs passed; `THIRD_PARTY_NOTICES.md` carries
  the upstream copyright lines, checked against each LICENSE; `VERSION`. One deviation from the
  plan: `specify init` gets `--non-interactive`, because under a pseudo-terminal it waited at
  "Choose script type" until killed.

**Review fix round (same day).** Three adversarial reviews and three end-to-end runs of this
release (a Go library from an empty directory with real Claude Code 2.1.284 headless sessions,
a web regression, a v1.3.2 → 1.4.0 upgrade with brownfield merges and teammate clones) filed
**42 findings: 13 majors, 29 minors, no blocker. 41 fixed, each reproduced first and pinned by
a test where code changed; 1 deferred** (tagging v1.4.0 and publishing its GitHub Release, a
maintainer step after merge). The ones that change behaviour:
- *The guard.* Abbreviated long options ran as the full option while every rule returned `{}`
  — `rm --recurs --forc ~`, `git push --delet origin main`, `git commit --no-verif`,
  `adopt.py --upg`; the rules now read options the way getopt_long, git and argparse do, and
  `adopt.py` accepts no abbreviation. The CI job `--ci github` installs could be edited, `git
  rm`-ed or overwritten with `{}` while an edit to `chain.conf` asked; it now asks, as do edits
  to `.git/config` and `.git/hooks/*`. An emptied shim exited 0 with no output — no decision,
  so a silent pass; the registered command now also blocks when the shim prints no JSON (re-run
  `--register-guard`). `find`-based `__pycache__`/`*.pyc` cleanup is silent, like `rm -rf
  __pycache__`.
- *adopt.py.* `--check` fails on a guard or gate script that differs from the kit's (a kept
  v1.3.2 matcher, an emptied shim and a brownfield gate that shadowed the kit's all passed with
  a warning), on a script without its execute bit on disk or in the index (a `.factory-new`
  taken by `mv` silently disabled the pre-commit hook; `.factory-new` of a script is now
  executable), and on a `factory/` older than what the project installed — a teammate's stale
  submodule, where `--upgrade` used to reinstall the older guard with a green `--check`; now
  `adopt.py` refuses there unless `--upgrade --allow-downgrade`. It warns on a clone whose
  `core.hooksPath` is not wired and on unfilled placeholders, and on a deleted CI job or hook
  (the second round below made that a failure). The appended `.gitattributes` rule `gates/**
  text eol=lf` rewrote the CRLF bytes inside every binary under `gates/` (a PNG's signature);
  the rules are now by extension (since the second round, the hook by name), and an earlier
  block is replaced. The constitution override's links are written for `.specify/memory/`, where
  `/speckit-constitution` copies them (one run had left 18 dead links). `--check` no longer runs
  a `run-chain.sh` the kit did not write, `.claude/settings.json.template` is no longer
  installed, a profile change is no longer blamed on the kit, a pristine v1.3 duplicate of the
  guard is recognised by `factory/`'s history, a rule without frontmatter is valid, and `--ci
  github` refuses in a project below the repository root, where GitHub would never read the job.
- *The spec gates.* `check-plan-sync.sh` read a 1.3.x `| ⬜ | M1-T2 |` table as no tasks, so a
  shipped spec with an open row was green in both gates; those rows are now tasks (with a
  warning to convert), and a task-less `tasks.md` past draft is red. `check-spec-approval.sh`
  is red on an open `[NEEDS CLARIFICATION]` marker in a spec past draft.
- *Doctrine.* "No commit on red, no exceptions" in six loaded files contradicted PHASE-0's
  feature-001 bootstrap; the exception is now defined once, in GATES §1, and every other
  statement points to it. Nothing a planning session loads named the kit's hook and CI
  installer, and both of a reviewer's `/speckit-plan` runs invented `.githooks/` and a workflow;
  `CLAUDE.md`, the tasks override and `plan-and-tdd` now name
  `adopt.py --install-git-hook --ci github`, and a bare `/speckit-plan` run after the fix
  planned exactly that. Every teammate document now says each clone runs `--install-git-hook`
  once. The support envelope said "Tested" on macOS and WSL with no run behind either; it now
  says what ran: CI on Linux and macOS, headless Claude Code on Linux, nothing on WSL or
  Windows. Smaller fixes: the release-notes script printed nothing on a first release; the
  agents' INVARIANTS copy and the vision template left dead links; Prettier's ignore list
  omitted `specs/`; a Go line for the library archetype; stale counts; release-step order.
The integration numbers below are from before this round; after it, 8 suites, **1,312 checks,
0 failed** — adopt 402, careful 613, plan-sync 97, spec-approval 65, run-chain 56,
orphan-endpoints 45, spec-numbers 21, metrics 13 — on Linux under bash 5.2 with Python 3.11
and again under bash 3.2.57 with Python 3.8. Kit links: 62 files, 445 relative links, 0 dead. A
fresh smoke adoption of this tree as a submodule tagged v1.4.0 (`--profile cli`, then real
`specify init`): `--check` clean; after `--register-guard`, `rm -rf ~` and `rm --recurs --forc ~`
denied, `git commit --no-verif` and an Edit of the CI job asked, the dry-run probe passed; the
hook refused a commit on the red chain; a `--recurse-submodules` clone warned until it ran
`--install-git-hook`; an emptied shim blocked with exit 2 and failed `--check`.

**Second review round (same day).** A second adversarial pass on the guard and a second
whole-kit pass — which re-ran the evidence for all 13 first-round majors, found one of them (the
CI job) only partly closed, and took a new archetype, a Data/ML pipeline, from an idea to a green
chain and an accepted spec — filed **8 findings: 2 majors, 6 minors. All 8 reproduced and fixed,
none rejected, none deferred;** the seven that changed behaviour are pinned by tests that fail on
the first-round tree, and the eighth (rows for deny shapes that already held) by rows that keep
them.
- *Force beats a lease.* `git push --force-with-lease --force origin main` (or `-f
  --force-if-includes`) was asked, with a reason saying it "refuses if the remote moved",
  instead of denied — and git 2.43 overwrote a remote a teammate had moved, because plain force
  defeats the lease. Plain force or a `+refspec` now decides, whatever lease sits beside it;
  `--force-with-lease` alone still asks, and `--force-if-includes` alone, a no-op, passes.
- *The CI job went with its directory.* `git rm -r .github`, `mv .github …`, `git mv
  .github/workflows …` and `git restore --source=HEAD~5 .github` returned `{}`; the commit
  passed the hook, CI stopped running the chain, and `adopt.py --check` said OK with a warning.
  A directory holding the job now asks too — `git rm`/`mv`/`checkout`/`restore`, `mv`,
  `rm -r`, `cp -r`, `rsync`, `tar -C`, `find -exec`, PowerShell `Move-Item`/`Remove-Item` — on
  disk evidence, so a `.github` without the job stays silent; and `--check` fails while the job
  is gone, unless another workflow runs `gates/run-chain.sh`.
- *Minors.* Any directory named `gates` was the gate chain: editing, moving or restoring
  feature-flag code under `src/gates/hooks/` drew 12 denies and 1 ask across 16 ordinary
  commands, and `careful.json`, additive only, could not relieve it. The chain is now the
  project's `gates/`, a `gates/` holding `run-chain.sh` (the kit copy), or one the matcher cannot
  look at (a relative `gates/…`, a path built at runtime); `git -C` pathspecs are resolved
  against the `-C` directory, and pathspec magic (`:/gates`) against the path it names.
  `core.hooksPath` could be dropped through `git --config-env`, `git config
  --remove-section`/`--rename-section core`, `git config --edit` or an `include.path`
  (`--config-env`, `--remove-section` and `include.path` each landed a red commit when
  measured); all ask now. `git update-index --chmod=-x` on the pre-commit hook passed while
  `chmod -x` was denied, and every later clone ignored the hook; `--chmod` other than `+x` and
  `--cacheinfo` on a guarded file are denied, `--assume-unchanged`/`--skip-worktree` on a gate
  file asks. The appended `.gitattributes` kept one directory rule, `gates/hooks/*`, which
  rewrote a PNG there; the hook is pinned by name and the earlier block is replaced.
  ARCHETYPES' CLI tag rule asked on a branch named `v2-api-cleanup`; it now needs
  `v<digits>.<digits>`, and the guard's table loads every `careful.json` stanza in ARCHETYPES
  and checks that rule both ways. Eight deny shapes SKILL.md documents (`chown`, `chgrp`,
  `chattr`, `setfacl`, `shred`, `vi`, `nano`, `git mv` on a guarded file) had no row; each has
  one now, with an allow row beside it.
After it, 8 suites, **1,432 checks, 0 failed** — adopt 413, careful 722, plan-sync 97,
spec-approval 65, run-chain 56, orphan-endpoints 45, spec-numbers 21, metrics 13 — on Linux
under bash 5.2 with Python 3.11 and again under bash 3.2.57 with Python 3.8. Against the
first-round tree the new tests fail: 53 table rows and the corpus check (7 commands), 2
ARCHETYPES checks, 10 adopt checks. The guard reviewer's own 462-command corpus: 12 denies
before, none after (its 2 designed asks remain). Kit links: 62 files, 445 relative links, 0
dead. A fresh smoke adoption of this tree as a submodule tagged v1.4.0 (`--profile cli`, real
`specify init`): `--check` clean; after `--register-guard`, `rm -rf ~` and `git push
--force-with-lease --force origin main` denied, `git mv src/gates src/feature_gates` and an
Edit under it passed, the dry-run probe passed; after `--install-git-hook --ci github` the hook
refused a commit on the red chain; `git rm -r .github` asked, and once a human committed it,
`--check` failed until `--ci github` reinstalled the job.

**Measured in the integration pass.** 8 suites, **1,140 checks, 0 failed** — adopt 309,
careful 550, plan-sync 89 (its original 8 rows unchanged), spec-approval 57, run-chain 56,
orphan-endpoints 45, spec-numbers 21, metrics 13 — under bash 5.2 with Python 3.11 and again
under bash 3.2.57 with Python 3.8; the same on a detached clone. Kit links: 62 files, 433
relative links, 0 dead. A from-idea smoke adoption of this tree as a submodule tagged v1.4.0:
`adopt.py --profile cli` installed 38 files; `specify init --force` changed none of them;
`--check` clean; `--register-guard` twice gave a byte-identical `settings.json`; through the
registered command, `rm -rf ~` and `rm .claude/hooks/check-careful.sh` denied, `ls` passed,
`git commit --no-verify` asked, and the pre-commit hook refused a commit on the red chain.
Changed test expectations, each deliberate: careful's `/etc` rows moved to `/srv` (`/etc` holds
managed settings, so deleting it is now deny); `tee` onto an ordinary file is now silent; an
`adopt.test.sh` fixture that filled `chain.conf` by appending a second `format:` line — a file
the runner rejects — now fills the `TODO` line.

**Adopters — action required:** a human runs these (from 1.4.0 on the guard asks when an agent
runs `--upgrade`; the v1.3.x guard you have installed does not).
```bash
git -C factory fetch --tags && git -C factory checkout v1.4.0
python3 factory/bin/adopt.py --upgrade --profile <p>   # your profile: no manifest yet, so the
                                            # kit cannot know which rules you dropped. Every
                                            # differing file becomes a .factory-new, with a
                                            # review list; nothing replaced
# for each: diff -u <file> <file>.factory-new, merge, delete the .factory-new. Take
# .claude/hooks/check-careful.py and .sh WHOLE and move any local rule into careful.json:
# a kept v1.3.x matcher fails --check (and passes the live probes, which is why they are not enough)
python3 .claude/hooks/check-careful.py --check-config   # after adapting .claude/hooks/careful.json
bash .claude/hooks/check-careful.test.sh                # the whole table, in your project
python3 factory/bin/adopt.py --register-guard           # new matchers and the fail-closed command
python3 factory/bin/adopt.py --check                    # exit 0 before you commit
```
Then re-run the careful live probes (SKILL.md, "Verification") and commit everything
`git status` shows except `*.factory-new`. Add the frontmatter to existing specs and
`acceptance.md` to shipped ones, and convert `tasks.md` tables to `- [ ] T001` lines (GATES §7,
"Upgrading from 1.3.x"); wire `gates/chain.conf`. A v1.3.x constitution saved from the kit's
template has links written for `factory/constitution/`: `--check` names each and its new target,
and re-pointing them is an amendment the owner approves; a constitution kept elsewhere (a root
`constitution.md`) moves to `.specify/memory/`. A bare `check-plan-sync.sh` now reads `specs/`;
the 1.3.x blueprint "understate" check (the `epic_sentinels` map inside it) is gone — if you had
filled it, keep that code as a gate of your own. Once the hook is installed, every clone runs
`adopt.py --install-git-hook` once. **Never pin a tag older than v1.3.0**: v1.0.0–v1.2.0 ship a
guard whose decisions Claude Code ignores.

**Still not covered.** The test suites ran in CI on Linux and macOS (runs 36603702199 and
36603705592, all four jobs green at db0d296), but nothing has run on WSL or on a Windows host,
and no full from-idea adoption has run on a Mac. Native Windows without Git Bash has no guard.
Hosts other than Claude Code need the harness and guard ported by hand; the per-host table comes
from documentation and source, not runs. The guard's two live probes ran in headless Claude
Code 2.1.284 sessions on Linux during review; the rest of its verification is payloads through
its registered command. It cannot see what a script or a formatter run over the whole tree
writes, and a session started below the project root runs without it (per Claude Code's docs).
Reachability gates exist for HTTP routes only. The LLM/ML eval doctrine (GATES §8) is not yet
measured on an adoption. The spec gates prove a well-formed record exists, not that the run
happened. `git merge`, `rebase` and `cherry-pick` skip pre-commit; CI is the backstop. The game
archetype has no profile. No GitHub Release has been published for any tag.

## 2026-09-11 (evening) — v1.3.2 (the guard was interrupting one command in eight)

Replaying **6,638 real shell commands** from 48h of work through the guard: **800 asks**, one
interruption every eight commands. Three of our own rules caused 85% of it — `-i` listed as a
write-flag so **`grep -i`** counted as writing; any redirect onto an absolute or home path
flagged, i.e. `cat > ~/notes.md`; and SQL keywords matching the word "Update" in grep patterns
and in paths like `specs/029-audit-log/`. All three narrowed, plus the matcher now resolves
`VAR=` and `cd <scratch>` declared in the same command. **800 → 77 (12% → 1.2%)**, and the
variable resolution made the guard *stronger* by accident: `R=/ ; rm -rf "$R"` went from ask to
deny. GATES §6 gains the rule this paid for: **a gate's false-positive rate is a safety number**
— one that fires on ordinary work gets dismissed unread, then switched off, which ends exactly
where the inert version did. Table 127 → 142 cases.

## 2026-09-11 (later) — v1.3.1 (a screenshot refuted the doctrine written yesterday)

- **The guard stopped interrupting housekeeping.** Dropping the old `bin`/`tmp` allowlist entries
  was right — written as `*/bin`/`*/tmp`, they swallowed `rm -rf /usr/bin` and `rm -rf /tmp` — but
  it left every `rm -rf /tmp/<scratch>` asking, dozens of times a session. Recursive delete
  strictly INSIDE a temp root now passes silently; the root itself, a `..` segment, or one
  non-scratch target in the same command still stops it. **A guard that cries wolf on routine
  cleanup gets switched off, and then guards nothing** — that is now a design rule here, not an
  afterthought.
- **GATES §6's auto-answer rule was WRONG and is rewritten.** Yesterday's entry stated, from a
  desktop measurement, that a host in skip-permissions mode auto-approves every "ask", therefore
  "only a hard refusal is real". A photograph of the same hook, same host mode, raising a genuine
  *Allow once / Deny* dialog on **mobile** refuted it inside a day. Corrected: **deny is a wall
  everywhere; ask is a wall wherever a human is actually looking** — and the rule now carries the
  method lesson that produced the error, that one surface is not the system. Both consequences
  bind: do not lean on `ask` unattended, and do not scatter it either.
- Test table 116 → 127 cases: five scratch-cleanup cases that must stay silent, six temp-root and
  climb-out cases that must not.

## 2026-09-11 — v1.3.0 (the adoption path was broken; an audit of the kit itself)

An 8-dimension adversarial audit of this repo (129 agents, every finding put through two
independent refuters) returned **23 surviving findings — 3 blockers, 6 majors**. One dimension
came back `not-ready`, seven `usable-with-gaps`, none `solid`. The theme: the doctrine is
sound and the **delivery** was broken. Everything below is fixed, with a runnable check.

- **`bin/adopt.py` (new)** replaces the hand-run copy-and-sed recipe in AI-ONBOARDING §2, which
  was wrong three independent ways: it sed-ed `.claude/CLAUDE.md`, a file the copy never creates
  (hard error on step 2 of 6, every adoption); its single global substitution mangled depth-3
  skill links while never touching depth-1 files — **20 of 82 links dead, silently**; and
  `sed -i ''` is BSD-only. The rule it missed: only the prefix that ESCAPES the harness tree may
  be rewritten, and that depth differs per file. The script rewrites per depth, installs the
  hooks, copies the gate **and its test**, then resolves every link and **exits non-zero if any
  is dead** — README says broken cross-links are bugs, so now the kit proves it. Measured on a
  clean adoption: 82 links, 0 broken.
- **The guardrail is now actually installed.** Nothing in the adoption path mentioned `careful`
  at all (`grep careful AI-ONBOARDING.md` → 0 hits), and the only wiring snippet registered the
  `Bash` matcher alone, so v1.3.0's guard-file tier could never fire. New
  `harness/settings.json.template` carries **both** `PreToolUse` matchers, adopt.py copies the
  hooks, and AI-ONBOARDING gains a step that ends at the skill's two live probes.
- **`gates/check-plan-sync.test.sh` (new)** — 8 cases, both directions. The kit shipped this
  gate with no test while CHANGELOG called it "two-direction-tested"; GATES §6 calls an
  untested gate decoration. Writing it immediately paid: the first fixture put the progress bar
  mid-line, where the gate's `^(M\d+)` cannot see it, so all three RED cases were passing
  **for the wrong reason** — the drift comparison they exist to test never ran.
- **The gate no longer passes vacuously on a wiring error.** A missing or mistyped docs dir
  exited 0, indistinguishable from a clean run, and GATES §1 shows the gate last in an `&&`
  chain that reads exit status only. It now exits 1 and says so; "dir exists, no formatted
  plan" stays green. Its docstring gained the `BLIND TO` block GATES §4 requires of every gate.
- **The `~65%` figure is gone.** Upstream withdrew it as a measured aggregate; the kit repeated
  it *and* added a corroboration of its own that was never measured. GATES §2 — claims are not
  evidence — has to bind the kit's own headline number first.
- **Lineage now credits gstack** (both READMEs), the source of the `careful` matcher and its
  two-tier design, previously missing while the guard it produced is the kit's headline artifact.
- Absorbed from the upstream backlog: caveman gains negation-safety and never-add-words;
  task-orchestra gains no-nested-dispatch and every-owned-file-appears-in-the-diff. HARNESS §4
  and the skills README no longer describe the guard as confirm-only.
- **Two audit findings were themselves wrong and were NOT applied**: README.vi.md does carry the
  graph-not-a-pile rule (README.vi.md:100), and no file assigns the tasks step a number 6 —
  neither README nor HARNESS mentions step numbers at all. The real defect there was a heading
  citing a positional number the SPEC-FLOW table does not carry; it now names the command.

## 2026-09-10 — v1.3.0-dev (the shipped guard was inert; the lesson is bigger than the fix)

The daily routine's second leg — an audit of all 11 upstream repos this kit was distilled from
(1,869 commits since we adapted them, 82 findings) — turned up a defect in **this kit's own
reference guardrail**. It is fixed here, and the two rules it teaches are now in the gate
doctrine.

- **`careful` hook rewritten** (`harness/skills/careful/hooks/`). It printed its decision as a
  top-level `permissionDecision`, which Claude Code drops — so the shipped guard blocked
  nothing, on this kit and on the factory it came from, for 2.5 months, while its own "7/7
  dangerous commands asked" check stayed green the entire time. Upstream gstack shipped and
  measured the identical bug (CHANGELOG `1.64.0.0`: *"deny meant allow"*). Also fixed, each
  reproduced before the change: the detector's lowercase-only `r` class let `rm -Rf /` past;
  the unanchored allowlist let `rm -rf / && rm -rf node_modules`, a `#`-commented twin, and a
  `$(…)` substitution ride the safe list; `bin`/`tmp` entries written as `*/bin`/`*/tmp`
  swallowed `rm -rf /usr/bin` and `rm -rf /tmp`; and `git push origin +main`,
  `git worktree remove --force`, `${IFS}` and `base64 -d | sh` matched nothing at all.
- **New `deny` tier**, covering exactly two shapes (recursive delete of `/` `~` `$HOME`;
  force-push to a protected branch), simple commands only, with a never-commit escape hatch.
  This **amends** the kit's own "warn, never hard-block" rule, and the amendment is recorded
  in the skill rather than quietly applied — see the next bullet for why it had to change.
- **GATES §6 gains two rules**, both paid for by the above: *test the CONSUMER, not just the
  emitter* (both directions of a table prove the bytes, not the enforcement), and *a gate whose
  verdict is auto-answered is not a gate* — the factory host ran `defaultMode:
  bypassPermissions` for every session, so its `ask` tier had never once stopped anything.
- **Then an adversarial audit broke the fixed version too** — six confirmed escapes from the
  new `deny` tier, worst of which (`sudo rm -rf /`) returned a silent `allow`: argv[0] read
  off token 0 so any wrapper hid the command; `; true` appended to anything downgraded the
  verdict; remote-branch **deletion** needs no `--force` and was unguarded; `git -C`'s operand
  posed as the subcommand; the root-target test was `all()` so adding a target softened it;
  and the root set was bare literals, missing `~/*` and `$HOME/*`. Plus exponential backtracking
  in the allowlist (17s against a 10s timeout) and a redirect that let one allowed command
  erase the guard. All fixed; table 63 → 97 cases with every escape family pinned.
- **GATES §6 gains a third rule** from that second round: *a green table proves its rows,
  never its coverage* — and two of those rows had encoded the vulnerability as expected
  behavior, so the correct fix first read as a regression.
- **Third tier: the guard can no longer be switched off.** The hook was wired only to the
  shell tool, so the matcher file — and the settings that register it — could be rewritten by
  the file-editing tool, which no gate watched. Now denied there too, with redirects onto the
  same paths raised from ask to deny. Reading a guard stays allowed (the first draft denied
  it; the table caught that). The interpreter-writes-a-file limit is written into the skill
  rather than papered over.
- **Heredoc bodies are stripped before scanning** — a command whose heredoc merely *contains*
  redirect-shaped text is not performing that redirect. Found when the command installing the
  fix was refused by it; the rest of the heredoc's command line is kept, since that is where a
  real redirect lives.
- **`hooks/check-careful.test.sh` (new)**: 116 cases pinning decision **and** envelope **and**
  the pass-through direction, plus two zero-blast-radius live probes documented in the skill —
  one proving the wall stands, one proving the door still opens.

## 2026-09-01 (night) — v1.2.0 (first ROUTINE-PROPOSED upgrade — the loop closed)

The daily research routine ran end-to-end for the first time, proposed three upgrades, and the
maintainer approved all three ("UPGRADE KIT 1 2 3"). What got smarter:

- **HARNESS §5 (new)**: map of the upstream community-extension catalog (categories docs/code/
  process/integration/visibility, effect read-only/read-write, `specify extension info`) onto the
  3-level model, with a 4-rule selection discipline — incl. the no-two-copies-of-one-duty rule.
- **RETROFIT-PLAYBOOK §1c (new)**: re-measure every number a doc states — scale-creep debts grow
  silently between freeze and retro-fit (observed twice, ~30% growth); file grown debts in the
  same wave with both numbers + a block-new-instances gate where cheap.
- **DAILY-SYNC**: adopter pinning guidance (pin release tags) + upstream release watch
  (`gh api .../releases/latest`, deliberate CLI bumps, re-run the adoption audit after majors).

## 2026-09-01 (evening) — v1.1.0 (first daily-ship sync)

Factory commits absorbed: `a8448782` (36-finding framework audit), `4d725882` (owed dual-review
paid, HIGH found), `47da95e2` (doc-frozen-mid-delivery retro-fit). What got smarter:

- **Constitution template**: Article IV gains the named *RETRO-FIT mode* (brownfield was implicit
  — a real adoption had to amend its constitution on day one to legalize its own first 9 specs).
- **AI-ONBOARDING §4 (new)**: the post-adoption **self-audit** — four lenses that caught two HIGH
  "always-loaded file still teaches the old process" conflicts on a production adoption.
- **RETROFIT-PLAYBOOK §1b (new)**: two more ways docs lie — status tables frozen mid-delivery
  (diff against git log), and **unpaid mandates**: pay the reviews/tests the doc promised itself;
  a review paid two months late found a HIGH exactly there.
- **SPEC-FLOW**: frontmatter is enforced at specify time (the kit's own source repo shipped 9
  specs without it — the roadmap view couldn't run on the kit's own factory).

## 2026-09-01 — v1.0.0 (initial release)

Distilled from the Nexus factory as of commit `c38c2319` (730+ commits; 3 retro-fit batches
absorbing 3 legacy docs into 8 verified specs; constitution v1.0.0 ratified). Ships: the 3-level model, the spec flow,
the retro-fit playbook, a 7-principle constitution template, the executable-gates doctrine with
a two-direction-tested self-globbing doc-sync gate, the harness anatomy with two measured
config-loading traps, four Level-2 agent roles, portable skills, and a worked example project.
