<!-- WHO READS ME: every agent before claiming anything is done — 5th in the reading order;
     whoever wires gates/chain.conf in feature 001 (the walking skeleton).
     I POINT TO: run-chain.sh + chain.conf.example (the chain) · the check-*.sh gates shipped
     here (§7) · ../model/SPEC-FLOW.md (quickstart as the acceptance script; spec frontmatter)
     · ../model/ARCHETYPES.md (slots and release gates per kind of product) ·
     ../model/NON-FEATURE-WORK.md (the release lane) · ../bin/metrics.py (§10)
     · ../constitution/constitution-template.md Article VI (which delegates here). -->

# Gates — the executable definition of done

Prose definitions of "done" die the day an agent talks its way past them. A gate is a **script
that exits non-zero**. This file is the doctrine plus the gate catalog; adapt commands to your
stack in the constitution's **Platform Constraints** section.

## 1. The gate chain (every commit)

```bash
./gates/run-chain.sh          # runs the slots in gates/chain.conf in order, stops at the first red
./gates/run-chain.sh --list   # shows each slot and its state without running anything
```

The SHAPE is the contract: format → static analysis → tests → build → wiring → acceptance
tests → spec and doc sync. [`gates/chain.conf`](chain.conf.example) declares each slot as a
shell command, as `NA: <reason>`, or as `TODO`. Exit 0 is green, 1 is red, 2 means chain.conf
itself is broken.

| Slot | Catches | Command comes from | Rule |
|---|---|---|---|
| `format` | mechanical rot | you — your formatter in check mode | rewrites nothing, fails on a diff |
| `static` | mechanical rot | you — lint / type check | zero warnings tolerated |
| `test` | regressions | you | **beware vacuous green** — a test filter (`-run`/`--grep`) matching zero tests exits 0; assert your patterns match real names |
| `build` | integration breaks | you | the artifact actually compiles/links |
| `orphan-endpoints` | the joint nobody wired (§4) | kit: [`check-orphan-endpoints.sh`](check-orphan-endpoints.sh) + your `orphan-endpoints.conf`, or `NA: <reason>` | every route has a caller, or a recorded reason |
| `acceptance` | a wall (isolation, permission) that a later commit breaks | you — automated isolation / acceptance tests (the cross-tenant probe), or `NA: <reason>` | runs **per commit**. The per-feature run by someone other than the builder is §3's `acceptance.md`, checked by `spec-approval` |
| `doc-sync` | specs that disagree with their own tasks and names; plan drift | kit: [`check-plan-sync.sh`](check-plan-sync.sh) | **self-globbing** — never hard-points at a deletable file |
| `spec-approval` | code ahead of spec approval; `accepted` without an acceptance record | kit: [`check-spec-approval.sh`](check-spec-approval.sh) | a ticked task on a draft spec is red |
| `spec-numbers` | two specs with one number after a merge | kit: [`check-spec-numbers.sh`](check-spec-numbers.sh) | `NNN-` or `YYYYMMDD-HHMMSS-` prefixes, each once |
| release — not a chain slot | the irreversible step | the release lane (§9) | a human performs or approves it |

**What the kit ships and what you wire.** The kit ships the scripts behind `doc-sync`,
`spec-approval` and `spec-numbers`, and a configurable reference for `orphan-endpoints`.
`format`, `static`, `test`, `build` and `acceptance` are your stack's commands; the kit cannot
know them. On a fresh adoption those first six slots say `TODO`, and `TODO` is red: the chain
is honestly red until feature 001, the walking skeleton
([`../model/PHASE-0.md`](../model/PHASE-0.md)), gives each one a command or an `NA` with its
reason. §7 lists every file.

**N/A needs a reason, and the reason is printed on every run.** A slot that does not apply to
the product — no routes in a CLI, no authorization boundary in a single-user tool — is
`NA: <reason>`, never a deleted line and never `true`. `run-chain.sh` refuses a chain.conf
that leaves out a standard slot, and one in which every slot is N/A, because a chain that checks
nothing is not green. Whether the reason is true is a review question.

**No commit on red. No exceptions. Fix or explicitly revert.** Two mechanisms enforce it, both
installed by feature 001 once its slots are wired, never at adoption (before that they would
refuse every commit): [`hooks/pre-commit`](hooks/pre-commit) (`adopt.py --install-git-hook`)
refuses the commit locally — `git commit --no-verify` skips it, and the careful guard asks
before an agent does that — and [`ci/github-actions.yml`](ci/github-actions.yml)
(`adopt.py --ci github`) runs the same chain on every push and pull request, where nothing
skips it. `gates/chain.conf` decides what "green" means, so the careful guard asks before an
agent edits it; the gate scripts themselves are denied to agent edits.

## 2. Claims are not evidence

- An agent (including you) saying "tests pass" is testimony. The orchestrator **re-runs the
  gates** and pastes output.
- A `file:line` citation is checked against the real file before it is believed.
- A reviewer's finding is **fixed or refuted with evidence** — never silently dropped, never
  bulk-accepted. Both failure modes are real: sycophantic acceptance and quiet shelving.

## 3. Third-person acceptance (the self-grading trap)

Privileged accounts bypass authorization **by construction** — an admin testing an ACL wall
walks through where the wall should be. Every acceptance run that touches permissions uses a
**non-privileged account**, in the real interface, following the feature's `quickstart.md`.
If provisioning grants no default permissions, the builder literally *cannot* see their own
mistake without this gate — which is exactly why it exists.

**The record.** Per feature, before its spec's status moves to `accepted`, someone other than
the builder runs `quickstart.md` and writes `specs/<id>/acceptance.md` — or, when the acceptor
is the `tester-e2e` agent, which has no Write tool, returns the record and the orchestrator
saves it unchanged:

```markdown
# Acceptance — 012-payment-qr
accepted_on: 2026-10-02
accepted_by: <who ran quickstart.md — never the builder>
run_as: <account/role used, or "n/a — no authorization boundary">
result: pass
(free text below: what was run, output excerpts)
```

The `spec-approval` slot ([`check-spec-approval.sh`](check-spec-approval.sh)) is red for any
spec marked `accepted`, `released` or (legacy) `shipped` without a valid record. The
least-privilege part is conditional: `run_as` names the non-privileged account wherever the
product has an authorization boundary, and says `n/a` with that reason where it has none. The
independent part is not conditional. The gate proves a well-formed record exists — not that
the run happened, nor who ran it; its BLIND TO block says so, and review covers the rest.

## 4. The deadliest bug class: the joint nobody wired

> Backend correct + frontend correct + **the connection never written** — and every gate green,
> because each gate checks only ONE end.

Countermeasures, all active at once:

1. The reachability principle (constitution Article V): API-only ≠ done.
2. An orphan-endpoint gate: new route ⇒ a caller exists, or an allow-listed reason. The kit's
   stack-neutral reference is [`check-orphan-endpoints.sh`](check-orphan-endpoints.sh): you give
   it the route regex and the server and client globs. A product without routes marks the slot
   `NA: <reason>`; [`../model/ARCHETYPES.md`](../model/ARCHETYPES.md) names the analogue for
   other shapes of product.
3. The question asked at every review: **"who will CALL this?"**
4. Gate humility: document what each gate is *blind* to (method-blind? response-key-blind?) in
   the gate's own docstring — a green gate is evidence only of what it actually checks.

## 5. Reviews are adversarial and independent

Builders never graduate their own work. Review lenses are prompted to **refute** (default to
"this finding is wrong until evidence survives my own refutation"), run independently
(accuracy-vs-code · fidelity-vs-spec · security), and the orchestrator spot-checks the heaviest
findings by hand. See [`../harness/agents/tech-lead-review.md`](../harness/agents/tech-lead-review.md).

## 6. Gate hygiene

- **Self-discovery over hard paths**: a gate that names one file becomes a hostage-taker when
  that file must move or die ([`check-plan-sync.sh`](check-plan-sync.sh) globs).
- **Test the gate itself in both directions**: green stays green through legitimate change
  (file deleted → skip, not red) and red still bites (inject drift → must fail). A gate proven
  in only one direction is decoration.
- **Both directions is not enough when a gate hands its verdict to someone else — test the
  CONSUMER.** A gate that only *emits* a verdict has a second half you did not test: the thing
  that reads it. Measured: this kit's own `careful` hook printed a correct-looking "ask" that
  its host silently ignored, because the decision sat at the wrong nesting level. Both
  directions of its table passed for 2.5 months while the guard blocked nothing. Producing the
  right bytes is not evidence; trigger the real condition end-to-end and watch the consumer
  act. Upstream gstack found the identical bug by the identical route.
- **A green table proves its rows, never its coverage — buy an adversary.** The same guard,
  once fixed and passing 63/63 in both directions, still let `sudo rm -rf /` through as a
  silent allow: the table pinned only the spellings its author thought of. An agent tasked
  with *breaking* it found six confirmed escapes in one pass. Two of those table rows turned
  out to assert the vulnerable behavior as correct, so the fix first looked like a
  regression — when an audit contradicts a test, settle which is right before editing
  either. Pin each escape family as its own row afterwards; that is what stops the next
  rewrite from quietly reopening it.
- **Ask of every gate: who answers this when nobody is watching — and does that answer differ
  by surface?** A confirm/approve step is only protection where someone is present to refuse.
  Measured on a production host in skip-permissions mode: the same hook's "ask" was
  auto-approved on the desktop surface and raised a real dialog on mobile. The first
  measurement alone produced a confident, WRONG rule ("only a hard refusal is real") that stood
  in the doctrine for a day. One surface is not the system — and the corollary cuts both ways:
  a soft verdict you scatter freely becomes a dialog somebody has to dismiss, and a gate that
  interrupts routine work gets switched off, after which it gates nothing.
- **Count what a gate costs on real traffic, not on its own fixtures.** A gate that fires on
  ordinary work gets dismissed unread and then disabled, which is indistinguishable from having
  no gate. Measured: this kit's guardrail passed 127/127 of its own cases while interrupting one
  in eight of 6,638 real commands, 85% of it from three over-broad rules of its own. Replay a
  real corpus through any gate that interrupts a human, and treat the false-positive rate as a
  safety number. Since 1.4.0 the guard's own test enforces it: 381 ordinary commands in
  `careful-corpus.txt` must pass uninterrupted, so a rule that starts crying wolf fails the
  build instead of a user's patience.
- **A hook does not run in your shell's environment.** Measured with git 2.43: committing from a
  linked worktree hands the pre-commit hook `GIT_DIR` and `GIT_INDEX_FILE` as absolute paths. A
  chain slot whose tests built a scratch repository (`git init`, `add`, `commit` in a temp dir)
  committed into the outer repository, set `core.bare=true` on it, and the real commit died with
  "cannot lock ref 'HEAD'". Every test passed when run by hand. `run-chain.sh` now unsets those
  variables, and its test commits through the real hook from a worktree.
- When a fix turns out to be "needed on every install", promote it from a repair path to a
  numbered migration — reconcilers don't replace versioned baselines.

## 7. What ships vs what you wire

`adopt.py` installs the kit's `gates/` into the project's `gates/` — all of it except this file,
with `hooks/` and `ci/` only when their flags ask for them. Every gate carries a BLIND TO block
in its header and is proven in both directions by a `*.test.sh` installed beside it
(`check-specs.py` through the three gates that use it, the hook through `run-chain.test.sh`).

| Kit file | Installed as | Role | You configure |
|---|---|---|---|
| [`run-chain.sh`](run-chain.sh) | `gates/run-chain.sh` | the runner (§1) | — |
| [`chain.conf.example`](chain.conf.example) | `gates/chain.conf.example`, and `gates/chain.conf` if absent | the slot list; first six slots `TODO` | **yes** — every `TODO` becomes a command or `NA: <reason>` |
| [`check-plan-sync.sh`](check-plan-sync.sh) | `gates/` | `doc-sync`: spec-corpus mode by default; docs mode for `docs/*-plan.md` views | nothing |
| [`check-spec-approval.sh`](check-spec-approval.sh) | `gates/` | `spec-approval` | nothing |
| [`check-spec-numbers.sh`](check-spec-numbers.sh) | `gates/` | `spec-numbers` | nothing |
| [`check-specs.py`](check-specs.py) | `gates/` | the one spec parser behind the three above | — |
| [`check-orphan-endpoints.sh`](check-orphan-endpoints.sh) | `gates/` | `orphan-endpoints`, reference | `gates/orphan-endpoints.conf`, optional `gates/orphan-allowlist.txt` |
| [`orphan-endpoints.conf.example`](orphan-endpoints.conf.example) | `gates/` | example config: Python, Express, Go routes | copy it to `.conf` |
| [`hooks/pre-commit`](hooks/pre-commit) | `gates/hooks/`, with `--install-git-hook` | local refusal (§1) | — |
| [`ci/github-actions.yml`](ci/github-actions.yml) | `.github/workflows/factory-gates.yml`, with `--ci github`; never overwritten | the chain in CI | your toolchain setup steps |
| `GATES.md` | stays in `factory/gates/` | this doctrine | — |
| [`../bin/metrics.py`](../bin/metrics.py) | stays in `factory/bin/` | the numbers (§10) | commit trailers |

**`gates/orphan-endpoints.conf`** holds either one line, `NA: <reason>`, or these keys, each
repeatable: `server: <glob>` (files that define routes), `route: <regex>` (group 1 is the path),
`client: <glob>` (files that call them), and optionally `exclude: <glob>` and `param: <regex>`.
Unconfigured, the gate is red with "not wired". `gates/orphan-allowlist.txt` takes one
`<route> <reason>` per line. The script header gives the matching rules and what it is blind
to — methods, and paths built by concatenation, above all.

**What you wire, and where it lives:** the five stack slots in `gates/chain.conf`; an eval
suite for judged behaviour (§8) as an extra slot; release gates (§9) in the release lane. A
gate you write yourself goes beside the kit's as `gates/check-<name>.sh`, where the careful
guard protects it like the kit's, and joins the chain as a slot.

**Ownership.** Kit scripts are kit-owned: `adopt.py --upgrade` replaces them when unmodified,
and agents may not edit them. `gates/chain.conf`, `gates/*.conf` and `orphan-allowlist.txt` are
yours; the guard asks before an agent edits them.

**Upgrading from 1.3.x.** The bare `./gates/check-plan-sync.sh` now finds `specs/` itself
(before, it read only `docs/` and was red without one); a wired `check-plan-sync.sh docs` is
unchanged. Existing specs need the frontmatter at line 1 — the pre-1.4.0 worked example put it
in a ```` ```yaml ```` fence, which is now red. Specs past `draft` need `approved_by` and
`approved_on`; specs marked `shipped` need `acceptance.md`. For work accepted before 1.4.0 whose
evidence lives in a commit or pull request, the record says so, dated when it happened. Where no
evidence exists, the honest status is `approved` until someone runs `quickstart.md`. The
1.3.x blueprint "understate" check (the `epic_sentinels` map inside `check-plan-sync.sh`) is
gone; if you had filled it, keep that code as its own gate.

## 8. Non-deterministic systems

The chain assumes one input gives one verdict. An LLM call, a sampled model or a provider-side
model update breaks that: the same commit can pass on one run and fail on the next. The rules
below keep "no commit on red" meaningful anyway. No LLM or ML product has yet adopted this kit
end to end, so they are doctrine, not measurement: they follow from the rules above and from the
one statistical gate the kit has run on itself — the careful guard's corpus replay (§6), where a
rate over a recorded corpus, not a pass/fail row, was the number that mattered.

- **Split what is deterministic from what is judged.** Parsing, prompt assembly, tool dispatch,
  retries and output-schema validation are ordinary code: TDD, `test` slot. Only the model's
  judgement goes to evals.
- **An eval suite is the test for the judged part**: a versioned golden set (inputs with the
  properties or rubric an answer must meet), a scorer, a threshold. Give it its own slot
  (`eval: <command>`) so its cost and its N/A are visible.
- **Thresholds are measured, not chosen.** Record a baseline in the repository — score, sample
  size, model id, date, commit — and gate on it with a stated tolerance. Moving the baseline is
  a reviewed commit with its reason, never an edit that turns red into green.
- **Pin the model.** An exact model version in the constitution's Platform Constraints, not an
  alias that moves under you. A model bump changes behaviour, so it is a spec: specify,
  approve, re-baseline, accept.
- **Flaky is not green.** A test or eval that passes on retry is red until it is fixed, or
  quarantined with a reason and a task. Never rerun until green. Cut variance where the
  provider allows (temperature 0, a fixed seed); otherwise score N samples, gate on the
  aggregate, and keep the observed spread in the baseline.
- **Budget the runs.** A small smoke set per commit; the full suite before a spec moves to
  `accepted` and again at release (§9). Say which in chain.conf's comments.
- **Acceptance of judged behaviour** asserts properties or rubric scores, not exact bytes;
  `acceptance.md` records the scores and the model id.
- **Input the model reads is untrusted.** For these products prompt injection is the injection
  class, and an agent's tool permissions are an authorization boundary — review them as such.

## 9. Release gates

The chain says a commit may land. Nothing in it says a release may ship. In the spec lifecycle,
`accepted` means an independent acceptance run passed; `released` means the work reached its
users through the release lane in [`../model/NON-FEATURE-WORK.md`](../model/NON-FEATURE-WORK.md).
Release gates run in that lane, not per commit, and they differ more by kind of product than
anything else in this file.

**The irreversible step gets a human.** The agent prepares and verifies; a person runs, or
explicitly approves, the step that cannot be taken back. The careful guard asks before the
commands it knows; a release gate does not rely on that.

| Product | Gate before the step | The irreversible step (a human's) |
|---|---|---|
| Web service / SaaS | deploy to a staging environment, smoke test, rollback rehearsed; migrations ordered expand → deploy → contract, backfills as their own step | production deploy; production migration |
| Library / SDK | public-API diff against the last release; version bump that matches it (semver); a publish dry run (`npm publish --dry-run`, `cargo publish --dry-run`) | publishing to the registry |
| CLI | release artefacts built; installed from the artefact (not the source tree) in a clean environment; `quickstart.md` run there | tagging and publishing the release |
| Mobile | signed store build; internal or beta track; staged rollout plan | store submission; widening the rollout |
| Embedded / firmware | signed image; smoke on real hardware; a proven recovery path; OTA to a canary group first | flashing or OTA to the fleet |
| Infrastructure as code | `terraform plan -out=FILE` (or `tofu`), and a human reads that plan (`terraform show FILE`) | `terraform apply FILE` — a saved plan applies **without a confirmation prompt** (Terraform 1.16 and OpenTofu docs), so handing over the file is the approval |
| Data / ML / LLM | backfill or migration dry run on a copy; full eval suite against the recorded baseline with the pinned model (§8) | switching production to the new data, model or prompt |

After the step, the spec's status becomes `released`. Release notes come from the specs — the
ones that moved to `released` — not from memory. The per-archetype detail is in
[`../model/ARCHETYPES.md`](../model/ARCHETYPES.md).

## 10. Commit trailers and the numbers

[`../model/LEVELS.md`](../model/LEVELS.md) names the measure that matters: first-pass land
rate, escaped joints, owner review time. git can supply part of that, if commits say which spec
they serve. The convention — git trailers, in the last paragraph of the message, one per line:

```text
feat(payments): QR checkout confirms before charging

Spec: 012-payment-qr
Task: T014
```

- `Spec: <id>` — every commit that implements, fixes or amends a spec (repeat it for two).
- `Task: T014` — optional; the task or tasks the commit lands.
- `Bug-class: escaped-joint` — on the fix commit for a §4 bug ("both ends correct, connection
  missing") that got past the gates.

`python3 factory/bin/metrics.py` (run from the project root; `--json` for machines) prints
trailer coverage, first-pass land rate (feat commits not followed within N commits by a fix or
revert for the same spec), escaped joints, and approval latency — days from a spec's first
commit to its `approved_on`, a proxy for owner review time, not the thing itself. Its BLIND TO
block matters more than its numbers: a correction without its trailer is invisible, so the land
rate rises exactly when discipline falls. Read coverage first. It is a report, not a gate.
