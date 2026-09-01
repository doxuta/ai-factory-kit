---
name: careful
description: >
  Deterministic guard that pauses for human confirmation before destructive commands —
  recursive delete, DROP/TRUNCATE, DELETE/UPDATE without WHERE, migrate-down,
  volume-destroying compose-down, force-push, hard-reset. Warn-not-block, fail-open. The last
  line of defense for autonomous runs. Matcher logic after gstack /careful (MIT,
  github.com/garrytan/gstack); reference hook shipped in hooks/check-careful.sh.
---
<!-- WHO READS ME: whoever wires guardrails for an agent that runs shell commands — especially
     unattended. I POINT TO: ../../HARNESS.md (§4, where this sits in the anatomy) ·
     ../../../gates/GATES.md (§6: test the guard in both directions) ·
     ../spec-first/SKILL.md (the first line of the same defense stack). -->

# Careful — confirm before the un-undoable

An agent reminding itself to be careful is a probabilistic guard; it fails exactly on the runs
nobody is watching. The contract here: a **deterministic pre-execution hook** that inspects
every shell command and demands human confirmation for the destructive ones. The model can
forget; the hook cannot. That is the whole point — and why this is positioned as the last
line for autonomous/scheduled runs, where "the human would have noticed" is false.

## What triggers confirmation

| Class | Patterns |
|---|---|
| Filesystem | recursive delete (`rm -r` / `rm -rf`) — except an allowlist of regenerable dirs [EXAMPLE: node_modules, dist, build, coverage] |
| SQL | `DROP TABLE/DATABASE/SCHEMA` · `TRUNCATE` · `DELETE` or `UPDATE` **without `WHERE`** |
| Migrations | any migrate `down` / `force` / `drop` |
| Containers | compose `down -v` · volume `rm` — data volumes die with them |
| Git history | `push --force` · `reset --hard` · `checkout .` / `restore .` — uncommitted work |
| Infra | cluster-scope `delete` · system `prune` |

Adapt the pattern table to your stack; the classes are the portable part.

## Design rules (each one paid for)

- **Warn, don't hard-block.** The hook asks; the human decides. A guard that cannot be
  overridden gets disabled the first time it is wrong — and then protects nothing.
- **Fail-open.** Unparseable input → pass through, silently. A guard that can wedge every
  command is a bigger availability risk than the risk it guards against.
- **Test in both directions** ([GATES §6](../../../gates/GATES.md)) before enabling: every
  dangerous pattern → confirmation fires; a set of safe commands → passes untouched; garbage
  input → fail-open. Measured on a production repo (7/7 dangerous asked, 5/5 safe passed,
  garbage stdin passed). A guard proven in only one direction is decoration.
- **Opt-in, explicitly.** The hook touches every shell command of every session — enable it
  as a deliberate config change, never silently. For unattended runs, enabled is the sane
  default; for interactive ones, the human's call.

## Position in the defense stack

Order of defenses: the spec gate keeps wrong work from starting
([`spec-first`](../spec-first/SKILL.md)) → the [gate chain](../../../gates/GATES.md) keeps
broken work from landing → adversarial review catches what gates miss → **careful** catches
the one command that would make a mistake permanent. Wire it through your platform's
pre-execution hook mechanism ([HARNESS §4](../../HARNESS.md)). New patterns go into the
hook's table; the fail-open branch stays intact no matter what you add.
