<!-- WHO READS ME: an adopter wiring skills into their agent platform, and any AI checking
     which procedures exist and which one owns a canonical prompt.
     I POINT TO (kit paths; factory/... once adopted): the five skill dirs below ·
     harness/HARNESS.md (§4 where skills sit in the anatomy · §7 other hosts) ·
     model/SPEC-FLOW.md (the loop they serve) · THIRD_PARTY_NOTICES.md (upstream credits). -->

# Skills

A skill is a recurring procedure an agent loads on demand — the "how" that doesn't belong in
always-loaded context. These five follow the [Agent Skills](https://agentskills.io) format
(`name` matching the directory, a `description` of at most 1,024 characters). The format
ports: Claude Code, GitHub Copilot, Gemini CLI and Codex each document a skills directory of
this shape ([HARNESS §7](../HARNESS.md)). The content ports less: two skills assume Spec
Kit's `/speckit-*` commands, and `careful` is a Claude Code hook.

## Format rules (both learned the hard way)

1. **Each skill is a DIRECTORY containing `SKILL.md`** — `skills/<name>/SKILL.md`. A flat
   `skills/<name>.md` file is **silently ignored by some platforms**: the skill "exists",
   never loads, and nothing warns you. Same disease as the silent-config traps measured in
   [`../HARNESS.md`](../HARNESS.md) §3 — foreign layout, no error, false confidence.
2. **YAML frontmatter (`name`, `description`) opens the file at byte 0** — loaders require it
   first, so in these files the kit's WHO-READS-ME header sits immediately below the
   frontmatter instead of on line 1. The same holds for the kit's agents and rules; `adopt.py`
   refuses to install any of them without it.

## The five

| Skill | One line | Serves |
|---|---|---|
| [`spec-first/`](spec-first/SKILL.md) | the discipline inside `/speckit-specify` and `/speckit-clarify`: premise, options, explicit approval | [SPEC-FLOW](../../model/SPEC-FLOW.md) specify and clarify, up to approval |
| [`plan-and-tdd/`](plan-and-tdd/SKILL.md) | the discipline inside `/speckit-implement`: tasks carry tests; red/green; gates; one concern per commit | SPEC-FLOW implement |
| [`careful/`](careful/SKILL.md) | deterministic guard: asks before destructive commands, denies the un-undoable ones and any change to its own files or the gate scripts | [HARNESS](../HARNESS.md) §4 guardrails |
| [`caveman/`](caveman/SKILL.md) | terse chat replies, no published reduction figure; contracts stay verbatim | every chat reply |
| [`ponytail/`](ponytail/SKILL.md) | lazy-senior code ladder; the constitution outranks laziness | every code change |

**One owner per canonical prompt.** "New feature" belongs to `/speckit-specify`, and
"implement" to `/speckit-implement`; `spec-first` and `plan-and-tdd` are how those commands are
conducted, never a second way in, and their descriptions say so, because a model routes by
description. Neither skill writes a spec, a plan or a task list of its own.

Pairing that matters: **ponytail compresses the code, caveman compresses the talk** — and
neither compresses contracts (specs, commit messages, gate output — see each skill's boundary
section). `careful` is the only one that is really a *hook*, not a prompt: read its file
before enabling it.

## Install

`adopt.py` installs each skill directory into `.claude/skills/<name>/` (the `careful` hook
scripts go to `.claude/hooks/`, one copy only), next to the `speckit-*` skills that
`specify init` writes. On another host, copy the directories into that host's skill location
(HARNESS §7) — keep the directory shape — then verify the host actually lists the skill;
rule 1 above fails silently.

## Writing a new skill

- One procedure per skill; if it needs an index, it's two skills.
- Frontmatter `description` carries the trigger phrases — that's all most routers read. If a
  Spec Kit command already owns the prompt, say "inside /speckit-…" in the description.
- Keep it stack-neutral; project specifics belong in the project's own overlay of the skill.
- Credit upstream sources (the five adapt superpowers, gstack, caveman, ponytail — all MIT;
  [THIRD_PARTY_NOTICES](../../THIRD_PARTY_NOTICES.md)).
