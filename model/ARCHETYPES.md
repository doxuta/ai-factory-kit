<!-- WHO READS ME: the AI and the owner choosing an archetype in Phase 0 (PHASE-0.md §4), and
     anyone wiring gates/chain.conf or careful.json for a product that is not a multi-tenant
     web app. I POINT TO: PHASE-0.md (where the choice is made) ·
     ../constitution/constitution-template.md (the slots filled from here) · ../gates/GATES.md
     (§1 the chain, §3 acceptance, §4 the joint nobody wired, §8 non-deterministic systems, §9
     release gates) · ../harness/skills/careful/SKILL.md (careful.json) · SPEC-FLOW.md (the
     monorepo layout) · NON-FEATURE-WORK.md (spikes, releases) · ../examples/todo-api/ and
     ../examples/budget-cli/ (worked examples). -->

# Archetypes — the same kit, shaped to the kind of product

The kit was distilled from one kind of product: a multi-tenant web platform with accounts, an
HTTP API, SQL and a UI. Kept verbatim, its constitution tells a CLI that API-only is not done,
tells a library to accept with a non-privileged account, and hands a firmware project a gate
that checks HTTP routes. In the 2026-09 audit's CLI simulation, the adopter had to reword
Articles V and VI on day one and record the rewording as improvised. This file is the
un-improvised version: for each kind of product, what to keep, what the analogue is, and what
the kit does not have an answer for yet.

What never changes, whatever the archetype: spec before code, approved before the first task
is ticked; the gate chain decides done; tests first; acceptance by someone other than the
builder, recorded in `acceptance.md`. What changes is *how each of those touches the product*:
the real entry point (Article V), whether there is an authorization boundary (Article VI's
conditional clause), which chain slots apply, and what the irreversible release step is.

## Summary

| Archetype | `adopt.py --profile` | Article V — the real entry point | Least-privilege acceptance | Release gate ([GATES §9](../gates/GATES.md)) |
|---|---|---|---|---|
| [Multi-tenant SaaS](#multi-tenant-saas) | `full` | the real UI, as the story's role | yes — a non-admin member of a second tenant | web service |
| [Backend / API service](#backend--api-service) | `backend` | the public gateway, real auth, the published contract | yes — a client credential with only the story's scopes | web service + contract |
| [Mobile + backend](#mobile--backend) | `full` | the app build on a device or emulator | yes, if there are accounts — a fresh install | mobile |
| [Frontend-only / static](#frontend-only--static-site) | `frontend` | the production build as users get it | usually N/A — no accounts | web service |
| [CLI](#cli) | `cli` | the installed command, listed in `--help` | usually N/A; a non-root user if it touches the system | CLI |
| [Library / SDK](#library--sdk) | `library` | the public API, imported as a user would | N/A | library |
| [Data / ML pipeline](#data--ml-pipeline) | `data` | a scheduled job whose output a named consumer reads | yes — the pipeline's own service role | data / ML |
| [Embedded / firmware](#embedded--firmware) | `embedded` | the device's real input, on real hardware | a production-configured device, where there are locked modes | embedded |
| [Game](#game) | none — `--without api-conventions,data` | a build, through the game's real input | N/A single-player; a player account online | store build (outside the kit) |
| [IaC / DevOps](#iac--devops) | `iac` | an environment stack the pipeline applies | yes — the CI role, plan-only where possible | infrastructure as code |
| [LLM / agent app](#llm--agent-app) | `llm` | the agent's entry point, calling the registered tool | yes — the agent's tool scopes are a boundary | data / ML / LLM |
| [Monorepo / multi-team](#monorepo--multi-team) | the union of the packages', usually `full` | per package | per package | per package |

Profiles decide which of the four `.claude/rules/` files are installed; no profile drops
`architecture.md` or `workflow.md`. `--without a,b` drops more; in the files `adopt.py`
writes, a link to a dropped rule becomes plain text. `adopt.py --help` prints the table.

| Profile | Rules not installed |
|---|---|
| `full` (default), `backend`, `llm` | none |
| `frontend` | `data` |
| `data` | `api-conventions` |
| `cli`, `library`, `embedded`, `iac` | `api-conventions`, `data` |

## How to read an entry

- **Constitution** — the fill for Article V's `[REAL_ENTRY_POINT]`, Article VI's
  `[ACCEPTOR]`, and whether the least-privilege clause applies or is
  `N/A — <reason> (decided <date> by <owner>)` (the template's "Adapting at ratification").
- **Chain** — `gates/chain.conf` lines that differ from a plain stack stanza (§"Stack
  stanzas"). `doc-sync`, `spec-approval` and `spec-numbers` are the kit's and are the same
  everywhere. Every `NA` carries its reason; `run-chain.sh` prints it on every run.
- **careful.json** — additions to `.claude/hooks/careful.json`, beyond the defaults (which
  already ask on IaC teardown, cloud deletes, database resets, package publishing, flash
  erase, and deny eFuse burns and raw device writes). Every pattern below was run through this
  release's `check-careful.py`, both directions (a matching command asks or denies, a near
  miss passes). Replace the deploy commands with yours; a pattern for a command you do not
  run is noise.
- **Acceptance** — who the third person is and what "the real interface" is for
  `quickstart.md`.
- **Known gaps** — where the kit has no answer. Stated so nobody assumes one.

## Multi-tenant SaaS

The kit's home turf; [`../examples/todo-api/`](../examples/todo-api/) is worked in this shape.

- **Constitution** — V: "operable in the real UI by the role the story names — API-only ≠
  done". VI: acceptor a teammate or `tester-e2e` in a fresh context; least privilege applies.
- **Chain** — `orphan-endpoints: ./gates/check-orphan-endpoints.sh` with
  `gates/orphan-endpoints.conf` (server route files, client call sites;
  [the example](../gates/orphan-endpoints.conf.example) has Python, Express and Go
  patterns). `acceptance:` your automated cross-tenant suite — create in tenant A, read from
  tenant B, expect nothing — per commit.
- **careful.json** — `"protected_branches": ["release/*"]`, and your deploy commands:
  `"extra_ask": ["\\b(make|just)\\s+(deploy|release)\\b", "\\bkubectl\\s+(apply|rollout|scale)\\b.*\\bprod"]`.
  A wrapper your team uses to reach the database (`mydb-cli`) goes in `db_clients`.
- **Acceptance** — `quickstart.md` in a browser against a deployed environment, signed in as
  a non-admin member of a second tenant; `run_as: member@tenant-b`.
- **Release** — deploy to staging, smoke, rollback rehearsed; migrations expand → deploy →
  contract.
- **Known gaps** — the orphan gate compares paths, not methods (its BLIND TO block); the kit
  ships no browser automation.

## Backend / API service

The API is the product; its callers live in other repositories.

- **Constitution** — V: "reachable through the public gateway with real authentication, and
  present in the published contract". "Who will CALL this?" has an answer by name: a consumer,
  or a contract test standing in for one. VI: least privilege applies.
- **Chain** — the orphan gate's `client:` side cannot see external callers, so point it at the
  contract tests: `server: src/api/**/*.py`, `client: tests/contract/**/*.py`. Checked on this
  release: a route with no contract test is red, and adding
  `client.post(f"/tasks/{tid}/complete")` turns it green. A route whose only callers are
  outside (a webhook) goes in `gates/orphan-allowlist.txt` with its reason.
- **careful.json** — as SaaS.
- **Acceptance** — `quickstart.md` as HTTP calls (curl or your client) against a deployed
  environment, with a credential holding only the scopes the story needs.
- **Release** — as SaaS, plus: a change that breaks the published contract is a new API
  version or a MAJOR decision recorded in the spec, never a silent edit.
- **Known gaps** — no contract-diff gate ships with the kit.

## Mobile + backend

- **Profile** — `full`: the backend half keeps `data` and `api-conventions`.
- **Constitution** — V: "usable in the app build on a device or emulator, through the screens
  the story names — backend-only ≠ done". VI: where there are accounts, least privilege
  applies — a non-privileged account on a fresh install (no cached session, OS permissions not
  yet granted).
- **Chain** — `format`, `static`, `test`: the platform's formatter in check mode, its
  analyzer, its unit tests; `build`: a debug build of each target. None were run for this
  release. `orphan-endpoints`: server = the backend's route files, client = the app's source;
  the reference gate sees literal paths only (BLIND TO).
- **careful.json** —
  `"extra_ask": ["\\bfastlane\\s+(\\w+\\s+)?(release|deploy|submit|beta)\\b", "\\beas\\s+(submit|update)\\b"]`
  (`eas update` ships code to installed apps; it is a release).
- **Acceptance** — the acceptor runs `quickstart.md` on a device or emulator; screenshots or a
  screen recording are the excerpt in `acceptance.md`.
- **Release** — signed store build, internal or beta track, staged rollout. Old app versions
  stay installed for months, so the backend keeps serving them: API changes follow expand →
  migrate → contract too.
- **Known gaps** — no device farm or UI automation; store review can reject after acceptance.

## Frontend-only / static site

- **Profile** — `frontend`: drops `data`, keeps `api-conventions` for the APIs it calls.
- **Constitution** — V: "works in the production build as users receive it — not the dev
  server — in the browsers Platform Constraints names". VI: usually
  `N/A — static content, no accounts`; acceptance still by someone else, in a fresh browser
  profile.
- **Chain** — `orphan-endpoints: NA: no server routes; the APIs it calls are checked in their
  own repositories`. `build`: the production build.
- **careful.json** —
  `"extra_ask": ["\\bvercel\\b.*\\s--prod\\b", "\\bnetlify\\s+deploy\\b.*\\s--prod\\b", "\\bfirebase\\s+deploy\\b", "\\bwrangler\\s+(pages\\s+)?deploy\\b"]`
  (Vercel and Netlify preview deploys pass; `--prod`, `firebase deploy` and any
  `wrangler … deploy` ask).
- **Acceptance** — the acceptor opens the preview deployment of the production build.
- **Release** — promote the preview to production; rollback = redeploy the previous build.
- **Known gaps** — visual regressions and accessibility are not gated by anything the kit ships.

## CLI

[`../examples/budget-cli/`](../examples/budget-cli/) is worked in this shape.

- **Constitution** — V: "reachable from the installed command and listed in its `--help`; a
  function no subcommand calls ≠ done". VI: least privilege `N/A — single-user tool, no
  accounts` — unless it runs as root or writes system paths, then a non-root user.
- **Chain** — `orphan-endpoints: NA: no network routes; every subcommand is run through the
  entry point by the e2e tests`. Do not point the reference gate at subcommands: its matching
  is unanchored on the left, so a subcommand named `import` counts as "called" by any Python
  line `import os` (checked on this release). `acceptance:` end-to-end tests that run the
  entry point as a subprocess on fixture files, or `NA: <reason>`.
- **careful.json** —
  `"extra_ask": ["\\bgit\\s+push\\b.*\\s(--tags|refs/tags/|v\\d)", "\\bgh\\s+release\\s+create\\b", "\\bgoreleaser\\s+release\\b(?!.*--snapshot)"]`
  (a pushed version tag is what most release pipelines trigger on;
  `goreleaser release --snapshot` passes).
- **Acceptance** — the acceptor installs from the built artifact (wheel, binary) in a clean
  environment, not from the source tree, and runs `quickstart.md`. Exit codes and output
  formats are part of the contract and are asserted.
- **Release** — artifacts built, installed from the artifact, quickstart run there; tag and
  publish.
- **Known gaps** — no subcommand-reachability gate; it is a test the project writes.

## Library / SDK

- **Constitution** — I is often "the public API is the contract". V: "exported from the
  public API, documented, and exercised by a test that imports it the way a user would" (from
  the package, not the internal module). VI: least privilege `N/A — no accounts`; the acceptor
  writes a consumer's use of the feature against the built package.
- **Chain** — `orphan-endpoints: NA: a library has no routes; public exports are exercised by
  the consumer tests`. `acceptance:` tests that install the built artifact into a fresh
  environment and import it — they catch what the source tree hides (a module left out of the
  package). **Go**, which has no built artifact: a consumer module in a temporary directory that
  requires the library through `go mod edit -replace` pointed at a copy of the *tracked* files
  (`git ls-files`), builds and runs — the copy is what makes it catch a package that exists on
  disk but was never `git add`-ed (a review adopter's check caught exactly that). Keep the
  script generic and the consumer program and its expected output in a test directory outside
  `gates/`: a `gates/check-*` script is guarded once it exists, so every new exported function
  would otherwise need a human's edit to the gate ([GATES §7](../gates/GATES.md)).
- **Public-API gate** — Python: `uvx griffe check <package> -s src --against <last tag>`;
  checked on this release, it exits 1 with `Public object was removed` and 0 on an unchanged
  API. Rust's `cargo semver-checks`, TypeScript's API Extractor and Go's `gorelease` (or
  `apidiff` against the last tag) do the same job; none of them was run for this release, and
  `gorelease -base=<tag>` needs that tag to be fetchable through the module proxy. Run it in the release lane: an intended break is legitimate once the
  spec records the MAJOR decision, and a per-commit slot would stay red until then.
- **careful.json** — publishing already asks by default (`npm`, `cargo`, `twine`, `uv`,
  `poetry` publish and friends); add the CLI's tag-push patterns.
- **Acceptance** — a consumer snippet from `quickstart.md`, run against the installed artifact.
- **Release** — API diff, version bump that matches it, publish dry run, then publish. A Go
  module has no publish dry run: publishing is pushing the version tag, which the module proxy
  makes permanent, so the tag push is the human's step ([GATES §9](../gates/GATES.md)); a
  consumer that fetches the tag through `GOPROXY` is the check after it.
- **Known gaps** — an API diff sees signatures, not behaviour: a function that keeps its
  signature and changes its result is a breaking change nothing flags.

## Data / ML pipeline

- **Profile** — `data`: drops `api-conventions`, keeps `data` (migrations, scoping keys).
- **Constitution** — I is often "every published number traces to its source rows". V: "the
  job is scheduled in the orchestrator and a named consumer reads its output — a transform
  nobody schedules ≠ done". VI: least privilege applies — acceptance runs as the pipeline's own
  service role (read-only on sources, write on its outputs), never the developer's broad
  credentials.
- **Chain** — `test`: unit tests on transforms over small fixture data. `acceptance:` data
  checks on a fixture run — row counts reconcile with the source, keys unique, no unexpected
  nulls. `orphan-endpoints: NA: no routes; outputs without a consumer are found in review`.
  Models: an `eval` slot ([below](#evals-for-judged-behaviour-llm-and-ml)).
- **careful.json** — warehouse clients are defaults already (`bq`, `snowsql`, `duckdb`,
  `spark-sql`, …); add
  `"extra_ask": ["\\bdbt\\s+(run|build|seed)\\b.*--full-refresh\\b", "\\bdbt\\b.*--target[= ]\\S*prod"]`.
- **Acceptance** — the acceptor runs `quickstart.md` against a copy of production-shaped data
  and reconciles totals with the source.
- **Release** — backfill or migration dry run on a copy; switch consumers to the new output.
- **Known gaps** — no lineage or data-contract gate.

## Embedded / firmware

- **Constitution** — II is often "an update that fails boots the previous image". V:
  "reachable on the device through its real input — button, serial command, radio message —
  on real hardware or a hardware-in-the-loop rig; simulator-only ≠ done". VI: where the
  product has locked modes, acceptance runs on a production-configured device (debug
  interfaces locked as shipped); otherwise N/A with the reason.
- **Chain** — `test`: host-side unit tests of the logic compiled for the host; `build`: the
  firmware image. `orphan-endpoints: NA: no routes; every command handler is reachable from the
  input dispatcher — covered by <test>`. `acceptance:` the hardware-in-the-loop suite if a rig
  is attached to CI, else `NA: hardware tests run on the bench in the release lane`.
- **careful.json** — the defaults deny eFuse burns and raw block-device writes and ask on
  flash erase; `write_flash` stays silent. Add your fleet-wide OTA command to `extra_ask`.
- **Acceptance** — someone with the hardware who did not write the code.
- **Release** — signed image, smoke on real hardware, a proven recovery path, OTA to a canary
  group first.
- **Known gaps** — no HIL runner; timing, power and flash wear are not gated.

## Game

- **Profile** — no dedicated profile: `--without api-conventions,data`. A server-backed
  multiplayer game keeps them: `full`.
- **Constitution** — V: "playable in a build — not the editor — through the game's real input;
  name the scene or menu that reaches it". VI: least privilege N/A for single-player; a
  non-admin player account online.
- **Chain** — engine-specific. Headless test runners exist for the major engines; none was run
  for this release. `build`: a headless build of one target. `orphan-endpoints: NA: no routes`.
- **careful.json** — engine caches are regenerated, so their deletion should not ask:
  `"safe_dirs": ["Library", "Temp", "Logs", "obj", "Intermediate", "DerivedDataCache"]`
  (Unity, Unreal; Godot's `.godot` is a default). Store uploads:
  `"extra_ask": ["\\bbutler\\s+push\\b", "\\bsteamcmd\\b.*\\+run_app_build\\b"]`.
- **Acceptance** — a playtester who did not build the feature runs `quickstart.md` as a play
  script: steps, and what must be on screen after each.
- **Release** — store builds and platform certification; outside the kit.
- **Known gaps** — "is it fun" is not a gate: game-feel questions are spikes
  ([NON-FEATURE-WORK](NON-FEATURE-WORK.md)), their findings numbers written into the spec.
  Large binary assets (git LFS) are not covered.

## IaC / DevOps

- **Constitution** — II is often "nothing is applied without a plan a human has read". V: "a
  module or resource is done when an environment stack the pipeline applies uses it". VI: least
  privilege applies — acceptance uses the CI role, plan-only for checks, apply only in the
  release lane; it verifies the intended access works and nothing broader does.
- **Chain** — Terraform's own `fmt -check -recursive`, `validate` and `test` commands fill
  `format`, `static` and `test`; `build`: a plan against a non-production environment with a
  plan-only role. No Terraform was installed on the machine that tested this release, so none
  of these were run. `orphan-endpoints: NA: no routes; unused modules are found in review`.
- **careful.json** — defaults ask on destroy and `state rm`. Add an ask on every apply and a
  deny on destroying anything production:
  `"extra_ask": ["\\b(terraform|tofu)\\b(\\s+-chdir=\\S+)?\\s+apply\\b", "\\bkubectl\\s+apply\\b"], "extra_deny": ["^(?=.*prod).*\\b(terraform|tofu)\\b.*\\s-?destroy\\b"]`
  (checked: `terraform -chdir=envs/prod destroy`, `TF_WORKSPACE=prod terraform destroy` and
  `terraform apply -destroy -var-file=prod.tfvars` are denied; `terraform destroy` alone
  asks). An ask is a wall only where someone answers it; an unattended run has nobody.
- **Acceptance** — the acceptor reads the saved plan (`terraform show FILE`) and checks the
  result with the least-privilege role.
- **Release** — `plan -out=FILE`, a human reads it, the saved plan is applied — a saved plan
  applies without a confirmation prompt, so handing over the file is the approval.
- **Known gaps** — drift from changes made outside the pipeline; state lives outside git.

## LLM / agent app

- **Profile** — `llm`: drops nothing; these products usually have an API and data.
- **Constitution** — II is often "model output never reaches a tool, a shell or a query
  without validation". V: "the tool is registered with the agent and exercised through the
  agent's real entry point by an eval case — a tool the model is never offered ≠ done". VI:
  tests first for everything deterministic; judged behaviour is tested by evals. Least
  privilege applies twice: an end user without privileges, and the agent's tool permissions
  as production grants them, not a developer's broad key.
- **Chain** — `test`: unit tests of prompt assembly, parsing, tool dispatch and retries, with
  the model stubbed. An extra slot, for example `eval-smoke: <your eval runner> --suite smoke`,
  runs a small set per commit; the full suite runs before `accepted` and at release.
- **careful.json** — if your eval runner has a flag that rewrites the baseline, ask on it:
  `"extra_ask": ["--update-baseline\\b"]` (use your runner's real flag name). `extra_ask` sees
  shell commands only: an edit to the baseline file through the Write or Edit tool is not
  matched, so review is what catches it.
- **Acceptance** — `quickstart.md` asserts properties or rubric scores, not exact text; it
  includes a prompt-injection case (untrusted content that tries to trigger a tool) and
  records scores and the model id in `acceptance.md`.
- **Release** — the full eval suite against the baseline with the pinned model, then the
  switch.
- **Known gaps** — see the next section; cost per request is not gated.

### Evals for judged behaviour (LLM and ML)

The doctrine is [GATES §8](../gates/GATES.md); this is how it lands in a project. It has not
yet been run end to end by an LLM or ML adopter of this kit — treat it as the plan, and
report what breaks.

- **The baseline is a file in the repository**, for example `evals/baseline.json`: score,
  sample size, model id, date, the commit it was measured on, and the spread across samples.
  Its path goes in Platform Constraints (the template has a `Models` line).
- **The threshold is the baseline minus a stated tolerance**, both in the file. Moving the
  baseline is its own reviewed commit, with the reason; a commit that edits the baseline and
  the code together is the one to read twice.
- **Pin the model** by its exact version id in Platform Constraints. **A model bump is a
  spec**: specify what should change, approve it, re-baseline, accept. The same goes for a
  prompt rewrite that is meant to change behaviour.
- **Flaky is not green.** Score N samples and gate on the aggregate; a case that passes on
  retry is recorded as unstable, not as passing.
- **Prompt injection is the injection class here.** In review
  ([tech-lead-review](../harness/agents/tech-lead-review.md)'s security lens): which untrusted
  text reaches the model (user input, fetched pages, file contents, tool results); which tools
  a model-chosen call can reach; what validates output before it touches a tool, a shell or a
  query.

## Monorepo / multi-team

- **Layout** — one `factory/`, one `.claude/`, one `specs/` and one `gates/` at the repository
  root; the root constitution holds what binds every package, and each package's stack lives
  in its own `platform.md`. The layout, spec ownership and numbering are in
  [SPEC-FLOW](SPEC-FLOW.md#numbering-teams-and-monorepos) — including why sessions start at
  the repository root: Claude Code reads the `.claude/settings.json` that registers the careful
  hook from the session's working directory, so a session started in a package runs without
  the guard.
- **Profile** — the union of the packages' needs; usually `full`.
- **Chain** — the standard slots run every package, for example
  `test: (cd packages/api && pytest -q) && (cd packages/web && npm test)`, or extra slots per
  package (`test-web: …`) next to the standard ones. Affected-only runs are your monorepo
  tool's job; the kit does not compute them.
- **careful.json** — the union of the packages' additions; `protected_branches` for release
  branches.
- **Known gaps** — the kit's gates assume one `specs/` and one chain; per-package chains, spec
  directories and owners files are the adopter's to compose.

## Stack stanzas

Each line below was run through `./gates/run-chain.sh` on this release (Linux; ruff 0.15.8,
pytest 9.0.2, mypy 1.19.1, uv 0.8.17; Go 1.24.7; Node 22.22.2; cargo 1.94.1 for the zero-test
row only). Use them as starting points; the versions you pin go in Platform Constraints.

**Keep the kit's files out of your formatter and linter.** Measured on this release: with the
kit's files in place, `ruff format --check .` wanted to reformat `gates/check-specs.py`,
`.claude/hooks/check-careful.py` and the scripts under `factory/bin/`, and `ruff check .`
failed on `gates/check-specs.py` — a red chain on day one. The obvious fix, `ruff format .`,
rewrites the guard's own matcher, and the careful guard lets it through (`{}`): a formatter is
not one of the writes it recognises. Exclude `factory`, `gates`, `.claude` and `.specify` in
the tool's own configuration; for ruff,
`extend-exclude = ["factory", "gates", ".claude", ".specify"]` under `[tool.ruff]` in
`pyproject.toml` turned both commands green. `adopt.py --check` reports a kit file that changed
anyway. ruff also reads Python code blocks inside Markdown: measured with ruff 0.16.9,
`ruff format --check .` counted the `specs/*.md` files and exited 1 on a ```` ```python ````
block holding `x=[1,2]`. Specs and quickstarts are in the `format` slot's scope unless you
exclude them or keep their code blocks formatted.

**Know whether your test runner is green with zero tests.**

| Runner | Zero tests collected | Guard |
|---|---|---|
| pytest | exit 5 — already red | none needed |
| `go test ./...` | exit 0, `[no test files]` or `[no tests to run]` | `&& test "$(go test -list '.*' ./... \| grep -c '^Test')" -gt 0` |
| `node --test` | exit 0, `# pass 0` | below |
| `cargo test` | exit 0, `0 passed` | count the passed tests in its `test result:` lines (not run through the chain for this release) |

```text
# Python, src/ layout, hatchling build backend
format: ruff format --check .
static: ruff check . && mypy --strict src
# src/ is not installed here; an installed project runs plain `pytest -q`
test: PYTHONPATH=src pytest -q
build: uv build

# Go
format: test -z "$(gofmt -l .)" || { gofmt -l .; exit 1; }
static: go vet ./...
test: go test ./... && test "$(go test -list '.*' ./... | grep -c '^Test')" -gt 0
build: go build ./...

# Node (built-in test runner)
test: out=$(node --test --test-reporter=tap 2>&1); rc=$?; printf "%s\n" "$out"; [ "$rc" -eq 0 ] && printf "%s\n" "$out" | grep -Eq "^# pass [1-9]"
```

The Go test guard was red with no tests and green with one; the Node guard was red with none,
green with one passing test, red with one failing. For JavaScript the same exclusion applies
to formatting: Prettier formats Markdown, and `npx prettier@3 --check .` flagged a kit document
under `factory/` — list `factory/`, `gates/`, `.claude/`, `.specify/` **and `specs/`** in
`.prettierignore`. Without `specs/` the `format` slot went red at spec 001 in a review run
(prettier 3.6.2 flagged `spec.md`, `plan.md`, `tasks.md` and `acceptance.md`), and
`prettier --write` there rewrites `acceptance.md`, which GATES §3 says is kept exactly as the
acceptor returned it. If the team wants Spec Kit's Markdown formatted, format everything in
`specs/` except `acceptance.md`, and do it before the acceptance run, not after.

## What the kit does not have an answer for yet

- Archetypes not listed here — desktop apps, browser extensions, compilers, scientific code —
  start from the closest entry and record the choices as ratification decisions.
- Hosts other than Claude Code: the harness and the guard need porting
  ([HARNESS §7](../harness/HARNESS.md)).
- Reachability gates for anything but HTTP routes. For a CLI, a library, a pipeline or
  firmware, reachability is a test the project writes and review reads.
- No archetype other than the multi-tenant web one has been run end to end by a real adopter;
  the CLI entry is backed by the audit's simulation and the budget-cli example.
