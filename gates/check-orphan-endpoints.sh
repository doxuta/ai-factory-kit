#!/usr/bin/env bash
# check-orphan-endpoints.sh — reference orphan-endpoint gate: every route the server defines has
# a caller in the client code, or a recorded reason (from the AI Factory Kit; GATES.md §4).
# Chain slot: orphan-endpoints (gates/chain.conf).
#
#   ./gates/check-orphan-endpoints.sh          # check
#   ./gates/check-orphan-endpoints.sh --list   # also print every route and where it is called
#
# Stack-neutral: it knows nothing about your framework. You tell it, in
# gates/orphan-endpoints.conf (start from gates/orphan-endpoints.conf.example), where routes are
# DEFINED, how to pull the path out of a definition, and where they are CALLED. Globs and paths
# are relative to the project root (the directory above gates/); ** recurses. Full-line "#"
# comments only — a regex may contain " #". Each key may repeat; every repeat is used.
#
#   server:  <glob>    files that define routes                          (1 or more)
#   route:   <regex>   run over each server file (re.MULTILINE); group 1, or (?P<path>...),
#                      is the route path                                  (1 or more)
#   client:  <glob>    files that call routes                            (1 or more)
#   exclude: <glob>    files left out on both sides (tests, generated code)       (optional)
#   param:   <regex>   how a path parameter is written inside a route; replaces the default
#                      :name {name} <name> <type:name> [name] *           (optional)
# or, instead of all of that, one line:
#   NA: <reason>       the product has no routes (a CLI, a library, firmware...). Printed on
#                      every run. Equivalent to "orphan-endpoints: NA: <reason>" in chain.conf.
#
# A route counts as CALLED when some client file contains its path, with each parameter
# matching any run of characters except / ? # quotes and whitespace (so /tasks/:id matches
# `/tasks/${id}`, f"/tasks/{task_id}", "/tasks/%s"), followed by a quote, ?, #, ), ], comma,
# semicolon, backslash, whitespace or end of line. A file matched by a server glob never counts
# as a caller, or every route would call itself from its own definition.
#
# gates/orphan-allowlist.txt (optional): one "<route> <reason>" per line, the route exactly as
# extracted (see --list). For routes whose caller is outside this repo: webhooks, health
# checks, a public API. The reason is required.
#
# Exit: 0 green (or NA) · 1 red: an uncalled route, no config ("not wired"), server globs that
# match no file, or a route regex that matches nothing · 2 config error (bad key or regex,
# NA or allowlist entry without a reason, NA mixed with other keys).
#
# BLIND TO (a green gate is evidence only of what it actually checks):
#   * METHODS. It compares paths: GET /tasks and POST /tasks are one route; a client that
#     only GETs satisfies both.
#   * DYNAMIC CALLERS. A path built by concatenation ("/tasks/" + id + "/complete"), from
#     constants in another file, or by a generated client is not seen: the route reads as an
#     orphan (false red). Allow-list it with the reason, or make the call site literal.
#   * PREFIXES AND SUFFIXES. The left side is unanchored, so a client path "/api/tasks" calls
#     the route "/tasks" (a mount prefix — usually right) and "/admin/tasks" calls it too
#     (wrong). Short routes like "/" match almost anything.
#   * WHETHER THE CALL IS REACHABLE. A caller in dead code, a comment or a test fixture the
#     globs include still counts. Exclude tests; review the rest.
#   * ROUTES YOUR REGEX DOES NOT MATCH. Routes registered in a way the regex misses are
#     invisible. Run --list after changing the server code's style and compare the count.
#   * FILES IN HIDDEN DIRECTORIES: ** does not descend into .dirs.
#   * ITSELF. Two-direction test: gates/check-orphan-endpoints.test.sh.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
case "${1:-}" in
  -h|--help) sed -n '2,/^set -euo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 0 ;;
  ""|--list) ;;
  *) echo "check-orphan-endpoints.sh: unknown argument '$1' (try --help)" >&2; exit 2 ;;
esac
cd "$HERE/.."
python3 - "${1:-}" <<'PY'
import glob, os, re, sys

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(errors="replace")  # legacy code page: print "?", do not crash
    except (AttributeError, ValueError):
        pass

LIST = sys.argv[1] == "--list"
CONF = "gates/orphan-endpoints.conf"
ALLOW = "gates/orphan-allowlist.txt"
KEYS = ("server", "route", "client", "exclude", "param")
DEFAULT_PARAM = r":[A-Za-z_]\w*|\{[^}/]*\}|<[^>/]*>|\[[^\]/]*\]|\*\w*"
ARG = r"[^/?#\s'\"`]+"
AFTER = r"/?(?=[?#'\"`\s)\],;\\]|$)"


def config_error(msg):
    print("❌ %s: %s" % (CONF, msg))
    sys.exit(2)


def not_wired(msg):
    print("❌ orphan-endpoint gate not wired: %s" % msg)
    print("   Copy gates/orphan-endpoints.conf.example to %s and fill it in, or declare it" % CONF)
    print("   not applicable with a reason: 'NA: <reason>' there, or")
    print("   'orphan-endpoints: NA: <reason>' in gates/chain.conf.")
    sys.exit(1)


if not os.path.isfile(CONF):
    not_wired("no %s" % CONF)

cfg = dict((k, []) for k in KEYS)
na = None
with open(CONF, encoding="utf-8") as fh:
    for lineno, line in enumerate(fh, 1):
        line = line.rstrip("\r\n")
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if text.startswith("NA:"):
            reason = text[3:].strip()
            if not reason:
                config_error("line %d: NA needs its reason ('NA: <reason>')" % lineno)
            na = reason
            continue
        m = re.match(r"^([a-z]+)[ \t]*:[ \t]*(.*)$", text)
        if not m or m.group(1) not in KEYS:
            config_error("line %d: %r - expected one of %s, followed by ':'"
                         % (lineno, text, ", ".join(KEYS)))
        if not m.group(2).strip():
            config_error("line %d: %s: has no value" % (lineno, m.group(1)))
        cfg[m.group(1)].append(m.group(2).strip())

configured = [k for k in KEYS if cfg[k]]
if na is not None:
    if configured:
        config_error("NA and %s both declared - it is one or the other" % ", ".join(configured))
    print("✅ orphan endpoints: N/A - %s (%s)" % (na, CONF))
    sys.exit(0)
if not configured:
    not_wired("%s declares nothing (only comments?)" % CONF)
for key in ("server", "route", "client"):
    if not cfg[key]:
        config_error("no %s: line - server, route and client are all required" % key)

route_rxs = []
for pattern in cfg["route"]:
    try:
        rx = re.compile(pattern, re.MULTILINE)
    except re.error as exc:
        config_error("route regex %r does not compile: %s" % (pattern, exc))
    if rx.groups < 1:
        config_error("route regex %r has no capturing group for the path" % pattern)
    route_rxs.append(rx)
try:
    param_rx = re.compile("|".join("(?:%s)" % p for p in cfg["param"]) or DEFAULT_PARAM)
except re.error as exc:
    config_error("param regex does not compile: %s" % exc)


def expand(globs):
    out = set()
    for g in globs:
        out.update(p for p in glob.glob(g, recursive=True) if os.path.isfile(p))
    return out


excluded = expand(cfg["exclude"])
server_files = sorted(expand(cfg["server"]) - excluded)
client_files = sorted(expand(cfg["client"]) - excluded - set(server_files))
if not server_files:
    print("❌ orphan endpoints: the server globs (%s) match no file - the gate would check "
          "nothing. Fix the globs, or declare NA with a reason until the first route exists."
          % ", ".join(cfg["server"]))
    sys.exit(1)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


routes = {}   # path -> [(file, line)]
for path in server_files:
    text = read(path)
    for rx in route_rxs:
        for m in rx.finditer(text):
            route = m.group("path") if "path" in rx.groupindex else m.group(1)
            if not route:
                continue
            routes.setdefault(route, []).append((path, text.count("\n", 0, m.start()) + 1))
if not routes:
    print("❌ orphan endpoints: the route regex matched nothing in %d server file(s) - the gate "
          "would check nothing. Fix the regex (compare with your router's syntax), or declare NA "
          "with a reason until the first route exists." % len(server_files))
    sys.exit(1)

allow = {}
if os.path.isfile(ALLOW):
    with open(ALLOW, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            parts = text.split(None, 1)
            if len(parts) < 2 or not parts[1].strip():
                print("❌ %s line %d: %r has no reason - '<route> <reason>'" % (ALLOW, lineno, text))
                sys.exit(2)
            allow[parts[0]] = parts[1].strip()


def caller_rx(route):
    r = route.rstrip("/") or "/"
    parts, pos = [], 0
    for m in param_rx.finditer(r):
        if m.end() == m.start():
            continue
        parts.append(re.escape(r[pos:m.start()]))
        parts.append(ARG)
        pos = m.end()
    parts.append(re.escape(r[pos:]))
    return re.compile("".join(parts) + AFTER, re.MULTILINE)


client_text = [(p, read(p)) for p in client_files]
called, allowed, orphans, warnings = {}, [], [], []
for route in sorted(routes):
    rx = caller_rx(route)
    hit = None
    for path, text in client_text:
        m = rx.search(text)
        if m:
            hit = (path, text.count("\n", 0, m.start()) + 1)
            break
    if hit:
        called[route] = hit
        if route in allow:
            warnings.append("%s is allow-listed but has a caller (%s:%d) - drop the entry"
                            % (route, hit[0], hit[1]))
    elif route in allow:
        allowed.append(route)
    else:
        orphans.append(route)
for route in sorted(set(allow) - set(routes)):
    warnings.append("%s: allow-list entry for a route the server no longer defines - drop it" % route)

if LIST:
    for route in sorted(routes):
        where = ", ".join("%s:%d" % loc for loc in routes[route][:3])
        if route in called:
            state = "called at %s:%d" % called[route]
        elif route in allowed:
            state = "allow-listed: %s" % allow[route]
        else:
            state = "NO CALLER"
        print("  %-40s %s  (defined %s)" % (route, state, where))
for w in warnings:
    print("⚠️  %s" % w)
scope = "server %d file(s), client %d file(s)" % (len(server_files), len(client_files))
if orphans:
    print("❌ ORPHAN ENDPOINTS - %d of %d route(s) have no caller in the client files (%s):"
          % (len(orphans), len(routes), scope))
    for route in orphans:
        where = ", ".join("%s:%d" % loc for loc in routes[route][:3])
        print("   • %s   defined at %s" % (route, where))
    print("   Who will CALL this? Wire the caller, or add '<route> <reason>' to %s." % ALLOW)
    sys.exit(1)
print("✅ orphan endpoints - %d route(s): %d called, %d allow-listed (%s)"
      % (len(routes), len(called), len(allowed), scope))
PY
