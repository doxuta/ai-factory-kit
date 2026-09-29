<!-- WHO READS ME: Part A — the maintainer's daily-ship routine (an AI on a schedule) and anyone
     wondering how fresh this kit is. Part B — every adopter keeping a project current: pinning,
     upgrading the kit, upgrading Spec Kit, and keeping its own Level-0 files true.
     I POINT TO: ../CHANGELOG.md (where releases land; its "Adopters" lines) ·
     ../model/RETROFIT-PLAYBOOK.md (the method syncs reuse) · ../.github/workflows/ci.yml (the
     kit's own gate) · ../bin/adopt.py (--upgrade, --check) · ../AI-ONBOARDING.md (§2.5, §4) ·
     ../harness/skills/careful/SKILL.md (the live probes) · ../speckit/README.md (the overrides) ·
     ../model/LEVELS.md (owner + trigger for every Level-0 file). -->

# Daily-Ship Sync — how this kit stays current, and how you stay current with it

Two readers, two parts. **Part A** is the maintainer's routine: how improvements reach the kit.
**Part B** is yours if you adopted the kit: how they reach your project. Until 1.4.0 this file
told adopters to "`git pull` when you want the latest lessons". That moved `factory/` and
nothing else: the hooks, gates, agents and rules that actually run are copies in `.claude/` and
`gates/`, and they stayed old. A v1.2.0 adopter who followed that advice kept a guard that
blocked nothing (readiness audit F2).

## Part A — How the maintainer keeps the kit current

This kit is distilled from a **living production factory** (the Nexus platform, a private
repository). When the factory's harness improves, the improvement flows here on the
maintainer's daily-ship routine, not "when someone remembers". Steps 1–2 read that private
repository; they are described so you can judge the process, not for you to run.

### The factory leg

1. **Diff the sources of truth** since the last sync recorded in
   [`../CHANGELOG.md`](../CHANGELOG.md): the factory's `.claude/` (rules, skills, agents),
   `.specify/memory/constitution.md`, its gate scripts and its campaign log.
   ```bash
   git -C <factory-repo> log --oneline --since="<last-sync-date>" -- .claude/ .specify/ <gates-dir>/
   ```
2. **Classify each change**: `portable` (a lesson any project benefits from) vs `factory-only`
   (stack- or product-specific). Only `portable` syncs. When unsure, it is factory-only.
3. **Apply with the retro-fit discipline** ([playbook](../model/RETROFIT-PLAYBOOK.md)): verify
   the lesson against the kit's current text, update every cross-linked file **in one commit**,
   keep the file-header link maps true.
4. **Record**: one `CHANGELOG.md` entry per release — date, factory commits absorbed, files
   touched, one line on what got smarter, and, from 1.4.0 on, a line an adopter can act on
   without reading the rest:
   ```text
   **Adopters — action required:** none.
   **Adopters — action required:** python3 factory/bin/adopt.py --upgrade; review the
   .claude/rules/*.factory-new it offers; re-run the careful live probes.
   ```
   Any entry that changes `harness/`, `gates/`, `bin/`, `speckit/` or `constitution/` needs at
   least the `--upgrade` step; one that moves the tested Spec Kit version names the Part B
   Spec Kit steps too.
5. **Gate** — executable, not prose. The kit's CI ([`ci.yml`](../.github/workflows/ci.yml))
   runs on every push and pull request: no CRLF in tracked files, every tracked `*.test.sh`,
   `python3 bin/check-links.py .`, and the three spec gates on each worked example — once as
   checked out and once on a detached `HEAD` (in v1.3.2 one test read the caller's branch and
   failed 141/142 on every feature branch, and nothing ran it there), on Linux and on macOS
   under the system `/bin/bash` 3.2. Before pushing, the same locally:
   ```bash
   fail=0
   for t in $(git ls-files '*.test.sh'); do
     bash "$t" >/dev/null || { echo "FAIL $t"; fail=1; }
   done
   python3 bin/check-links.py . && [ "$fail" = 0 ] && echo "gate green"
   ```
6. **Release**: bump [`../VERSION`](../VERSION); write the CHANGELOG entry; move the pinned-tag
   example in the docs (`grep -rn 'v1\.4\.0' --include='*.md' .`); tag, push the tag, and
   publish a GitHub Release from it, so `gh api repos/doxuta/ai-factory-kit/releases/latest`
   answers:
   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z
   gh release create vX.Y.Z --verify-tag --title vX.Y.Z --notes-file <the CHANGELOG entry>
   ```
   (On 2026-09-29 the repository's Releases page still read "There aren't any releases here"
   for tags v1.0.0–v1.3.2.)

### The research leg

Mirroring the factory is only half the job. A second daily pass looks OUTWARD and forward:

1. **Upstream watch** — new [github/spec-kit](https://github.com/github/spec-kit) releases or
   command changes worth absorbing (`gh api repos/github/spec-kit/releases/latest`). Moving the
   kit's **tested** Spec Kit version is a release of its own: install the new version in
   isolation (`UV_TOOL_DIR=… UV_TOOL_BIN_DIR=… uv tool install specify-cli==X.Y.Z`); run a
   from-idea adoption (`adopt.py`, then
   `specify init --here --force --non-interactive --integration claude`, then
   `adopt.py --check`) and a brownfield one, once without a terminal and once under one;
   compare the new upstream templates with [`speckit/overrides/`](../speckit/overrides/); then
   change `TESTED_SPECKIT` in
   `bin/adopt.py` and every `1.0.12` in the docs (`grep -rn '1\.0\.12' .`).
2. **Adopter feedback** — new issues/PRs/stars on this repo; every real adopter question is a
   candidate doc fix.
3. **Self-check** — the gate in step 5 still passes on a clean clone.
4. **Proposals, not stealth edits** — the routine posts 2–3 concrete upgrade proposals (with
   S/M/L effort) to the maintainer; changes land only after approval, through the same commit
   discipline as everything else. "Nothing worth doing" is a valid, honest report.

## Part B — How an adopter stays current

The commands below were run on Linux against this release's `adopt.py`, with a local copy of
the kit tagged as the release and specify-cli 1.0.11 → 1.0.12 under uv 0.8.17.

### Pin a release tag

A submodule records one commit of the kit; pin it to a release tag, not a moving branch:

```bash
git -C factory fetch --tags
git -C factory tag                          # or: git ls-remote --tags <kit-url>
git -C factory checkout v1.4.0 && git add factory
```

**Never pin a tag older than v1.3.0.** At v1.0.0–v1.2.0 the careful hook printed its decision
in a shape Claude Code ignores, so the guard blocked nothing; there is no `adopt.py`; and the
adoption recipe was the hand-run copy-and-`sed` one, which left 20 of 82 links dead. v1.3.x
works, but a v1.3.x adoption moves forward only through 1.4.0's `adopt.py --upgrade` (below).
The kit follows semver-ish discipline: fixes bump PATCH, content additions MINOR, breaking
restructures MAJOR.

### Upgrade the kit

Read the CHANGELOG entries between your tag and the target first — each one from 1.4.0 on ends
with an **Adopters — action required** line. Then:

```bash
git -C factory fetch --tags
git -C factory checkout v1.4.1                     # the target tag
python3 factory/bin/adopt.py --upgrade             # a human runs this, or approves the guard's ask
```

`--upgrade` sorts every file it installed:

| File | Unmodified since install | Modified by you |
|---|---|---|
| **kit-owned** — hooks, gates and their tests, agents, skills, `HARNESS.md`, the overrides | replaced | kept; when the kit's version changed, it is written beside yours as `<file>.factory-new` |
| **adopter-filled** — `.claude/CLAUDE.md`, `.claude/rules/*.md`, `.specify/memory/constitution.md`, `gates/chain.conf`, `.claude/hooks/careful.json` | never replaced; a `.factory-new` when the kit's source changed | never replaced; a `.factory-new` when the kit's source changed |

It then runs `adopt.py --check`, which exits non-zero while any `.factory-new` is waiting. For
each: `diff -u <file> <file>.factory-new`, merge what applies, delete the `.factory-new`. Then:

1. `python3 factory/bin/adopt.py --check` exits 0. If it reports the guard registration as
   stale (the kit's `harness/settings.json.template` changed — it did in 1.4.0), run
   `python3 factory/bin/adopt.py --register-guard`, then `--check` again.
2. Re-run the two live probes in [careful](../harness/skills/careful/SKILL.md)
   ("Verification") — the guard's own files may be among those just replaced.
3. One commit: `factory` (the new pointer), `.claude/`, `gates/`, the manifest.
4. Teammates: `git pull`, then `git submodule update --init` — or set
   `git config submodule.recurse true` once. A plain `git pull` leaves their `factory/` on the
   old commit, shown as ` M factory`; committing that undoes your upgrade.

**Why a human.** `--upgrade` replaces the guard's own files. The guard asks before an agent
runs it, and denies an agent's file edits under `.claude/hooks/`: approve the ask only if you
will review the result.

**A project adopted before 1.4.0** has no manifest (`.claude/.factory-manifest.json`), so
`--upgrade` cannot tell your edits from the kit's: every file that differs gets a
`.factory-new` and a printed review list, and the v1.3.x duplicate of the guard under
`.claude/skills/careful/hooks/` is removed. Spec files need the 1.4.0 frontmatter before the
spec gates pass: [GATES §7](../gates/GATES.md), "Upgrading from 1.3.x".

**A vendored copy** (no submodule): replace `factory/` with the target release, then run
`--upgrade` the same way.

### Upgrade Spec Kit

Stay on the version your kit release was tested with — specify-cli 1.0.12 for kit 1.4.0; the
`Next:` list `adopt.py` prints names it — and move when a kit release moves it. Moving ahead of
the kit is your call; the steps are the same.

```bash
uv tool install specify-cli==<version>             # a == pin makes `uv tool upgrade` a no-op
specify integration upgrade claude --force         # refresh Spec Kit's files in the project
specify extension update                           # only if you installed extensions
python3 factory/bin/adopt.py --check
```

What each step does, as run:

- Installing the new CLI changes **no file in the project**; `.specify/init-options.json` still
  names the old version. With the CLI installed as `specify-cli==1.0.11`,
  `uv tool upgrade specify-cli` printed "Nothing to upgrade"; installing with the new pin
  replaced it.
- `specify integration upgrade claude` without `--force` refreshed `.claude/skills/speckit-*`
  and Spec Kit's manifests, but listed 12 existing `.specify/scripts/` and
  `.specify/templates/` files as "not updated", and it stops with exit 1 if you edited any
  Spec Kit file. With `--force` it restored all of them, overwriting such edits — commit first
  and read `git diff` after.
- Neither form touched `.claude/settings.json` (the guard stayed registered),
  `.specify/memory/`, `.specify/templates/overrides/` or any file `adopt.py` installed.
  `specify self upgrade` did not recognise a uv install with a custom tool directory and only
  printed instructions; the `uv tool install` line above is the one that worked.
- The kit's overrides in `.specify/templates/overrides/` take precedence over Spec Kit's own
  templates, so an upstream template change reaches you when a kit release adapts it
  ([speckit/README.md](../speckit/README.md)).
- After a major Spec Kit bump, also re-run the adoption audit,
  [AI-ONBOARDING §4](../AI-ONBOARDING.md).

### Keeping your own Level-0 files current

[LEVELS](../model/LEVELS.md) asks every Level-0 file for an owner and an update trigger; a file
with neither becomes a confident liar. The kit ships the templates; keeping your filled copies
true is yours. A starting assignment:

| File | Changes when | Lands in the same commit as |
|---|---|---|
| `.specify/memory/constitution.md` | a principle no longer holds, a stack decision is reversed, an incident teaches an invariant | the `.claude/CLAUDE.md` mirror and each agent's INVARIANTS block; the version and date on its Version line |
| `.specify/memory/vision.md` | users, value or business model change | a constitution amendment, if an article depends on it |
| `.claude/CLAUDE.md` | the constitution's safety articles change | that amendment |
| `.claude/rules/*.md` | an architecture, API or data convention changes | the first code that follows the new convention |
| `gates/chain.conf` | a formatter, linter, test runner or build command changes | the change of tool |
| `.claude/hooks/careful.json` | a new protected branch, database client or deploy command | — a human edit: the file is guarded |

A routine that catches drift: at every kit upgrade and at least monthly, run
`python3 factory/bin/adopt.py --check` and the four-lens audit in
[AI-ONBOARDING §4](../AI-ONBOARDING.md).

## The standing rule this encodes

> **Always institutionalize findings.** Every bug batch, every review finding, every measured
> trap gets written into the operating files (constitution, harness, gates) the day it is
> learned — a lesson that lives only in a chat transcript is a lesson scheduled for re-learning.
