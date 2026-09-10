---
name: careful
description: >
  Deterministic guard that stops before destructive commands — recursive delete,
  DROP/TRUNCATE, DELETE/UPDATE without WHERE, migrate-down, volume-destroying compose-down,
  force-push, remote-branch delete, hard-reset, in-place rewrites. Two tiers: hard-deny for
  the un-undoable shapes, ask for the rest. The last line of defense for autonomous runs.
  Matcher logic after gstack /careful (MIT, github.com/garrytan/gstack); reference hook
  shipped in hooks/.
---
<!-- WHO READS ME: whoever wires guardrails for an agent that runs shell commands — especially
     unattended. I POINT TO: ../../HARNESS.md (§4, where this sits in the anatomy) ·
     ../../../gates/GATES.md (§6: test the guard in both directions, including the consumer) ·
     ../spec-first/SKILL.md (the first line of the same defense stack). -->

# Careful — confirm before the un-undoable

An agent reminding itself to be careful is a probabilistic guard; it fails exactly on the runs
nobody is watching. The contract here: a **deterministic pre-execution hook** that inspects
every shell command and stops the destructive ones. The model can forget; the hook cannot.

## 🔴 Read first: the guard that was there but was not on

This skill shipped for 2.5 months with a hook that **did nothing**, and with a green test the
whole time.

The hook printed its decision as a top-level `{"permissionDecision":"ask", …}`. Claude Code
reads a PreToolUse decision only from inside `hookSpecificOutput`, so an unknown top-level
field was dropped and the command ran. Its own check — "7/7 dangerous commands asked" — read
the **script's stdout** and never asked whether the host honoured it. Upstream gstack shipped
the identical bug and measured it the same way (CHANGELOG `1.64.0.0`: *"deny meant allow"*,
*"guard hooks that can block: 0 of 3 → 3 of 3"*).

Two rules fall out, and they are the portable part of this whole document:

1. **A guard is not verified until you verify the CONSUMER.** Producing the right bytes proves
   nothing. Trigger a real destructive command in a live session and watch the host stop it.
2. **`ask` is only a wall if someone is at the wall.** A host running in a skip-permissions /
   auto-approve mode answers every `ask` for you, instantly, forever. Find out which mode your
   unattended runs actually use before you count `ask` as protection. On the factory repo the
   answer was `defaultMode: bypassPermissions` for every session — so `ask` had never once
   stopped anything, and only a hard `deny` was real.

Correct shape (Claude Code; find your own host's contract before porting):

```json
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"[careful] …"}}
```

Never emit `permissionDecision: "allow"` — on Claude Code that **auto-approves** the tool,
turning the guard into a blanket bypass for everything it fails to recognise. Passing through
means printing `{}`.

## Two tiers

| Tier | Scope | Shapes |
|---|---|---|
| `deny` | catastrophic and unrecoverable. Forfeited only when a segment's expansion is genuinely unreadable (`$(…)`, backticks) | recursive delete where **any** target is a root/home spelling — `/` `//` `///` `/*` `/.` `~` `~/*` `$HOME` `$HOME/*` `~user`, the expanded home path, `--no-preserve-root` included; force-push (flag **or** `+refspec`) to a protected branch, incl. bare `git push -f` while standing on it and a symbolic `HEAD`; **deleting** a protected remote branch (`git push origin :main`, `--delete`), which needs no force at all; `git push --mirror` |
| `ask` | everything else | `rm -r` outside the allowlist · `DROP TABLE/DATABASE/SCHEMA` · `TRUNCATE` · `DELETE`/`UPDATE` **without `WHERE`** · migrate `down`/`force`/`drop`/`rollback` · compose `down -v` · `volume rm` · force-remove/`prune` · `reset --hard` · `checkout/restore .` · `worktree remove --force` · force-push to a normal branch · `--force-with-lease` · `find -delete` / `-exec rm` · `sed -i` · `tee` · cluster `delete` · obfuscation (`${IFS}`, `base64 -d \| sh`) |

Decisiveness is judged **per segment**, and only real opacity forfeits it. An earlier draft
backed off from `deny` for any compound command, which meant appending `; true` defeated the
whole tier — see the audit note below.

Adapt the pattern table to your stack; **the tier split and the classes are the portable part.**

## 🔴 The second lesson: a fresh adversary, not a fresh test

The fix above was written, tested 63/63 in both directions, and verified live. An adversarial
audit against that "green" build then found **six confirmed escapes from the deny tier**,
every one reproducible. The worst returned `allow` — silently, with no reason in the
transcript — which is quieter than the auto-approved `ask` it bypassed:

| Escape | Why the matcher missed it |
|---|---|
| `sudo rm -rf /`, `env …`, `FOO=1 …`, `timeout 60 …`, `bash -c "…"` | argv[0] was read straight off token 0, so any wrapper or env assignment moved the real command out of view |
| `rm -rf / ; echo done` | "compound ⇒ not decisive" was computed over the WHOLE command, so appending anything downgraded the verdict |
| `git push origin :main`, `--delete`, `--mirror` | deleting a remote branch needs no `--force`, and the matcher only looked for force |
| `git -C /repo push -f origin main` | git's own `-C` operand survived flag-stripping and posed as the subcommand |
| `rm -rf / /home` | the target test was `all()`, so **adding** a target softened the verdict |
| `rm -rf ~/*`, `rm -rf $HOME/*` | the root set was bare literals, missing the ordinary way to empty a home directory |

Plus: exponential regex backtracking in the allowlist (17s against a 10s hook timeout, on a
string that carried `/` as its target), and a redirect (`echo '' > …/check-careful.py`) that
let one allowed command erase the guard itself.

**The transferable rules:**

1. **Your own test table only pins the spellings you thought of.** 63/63 green while
   `sudo rm -rf /` returned `allow` is the same failure as the envelope bug one level up.
   A table proves the cases in it; it never proves coverage.
2. **Test expectations can encode the vulnerability.** Two lines of that table asserted
   `rm -rf / && …` should be `ask`. They were wrong, and they would have made the fix look
   like a regression. When an audit contradicts a test, decide which one is right before
   touching either.
3. **Buy an adversary, not another pass of your own eyes.** The escapes were found by an
   agent told to break it, with the standing fact that `ask` is auto-approved so an
   escape-into-ask counts as a hole. That framing is what made the findings sharp.
4. **Pin every escape family, one line each**, so the next rewrite cannot quietly reopen
   them. The table went 63 → 97 cases; the additions are the escapes, not new features.

## Design rules (each one paid for)

- **Warn by default, deny for the two shapes nothing undoes.** The original rule here was
  "warn, never hard-block", on the sound logic that an unoverridable guard gets disabled the
  first time it is wrong. That still holds for everything recoverable. It stopped holding for
  `rm -rf ~` and force-push-to-main once measurement showed `ask` was auto-approved on
  unattended runs: there, "warn" and "no guard" are the same object.
- **Give `deny` an escape hatch, and never commit it.** `CAREFUL_ALLOW_HIGH=1` downgrades
  `deny` to `ask` and still prints the reason. Hooks inherit the agent process's environment,
  so a command the agent runs cannot set it for later invocations — that is deliberate. Writing
  it into committed config disables the tier permanently and invisibly; treat it as an
  operator's one-shot, not configuration.
- **Fail polarity is asymmetric, on purpose.**

  | Situation | Decision | Why |
  |---|---|---|
  | payload unreadable | `ask` | something was there and you could not read it — do not guess it was safe |
  | payload fine, no command field | pass `{}` | nothing to inspect; never wedge non-shell tools |
  | interpreter missing / matcher crashed | `ask` | a guard that vanishes with its interpreter is the original bug, restated |
  | empty stdin | pass `{}` | hook invoked oddly; nothing to inspect |

- **An allowlist that is not anchored is an allowlist for everything.** The earlier matcher
  stripped up to the *last* `rm` with a greedy `sed` and judged only the final target, so
  `rm -rf / && rm -rf node_modules`, `rm -rf / # rm -rf node_modules` and
  `rm -rf $(./wipe-all)/node_modules` all passed in silence. Anchor over the whole command
  (`\A…\Z`) and allow **relative paths only** — the same list once carried `bin` and `tmp` as
  `*/bin`/`*/tmp` globs, which swallowed `rm -rf /usr/bin` and `rm -rf /tmp`.
- **A skip list is a safety claim, not a convenience.** Skipping segments whose `argv[0]` is a
  read-only text tool is what stops `grep -rn "migrate down" docs/` and
  `echo "rm -rf / is dangerous"` from crying wolf. But `tee` writes, `sed -i` rewrites in
  place, `find -delete` removes — all three sat in that set for a day and made themselves
  unreachable by any rule. Before adding a name, ask what it does with a `>` or an `-i`.
- **Test in both directions, then test the consumer** ([GATES §6](../../../gates/GATES.md)):
  every dangerous pattern → the right tier fires; a set of safe commands → passes untouched;
  garbage input → the documented polarity. Shipped table: `hooks/check-careful.test.sh`, 116
  cases, pinning the decision, the envelope, every escape family an adversary found, the
  guardrail-file tier, and the heredoc rule.
  Then the live checks below.
- **Opt-in, explicitly.** The hook touches every shell command of every session — enable it as
  a deliberate config change, never silently. For unattended runs, enabled is the sane default.

## The third tier: nothing may switch the guard off

A hook wired only to the shell tool has an obvious hole: the guard file itself can be
rewritten by the file-editing tool, which that hook never sees. A guard that refuses
`rm -rf /` and can be deleted by one Edit call is not a guard. Wire the same hook to your
host's write-family tools as well, and **deny** on:

| Path | Why |
|---|---|
| the hook/matcher files themselves | this is the guard |
| the settings file(s) that register hooks | where it gets unregistered, or disabled wholesale |
| scripts your gate chain shells out to | same reasoning, one step removed |

On the shell side, a redirect (`>`) onto those same paths rises from `ask` to **deny** —
where `ask` is auto-approved it stops nothing.

**Reading** a guard file stays allowed. Denying the read blocks the ordinary "look at what
this thing does" step and buys nothing; the first draft here denied it and the table caught
it. The legitimate way to edit is a human, or a session run with the escape-hatch variable.

> ⚠️ **Limit, stated rather than hidden.** This matcher judges **command shapes**, not
> program semantics. An interpreter handed a script still writes any file it likes —
> `python3 -c "open(...,'w')..."` is not a redirect and is not caught. The write-tool tier
> raises the bar and makes the ordinary path loud; it does not seal the box. Per
> [GATES §4](../../../gates/GATES.md), say what a gate is blind to in the gate's own text.

**Heredoc bodies are data, not shell syntax**, and must be stripped before scanning — a
command whose heredoc merely *contains* redirect-shaped text is not performing that
redirect. (Found the honest way: the command installing this very fix was refused by it.)
Keep the rest of the heredoc's own command line, though — that is where a real redirect sits
(`cat <<EOF > file`).

## Verification — two steps, and step 2 is the one that was skipped

```bash
bash hooks/check-careful.test.sh     # step 1: 116/116
```

**Step 2, in a live session.** Two probes, both with zero blast radius:

```bash
git push --force nonexistent-remote-probe main
```
Must be **blocked**, citing the protected-branch reason. If it instead runs and fails with
"does not appear to be a git repository", your `deny` never reached the host — the guard is
decoration.

```bash
git push origin main --dry-run
```
Must **run**. It sits right next to the deny logic (same subcommand, same branch) without
`--force`. A guard that blocks everything is as broken as one that blocks nothing; prove the
door still opens, not just that the wall still stands.

Adding a pattern means: edit the matcher, add cases **in both directions** to the table, re-run
both steps.

## Position in the defense stack

The spec gate keeps wrong work from starting ([`spec-first`](../spec-first/SKILL.md)) → the
[gate chain](../../../gates/GATES.md) keeps broken work from landing → adversarial review
catches what gates miss → **careful** catches the one command that would make a mistake
permanent. Wire it through your platform's pre-execution hook mechanism
([HARNESS §4](../../HARNESS.md)).
