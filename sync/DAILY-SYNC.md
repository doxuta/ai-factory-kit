<!-- WHO READS ME: the maintainer's daily-ship routine (an AI on a schedule) — and any adopter
     wondering how fresh this kit is. I POINT TO: ../CHANGELOG.md (where syncs land) ·
     ../model/RETROFIT-PLAYBOOK.md (the method syncs reuse). -->

# Daily-Ship Sync — how this kit stays current

This kit is distilled from a **living production factory** (the Nexus platform). When the
factory's harness improves, the improvement flows here — on the maintainer's daily-ship
routine, not "when someone remembers".

## The protocol (runs inside the maintainer's daily routine)

1. **Diff the sources of truth** since the last sync commit recorded in [`../CHANGELOG.md`](../CHANGELOG.md):
   the factory repo's `.claude/` (rules, skills, agents), `.specify/memory/constitution.md`,
   `gates/` scripts, and `loop/STATE.md` campaign entries.
   ```bash
   git -C <factory-repo> log --oneline --since="<last-sync-date>" -- .claude/ .specify/ nexus-platform/scripts/
   ```
2. **Classify each change**: `portable` (a lesson any project benefits from) vs `factory-only`
   (stack- or product-specific). Only `portable` syncs. When unsure, it is factory-only —
   this kit stays stack-neutral except `platform.md`.
3. **Apply with the retro-fit discipline** ([playbook](../model/RETROFIT-PLAYBOOK.md)): verify
   the lesson against the kit's current text, update every cross-linked file **in one commit**,
   keep the file-header link maps true.
4. **Record**: one `CHANGELOG.md` entry per sync — date, factory commits absorbed, files touched,
   one-line "what got smarter".
5. **Gate**: the kit's own link integrity (`grep` every relative `.md` link resolves) + the
   gate script's two-direction test must pass before push.

## What an adopter should do

Nothing. `git pull` when you want the latest lessons; `CHANGELOG.md` tells you what changed and
why it matters. Pin a commit if you need stability — the kit follows semver-ish discipline:
breaking restructures bump a `vN` tag.

## The standing rule this encodes

> **Always institutionalize findings.** Every bug batch, every review finding, every measured
> trap gets written into the operating files (constitution, harness, gates) the day it is
> learned — a lesson that lives only in a chat transcript is a lesson scheduled for re-learning.
