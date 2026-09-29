---
name: careful
description: >
  Deterministic pre-execution guard for an agent's shell and file-edit tools (Claude Code hooks,
  Bash and PowerShell). Denies the un-undoable — recursive delete of / or $HOME, force-push or
  delete of a protected branch, raw block-device writes and eFuse burns, any write, move or
  delete of the guard's own files, deleting .git with no remote. Asks on the destructive but
  recoverable — rm -r, DROP/TRUNCATE, cloud and IaC teardown, migrate down, publish/unpublish,
  reset --hard, --no-verify, sed -i. The last line of defense for autonomous runs. Matcher
  after gstack /careful (MIT, github.com/garrytan/gstack).
---
<!-- WHO READS ME: whoever wires guardrails for an agent that runs shell commands — especially
     unattended — and whoever adapts or upgrades the guard. I POINT TO: ../../HARNESS.md (§4
     where this sits in the anatomy; §7 hosts and platforms) · ../../../gates/GATES.md (§4 say
     what a gate is blind to; §6 test the guard in both directions, including the consumer) ·
     ../../../model/ARCHETYPES.md (careful.json additions per archetype) · ../spec-first/SKILL.md
     (the first line of the same defense stack). -->

# Careful — confirm before the un-undoable

An agent reminding itself to be careful is a probabilistic guard; it fails exactly on the runs
nobody is watching. The contract here: a **deterministic pre-execution hook** that inspects
every shell command and every file edit and stops the destructive ones. The model can forget;
the hook cannot.

## Where it runs

| Host / platform | Status |
|---|---|
| Claude Code on Linux, macOS, WSL (Linux filesystem) | Supported. For v1.4.0 the test table ran on Linux under bash 3.2.57 (the macOS version) and 5.2, Python 3.8 and 3.11; it was not run on a Mac |
| Claude Code on native Windows, hooks under Git Bash | Best-effort. PowerShell payloads and backslash paths are handled and pinned in the table, but no run on a real Windows host has been made |
| Native Windows **without** Git Bash | **No guard.** Claude Code then runs hooks in PowerShell, where the registered `bash …` command cannot run; a hook that fails that way is a non-blocking error, so every call proceeds |
| Other hosts (Codex, Gemini, Copilot, Cursor, …) | Port by hand: decision envelope, tool names, path fields and `$CLAUDE_PROJECT_DIR` are Claude Code's. See [HARNESS](../../HARNESS.md) §7 |

**One installed copy.** `adopt.py` installs the hook into `.claude/hooks/` — `check-careful.py`
(the matcher), `check-careful.sh` (the shim), `careful.json` (your additions),
`check-careful.test.sh` and `careful-corpus.txt` — and leaves no copy under
`.claude/skills/careful/`. That is the only copy that runs. The kit copy under
`factory/harness/skills/careful/hooks/` is what `adopt.py --upgrade` installs from; only kit
maintainers edit it. (v1.3 installed the matcher twice: the documented procedure edited and
tested the unregistered copy, the test went green, and the live guard was unchanged — F10.)
`adopt.py --check` fails while a `.claude/skills/careful/hooks/` directory exists, and
`--upgrade` removes a byte-identical v1.3 copy.

## Install, adapt, register — in that order

1. `python3 factory/bin/adopt.py --profile <archetype>` installs `.claude/hooks/`.
2. **Adapt `.claude/hooks/careful.json` now**, while the agent can still edit it. It is
   additive only — every list is added to the defaults, nothing in it removes one:

   | Key | Effect | Example |
   |---|---|---|
   | `protected_branches` | force-push or delete → **deny**; fnmatch patterns | `["develop", "release/*"]` |
   | `db_clients` | commands that execute SQL; DROP/TRUNCATE/unbounded DELETE through them → ask | `["mydb-cli"]` |
   | `safe_dirs` | relative dirs (fnmatch) whose recursive delete is routine and regenerated → silent; `~/` entries are home-anchored | `["obj", "Library"]` |
   | `extra_ask` | Python regexes matched against each shell segment as written → ask | `["\\bmake\\s+deploy\\b"]` |
   | `extra_deny` | the same → **deny** | `["\\bterraform\\s+destroy\\b.*\\bprod\\b"]` |

   What to add per archetype: [ARCHETYPES](../../../model/ARCHETYPES.md). Anything malformed —
   invalid JSON, an unknown key (`extra_denny`), a regex that does not compile — is **not**
   ignored: every shell command that would have passed gets `ask`, naming the error; deny
   stays deny. A typo that quietly switched a rule off is the failure this file exists to end.
3. Check it: `python3 .claude/hooks/check-careful.py --check-config`, then
   `bash .claude/hooks/check-careful.test.sh`.
4. First commit; create a remote and push (until one exists, `.git` is the only copy of your
   history — see the deny tier). Then `python3 factory/bin/adopt.py --register-guard`, which
   merges both matchers from [`settings.json.template`](../../settings.json.template) into
   `.claude/settings.json`.
5. Run the live probes below.

After registration `careful.json` is a guarded file: the agent is denied, and changing it is a
human edit (or a session whose host environment carries `CAREFUL_ALLOW_HIGH=1`). Upgrading the
guard is `python3 factory/bin/adopt.py --upgrade` — meant to be run and reviewed by a human; the
guard asks when the agent runs it.

## 🔴 Read first: the guard that was there but was not on

This skill shipped for 2.5 months with a hook that **did nothing**, and with a green test the
whole time. The hook printed its decision as a top-level `{"permissionDecision":"ask", …}`.
Claude Code reads a PreToolUse decision only from inside `hookSpecificOutput`, so the unknown
field was dropped and the command ran. The check — "7/7 dangerous commands asked" — read the
**script's stdout** and never asked whether the host honoured it. Upstream gstack shipped the
identical bug (CHANGELOG `1.64.0.0`: *"deny meant allow"*).

1. **A guard is not verified until you verify the CONSUMER.** Producing the right bytes proves
   nothing. Trigger a real destructive command in a live session and watch the host stop it.
2. **How strong `ask` is depends on the SURFACE.** With the host in a skip-permissions mode, a
   hook `ask` was auto-approved on the desktop/terminal surface — measured — and raised a real
   *Allow once / Deny* dialog on mobile/remote control. **`deny` is a wall everywhere; `ask`
   is a wall wherever a human is actually looking.** Do not rely on `ask` for unattended runs,
   and do not scatter it either: where someone IS looking it is a real dialog, and a guard
   that interrupts routine work gets switched off.

Correct shape (Claude Code; find your own host's contract before porting):

```json
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"[careful] …"}}
```

Never emit `permissionDecision: "allow"` — on Claude Code that **auto-approves** the tool,
turning the guard into a blanket bypass for everything it fails to recognise. Passing through
means printing `{}`.

## Three tiers

| Tier | Shapes |
|---|---|
| `deny` — nothing undoes it | recursive delete (`rm -r`, `find -delete` without a filter, `Remove-Item -Recurse`, `rd /s`, `rsync --delete`) of `/`, `$HOME`, any directory above `$HOME`, `/home` / `/Users` / `C:\Users\<name>`, or everything in one of them (`~/*`, `"$DIR/"*` with `DIR` unset); force-push (flag or `+refspec`) or delete (`:main`, `--delete`, `gh api -X DELETE …/refs/heads/main`) of a protected branch, `--mirror`, `--force --all`, and a force-push whose branch cannot be named (detached or unborn `HEAD`, `$VAR`, `$(…)`); raw block-device writes (`dd of=/dev/sda`, `> /dev/disk4`, `mkfs`/`wipefs -a`/`blkdiscard`/`sgdisk --zap-all` on a device, `diskutil eraseDisk`); eFuse burns (`espefuse burn_*`, `idf.py efuse-burn`); recursive delete of `.git`, `.specify` or `.specify/memory` in a repository with **no remote**, and of the project directory itself; every write, move, link, delete, `chmod` or `git checkout/restore/rm` of a guarded file (next section) |
| `ask` — destructive but recoverable, or unreadable | `rm -r` outside the safe list · SQL `DROP`/`TRUNCATE`/`DELETE`/`UPDATE` without `WHERE` through a DB client, including warehouses (`bq`, `snowsql`, `duckdb`, `spark-sql`, `clickhouse-client`, …) · ORM resets (`prisma migrate reset`, `rails db:drop`, `manage.py flush`, `artisan migrate:fresh`, `redis-cli FLUSHALL`, `dropdb`, …) · migrate down · cloud and IaC teardown (`terraform`/`tofu`/`pulumi`/`cdk destroy`, `apply -destroy`, `state rm`, `helm uninstall`, `kubectl delete`, `aws s3 rm --recursive`, `aws … delete-*`, `gcloud … delete`, `az … delete`) · flash erase (`esptool erase_flash`, `st-flash erase`, `nrfjprog --eraseall`) · publish and unpublish (`npm publish`/`unpublish`, `cargo publish`/`yank`, `twine upload`, `gh release delete`, …) · `git commit/push --no-verify`, `commit -n`, `git config core.hooksPath`, `git -c core.hooksPath=…` · `adopt.py --upgrade` · `reset --hard` · `checkout/restore .` · `clean -f` · `branch -D` · `--force-with-lease` and force-push to other branches · `sed -i` / `perl -i` · compose `down -v` · edits to gate configuration (`gates/*.conf`, `gates/orphan-allowlist.txt`) and creating a **new** `gates/check-*` script · writes to a dot-entry in `$HOME` or a system path (`/etc`, `/usr`, …) · anything piped into a shell that is not a readable literal · a command name built at runtime · a command over 256 K characters |
| pass | everything else — printed as `{}`, so the host's own permission flow decides |

Adapt the lists to your stack through `careful.json`; **the tier split and the classes are the
portable part.** Why cloud teardown is `ask`, not `deny`: whether `terraform destroy` erases
production or a throwaway stack depends on credentials the matcher cannot see; an IaC adopter
who knows which one it is promotes it with `extra_deny`. Why raw devices are `deny`: one wrong
letter in `of=/dev/sdX` erases the host disk, the same class as `rm -rf /`; embedded work
flashes boards with `write_flash`, which stays silent.

## The guarded files: nothing may switch the guard off

| Path (normalised, case-folded) | Why |
|---|---|
| `.claude/hooks/**` — matcher, shim, `careful.json`, tests | this is the guard |
| `.claude/settings.json`, `.claude/settings.local.json` (any `.claude/`, incl. `~/.claude/`) | where hooks are registered, or disabled wholesale with `disableAllHooks` |
| managed settings: `/etc/claude-code/**`, `/Library/Application Support/ClaudeCode/**`, `C:\Program Files\ClaudeCode\**` | the same switch, one level up; writable by an agent running as root, as in most containers |
| `gates/run-chain.sh`, `gates/check-*.sh`, `gates/check-*.py`, `gates/hooks/**` | the gate chain the guard protects |
| `harness/skills/careful/hooks/**`, including under `factory/` | the copy an upgrade installs |
| `harness/settings.json.template`, including under `factory/` | the wiring `adopt.py --register-guard` copies into `.claude/settings.json`; that command stays allowed because it can only restore the kit's wiring, so its source must not be editable |
| `.specify/scripts/**` | scripts the Spec Kit flow shells out to |

**Deny** covers the file-edit tools (`Write`, `Edit`, `MultiEdit`, `NotebookEdit`) and, on the
shell side, every redirect (`>`, `>>`, `>|`, `&>`, `2>`), `rm`, `mv`, `cp`, `ln`, `install`,
`truncate`, `dd of=`, `tee`, `sponge`, `sed -i`, `perl -i`, editors, `chmod`/`chown`, `rsync`,
`git rm`, `git checkout … --`, `git restore`, `git mv`, `git clean <path>`, `find -delete` or
`find -exec` whose traversal reaches the guard, `xargs` fed a listing of it, `cp -r`/`rsync`/
`tar -C`/`unzip -d` into a directory holding it, PowerShell `Remove-Item`/`Move-Item`/
`Set-Content`/`Out-File`/`Copy-Item`, and deleting or moving any directory that holds these
files (`.claude`, `gates`).
A path is normalised before it is matched — `//`, `/./`, `..`, backslashes, case, NTFS trailing
dots and `::$DATA`, globs expanded against the disk, symlinks resolved — because v1.3 matched
the literal spelling and `.claude//hooks/x`, `.CLAUDE/Hooks/x`, `>|` and
`C:\proj\.claude\hooks\x` each passed with `{}` (F8, F44), as did `rm`, `mv`, `cp`, `ln`,
`truncate`, `git rm`, `git checkout HEAD~1 -- …` on the guard (F9).

Two edits stay possible, and shown: gate configuration (`gates/chain.conf`, `gates/*.conf`,
`gates/orphan-allowlist.txt`) asks, because the adopter wires it — but a quiet change turns a
red gate green. A `gates/check-*` script that does **not exist yet** asks, so feature 001 can add
a project gate after registration; once it exists it is guarded. **Reading** a guarded file is
always allowed — the first draft denied the read, which blocked the ordinary "look at what this
does" step and bought nothing.

The registered command **fails closed**: if `check-careful.sh` is missing or broken it exits 2,
which Claude Code treats as a block, and names `.claude/hooks/` on stderr. A plain
`bash <missing file>` exits 127, which Claude Code treats as a non-blocking error — deleting the
shim used to switch the guard off for every later call (F9).

## 🔴 The second lesson: a fresh adversary, not a fresh test

The v1.3.0 fix was tested 63/63 in both directions and verified live. An adversarial audit then
found **six confirmed escapes from the deny tier** — `sudo rm -rf /` and `FOO=1 rm -rf /`
returned `{}` (argv[0] read off token 0), `rm -rf / ; echo done` downgraded to ask, `git push
origin :main` needed no `--force`, `git -C /repo push -f` hid the subcommand, `rm -rf / /home`
softened by *adding* a target, `rm -rf ~/*` was missing from the root set.

It happened again in v1.4.0, which is why this is a lesson and not a story. The v1.3.2 matcher
split commands on a regex and tokenised with `shlex`. Measured 2026-09-29, each of these
returned `{}` for `rm -rf /`: `if true; then rm -rf /; fi`, `(rm -rf /)`, `f(){ rm -rf /; }`,
`echo $(rm -rf /)`, `bash <<EOF` with `rm -rf /` in the body, `echo "rm -rf /" | sh` — and a
129-character `echo x | base64 --- --- …` took **69 s** against the 10 s hook timeout (a
timed-out hook does not block). The matcher is now a quote-, substitution- and heredoc-aware
lexer, one linear pass per nesting level. Then a generator wrapped ten deny-tier cores in random
shell constructs: of 4,000 variants, three escaped — all `case … in a)` inside `$( )`, whose
`)` closed the substitution early. After the fix, 16,000 more escaped none, and a seeded
generator now runs inside the test table.

**The transferable rules:**

1. **Your own test table only pins the spellings you thought of.** A table proves the cases in
   it; it never proves coverage. Generate combinations as well as listing escapes.
2. **Test expectations can encode the vulnerability.** When an audit contradicts a test, decide
   which one is right before touching either.
3. **Buy an adversary, not another pass of your own eyes** — and tell it that `ask` is
   auto-approved, so an escape into `ask` counts as a hole.
4. **Pin every escape family, one line each**, so the next rewrite cannot quietly reopen them.
5. **Slowness is an escape.** A hook the host kills at its timeout renders no decision. The
   matcher answers `ask` at 7 s on its own, inspects 256 K characters in full (beyond that:
   the head for deny, then `ask`), and the table asserts every adversarial size stays under
   5 s. (The 7 s self-timeout uses SIGALRM: Linux and macOS have it, Windows Python does not.)

## 🔴 The third lesson: measure the FALSE POSITIVES, or the guard gets switched off

Replaying **6,638 real shell commands** from 48 hours of work through the v1.2 guard: **800
asks** — one interruption every eight commands. Three rules produced 85% of it: `-i` listed as
a "writes in place" flag caught `grep -i` (594), any redirect onto an absolute or home path
flagged `cat > ~/notes.md` (89), SQL keywords matched the word "Update" in a grep pattern (9).
After fixing those: 800 → 77.

1. **A guard's false-positive rate is a safety property, not an ergonomics one.** One dialog per
   eight commands trains people to dismiss without reading, then to switch the guard off.
2. **Measure it against real traffic, not against your test table.** The table said green; the
   corpus said one in eight.
3. **Precision beats scope.** Every fix above made the matcher narrower.

v1.4.0 numbers, from real runs. `careful-corpus.txt` holds 381 ordinary commands across stacks
(git, JS, Python, Go, Rust, JVM, .NET, Ruby/PHP/Elixir, mobile, containers, IaC, embedded,
data, PowerShell): **0 interrupted**, and the table fails if one ever is. That corpus is
constructed, so the real-traffic replay was repeated on the **2,002 unique commands** from the
agent sessions that built and audited this kit: v1.3.2 interrupted 165 (8.2%), v1.4.0
interrupts 89 (4.4%). Each of the 89 is a rule doing what it says: 40 denies on writes, moves
and deletes of guard files and gate scripts, and on protected pushes (those sessions probed
exactly that); 22 `sed -i`; 19 inline Python that opens a guarded path and writes (kit
maintenance scripts, mostly — the kit repository does not register the guard); 8 other asks
(`core.hooksPath`, `branch -D`, force-push, `checkout .`, `adopt.py --upgrade`, a command name
built at runtime). The 8 commands v1.3.2 denied and v1.4.0 allows each passed a destructive
string as quoted **data** to a probe; none executed it. Replay your own history the same way:
it is the only number about your cost.

## Design rules (each one paid for)

- **Warn by default, deny for the shapes nothing undoes.** "Warn, never hard-block" holds for
  everything recoverable; it stopped holding for `rm -rf ~` and force-push-to-main once `ask`
  was measured auto-approved on unattended runs.
- **Give `deny` an escape hatch, and never commit it.** `CAREFUL_ALLOW_HIGH=1` in the host's
  environment downgrades deny to ask and still prints the reason. Hooks inherit Claude Code's
  environment, so a command the agent runs cannot set it for later hook runs, and the settings
  files whose `env` key could set it are guarded.
- **Fail polarity is asymmetric, on purpose.**

  | Situation | Decision |
  |---|---|
  | payload unreadable, matcher crashed, Python missing, time budget spent, command over 256 K characters | `ask` |
  | shim missing or broken (registered command) | exit 2: block |
  | `careful.json` invalid | `ask` on everything that would pass; deny stays deny |
  | no command field, not a write tool, empty stdin | pass `{}` |

- **Decisiveness is judged per word, and only real opacity forfeits it.** A literal `/` next to
  a `$(…)` is still a literal `/`; an unset `$DIR` in front of `/` is treated as empty, because
  that is what bash does (`rm -rf "$STEAMROOT/"*`). A force-push whose branch cannot be read is
  denied, not asked: an unresolvable destination is a reason to stop.
- **Substitutions run.** `echo $(rm -rf /)` executes `rm`; `$(…)`, backticks, `<(…)`, heredocs
  fed to a shell, `sh -c`, `eval`, `ssh host '…'`, `git -c alias.x='!…'` and literals piped into
  a shell are judged as the commands they are.
- **An allowlist that is not anchored is an allowlist for everything.** Safe dirs are relative
  names only; `..` climbs out of nothing; an absolute twin never rides the list (`bin` and
  `tmp` once did, as `*/bin`, and swallowed `rm -rf /usr/bin`). `bin`, `lib`, `out` stay off it
  because they hold committed files in many repos — this kit's `bin/` included.
- **A skip list is a safety claim.** A segment whose argv[0] only reads text (`grep`, `echo`,
  `cat`, …) skips the SQL and extra rules, so `grep -rn "migrate down" docs/` does not cry wolf.
  Redirects are judged on every segment regardless.
- **Test in both directions, then test the consumer** ([GATES](../../../gates/GATES.md) §6).

## What it is blind to

Per [GATES](../../../gates/GATES.md) §4, a gate says what it cannot see, in its own text:

- **Program semantics.** An interpreter handed a script — `python3 x.py`, `node -e`, a Makefile
  target, an npm script, `docker run -v /:/host …` — writes and deletes whatever it likes.
  Inline code is flagged only when it opens a guarded path by name and writes, or hands a
  destructive literal to `system()`; both are string heuristics, and building the path from
  parts defeats them.
- **Whole-tree swaps.** `git checkout <branch>`, `git switch`, `git reset --hard <old>`,
  `git stash pop`, `patch < file`, or `tar -x`/`unzip` into the project root can restore a tree
  without the guard; the matcher judges the paths a command names.
- **Anything outside the hooked tools**: a human's terminal, CI, git hooks, other command-running
  tools the matcher is not wired to. (Any tool routed to this hook whose input has a string
  `command` is inspected as a POSIX command.)
- **Native Windows without Git Bash** (see *Where it runs*), and every host that is not Claude
  Code until it is ported.
- **Formatters and fixers run over the whole tree.** `ruff format .`, `ruff check --fix .` or
  `npx prettier --write .` at the project root rewrite `.claude/hooks/check-careful.py` and the
  gate scripts, and pass silently: a formatter is not a write shape this matcher recognises
  (measured on this release). Keep the kit's directories out of the formatter's scope
  ([ARCHETYPES](../../../model/ARCHETYPES.md), "Stack stanzas"); `adopt.py --check` reports a
  kit file that changed anyway.
- **A session started below the project root.** Claude Code reads the shared
  `.claude/settings.json` from the session's primary working directory (its settings docs, read
  2026-09-29; not observed live), so a session opened in a monorepo package runs without the
  root's hook registration. Start sessions at the repository root.

## Verification — two steps, and step 2 is the one that was skipped

```bash
bash .claude/hooks/check-careful.test.sh   # step 1: passed 550, failed 0
```

(Before `--register-guard` it reads 543 and prints `SKIP` for the wiring checks, which test the
registered command in `.claude/settings.json`.)

Step 1 builds its own fixtures — throwaway repos on `main`, a feature branch, detached and
unborn `HEAD`, with and without a remote; a fake `$HOME` and project; a clean copy of the hook —
so it passes on any branch and in any checkout state. (v1.3.2 read 141/142 on every feature
branch, in detached CI checkouts and in a fresh repo, because one row asked the caller's own
checkout which branch it was on — F26.) It pins decision and envelope for every row, the
generated escapes, the size limits, the fail-closed wiring, the no-Python fallback, your
`careful.json`, and the false-positive corpus.

**Step 2, in a live session**, after the first commit. Both probes work in a repository with
no remote, and neither has any blast radius:

```bash
git push --force nonexistent-remote-probe main
```
Must be **blocked**, citing `[careful] force-push to the protected branch 'main'`. If it
instead runs and fails with *"'nonexistent-remote-probe' does not appear to be a git
repository"*, your `deny` never reached the host — the guard is decoration.

```bash
git push --dry-run . HEAD:refs/heads/careful-probe
```
Must **run** and print `* [new branch] HEAD -> careful-probe`: a dry run into the repository
itself creates nothing and needs no remote. It sits next to the deny logic (same subcommand)
without `--force`. A guard that blocks everything is as broken as one that blocks nothing.

Optional third probe, for the file-edit matcher: ask the agent to **Write**
`.claude/hooks/careful-probe.txt`. It must be denied. If the file appears, the
`Write|Edit|MultiEdit|NotebookEdit` matcher is not registered — fix that; a human deletes the
file, because the shell side will (correctly) refuse the agent.

Adding a pattern means: `careful.json` for your project, or — for kit maintainers — the matcher
in `factory/harness/skills/careful/hooks/`, with rows **in both directions** in the table and a
clean corpus run, then both steps again.

## Position in the defense stack

The spec gate keeps wrong work from starting ([`spec-first`](../spec-first/SKILL.md)) → the
[gate chain](../../../gates/GATES.md) keeps broken work from landing → adversarial review
catches what gates miss → **careful** catches the one command that would make a mistake
permanent. Wire it through your platform's pre-execution hook mechanism
([HARNESS](../../HARNESS.md) §4).
