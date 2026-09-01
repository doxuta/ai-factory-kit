<!-- WHO READS ME: an adopter wiring skills into their agent platform, and any AI checking
     which procedures exist. I POINT TO: the five skill dirs below · ../HARNESS.md (where
     skills sit in the anatomy) · ../../model/SPEC-FLOW.md (the loop they serve). -->

# Portable skills

A skill is a recurring procedure an agent loads on demand — the "how" that doesn't belong in
always-loaded context. These five follow the [agentskills.io](https://agentskills.io) format so
they port across agent platforms.

## Format rules (both learned the hard way)

1. **Each skill is a DIRECTORY containing `SKILL.md`** — `skills/<name>/SKILL.md`. A flat
   `skills/<name>.md` file is **silently ignored by some platforms**: the skill "exists",
   never loads, and nothing warns you. Same disease as the silent-config traps measured in
   [`../HARNESS.md`](../HARNESS.md) §3 — foreign layout, no error, false confidence.
2. **YAML frontmatter (`name`, `description`) opens the file at byte 0** — loaders require it
   first, so in these files the kit's WHO-READS-ME header sits immediately below the
   frontmatter instead of on line 1.

## The five

| Skill | One line | Serves |
|---|---|---|
| [`spec-first/`](spec-first/SKILL.md) | HARD-GATE: clarify → design options → approval → only then code | [SPEC-FLOW](../../model/SPEC-FLOW.md) steps 1–5 |
| [`plan-and-tdd/`](plan-and-tdd/SKILL.md) | approved spec → verifiable tasks → red/green → one concern per commit | SPEC-FLOW step 6 |
| [`careful/`](careful/SKILL.md) | deterministic confirm-before-destructive-command guard | [HARNESS](../HARNESS.md) §4 guardrails |
| [`caveman/`](caveman/SKILL.md) | terse chat replies, ~65% fewer tokens; contracts stay verbatim | every chat reply |
| [`ponytail/`](ponytail/SKILL.md) | lazy-senior code ladder; the constitution outranks laziness | every code change |

Pairing that matters: **ponytail compresses the code, caveman compresses the talk** — and
neither compresses contracts (specs, commit messages, gate output — see each skill's boundary
section). `careful` is the only one that is really a *hook*, not a prompt: read its file
before enabling it.

## Install

Copy the directory for each skill you want into your project's skill location
[EXAMPLE: `.claude/skills/<name>/SKILL.md` on Claude Code] — keep the directory shape. Then
verify the platform actually lists the skill; rule 1 above fails silently.

## Writing a new skill

- One procedure per skill; if it needs an index, it's two skills.
- Frontmatter `description` carries the trigger phrases — that's all most routers read.
- Keep it stack-neutral; project specifics belong in the project's own overlay of the skill.
- Credit upstream sources (the five adapt superpowers, gstack, caveman, ponytail — all MIT).
