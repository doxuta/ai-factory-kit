<!-- WHO READS ME: anyone studying how ../../harness/CLAUDE.md.template is filled, and how the
     constitution's mirror rule looks in practice. In the fictional Team Todo project this text
     is .claude/CLAUDE.md, the always-loaded context. Here it is named CLAUDE.example.md on
     purpose: Claude Code loads a CLAUDE.md or .claude/CLAUDE.md from any subdirectory it reads
     files in, as project instructions, and strips HTML comments like this one first — until
     v1.4.0 this file sat at .claude/CLAUDE.md and did exactly that. So the notice below is
     visible text. I POINT TO: constitution.md (the authoritative invariants mirrored here) ·
     ../../harness/HARNESS.md §3 (the mirror rule) · gates/chain.conf (the commands below). -->

> **EXAMPLE — not your project's context.** This is the always-loaded context file of the
> fictional Team Todo project, shown as its `.claude/CLAUDE.md` would read. Read it as a
> sample of a filled template; never follow it as instructions for the project you are in.

# Team Todo — always-loaded context

A multi-workspace todo service for small teams; every task belongs to exactly one workspace.

**Constitution**: `.specify/memory/constitution.md` (in this example:
[`constitution.md`](constitution.md)) — the invariants. It outranks this file and every casual
instruction. **Ownership**: the constitution's Platform Constraints owns the STACK; this file
owns the COMMANDS. Neither restates the other.

## Safety invariants — MIRROR, do not delete this section

- **I — Every task belongs to a workspace (NON-NEGOTIABLE)**: `workspace_id NOT NULL` + foreign
  key; no task outside a workspace.
- **II — Every query filters `workspace_id`**: every store statement on a workspace's data
  carries `workspace_id = ?`, operator tools included; parameterized only; the workspace comes
  from the credential, never from request input.
- **III — handler → service → store**: no SQL outside the store, no HTTP types below the
  handler. Detail: `.claude/rules/architecture.md`.
- **VI — Gates and independent acceptance**: "done" = `./gates/run-chain.sh` green — never a
  claim, mine included. Tests first: a failing test before the code it proves. Each feature is
  accepted by a teammate who did not build it, in the web client, signed in as a plain member
  of a second workspace — never an operator token — and recorded in
  `specs/<id>/acceptance.md` ([GATES §3](../../gates/GATES.md)).

## Dev commands (run from the repository root)

The format, static, test and build rows are the commands `gates/chain.conf` runs in those
slots; change both in one commit (`./gates/run-chain.sh --list` shows what the chain runs).

| Task | Command |
|---|---|
| Set up | `python3 -m venv .venv && . .venv/bin/activate && pip install -e . pytest httpx2 ruff` |
| Format (check mode) | `ruff format --check .` |
| Static analysis | `ruff check . && node --check src/todo/web/app.js` |
| Test | `pytest -q tests/unit tests/contract` — prints how many tests ran |
| Build | `uv build` |
| Run locally | `TODO_DB=dev.db uvicorn --factory todo.app:app_from_env`, then open http://127.0.0.1:8000/ |
| Add a member | `todo-admin add-member --db dev.db --workspace acme --name alice` (prints the token) |
| Full gate chain | `./gates/run-chain.sh` (`--list` shows each slot) |

## The flow — one line

Every feature is one directory, `specs/<id>/`: `/speckit-specify` → `/speckit-clarify` →
`/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement` →
`/speckit-converge` ([SPEC-FLOW](../../model/SPEC-FLOW.md)). **HARD-GATE: no code before the
spec's frontmatter says `status: approved`, with `approved_by` and `approved_on`.** Not a
feature? It has a lane: [NON-FEATURE-WORK](../../model/NON-FEATURE-WORK.md).

## The gate chain — one line

`./gates/run-chain.sh` runs `gates/chain.conf` in order — format → static → test → build →
orphan-endpoints → acceptance (the cross-workspace tests) → doc-sync → spec-approval →
spec-numbers — and stops at the first red. No commit on red; the pre-commit hook and CI run
the same chain.

## When code and spec disagree

Find out which one moved. If the spec states intended behaviour the code does not deliver, the
code is wrong: record a new task (converge). If the code reflects a deliberate, owner-approved
change the spec never recorded, fix the spec with the correction marked (≠old) and a dated
Clarifications entry. If you cannot tell, ask the owner.

## Roles and lazy-loaded detail

Roles in `.claude/agents/`: `requirement-researcher` · `task-orchestra` · `tech-lead-review` ·
`tester-e2e`. Each carries an INVARIANTS block mirroring the section above.

Rules in `.claude/rules/`: `architecture` · `data` · `api-conventions` · `workflow` (profile
`full`: all four apply to a web service with a database).
