#!/usr/bin/env python3
"""Destructive-command matcher for the careful pre-execution guardrail (AI Factory Kit).

Reads one PreToolUse payload (JSON) on stdin and prints one hook decision on stdout.
The classes are portable; the individual patterns are examples. Adapters extend them through
careful.json next to this file (additive only), never by editing this file.

THE ENVELOPE IS LOAD-BEARING. Claude Code reads a PreToolUse decision only from
hookSpecificOutput.{hookEventName,permissionDecision,permissionDecisionReason}. The v1.2 guard
printed a top-level "permissionDecision", which the host drops, so it was inert from
2026-06-25 to 2026-09-10 while its own test stayed green. Upstream gstack hit the same bug
(CHANGELOG 1.64.0.0: "deny meant allow"). Do not "simplify" the envelope, and never print
permissionDecision "allow": that AUTO-APPROVES the tool. Passing through means printing {}.

HOW STRONG "ask" IS DEPENDS ON THE SURFACE. Measured on the source factory: in a
skip-permissions mode a hook "ask" was auto-approved on the desktop/terminal surface and raised
a real dialog on mobile/remote control. So deny is a wall everywhere; ask is a wall wherever a
human is looking. An escape from deny into ask is a real hole, not a cosmetic one.

Tiers:
  deny  - catastrophic and unrecoverable: recursive delete of / or $HOME (or an ancestor),
          force-push/branch-delete on a protected branch, raw block-device writes, eFuse burns,
          any write/delete/move of a guardrail file, recursive delete of .git or .specify in a
          repository with no remote.
  ask   - destructive but recoverable, or unreadable: see SKILL.md for the table.
  pass  - print {} and let the host's normal permission flow decide.

Escape hatch: CAREFUL_ALLOW_HIGH=1 in the HOST's environment downgrades deny to ask (a command
the agent runs cannot set it for later hook runs). Never commit it into configuration.

Fail polarity, deliberately asymmetric:
  unreadable payload / inspection error / time budget exhausted / oversize command -> ask
  payload fine, nothing to inspect (no command, not a write tool)                   -> pass
  invalid careful.json -> every shell command that would pass gets ask, naming the error;
                          deny stays deny. A broken config never silently drops a rule.

BLIND TO (said here because GATES section 4 asks every gate to say it in its own text):
  - program semantics: an interpreter handed a script (python3 x.py, node -e, a Makefile
    target, an npm script) writes whatever it likes. Inline code is flagged, as ask, only when
    it opens a guarded path by name and writes, or hands a destructive literal to system().
  - anything that swaps the whole tree to a commit without the guard (git checkout <branch>,
    git switch, git reset --hard <old>, git stash pop, archive extraction, patch < file).
  - commands run outside the hooked tools (a human's terminal, CI, a git hook, a Makefile).
  - hosts other than Claude Code: the decision envelope, tool names and $CLAUDE_PROJECT_DIR
    are Claude Code's. Native Windows without Git Bash never runs this hook at all.
"""
import bisect
import fnmatch
import glob as globmod
import json
import os
import posixpath
import re
import signal
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "careful.json")

# F47 (2026-09-29): the previous matcher was quadratic — a heredoc regex rescanned to the end of
# the command for every unclosed `<< word`, and shlex is quadratic on one long token. 70 KB of
# `acc << item` took 6 s, 280 KB took 95 s, and a deny placed ahead of the padding was lost when
# the host killed the hook at its 10 s timeout (a timed-out PreToolUse hook does not block).
# Everything below is a single linear pass per nesting level; these two limits bound the rest.
MAX_INSPECT = 256 * 1024     # characters inspected in full; beyond it: the head for deny, then ask
MAX_DEPTH = 4                # nested $(...) / sh -c / eval levels inspected before giving up (ask)
DEADLINE_S = 7               # below the template's 10 s hook timeout: answer ask, never time out

# ---------------------------------------------------------------------------------------------
# Defaults. careful.json can only ADD to these lists; nothing in it can remove a default.
# ---------------------------------------------------------------------------------------------
DEFAULT_PROTECTED_BRANCHES = ["main", "master"]

# Something in the command must be able to EXECUTE SQL before SQL-shaped text means anything.
# Listing the client by name also covers `docker exec <container> mysql -e "..."`.
DEFAULT_DB_CLIENTS = [
    "mysql", "mariadb", "psql", "sqlite3", "sqlite", "mongo", "mongosh", "cockroach",
    "sqlcmd", "mysqladmin", "pg_dump", "usql", "mysqlsh", "pgcli", "mycli", "litecli",
    # warehouses and analytics engines (F15: all of these passed DROP TABLE silently)
    "bq", "snowsql", "duckdb", "spark-sql", "clickhouse-client", "clickhouse", "trino",
    "presto", "beeline", "impala-shell", "hive", "cqlsh", "influx", "turso", "wrangler",
]

# Throwaway build and cache directories whose recursive deletion is routine and whose content a
# tool regenerates. RELATIVE PATHS ONLY (plus the one home-anchored Xcode cache): an absolute
# path never rides this list. The v1.2 list carried `bin` and `tmp` as */bin|*/tmp globs and
# swallowed `rm -rf /usr/bin` and `rm -rf /tmp`; a bare name whose absolute twin matters, or
# that commonly holds committed files (`bin`, `lib`, `out`, `deps`, `Library`, `obj`), stays out.
# F15/F29: the list was JavaScript-centred, so routine cache cleanup on other stacks raised a
# dialog — and GATES section 6 counts the false-positive rate as a safety number.
DEFAULT_SAFE_DIRS = [
    # JavaScript / TypeScript: package installs, bundler and framework caches, test coverage
    "node_modules", ".next", ".nuxt", ".svelte-kit", ".angular", ".turbo", ".nx",
    ".parcel-cache", "dist", "build", "coverage", ".cache",
    # Python: bytecode, virtualenv (recreated by uv/pip/poetry), tool caches, packaging metadata
    "__pycache__", ".venv", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".nox",
    ".eggs", "*.egg-info", "htmlcov",
    # JVM / Rust / Go-adjacent build outputs: cargo and Maven `target`, Gradle's project cache
    "target", ".gradle",
    # Dart / Flutter, Apple (CocoaPods install dir, Xcode derived data), Godot import cache
    ".dart_tool", "Pods", "DerivedData", "~/Library/Developer/Xcode/DerivedData", ".godot",
    # Infrastructure: provider/module cache, rebuilt by `terraform init` (state is NOT in it)
    ".terraform",
    # Native and polyglot build systems: Bazel output symlinks, CMake IDE dirs, Zig, Haskell,
    # Elixir/OCaml `_build`
    "bazel-out", "bazel-bin", "bazel-testlogs", "cmake-build-*", ".zig-cache", "zig-out",
    ".stack-work", "dist-newstyle", "_build",
]

CONFIG_KEYS = ("protected_branches", "db_clients", "safe_dirs", "extra_ask", "extra_deny")


def load_config(path=CONFIG_PATH):
    """(config, error). Missing file -> defaults, no error. Anything malformed -> an error string.

    Unknown keys are an error too: a typo such as "extra_denny" would otherwise switch a rule
    off without a word, which is the failure this whole file exists to prevent.
    """
    cfg = {
        "protected_branches": list(DEFAULT_PROTECTED_BRANCHES),
        "db_clients": set(DEFAULT_DB_CLIENTS),
        "safe_dirs": list(DEFAULT_SAFE_DIRS),
        "extra_ask": [],
        "extra_deny": [],
    }
    if not os.path.exists(path):
        return cfg, None
    try:
        with open(path, "rb") as fh:
            data = json.loads(fh.read().decode("utf-8"))
    except Exception as exc:
        return cfg, "careful.json is not valid JSON (%s)" % str(exc).splitlines()[0]
    if not isinstance(data, dict):
        return cfg, "careful.json must hold a JSON object"
    for key, val in data.items():
        if key.startswith("_"):          # _comment and friends: documentation
            continue
        if key not in CONFIG_KEYS:
            return cfg, "careful.json has an unknown key %r (allowed: %s)" % (
                key, ", ".join(CONFIG_KEYS))
        if not isinstance(val, list) or not all(isinstance(v, str) and v for v in val):
            return cfg, "careful.json key %r must be a list of non-empty strings" % key
        if key in ("extra_ask", "extra_deny"):
            compiled = []
            for rx in val:
                try:
                    compiled.append(re.compile(rx))
                except re.error as exc:
                    return cfg, "careful.json %s has a bad regex %r (%s)" % (key, rx, exc)
            cfg[key] = compiled
        elif key == "db_clients":
            cfg[key] |= {v.lower() for v in val}
        else:
            cfg[key] = cfg[key] + val
    return cfg, None


# ---------------------------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------------------------
_HOME = os.path.expanduser("~")


def _slash(p):
    return p.replace("\\", "/")


def is_abs(p):
    return p.startswith("/") or bool(re.match(r"[A-Za-z]:(?:/|$)", p))


def norm(p, base=None):
    """Lexical normal form: backslashes to slashes, // and /./ collapsed, .. resolved.

    F44: the guarded tier matched the raw path text, so `.claude//hooks/x`, `.claude/./hooks/x`
    and `.CLAUDE/Hooks/x` (the same file on APFS and NTFS) all passed with {}. F8: Claude Code
    delivers Windows paths with backslashes, which never matched a forward-slash pattern.
    """
    p = _slash(p)
    p = re.sub(r"::?\$data$", "", p, flags=re.I)          # NTFS default stream: file::$DATA
    if os.name == "nt":
        p = re.sub(r"^/(?:cygdrive/)?([A-Za-z])(?=/|$)", r"\1:", p)   # Git Bash /c/x -> c:/x
    if base and not is_abs(p) and not p.startswith("~"):
        p = _slash(base).rstrip("/") + "/" + p
    if not p:
        return p
    q = posixpath.normpath(p)
    if q.startswith("//"):
        q = "/" + q.lstrip("/")
    # NTFS drops trailing dots and spaces from a name: `settings.json.` IS settings.json there.
    parts = [c if c in (".", "..") else c.rstrip(". ") or c for c in q.split("/")]
    return "/".join(parts)


def fold(p):
    return p.casefold()


# Guarded files: the guard itself, where it is registered, the gate chain it protects, and the
# host's managed settings (which can switch every hook off with disableAllHooks). Matched
# against the normalised, case-folded path — case-folded everywhere, because a false deny on
# `.CLAUDE/HOOKS/` costs nothing on Linux and the fold is required on macOS and Windows.
GUARDED_RX = re.compile(
    r"(?:^|/)\.claude/hooks(?:/|$)"                         # the hook, its config, its tests
    r"|(?:^|/)\.claude/settings(?:\.local)?\.json$"        # where hooks are registered
    r"|(?:^|/)gates/(?:run-chain\.sh|check-[^/]*\.(?:sh|py)|hooks(?:/|$))"   # the gate chain
    r"|(?:^|/)harness/skills/careful/hooks(?:/|$)"         # the kit copy an upgrade installs
    # The wiring `adopt.py --register-guard` copies into .claude/settings.json. That command is
    # allowed (it can only restore the kit's wiring), so the template it copies must not be
    # editable: a neutered template plus one allowed command would rewrite the guarded settings.
    r"|(?:^|/)harness/settings\.json\.template$"
    r"|(?:^|/)\.specify/scripts(?:/|$)"                    # Spec Kit scripts the flow shells to
    r"|^/etc/claude-code(?:/|$)"                           # managed settings: Linux and WSL
    r"|^/library/application support/claudecode(?:/|$)"    # managed settings: macOS
    r"|(?:^|/)program files/claudecode(?:/|$)"             # managed settings: Windows
)
# A gates/check-* file that does not exist yet cannot disable anything: creating one is shown
# (ask), so feature 001 can add a project gate after the guard is registered. Once it exists,
# it is guarded like the rest of the chain.
NEW_GATE_RX = re.compile(r"(?:^|/)gates/check-[^/]*\.(?:sh|py)$")


def new_gate_file(p, ab):
    f = fold(p)
    if not NEW_GATE_RX.search(f) or GUARDED_RX.search(NEW_GATE_RX.sub("/x", f)):
        return False
    return is_abs(ab) and not os.path.lexists(ab)


# Directories that CONTAIN guarded files: deleting or moving one removes them all at once.
# (`mv .claude .claude.off` passed silently before v1.4.0 — F9.)
GUARDED_ANCESTOR_RX = re.compile(
    r"(?:^|/)(?:\.claude|gates|harness/skills/careful)$"
    r"|^/etc$|^/library$|^/library/application support$|(?:^|/)program files$"
)
# Gate configuration: the adopter wires it, so an edit is legitimate — but quietly changing it
# turns a red gate green, so it is always shown (ask), never silent.
GATE_CONFIG_RX = re.compile(r"(?:^|/)gates/(?:[^/]+\.conf|orphan-allowlist\.txt)$")
# The other two places that decide whether the chain runs at all, same treatment (ask):
#   - the CI job `adopt.py --ci github` installs. GATES §1 calls CI the check nothing skips, yet
#     an agent could Edit it to `run: true`, or `git rm` it, with {} (review 2026-09-29) while an
#     edit to chain.conf asked. Ask, not deny: the kit tells adopters to add toolchain steps to it.
#   - git's own hook wiring. `git config --unset core.hooksPath` asked; an Edit of .git/config
#     that deleted the same line passed. A hook dropped into .git/hooks/ is the same lever.
GATE_WIRING_RX = re.compile(
    r"(?:^|/)\.github/workflows/factory-gates\.ya?ml$"
    r"|(?:^|/)\.git/(?:config(?:\.worktree)?|hooks/[^/]+)$"
    r"|(?:^|/)\.git/modules/.+/(?:config(?:\.worktree)?|hooks/[^/]+)$")


def gate_wiring(p):
    """Why path p (normalised) is gate configuration or wiring, or None."""
    f = fold(p)
    if GATE_CONFIG_RX.search(f):
        return "gate configuration (%s) — changing it can turn a red gate green" % p
    if GATE_WIRING_RX.search(f):
        if "/.github/" in "/" + f:
            return ("the CI job that runs the gate chain (%s) — changing or removing it changes "
                    "what CI enforces" % p)
        return "git's hook wiring (%s) — it decides whether the gate chain's hook runs" % p
    return None


# F32 (review 2026-09-29): GNU getopt_long, git's parse-options and Python's argparse all accept
# any unambiguous PREFIX of a long option. `rm --recurs --forc ~`, `git push --delet origin main`,
# `git commit --no-verif` and `adopt.py --upg` each RAN as the full option (measured: git 2.43,
# coreutils 9.4) while every rule below, matching the full spelling, returned {}. Per command,
# the long options a rule keys on, dangerous ones first: an argument that is a prefix of one of
# them is read as that option. An ambiguous prefix makes the real tool stop with an error, so
# reading it the dangerous way can only cost a false alarm on a command that would not have run.
# Every real option that is itself a prefix of a listed dangerous one (git push --force, a prefix
# of --force-with-lease) must be listed too, so that its exact spelling wins.
LONG_OPTS = {
    "rm": ("--recursive", "--force", "--dir", "--interactive", "--no-preserve-root",
           "--preserve-root", "--one-file-system", "--verbose", "--help", "--version"),
    "cp": ("--recursive", "--archive", "--target-directory"),
    "sed": ("--in-place", "--expression", "--file"),
    "adopt.py": ("--upgrade",),
}
GIT_LONG_OPTS = {
    "push": ("--delete", "--mirror", "--force", "--force-with-lease", "--force-if-includes",
             "--prune", "--all", "--branches", "--no-verify", "--dry-run", "--tags",
             "--follow-tags", "--set-upstream", "--atomic", "--porcelain", "--progress",
             "--quiet", "--verbose", "--signed", "--thin", "--verify", "--repo", "--receive-pack",
             "--exec", "--push-option", "--recurse-submodules", "--ipv4", "--ipv6"),
    "commit": ("--no-verify",), "merge": ("--no-verify",), "rebase": ("--no-verify",),
    "am": ("--no-verify",), "cherry-pick": ("--no-verify",), "revert": ("--no-verify",),
    "reset": ("--hard",),
    "clean": ("--force",),
    "checkout": ("--force", "--discard-changes"),
    "switch": ("--force", "--discard-changes"),
    "restore": (),
    "branch": ("--delete", "--force"),
    "worktree": ("--force",),
    "gc": ("--prune",),
    "config": ("--unset", "--unset-all", "--add", "--replace-all", "--edit", "--get", "--get-all",
               "--get-regexp", "--list", "--show-origin", "--show-scope"),
}


def canon_long(a, options):
    """`--recurs` -> `--recursive` when it is a prefix of a listed long option (see LONG_OPTS)."""
    if not a.startswith("--") or len(a) < 3 or not options:
        return a
    name, eq, val = a.partition("=")
    if name in options:
        return a
    for o in options:
        if o.startswith(name):
            return o + eq + val
    return a


def canon_args(args, options):
    """canon_long over every argument before a `--` end-of-options marker; words keep their type."""
    out, done = [], False
    for a in args:
        s = str(a)
        if done or s == "--":
            done = True
            out.append(a)
            continue
        c = canon_long(s, options)
        out.append(a if c == s else _word(c, getattr(a, "opaque", False)))
    return out
SYSTEM_RX = re.compile(r"^/(?:etc|usr|bin|sbin|lib|lib32|lib64|boot|system|library|private/etc)"
                       r"(?:/|$)|^[a-z]:/windows(?:/|$)")
BLOCK_DEVICE_RX = re.compile(
    r"^/dev/(?:sd[a-z]|hd[a-z]|vd[a-z]|xvd[a-z]|nvme\d|mmcblk\d|r?disk\d|md\d|dm-\d|mapper/"
    r"|sr\d|mtdblock\d|mtd\d)|^//\./physicaldrive|^/\./physicaldrive", re.I)
# Inline program text that names a guarded file. Inline code is not a shape this matcher can
# judge, so naming one of these files earns ask — the path is the only readable signal.
INTERP_WRITE_RX = re.compile(
    r"['\"](?:w|a|x|wb|ab|xb|w\+|a\+|r\+|wt|at)['\"]|write|dump|unlink|remove|rmtree|rename"
    r"|replace\s*\(|truncate|chmod|copy"
    r"|move|rmSync|rmdir|os\.system|subprocess|child_process|File\.|Set-Content|Out-File"
    r"|>>?\s*[\"']", re.I)
GUARDED_MENTION_RX = re.compile(
    r"\.claude[/\\]+(?:hooks|settings(?:\.local)?\.json)|gates[/\\]+(?:run-chain|check-|hooks[/\\])"
    r"|careful[/\\]+hooks|claude-code[/\\]|managed-settings|claudecode[/\\]"
    r"|settings\.json\.template", re.I)

_SCRATCH_ROOTS = ["/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/"]
for _var in ("TMPDIR", "TEMP", "TMP"):
    _v = os.environ.get(_var)
    if _v and norm(_v) not in ("/", ""):
        _SCRATCH_ROOTS.append(norm(_v).rstrip("/") + "/")
SCRATCH_ROOTS = tuple(fold(r) for r in _SCRATCH_ROOTS)

STAR_ALL = {"*", ".*", "**", ".[!.]*", "..?*", "{*,.*}", "{.*,*}"}


def in_scratch(p, extra=()):
    """True for an absolute path strictly INSIDE a temp root, with no way to climb out."""
    f = fold(p)
    for root in SCRATCH_ROOTS + tuple(extra):
        if f.startswith(root) and len(f) > len(root):
            return ".." not in f.split("/")
    return False


def is_ancestor_or_self(p, of):
    """p is `of` itself or one of its parent directories."""
    a, b = fold(p).rstrip("/"), fold(of).rstrip("/")
    if a in ("", "/") or re.fullmatch(r"[a-z]:", a or ""):
        return True
    return b == a or b.startswith(a + "/")


def is_root(p):
    f = fold(p).rstrip("/")
    return f in ("", "/") or bool(re.fullmatch(r"[a-z]:", f))


# ---------------------------------------------------------------------------------------------
# Lexing. One pass per nesting level, quote-aware, heredoc-aware.
#
# The v1.3 matcher split on a regex and tokenised with shlex. Measured 2026-09-29, that let
# `rm -rf /` through with {} in every one of these shells: `if true; then rm -rf /; fi`,
# `(rm -rf /)`, `f(){ rm -rf /; }; f`, `echo $(rm -rf /)`, `bash <<EOF` + `rm -rf /`, and
# `echo "rm -rf /" | sh` — and a 129-character `echo x | base64 --- --- …` took 69 s against a
# 10 s timeout. A lexer that knows what a separator, a substitution and a heredoc are is the fix.
# ---------------------------------------------------------------------------------------------
class W(str):
    """One shell word after quote removal. `opaque`: part of it is an expansion whose value
    cannot be read ($(...), backticks, <(...), ${x:-...})."""
    opaque = False


def _word(text, opaque):
    w = W(text)
    w.opaque = opaque
    return w


class Seg(object):
    __slots__ = ("words", "redirs", "text", "piped", "bodies", "subs", "herestrings")

    def __init__(self, piped=False):
        self.words = []          # [W]
        self.redirs = []         # [(op, W)]
        self.text = ""           # source text of the segment (heredoc bodies excluded)
        self.piped = piped       # stdin comes from the previous segment through a pipe
        self.bodies = []         # heredoc bodies feeding stdin
        self.subs = []           # source of substitutions ($(...), `...`, <(...)) to inspect
        self.herestrings = []    # <<< words


def _kw_at(s, j, kw):
    return s.startswith(kw, j) and (j == 0 or s[j - 1] in " \t\n;(&|") and \
        (j + len(kw) == len(s) or s[j + len(kw)] in " \t\n;)")


def match_close(s, j, op, cl):
    """Index of the bracket closing an opener just before j (quote-aware); len(s) if none.

    `case` patterns end in a bare `)`; inside $( ) that must not close the substitution, or
    `echo $(case a in a) rm -rf / ;; esac)` hides the rm from inspection (found by fuzzing).
    """
    n, depth, cases = len(s), 1, 0
    while j < n:
        c = s[j]
        if c == "c" and _kw_at(s, j, "case"):
            cases += 1
        elif c == "e" and cases and _kw_at(s, j, "esac"):
            cases -= 1
        elif c == cl and cases and depth == 1:
            j += 1                                       # a case pattern's `)`
            continue
        if c == "\\":
            j += 2
            continue
        if c == "'":
            k = s.find("'", j + 1)
            j = n if k < 0 else k + 1
            continue
        if c == '"':
            j = skip_dquote(s, j + 1)
            continue
        if c == "`":
            j = skip_backtick(s, j + 1)
            continue
        if c == op:
            depth += 1
        elif c == cl:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return n


def skip_dquote(s, j):
    n = len(s)
    while j < n:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == '"':
            return j + 1
        if c == "$" and j + 1 < n and s[j + 1] == "(":
            j = match_close(s, j + 2, "(", ")") + 1
            continue
        if c == "`":
            j = skip_backtick(s, j + 1)
            continue
        j += 1
    return n


def skip_backtick(s, j):
    n = len(s)
    while j < n:
        if s[j] == "\\":
            j += 2
            continue
        if s[j] == "`":
            return j + 1
        j += 1
    return n


_ANSI = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b",
         "f": "\f", "v": "\v", "\\": "\\", "'": "'", '"': '"', "?": "?"}
_NAME_AT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9@*#?$!-]")


class BashLexer(object):
    def __init__(self, s):
        self.s, self.n = s, len(s)
        self.segs = []
        self.seg = Seg()
        self.start = 0
        self.buf, self.inw, self.opq = [], False, False
        self.redir = None
        self.docs = []           # (seg, strip_tabs, delimiter) waiting for the end of the line
        self.index = None

    # -- words and segments --
    def word(self):
        if not self.inw:
            return
        w = _word("".join(self.buf), self.opq)
        self.buf, self.inw, self.opq = [], False, False
        op, self.redir = self.redir, None
        if op in ("<<", "<<-"):
            self.docs.append((self.seg, op == "<<-", str(w)))
        elif op == "<<<":
            self.seg.herestrings.append(w)
        elif op is not None:
            self.seg.redirs.append((op, w))
        else:
            self.seg.words.append(w)

    def end(self, i, nxt, piped=False):
        self.word()
        self.redir = None
        self.seg.text = self.s[self.start:i]
        sg = self.seg
        if sg.words or sg.redirs or sg.subs or sg.herestrings or sg.bodies:
            self.segs.append(sg)
        self.seg = Seg(piped)
        self.start = nxt

    # -- heredocs: bodies begin after the end of the line that opened them --
    def _build_index(self):
        exact, tabbed = {}, {}
        pos = 0
        for line in self.s.split("\n"):
            end = pos + len(line) + 1
            key = line[:-1] if line.endswith("\r") else line
            exact.setdefault(key, []).append((pos, end))
            tabbed.setdefault(key.lstrip("\t"), []).append((pos, end))
            pos = end
        self.index = (exact, tabbed)

    def after_newline(self, i):
        if not self.docs:
            return i
        if self.index is None:
            self._build_index()
        docs, self.docs = self.docs, []
        for seg, strip, delim in docs:
            table = self.index[1] if strip else self.index[0]
            spans = table.get(delim)
            if not spans:
                # No terminator line anywhere below. Bash would read to EOF, but a misread
                # opener (arithmetic `1 << 2`, a quoted `<<` we got wrong) must never hide the
                # real commands after it, so this is treated as no heredoc at all.
                continue
            k = bisect.bisect_left(spans, (i, -1))
            if k >= len(spans):
                continue
            t0, t1 = spans[k]
            seg.bodies.append(self.s[i:t0])
            i = min(t1, self.n)
        return i

    # -- the main loop --
    def run(self):
        s, n = self.s, self.n
        i = 0
        while i < n:
            c = s[i]
            if c == "\n":
                self.end(i, i + 1)
                i = self.after_newline(i + 1)
                self.start = i
                continue
            if c in " \t\r":
                self.word()
                i += 1
                continue
            if c == "#" and not self.inw:
                j = s.find("\n", i)
                if j < 0:
                    self.seg.text = s[self.start:i]
                    i = n
                else:
                    i = j
                continue
            if c == "\\":
                if i + 1 < n and s[i + 1] == "\n":
                    i += 2
                    continue
                if i + 1 < n:
                    self.buf.append(s[i + 1])
                self.inw = True
                i += 2
                continue
            if c == "'":
                j = s.find("'", i + 1)
                j = n if j < 0 else j
                self.buf.append(s[i + 1:j])
                self.inw = True
                i = j + 1
                continue
            if c == '"':
                i = self.dquote(i + 1)
                continue
            if c == "$":
                i = self.dollar(i)
                continue
            if c == "`":
                j = skip_backtick(s, i + 1)
                self.seg.subs.append(s[i + 1:j - 1] if j <= n and s[j - 1] == "`" else s[i + 1:j])
                self.buf.append(s[i:j])
                self.inw, self.opq = True, True
                i = j
                continue
            if c in ";&|()<>":
                i = self.operator(i)
                continue
            self.buf.append(c)
            self.inw = True
            i += 1
        self.end(n, n)
        return self.segs

    def dquote(self, i):
        s, n = self.s, self.n
        self.inw = True
        while i < n:
            c = s[i]
            if c == '"':
                return i + 1
            if c == "\\" and i + 1 < n and s[i + 1] in '"\\$`\n':
                if s[i + 1] != "\n":
                    self.buf.append(s[i + 1])
                i += 2
                continue
            if c == "$":
                i = self.dollar(i)
                continue
            if c == "`":
                j = skip_backtick(s, i + 1)
                self.seg.subs.append(s[i + 1:max(i + 1, j - 1)])
                self.buf.append(s[i:j])
                self.opq = True
                i = j
                continue
            self.buf.append(c)
            i += 1
        return n

    def dollar(self, i):
        s, n = self.s, self.n
        self.inw = True
        nxt = s[i + 1] if i + 1 < n else ""
        if nxt == "(":
            j = match_close(s, i + 2, "(", ")")
            self.seg.subs.append(s[i + 2:j])
            self.buf.append(s[i:j + 1])
            self.opq = True
            return j + 1
        if nxt == "{":
            j = match_close(s, i + 2, "{", "}")
            inner = s[i + 2:j]
            self.buf.append(s[i:j + 1])
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", inner):
                self.opq = True                      # ${x:-y} ${x[0]} ${!x}: not readable
                if "$(" in inner or "`" in inner:
                    self.seg.subs.append(inner)
            return j + 1
        if nxt == "'":                               # $'...' ANSI-C quoting: decode it
            j, out = i + 2, []
            while j < n and s[j] != "'":
                if s[j] == "\\" and j + 1 < n:
                    e = s[j + 1]
                    m = re.match(r"x([0-9A-Fa-f]{1,2})|([0-7]{1,3})|u([0-9A-Fa-f]{1,4})", s[j + 1:j + 6])
                    if m and (m.group(1) or m.group(2) or m.group(3)):
                        code = m.group(1) or m.group(3)
                        out.append(chr(int(code, 16)) if code else chr(int(m.group(2), 8)))
                        j += 1 + m.end()
                        continue
                    out.append(_ANSI.get(e, "\\" + e))
                    j += 2
                    continue
                out.append(s[j])
                j += 1
            self.buf.append("".join(out))
            return j + 1
        if nxt == '"':
            return self.dquote(i + 2)
        m = _NAME_AT.match(s, i + 1)
        if m:
            self.buf.append(s[i:m.end()])
            return m.end()
        self.buf.append("$")
        return i + 1

    def operator(self, i):
        s, n = self.s, self.n
        c, two, three = s[i], s[i:i + 2], s[i:i + 3]
        if c in "<>":
            if self.inw and not self.opq and "".join(self.buf).isdigit():
                self.buf, self.inw = [], False           # `2>file`: the digit is the fd
            else:
                self.word()
            if c in "<>" and i + 1 < n and s[i + 1] == "(":  # <(...) >(...) process substitution
                j = match_close(s, i + 2, "(", ")")
                self.seg.subs.append(s[i + 2:j])
                self.buf.append(s[i:j + 1])
                self.inw, self.opq = True, True
                return j + 1
            for op in ("<<<", "<<-", "&>>"):
                if three == op:
                    self.redir = op
                    return i + 3
            if two in ("<<", ">>", ">|", "<>", ">&", "<&"):
                self.redir = two
                return i + 2
            self.redir = c
            return i + 1
        if c == "&":
            if two == "&&":
                self.end(i, i + 2)
                return i + 2
            if three == "&>>":
                self.word()
                self.redir = "&>>"
                return i + 3
            if two == "&>":
                self.word()
                self.redir = "&>"
                return i + 2
            self.end(i, i + 1)
            return i + 1
        if c == "|":
            if two == "||":
                self.end(i, i + 2)
                return i + 2
            if two == "|&":
                self.end(i, i + 2, piped=True)
                return i + 2
            self.end(i, i + 1, piped=True)
            return i + 1
        if c == ";":
            k = i + 1
            while k < n and s[k] in ";&":
                k += 1
            self.end(i, k)
            return k
        self.end(i, i + 1)                               # ( and ): subshell / function syntax
        return i + 1


def lex_bash(s):
    return BashLexer(s).run()


class PwshLexer(object):
    """PowerShell: backtick escapes, '' and "" quoting, @'...'@ here-strings, <# #> comments.

    Best-effort and unverified on a real Windows host (C3: native Windows is best-effort). Its
    job is the shapes that matter — separators, quoting, redirects, $( ) subexpressions — so
    the argv rules below can run on PowerShell commands too.
    """

    def __init__(self, s):
        self.s, self.n = s, len(s)
        self.segs, self.seg, self.start = [], Seg(), 0
        self.buf, self.inw, self.opq, self.redir = [], False, False, None

    def word(self):
        if not self.inw:
            return
        w = _word("".join(self.buf), self.opq)
        self.buf, self.inw, self.opq = [], False, False
        op, self.redir = self.redir, None
        if op is not None:
            self.seg.redirs.append((op, w))
        else:
            self.seg.words.append(w)

    def end(self, i, nxt, piped=False):
        self.word()
        self.redir = None
        self.seg.text = self.s[self.start:i]
        sg = self.seg
        if sg.words or sg.redirs or sg.subs or sg.bodies:
            self.segs.append(sg)
        self.seg, self.start = Seg(piped), nxt

    def run(self):
        s, n = self.s, self.n
        i = 0
        while i < n:
            c = s[i]
            if c == "@" and not self.inw and s[i + 1:i + 2] in ("'", '"') and s[i + 2:i + 3] in ("\n", "\r"):
                q = s[i + 1]
                m = re.compile(r"\n" + re.escape(q) + "@").search(s, i + 2)
                j = n if m is None else m.end()
                self.seg.bodies.append(s[i + 2:(m.start() if m else n)])
                self.buf.append("@here")
                self.inw = True
                i = j
                continue
            if c == "<" and s[i + 1:i + 2] == "#":
                j = s.find("#>", i + 2)
                i = n if j < 0 else j + 2
                continue
            if c in "\n;":
                self.end(i, i + 1)
                i += 1
                continue
            if c in " \t\r,":
                self.word()
                i += 1
                continue
            if c == "#" and not self.inw:
                j = s.find("\n", i)
                i = n if j < 0 else j
                continue
            if c == "`":
                if i + 1 < n and s[i + 1] == "\n":
                    i += 2
                    continue
                if i + 1 < n:
                    self.buf.append(s[i + 1])
                self.inw = True
                i += 2
                continue
            if c == "'":
                j, out = i + 1, []
                while j < n:
                    if s[j] == "'":
                        if s[j + 1:j + 2] == "'":
                            out.append("'")
                            j += 2
                            continue
                        break
                    out.append(s[j])
                    j += 1
                self.buf.append("".join(out))
                self.inw = True
                i = j + 1
                continue
            if c == '"':
                i = self.dquote(i + 1)
                continue
            if c == "$" and s[i + 1:i + 2] == "(":
                j = match_close(s, i + 2, "(", ")")
                self.seg.subs.append(s[i + 2:j])
                self.buf.append(s[i:j + 1])
                self.inw, self.opq = True, True
                i = j + 1
                continue
            if c == "$" and s[i + 1:i + 2] == "{":           # ${env:USERPROFILE}: a variable
                j = s.find("}", i + 2)
                j = n - 1 if j < 0 else j
                self.buf.append(s[i:j + 1])
                self.inw = True
                i = j + 1
                continue
            if c == "&" and s[i + 1:i + 2] == "&" or c == "|" and s[i + 1:i + 2] == "|":
                self.end(i, i + 2)
                i += 2
                continue
            if c == "|":
                self.end(i, i + 1, piped=True)
                i += 1
                continue
            if c == "&" and not self.inw:
                i += 1                                   # call operator `& cmd`: not a word
                continue
            if c in "{}()":
                self.end(i, i + 1)
                i += 1
                continue
            if c == ">" or (c in "0123456789*" and s[i + 1:i + 2] == ">" and not self.inw):
                self.word()
                j = i if c == ">" else i + 1
                op = ">>" if s[j:j + 2] == ">>" else ">"
                j += len(op)
                if s[j:j + 1] == "&":                    # 2>&1: a stream merge, not a file
                    i = j + 2
                    continue
                self.redir = op
                i = j
                continue
            self.buf.append(c)
            self.inw = True
            i += 1
        self.end(n, n)
        return self.segs

    def dquote(self, i):
        s, n = self.s, self.n
        self.inw = True
        while i < n:
            c = s[i]
            if c == "`" and i + 1 < n:
                self.buf.append(s[i + 1])
                i += 2
                continue
            if c == '"':
                if s[i + 1:i + 2] == '"':
                    self.buf.append('"')
                    i += 2
                    continue
                return i + 1
            if c == "$" and s[i + 1:i + 2] == "(":
                j = match_close(s, i + 2, "(", ")")
                self.seg.subs.append(s[i + 2:j])
                self.buf.append(s[i:j + 1])
                self.opq = True
                i = j + 1
                continue
            self.buf.append(c)
            i += 1
        return n


# ---------------------------------------------------------------------------------------------
# Inspection context
# ---------------------------------------------------------------------------------------------
class Ctx(object):
    def __init__(self, cfg, cwd, project, scratch_extra):
        self.cfg = cfg
        self.cwd = cwd               # the session's working directory (payload cwd)
        self.cd = None               # a directory this command itself cd'd into
        self.vars = {}               # NAME -> [values] declared earlier in this command
        self.project = project       # $CLAUDE_PROJECT_DIR, normalised, or None
        self.scratch_extra = scratch_extra
        self.lost = False            # `cd -` or `cd $(...)`: the directory is no longer known

    def base(self):
        return None if self.lost else (self.cd or self.cwd)

    def child(self):
        """A substitution runs in a subshell: its cd and assignments do not leak out."""
        c = Ctx(self.cfg, self.cwd, self.project, self.scratch_extra)
        c.cd, c.vars, c.lost = self.cd, dict(self.vars), self.lost
        return c


def verdict_rank(v):
    return 0 if v is None else (2 if v[0] == "deny" else 1)


def worse(a, b):
    return b if verdict_rank(b) > verdict_rank(a) else a


ASK, DENY = "ask", "deny"


# -- expansion ---------------------------------------------------------------------------------
_VAR_RX = re.compile(r"\$\{?env:([A-Za-z_][A-Za-z0-9_]*)\}?|\$\{([A-Za-z_][A-Za-z0-9_]*)\}"
                     r"|\$([A-Za-z_][A-Za-z0-9_]*)", re.I)


BRACE_RX = re.compile(r"\{([^{}]*,[^{}]*)\}")


def brace_expand(w, limit=16):
    """{a,b}x -> ax bx, in order, capped. `rm -rf {/,x}` IS `rm -rf / x`."""
    out, todo = [], [w]
    while todo and len(out) + len(todo) <= limit:
        cur = todo.pop(0)
        m = BRACE_RX.search(cur)
        if not m:
            out.append(cur)
            continue
        todo = [cur[:m.start()] + alt + cur[m.end():] for alt in m.group(1).split(",")] + todo
    return out + todo


def _subst(v, ctx, known):
    """Every variable in v replaced by its known values (unknown ones left as written)."""
    outs, pos = [""], 0
    for m in _VAR_RX.finditer(v):
        name = m.group(1) or m.group(2) or m.group(3)
        subs = ctx.vars.get(name) or known.get(name) or known.get(name.upper())
        lit = v[pos:m.start()]
        if subs:
            outs = [o + lit + sv for o in outs for sv in subs[:8]][:16]
        else:
            outs = [o + lit + m.group(0) for o in outs]
        pos = m.end()
    return [o + v[pos:] for o in outs]


def expand(w, ctx):
    """Candidate values of a word: braces, variables declared in the command, ~ and $HOME."""
    known = {"HOME": [_HOME], "USERPROFILE": [_HOME]}
    for tv in ("TMPDIR", "TEMP", "TMP"):
        if os.environ.get(tv):
            known[tv] = [os.environ[tv]]
    if ctx.base():
        known["PWD"] = [ctx.base()]
    outs = []
    for cand in brace_expand(str(w)):
        vals = [cand]
        for _ in range(2):                    # A=$HOME/x; rm -rf "$A": values hold variables too
            if not any("$" in v for v in vals):
                break
            vals = [x for v in vals for x in _subst(v, ctx, known)][:32]
        for v in vals:
            if (v == "~+" or v.startswith("~+/")) and ctx.base():
                v = ctx.base() + v[2:]
            elif v == "~" or v.startswith("~/") or v.startswith("~\\"):
                v = _HOME + v[1:]
            elif re.match(r"~[A-Za-z0-9_.-]+(/|$)", v):
                v = os.path.expanduser(v)
            outs.append(v)
    return outs[:32]


# -- target classification -----------------------------------------------------------------------
def _forms(w, ctx):
    """(raw-normalised, absolute) spellings of each candidate value of word w.

    A glob is also expanded against the disk, as bash would: `> .claude/hook?/x` and
    `rm -rf .clau*` name the guard without spelling it.
    """
    res = []
    for v in expand(w, ctx):
        rel = norm(v)
        ab = norm(v, ctx.base()) if ctx.base() else rel
        res.append((v, rel, ab))
        if re.search(r"[*?\[]", v) and is_abs(ab) and len(res) < 64:
            try:
                hits = globmod.glob(ab)[:32]
            except Exception:
                hits = []
            for h in hits:
                hn = norm(h)
                res.append((hn, hn, hn))
    return res


def _realpath(p):
    try:
        return norm(os.path.realpath(p))
    except Exception:
        return p


def _realparent(p):
    """For deletes: `rm -rf link` removes the link; `rm -rf link/` follows it."""
    if p.endswith("/") or p.endswith("/."):
        return _realpath(p)
    head, _, tail = p.rstrip("/").rpartition("/")
    if not head:
        return p
    return norm(_realpath(head) + "/" + tail)


_HERE_F = fold(norm(HERE))


def guarded(p):
    f = fold(p)
    return bool(GUARDED_RX.search(f)) or f == _HERE_F or f.startswith(_HERE_F + "/")


def guarded_ancestor(p):
    f = fold(p).rstrip("/")
    if GUARDED_ANCESTOR_RX.search(f):
        return True
    # `harness` and `harness/skills` are common names; only on-disk evidence makes them guarded
    if re.search(r"(?:^|/)harness(?:/skills)?$", f):
        tail = "skills/careful/hooks" if f.endswith("harness") else "careful/hooks"
        return os.path.isdir(os.path.join(p, tail))
    return False


HOMES_RX = re.compile(r"^(?:/home|/users|[a-z]:/users)(?:/[^/]+)?$|^/root$")


def touches_guard(w, ctx, ancestors):
    """True when word w names a guarded file (or, with ancestors, a directory holding one)."""
    for v, rel, ab in _forms(w, ctx):
        for p in (rel, ab, _realpath(ab) if is_abs(ab) else ab):
            if guarded(p) or (ancestors and guarded_ancestor(p)):
                return True
    return False


def catastrophic(p):
    """/ itself, $HOME or any directory above it, or any user's home or the homes root."""
    if not is_abs(p):
        return False
    f = fold(p).rstrip("/")
    return is_root(p) or is_ancestor_or_self(p, norm(_HOME)) or bool(HOMES_RX.match(f))


def star_parent(v):
    """`dir/*` and friends mean 'everything in dir' for the root/home test."""
    v2 = _slash(v).rstrip("/")
    head, _, last = v2.rpartition("/")
    if last in STAR_ALL:
        return head or "/"
    if v2 in STAR_ALL:
        return "."
    return None


# `perl -pi -e … $(git ls-files .claude)`: the target list is built at runtime, but the text
# that builds it names the guard's own directory — that is enough to stop.
GUARD_DIR_MENTION_RX = re.compile(r"(?:^|[\s/'\"(=])(?:\.claude|gates|careful[/\\]hooks)"
                                  r"(?:[/\\\s'\")]|$)", re.I)


def _opaque_guard(w):
    return getattr(w, "opaque", False) and bool(GUARD_DIR_MENTION_RX.search(str(w)))


def judge_write(w, ctx, what):
    """Verdict for writing/overwriting the path named by word w."""
    if _opaque_guard(w):
        return (DENY, "%s onto paths built at runtime from the guard's own directory (%s) — "
                      "have a human do it." % (what, str(w)[:60]))
    for v, rel, ab in _forms(w, ctx):
        for p in (rel, ab, _realpath(ab) if is_abs(ab) else ab):
            if guarded(p):
                if new_gate_file(p, ab):
                    return (ASK, "%s creates a new gate script (%s) — review it; once it exists "
                                 "it is guarded like the rest of the chain." % (what, w))
                return (DENY, "%s onto a guardrail file (%s) — this would disable or rewrite the "
                              "guard itself. Have a human make this change." % (what, w))
            if BLOCK_DEVICE_RX.search(p):
                return (DENY, "%s onto a raw block device (%s) — overwrites a disk; one wrong "
                              "letter erases the machine." % (what, w))
    for v, rel, ab in _forms(w, ctx):
        why = gate_wiring(rel) or gate_wiring(ab)
        if why:
            return (ASK, "%s onto %s; a human should see it." % (what, why))
        f = fold(ab)
        home = fold(norm(_HOME))
        if f.startswith(home + "/.") and not f.startswith(home + "/.claude/projects/"):
            return (ASK, "%s onto a config dot-entry in $HOME (%s) — it changes how later "
                         "sessions behave, quietly." % (what, w))
        if SYSTEM_RX.search(f):
            return (ASK, "%s onto a system path (%s)." % (what, w))
    return None


def _remote_less_repo(abspath, which, ctx):
    """True when deleting `which` at abspath would destroy the only copy (no git remote).

    F48: a from-idea project spends its first days with no remote, and `rm -rf .git` there
    erased every commit on an ask, while a force-push to a remote that holds a copy was a deny.
    A repository under a temp root is scratch — unless it is the project itself.
    """
    if not os.path.isdir(abspath):
        return False
    if in_scratch(abspath, ctx.scratch_extra) and not (
            ctx.project and is_ancestor_or_self(ctx.project, abspath)):
        return False
    repo = os.path.dirname(abspath.rstrip("/"))
    if which == ".specify/memory":
        repo = os.path.dirname(repo)
    try:
        r = subprocess.run(["git", "-C", repo, "remote"], capture_output=True, text=True,
                           timeout=2)
    except Exception:
        return True
    return r.returncode != 0 or not r.stdout.strip()


def judge_delete(w, ctx, recursive, what="recursive delete"):
    """(verdict or None, safe) for deleting the path named by word w."""
    if _opaque_guard(w):
        return (DENY, "%s of paths built at runtime from the guard's own directory (%s) — have "
                      "a human do it." % (what, str(w)[:60])), False
    forms = _forms(w, ctx)
    for v, rel, ab in forms:
        sp = star_parent(v)
        follow = _slash(v).endswith("/") or _slash(v).endswith("/.")
        rp = (_realpath(ab) if follow else _realparent(ab)) if is_abs(ab) else ab
        for p in {ab, rp}:
            if recursive and catastrophic(p):
                return (DENY, "%s of %s — this erases the machine or the whole home directory. "
                              "There is no undo." % (what, w)), False
            if recursive and sp is not None:
                par = norm(sp, ctx.base()) if ctx.base() else norm(sp)
                if catastrophic(par):
                    return (DENY, "%s of everything in %s — this empties the machine or the "
                                  "home directory. There is no undo." % (what, sp)), False
        for p in (rel, ab, rp):
            if guarded(p) or (recursive and guarded_ancestor(p)):
                return (DENY, "%s of a guardrail file or a directory holding one (%s) — this "
                              "switches the guard off. Have a human do it." % (what, w)), False
        if recursive and "$" in v and not getattr(w, "opaque", False):
            empty = norm(_VAR_RX.sub("", v))
            esp = star_parent(_VAR_RX.sub("", v))
            if (is_abs(empty) and catastrophic(empty)) or (esp is not None and is_abs(norm(esp))
                                                           and catastrophic(norm(esp))):
                return (DENY, "%s of %s — if that variable is empty or unset this is rm -rf / "
                              "(or of $HOME). Set it in the same command, or write ${VAR:?}."
                        % (what, w)), False
        if recursive and ctx.project and is_abs(ab) and is_ancestor_or_self(ab, ctx.project):
            return (DENY, "%s of the project directory itself or a parent of it (%s) — it takes "
                          "the guard, the gates and uncommitted work with it." % (what, w)), False
        if recursive and is_abs(ab):
            f = fold(ab).rstrip("/")
            for which in (".git", ".specify", ".specify/memory"):
                if f.endswith("/" + which) and _remote_less_repo(ab, which, ctx):
                    return (DENY, "%s of %s in a repository with NO remote — this is the only "
                                  "copy of that history. Push to a remote first." % (what, w)), False
        why = gate_wiring(rel) or gate_wiring(ab)
        if why:
            return (ASK, "deleting %s." % why), False
    if not recursive:
        return None, True
    if getattr(w, "opaque", False):
        return None, False
    safe = all(_safe(v, rel, ab, ctx) for v, rel, ab in forms) and bool(forms)
    return None, safe


def _safe(v, rel, ab, ctx):
    # scratch: an absolute temp path, or a relative one under a temp dir this command cd'd into
    if is_abs(rel) and in_scratch(rel, ctx.scratch_extra):
        return True
    if not is_abs(rel) and ctx.cd and in_scratch(norm(v, ctx.cd), ctx.scratch_extra):
        return True
    home = norm(_HOME)
    for entry in ctx.cfg["safe_dirs"]:
        if entry.startswith("~/"):
            anchored = norm(home + entry[1:])
            if is_abs(ab) and (fold(ab) == fold(anchored) or fold(ab).startswith(fold(anchored) + "/")):
                if ".." not in _slash(v).split("/"):
                    return True
    if is_abs(rel) or rel.startswith("~") or rel.startswith("$") or not rel or rel == ".":
        return False
    if ".." in _slash(v).split("/") or ".." in rel.split("/"):
        return False
    parts = rel.rstrip("/").split("/")
    for entry in ctx.cfg["safe_dirs"]:
        if entry.startswith("~/"):
            continue
        ep = entry.strip("/").split("/")
        if len(ep) <= len(parts) and all(fnmatch.fnmatchcase(a, b) for a, b in
                                         zip(parts[-len(ep):], ep)):
            return True
    return False


# ---------------------------------------------------------------------------------------------
# argv helpers
# ---------------------------------------------------------------------------------------------
def base_name(w):
    b = _slash(str(w)).rstrip("/").rsplit("/", 1)[-1].lstrip("\\")
    b = b.lower()
    return b[:-4] if b.endswith(".exe") else b


KEYWORDS = {"if", "then", "else", "elif", "do", "while", "until", "!", "{", "time", "coproc"}
ENDERS = {"fi", "done", "esac", "}", "in"}

# Wrappers that put the real command later in argv, with the options that consume an operand.
# The v1.3 audit found `sudo rm -rf /` and `FOO=1 rm -rf /` returning {}: argv[0] was token 0.
WRAPPERS = {
    "sudo": {"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-T", "-U", "-R", "--user",
             "--group", "--chdir", "--host", "--prompt", "--role", "--type", "--other-user"},
    "doas": {"-u", "-C"},
    "env": {"-u", "-C", "-P", "--unset", "--chdir"},
    "command": set(), "builtin": set(), "exec": {"-a"}, "nohup": set(), "setsid": set(),
    "time": {"-o", "-f", "--output", "--format"}, "nice": {"-n", "--adjustment"},
    "ionice": {"-c", "-n", "-p", "--class", "--classdata"}, "stdbuf": {"-i", "-o", "-e"},
    "timeout": {"-s", "-k", "--signal", "--kill-after"},
    "xargs": {"-I", "-n", "-P", "-L", "-d", "-E", "-a", "-s", "--max-args", "--max-procs",
              "--delimiter", "--arg-file", "--replace", "--max-lines"},
    "flock": {"-w", "-E", "--timeout", "--conflict-exit-code"},
    "proxychains": {"-f"}, "proxychains4": {"-f"}, "chronic": set(), "unbuffer": set(),
    "unshare": {"-S", "-G", "--setuid", "--setgid"}, "firejail": set(),
    "script": {"-T", "-B", "-I", "-O", "-E", "-o", "-m", "--log-timing", "--log-io"},
    "systemd-run": {"-u", "-p", "-E", "--unit", "--property", "--setenv", "-M", "--machine"},
    "strace": {"-o", "-e", "-p", "-s", "-E", "-u", "-a", "-b", "-I", "-O", "-S", "-X", "-P"},
    "ltrace": {"-o", "-e", "-p", "-s", "-u", "-n", "-a"},
    "caffeinate": {"-t", "-w"}, "busybox": set(), "toybox": set(), "watch": {"-n", "-d"},
    "shx": set(),
    "npx": {"-p", "--package"}, "bunx": {"-p", "--package"}, "pnpx": set(), "uvx": {"--from", "--with", "-p", "--python"},
}
RUNNER_PAIRS = {("npm", "exec"), ("pnpm", "exec"), ("pnpm", "dlx"), ("yarn", "dlx"),
                ("yarn", "exec"), ("bun", "x"), ("uv", "run"), ("poetry", "run"),
                ("pipenv", "run"), ("pdm", "run"), ("hatch", "run"), ("rye", "run"),
                ("bundle", "exec"), ("pixi", "run"), ("mise", "exec")}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "mksh", "ash", "fish"}
PWSH = {"pwsh", "powershell"}
INTERPRETERS_RX = re.compile(r"^(?:python[\d.]*|pypy[\d.]*|node|nodejs|deno|bun|ruby|perl[\d.]*"
                             r"|php[\d.]*|lua[\d.]*|rscript|osascript|tclsh|groovy|jshell)$")
READONLY_ARGV0 = {
    "echo", "printf", "grep", "rg", "egrep", "fgrep", "cat", "bat", "less", "more", "head",
    "tail", "ls", "wc", "sort", "uniq", "diff", "man", "which", "type", "file", "stat", "jq",
    "yq", "column", "tree", "du", "df", "pwd", "whoami", "date", "true", "false", "test", "[",
    "[[", "basename", "dirname", "realpath", "readlink", "cut", "tr", "nl", "od", "xxd",
    "hexdump", "strings", "cmp", "comm", "sha256sum", "shasum", "md5sum", "md5", "get-content",
    "select-string", "get-childitem", "write-output", "write-host", "get-item", "test-path",
}
# awk can spawn a shell from its program text, so it is NOT read-only (the v1.3 audit:
# awk 'BEGIN{system("rm -rf /")}' rode the skip list).
EXECUTORS = {"awk", "gawk", "mawk", "nawk"}


def split_opts(args):
    """(options, operands) with a `--` end-of-options marker honoured."""
    opts, ops, done = [], [], False
    for a in args:
        if done:
            ops.append(a)
        elif a == "--":
            done = True
        elif a.startswith("-") and a != "-":
            opts.append(a)
        else:
            ops.append(a)
    return opts, ops


def short_has(opts, letter):
    return any(not o.startswith("--") and letter in o[1:] for o in opts)


def strip_wrappers(words, ctx, findings):
    """Drop env assignments, keywords and wrappers so argv[0] is the real command.

    Records assignments into ctx.vars. Appends inner command strings (env -S, flock -c,
    script -c) to findings["inner"].
    """
    w = list(words)
    i = 0
    while i < len(w):
        t = str(w[i])
        if t in KEYWORDS:
            i += 1
            continue
        if t == "function":
            i += 2
            continue
        m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(\+?)=(.*)", t, re.S)
        if m:
            record_assign(m.group(1), m.group(3), ctx, findings)
            i += 1
            continue
        b = base_name(t)
        if b in WRAPPERS:
            if b == "command" and i + 1 < len(w) and str(w[i + 1]) in ("-v", "-V"):
                return []                                # `command -v x` only prints a path
            takes = WRAPPERS[b]
            if b == "xargs":
                findings["xargs"] = True
            i += 1
            while i < len(w) and str(w[i]).startswith("-") and str(w[i]) != "-":
                o = str(w[i])
                if b == "env" and (o.startswith("-S") or o.startswith("--split-string")):
                    if o in ("-S", "--split-string") and i + 1 < len(w):
                        findings["inner"].append(str(w[i + 1]))
                        i += 2
                    else:                                # -S'rm -rf /' / --split-string=…
                        findings["inner"].append(o[2:] if o.startswith("-S") else o.split("=", 1)[-1])
                        i += 1
                    continue
                if b in ("flock", "script") and (o == "--command" or re.fullmatch(r"-[a-zA-Z]*c", o)) \
                        and i + 1 < len(w):
                    findings["inner"].append(str(w[i + 1]))
                    i += 2
                    continue
                i += 2 if (o in takes and "=" not in o) else 1
            if b == "timeout" and i < len(w) and re.fullmatch(r"\d+(\.\d+)?[smhd]?", str(w[i])):
                i += 1
            if b in ("flock", "script") and i < len(w):
                i += 1                   # the lock file; script's typescript (BSD: then a command)
            if b == "env":
                while i < len(w) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", str(w[i]), re.S):
                    mm = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", str(w[i]), re.S)
                    record_assign(mm.group(1), mm.group(2), ctx, findings)
                    i += 1
            continue
        if i + 1 < len(w) and (b, str(w[i + 1]).lower()) in RUNNER_PAIRS:
            i += 2
            while i < len(w) and str(w[i]).startswith("-"):
                i += 1
            if i < len(w) and str(w[i]) == "--":
                i += 1
            continue
        break
    return w[i:]


MKTEMP_RX = re.compile(r"\$\(\s*mktemp(?:\s+-[a-zA-Z]+)*(?:\s+-t)?(?:\s+[^\s/)]+)?\s*\)")


def record_assign(name, value, ctx, findings):
    # `T=$(mktemp -d)` is a fresh directory under the temp root: remember it as scratch, so
    # the `rm -rf "$T"` that ends every such script stays silent.
    ctx.vars[name] = ["/tmp/mktemp.careful"] if MKTEMP_RX.fullmatch(value) else [value]
    up = name.upper()
    low = value.lower()
    if (up.startswith("GIT_CONFIG_KEY_") and low == "core.hookspath") or \
            (up == "GIT_CONFIG_PARAMETERS" and "core.hookspath" in low):
        findings["verdicts"].append((ASK, "git hooks path overridden through the environment "
                                          "(%s) — this can skip the gate chain's git hook." % name))


# ---------------------------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------------------------
def protected(branch, ctx):
    b = branch
    for pre in ("refs/heads/", "heads/"):
        if b.startswith(pre):
            b = b[len(pre):]
    return any(fnmatch.fnmatchcase(b, pat) for pat in ctx.cfg["protected_branches"])


def git_out(args, gitdir):
    try:
        r = subprocess.run(["git"] + (["-C", gitdir] if gitdir else []) + args,
                           capture_output=True, text=True, timeout=2)
        return r.returncode, r.stdout.strip()
    except Exception:
        return 1, ""


def current_branch(gitdir):
    """The checked-out branch, or None when it cannot be named.

    F26: this used `git rev-parse --abbrev-ref HEAD`, which prints the literal "HEAD" when
    detached and in an unborn repository, so `git push -f origin HEAD` relaxed to ask there —
    against its own comment. Detached HEAD and unborn branches are now unknown, and unknown
    denies (there is nothing to push from an unborn branch anyway, so the deny costs nothing).
    """
    rc, out = git_out(["symbolic-ref", "--quiet", "--short", "HEAD"], gitdir)
    if rc != 0 or not out:
        return None
    rc2, _ = git_out(["rev-parse", "--quiet", "--verify", "HEAD"], gitdir)
    if rc2 != 0:
        return None
    return out


GIT_GLOBAL_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                       "--config-env", "--super-prefix", "--list-cmds", "--attr-source"}
PUSH_OPT_WITH_ARG = {"-o", "--push-option", "--receive-pack", "--exec", "--repo"}


def rule_git(argv, seg, ctx):
    words = [str(x) for x in argv[1:]]
    gitdir, i, verdict = None, 0, None
    while i < len(words) and words[i].startswith("-"):
        o = words[i]
        val = words[i + 1] if i + 1 < len(words) else ""
        if o == "-C":
            gitdir = norm(val, gitdir or ctx.base()) if val else gitdir
        m = re.match(r"alias\.[^=]+=\s*!(.*)", val, re.S) if o == "-c" else None
        if m:
            verdict = worse(verdict, inspect_command(m.group(1), "bash", ctx, MAX_DEPTH))
        if o == "-c" and val.lower().replace(" ", "").startswith("core.hookspath"):
            verdict = worse(verdict, (ASK, "git -c core.hooksPath=… — runs git with the hooks "
                                           "directory swapped, skipping the gate chain's hook."))
        i += 2 if (o in GIT_GLOBAL_WITH_ARG and "=" not in o) else 1
    if i >= len(words):
        return verdict
    sub = words[i]
    args = [str(a) for a in canon_args(words[i + 1:], GIT_LONG_OPTS.get(sub, ()))]
    gitdir = gitdir or ctx.base()
    opts, ops = split_opts(args)
    anyarg = lambda *xs: any(a in xs for a in args)

    if sub in ("commit", "push", "merge", "rebase", "am", "cherry-pick", "revert") and \
            "--no-verify" in args:
        verdict = worse(verdict, (ASK, "git %s --no-verify — skips the git hooks, including the "
                                       "gate chain's pre-commit hook." % sub))
    if sub == "commit":
        for o in opts:
            if o.startswith("-") and not o.startswith("--"):
                for ch in o[1:]:
                    if ch in "mFcCtSu":
                        break                            # the rest of the cluster is an argument
                    if ch == "n":
                        verdict = worse(verdict, (ASK, "git commit -n (--no-verify) — skips the "
                                                       "gate chain's pre-commit hook."))

    if sub == "config":
        keys = [a for a in args if a.lower() == "core.hookspath"]
        if keys:
            reads = {"--get", "--get-all", "--get-regexp", "get", "-l", "--list", "list",
                     "--show-origin", "--show-scope"}
            writes = {"--unset", "--unset-all", "--add", "--replace-all", "set", "unset",
                      "--edit", "-e"}
            k = args.index(keys[0])
            after = [a for a in args[k + 1:] if not a.startswith("-")]
            if anyarg(*writes) or (after and not anyarg(*reads)):
                verdict = worse(verdict, (ASK, "git config core.hooksPath — changes which git "
                                               "hooks run; the gate chain's hook can drop out."))
        return verdict

    if sub == "push":
        return worse(verdict, rule_git_push(args, gitdir, ctx))

    if sub == "worktree" and ops[:1] == ["remove"] and (anyarg("--force", "-f") or "-ff" in args):
        return worse(verdict, (ASK, "git worktree remove --force — deletes a worktree that still "
                                    "has modified or untracked files; they exist nowhere else."))
    if sub == "reset" and "--hard" in opts:
        return worse(verdict, (ASK, "git reset --hard — discards all uncommitted changes."))

    if sub in ("checkout", "restore", "rm", "mv", "clean"):
        # F9: `git rm`, `git checkout HEAD~1 -- .claude/settings.json` and `git restore` all
        # rewrote or removed the guard with {}. Every pathspec is judged; a branch name that
        # looks like a guarded path is not a real case.
        paths = args[args.index("--") + 1:] if "--" in args else ops
        for pth in paths:
            hit = touches_guard(_word(pth, False), ctx, ancestors=True)
            if hit:
                return worse(verdict, (DENY, "git %s on a guardrail file or a directory holding "
                                             "one (%s) — it rewrites or removes the guard." %
                                       (sub, pth)))
        if sub != "clean":
            for pth in paths:
                for v, rel, ab in _forms(_word(pth, False), ctx):
                    why = gate_wiring(rel) or gate_wiring(ab)
                    if why:
                        verdict = worse(verdict, (ASK, "git %s on %s; a human should see it."
                                                  % (sub, why)))
                        break
    if sub in ("checkout", "restore") and "." in ops:
        return worse(verdict, (ASK, "git checkout/restore . — discards all uncommitted "
                                    "working-tree changes."))
    if sub in ("checkout", "switch") and (anyarg("-f", "--force", "--discard-changes")):
        return worse(verdict, (ASK, "git %s --force — discards local changes." % sub))
    if sub == "clean" and any(not o.startswith("--") and "f" in o[1:] or o == "--force" for o in opts):
        return worse(verdict, (ASK, "git clean -f — deletes untracked files; they were never "
                                    "committed, so nothing can bring them back."))
    if sub == "branch" and ("-D" in opts or ("--delete" in opts and "--force" in opts)
                            or any(re.fullmatch(r"-[a-zA-Z]*(df|fd)[a-zA-Z]*", o) for o in opts)):
        return worse(verdict, (ASK, "git branch -D — force-deletes a branch, unmerged commits "
                                    "included."))
    if sub == "reflog" and "expire" in ops:
        return worse(verdict, (ASK, "git reflog expire — discards the reflog, the last route back "
                                    "to a lost commit."))
    if sub == "gc" and any(a.startswith("--prune") for a in args):
        return worse(verdict, (ASK, "git gc --prune — drops unreachable objects for good."))
    if sub == "stash" and "clear" in ops:
        return worse(verdict, (ASK, "git stash clear — deletes every stash entry."))
    if sub in ("filter-branch", "filter-repo"):
        return worse(verdict, (ASK, "git %s — rewrites history across the repository." % sub))
    return verdict


def rule_git_push(args, gitdir, ctx):
    lease = any(a.startswith("--force-with-lease") or a.startswith("--force-if-includes")
                for a in args)
    forced = any(a in ("--force", "-f") or (re.fullmatch(r"-[a-zA-Z]+", a) and "f" in a[1:])
                 for a in args)
    pos, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a in PUSH_OPT_WITH_ARG:
            skip = True
            continue
        if not a.startswith("-"):
            pos.append(a)
    refspecs = pos[1:]
    plus = any(r.startswith("+") and len(r) > 1 for r in refspecs)
    deleting = any(a in ("--delete", "-d") for a in args) or any(r.startswith(":") for r in refspecs)
    if "--prune" in args:
        return (ASK, "git push --prune — deletes every remote branch that has no local "
                     "counterpart under the pushed refspec.")
    if "--mirror" in args:
        return (DENY, "git push --mirror — deletes every remote ref that is missing locally. "
                      "Push the branch you mean by name instead.")
    if not (lease or forced or plus or deleting):
        return None
    if lease and not (plus or deleting):
        return (ASK, "git push --force-with-lease — still rewrites remote history, but refuses "
                     "if the remote moved.")
    if forced and any(a in ("--all", "--branches") for a in args):
        return (DENY, "git push --force --all — force-pushes every branch, protected ones "
                      "included.")
    dests = []
    unknown = False
    for r in refspecs:
        r = r.lstrip("+")
        d = r.split(":")[-1] if ":" in r else r
        if "$" in d or "`" in d:
            unknown = True                   # `origin ma${X}in`, `origin $(git branch …)`
            continue
        dests.append(d)
    resolved = []
    for d in dests or ([] if unknown else [None]):
        if d in (None, "", "HEAD", "@"):
            cur = current_branch(gitdir)
            if cur is None:
                unknown = True
                continue
            resolved.append(cur)
            if d is None and not deleting:
                # no refspec: push.default decides. `matching` pushes every matching branch
                # (main included); `upstream` pushes to whatever the branch tracks.
                rc, mode = git_out(["config", "push.default"], gitdir)
                if mode == "matching":
                    resolved.append("main")
                    resolved.extend(ctx.cfg["protected_branches"])
                rc, up = git_out(["rev-parse", "--abbrev-ref", "@{upstream}"], gitdir)
                if rc == 0 and "/" in up:
                    resolved.append(up.split("/", 1)[1])
        else:
            resolved.append(d)
    hit = [d for d in resolved if protected(d, ctx)]
    if deleting:
        if hit:
            return (DENY, "deleting the protected remote branch '%s' — this removes shared "
                          "history from the remote." % hit[0])
        return (ASK, "git push --delete — removes a ref from the remote.")
    if hit:
        return (DENY, "force-push to the protected branch '%s' — rewrites shared history "
                      "irreversibly. Push without --force, or use --force-with-lease." % hit[0])
    if unknown:
        return (DENY, "force-push to a branch that cannot be named here (detached or unborn HEAD, "
                      "or a destination built at runtime) — treated as protected. Name the "
                      "branch, or use --force-with-lease.")
    return (ASK, "git force-push — rewrites remote history; collaborators may lose work.")


def rule_rm(argv, seg, ctx, a0):
    opts, targets = split_opts(canon_args(argv[1:], LONG_OPTS["rm"] if a0 in ("rm", "srm") else ()))
    # rimraf (the npm package, often run through npx) is rm -rf under another name.
    rec = a0 in ("rimraf", "del-cli") or (a0 in ("rm", "srm") and any(
        o == "--recursive" or (not o.startswith("--") and ("r" in o[1:] or "R" in o[1:]))
        for o in opts))
    if not targets:
        return (ASK, "recursive delete with targets fed from elsewhere (xargs, globs) — cannot "
                     "see what it removes.") if rec else None
    all_safe, verdict = True, None
    for t in targets:
        v, safe = judge_delete(t, ctx, rec, "recursive delete" if rec else "delete")
        if v and v[0] == DENY:
            return v
        verdict = worse(verdict, v)
        all_safe = all_safe and safe
    if verdict:
        return verdict
    if rec and not all_safe:
        return (ASK, "recursive delete (rm -r) — permanently removes files.")
    return None


def _t_arg(argv):
    """cp/mv/ln/install `-t DIR` / `--target-directory=DIR`, removed from argv."""
    out, tdir, i = [], None, 0
    while i < len(argv):
        a = str(argv[i])
        if a in ("-t", "--target-directory") and i + 1 < len(argv):
            tdir = argv[i + 1]
            i += 2
            continue
        if a.startswith("--target-directory="):
            tdir = _word(a.split("=", 1)[1], getattr(argv[i], "opaque", False))
            i += 1
            continue
        out.append(argv[i])
        i += 1
    return out, tdir


def _join(dest, src):
    name = _slash(str(src)).rstrip("/").rsplit("/", 1)[-1]
    return _word(_slash(str(dest)).rstrip("/") + "/" + name, getattr(dest, "opaque", False))


def rule_copyish(argv, seg, ctx, a0):
    """mv / cp / ln / install / rsync: what gets removed, and what gets written."""
    if a0 == "cp":
        argv = argv[:1] + canon_args(argv[1:], LONG_OPTS["cp"])
    argv, tdir = _t_arg(argv)
    opts, ops = split_opts(argv[1:])
    if a0 == "install" and short_has(opts, "d"):
        return None                                      # install -d only creates directories
    if a0 == "rsync":
        dest = ops[-1] if ops else None
        if dest is None or re.match(r"^[^/]*:", str(dest)):
            return None                                  # remote destination: not this machine
        if any(o.startswith("--del") for o in opts):
            v, _ = judge_delete(dest, ctx, True, "rsync --delete into")
            if v and v[0] == DENY:
                return v
        if touches_guard(dest, ctx, ancestors=True):
            return (DENY, "rsync into a directory holding guardrail files (%s) — `src/` copies "
                          "its contents over whatever is there, the guard included." % dest)
        verdict = judge_write(dest, ctx, "rsync")
        for s in ops[:-1]:
            verdict = worse(verdict, judge_write(_join(dest, s), ctx, "rsync"))
        return verdict
    if tdir is not None:
        sources, dest = list(ops), tdir
    elif len(ops) >= 2:
        sources, dest = list(ops[:-1]), ops[-1]
    else:
        return None
    # F9: `mv .claude .claude.off`, `mv .claude/hooks/check-careful.sh /tmp/`, and
    # `ln .claude/hooks/check-careful.py x` (a second name for the guard) all passed with {}.
    # `cp -r x/. .claude/` copies x's CONTENTS over .claude — hooks and settings included.
    recursive = a0 == "cp" and (short_has(opts, "r") or short_has(opts, "R") or
                                short_has(opts, "a") or "--recursive" in opts or "--archive" in opts)
    if recursive and touches_guard(dest, ctx, ancestors=True):
        return (DENY, "recursive copy into a directory holding guardrail files (%s) — it can "
                      "overwrite the guard." % dest)
    verdict = None
    if a0 in ("mv", "rename", "ln"):
        for s in sources:
            if touches_guard(s, ctx, ancestors=True):
                return (DENY, "%s of a guardrail file or a directory holding one (%s) — it "
                              "moves the guard away or gives it a second, unguarded name." % (a0, s))
            if a0 != "ln":
                for v, rel, ab in _forms(s, ctx):
                    why = gate_wiring(rel) or gate_wiring(ab)
                    if why:
                        verdict = worse(verdict, (ASK, "%s moves away %s; a human should see it."
                                                  % (a0, why)))
                        break
    for t in [dest] + [_join(dest, s) for s in sources]:
        v = judge_write(t, ctx, a0)
        if v and v[0] == DENY:
            return v
        verdict = worse(verdict, v)
    return verdict


def rule_dd(argv, seg, ctx):
    for a in argv[1:]:
        a = str(a)
        if a.lower().startswith("of="):
            return judge_write(_word(a[3:], False), ctx, "dd")
    return None


DEVICE_TOOLS = {"mkfs", "mke2fs", "mkswap", "newfs", "mkdosfs", "mkntfs", "mkexfatfs"}


def rule_device(argv, seg, ctx, a0):
    opts, ops = split_opts(argv[1:])
    devs = [o for o in ops if BLOCK_DEVICE_RX.search(norm(str(o)))]
    if a0 == "wipefs":
        if not (short_has(opts, "a") or "--all" in opts or short_has(opts, "o") or
                any(o.startswith("--offset") for o in opts)):
            return None
        if devs:
            return (DENY, "wipefs -a on a block device — erases partition-table and filesystem "
                          "signatures. Have a human run it.")
        return (ASK, "wipefs -a — erases filesystem signatures.")
    if a0 in ("blkdiscard", "shred") and devs:
        return (DENY, "%s on a block device — destroys every byte on it." % a0)
    if a0 == "sgdisk" and devs and (short_has(opts, "Z") or short_has(opts, "o") or
                                    "--zap-all" in opts or "--clear" in opts):
        return (DENY, "sgdisk --zap-all/--clear — destroys the partition table.")
    if a0 == "diskutil" and ops and ops[0].lower() in (
            "erasedisk", "erasevolume", "zerodisk", "randomdisk", "secureerase",
            "partitiondisk", "reformat", "apfs"):
        if ops[0].lower() != "apfs" or (len(ops) > 1 and ops[1].lower().startswith("delete")):
            return (DENY, "diskutil %s — erases a disk or volume. Have a human run it." % ops[0])
    if a0 in DEVICE_TOOLS or a0.startswith("mkfs.") or a0.startswith("newfs_"):
        if devs:
            return (DENY, "%s on a block device — formats it; everything on it is gone." % a0)
        return (ASK, "%s — creates a filesystem over the target, destroying what was there." % a0)
    return None


def rule_flash(argv, seg, ctx, a0):
    ops = [str(o).lower() for o in argv[1:] if not str(o).startswith("-")]
    flags = [str(o).lower() for o in argv[1:] if str(o).startswith("-")]
    if a0 in ("espefuse", "espefuse.py") or (a0 == "idf.py" and any(o.startswith("efuse") for o in ops)):
        if any(re.match(r"(?:efuse[-_])?(?:burn|write[-_]protect|read[-_]protect|set[-_]flash[-_]voltage)", o)
               for o in ops):
            return (DENY, "eFuse burn/protect — one-time programmable and physically irreversible; "
                          "a wrong value can brick the chip. Have a human run it.")
    if a0 in ("esptool", "esptool.py", "idf.py") and any(o in ("erase_flash", "erase-flash",
                                                               "erase_region", "erase-region")
                                                         for o in ops):
        return (ASK, "flash erase — wipes the device's firmware and data (reflashable).")
    if a0 == "st-flash" and "erase" in ops:
        return (ASK, "st-flash erase — wipes the device's flash (reflashable).")
    if a0 == "nrfjprog" and any(f in ("--eraseall", "-e", "--recover") for f in flags):
        return (ASK, "nrfjprog --eraseall/--recover — wipes the device's flash.")
    if a0 in ("nrfutil", "pyocd", "probe-rs") and any(o in ("erase", "recover") for o in ops):
        return (ASK, "%s erase — wipes the device's flash." % a0)
    return None


def _ops(argv):
    return [str(a) for a in argv[1:] if not str(a).startswith("-")]


def rule_iac(argv, seg, ctx, a0):
    ops, args = _ops(argv), [str(a) for a in argv[1:]]
    low = [o.lower() for o in ops]
    pairs = list(zip(low, low[1:]))
    if a0 in ("terraform", "tofu", "terragrunt", "cdktf"):
        if "destroy" in low:
            return (ASK, "%s destroy — tears down real infrastructure; data in it goes too." % a0)
        if "apply" in low and any(a.lstrip("-") == "destroy" for a in args):
            return (ASK, "%s apply -destroy — tears down real infrastructure." % a0)
        if ("state", "rm") in pairs or ("workspace", "delete") in pairs:
            return (ASK, "%s state rm / workspace delete — edits or deletes state; resources can "
                         "be orphaned." % a0)
    if a0 == "pulumi":
        if "destroy" in low or "down" in low or ("stack", "rm") in pairs or ("state", "delete") in pairs:
            return (ASK, "pulumi destroy / stack rm / state delete — tears down infrastructure or "
                         "deletes its state.")
    if a0 == "cdk" and "destroy" in low:
        return (ASK, "cdk destroy — deletes the CloudFormation stacks and what they own.")
    if a0 in ("serverless", "sls") and "remove" in low:
        return (ASK, "serverless remove — deletes the deployed service.")
    if a0 == "sam" and "delete" in low:
        return (ASK, "sam delete — deletes the deployed stack.")
    if a0 == "helm" and any(o in ("uninstall", "delete", "del", "un") for o in low[:3]):
        return (ASK, "helm uninstall — removes a release and the resources it owns.")
    if a0 in ("kubectl", "oc") and "delete" in low:
        return (ASK, "%s delete — removes cluster resources; may impact production." % a0)
    return None


CLOUD_CLIS = {"aws", "gcloud", "gsutil", "az", "doctl", "hcloud", "linode-cli", "fly", "flyctl",
              "heroku", "vercel", "netlify", "railway", "oci", "ibmcloud", "scw", "eksctl",
              "wrangler", "supabase", "firebase", "render"}


def rule_cloud(argv, seg, ctx, a0):
    ops = [o.lower() for o in _ops(argv)]
    args = [str(a).lower() for a in argv[1:]]
    if a0 == "aws" and ops[:2] == ["s3", "rm"] and "--recursive" in args:
        return (ASK, "aws s3 rm --recursive — deletes every object under the prefix.")
    if a0 == "aws" and ops[:2] == ["s3", "rb"]:
        return (ASK, "aws s3 rb — deletes a bucket (with --force, its contents first).")
    if a0 == "aws" and ops[:2] == ["s3", "sync"] and "--delete" in args:
        return (ASK, "aws s3 sync --delete — deletes destination objects missing at the source.")
    if a0 == "gsutil" and ops[:1] in (["rm"], ["rb"]) or (a0 == "gcloud" and ops[:2] == ["storage", "rm"]):
        return (ASK, "%s — deletes cloud storage objects or buckets." % " ".join([a0] + ops[:2]))
    if a0 == "supabase" and ops[:2] == ["db", "reset"]:
        return (ASK, "supabase db reset — drops and recreates the database.")
    if a0 == "heroku" and any(o in ("pg:reset", "apps:destroy", "apps:delete") for o in ops):
        return (ASK, "heroku %s — deletes an app or wipes its database." % ops[0])
    for o in ops:
        if o in ("delete", "destroy", "rm", "rb", "remove", "purge", "terminate") or \
                re.match(r"(?:delete|terminate|destroy|purge)-", o) or re.search(r":(?:destroy|delete|reset)$", o):
            return (ASK, "%s %s — deletes cloud resources; what they held may not come back." % (a0, o))
    return None


DB_RESET = [
    # (argv0 names, words that must appear, reason)
    ({"dropdb"}, None, "dropdb — deletes an entire PostgreSQL database."),
    ({"prisma"}, ("migrate", "reset"), "prisma migrate reset — drops the database and re-applies migrations."),
    ({"rails", "rake"}, {"db:drop", "db:reset", "db:schema:load", "db:purge", "db:rollback",
                         "db:migrate:down", "db:truncate_all", "db:seed:replant", "db:migrate:reset"},
     "rails db:drop/reset/rollback — drops or rewinds the database."),
    ({"artisan"}, {"migrate:fresh", "migrate:reset", "migrate:rollback", "migrate:refresh", "db:wipe"},
     "artisan migrate:fresh/reset/rollback/db:wipe — drops or rewinds the database."),
    ({"mix"}, {"ecto.drop", "ecto.reset", "ecto.rollback"}, "mix ecto.drop/reset/rollback — drops or rewinds the database."),
    ({"diesel"}, {"reset", "revert", "redo"}, "diesel database reset / migration revert — drops or rewinds the database."),
    ({"sqlx"}, {"drop", "reset", "revert"}, "sqlx database drop/reset / migrate revert — drops or rewinds the database."),
    ({"typeorm"}, {"schema:drop", "migration:revert"}, "typeorm schema:drop / migration:revert — drops or rewinds the schema."),
    ({"sequelize", "sequelize-cli"}, {"db:drop", "db:migrate:undo", "db:migrate:undo:all"}, "sequelize db:drop / migrate:undo — drops or rewinds the database."),
    ({"knex"}, {"migrate:rollback", "migrate:down"}, "knex migrate:rollback — rewinds the schema."),
    ({"drizzle-kit"}, {"drop"}, "drizzle-kit drop — deletes a migration."),
    ({"alembic"}, {"downgrade"}, "alembic downgrade — rewinds the schema past possibly destructive steps."),
    ({"flyway"}, {"clean", "undo"}, "flyway clean/undo — drops every object in the schema, or rewinds it."),
    ({"liquibase"}, {"drop-all", "dropall", "rollback", "rollback-count", "rollbackcount", "rollback-to-date"},
     "liquibase drop-all/rollback — drops or rewinds the schema."),
    ({"dbmate"}, {"drop", "down", "rollback"}, "dbmate drop/down — drops or rewinds the database."),
    ({"goose"}, {"down", "reset", "down-to"}, "goose down/reset — rewinds the schema."),
    ({"atlas"}, ("schema", "clean"), "atlas schema clean — drops every object in the schema."),
    ({"redis-cli", "valkey-cli", "keydb-cli"}, {"flushall", "flushdb"}, "redis FLUSHALL/FLUSHDB — deletes every key."),
]


def rule_db(argv, seg, ctx, a0):
    ops = [o.lower() for o in _ops(argv)]
    args = [str(a).lower() for a in argv[1:]]
    names = {a0} | {base_name(o) for o in ops[:1]}
    for who, need, reason in DB_RESET:
        if not (names & who):
            continue
        if need is None:
            return (ASK, reason)
        if isinstance(need, tuple):
            if all(x in ops for x in need):
                return (ASK, reason)
        elif any(o in need for o in ops):
            return (ASK, reason)
    if a0 == "prisma" and "db" in ops and "push" in ops and any(
            a in ("--force-reset", "--accept-data-loss") for a in args):
        return (ASK, "prisma db push --force-reset/--accept-data-loss — can drop data.")
    if a0 == "django-admin" or any(base_name(o) == "manage.py" for o in ops):
        if any(o in ("flush", "reset_db") for o in ops) or ("migrate" in ops and "zero" in ops):
            return (ASK, "django flush / migrate <app> zero — deletes every row or rewinds the schema.")
    if a0 == "bq" and "rm" in ops:
        return (ASK, "bq rm — deletes a BigQuery dataset or table.")
    if a0 == "mysqladmin" and "drop" in ops:
        return (ASK, "mysqladmin drop — deletes an entire database.")
    if a0 == "migrate" or (a0 in ("go", "make", "task", "just", "npm", "pnpm", "yarn", "bun")
                           and any("migrat" in o for o in ops)):
        if any(re.search(r"(?:^|[-_:])(?:down|force|drop|reset|rollback)(?:$|[-_:])", o) for o in ops):
            return (ASK, "migration down/force/drop — can roll a schema past a destructive step "
                         "(data loss).")
    return None


SQL_RULES = [
    (re.compile(r"\bdrop\s+(?:table|database|schema|keyspace)\b", re.I),
     "SQL DROP — permanently deletes database objects."),
    (re.compile(r"\btruncate\b", re.I), "SQL TRUNCATE — deletes all rows from a table."),
    (re.compile(r"\.drop(?:Database)?\s*\(", re.I), "MongoDB drop — deletes a collection or database."),
]


def sql_verdict(text):
    for rx, reason in SQL_RULES:
        if rx.search(text):
            return (ASK, reason)
    low = text.lower()
    if re.search(r"\b(?:delete\s+from|update)\b", low) and not re.search(r"\bwhere\b", low):
        return (ASK, "SQL DELETE/UPDATE without WHERE — affects every row in the table.")
    return None


def rule_publish(argv, seg, ctx, a0):
    ops = [o.lower() for o in _ops(argv)]
    args = [str(a).lower() for a in argv[1:]]
    dry = "--dry-run" in args or "-n" in args and a0 == "cargo"
    if a0 in ("npm", "pnpm", "yarn", "bun"):
        if "unpublish" in ops:
            return (ASK, "%s unpublish — removes a published version other people may depend on." % a0)
        if "publish" in ops and not dry:
            return (ASK, "%s publish — a published version is permanent; it cannot be reused." % a0)
    if a0 == "cargo":
        if "yank" in ops and "--undo" not in args:
            return (ASK, "cargo yank — withdraws a published version from new resolutions.")
        if "publish" in ops and not dry:
            return (ASK, "cargo publish — crates.io versions are permanent.")
    if a0 == "twine" and "upload" in ops:
        return (ASK, "twine upload — a published version is permanent.")
    if a0 in ("poetry", "flit", "hatch", "pdm", "uv") and "publish" in ops and not dry:
        return (ASK, "%s publish — a published version is permanent." % a0)
    if a0 == "gem" and ops[:1] and ops[0] in ("push", "yank"):
        return (ASK, "gem %s — publishes or withdraws a version." % ops[0])
    if a0 in ("dotnet", "nuget") and ("push" in ops or "delete" in ops) and (a0 == "nuget" or "nuget" in ops):
        return (ASK, "nuget push/delete — publishes or withdraws a package version.")
    if a0 == "gh":
        if ops[:2] in (["release", "delete"], ["release", "delete-asset"], ["repo", "delete"]):
            return (ASK, "gh %s %s — deletes it from GitHub." % (ops[0], ops[1]))
        if ops[:1] == ["api"] and ("delete" in args or "--method=delete" in args or "-xdelete" in args):
            for a in args:
                m = re.search(r"git/refs/heads/(.+)$", a)
                if m and protected(m.group(1), ctx):
                    return (DENY, "gh api DELETE of the protected branch '%s' — removes shared "
                                  "history from the remote." % m.group(1))
            return (ASK, "gh api DELETE — deletes a GitHub resource.")
    if a0 in ("vsce", "ovsx") and "unpublish" in ops:
        return (ASK, "%s unpublish — removes an extension from the marketplace." % a0)
    return None


def rule_docker(argv, seg, ctx, a0):
    ops = [o.lower() for o in _ops(argv)]
    args = [str(a).lower() for a in argv[1:]]
    if "down" in ops and ("-v" in args or "--volumes" in args or
                          any(re.fullmatch(r"-[a-z]*v[a-z]*", a) for a in args)):
        return (ASK, "docker compose down -v — destroys the persistent data volumes.")
    if ops[:2] in (["volume", "rm"], ["volume", "prune"]):
        return (ASK, "docker volume rm/prune — destroys persistent data volumes.")
    if ops[:2] == ["system", "prune"]:
        return (ASK, "docker system prune — may delete stopped containers, networks and cached "
                     "images (and volumes with --volumes).")
    if ops[:1] in (["rm"], ["rmi"]) or ops[:2] in (["container", "rm"], ["image", "rm"]):
        if any(a in ("-f", "--force") or re.fullmatch(r"-[a-z]*f[a-z]*", a) for a in args):
            return (ASK, "docker force-remove — deletes running containers or images in use.")
    return None


def _cluster_has(opt, letter, stop):
    """Short-option cluster `-pi.bak` has `letter` before any option that takes an argument."""
    if opt.startswith("--") or not opt.startswith("-"):
        return False
    for ch in opt[1:]:
        if ch == letter:
            return True
        if ch in stop:
            return False
    return False


def rule_inplace(argv, seg, ctx, a0):
    opts, ops = split_opts(canon_args(argv[1:], LONG_OPTS["sed"]) if a0 == "sed" else argv[1:])
    if a0 == "sed":
        inplace = any(o in ("-i", "--in-place") or o.startswith("--in-place=") or
                      _cluster_has(o, "i", "ef") for o in opts)
        if not inplace:
            return None
        explicit = any(o.startswith("-e") or o.startswith("-f") or
                       o.split("=", 1)[0] in ("--expression", "--file") for o in opts)
        files = ops if explicit else ops[1:]
    else:  # perl -i / ruby -i: letters after M m I e E l 0 x C d D r are that option's argument
        if not any(_cluster_has(o, "i", "MmIeEl0xCdDrV") for o in opts):
            return None
        files = [o for o in ops if getattr(o, "opaque", False) or not re.search(r"\s", str(o))]
    for f in files:
        v = judge_write(f, ctx, "%s -i" % a0)
        if v:
            return v
    return (ASK, "%s -i — rewrites files in place, with no backup unless a suffix was given." % a0)


def rule_writer_operands(argv, seg, ctx, a0):
    """Tools whose operands are files they modify: judge every operand."""
    opts, ops = split_opts(argv[1:])
    verdict = None
    for o in ops:
        if a0 == "truncate" and re.fullmatch(r"[+-<>/%]?\d+[KMGTPEZY]?i?B?", str(o)):
            continue
        v = judge_write(o, ctx, a0)
        if v and v[0] == DENY:
            return v
        if a0 in ("unlink", "shred"):
            dv, _ = judge_delete(o, ctx, False, a0)
            if dv and dv[0] == DENY:
                return dv
        if a0 in ("chmod", "chown", "chgrp", "chattr", "setfacl") and v and v[0] == ASK:
            continue                     # a system path chmod is not this guard's business
        verdict = worse(verdict, v)
    return verdict


FIND_FILTERS = {"-name", "-iname", "-path", "-ipath", "-wholename", "-iwholename", "-regex",
                "-iregex", "-lname", "-ilname"}


GUARD_BASENAMES = ("check-careful.sh", "check-careful.py", "careful.json", "settings.json",
                   "settings.local.json", "run-chain.sh", "check-plan-sync.sh", "pre-commit",
                   "settings.json.template")


def _reaches_guard(w, ctx):
    """True when a traversal from w would pass through the project's guarded directories."""
    for v, rel, ab in _forms(w, ctx):
        if not is_abs(ab):
            continue
        if ctx.project and is_ancestor_or_self(ab, ctx.project):
            return True
        if os.path.isdir(os.path.join(ab, ".claude", "hooks")) or \
                os.path.isfile(os.path.join(ab, "gates", "run-chain.sh")):
            return True
    return False


def rule_find(argv, seg, ctx):
    args = [str(a) for a in argv[1:]]
    roots = []
    for a in args:
        if a.startswith("-") or a in ("(", "!", ")"):
            break
        roots.append(a)
    deletes = "-delete" in args or any(
        a in ("-exec", "-execdir", "-ok", "-okdir") and i + 1 < len(args) and
        base_name(args[i + 1]) in ("rm", "shred", "unlink") for i, a in enumerate(args))
    execs = [base_name(args[i + 1]) for i, a in enumerate(args)
             if a in ("-exec", "-execdir", "-ok", "-okdir") and i + 1 < len(args)]
    writes = deletes or any(e not in READONLY_ARGV0 for e in execs)
    if writes and not deletes:
        # `find .claude -name settings.json -exec cp /dev/null {} \;` rewrote the guard with {}.
        pats = [args[i + 1] for i, a in enumerate(args[:-1]) if a in FIND_FILTERS]
        for r in roots or ["."]:
            w = _word(r, False)
            if touches_guard(w, ctx, ancestors=True) or (_reaches_guard(w, ctx) and any(
                    fnmatch.fnmatch(b, p.rsplit("/", 1)[-1]) for p in pats for b in GUARD_BASENAMES)):
                return (DENY, "find -exec %s over the guard's own files (%s) — it can rewrite or "
                              "remove them." % (", ".join(execs), r))
        return None
    if not deletes:
        return None
    # With a name filter the traversal picks files; without one (or with `-name '*'`) it takes
    # everything under the root, which is a recursive delete of the root in all but name.
    pats = [args[i + 1] for i, a in enumerate(args[:-1]) if a in FIND_FILTERS]
    filtered = any(p not in ("*", "**") for p in pats)
    for r in roots or ["."]:
        w = _word(r, False)
        if touches_guard(w, ctx, ancestors=True):
            return (DENY, "find -delete under a directory holding guardrail files (%s) — it "
                          "can remove the guard." % r)
        # `find . -name '*.sh' -delete` from the project root reaches .claude/hooks/ too.
        if filtered and _reaches_guard(w, ctx) and any(
                fnmatch.fnmatch(b, p.rsplit("/", 1)[-1]) for p in pats for b in GUARD_BASENAMES):
            return (DENY, "find -delete from %s with a filter that matches the guard's own files "
                          "(%s) — it would remove them too." % (r, ", ".join(pats)))
        if not filtered:
            v, _ = judge_delete(w, ctx, True, "find -delete of everything under")
            if v and v[0] == DENY:
                return v
    if _find_cache_cleanup(args, roots, ctx):
        return None
    return (ASK, "find -delete / -exec rm — removes every file the traversal matches; the match "
                 "set is not visible before it runs.")


# Bytecode a Python interpreter rewrites on the next import.
CACHE_FILE_PATTERNS = {"*.pyc", "*.pyo", "*.py[co]", "*.py[cod]"}


def _find_cache_cleanup(args, roots, ctx):
    """True for `find . -name '*.pyc' -delete` and `find . -type d -name __pycache__ -exec rm -rf
    {} +`: the find spelling of a cache cleanup that `rm -rf __pycache__` already does silently.

    Review 2026-09-29: both asked, careful.json could not silence them (safe_dirs was read for rm
    targets only), and the corpus had no find-based cleanup to notice. Silent only when every
    root is relative and inside the project, every -name/-iname is a safe_dirs entry or a
    bytecode pattern, and nothing else in the expression can widen the match: no -o, no !, no
    -path, no other -exec. Anything outside that shape keeps the ask.
    """
    for r in roots or ["."]:
        if is_abs(r) or r.startswith(("~", "$")) or ".." in _slash(r).split("/"):
            return False
    safe_names = {e for e in ctx.cfg["safe_dirs"] if "/" not in e and not e.startswith("~")}
    rest = args[len(roots):]
    i, names = 0, 0
    while i < len(rest):
        a = rest[i]
        nxt = rest[i + 1] if i + 1 < len(rest) else None
        if a in ("-name", "-iname") and nxt is not None:
            if nxt not in CACHE_FILE_PATTERNS and nxt not in safe_names:
                return False
            names, i = names + 1, i + 2
        elif (a == "-type" and nxt in ("f", "d")) or (
                a in ("-maxdepth", "-mindepth") and nxt is not None and nxt.isdigit()):
            i += 2
        elif a in ("-delete", "-print", "-print0", "-depth", "-prune"):
            i += 1
        elif a in ("-exec", "-execdir") and nxt is not None and base_name(nxt) == "rm":
            j = i + 2
            while j < len(rest) and re.fullmatch(r"-[rRf]+|--recursive|--force", rest[j]):
                j += 1
            if j + 1 >= len(rest) or rest[j] != "{}" or rest[j + 1] not in ("+", ";", "\\;"):
                return False
            i = j + 2
        else:
            return False
    return names > 0


def rule_extract(argv, seg, ctx, a0):
    """Archive extraction INTO a directory that holds guardrail files overwrites them."""
    args = [str(a) for a in argv[1:]]
    dests = []
    for i, a in enumerate(args):
        if a in ("-C", "--directory", "-d") and i + 1 < len(args):
            dests.append(args[i + 1])
        elif a.startswith("--directory="):
            dests.append(a.split("=", 1)[1])
        elif a0.startswith("7z") and a.startswith("-o") and len(a) > 2:
            dests.append(a[2:])
    for d in dests:
        if touches_guard(_word(d, False), ctx, ancestors=True):
            return (DENY, "%s extracting into a directory holding guardrail files (%s) — the "
                          "archive can overwrite the guard." % (a0, d))
    return None


def rule_adopt(argv, seg, ctx):
    words = [str(w) for w in argv]
    if any(base_name(w) == "adopt.py" for w in words) and "--upgrade" in [
            canon_long(w, LONG_OPTS["adopt.py"]) for w in words]:
        return (ASK, "adopt.py --upgrade — replaces the installed guard, gates and harness files; "
                     "meant to be run and reviewed by a human.")
    return None


def shell_script_operand(argv):
    """For sh/bash/zsh: ("c", string) | ("stdin", None) | ("file", path)."""
    args = [str(a) for a in argv[1:]]
    has_c, i = False, 0
    while i < len(args):
        a = args[i]
        if a == "--":
            i += 1
            break
        if a in ("-o", "+o", "-O", "+O", "--rcfile", "--init-file"):
            i += 2
            continue
        if re.fullmatch(r"[-+][a-zA-Z]+", a):
            if "c" in a[1:] and a[0] == "-":
                has_c = True
            if "s" in a[1:] and a[0] == "-" and not has_c:
                return ("stdin", None)
            i += 1
            continue
        if a.startswith("--"):
            i += 1
            continue
        break
    rest = argv[1 + i:]
    if has_c:
        return ("c", rest[0] if rest else None)
    if not rest:
        return ("stdin", None)
    return ("file", rest[0])


def pwsh_command_arg(argv):
    args = [str(a) for a in argv[1:]]
    for i, a in enumerate(args):
        al = a.lower()
        if al in ("-c", "-command", "/c", "-com", "-comm", "-comma", "-comman"):
            return ("c", " ".join(args[i + 1:]))
        if al in ("-e", "-ec", "-encodedcommand", "-enc", "-en"):
            try:
                import base64
                return ("c", base64.b64decode(args[i + 1]).decode("utf-16-le"))
            except Exception:
                return ("opaque", None)
        if al in ("-f", "-file"):
            return ("file", args[i + 1] if i + 1 < len(args) else None)
    return ("stdin", None)


EXEC_RX = re.compile(r"\bsystem\s*\(|\bpopen|\bexec[lv]?p?e?\s*\(|subprocess|\bspawn|child_process"
                     r"|execSync|os\.system|%x\{|\bRuntime\.getRuntime|Process\.Start|shell_exec"
                     r"|passthru|IO\.popen", re.I)
LITERAL_RX = re.compile(r"'([^'\n]{3,300})'|\"([^\"\n]{3,300})\"")
# A quoted string that is one path and nothing else ('.claude/settings.json', ">x.json").
PATH_LITERAL_RX = re.compile(r"(['\"])[ +<>|]*([^'\"\s]{1,300})\1")


def _resolved(w, ctx):
    if "$" not in w or getattr(w, "opaque", False):
        return w
    cands = set(expand(w, ctx))
    if len(cands) == 1:
        c = cands.pop()
        if "$" not in c:
            return _word(c, False)
    return w


def _shell_quote(w):
    return w if re.fullmatch(r"[\w@%+=:,./~-]+", w) else "'" + w.replace("'", "'\\''") + "'"


def _expanded_code(code, ctx):
    """The program text of sh -c / eval, with variables declared earlier in the command."""
    code = str(code)
    if "$" not in code:
        return [code]
    outs = [c for c in expand(_word(code, False), ctx)]
    return (outs or [code])[:4]


def literal_text(seg):
    """What a pipe source writes, when it is literal: echo/printf args, or cat <<heredoc."""
    ws = strip_wrappers(seg.words, Ctx({"protected_branches": [], "db_clients": set(),
                                        "safe_dirs": [], "extra_ask": [], "extra_deny": []},
                                       None, None, ()), {"inner": [], "verdicts": []})
    if not ws:
        return None
    a0 = base_name(ws[0])
    if any(getattr(w, "opaque", False) for w in ws):
        return None
    if a0 in ("echo", "printf"):
        return " ".join(str(w) for w in ws[1:] if not re.fullmatch(r"-[neE]+", str(w)))
    if a0 == "cat" and seg.bodies and len(ws) == 1:
        return "\n".join(seg.bodies)
    return None


# ---------------------------------------------------------------------------------------------
# Segment inspection
# ---------------------------------------------------------------------------------------------
REMOVE_ITEM = {"remove-item", "ri", "rm", "del", "erase", "rd", "rmdir"}
MOVE_ITEM = {"move-item", "mi", "move", "mv", "rename-item", "rni", "ren"}
PS_WRITERS = {"set-content", "sc", "add-content", "ac", "out-file", "clear-content", "clc",
              "new-item", "ni", "tee-object", "copy-item", "cpi", "copy", "cp", "set-itemproperty"}


def ps_params(argv):
    """PowerShell: ({lowercased param name: value-or-True}, [positional])."""
    params, pos, i = {}, [], 1
    while i < len(argv):
        a = str(argv[i])
        if a.startswith("-") and len(a) > 1 and not re.match(r"-\d", a):
            name, _, val = a[1:].partition(":")
            name = name.lower()
            if val:
                params[name] = val
            elif i + 1 < len(argv) and not str(argv[i + 1]).startswith("-") and \
                    name not in ("recurse", "force", "whatif", "confirm", "r", "rf", "fr", "re", "rec", "fo", "for"):
                params[name] = argv[i + 1]
                i += 1
            else:
                params[name] = True
            i += 1
            continue
        pos.append(argv[i])
        i += 1
    return params, pos


def _pp(params, *prefixes):
    return [v for k, v in params.items() if any(k.startswith(p) for p in prefixes)]


def rule_pwsh_cmdlet(argv, seg, ctx, a0):
    params, pos = ps_params(argv)
    paths = [p for p in _pp(params, "path", "literalpath", "lp", "pspath", "filepath", "fullname")
             if p is not True] + list(pos)
    words = []
    for p in paths:
        for part in str(p).split(","):
            if part:
                words.append(_word(part, getattr(p, "opaque", False)))
    if a0 in REMOVE_ITEM:
        if "whatif" in params:
            return None
        rec = any(k.startswith("r") and "recurse".startswith(k[:7]) or k in ("rf", "fr")
                  for k in params)
        verdict, all_safe = None, True
        for w in words:
            v, safe = judge_delete(w, ctx, rec, "Remove-Item -Recurse" if rec else "Remove-Item")
            if v and v[0] == DENY:
                return v
            verdict, all_safe = worse(verdict, v), all_safe and safe
        if verdict:
            return verdict
        if rec and (not all_safe or not words):
            return (ASK, "Remove-Item -Recurse — permanently removes files.")
        return None
    if a0 in MOVE_ITEM:
        dest = _pp(params, "destination", "newname")
        for w in words[:1] if dest else words[:-1] or words:
            if touches_guard(w, ctx, ancestors=True):
                return (DENY, "Move-Item of a guardrail file or a directory holding one (%s) — it "
                              "moves the guard away." % w)
        for d in (dest or words[1:2]):
            if d is not True:
                v = judge_write(_word(str(d), False), ctx, "Move-Item")
                if v:
                    return v
        return None
    if a0 in PS_WRITERS:
        # the path is -Path/-LiteralPath/-FilePath or the FIRST positional; the rest is -Value
        named = [p for p in _pp(params, "path", "literalpath", "lp", "pspath", "filepath")
                 if p is not True]
        targets = [_word(str(p), False) for p in named] or words[:1]
        if a0 in ("copy-item", "cpi", "copy", "cp"):
            targets = [_word(str(d), False) for d in _pp(params, "destination") if d is not True] or words[1:2]
        verdict = None
        for w in targets:
            verdict = worse(verdict, judge_write(w, ctx, a0))
        return verdict
    return None


def inspect_command(text, shell, ctx, depth=0):
    if depth > MAX_DEPTH:
        return (ASK, "command nested more than %d levels deep ($(…), sh -c, eval) — too deep to "
                     "inspect." % MAX_DEPTH)
    if "${IFS}" in text or "$IFS" in text:
        return (ASK, "shell obfuscation (${IFS} word-splitting) — a string matcher cannot see "
                     "through it.")
    segs = (PwshLexer(text).run() if shell == "pwsh" else lex_bash(text))
    worst, prev = None, None
    for seg in segs:
        worst = worse(worst, inspect_segment(seg, prev, shell, ctx, depth))
        if worst and worst[0] == DENY:
            return worst
        prev = seg
    return worst


def inspect_segment(seg, prev, shell, ctx, depth):
    worst = None
    findings = {"inner": [], "verdicts": []}

    def add(v):
        nonlocal worst
        worst = worse(worst, v)
        return worst is not None and worst[0] == DENY

    # Substitutions RUN. `echo $(rm -rf /)` executes rm; judge the inner command in its own right.
    for sub in seg.subs:
        if add(inspect_command(sub, shell, ctx.child(), depth + 1)):
            return worst

    for op, target in seg.redirs:
        if op in ("<", "<&") or (op in (">&",) and re.fullmatch(r"\d+|-", str(target))):
            continue
        if add(judge_write(target, ctx, "output redirected")):
            return worst

    words = seg.words
    if shell == "bash":
        # for NAME in words: remember the values so `for d in /; do rm -rf $d; done` resolves
        if words and str(words[0]) in ("for", "select") and len(words) >= 2:
            name = str(words[1])
            if "in" in [str(x) for x in words[2:3]]:
                ctx.vars[name] = [str(x) for x in words[3:]] or [""]
            return worst
        if words and str(words[0]) in ENDERS | {"case"}:
            return worst
    argv = strip_wrappers(words, ctx, findings)
    for v in findings["verdicts"]:
        if add(v):
            return worst
    for inner in findings["inner"]:
        if add(inspect_command(inner, "bash", ctx, depth + 1)):
            return worst
    if not argv:
        return worst
    # `echo / | xargs rm -rf`: xargs appends what it reads; when that is literal, it is argv.
    if findings.get("xargs") and seg.piped and prev is not None:
        lt = literal_text(prev)
        if lt:
            argv = list(argv) + [_word(x, False) for x in lt.split()]
    # `find .claude | xargs rm`, `gci .claude -Recurse | Remove-Item`: the targets arrive on the
    # pipe, but the command listing them names the guard.
    if seg.piped and prev is not None:
        sink = base_name(argv[0])
        # `xargs sh -c '…'` is destructive only when its script is: `cat {}` just reads.
        shell_writes = sink in SHELLS and bool(SINK_SCRIPT_RX.search(" ".join(str(x) for x in argv[1:])))
        destructive = (findings.get("xargs") and (sink in PIPE_SINKS or shell_writes)) or (
            shell == "pwsh" and (sink in REMOVE_ITEM or sink in MOVE_ITEM or sink in PS_WRITERS))
        if destructive and _lister_touches_guard(prev, ctx):
            return worse(worst, (DENY, "%s fed a list of the guard's own files — it would "
                                       "rewrite or remove them." % sink))

    # A command NAME that is an expansion. `$(echo rm) -rf /` cannot be judged at all; `$CMD`
    # declared earlier in the same command can — expand it and judge the result.
    if getattr(argv[0], "opaque", False):
        return worse(worst, (ASK, "the command name is built at runtime (%s) — what runs cannot "
                                  "be read before it runs." % str(argv[0])[:40]))
    if "$" in str(argv[0]) and shell == "bash":
        cands = [c for c in expand(argv[0], ctx) if "$" not in c]
        for c in cands[:4]:
            rest = " ".join(_shell_quote(str(x)) for x in argv[1:])
            if add(inspect_command(c + " " + rest, shell, ctx, depth + 1)):
                return worst
        if not cands:
            return worse(worst, (ASK, "the command name is a variable this command never sets "
                                      "(%s) — what runs cannot be read." % str(argv[0])[:40]))
        return worst

    # `{rm,-rf,/}` is brace-expanded into `rm -rf /` before it runs.
    if shell == "bash" and BRACE_RX.search(str(argv[0])):
        words0 = brace_expand(str(argv[0]))
        rest = " ".join(_shell_quote(str(x)) for x in argv[1:])
        return worse(worst, inspect_command(" ".join(_shell_quote(x) for x in words0) + " " + rest,
                                            shell, ctx, depth + 1))

    # `f=-rf; rm $f /`: an option or operand held in a variable set earlier is still that word.
    argv = [argv[0]] + [_resolved(w, ctx) for w in argv[1:]]

    a0 = base_name(argv[0])
    if a0 in ("cd", "pushd", "set-location", "sl", "chdir"):
        # `cd /tmp && rm -rf build` is the commonest scratch cleanup there is; resolving the cd
        # is what keeps it silent. A cd we cannot follow makes relative paths unknown.
        ops = [a for a in argv[1:] if not str(a).startswith("-") or str(a) == "-"]
        if not ops:
            ctx.cd, ctx.lost = norm(_HOME), False
        elif str(ops[0]) == "-" or getattr(ops[0], "opaque", False):
            ctx.cd, ctx.lost = None, True
        else:
            vals = expand(ops[0], ctx)
            if ctx.lost and not is_abs(_slash(vals[0])):
                return worst
            ctx.cd, ctx.lost = norm(vals[0], ctx.base()), False
        return worst
    if a0 in ("export", "local", "declare", "typeset", "readonly") and shell == "bash":
        for a in argv[1:]:
            m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", str(a), re.S)
            if m:
                record_assign(m.group(1), m.group(2), ctx, findings)
        for v in findings["verdicts"]:
            add(v)
        return worst
    if shell == "pwsh" and re.fullmatch(r"\$[A-Za-z_][A-Za-z0-9_]*", str(argv[0])) and \
            len(argv) >= 3 and str(argv[1]) == "=":
        ctx.vars[str(argv[0])[1:]] = [str(argv[2])]
        return worst

    readonly = a0 in READONLY_ARGV0

    # -- shells and interpreters: the program is inside a string, a heredoc or a pipe --------
    if a0 in SHELLS or a0 in PWSH or a0 in ("cmd",):
        if a0 in PWSH:
            kind, script = pwsh_command_arg(argv)
            inner_shell = "pwsh"
        elif a0 == "cmd":
            args = [str(a) for a in argv[1:]]
            low = [a.lower() for a in args]
            kind, script = ("c", " ".join(args[low.index("/c") + 1:])) if "/c" in low else \
                (("c", " ".join(args[low.index("/k") + 1:])) if "/k" in low else ("stdin", None))
            inner_shell = "cmd"
        else:
            kind, script = shell_script_operand(argv)
            inner_shell = "bash"
        if kind == "c":
            if script is None or getattr(script, "opaque", False):
                if add((ASK, "%s -c with a program built at runtime — its text cannot be read "
                             "before it runs." % a0)):
                    return worst
            elif inner_shell == "cmd":
                if add(inspect_cmd_exe(script, ctx)):
                    return worst
            else:
                for code in _expanded_code(script, ctx):
                    if add(inspect_command(code, inner_shell, ctx, depth + 1)):
                        return worst
        elif kind == "opaque":
            add((ASK, "%s with an encoded command that could not be decoded." % a0))
        elif kind == "file" and script is not None and getattr(script, "opaque", False):
            add((ASK, "%s running a script from a substitution — its text is never visible." % a0))
        elif kind == "stdin":
            for body in seg.bodies:
                if add(inspect_command(body, inner_shell if inner_shell != "cmd" else "bash", ctx, depth + 1)):
                    return worst
            for hs in seg.herestrings:
                if add(inspect_command(str(hs), inner_shell if inner_shell != "cmd" else "bash", ctx, depth + 1)):
                    return worst
            if seg.piped and prev is not None:
                if add(judge_pipe_into(prev, a0, inner_shell, ctx, depth)):
                    return worst
    elif a0 == "eval" or a0 == "invoke-expression" or a0 == "iex":
        code = " ".join(str(w) for w in argv[1:])
        if any(getattr(w, "opaque", False) for w in argv[1:]):
            add((ASK, "eval of a string built at runtime — its text cannot be read."))
        else:
            for c in _expanded_code(code, ctx):
                if add(inspect_command(c, shell, ctx, depth + 1)):
                    return worst
    elif a0 in ("source", ".") and len(argv) > 1 and getattr(argv[1], "opaque", False):
        add((ASK, "source of a substitution — the script is never visible."))
    elif a0 in ("su", "runuser"):
        args = [str(a) for a in argv[1:]]
        for i, a in enumerate(args):
            if a in ("-c", "--command") and i + 1 < len(args):
                if add(inspect_command(args[i + 1], "bash", ctx, depth + 1)):
                    return worst
    elif a0 == "ssh":
        args, i = [str(a) for a in argv[1:]], 0
        while i < len(args) and args[i].startswith("-"):
            i += 2 if re.fullmatch(r"-[bcDEeFIiJLlmOopQRSWw]", args[i]) else 1
        remote = " ".join(args[i + 1:])
        if remote and add(inspect_command(remote, "bash", ctx, depth + 1)):
            return worst
    elif INTERPRETERS_RX.match(a0) or a0 in EXECUTORS:
        inline = " ".join(str(w) for w in argv[1:])
        code = inline + "\n" + "\n".join(seg.bodies)
        # A realistic accident: "fixing" .claude/settings.json with a Python one-liner. Program
        # text holding a string literal that IS a guarded path, plus a writing call, earns ask.
        # A heuristic (string-building defeats it), stated as such in SKILL.md. Measured on the
        # sessions that built this kit: matching any MENTION flagged 26 edit scripts whose text
        # merely talked about the guard, so only a whole-literal path counts.
        if GUARDED_MENTION_RX.search(code) and INTERP_WRITE_RX.search(code) and any(
                guarded(norm(m.group(2))) for m in PATH_LITERAL_RX.finditer(code)):
            add((ASK, "inline %s code opens a guardrail file and writes or deletes files — "
                      "a program's writes cannot be judged from its shape." % a0))
        # One-liners (-c/-e, not heredoc programs) that hand a literal to the shell.
        if EXEC_RX.search(inline) and a0 not in EXECUTORS:
            for m in LITERAL_RX.finditer(inline):
                lit = m.group(1) if m.group(1) is not None else m.group(2)
                if " " not in lit.strip():
                    continue
                v = inspect_command(lit, "bash", ctx, MAX_DEPTH)
                if v:
                    add((ASK, "inline %s code hands a destructive command to the shell (%s) — "
                              "%s" % (a0, lit[:60], v[1])))
                    break
        if a0 in EXECUTORS and re.search(r"system\s*\(|\|\s*getline|\bENVIRON\b|print[^;]*\|\s*\"",
                                         code):
            add((ASK, "awk program that runs commands (system(), a pipe to getline) — it is "
                      "executing, not reading."))
        if seg.piped and prev is not None and INTERPRETERS_RX.match(a0) and \
                not any(not str(w).startswith("-") for w in argv[1:]):
            src = strip_wrappers(prev.words, ctx, {"inner": [], "verdicts": []})
            if src and base_name(src[0]) in ("curl", "wget", "fetch", "http", "https", "iwr",
                                             "invoke-webrequest", "irm", "invoke-restmethod"):
                add((ASK, "remote script piped straight into %s — the payload is never seen "
                          "before it runs." % a0))

    # -- file-system writers and deleters ------------------------------------------------------
    rules = []
    if shell == "pwsh" and (a0 in REMOVE_ITEM or a0 in MOVE_ITEM or a0 in PS_WRITERS):
        rules.append(lambda: rule_pwsh_cmdlet(argv, seg, ctx, a0))
    elif a0 in ("rm", "srm", "unlink", "rimraf", "del-cli"):
        rules.append(lambda: rule_rm(argv, seg, ctx, a0) if a0 != "unlink"
                     else rule_writer_operands(argv, seg, ctx, a0))
    elif a0 in ("mv", "cp", "ln", "install", "rsync", "rename"):
        rules.append(lambda: rule_copyish(argv, seg, ctx, a0))
    elif a0 == "dd":
        rules.append(lambda: rule_dd(argv, seg, ctx))
    elif a0 in ("truncate", "shred", "chmod", "chown", "chgrp", "chattr", "setfacl", "tee",
                "vi", "vim", "nvim", "nano", "emacs", "ed", "ex", "patch", "touch", "sponge"):
        if a0 != "touch":
            rules.append(lambda: rule_writer_operands(argv, seg, ctx, a0))
    elif a0 in ("sed", "perl") or (a0 == "ruby" and any(str(x).startswith("-i") for x in argv[1:])):
        rules.append(lambda: rule_inplace(argv, seg, ctx, a0))
    elif a0 == "find":
        rules.append(lambda: rule_find(argv, seg, ctx))
    elif a0 in ("tar", "bsdtar", "gtar", "unzip", "7z", "7za"):
        rules.append(lambda: rule_extract(argv, seg, ctx, a0))
    elif a0 == "git":
        rules.append(lambda: rule_git(argv, seg, ctx))
    elif a0 in ("docker", "docker-compose", "podman", "podman-compose", "nerdctl"):
        rules.append(lambda: rule_docker(argv, seg, ctx, a0))
    if a0 in ("wipefs", "blkdiscard", "shred", "sgdisk", "diskutil") or a0 in DEVICE_TOOLS or \
            a0.startswith("mkfs") or a0.startswith("newfs"):
        rules.append(lambda: rule_device(argv, seg, ctx, a0))
    if a0 in ("esptool", "esptool.py", "espefuse", "espefuse.py", "idf.py", "st-flash",
              "nrfjprog", "nrfutil", "pyocd", "probe-rs"):
        rules.append(lambda: rule_flash(argv, seg, ctx, a0))
    if a0 in ("terraform", "tofu", "terragrunt", "cdktf", "pulumi", "cdk", "serverless", "sls",
              "sam", "helm", "kubectl", "oc"):
        rules.append(lambda: rule_iac(argv, seg, ctx, a0))
    if a0 in CLOUD_CLIS:
        rules.append(lambda: rule_cloud(argv, seg, ctx, a0))
    if a0 in ("npm", "pnpm", "yarn", "bun", "cargo", "twine", "poetry", "flit", "hatch", "pdm",
              "uv", "gem", "dotnet", "nuget", "gh", "vsce", "ovsx"):
        rules.append(lambda: rule_publish(argv, seg, ctx, a0))
    if not readonly:
        rules.append(lambda: rule_db(argv, seg, ctx, a0))
        rules.append(lambda: rule_adopt(argv, seg, ctx))
    for r in rules:
        if add(r()):
            return worst

    # -- SQL through a client that can run it -------------------------------------------------
    clients = ctx.cfg["db_clients"]
    if not readonly and (any(base_name(w) in clients for w in argv) or
                         (a0 == "aws" and "athena" in [str(w).lower() for w in argv])):
        texts = [seg.text] + list(seg.bodies) + [str(h) for h in seg.herestrings]
        if seg.piped and prev is not None:
            lt = literal_text(prev)
            if lt:
                texts.append(lt)
        for t in texts:
            if add(sql_verdict(t)):
                return worst

    # -- adopter rules (careful.json), matched against the segment as written ------------------
    if not readonly:
        for rx in ctx.cfg["extra_deny"]:
            if rx.search(seg.text):
                if add((DENY, "matches an extra_deny rule in careful.json (%s)." % rx.pattern)):
                    return worst
        for rx in ctx.cfg["extra_ask"]:
            if rx.search(seg.text):
                add((ASK, "matches an extra_ask rule in careful.json (%s)." % rx.pattern))
                break
    return worst


PIPE_SINKS = {"rm", "mv", "cp", "truncate", "tee", "sed", "perl", "chmod", "chown", "ln", "dd",
              "shred", "unlink", "rimraf", "install", "rsync", "sponge"}
SINK_SCRIPT_RX = re.compile(r"(?:^|[\s;&|(])(?:rm|mv|cp|truncate|tee|sed\s+-\w*i|perl\s+-\w*i|chmod"
                            r"|chown|ln|dd|shred|unlink|sponge)(?:\s|$)|>")
LISTERS = {"find", "fd", "fdfind", "ls", "git", "get-childitem", "gci", "dir", "get-item", "gi",
           "echo", "printf", "rg", "grep"}


def _lister_touches_guard(prev, ctx):
    src = strip_wrappers(prev.words, ctx.child(), {"inner": [], "verdicts": []})
    if not src or base_name(src[0]) not in LISTERS:
        return False
    for a in src[1:]:
        a = str(a)
        if a.startswith("-") or a in ("ls-files", "ls-tree", "diff", "--"):
            continue
        for part in a.split(","):
            if part and touches_guard(_word(part, False), ctx, ancestors=True):
                return True
    return False


def judge_pipe_into(prev, sink, shell, ctx, depth):
    """Something is piped into a shell. Read it when it is literal; otherwise ask."""
    lt = literal_text(prev)
    if lt is not None:
        return inspect_command(lt, shell, ctx, depth + 1)
    src = strip_wrappers(prev.words, ctx, {"inner": [], "verdicts": []})
    a0 = base_name(src[0]) if src else ""
    if a0 in ("curl", "wget", "fetch", "http", "https", "iwr", "invoke-webrequest", "irm",
              "invoke-restmethod"):
        return (ASK, "remote script piped straight into %s — the payload is never seen before it "
                     "runs." % sink)
    if a0 in ("base64", "openssl", "xxd", "gunzip", "zcat", "base32"):
        return (ASK, "decoded or decompressed data piped into %s — the payload is unreadable "
                     "before it runs." % sink)
    return (ASK, "the output of `%s` piped into %s — the script it runs is never visible." %
            (a0 or "a command", sink))


def inspect_cmd_exe(script, ctx):
    """cmd.exe /c: rd /s and del /s on roots, home and guarded paths. Best-effort."""
    verdict = None
    for part in re.split(r"&&|\|\||[&|]", script):
        toks = [t.strip('"') for t in re.findall(r'"[^"]*"|\S+', part)]
        if not toks:
            continue
        a0 = base_name(toks[0])
        flags = [t.lower() for t in toks[1:] if t.startswith("/")]
        ops = [t for t in toks[1:] if not t.startswith("/")]
        if a0 in ("rd", "rmdir", "del", "erase"):
            rec = "/s" in flags
            for o in ops:
                v, safe = judge_delete(_word(o, False), ctx, rec, "%s /s" % a0 if rec else a0)
                if v and v[0] == DENY:
                    return v
                verdict = worse(verdict, v)
            if rec:
                verdict = worse(verdict, (ASK, "%s /s — deletes a directory tree." % a0))
    return verdict


# ---------------------------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------------------------
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "StrReplace", "ApplyPatch"}
SHELL_TOOLS = {"Bash": "bash", "PowerShell": "pwsh"}


def payload_paths(tool_input):
    out = []
    for key in ("file_path", "notebook_path", "path"):
        v = tool_input.get(key)
        if isinstance(v, str):
            out.append(v)
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for e in edits:
            if isinstance(e, dict) and isinstance(e.get("file_path"), str):
                out.append(e["file_path"])
    return out


def decide(payload, cfg=None, cfg_error=None):
    """Return (decision, reason) with decision in allow | ask | deny."""
    if cfg is None:
        cfg, cfg_error = load_config()
    if not isinstance(payload, dict):
        return ASK, "unexpected tool payload shape — asking instead of allowing."
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return "allow", None
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None
    try:
        cwd = norm(cwd or os.getcwd())
    except Exception:
        cwd = None
    proj = os.environ.get("CLAUDE_PROJECT_DIR")
    scratch_extra = ()
    if isinstance(payload.get("scratchpad_dir"), str) and payload["scratchpad_dir"]:
        scratch_extra = (fold(norm(payload["scratchpad_dir"])).rstrip("/") + "/",)
    ctx = Ctx(cfg, cwd, norm(proj) if proj else None, scratch_extra)

    if tool in WRITE_TOOLS:
        verdict = None
        for p in payload_paths(tool_input):
            ab = norm(p, cwd) if cwd else norm(p)
            for q in (norm(p), ab, _realpath(ab) if is_abs(ab) else ab):
                if guarded(q) and new_gate_file(q, ab):
                    verdict = (ASK, "new gate script (%s) — review it; once it exists it is "
                                    "guarded like the rest of the chain." % p)
                    break
                if guarded(q):
                    return DENY, ("edit to a guardrail file (%s) — changing it disables the "
                                  "protection itself. Have a human make this edit." % p)
            for q in (norm(p), norm(p, cwd) if cwd else norm(p)):
                why = gate_wiring(q)
                if why:
                    verdict = (ASK, "edit to %s; a human should see the change." % why)
        return verdict or ("allow", None)

    # Bash and PowerShell carry `command`. Any other tool routed here with a string `command`
    # is read as a POSIX shell command: an adopter who adds a command-running tool to the
    # matcher gets inspection rather than a silent pass.
    cmd = tool_input.get("command", "")
    if not isinstance(cmd, str) or not cmd.strip():
        return "allow", None
    shell = SHELL_TOOLS.get(tool, "bash")

    oversize = len(cmd) > MAX_INSPECT
    verdict = inspect_command(cmd[:MAX_INSPECT] if oversize else cmd, shell, ctx)
    if oversize and not (verdict and verdict[0] == DENY):
        return ASK, ("command is %d characters; only the first %d were inspected. Too large to "
                     "judge in full — asking instead of allowing." % (len(cmd), MAX_INSPECT))
    if verdict is None:
        if cfg_error:
            return ASK, ("%s — its extra rules are not being applied. Fix .claude/hooks/"
                         "careful.json (a human edit; run check-careful.py --check-config)." %
                         cfg_error)
        return "allow", None
    return verdict


def emit(decision, reason=None):
    """allow == print {} (no decision, normal permission flow).

    Never print permissionDecision "allow": that AUTO-APPROVES the tool and would turn this
    guard into a blanket bypass for every command it does not recognise.
    """
    if decision == "allow":
        out = "{}"
    else:
        if decision == DENY and os.environ.get("CAREFUL_ALLOW_HIGH") == "1":
            decision, reason = ASK, reason + " [CAREFUL_ALLOW_HIGH=1 — downgraded to ask]"
        out = json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": "[careful] " + reason,
        }})
    sys.stdout.write(out + "\n")
    sys.stdout.flush()


def _deadline(signum, frame):
    # Answer before the host's timeout does: a hook killed at its timeout does not block.
    emit(ASK, "inspection ran out of its %d s budget — asking instead of letting the host's "
              "timeout pass the command silently." % DEADLINE_S)
    os._exit(0)


def main(argv):
    try:                                   # a cp1252 console must not crash a message (F8)
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(argv) > 1 and argv[1] == "--check-config":
        path = argv[2] if len(argv) > 2 else CONFIG_PATH
        cfg, err = load_config(path)
        if err:
            print("careful.json INVALID: %s" % err)
            return 1
        print("careful.json OK (%s): %d protected branch patterns, %d db clients, %d safe dirs, "
              "%d extra_ask, %d extra_deny" % (
                  path if os.path.exists(path) else "absent, defaults only",
                  len(cfg["protected_branches"]), len(cfg["db_clients"]), len(cfg["safe_dirs"]),
                  len(cfg["extra_ask"]), len(cfg["extra_deny"])))
        return 0
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _deadline)
        signal.alarm(DEADLINE_S)
    raw = sys.stdin.buffer.read()
    if not raw.strip():
        emit("allow")
        return 0
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace"))
    except Exception:
        emit(ASK, "could not parse the tool payload, so the command could not be checked. "
                  "Asking instead of allowing.")
        return 0
    try:
        decision, reason = decide(payload)
    except RecursionError:
        decision, reason = ASK, "command nested too deeply to inspect — asking instead of allowing."
    except Exception as exc:
        decision, reason = ASK, ("the matcher failed on this command (%s: %s) — asking instead "
                                 "of allowing." % (type(exc).__name__, exc))
    emit(decision, reason)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
