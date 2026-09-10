#!/usr/bin/env python3
"""Destructive-command matcher for the careful pre-execution guardrail.

Reference implementation for the AI Factory Kit; the classes are portable, the individual
patterns are examples — extend the table for your stack.

Reads the tool-call JSON on stdin, prints a PreToolUse hook decision on stdout.

THE ENVELOPE IS LOAD-BEARING. Claude Code reads a PreToolUse decision only from
hookSpecificOutput.{hookEventName,permissionDecision,permissionDecisionReason}. A
top-level "permissionDecision" is not a field it knows, so it is dropped and the tool
runs. The previous version of this guard printed exactly that shape and was therefore
inert from 2026-06-25 to 2026-09-10 while its own test stayed green — the test read the
script's stdout and never asked whether Claude Code honoured it. Upstream gstack hit the
same bug (CHANGELOG 1.64.0.0: "deny meant allow"). Do not "simplify" the envelope.

HOW STRONG "ask" IS DEPENDS ON THE SURFACE — do not generalise from one measurement.
Measured on the source factory: with the host in a skip-permissions mode, a hook "ask" was
auto-approved on the desktop/terminal surface and DID raise a real dialog on mobile/remote
control. So deny is a wall everywhere; ask is a wall wherever a human is actually looking. Treat an escape from deny into ask as a real hole, not a
cosmetic one — that is the standard the 2026-09-10 adversarial audit applied, and it
found six. Their fixes are marked AUDIT below; the escape families they name are pinned
in check-careful.test.sh so a later rewrite cannot quietly reopen them.

Two tiers:
  ask  — destructive but recoverable. Human confirms (where a human is watching).
  deny — catastrophic and unrecoverable: recursive delete of / ~ $HOME, force-push or
         branch-delete against a protected branch. --force-with-lease never denies.

Escape hatch: CAREFUL_ALLOW_HIGH=1 downgrades deny to ask. Needed because this hook
is always-on in settings.json (gstack's is session-scoped, so ending /careful was theirs).

Fail polarity, deliberately asymmetric:
  unreadable payload   -> ask   (something was there and we could not read it)
  no command field     -> allow (nothing to inspect; never wedge non-Bash tools)
"""
import json
import os
import re
import shlex
import subprocess
import sys

PROTECTED_BRANCHES = {"main", "master"}

# Something in the command must be able to EXECUTE SQL before SQL-shaped text means anything.
# Listing the client by name also covers `docker exec <container> mysql -e "..."`.
DB_CLIENTS = {"mysql", "mariadb", "psql", "sqlite3", "sqlite", "mongo", "mongosh",
              "clickhouse-client", "cockroach", "sqlcmd", "mysqladmin", "pg_dump", "usql"}

# AUDIT: was a bare set of literals, so `rm -rf ~/*` and `rm -rf $HOME/*` — the ordinary
# way to empty a home directory — scored only "ask". Roots are now normalized and expanded
# into their equivalent spellings.
_HOME = os.path.expanduser("~")
_ROOT_SEEDS = {"/", "~", "$HOME", "${HOME}", _HOME, "~" + os.path.basename(_HOME)}


def _root_variants(seed):
    # rstrip first: for seed "/" a naive seed+"/*" yields "//*", so `rm -rf /*` — the
    # canonical "empty the filesystem" spelling — missed the set entirely.
    base = seed.rstrip("/")
    yield seed
    for suffix in ("/", "/*", "/.", "/..", "/.*"):
        yield base + suffix


ROOT_TARGETS = {v for s in _ROOT_SEEDS for v in _root_variants(s)}


def normalize_target(t):
    """Collapse //, drop a trailing slash, so /// and /  and //. land on one key."""
    t = re.sub(r"/{2,}", "/", t)
    if len(t) > 1 and t.endswith("/") and not t.endswith("/*"):
        t = t.rstrip("/") or "/"
    return t


# Wrappers that put the real command later in argv. AUDIT: argv[0] was read straight off
# token 0, so `sudo rm -rf /` and `FOO=1 rm -rf /` returned {} — allowed, silently, with no
# reason in the transcript. That is quieter than the auto-approved ask it bypassed.
WRAPPERS = {"sudo", "doas", "env", "command", "builtin", "exec", "nohup", "time", "nice",
            "ionice", "stdbuf", "setsid", "timeout", "xargs", "proxychains", "script"}
# Wrapper flags that consume the next token as their operand.
WRAPPER_OPT_WITH_ARG = {"-u", "-g", "-C", "-U", "--user", "--group", "--chdir"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish"}

# git's own global options that take a separate operand; leaving the operand in place made
# it masquerade as the subcommand, so `git -C /repo push -f origin main` read as sub="/repo".
GIT_GLOBAL_OPT_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

# argv[0] of a segment that only reads or prints text: it cannot destroy anything, so a
# destructive-looking STRING inside its arguments is talk, not action.
#   grep -rn "migrate down" docs/   ·   echo "rm -rf / is dangerous"
#
# MEMBERSHIP IS A SAFETY CLAIM, NOT A CONVENIENCE. A segment whose argv[0] is in here skips
# EVERY check below, so anything that can write must stay out — `tee` writes files, `sed -i`
# edits in place, `find -delete`/`-exec` removes. Before adding a name, ask what it does
# with a `>` or an `-i`, not what it usually does.
READONLY_ARGV0 = {
    "echo", "printf", "grep", "rg", "egrep", "fgrep", "cat", "bat", "less", "more",
    "head", "tail", "awk", "ls", "wc", "sort", "uniq", "diff", "man",
    "which", "type", "file", "stat", "jq", "yq", "column",
}
# ...and even then, only while the invocation stays read-only. AUDIT: `awk 'BEGIN{system("rm -rf /")}'`
# rode the skip list. Matched against the tool's own ARGV, never the raw segment text —
# `grep -rn "sed -i" docs/` mentions a flag, it does not use one.
# Deliberately carries NO flag names. The first draft listed `-i` to catch `sed -i`, and so
# flagged `grep -i` — case-insensitive search, the most common flag in the shell. Measured over
# 48h of real commands: 594 of 802 interruptions came from that single entry. sed, find and tee
# are not in READONLY_ARGV0 and each has its own branch below, so their flags were never needed
# here. What remains is what a genuinely read-only tool can still do: execute, or redirect.
EXECUTORS = {"awk", "gawk", "mawk", "nawk"}  # these can spawn a shell from their program text


def is_writeful(tokens, segment):
    if argv0(tokens) in EXECUTORS:
        joined = " ".join(tokens[1:]).replace(" ", "")
        if "system(" in joined or "ENVIRON" in joined or "|getline" in joined:
            return True
    return bool(REDIRECT_OVER_REAL_PATH.search(segment))

# Throwaway build/dependency dirs. RELATIVE PATHS ONLY — an absolute path can never ride
# this list. (The old list carried "bin" and "tmp" as */bin|*/tmp globs, which swallowed
# `rm -rf /usr/bin` and `rm -rf /tmp`. They are gone; do not add a bare dir name whose
# absolute twin matters.)
SAFE_DIR = r"(?:\./)?(?:[\w.@+-]+/)*(?:node_modules|\.next|dist|build|__pycache__|\.cache|\.turbo|coverage)/?"
# AUDIT: matched per TOKEN, not over the whole command. The old whole-command form
# `(?:SAFE_DIR\s*)+` backtracked exponentially — 26 repeated segments took 17s against a
# 10s hook timeout, and that same string carried `/` as an rm target. Per-token is linear
# and keeps the anchoring lesson: a token must be a safe dir ENTIRELY, and `..` is refused
# so `node_modules/../../..` cannot climb out.
SAFE_ONE = re.compile(r"\A" + SAFE_DIR + r"\Z")

# A heredoc body is DATA handed to a program on stdin, not shell syntax. Scanning it caused
# a real false positive: a command whose heredoc merely CONTAINED redirect-shaped text
# naming a guardrail file was refused as if it were performing that redirect — the same
# "mentioning a flag is not using it" error as grep -rn "sed -i". It was hit while writing
# this very fix, which is the tidiest proof it was real.
# LIMIT, stated rather than hidden: stripping the body also means a program run FROM a
# heredoc (python3 - <<PY ... PY) is not inspected. This matcher judges command shapes, not
# program semantics; an interpreter handed a script can still write any file. The Write/Edit
# denial raises the bar and makes the ordinary path loud, it does not seal the box.
# The body starts on the NEXT line — everything after the tag on the same line is still
# command line, and that is exactly where a redirect lives (`cat <<EOF >file`). Keep it.
HEREDOC = re.compile(
    r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1(?P<rest>[^\n]*)\n"
    r"(?P<body>.*?)^\s*\2\s*$",
    re.S | re.M)


def strip_heredocs(cmd):
    return HEREDOC.sub(lambda m: "<<" + m.group(2) + m.group("rest") + "\n", cmd)


SEGMENT_SPLIT = re.compile(r"&&|\|\||[;&|\n]")
# AUDIT: `simple` used to be computed over the WHOLE command, so appending `; true` to
# anything downgraded deny to ask. Only genuine opacity — a substitution whose expansion we
# cannot see — justifies backing off, and it is judged per segment.
OPAQUE = re.compile(r"\$\(|`|\$\{[^}]*\[")

# Redirection over a path that is not scratch. AUDIT: the guard could be erased by one
# allowed Bash command (`echo '' > .claude/hooks/check-careful.py`) with no Write tool and
# no prompt — a self-disabling primitive.
# A dot-entry sitting directly in $HOME is configuration (.zshrc, .ssh, .gitconfig):
# overwriting one changes what later sessions do, silently. Anything else under $HOME
# is ordinary work.
# ...but .claude/projects/ holds session memory and notes, which are written constantly.
HOME_DOTFILE = re.compile(
    r"(?:~|\$\{?HOME\}?|" + re.escape(os.path.expanduser("~"))
    + r")/\.(?!claude/projects/)[A-Za-z]")

REDIRECT_OVER_REAL_PATH = re.compile(
    r">>?\s*(?:/(?!tmp/|dev/null|dev/stderr|dev/stdout)\S+|~/\S+|\$\{?HOME\}?/\S+|\S*\.claude/\S+)")

# Text-level patterns. These live inside quoted arguments (`mysql -e "DROP TABLE t"`), so
# argv analysis cannot see them — they must stay whole-segment regexes.
TEXT_RULES = [
    (re.compile(r"drop\s+(table|database|schema)", re.I),
     "SQL DROP — permanently deletes database objects."),
    (re.compile(r"\btruncate\b", re.I),
     "SQL TRUNCATE — deletes all rows from a table."),
]

OBFUSCATION = [
    (re.compile(r"\$\{IFS\}|\$IFS"),
     "shell obfuscation (${IFS} word-splitting) — a string matcher cannot see through it."),
    (re.compile(r"base64\s+(-{1,2}[a-zA-Z-]*\s+)*(-d|--decode)\b[^\n]*\|\s*(sh|bash|zsh)\b"),
     "base64-decoded script piped to a shell — the payload is unreadable before it runs."),
    (re.compile(r"\b(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(sh|bash|zsh)\b"),
     "remote script piped straight into a shell — the payload is never seen before it runs."),
]


# Files whose whole purpose is to stop the agent. Editing one turns the guard off, so they
# are the one path set this hook denies on the Write/Edit side too.
#
# WHY THIS EXISTS: the Bash matcher below can be erased by editing it, and the hook itself can
# be unregistered by editing settings.json (or neutered wholesale with disableAllHooks). Until
# 2026-09-10 nothing watched Write/Edit at all, so a guard that refused `rm -rf /` could be
# deleted by a single Edit call that no gate saw — the audit filed this as the standing
# THEORETICAL bypass and it was real.
# Lookbehind, not (?:^|/): the Bash side matches against redirect text like
# `> .claude/hooks/x.py`, where the dot follows a space. `[\w.-]` still blocks a false hit
# on something like `myapp.claude/`.
GUARDED_PATH = re.compile(
    r"(?<![\w.-])\.claude/(?:hooks/|settings(?:\.local)?\.json\b)"
    r"|(?<![\w.-])\.specify/scripts/"
)


# Only tools that MUTATE a file. Reading a guardrail is harmless — and denying the read
# would break the ordinary "look at what the guard does" step.
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "StrReplace", "ApplyPatch"}


def guarded_paths(tool_input):
    """Every path a Write/Edit-family payload would touch."""
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
    return [p for p in out if GUARDED_PATH.search(p)]


def emit(decision, reason=None):
    """allow == print {} (no decision, normal permission flow).

    Never print permissionDecision:"allow" — that AUTO-APPROVES the tool and would turn
    this guard into a blanket bypass for every command it does not recognise.
    """
    if decision == "allow":
        print("{}")
    else:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": "[careful] " + reason,
        }}))
    sys.exit(0)


def tokens_of(segment):
    try:
        # comments=True so `rm -rf / # cleanup` does not smuggle "cleanup" in as a target.
        return shlex.split(segment, comments=True)
    except ValueError:
        return segment.split()


def strip_wrappers(tokens):
    """Drop env assignments and command wrappers so argv[0] is the real command."""
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", t):      # FOO=1 rm -rf /
            i += 1
            continue
        if os.path.basename(t).lstrip("\\") in WRAPPERS:        # sudo / env / timeout ...
            i += 1
            while i < len(tokens) and tokens[i].startswith("-"):
                if tokens[i] in WRAPPER_OPT_WITH_ARG:
                    i += 1
                i += 1
            # `timeout 60 rm -rf /` — a bare numeric operand belongs to the wrapper.
            if i < len(tokens) and re.fullmatch(r"\d+(\.\d+)?[smhd]?", tokens[i]):
                i += 1
            continue
        break
    return tokens[i:]


def argv0(tokens):
    return os.path.basename(tokens[0]).lstrip("\\") if tokens else ""


def split_flags(tokens):
    return ([t for t in tokens[1:] if t.startswith("-")],
            [t for t in tokens[1:] if not t.startswith("-")])


def is_recursive(opts):
    for o in opts:
        if o == "--recursive":
            return True
        if not o.startswith("--") and ("r" in o[1:] or "R" in o[1:]):
            return True
    return False


# Scratch roots. Deleting INSIDE one is ordinary housekeeping; deleting the root itself is
# not, and is still asked about.
#
# WHY: removing the old `bin`/`tmp` allowlist entries was right — they were written as the
# globs `*/bin`/`*/tmp` and swallowed `rm -rf /usr/bin` and `rm -rf /tmp`. But it left every
# `rm -rf /tmp/<scratch>` asking, and on a surface where a hook's `ask` really does prompt
# (mobile / remote control) that is a confirmation dialog on routine cleanup, several times a
# session. A guard that cries wolf on housekeeping gets switched off, and then guards nothing.
SCRATCH_ROOTS = tuple(r for r in (
    "/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/",
    (os.environ.get("TMPDIR") or "").rstrip("/") + "/" if os.environ.get("TMPDIR") else "",
) if r and r != "/")


def in_scratch(t):
    """True for a path strictly INSIDE a temp root, with no way to climb out of it."""
    t = normalize_target(t)
    for root in SCRATCH_ROOTS:
        if t.startswith(root) and len(t) > len(root):
            return ".." not in t.split("/")
    return False


def safe_target(t):
    return bool(SAFE_ONE.match(t)) and ".." not in t.split("/")


def current_branch():
    try:
        return subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                              capture_output=True, text=True, timeout=2).stdout.strip()
    except Exception:
        return ""


def push_destination(args):
    """Branch a `git push` would overwrite or delete.

    `args` is everything after the `push` word, with flags removed: [remote, refspec...].
    The destination is the refspec's right-hand side (`HEAD:main` -> main, `+main` -> main,
    `:main` -> main, the delete form). With no refspec, or a symbolic one, the current
    branch is the destination.
    """
    dest = None
    for spec in args[1:]:
        spec = spec.lstrip("+")
        dest = spec.split(":")[-1] if ":" in spec else spec
        dest = dest.replace("refs/heads/", "")
        break
    # AUDIT: `git push -f origin HEAD` never resolved, so it scored ask on a repo whose
    # HEAD is main. An unresolvable destination is a reason to stop, not to relax.
    if dest in (None, "", "HEAD", "@"):
        dest = current_branch() or "?unknown"
    return dest


def inspect_git(tokens, opts, targets):
    if not targets:
        return None
    sub = targets[0]

    if sub == "push":
        lease = any(t.startswith("--force-with-lease") for t in tokens)
        flag_forced = any(
            t in ("--force", "-f") or
            (not t.startswith("--") and t.startswith("-") and "f" in t[1:])
            for t in tokens)
        args = targets[1:]  # everything after the `push` word: [remote, refspec...]
        plus_forced = any(t.startswith("+") and len(t) > 1 for t in args)
        # AUDIT: deleting a remote branch needs no force at all, and was fully allowed.
        deleting = (any(t in ("--delete", "-d") for t in tokens)
                    or any(a.startswith(":") for a in args))
        mirror = "--mirror" in tokens
        if mirror:
            return ("deny", "git push --mirror — deletes every remote ref that is missing "
                            "locally. Push the branch you mean by name instead.")
        if not (lease or flag_forced or plus_forced or deleting):
            return None
        if lease:
            return ("ask", "git push --force-with-lease — still rewrites remote history, "
                           "but refuses if the remote moved.")
        dest = push_destination(args)
        if deleting:
            if dest in PROTECTED_BRANCHES:
                return ("deny", "deleting the protected remote branch '%s' — this removes "
                                "shared history from the remote." % dest)
            return ("ask", "git push --delete — removes a branch from the remote.")
        if dest in PROTECTED_BRANCHES or dest == "?unknown":
            return ("deny", "force-push to the protected branch '%s' — rewrites shared "
                            "history irreversibly. Push without --force, or use "
                            "--force-with-lease." % dest)
        return ("ask", "git force-push — rewrites remote history; collaborators may lose work.")

    if sub == "worktree" and len(targets) > 1 and targets[1] == "remove":
        if any(t in ("--force", "-f") for t in tokens):
            return ("ask", "git worktree remove --force — deletes a worktree that still has "
                           "modified or untracked files; they exist nowhere else.")
        return None

    if sub == "reset" and "--hard" in opts:
        return ("ask", "git reset --hard — discards all uncommitted changes.")

    if sub in ("checkout", "restore") and "." in targets[1:]:
        return ("ask", "git checkout/restore . — discards all uncommitted working-tree changes.")

    # AUDIT: the family below was missed entirely, and it is the family that destroys the
    # recovery net every other mistake relies on.
    if sub == "clean" and any(not o.startswith("--") and "f" in o[1:] for o in opts):
        return ("ask", "git clean -f — deletes untracked files; they were never committed, "
                       "so nothing can bring them back.")
    if sub == "branch" and "-D" in opts:
        return ("ask", "git branch -D — force-deletes a branch, unmerged commits included.")
    if sub == "reflog" and "expire" in targets[1:]:
        return ("ask", "git reflog expire — discards the reflog, the last route back to a "
                       "lost commit.")
    if sub == "gc" and any(t.startswith("--prune") for t in tokens):
        return ("ask", "git gc --prune — drops unreachable objects for good.")
    if sub == "stash" and "clear" in targets[1:]:
        return ("ask", "git stash clear — deletes every stash entry.")
    if sub == "filter-branch":
        return ("ask", "git filter-branch — rewrites history across the repository.")

    return None


def command_context(cmd):
    """(vars, cwd) declared earlier in the same command line.

    `cd /tmp && rm -rf build` and `H=/tmp/bk; rm -rf "$H"` are the two commonest scratch
    cleanups in practice, and a matcher that reads one segment at a time sees a bare relative
    name or an unexpanded $H and has to ask. Measured over 48h of real commands, those two
    shapes were 76 of the 122 remaining interruptions.
    """
    variables, cwd = {}, None
    for seg in SEGMENT_SPLIT.split(cmd):
        seg = seg.strip()
        if not seg:
            continue
        for m in re.finditer(r"(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)=([^\s;&|]+)", seg):
            variables[m.group(1)] = m.group(2).strip("\"'")
        t = tokens_of(seg)
        if t and argv0(t) == "cd" and len(t) > 1 and not t[1].startswith("-"):
            cwd = t[1]
    return variables, cwd


def expand(t, variables):
    def sub(m):
        return variables.get(m.group(1) or m.group(2), m.group(0))
    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)", sub, t)


def inspect_segment(segment, decisive, depth=0, ctx=(None, None)):
    tokens = strip_wrappers(tokens_of(segment))
    a0 = argv0(tokens)

    # `bash -c "rm -rf /"` hides the real command inside a quoted string.
    if depth < 2 and a0 in SHELLS and "-c" in tokens:
        i = tokens.index("-c")
        if i + 1 < len(tokens):
            inner = inspect_segment(tokens[i + 1], decisive, depth + 1, ctx)
            if inner:
                return inner

    if a0 in READONLY_ARGV0:
        if not is_writeful(tokens, segment):
            return None
        # A read-only tool invoked in a way that writes or executes is no longer read-only,
        # and nothing further down knows how to judge it — so say so rather than fall
        # through to allow. AUDIT: awk 'BEGIN{system("rm -rf /")}' passed this gate and
        # then matched no rule at all.
        if not REDIRECT_OVER_REAL_PATH.search(segment):
            return ("ask", "a read-only tool (%s) invoked with an in-place, delete, exec, "
                           "system() or redirect form — it is writing, not reading." % a0)

    # Writing a file IS the work. The first draft asked about any redirect onto an absolute or
    # home path, which made 89 of 802 interruptions in 48h out of `cat > ~/notes.md` and its
    # relatives. Only two targets are worth stopping for.
    m = REDIRECT_OVER_REAL_PATH.search(segment)
    if m:
        if GUARDED_PATH.search(m.group(0)):
            return ("deny", "output redirected over a guardrail file — this would disable the "
                            "very check reading this command.")
        if HOME_DOTFILE.search(m.group(0)):
            return ("ask", "output redirected over a config dot-entry in $HOME — it changes how "
                           "later sessions behave, quietly.")

    # Without the client check, the word "Update" inside a grep pattern, or a path such as
    # specs/029-audit-log/, tripped the DELETE/UPDATE rule.
    if any(os.path.basename(t) in DB_CLIENTS for t in tokens):
        for rx, reason in TEXT_RULES:
            if rx.search(segment):
                return ("ask", reason)
        low = segment.lower()
        if re.search(r"\b(delete\s+from|update)\b", low) and not re.search(r"\bwhere\b", low):
            return ("ask", "SQL DELETE/UPDATE without WHERE — affects every row in the table.")

    if a0 == "rm":
        opts, targets = split_flags(tokens)
        targets = [t for t in targets if t != "--"]
        if not is_recursive(opts):
            return None
        # expand BEFORE the root check as well: `R=/ ; rm -rf "$R"` must still be caught
        targets = [expand(t, (ctx[0] or {})) for t in targets]
        # AUDIT: this was `all(...)`, so `rm -rf / /home` — strictly worse than `rm -rf /` —
        # was downgraded to ask by ADDING a target. Any root target is catastrophic.
        if any(normalize_target(t) in ROOT_TARGETS for t in targets):
            if decisive:
                return ("deny", "recursive delete of %s — this erases the machine or the whole "
                                "home directory. There is no undo." % " ".join(targets))
            return ("ask", "recursive delete of a root/home path, inside a command whose "
                           "expansion cannot be read.")
        variables, cwd = ctx
        resolved = [expand(t, variables or {}) for t in targets]
        # A relative target is scratch only when the command itself cd'd into a scratch dir.
        if cwd and in_scratch(cwd.rstrip("/") + "/x"):
            resolved = [t if t.startswith(("/", "~", "$")) else cwd.rstrip("/") + "/" + t
                        for t in resolved]
        if resolved and all(safe_target(t) or in_scratch(t) for t in resolved):
            return None
        return ("ask", "recursive delete (rm -r) — permanently removes files.")

    if a0 == "find":
        if "-delete" in tokens:
            return ("ask", "find -delete — removes every file the traversal matches; the match "
                           "set is not visible before it runs.")
        if re.search(r"-exec(dir)?\s+(/usr/bin/|/bin/)?rm\b", segment):
            return ("ask", "find -exec rm — removes every file the traversal matches.")
        return None

    if a0 == "sed":
        opts, _ = split_flags(tokens)
        if any(o == "-i" or o == "--in-place" or o.startswith("--in-place=")
               or (not o.startswith("--") and "i" in o[1:]) for o in opts):
            return ("ask", "sed -i — rewrites files in place, with no backup unless a suffix "
                           "was given.")
        return None

    if a0 == "tee":
        return ("ask", "tee — writes its input to the named files, overwriting them unless -a "
                       "was given.")

    if a0 == "git":
        # AUDIT: git's own -C/-c/--git-dir operands used to survive split_flags and be read
        # as the subcommand, so `git -C /repo push -f origin main` inspected nothing.
        rest = tokens[1:]
        while rest and rest[0].startswith("-"):
            rest = rest[2:] if rest[0] in GIT_GLOBAL_OPT_WITH_ARG else rest[1:]
        tokens = tokens[:1] + rest
        opts, targets = split_flags(tokens)
        verdict = inspect_git(tokens, opts, targets)
        if verdict and verdict[0] == "deny" and not decisive:
            return ("ask", verdict[1])
        return verdict

    if a0 == "migrate" or (a0 in ("go", "make", "task", "just") and "migrate" in segment):
        if re.search(r"\b(down|force|drop)\b", segment):
            return ("ask", "migration down/force/drop — can roll a schema past a "
                           "destructive step (data loss).")

    if a0 in ("docker", "docker-compose", "podman"):
        if re.search(r"(compose\s+)?down\b[^\n]*(-v\b|--volumes\b)", segment):
            return ("ask", "docker compose down -v — destroys the persistent data volumes.")
        if re.search(r"\bvolume\s+rm\b", segment):
            return ("ask", "docker volume rm — destroys a persistent data volume.")
        if re.search(r"\brm\s+-[a-zA-Z]*f|\bsystem\s+prune\b", segment):
            return ("ask", "docker force-remove / prune — may delete running containers or "
                           "cached images.")

    if a0 == "kubectl" and "delete" in split_flags(tokens)[1]:
        return ("ask", "kubectl delete — removes cluster resources; may impact production.")

    if a0 == "mysqladmin" and "drop" in split_flags(tokens)[1]:
        return ("ask", "mysqladmin drop — deletes an entire database.")

    return None


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        emit("allow")

    try:
        payload = json.loads(raw)
    except Exception:
        emit("ask", "could not parse the tool payload, so the command could not be checked. "
                    "Asking instead of allowing.")
    if not isinstance(payload, dict):
        emit("ask", "unexpected tool payload shape — asking instead of allowing.")

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        emit("allow")

    # Write/Edit/MultiEdit/NotebookEdit carry a path, not a command.
    hit = guarded_paths(tool_input) if payload.get("tool_name") in WRITE_TOOLS else []
    if hit:
        decision = "deny"
        if os.environ.get("CAREFUL_ALLOW_HIGH") == "1":
            decision = "ask"
        emit(decision, "edit to a guardrail file (%s) — changing it disables the protection "
                       "itself. Have a human make this edit, or set CAREFUL_ALLOW_HIGH=1 "
                       "for the session." % ", ".join(hit))

    cmd = tool_input.get("command", "")
    if not isinstance(cmd, str) or not cmd.strip():
        emit("allow")

    cmd = strip_heredocs(cmd)

    for rx, reason in OBFUSCATION:
        if rx.search(cmd):
            emit("ask", reason)

    ctx = command_context(cmd)
    worst = None  # ("deny"|"ask", reason); deny outranks ask
    for segment in SEGMENT_SPLIT.split(cmd):
        if not segment.strip():
            continue
        # Decisiveness is per SEGMENT and only opacity forfeits it — appending `; true`
        # must never soften a verdict.
        verdict = inspect_segment(segment.strip(), not OPAQUE.search(segment), ctx=ctx)
        if verdict is None:
            continue
        if verdict[0] == "deny":
            worst = verdict
            break
        if worst is None:
            worst = verdict

    if worst is None:
        emit("allow")
    decision, reason = worst
    if decision == "deny" and os.environ.get("CAREFUL_ALLOW_HIGH") == "1":
        emit("ask", reason + " [CAREFUL_ALLOW_HIGH=1 — downgraded to ask]")
    emit(decision, reason)


if __name__ == "__main__":
    main()
