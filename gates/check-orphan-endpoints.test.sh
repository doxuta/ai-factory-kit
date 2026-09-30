#!/usr/bin/env bash
# Two-direction test for check-orphan-endpoints.sh on a tiny fixture: one route wired to a
# caller, one orphan. GATES.md §6: a gate proven in only one direction is decoration; every
# RED row pins its reason. It also runs the three example route regexes shipped in
# orphan-endpoints.conf.example against matching fixtures, so the examples cannot rot.
#
# Run: bash gates/check-orphan-endpoints.test.sh      Exit 0 = all green.

HERE="$(cd "$(dirname "$0")" && pwd)"
GATE="$HERE/check-orphan-endpoints.sh"
EXAMPLE="$HERE/orphan-endpoints.conf.example"
PASS=0; FAIL=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# project <dir>: a project root holding gates/check-orphan-endpoints.sh (the gate reads
# gates/orphan-endpoints.conf relative to its own location)
project() { mkdir -p "$1/gates"; cp "$GATE" "$1/gates/"; }
conf() { local d="$1"; shift; printf '%s\n' "$@" > "$d/gates/orphan-endpoints.conf"; }
run() { # run <want-exit> <label> <project-dir> [args]
  local want="$1" label="$2" dir="$3" got
  shift 3
  ( cd "$TMP" && bash "$dir/gates/check-orphan-endpoints.sh" ${1+"$@"} ) >"$TMP/out" 2>&1
  got=$?
  if [ "$got" = "$want" ]; then PASS=$((PASS+1)); else
    FAIL=$((FAIL+1)); printf '  FAIL  want exit %s, got %s — %s\n' "$want" "$got" "$label"
    sed 's/^/        /' "$TMP/out"; fi
}
said() {
  if grep -qF -- "$2" "$TMP/out"; then PASS=$((PASS+1)); else
    FAIL=$((FAIL+1)); printf '  FAIL  output lacks %s — %s\n' "$2" "$1"; sed 's/^/        /' "$TMP/out"; fi
}
never_said() {
  if grep -qF -- "$2" "$TMP/out"; then
    FAIL=$((FAIL+1)); printf '  FAIL  output contains %s — %s\n' "$2" "$1"; sed 's/^/        /' "$TMP/out"
  else PASS=$((PASS+1)); fi
}
# example_route <n>: the n-th "# route:" line of the shipped example, uncommented
example_route() { grep '^# route: [^ ]' "$EXAMPLE" | sed -n "${1}p" | sed 's/^# route: //'; }
PY_ROUTE="$(example_route 1)"
EXPRESS_ROUTE="$(example_route 2)"
GO_ROUTE="$(example_route 3)"

# the fixture: a Python API with two routes, a TypeScript client
fixture() { # fixture <dir> <client-calls-complete: yes|no>
  local d="$1"
  project "$d"
  mkdir -p "$d/src/api" "$d/web/src"
  cat > "$d/src/api/tasks.py" <<'PYSRC'
from fastapi import APIRouter
router = APIRouter()

@router.get("/tasks")
def list_tasks(): ...

@router.patch("/tasks/{task_id}/complete")
def complete(task_id: str): ...
PYSRC
  {
    echo 'export const listTasks = () => fetch(`/api/tasks?page=1`);'
    if [ "$2" = yes ]; then
      echo 'export const complete = (id: string) => fetch(`/api/tasks/${id}/complete`, { method: "PATCH" });'
    fi
  } > "$d/web/src/api.ts"
  conf "$d" "# configured" "server: src/api/**/*.py" "route: $PY_ROUTE" "client: web/src/**/*.ts"
}

echo "== GREEN: wired routes must pass =="
fixture "$TMP/wired" yes
run 0 "both routes have a caller (template literal, /api prefix, query string)" "$TMP/wired"
said "summary" "2 route(s): 2 called, 0 allow-listed"

run 0 "--list prints each route and its caller" "$TMP/wired" --list
said "list" "/tasks/{task_id}/complete"
said "list" "called at web/src/api.ts:2"

fixture "$TMP/allow" no
printf '# route reason\n/tasks/{task_id}/complete called by the mobile app, repo acme/mobile\n' > "$TMP/allow/gates/orphan-allowlist.txt"
run 0 "the uncalled route is allow-listed with a reason" "$TMP/allow"
said "summary" "1 called, 1 allow-listed"

fixture "$TMP/stale" yes
printf '/gone kept for the old client\n' > "$TMP/stale/gates/orphan-allowlist.txt"
run 0 "a stale allow-list entry warns, it does not fail" "$TMP/stale"
said "warning" "no longer defines"

fixture "$TMP/fstr" no
printf 'import requests\nrequests.patch(f"{BASE}/tasks/{task_id}/complete")\n' > "$TMP/fstr/web/src/cli.py"
conf "$TMP/fstr" "server: src/api/**/*.py" "route: $PY_ROUTE" "client: web/src/**/*.ts" "client: web/src/**/*.py"
run 0 "a Python f-string caller satisfies the {task_id} route" "$TMP/fstr"

fixture "$TMP/pct" no
printf 'url := fmt.Sprintf("/tasks/%%s/complete", id)\n' > "$TMP/pct/web/src/client.go"
conf "$TMP/pct" "server: src/api/**/*.py" "route: $PY_ROUTE" "client: web/src/**/*.ts" "client: web/src/**/*.go"
run 0 "a %s format-string caller satisfies it too" "$TMP/pct"

project "$TMP/na"
conf "$TMP/na" "# no network surface" "NA: single-user CLI, no routes"
run 0 "NA with a reason" "$TMP/na"
said "reason printed" "N/A - single-user CLI, no routes"

project "$TMP/express"
mkdir -p "$TMP/express/server" "$TMP/express/web"
printf "const router = express.Router();\nrouter.get('/users/:id', show);\napp.post(\`/users\`, create);\n" > "$TMP/express/server/users.js"
printf 'fetch(`/users/${u.id}`);\naxios.post("/users", body);\n' > "$TMP/express/web/client.js"
conf "$TMP/express" "server: server/**/*.js" "route: $EXPRESS_ROUTE" "client: web/**/*.js"
run 0 "the shipped Express example regex, wired fixture" "$TMP/express"
said "express routes found" "2 route(s): 2 called"

project "$TMP/go"
mkdir -p "$TMP/go/internal/http" "$TMP/go/web"
printf 'mux.HandleFunc("GET /items/{id}", getItem)\nmux.HandleFunc("/healthz", health)\n' > "$TMP/go/internal/http/routes.go"
printf 'fetch(`/items/${id}`)\nfetch("/healthz")\n' > "$TMP/go/web/app.ts"
conf "$TMP/go" "server: internal/http/**/*.go" "route: $GO_ROUTE" "client: web/**/*.ts"
run 0 "the shipped Go net/http example regex, wired fixture" "$TMP/go"
said "go routes found" "2 route(s): 2 called"

echo "== RED: it must actually bite =="
fixture "$TMP/orphan" no
run 1 "one route has no caller" "$TMP/orphan"
said "names the orphan" "/tasks/{task_id}/complete   defined at src/api/tasks.py:7"
never_said "the wired one is not blamed" "• /tasks   defined"

project "$TMP/unwired"
run 1 "no gates/orphan-endpoints.conf: not wired" "$TMP/unwired"
said "reason" "not wired: no gates/orphan-endpoints.conf"

project "$TMP/copied"
cp "$EXAMPLE" "$TMP/copied/gates/orphan-endpoints.conf"
run 1 "the example copied unchanged (all comments): not wired" "$TMP/copied"
said "reason" "declares nothing"

fixture "$TMP/noserver" yes
conf "$TMP/noserver" "server: app/**/*.py" "route: $PY_ROUTE" "client: web/src/**/*.ts"
run 1 "server globs match no file" "$TMP/noserver"
said "reason" "match no file"

fixture "$TMP/noroute" yes
conf "$TMP/noroute" "server: src/api/**/*.py" "route: @app\\.route\\(\"([^\"]+)\"" "client: web/src/**/*.ts"
run 1 "the route regex matches nothing (wrong framework syntax)" "$TMP/noroute"
said "reason" "matched nothing"

fixture "$TMP/self" no
conf "$TMP/self" "server: src/api/**/*.py" "route: $PY_ROUTE" "client: src/**/*.py" "client: web/src/**/*.ts"
run 1 "a route's own definition is not its caller (overlapping globs)" "$TMP/self"
said "reason" "/tasks/{task_id}/complete"

fixture "$TMP/prefix" no
printf 'fetch(`/api/tasks/${id}/complete`)\n' > "$TMP/prefix/web/src/api.ts"
run 1 "calling /tasks/:id/complete does not call the /tasks route" "$TMP/prefix"
said "reason" "• /tasks   defined"

fixture "$TMP/concat" no
printf 'fetch("/api/tasks/" + id + "/complete");\nfetch(`/api/tasks`);\n' > "$TMP/concat/web/src/api.ts"
run 1 "a concatenated caller is not seen (BLIND TO: false red; allow-list or make it literal)" "$TMP/concat"
said "reason" "• /tasks/{task_id}/complete   defined"

fixture "$TMP/excluded" no
printf 'fetch(`/tasks/${id}/complete`)\n' > "$TMP/excluded/web/src/api.test.ts"
conf "$TMP/excluded" "server: src/api/**/*.py" "route: $PY_ROUTE" "client: web/src/**/*.ts" "exclude: **/*.test.ts"
run 1 "a caller only in an excluded test file does not count" "$TMP/excluded"

echo "== config errors (exit 2) =="
fixture "$TMP/noreason" no
printf '/tasks/{task_id}/complete\n' > "$TMP/noreason/gates/orphan-allowlist.txt"
run 2 "allow-list entry without a reason" "$TMP/noreason"
said "reason" "has no reason"

project "$TMP/na-empty"
conf "$TMP/na-empty" "NA:"
run 2 "NA without a reason" "$TMP/na-empty"

fixture "$TMP/na-mixed" yes
printf 'NA: no routes\n' >> "$TMP/na-mixed/gates/orphan-endpoints.conf"
run 2 "NA mixed with server/route/client" "$TMP/na-mixed"

fixture "$TMP/badrx" yes
conf "$TMP/badrx" "server: src/api/**/*.py" "route: @router\\.(get(" "client: web/src/**/*.ts"
run 2 "route regex does not compile" "$TMP/badrx"

fixture "$TMP/nogroup" yes
conf "$TMP/nogroup" "server: src/api/**/*.py" "route: @router\\.get" "client: web/src/**/*.ts"
run 2 "route regex without a capturing group" "$TMP/nogroup"

fixture "$TMP/badkey" yes
printf 'servers: src/**/*.py\n' >> "$TMP/badkey/gates/orphan-endpoints.conf"
run 2 "unknown key" "$TMP/badkey"

fixture "$TMP/noclient" yes
conf "$TMP/noclient" "server: src/api/**/*.py" "route: $PY_ROUTE"
run 2 "client: missing" "$TMP/noclient"

run 0 "--help" "$TMP/wired" --help
run 2 "unknown argument" "$TMP/wired" --bogus

echo
echo "passed $PASS, failed $FAIL"
[ "$FAIL" -eq 0 ]
