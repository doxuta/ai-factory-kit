# Changelog

All kit updates land here via the [daily-ship sync](sync/DAILY-SYNC.md) — one entry per sync,
newest first.

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
