<!-- WHO READS ME: an AI learning its own anatomy on this system — 6th in the reading order.
     I POINT TO: agents/ (roles) · skills/ (procedures) · CLAUDE.md.template (always-loaded
     context) · ../gates/GATES.md (guardrails' floor). -->

# Harness — AGENT = MODEL + HARNESS

The model is already smart; what makes an agent strong or weak is the **harness** around it:
its loop, its tools, its memory, its guardrails. This file maps those four onto the kit.

## 1) Loop — how work moves

New feature → the [Level-1 spec flow](../model/SPEC-FLOW.md) (HARD-GATE at spec approval) →
TDD implement → [gate chain](../gates/GATES.md) → adversarial review → commit. Skills in
[`skills/`](skills/) encode the recurring procedures; agents in [`agents/`](agents/) are the
Level-2 roles the orchestrator dispatches.

## 2) Tools — give the model hands, then verify what the hands did

Subagents for specialist work (backend/db/frontend/review/security per your stack), a real
browser for UI verification (screenshots are evidence; "it should render" is not), and the gate
scripts. Rule of the house: **the orchestrator re-runs every gate a subagent reports** — trust
is for intentions, not numbers.

## 3) Memory — and the two traps we paid to learn

Project memory lives in: the constitution + always-loaded context (`CLAUDE.md`), the spec corpus
(`specs/`), the architecture blueprint, and git history. Two traps, both **measured on a real
repo**, both expensive:

1. **Path-scoped config loads lazily — and foreign syntax fails silently.** Rules scoped to file
   patterns activate only when a matching file is read; and a scoping key your platform doesn't
   recognize is ignored *without any warning* (this repo ran 7 rules at 84KB/session for months,
   believing them scoped, because the frontmatter used another tool's syntax). Consequences:
   **safety invariants must live in the ALWAYS-loaded file and inside each agent definition** —
   only details may lazy-load (the constitution's "mirror rule"). And verify your scoping syntax
   against your platform's docs, not by vibes.
2. **Subagents see a snapshot of config taken at session start.** Editing a rule mid-session
   does nothing for agents spawned in that same session — even after the edit. To verify what an
   agent actually sees, open a fresh session, and when asking an agent "is string X in your
   context?", always include a **decoy string that exists nowhere**: an agent that answers yes
   to everything is telling you about its compliance, not its context.

Corollary: a memory file with no owner and no update trigger becomes a **confident liar** —
delete it or wire it into [the daily sync](../sync/DAILY-SYNC.md).

## 4) Guardrails — trip, don't crash

- The [gate chain](../gates/GATES.md) on every commit; no commit on red.
- Third-person acceptance for anything touching authorization (GATES §3).
- A destructive-command guard (confirm before `rm -r` / `DROP` / force-push / migrate-down —
  see [`skills/careful/`](skills/careful/SKILL.md)) — the last line for autonomous runs.
- HARD-GATE: no code before an approved spec.
- Review findings: fixed or refuted with evidence, never shelved (GATES §2).

## 5) Extending with the upstream ecosystem

Spec Kit v1.x ships an official **community extension catalog**
([browse](https://speckit-community.github.io/extensions/) ·
[`catalog.community.json`](https://github.com/github/spec-kit/blob/main/extensions/catalog.community.json) ·
`specify extension info <name>`), tagged by category and effect. Map it onto the three levels
before shopping, so an extension lands where the model already has a socket:

| Upstream category | Slots into | Examples ↔ this kit's native part |
|---|---|---|
| `docs` / `visibility` | **Level 1 artifacts** — readers/reporters over spec/plan/tasks | architecture maps, diagram renderers ↔ the spec corpus is already the source of truth |
| `code` | the **implement** step | checkpoint commits, cleanup gates ↔ [plan-and-tdd](skills/plan-and-tdd/SKILL.md) + [GATES](../gates/GATES.md) |
| `process` | **Level 2 orchestration** | agent-assign ≈ [task-orchestra](agents/task-orchestra.md) · BDD/V-Model feed [tester-e2e](agents/tester-e2e.md) · CI-guard/blueprint-index ≈ executable gates · brownfield-bootstrap ≈ the [retro-fit playbook](../model/RETROFIT-PLAYBOOK.md) |
| `integration` | task-orchestra's external edge (Jira/DevOps sync, dashboards) |

Selection discipline (upstream's own warning: catalog entries are **not reviewed or audited**):

1. **Read the extension's source before installing** — it runs inside your agent's context.
2. Prefer `read-only` first; promote to `read-write` only after it earns trust.
3. One overlap rule: if the kit already has the native part (gates, roles, playbooks), the
   extension must REPLACE or FEED it — never run a second copy of the same duty in parallel
   (two sources claiming one duty is the routing disease the adoption audit hunts).
4. Record adopted extensions in the constitution's **Platform Constraints** so the next AI knows
   they exist.

## 6) Verification discipline in one table

| You are tempted to… | Instead |
|---|---|
| Believe a subagent's "all green" | Re-run the gates yourself, paste output |
| Trust a doc's claim about code | Read the executing code; docs freeze, code moves |
| Accept a `-run` filter's exit 0 | Check the filter matches ≥1 real test name |
| Test with the admin account | Non-privileged account — the wall only exists for a third person |
| Ship the backend, note "FE later" nowhere | Record the gap as a named task, or wire it now |
| Edit config mid-session and assume agents see it | Fresh session; decoy-string check |
