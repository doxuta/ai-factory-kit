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
  `--register-guard`, `--install-git-hook` and `--ci github` do the wiring. It refuses to
  install an agent, rule or skill whose frontmatter is not at byte 0: in v1.3.x all four agents
  loaded as documentation, not subagents, and every rule loaded in every session. Integration
  also made it emulate Claude Code 2.1.284's frontmatter parser, which ends the block at the
  first `---` anywhere — the first draft of this release's rules had one in a comment.
- **The careful guard was rebuilt, because v1.3.2's deny tier had holes.** Tested before the
  rewrite, `rm -rf /` returned `{}` (allow) inside `if … then … fi`, a subshell, a function
  body, `$(…)`, a heredoc fed to `bash`, and `echo "…" | sh`; a 129-character `base64` line
  took 69 s against a 10 s hook timeout, and a timed-out hook blocks nothing. The regex matcher
  is replaced by a lexer for bash and one for PowerShell. Deny now covers every tool and shell
  form of writing, moving or deleting the guard's files, the gate scripts and Claude Code's
  managed settings, after path normalisation; raw block-device writes and eFuse burns; and
  recursive delete of `.git` or `.specify` in a repository with no remote. New asks: cloud and
  IaC teardown, warehouse SQL, ORM resets, publish, `--no-verify`, `core.hooksPath`,
  `adopt.py --upgrade`. `careful.json` adds project rules and can remove none, and a typo in it
  turns every pass into an ask instead of quietly dropping a rule. The registered command fails
  closed. Integration closed one more hole: `harness/settings.json.template` was editable while
  `adopt.py --register-guard` is allowed, so one edit plus one allowed command could rewrite the
  guarded `settings.json`; the template is now guarded (5 rows; removing the rule fails 3).
  The test table grew from 142 to **550 rows**, hermetic (it builds its own repos, so it passes
  on any branch or detached `HEAD`), plus 1,200 generated wrapper variants that must stay deny —
  the generator's first run found three escapes, fixed. Its false-positive corpus: **381
  ordinary commands, 0 interrupted**. Replaying the 2,002 unique shell commands from the
  sessions that built this release: v1.3.2 interrupted 165 (8.2%), v1.4.0 interrupts 89
  (4.4%), every one by a designed rule. The cost: about 75 ms per call, up from 48.
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
  spec gates on Linux and macOS, as checked out and detached; `THIRD_PARTY_NOTICES.md` carries
  the upstream copyright lines, checked against each LICENSE; `VERSION`. One deviation from the
  plan: `specify init` gets `--non-interactive`, because under a pseudo-terminal it waited at
  "Choose script type" until killed.

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
python3 factory/bin/adopt.py --upgrade      # no manifest yet: every differing file becomes a
                                            # .factory-new, with a review list; nothing replaced
# for each: diff -u <file> <file>.factory-new, merge, delete the .factory-new
python3 .claude/hooks/check-careful.py --check-config   # after adapting .claude/hooks/careful.json
python3 factory/bin/adopt.py --register-guard           # new matchers and the fail-closed command
python3 factory/bin/adopt.py --check                    # exit 0 before you commit
```
Then re-run the careful live probes (SKILL.md, "Verification"); add the frontmatter to existing
specs and `acceptance.md` to shipped ones (GATES §7, "Upgrading from 1.3.x"); and wire
`gates/chain.conf`. A bare `check-plan-sync.sh` now reads `specs/`. **Never pin a tag older
than v1.3.0**: v1.0.0–v1.2.0 ship a guard whose decisions Claude Code ignores.

**Still not covered.** No run on a real Mac or Windows host; the macOS and Linux CI jobs have
not yet run on GitHub. Native Windows without Git Bash has no guard. Hosts other than Claude
Code need the harness and guard ported by hand; the per-host table comes from documentation and
source, not runs. The guard was verified by payloads through its registered command, not in a
live Claude Code session; it cannot see what a script or a formatter run over the whole tree
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
