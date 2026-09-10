# Changelog

All kit updates land here via the [daily-ship sync](sync/DAILY-SYNC.md) — one entry per sync,
newest first.

## 2026-09-10 — v1.3.0 (the shipped guard was inert; the lesson is bigger than the fix)

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
- **`hooks/check-careful.test.sh` (new)**: 97 cases pinning decision **and** envelope **and**
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
