<!-- WHO READS ME: an AI learning its own anatomy on this system — 6th in the reading order —
     and anyone asking whether the kit runs on their host or platform (§7).
     I POINT TO (kit paths; factory/... once adopted): harness/agents/ (roles) ·
     harness/skills/ (procedures) · harness/CLAUDE.md.template (always-loaded context) ·
     harness/rules/ (lazy-loaded detail) · gates/GATES.md (guardrails' floor) ·
     harness/skills/careful/SKILL.md (the guard, and its own host notes). -->

# Harness — AGENT = MODEL + HARNESS

The model is already smart; what makes an agent strong or weak is the **harness** around it:
its loop, its tools, its memory, its guardrails. This file maps those four onto the kit, then
says which hosts and platforms the harness actually runs on (§7).

## 1) Loop — how work moves

New feature → the [Level-1 spec flow](../model/SPEC-FLOW.md): `/speckit-specify` →
`/speckit-clarify` → HARD-GATE (the owner approves; the spec's frontmatter records it) →
`/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement` (TDD, the
[gate chain](../gates/GATES.md) per commit, adversarial review) → independent acceptance →
`accepted`. Spec Kit's commands own the entry points; the skills in [`skills/`](skills/)
encode how each step is conducted (`spec-first` inside specify and clarify, `plan-and-tdd`
inside implement), and the agents in [`agents/`](agents/) are the Level-2 roles the
orchestrator dispatches. Work that is not a feature — a bug in shipped behaviour, a hotfix, a
refactor, a spike, a release — runs in its lane in
[NON-FEATURE-WORK](../model/NON-FEATURE-WORK.md).

## 2) Tools — give the model hands, then verify what the hands did

Subagents for specialist work (backend/db/frontend/review/security per your stack), a real
browser for UI verification (screenshots are evidence; "it should render" is not), and the gate
scripts. The four agent files are Claude Code subagent definitions: YAML frontmatter at line 1
(`name`, `description`), and the roles that must not change what they judge —
`tech-lead-review`, `tester-e2e`, `requirement-researcher` — drop the file-editing tools with
`disallowedTools`. A tool list narrows what is easy, not what is possible: Bash can still
write a file, so the rule in each role card and the orchestrator's diff check still apply.
Rule of the house: **the orchestrator re-runs every gate a subagent reports** — trust is for
intentions, not numbers.

## 3) Memory — and the two traps we paid to learn

Project memory lives in: the constitution (`.specify/memory/constitution.md`) and the vision
beside it, the always-loaded context (`.claude/CLAUDE.md`), the spec corpus (`specs/`), the
architecture blueprint, and git history. Two traps, both **measured on a real repo**, both
expensive:

1. **Path-scoped config loads lazily — and foreign syntax fails silently.** Rules scoped to file
   patterns activate only when a matching file is read; and a scoping key your platform doesn't
   recognize is ignored *without any warning* (this repo ran 7 rules at 84KB/session for months,
   believing them scoped, because the frontmatter used another tool's syntax). The kit repeated
   the mistake in its own files until v1.4.0: every rule opened with a comment, so its `paths:`
   frontmatter was not on line 1, and Claude Code's docs say such a rule loads unconditionally;
   the agents had no frontmatter at all, so Claude Code treated them as documentation, not
   subagents. Consequences: **safety invariants must live in the ALWAYS-loaded file and in
   each agent's INVARIANTS block** — only details may lazy-load (the constitution's "mirror
   rule"); frontmatter goes at byte 0 and `adopt.py` refuses to install a file without it;
   and verify your scoping syntax against your platform's docs, not by vibes. Two more
   Claude Code details with the same shape. Its parser (2.1.284) ends the frontmatter at the
   first three dashes it meets, even in the middle of a comment line: the first draft of the
   1.4.0 rules explained the fence in a YAML comment, and that one mention would have cut
   `paths:` off again. And it strips block-level HTML comments from `CLAUDE.md` before loading
   it, so nothing an agent must obey belongs in one.
2. **Subagents see a snapshot of config taken at session start.** Editing a rule mid-session
   does nothing for agents spawned in that same session — even after the edit. To verify what an
   agent actually sees, open a fresh session, and when asking an agent "is string X in your
   context?", always include a **decoy string that exists nowhere**: an agent that answers yes
   to everything is telling you about its compliance, not its context.

Corollary: a memory file with no owner and no update trigger becomes a **confident liar** —
delete it or wire it into the daily sync ([DAILY-SYNC](../sync/DAILY-SYNC.md#keeping-your-own-level-0-files-current),
Part B, "Keeping your own Level-0 files current").

## 4) Guardrails — trip, don't crash

- The [gate chain](../gates/GATES.md) — `./gates/run-chain.sh` — on every commit; no commit on
  red. Feature 001, the walking skeleton, wires its slots and installs the pre-commit hook and
  CI that enforce it; until then the unwired slots are honestly red.
- Independent acceptance per feature, recorded in `specs/<id>/acceptance.md` — someone other
  than the builder, and a non-privileged account wherever the product has an authorization
  boundary (GATES §3).
- A destructive-command guard — asks before `rm -r` / `DROP` / force-push / migrate-down /
  cloud teardown / `--no-verify`, and **hard-denies** the shapes nothing undoes: recursive
  delete of `/`, `~`, `$HOME` or the project; force-push or branch-delete against a protected
  branch; raw block-device writes and eFuse burns; recursive delete of `.git` or `.specify` in
  a repository with no remote; and every tool or shell form of writing, moving or deleting the
  guard's own files, the gate scripts and Claude Code's managed settings. Its registered
  command fails closed: a missing or broken hook blocks instead of passing. See
  [`skills/careful/`](skills/careful/SKILL.md). Ask is only a wall where someone answers it:
  check what your unattended runs do with a prompt before counting it as protection.
- HARD-GATE: no code before an approved spec — `status: approved` with `approved_by` and
  `approved_on`, which the `spec-approval` gate checks.
- Review findings: fixed or refuted with evidence, never shelved (GATES §2).

## 5) Extending with the upstream ecosystem

Spec Kit has two kinds of extension, and specify-cli 1.0.12 treats them differently
(`specify extension search`, `specify extension catalog list`):

- **Bundled, installable** — the `default` catalog, by the Spec Kit authors. Checked
  2026-09-29 with `specify extension search` (specify-cli 1.0.12; the catalog is fetched live,
  so it changes without a CLI release; an earlier check of this section counted four):
  `agent-context` (manages agent context files such as `CLAUDE.md` between markers — the file
  the kit's template fills, so read what it writes before adding it); `assess` (intake →
  research → define → shape → decide; "a go verdict hands off to /speckit.specify"; it lives under
  `.specify/assessments/<slug>/`); `bug` (bug triage under `.specify/bugs/<slug>/`); `git`
  (branch creation, sequential or timestamp numbering); and `github` ("create GitHub issues
  from a feature's task list"). `specify extension add <name>` installs them. `github` does
  the job of the built-in `/speckit-taskstoissues`: pick one of the two, never both, or a
  task list becomes two sets of issues. The kit takes no position on which; neither is part of
  the flow (SPEC-FLOW lists `/speckit-taskstoissues` as optional).
- **Community, discovery only** — 176 entries in `catalog.community.json` when this was
  checked (181 results in all with the five above), tagged by category and effect, browsable on a
  [website](https://speckit-community.github.io/extensions/) that upstream itself calls a
  third-party resource. The CLI searches them but will not install them by name: after you have
  read the source, `specify extension add <name> --from <url>`.

Map a candidate onto the three levels before shopping, so an extension lands where the model
already has a socket:

| Upstream category | Slots into | Examples ↔ this kit's native part |
|---|---|---|
| `docs` / `visibility` | **Level 1 artifacts** — readers/reporters over spec/plan/tasks | architecture maps, diagram renderers ↔ the spec corpus is already the source of truth |
| `code` | the **implement** step | checkpoint commits, cleanup gates ↔ [plan-and-tdd](skills/plan-and-tdd/SKILL.md) + [GATES](../gates/GATES.md) |
| `process` | **Level 2 orchestration** | agent-assign ≈ [task-orchestra](agents/task-orchestra.md) · BDD/V-Model feed [tester-e2e](agents/tester-e2e.md) · CI-guard/blueprint-index ≈ executable gates · brownfield-bootstrap ≈ the [retro-fit playbook](../model/RETROFIT-PLAYBOOK.md) · bundled `assess` ≈ the idea check before Phase 0's first spec |
| `integration` | task-orchestra's external edge (Jira/DevOps sync, dashboards) | — |

Selection discipline (upstream's own warning: community entries are **not reviewed or
audited**):

1. **Read the extension's source before installing** — it runs inside your agent's context.
2. Prefer `read-only` first; promote to `read-write` only after it earns trust.
3. One overlap rule: if the kit already has the native part (gates, roles, playbooks), the
   extension must REPLACE or FEED it — never run a second copy of the same duty in parallel
   (two sources claiming one duty is the routing disease the adoption audit hunts). An
   extension's working directory (`.specify/assessments/`, `.specify/bugs/`) holds pointers
   and working notes; what the owner approves still lands in `specs/<id>/`.
4. Record adopted extensions in the constitution's **Platform Constraints** so the next AI knows
   they exist.

## 6) Verification discipline in one table

| You are tempted to… | Instead |
|---|---|
| Believe a subagent's "all green" | Re-run the gates yourself, paste output |
| Trust a doc's claim about code | Read the executing code; docs freeze, code moves |
| Accept a `-run` filter's exit 0 | Check the filter matches ≥1 real test name |
| Accept your own feature, or test with the admin account | Someone other than the builder; a non-privileged account wherever there is an authorization boundary |
| Ship a capability no entry point reaches | Record the gap as a named task, or wire it now |
| Edit config mid-session and assume agents see it | Fresh session; decoy-string check |
| Assume a file loaded because it exists | Frontmatter at line 1; in a fresh session check the host lists it — `/context` (memory files), `/skills`, and ask which subagents are available |

## 7) Hosts and platforms

**The supported envelope.**

- **Supported** — Claude Code on Linux, macOS and WSL (with the project on the Linux
  filesystem). For 1.4.0 the test suites ran in CI on Linux and macOS, and headless Claude Code
  sessions (the guard's live probes among them) on Linux; nothing has run on WSL.
- **Best-effort** — native Windows, where Claude Code runs hooks under Git Bash. Not run.
- **Other AI hosts** (Codex, Gemini CLI, GitHub Copilot, Cursor, …) — the model, the specs, the
  Spec Kit flow and the gates port, because they are Markdown, shell and git. The harness —
  the `.claude/` layout, the agents, the rules — and the careful guard need porting by hand.
  `adopt.py` writes only the Claude Code layout.

**Per host.** What each host documents for the parts the harness depends on. Checked on
2026-09-29 against: Claude Code's docs (code.claude.com; CLI 2.1.284); the GitHub Copilot and
VS Code docs, and the Gemini CLI and Codex source repositories, at their 2026-09-28 heads; and
what `specify init --integration <host>` writes with specify-cli 1.0.12. "Unverified" means
not checked, not "absent".

| | Claude Code (target) | GitHub Copilot CLI | VS Code agent (local) | Gemini CLI | Codex CLI | Cursor |
|---|---|---|---|---|---|---|
| Context file | `CLAUDE.md` or `.claude/CLAUDE.md`; `AGENTS.md` only when neither exists, or through an `@`-import | `.github/copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md` and `.claude/CLAUDE.md`, `GEMINI.md` — all combined, no defined precedence | `.github/copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md` | `GEMINI.md`; the name is configurable (`context.fileName`), e.g. to `AGENTS.md` | `AGENTS.md`, every one from the project root down to the working directory | unverified |
| Path-scoped rules | `.claude/rules/*.md`, `paths:` in frontmatter on line 1 | `.github/instructions/**/*.instructions.md`, `applyTo` | `.github/instructions/`, or `.claude/rules/` | none by glob; `GEMINI.md` files in subdirectories load when a tool touches them | none by glob; an `AGENTS.md` in a subfolder applies when the session runs there | unverified |
| Agent format | `.claude/agents/*.md`: YAML frontmatter first, `name` + `description` required | `.github/agents/*.agent.md` | `.github/agents/`, or `.claude/agents/*.md` in Claude's format | `.gemini/agents/*.md`, YAML frontmatter first | TOML roles: `[agents]` in `config.toml`, or a config folder's `agents/` | unverified |
| Skills dir | `.claude/skills/<name>/SKILL.md` | `.github/skills`, `.claude/skills`, `.agents/skills` | `.github/skills`, `.claude/skills`, `.agents/skills` | `.gemini/skills` or `.agents/skills` | `.agents/skills` | Spec Kit writes `.cursor/skills` |
| Pre-tool hook, and what "ask" means | `PreToolUse` in `.claude/settings.json`; `hookSpecificOutput.permissionDecision` allow / deny / ask / defer; ask prompts the user; exit 2 blocks | `preToolUse` in `.github/hooks/*.json`, and `.claude/settings.json` is read too; top-level `permissionDecision` allow / deny / ask; a non-zero exit denies, a timeout lets the call through; in the cloud agent, ask = deny. Whether it reads the nested envelope careful prints is not documented | `.claude/settings.json` hooks only with `chat.useClaudeHooks` (off by default), and matcher values are ignored, so every command for the event runs; decision fields unverified | `BeforeTool` in `.gemini/settings.json`; top-level `decision` allow / deny — no ask; exit 2 blocks, any other non-zero exit only warns | `hooks.json` in a config folder, or `[hooks]` in `config.toml`; deny with a reason blocks; **ask is unsupported and fails open** — the call runs | unverified |
| Tool names a guard must match | `Bash`, `PowerShell`; `Write`, `Edit`, `NotebookEdit` | for PascalCase `PreToolUse`, Claude names: `bash` and `powershell` → `Bash`, `edit` and `apply_patch` → `Edit`, `create` → `Write` | unverified | `run_shell_command`; `write_file`, `replace` | shell as `Bash`; edits as `apply_patch` (matched by `Write`/`Edit`), the file path inside the patch text | unverified |
| Spec Kit command syntax | `/speckit-specify` | `/speckit-specify` | unverified | `/speckit.specify` | `$speckit-specify` | `/speckit-specify` |

What this means for the kit:

- **Commands.** The kit writes every Spec Kit command in Claude Code's form, `/speckit-<name>`.
  Read it as `/speckit.<name>` on Gemini CLI and `$speckit-<name>` on Codex.
  `/speckit-taskstoissues` works only with a GitHub remote and the GitHub MCP server's tools.
- **Context.** On a host that reads `AGENTS.md`, make it the shared file and import it from
  `.claude/CLAUDE.md` (the comment at the top of that file says how). Moving `CLAUDE.md` itself
  to `AGENTS.md` breaks its relative links; `python3 factory/bin/check-links.py <dir>` finds
  them.
- **Agents and rules.** Gemini CLI takes the agents' Markdown-with-frontmatter shape; Codex
  needs them rewritten as TOML roles; Copilot needs `.agent.md` files; the rules' `paths:` key
  is Claude Code's alone (Copilot's equivalent is `applyTo`). Until ported, the role cards still
  work as dispatch prompts: paste the Dispatch template.
- **The careful guard** is written to Claude Code's contract: its decision envelope, its tool
  names, its path fields and `$CLAUDE_PROJECT_DIR`. On Codex its ask tier would fail open and
  file edits arrive as `apply_patch`; on Gemini CLI there is no ask, and the decision is a
  top-level field; in Copilot's cloud agent ask becomes deny. Porting it means rewriting the
  envelope and the tool-name table for that host, then proving every tier — deny, ask and
  pass — with a live probe there ([careful](skills/careful/SKILL.md)). Until then, count it as
  absent on that host, whatever its test table says.

**Native Windows (Claude Code).** From Claude Code's docs:

- Without Git for Windows, Claude Code runs shell commands through its **PowerShell tool** and
  does not register the Bash tool at all. With Git for Windows, Bash runs under Git Bash and
  the PowerShell tool is available as well (on by default for claude.ai and Console accounts).
  A hook matching only `Bash` never fires for PowerShell; the kit's settings template matches
  `Bash|PowerShell`.
- Command hooks run under Git Bash, or under PowerShell when Git Bash is not installed. The
  kit's hook command line is written for bash, so on native Windows without Git Bash it cannot
  run and the careful guard is absent ([careful](skills/careful/SKILL.md) says what remains).
- File-tool paths arrive with backslash separators, even when the hook runs under Git Bash; the
  guard normalises them before matching.
- A CRLF checkout makes bash fail on the scripts; `adopt.py` appends LF rules for the
  installed scripts and gate configuration, by extension (`.claude/hooks/*.sh`, `gates/*.sh`,
  `gates/hooks/*`, …), to the project's `.gitattributes` — never a whole-tree rule, which would
  also rewrite the CRLF bytes inside a binary under `gates/`.

**Untested.** No live session on a native Windows host, and none on any host other than Claude
Code, has been run against this version of the harness. The per-host rows above come from
documentation and source code, not from running the kit there.
