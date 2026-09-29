<!-- WHO READS ME: any agent handed work that is not a new feature — a bug, an incident, a
     vulnerability, a refactor or dependency bump, a spike, a release — and the owner deciding
     which lane a change belongs in. I POINT TO: SPEC-FLOW.md (the feature lane; the
     code-vs-spec rule) · ../gates/GATES.md (§1 the chain, §9 release gates, §10 trailers) ·
     ARCHETYPES.md (release gates and deploy commands per kind of product) ·
     ../harness/skills/plan-and-tdd/SKILL.md (the loop every code-changing lane runs) ·
     ../harness/agents/tech-lead-review.md (the security lens) · PHASE-0.md (spikes before
     the stack is chosen). -->

# Work that is not a feature

The constitution routes every feature through `specs/<id>/` and the HARD-GATE. Most commits
are not features: a bug in something already accepted, a production incident, a dependency
bump, a refactor, a question only code can answer, a release. Until v1.4.0 the kit had no word
for any of them — `grep -rni hotfix` returned nothing — so an agent either forced each one
through a new spec or skipped the process entirely. Each lane below says whether a spec is
needed, where the record goes, which gates apply, and what the commit looks like.

Two things hold in every lane: **the gate chain is green before a commit lands**, and **a
change a user, a caller or an operator could notice is behaviour** — it belongs to a spec,
whatever the lane was called when it started.

## Which lane

| The change | Lane | Spec | Commit type |
|---|---|---|---|
| New behaviour, or a change to specified behaviour | feature ([SPEC-FLOW](SPEC-FLOW.md)) | a new spec, approved first | `feat` |
| Accepted behaviour does not match its spec | [bug](#bug-in-an-accepted-feature) | a task in that spec | `fix` |
| Production is broken now | [hotfix](#hotfix-and-incident) | a task and a dated clarification in that spec, same commit | `fix` |
| A vulnerability | [security](#security-patch) | as bug, hotfix or dependency bump | `fix`, `chore(deps)` |
| Same behaviour, different code | [refactor](#refactor-dependency-bump-chore-docs) | none | `refactor` |
| A dependency bump nobody can notice | [chore](#refactor-dependency-bump-chore-docs) | none | `chore(deps)` |
| Build, CI, tooling, configuration | [chore](#refactor-dependency-bump-chore-docs) | none | `chore` |
| Documentation outside `specs/` | [docs](#refactor-dependency-bump-chore-docs) | none | `docs` |
| A question only code can answer | [spike](#spike) | none until the finding | nothing on the main branch |
| Accepted work reaching its users | [release](#release) | a status change | `chore(release)` |

Who claims each canonical prompt (the adoption audit's lens 3,
[AI-ONBOARDING §4](../AI-ONBOARDING.md)): "new feature" →
[spec-first](../harness/skills/spec-first/SKILL.md), then Spec Kit's `/speckit-specify`;
"fix bug", "hotfix", "refactor", "bump dependency" → this file for the
lane, then the per-task loop of [plan-and-tdd](../harness/skills/plan-and-tdd/SKILL.md) (red,
green, refactor, the chain, review, commit) — with the lane's entry condition standing in for
that skill's approved-spec one, since these lanes add no new spec;
"review" → [tech-lead-review](../harness/agents/tech-lead-review.md); "e2e acceptance" →
[tester-e2e](../harness/agents/tester-e2e.md); "migrate schema" → a task inside the spec that
needs the schema, never a lane of its own; "spike" and "release" → this file.

## Bug in an accepted feature

The spec says one thing and the accepted code does another. The code-vs-spec rule
([SPEC-FLOW](SPEC-FLOW.md)): when code and spec disagree, find out which one moved. If the spec
states intended behaviour the code does not deliver, the code is wrong: record a new task
(converge). If the code reflects a deliberate, owner-approved change the spec never recorded,
fix the spec with the correction marked (≠old) and a dated Clarifications entry. If you cannot
tell, ask the owner. The first case is this lane; in the second no code changes.

1. **A failing regression test first** — it reproduces the report, and it fails for the
   reported reason.
2. **The fix**, the minimum that turns it green.
3. **A task line in that spec's `tasks.md`**, checked: `- [x] T031 Fix duplicate rows on
   re-import (bug #12)`.
4. **If acceptance should have caught it**, the step that would have caught it goes into
   `quickstart.md`; re-run that step and add the result, dated, to `acceptance.md`'s free text.
5. **One commit** for all of it: `fix(import): …` with `Spec: <id>`, and
   `Bug-class: escaped-joint` when both ends were right and the connection was missing
   ([GATES §4, §10](../gates/GATES.md)).

**Why the task lands checked.** Measured on this release: an unchecked task on an `accepted`
spec turns `doc-sync` red — the spec would claim done while it is not. So the task, its test
and its fix land together. A bug whose fix cannot land in one commit stays in the tracker until
it can; or the spec goes back to `approved`, with the open task, and is re-accepted when the
task is done. `(deferred → <where>)` is for scope moved to another spec, not for a bug nobody
has fixed yet.

**New behaviour is not a bug.** "It should also handle X" when the spec never mentioned X is a
new spec, however small. And a "one-line bug fix" can be a symptom patch on one caller while
the cause sits in a shared function — the "one-line bug fix" row of
[spec-first](../harness/skills/spec-first/SKILL.md)'s anti-pattern table.

**Spec Kit's `bug` extension** (`specify extension add bug` installed `/speckit-bug-assess`,
`-fix` and `-test`, writing under `.specify/bugs/<slug>/`; checked with 1.0.12) may do the
assessing. Its files are working notes; the record the gates read is still the task line in the
spec. List the extension in Platform Constraints if you adopt it.

## Hotfix and incident

Production is broken and waiting for a spec cycle would cost more than the risk of fixing
first.

1. **Stop the harm with the smallest reversible move.** When a recent change caused it,
   `git revert <sha>` is usually that move. `git revert` does not run the pre-commit hook
   (checked with git 2.43; the hook's BLIND TO block), so run `./gates/run-chain.sh` yourself
   before pushing; CI runs it anyway.
2. **Fix under the chain.** Regression test first wherever one can be written; the chain green;
   no `--no-verify` — the careful guard asks before an agent uses it, and in an incident the
   answer is still no.
3. **Record it in the same commit**: the checked task in the affected spec, and a dated entry
   in its Clarifications — `2026-10-01 — HOTFIX (incident #7): imports over 10 MB now rejected
   instead of timing out. Owner review owed by 2026-10-03.` The entry states the behaviour the
   hotfix introduced, because a hotfix usually changes behaviour.
4. **Within the window** — two working days unless the constitution's Development Workflow
   states another — the owner either confirms the entry (edited to say so, dated) or the proper
   fix becomes a new spec. An entry still saying "owed" after its date is a finding for the
   next review.
5. **Then the lesson**, in operating files rather than a document: the test that now catches
   it, a new quickstart step, a gate, or a constitution amendment. Keep the incident narrative
   wherever your team keeps them; it is not a spec.

The deploy that ships a hotfix is still the release lane's irreversible step: a human performs
or approves it.

## Security patch

- **In your own code**: the hotfix lane, or the bug lane when nothing is exploited yet, plus a
  review with [tech-lead-review](../harness/agents/tech-lead-review.md)'s security lens and a
  regression test that reproduces the exploit. Put the advisory or CVE id in the commit body.
  For a public repository, keep exploit detail out of public commits, specs and tests until the
  fix is released — use your host's private advisory workflow if it has one.
- **In a dependency**: the dependency-bump lane below, with the advisory id in the commit body.
  If the fixed version changes behaviour your users can notice, that change needs a spec.
- **A leaked secret**: revoke or rotate it first. Deleting it from the repository, or from
  history, does not un-leak it.

## Refactor, dependency bump, chore, docs

No new spec, as long as nobody outside the code can notice the change.

- **The test is "could a user, a caller or an operator notice?"** A changed error message, a
  different default, a new log line an alert keys on, a dependency major version with new
  defaults: noticeable. That is a feature or a bug.
- **Tests prove the behaviour did not move.** If the code you are about to change has no test
  covering it, write characterization tests first — they are the refactor's red step. The chain
  green before and after.
- **One concern per commit**, typed: `refactor(scope): …`, `chore(deps): bump x 1.2.3 → 1.3.0`,
  `chore(ci): …`, `docs: …`. A refactor that serves a spec's upcoming work carries that spec's
  `Spec:` trailer; one that serves none carries none. `metrics.py`'s trailer coverage counts
  every commit, so it sits below 100% on any project that does chores; read the feat and fix
  commits in it.
- **Never mix** a refactor into a `feat` or `fix` commit: the diff then proves neither.
- **A change to Article III's layering** is not a refactor: it amends the constitution first.
- **Docs**: a correction to a spec follows the code-vs-spec rule in
  [SPEC-FLOW](SPEC-FLOW.md); everything else is a `docs` commit.

## Spike

A spike answers a question that only code can answer — does this library read those files,
is this latency reachable, does this control feel right — inside a time box, and its output is
a decision, not code.

- **The owner approves the question and the time box**, not the code. The HARD-GATE covers code
  that ships; spike code never does.
- **Where the code lives**: in `spikes/<name>/`. Put `spikes/` in `.gitignore`, so it cannot
  be committed by accident (`git add` of an ignored path refuses and asks for `-f`; checked
  with git 2.43), and exclude it from the stack slots' tools the same way as `factory/`
  ([ARCHETYPES](ARCHETYPES.md), "Stack stanzas"), so spike code never turns the chain red. To
  share it, commit it with `git add -f` on a `spike/<name>` branch, push that branch, and never
  merge it; delete the branch after the decision. No `--no-verify` is needed anywhere.
- **The finding goes where the decision lives**: into the `research.md` of the spec that needed
  it (a draft spec is fine), into Platform Constraints' rationale when it decided the stack
  ([PHASE-0](PHASE-0.md) §5), or into a new spec. Write the numbers measured, the time spent
  against the box, and what was not tried.
- **Promotion is by rewriting, never by merging.** The real implementation is written test
  first under an approved spec. Copying a snippet across is fine; it gets its test first like
  any other code.
- **Over the time box**, stop and report what is known. A spike that keeps growing has become
  unapproved implementation.

## Release

`accepted` means an independent acceptance run passed. `released` means the work reached its
users. Between them sits the step that cannot be taken back.

1. **Preconditions** — every spec in the release is `accepted`, with its `acceptance.md`; the
   chain is green on the release commit; the release gate for the archetype has passed
   ([GATES §9](../gates/GATES.md), [ARCHETYPES](ARCHETYPES.md)).
2. **The plan exists before the step** — in `plan.md`, a `## Release` section: the deploy or
   publish steps, the migration order (expand → deploy → contract, backfills as their own
   step), the rollback steps and the signal that triggers them, and any feature flag. Before
   the first release, Platform Constraints names the environments, where secrets live (never
   in the repository), and the signal that tells you a release is broken — an alert, a smoke
   check, a dashboard someone watches.
3. **A human performs or approves the irreversible step.** The agent prepares and verifies.
   The careful guard asks before the publish commands it knows — `npm`, `cargo`, `uv` and
   `poetry publish`, `twine upload`, `gem push` and `gem yank`, `gh release delete` — and lets
   their dry runs through, so a human answers the real one (checked on this release). Treat
   that as a backstop, not the gate: a deploy script it does not know is not asked about.
4. **Afterwards**, one commit flips each spec's frontmatter to `status: released`
   (`chore(release): 1.4.0`, one `Spec:` trailer per spec), then the tag. Release notes come
   from the specs that became `released` since the last tag — run this before tagging:

   ```bash
   sh <<'EOF'
   last=$(git describe --tags --abbrev=0)
   st() { awk '{ sub(/\r$/, "") } NR == 1 { if ($0 != "---") exit; next } $0 == "---" { exit }
     /^status[ \t]*:/ { v = $0; sub(/^[^:]*:[ \t]*/, "", v); sub(/[ \t]+#.*$/, "", v)
       sub(/[ \t]+$/, "", v); print v; exit }'; }
   for f in specs/*/spec.md; do
     [ -f "$f" ] || continue
     [ "$(st < "$f")" = released ] || continue
     [ "$(git show "$last:$f" 2>/dev/null | st)" = released ] && continue
     echo "${f%/spec.md}"
   done
   EOF
   ```

   Checked on a scratch repository: with specs `released`, `accepted → released` and
   `approved → accepted` since the tag, it printed only the second.
5. **Rollback** follows the plan. A spec already flipped to `released` goes back to
   `accepted` in a commit with a dated Clarifications entry; the fix takes the bug or hotfix
   lane.

## What these lanes do not cover yet

- On-call, paging and incident tooling: the kit states where the record and the lesson go,
  not how an incident is run.
- Release trains across several services: each service releases in its own lane; the kit does
  not coordinate them.
- Feature flags as a lifecycle: a flag is named in the release plan; retiring it is a chore
  the kit does not track.
