# Changelog

All kit updates land here via the [daily-ship sync](sync/DAILY-SYNC.md) — one entry per sync,
newest first.

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
