<!-- WHO READS ME: every agent before claiming anything is done — 5th in the reading order.
     I POINT TO: check-plan-sync.sh (shipped here) · ../model/SPEC-FLOW.md (quickstart as the
     acceptance script) · ../constitution/constitution-template.md Article VI (which delegates here). -->

# Gates — the executable definition of done

Prose definitions of "done" die the day an agent talks its way past them. A gate is a **script
that exits non-zero**. This file is the doctrine plus the gate catalog; adapt commands to your
stack in the constitution's **Platform Constraints** section.

## 1. The gate chain (every commit)

```bash
# adapt per stack — the SHAPE is the contract: static analysis → tests → build → wiring → docs-sync
<format-check> && <static-analysis> && <test-suite> && <build> \
  && <orphan-endpoint-gate> && <third-person-acceptance-gate> && ./gates/check-plan-sync.sh
```

| Gate | Catches | Rule |
|---|---|---|
| Format + static analysis | mechanical rot | zero warnings tolerated |
| Test suite | regressions | **beware vacuous green** — a test filter (`-run`/`--grep`) matching zero tests exits 0; assert your patterns match real names |
| Build | integration breaks | the artifact actually compiles/links |
| Orphan-endpoint | the joint nobody wired (§4) | every new route has a caller, or a recorded reason |
| Third-person acceptance (§3) — **per feature**, before its spec flips to `shipped`; automated isolation tests stand in per-commit | self-graded homework | non-privileged account hits the wall |
| Doc-sync ([`check-plan-sync.sh`](check-plan-sync.sh)) | plan/blueprint drift | **self-globbing** — never hard-points at a deletable file |

**No commit on red. No exceptions. Fix or explicitly revert.**

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

## 4. The deadliest bug class: the joint nobody wired

> Backend correct + frontend correct + **the connection never written** — and every gate green,
> because each gate checks only ONE end.

Countermeasures, all active at once:

1. The reachability principle (constitution Article V): API-only ≠ done.
2. An orphan-endpoint gate: new route ⇒ a caller exists, or an allow-listed reason.
3. The question asked at every review: **"who will CALL this?"**
4. Gate humility: document what each gate is *blind* to (method-blind? response-key-blind?) in
   the gate's own docstring — a green gate is evidence only of what it actually checks.

## 5. Reviews are adversarial and independent

Builders never graduate their own work. Review lenses are prompted to **refute** (default to
"this finding is wrong until evidence survives my own refutation"), run independently
(accuracy-vs-code · fidelity-vs-intent · security), and the orchestrator spot-checks the heaviest
findings by hand. See [`../harness/agents/tech-lead-review.md`](../harness/agents/tech-lead-review.md).

## 6. Gate hygiene

- **Self-discovery over hard paths**: a gate that names one file becomes a hostage-taker when
  that file must move or die ([`check-plan-sync.sh`](check-plan-sync.sh) globs).
- **Test the gate itself in both directions**: green stays green through legitimate change
  (file deleted → skip, not red) and red still bites (inject drift → must fail). A gate proven
  in only one direction is decoration.
- When a fix turns out to be "needed on every install", promote it from a repair path to a
  numbered migration — reconcilers don't replace versioned baselines.
