<!-- WHO READS ME: a kit maintainer editing the Spec Kit overrides or moving the tested Spec Kit
     version; an adopter who wonders why their specs start with frontmatter and their task lists
     always carry tests. I POINT TO: overrides/ (the files) · ../bin/adopt.py (installs them) ·
     ../model/SPEC-FLOW.md (what the frontmatter means to the flow) ·
     ../constitution/constitution-template.md (the third override) ·
     ../gates/check-plan-sync.sh and ../gates/check-spec-approval.sh (the gates that read the
     result) · ../THIRD_PARTY_NOTICES.md (upstream licence). -->

# Spec Kit template overrides

**Tested with specify-cli 1.0.12** (github/spec-kit tag `v1.0.12`). Every claim below was
checked against that version on 2026-09-29; for another version, check them again
([Keeping them current](#keeping-them-current)).

## Why the kit overrides Spec Kit's templates

Spec Kit 1.0.12 finds each template through a stack, highest first
(`.specify/scripts/bash/common.sh`, `resolve_template`):

1. `.specify/templates/overrides/<name>.md` — the project's overrides
2. `.specify/presets/<preset-id>/templates/` — installed presets, by priority
3. `.specify/extensions/<ext-id>/templates/` — extensions
4. `.specify/templates/<name>.md` — the core templates `specify init` writes

An override replaces the core template whole; nothing is merged. Until kit 1.4.0 the kit
installed no override, so Spec Kit's defaults decided three things the kit's rules depend on
(audit finding F6, 2026-09):

- **No frontmatter.** Spec Kit's spec template has none, only a body line `**Status**: Draft`
  that no command reads again. Specs generated with it carried no `feature` / `status` /
  `epic`, the roadmap view printed nothing, and an AI that added the keys by hand left the
  spec with two status fields.
- **Tests optional.** The tasks template says "Tests are OPTIONAL - only include them if
  explicitly requested in the feature specification", and the `/speckit-tasks` command says
  the same. The kit's constitution requires tests first (Article VI).
- **The wrong constitution skeleton.** `/speckit-constitution` uses the resolved template "as
  the required structure" — Spec Kit's five principles and two unnamed sections, not the
  kit's seven articles.

Spec Kit also has presets. The kit uses the overrides layer instead because installing it is
a plain file copy, which `adopt.py` already does, and it sits above every preset. A preset was
not tried.

## What each override changes

| Installed as | Kit source | Changes from Spec Kit 1.0.12 | Why |
|---|---|---|---|
| `.specify/templates/overrides/spec-template.md` | [`overrides/spec-template.md`](overrides/spec-template.md) | Frontmatter at line 1: `feature`, `status: draft`, `epic`, `owner`, `approved_by`, `approved_on`, as placeholders. The body line `**Status**: Draft` is removed. One `**Tests**: required …` line under "User Scenarios & Testing". Everything else is upstream text. | The gates read the frontmatter ([SPEC-FLOW](../model/SPEC-FLOW.md)); one status field, not two; `/speckit-tasks` writes test tasks when "explicitly requested in the feature specification", and that line is the request. |
| `.specify/templates/overrides/tasks-template.md` | [`overrides/tasks-template.md`](overrides/tasks-template.md) | Tests REQUIRED instead of optional: the "Tests" line, the three "Tests for User Story N" headings, the unit-test task in the last phase, the ordering rule and the parallel example. `(test-exempt: <reason>)` for a task with no testable behaviour. The last phase's "Run quickstart.md validation" becomes the acceptance run by someone other than the builder, recorded in `acceptance.md`. Notes add tick-in-the-landing-commit and `(deferred → <where>)`. | Constitution Article VI (tests first, independent acceptance); the gates' task format ([`check-plan-sync.sh`](../gates/check-plan-sync.sh)). |
| `.specify/templates/overrides/constitution-template.md` | [`../constitution/constitution-template.md`](../constitution/constitution-template.md) | The kit's template replaces Spec Kit's scaffold. | `/speckit-constitution` amends against the kit's seven articles. |

Both templates in [`overrides/`](overrides/) open, after their frontmatter, with a comment that
names what changed and carries the upstream attribution; the comment asks the generator to
delete it from the generated file.
To see the kit's changes in an adopted project, diff the core template against the override:
`diff .specify/templates/spec-template.md .specify/templates/overrides/spec-template.md`.

**Not overridden.** `plan-template.md`: its Constitution Check is "[Gates determined based on
constitution file]", so with the kit's constitution installed `/speckit-plan` already checks
the kit's articles — in the live run below it checked the fixed articles and reported the
unratified slots as blocking. `checklist-template.md`: requirement-quality checklists are
outside what the kit enforces.

## What an override cannot change

- **The command prompts.** The `/speckit-*` skills that `specify init` writes to
  `.claude/skills/` are not templates. `/speckit-tasks` still says "Tests are OPTIONAL: Only
  generate test tasks if explicitly requested in the feature specification or if user
  requests TDD approach." Three things make that request on the kit's behalf: the spec's
  `**Tests**:` line, the tasks override, and Article VI in the constitution the command loads.
  If a task list comes back without tests anyway, re-run `/speckit-tasks` with "tests first
  for every behaviour change" as its argument
  ([plan-and-tdd](../harness/skills/plan-and-tdd/SKILL.md)).
- **Integrations other than Claude.** An override is read as-is. Spec Kit's packaged tasks
  template writes the command as `__SPECKIT_COMMAND_TASKS__`, which `specify init` renders for
  the chosen integration; the override spells it `/speckit-tasks`, Claude Code's form. The
  name appears only in two HTML comments of the template, and the live run below carried
  neither into `tasks.md`.
- **Other files the commands write.** `/speckit-specify` also writes
  `checklists/requirements.md` with `- [ ]` items. The gates read `tasks.md` only.

## How adopt.py installs them

`python3 factory/bin/adopt.py` copies every `speckit/overrides/*.md` to
`.specify/templates/overrides/`, and `constitution/constitution-template.md` both to
`.specify/templates/overrides/constitution-template.md` and to
`.specify/memory/constitution.md` — the latter only when it is absent or still Spec Kit's
unfilled scaffold. The manifest records the overrides as kit-owned. Checked in a scratch
project: `--upgrade` replaced an override nobody had edited and wrote
`spec-template.md.factory-new` beside one that had been edited; `--check` failed (exit 1) on a
deleted override and warned on an edited one. Run adopt.py before
`specify init --here --force`: in the check below, init left all three overrides
byte-identical.

## Verified on 2026-09-29

In a scratch git repository: `adopt.py --profile cli` from this kit, then
`specify init --here --force --integration claude` (specify-cli 1.0.12, installed with
`uv tool install specify-cli==1.0.12`).

| Check | Result |
|---|---|
| The three files in `.specify/templates/overrides/` after init | present, byte-identical to the kit's |
| `bash .specify/scripts/bash/resolve-template.sh spec-template` (and `tasks-template`) | exit 0; output byte-identical to the override |
| `resolve-template.sh plan-template` | Spec Kit's core template, as intended |
| `specify preset resolve spec-template` | `(top layer from: project override)`; the same for `tasks-template`; `(top layer from: core)` for `plan-template` |
| `create-new-feature.sh --json --short-name monthly-report "…"` | exit 0; `specs/001-monthly-report/spec.md` starts with the override's frontmatter |
| `setup-plan.sh --json`, `check-prerequisites.sh --json` (and `--paths-only`), `setup-tasks.sh --json` | exit 0 each; `setup-tasks.sh` returns the override as `TASKS_TEMPLATE` |
| The frontmatter as copied, through PyYAML `safe_load` | parses; `approved_by` and `approved_on` are null |
| `./gates/check-plan-sync.sh` on the unfilled copy | exit 1: `feature:` and `epic:` are placeholders, `feature:` differs from the directory |
| … after filling `feature`, `epic`, `owner` | exit 0; `check-spec-approval.sh` and `check-spec-numbers.sh` exit 0 |

**Live runs** — Claude Code 2.1.284, headless (`claude -p`), one run of each command in a
fresh project with the overrides installed:

- `/speckit-specify` wrote the frontmatter at line 1 with `feature:` equal to the directory
  name and `status: draft`, no body `**Status**` line, kept the `**Tests**:` line, and deleted
  the template comment. `./gates/check-plan-sync.sh`: green.
- `/speckit-plan`, with the spec marked approved and the constitution still the unfilled
  template, ran its Constitution Check against the kit's fixed articles and reported the
  unratified slots as a blocking finding for the owner.
- `/speckit-tasks` then wrote 33 tasks in the `- [ ] T001` format. Each of the three story
  phases opened with "Tests for User Story N (REQUIRED - write them first, watch them fail)"
  ahead of its implementation tasks; setup tasks carried `(test-exempt: <reason>)`; the last
  phase held the acceptance run recorded in `acceptance.md`. It dropped the template's
  `description:` frontmatter and its comment.

One run of each is evidence that the text works, not a guarantee: a model can still drift,
which is why the gates check the frontmatter and the acceptance record on every commit.

## Keeping them current

When the tested Spec Kit version moves:

1. Install the new version in isolation
   (`UV_TOOL_DIR=<dir> UV_TOOL_BIN_DIR=<dir>/bin uv tool install specify-cli==<version>`)
   and run `specify init --here --force --integration claude` in a scratch directory, once
   with the old version and once with the new.
2. Diff the old core templates against the new ones: those are the upstream changes to carry
   into the overrides.
3. Re-apply the kit's changes listed above to the new upstream text; keep the rest upstream.
4. Run every check in "Verified" again and update the version at the top of this file, in
   `bin/adopt.py` (`TESTED_SPECKIT`) and wherever the kit names the tested version.

## Licence

The two templates here are adapted from [github/spec-kit](https://github.com/github/spec-kit),
MIT License, Copyright GitHub, Inc. The notice travels in
[`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).
