#!/usr/bin/env python3
"""Install the AI Factory Kit into a project, keep it current, and prove the result.

Run from the project root, with the kit vendored inside the project (a git submodule or a
plain copy; the directory name is yours, factory/ is the convention):

    python3 factory/bin/adopt.py [--profile P] [--without RULES]      install or merge
    python3 factory/bin/adopt.py --upgrade                            after updating factory/
    python3 factory/bin/adopt.py --check                              audit, writes nothing
    python3 factory/bin/adopt.py --register-guard                     wire the careful hook
    python3 factory/bin/adopt.py --install-git-hook --ci github       feature 001 does this

Every run is idempotent and never overwrites a file that differs from what the kit would
write: it leaves <file>.factory-new next to it and lists it for review. settings*.json (except
through --register-guard) and Spec Kit's skills/speckit-* are never touched.

What each earlier version of this step got wrong, and what paid for the lesson:

  - The hand-run copy-and-sed recipe (before v1.3.0) sed-ed a file that did not exist yet,
    matched only `../../` so depth-3 links were mangled and depth-1 links never rewritten
    (20 of 82 dead), and used BSD-only `sed -i ''`. Links are now rewritten generically:
    each is resolved against the file's SOURCE location in the kit, mapped to where that
    target is installed (or to the vendored kit copy), then made relative to the file's
    DESTINATION. No depth arithmetic, so no depth can be wrong.
  - v1.3.x refused any existing .claude/: a Spec Kit project, or anyone who had once clicked
    "don't ask again" (which writes .claude/settings.local.json), could not adopt, and there
    was no upgrade path at all. A v1.2.0 adopter who followed "git pull" kept a guard that
    blocked nothing, because the pull never reached the copies in .claude/. Now: per-file
    merge, a manifest of what was installed, and --upgrade.
  - v1.3.x copied the guard's hooks twice. The registered copy in .claude/hooks/ was
    edit-denied; the unregistered copy under skills/careful/hooks/ was editable and its test
    went green, so an AI adapting the guard changed nothing live. There is one copy now.
  - Agents and rules shipped with an HTML comment at byte 0. Claude Code treated all four
    agents as documentation and loaded every rule unconditionally. The frontmatter position
    is now asserted before anything is written.
  - A CRLF checkout (core.autocrlf=true) turned the hook shim into a script bash cannot
    parse; a PreToolUse hook that exits 2 blocks every tool call. Text is normalised to LF,
    scripts are asserted CR-free, and .gitattributes pins the installed dirs to LF.
  - On a cp1252 console the success line's emoji raised UnicodeEncodeError after .claude/
    had been written. Output is ASCII and the streams never raise on encoding.

Exit: 0 done; 1 a failure, or (--check, --upgrade) a problem to resolve; 2 usage error.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)

# The manifest: kit_version, kit_commit, kit_dir, profile, without, dropped_rules, and files:
# {project path: {source: kit path, sha256, kind: kit-owned | adopter-filled}}. sha256 is the
# kit's rendering last DELIVERED for that path, installed in place or offered as .factory-new.
# A kit-owned file whose bytes still hash to it is unmodified, so --upgrade may replace it; a
# new rendering that hashes differently means the kit changed since then.
MANIFEST = ".claude/.factory-manifest.json"
NEW = ".factory-new"
TESTED_SPECKIT = "1.0.12"

# Rules NOT installed per archetype profile (model/ARCHETYPES.md explains each choice).
PROFILES = {
    "full": [],
    "backend": [],
    "frontend": ["data"],
    "cli": ["api-conventions", "data"],
    "library": ["api-conventions", "data"],
    "data": ["api-conventions"],
    "embedded": ["api-conventions", "data"],
    "iac": ["api-conventions", "data"],
    "llm": [],
}

# Files the adopter fills in. --upgrade never replaces them; it offers a .factory-new when the
# kit's source changed. Everything else the kit installs is kit-owned. The agents carry an
# INVARIANTS block the adopter fills (AI-ONBOARDING §2.2 step 7) and the CI job gets the
# adopter's toolchain steps (its own header says so): both were kit-owned until the 2026-09-29
# review, so every correct adoption showed five permanent "modified locally" warnings and an
# upgrade diff made of the adopter's own fill, reversed.
ADOPTER_FILLED = re.compile(
    r"^(?:\.claude/CLAUDE\.md|\.claude/rules/[^/]+\.md|\.claude/agents/[^/]+\.md"
    r"|\.specify/memory/constitution\.md|gates/chain\.conf|\.claude/hooks/careful\.json"
    r"|\.github/workflows/factory-gates\.yml)$")
# Enforcement code: the guard's matcher and shim, the chain runner, the gates and the git hook.
# A local edit here is not "modified locally" but a guard or a gate that may be off, so --check
# fails on it. Since 1.4.0 the guard's rules go in careful.json; a project's own gate goes in its
# own gates/check-<name>.sh.
ENFORCEMENT = re.compile(
    r"^(?:\.claude/hooks/check-careful\.(?:sh|py)"
    r"|gates/(?:run-chain\.sh|check-[^/]+\.(?:sh|py)|hooks/pre-commit))$")
# Installed only when their flag asks. One the adopter deletes is not re-created, but --check
# keeps saying it is gone: CI and the hook are the two things that enforce "no commit on red".
FLAG_FILES = (("gates/hooks/pre-commit", "git-hook"),
              (".github/workflows/factory-gates.yml", "ci-github"))
# The constitution override is what /speckit-constitution drafts .specify/memory/constitution.md
# from, links included (review 2026-09-29: 18 dead links after one run). Its links are written
# for the file that receives them, and checked from there.
CONST_OVERRIDE = ".specify/templates/overrides/constitution-template.md"
CONST_MEMORY = ".specify/memory/constitution.md"

LINK_SCOPE = (".claude", "gates", ".specify/memory", ".specify/templates/overrides")
# By extension and by directory, never `gates/**`: `text` on a whole tree also normalises the
# CRLF bytes inside every binary under it (review 2026-09-29: a PNG committed under gates/
# lost its signature, \r\n -> \n).
GITATTRIBUTES = (
    "# ai-factory-kit: installed scripts stay LF - a CRLF checkout makes bash exit 2, and a",
    "# PreToolUse hook that exits 2 blocks every tool call. Pinned by extension, so a binary",
    "# under gates/ is never touched.",
    ".claude/hooks/*.sh text eol=lf",
    ".claude/hooks/*.py text eol=lf",
    ".claude/hooks/*.json text eol=lf",
    ".claude/hooks/*.txt text eol=lf",
    "gates/*.sh text eol=lf",
    "gates/*.py text eol=lf",
    "gates/*.conf text eol=lf",
    "gates/*.example text eol=lf",
    "gates/hooks/* text eol=lf",
)
# What a pre-release 1.4.0 adopt.py appended; replaced when found under our comment.
GITATTRIBUTES_OLD = (
    "# ai-factory-kit: installed scripts stay LF - a CRLF checkout makes bash exit 2, and a",
    "# PreToolUse hook that exits 2 blocks every tool call.",
    ".claude/hooks/** text eol=lf",
    "gates/** text eol=lf",
)
IGNORED_NAMES = {"__pycache__", ".DS_Store", ".git"}
IGNORED_SUFFIXES = (".pyc", NEW, ".orig", ".rej", ".swp")
GUARD_MARK = "check-careful"  # identifies the careful hook's entries inside settings.json
# The host's settings (only --register-guard merges into settings.json) and Spec Kit's skills.
NEVER_TOUCH = re.compile(r"^\.claude/(?:settings[^/]*\.json|skills/speckit-[^/]*(?:/.*)?)$")


def load_linkcheck():
    # No __pycache__ inside the vendored kit: in a submodule it shows as "untracked content".
    sys.dont_write_bytecode = True
    path = os.path.join(HERE, "check-links.py")
    spec = importlib.util.spec_from_file_location("check_links", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    LC = load_linkcheck()
except (IOError, OSError) as _e:
    sys.exit("ERROR: %s/check-links.py is missing or unreadable (%s)" % (HERE, _e))


# ---------------------------------------------------------------------------- small helpers

class Fail(Exception):
    """A failure that ends the run with exit 1 (or 2 when usage=True)."""

    def __init__(self, msg, usage=False):
        Exception.__init__(self, msg)
        self.usage = usage


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def pjoin(root, rel):
    return os.path.join(root, *rel.split("/"))


def read_bytes(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except (IOError, OSError):
        return None


def write_bytes(path, data, executable=False):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".factory-tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)
    if executable:
        os.chmod(path, 0o755)


def relpath_posix(target, start_dir):
    """Relative path from directory `start_dir` to `target`; both project-relative, posix."""
    t = [p for p in target.split("/") if p not in ("", ".")]
    s = [p for p in start_dir.split("/") if p not in ("", ".")]
    i = 0
    while i < len(t) and i < len(s) and t[i] == s[i]:
        i += 1
    parts = [".."] * (len(s) - i) + t[i:]
    return "/".join(parts) if parts else "."


def normpath_posix(path):
    out = []
    for p in path.split("/"):
        if p in ("", "."):
            continue
        if p == ".." and out and out[-1] != "..":
            out.pop()
        else:
            out.append(p)
    return "/".join(out)


def git(cwd, *args):
    """stdout of a git command, stripped, or None if git is missing or the command fails."""
    try:
        r = subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True)
    except OSError:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def is_script(dest, data):
    base = dest.rsplit("/", 1)[-1]
    return base.endswith((".sh", ".py")) or base == "pre-commit" or data.startswith(b"#!")


def is_markdown(path):
    return path.endswith((".md", ".md.template"))


def kind_of(dest):
    return "adopter-filled" if ADOPTER_FILLED.match(dest) else "kit-owned"


def say(msg=""):
    print(msg)


# ---------------------------------------------------------------------------- kit layout

class Kit(object):
    def __init__(self, root, proj):
        self.root = root
        rel = None
        # abspath first (keeps a symlinked kit dir inside the project); then the resolved paths
        # (cwd comes back resolved, e.g. /private/tmp for /tmp on macOS).
        for r, p in ((root, proj), (os.path.join(os.path.realpath(os.path.dirname(root)),
                                                 os.path.basename(root)), os.path.realpath(proj)),
                     (os.path.realpath(root), os.path.realpath(proj))):
            try:
                cand = os.path.relpath(r, p)
            except ValueError:  # Windows: another drive
                continue
            if not (cand == "." or cand == ".." or cand.startswith(".." + os.sep)):
                rel = cand
                break
        if rel is None:
            raise Fail("the kit must live inside the project, and this must run from the project "
                       "root.\n  kit:     %s\n  project: %s (the current directory)\n"
                       "  Vendor it first (git submodule add <kit-url> factory), then run "
                       "python3 factory/bin/adopt.py from the project root." % (root, proj),
                       usage=True)
        self.rel = rel.replace(os.sep, "/")
        if not os.path.isdir(os.path.join(root, "harness")):
            raise Fail("%s does not look like the AI Factory Kit (no harness/)" % root)
        v = read_bytes(os.path.join(root, "VERSION"))
        self.version = v.decode("utf-8", "replace").strip() if v else "unknown"
        self.has_git = os.path.exists(os.path.join(root, ".git"))
        self.commit = git(root, "rev-parse", "HEAD") if self.has_git else None
        self.rules = sorted(f[:-3] for f in os.listdir(os.path.join(root, "harness", "rules"))
                            if f.endswith(".md")) if os.path.isdir(
            os.path.join(root, "harness", "rules")) else []

    def files(self, sub):
        """Kit-relative posix paths of every file under `sub`, sorted, junk skipped."""
        base = os.path.join(self.root, *sub.split("/"))
        out = []
        for dirpath, dirs, files in os.walk(base):
            dirs[:] = sorted(d for d in dirs if d not in IGNORED_NAMES)
            for f in sorted(files):
                if f in IGNORED_NAMES or f.endswith(IGNORED_SUFFIXES):
                    continue
                full = os.path.join(dirpath, f)
                out.append(os.path.relpath(full, self.root).replace(os.sep, "/"))
        return out

    def exists(self, rel):
        return os.path.exists(pjoin(self.root, rel))

    def isdir(self, rel):
        return os.path.isdir(pjoin(self.root, rel))


# ---------------------------------------------------------------------------- the install plan

class Item(object):
    __slots__ = ("dest", "source", "kind", "data", "script", "source_sha")

    def __init__(self, dest, source, kind, data, script, source_sha=None):
        self.dest, self.source, self.kind, self.data, self.script = dest, source, kind, data, script
        self.source_sha = source_sha


def installed_location(src, kit, dropped):
    """Where kit path `src` lives in the project: a project path, "DROP", or None (not installed).

    Static on purpose: it does not depend on --install-git-hook or --ci, so a doc's rendering
    never changes because a flag was passed on a later run.
    """
    if src == "harness/CLAUDE.md.template":
        return ".claude/CLAUDE.md"
    if src == "harness/settings.json.template":
        # --register-guard reads the kit's copy; an installed second copy was unguarded and
        # read by nothing, so an edit there changed nothing (review 2026-09-29).
        return None
    hooks = "harness/skills/careful/hooks"
    if src == hooks or src.startswith(hooks + "/"):
        return ".claude/hooks" + src[len(hooks):]
    if src.startswith("harness/rules/") and src.endswith(".md"):
        if src[len("harness/rules/"):-3] in dropped:
            return "DROP"
    if src == "harness" or src.startswith("harness/"):
        return ".claude" + src[len("harness"):]
    if src.startswith("gates/") and not kit.isdir(src):
        rest = src[len("gates/"):]
        if not rest.endswith(".md") and not rest.startswith(("hooks/", "ci/")):
            return src
    if src.startswith("speckit/overrides/") and src.endswith(".md") and src.count("/") == 2:
        return ".specify/templates/overrides/" + src.rsplit("/", 1)[1]
    return None


def rewrite_links(text, src, dest, kit, dropped):
    """Re-point every relative link in `text` (kit file `src`) for its new home `dest`."""
    links = LC.find_links(text)
    src_dir = src.rsplit("/", 1)[0] if "/" in src else ""
    dest_dir = dest.rsplit("/", 1)[0] if "/" in dest else ""
    out, pos = [], 0
    for link in links:
        raw = link.target
        angle = raw.startswith("<") and raw.endswith(">")
        inner = raw[1:-1] if angle else raw
        if LC.local_path(raw) is None:
            continue
        m = re.match(r"^([^#?]*)(.*)$", inner)
        path, suffix = m.group(1), m.group(2)
        encoded = "%" in path
        plain = LC.unquote(path)
        trailing = plain.endswith("/")
        target = normpath_posix((src_dir + "/" if src_dir else "") + plain)
        if target == ".." or target.startswith("../"):
            continue  # escapes the kit: leave it for the checker to judge
        where = kit.rel if not target else None
        if target == "constitution/constitution-template.md" \
                and src.startswith(("harness/", "speckit/")):
            where = ".specify/memory/constitution.md"  # the project's constitution, not the blank
        if where is None and target:
            where = installed_location(target, kit, dropped)
        if where == "DROP":
            if link.ref:
                where = None  # a reference definition cannot become plain text; use the kit copy
            else:
                out.append(text[pos:link.start])
                out.append(link.text)
                pos = link.end
                continue
        if where is None:
            where = kit.rel + "/" + target
        new = relpath_posix(where, dest_dir)
        if trailing and not new.endswith("/"):
            new += "/"
        if encoded:
            new = re.sub(r"[ ]", "%20", new)
        new = new + suffix
        if angle:
            new = "<" + new + ">"
        if new == raw:
            continue
        out.append(text[pos:link.tstart])
        out.append(new)
        pos = link.tend
    out.append(text[pos:])
    return "".join(out)


def link_home(dest):
    """Where the links in project file `dest` are written to resolve from (see CONST_OVERRIDE)."""
    return CONST_MEMORY if dest == CONST_OVERRIDE else dest


def render(kit, src, dest, dropped):
    data = read_bytes(pjoin(kit.root, src))
    if data is None:
        raise Fail("kit defect: cannot read %s/%s" % (kit.rel, src))
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data  # not text: copied byte for byte
    text = text.replace("\r\n", "\n")
    if text.startswith("\ufeff"):
        text = text[1:]  # a BOM before "#!" or "---" breaks the shebang and the frontmatter
    if is_markdown(src):
        text = rewrite_links(text, src, link_home(dest), kit, dropped)
    return text.encode("utf-8")


def build_plan(kit, dropped, extras):
    """Every file this run installs, rendered. `extras`: {"git-hook", "ci-github"}."""
    pairs = []
    for src in kit.files("harness"):
        dest = installed_location(src, kit, dropped)
        if dest and dest != "DROP":
            pairs.append((src, dest))
    for src in kit.files("gates"):
        rest = src[len("gates/"):]
        if rest.endswith(".md") and "/" not in rest:
            continue  # GATES.md stays in the kit; installed files link to it there
        if rest.startswith("hooks/"):
            if "git-hook" in extras:
                pairs.append((src, src))
            continue
        if rest.startswith("ci/"):
            if rest == "ci/github-actions.yml" and "ci-github" in extras:
                pairs.append((src, ".github/workflows/factory-gates.yml"))
            continue
        pairs.append((src, src))
        if rest == "chain.conf.example":
            pairs.append((src, "gates/chain.conf"))
    if os.path.isdir(os.path.join(kit.root, "speckit", "overrides")):
        for src in kit.files("speckit/overrides"):
            dest = installed_location(src, kit, dropped)
            if dest:
                pairs.append((src, dest))
    const = "constitution/constitution-template.md"
    if kit.exists(const):
        pairs.append((const, CONST_OVERRIDE))
        pairs.append((const, CONST_MEMORY))

    plan, seen = [], {}
    for src, dest in pairs:
        if NEVER_TOUCH.match(dest):
            raise Fail("kit defect: %s would install %s, which adopt.py never touches"
                       % (src, dest))
        if dest in seen:
            raise Fail("kit defect: %s and %s would both install to %s" % (seen[dest], src, dest))
        seen[dest] = src
        data = render(kit, src, dest, dropped)
        plan.append(Item(dest, src, kind_of(dest), data, is_script(dest, data),
                         sha256(read_bytes(pjoin(kit.root, src)) or b"")))
    return plan


# ---------------------------------------------------------------------------- assertions

FM_RULES = (
    (re.compile(r"^\.claude/agents/[^/]+\.md$"), "agent",
     "Claude Code skips it as a subagent and treats it as documentation"),
    (re.compile(r"^\.claude/rules/[^/]+\.md$"), "rule",
     "its paths: scope is never parsed, so the rule loads in every session"),
    (re.compile(r"^\.claude/skills/[^/]+/SKILL\.md$"), "skill",
     "skill loaders require the frontmatter first (harness/skills/README.md rule 2)"),
)
FM_OPEN = re.compile(r"^---[ \t\r]*\n")
# A frontmatter block that exists but does not open at byte 0: a fence, then a key, early on.
MISPLACED_FM = re.compile(r"(?:^|\n)---[ \t\r]*\n(?:[^\n]*\n){0,10}?[ \t]*(?:paths|name|description)[ \t]*:")
FM_CLOSE = re.compile(r"^---[ \t\r]*$", re.M)
# Claude Code 2.1.284 parses frontmatter with /^---\s*\n([\s\S]*?)---\s*\n?/: the closing fence
# is NOT line-anchored, so three dashes anywhere inside the block (a YAML comment explaining the
# fence, a "---" in a description) end the frontmatter there and drop every key after it.


def frontmatter_problem(dest, data):
    """None, or why `dest` (a project path) fails the byte-0 frontmatter contract."""
    for pattern, what, consequence in FM_RULES:
        if not pattern.match(dest):
            continue
        text = data.decode("utf-8", "replace")
        m = FM_OPEN.match(text)
        if not m and what == "rule" and not MISPLACED_FM.search(text[:4000]):
            # No frontmatter at all is a valid rule: it has no paths: scope and loads in every
            # session, as the author meant (review 2026-09-29: a brownfield workflow.md failed
            # --check for ever, over a scope it never had).
            return None
        if not m:
            lead = "a UTF-8 BOM" if text.startswith("\ufeff") else repr(text[:12])
            return "%s: YAML frontmatter must open at byte 0 (starts with %s) - %s" % (
                what, lead, consequence)
        close = FM_CLOSE.search(text, m.end())
        if not close:
            return "%s: frontmatter opened at byte 0 is never closed with ---" % what
        early = text.find("---", m.end(), close.start())
        if early >= 0:
            line = text.count("\n", 0, early) + 1
            return ("%s: three dashes inside the frontmatter (line %d) - Claude Code ends the "
                    "block there and drops the keys after it; reword without them" % (what, line))
        if what == "agent":
            block = text[m.end():close.start()]
            missing = [k for k in ("name", "description")
                       if not re.search(r"^%s:[ \t]*\S" % k, block, re.M)]
            if missing:
                return "agent: frontmatter lacks %s - %s" % (" and ".join(missing), consequence)
        return None
    return None


def cr_problem(dest, data):
    """A CR in a script or in the config a script reads. Never a binary: a PNG's signature holds
    \r\n, and a warning about it trained people to ignore this one (review 2026-09-29)."""
    if is_markdown(dest) or b"\r" not in data:
        return None
    if not (is_script(dest, data) or dest.endswith((".conf", ".json"))):
        return None
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return "contains a carriage return (CR): bash cannot run a CRLF script"


# ---------------------------------------------------------------------------- manifest

def load_manifest(proj):
    raw = read_bytes(pjoin(proj, MANIFEST))
    if raw is None:
        return None
    try:
        m = json.loads(raw.decode("utf-8"))
        if not isinstance(m.get("files"), dict):
            raise ValueError("no files map")
        return m
    except ValueError as e:
        raise Fail("%s is unreadable (%s). Fix it, or delete it and run --upgrade (the project is "
                   "then treated as a pre-1.4.0 adoption: every differing file is offered as "
                   ".factory-new)." % (MANIFEST, e))


def manifest_text(m):
    return (json.dumps(m, indent=2, sort_keys=False) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------- selection

def parse_without(value, kit):
    names = [n.strip() for n in (value or "").split(",") if n.strip()]
    unknown = [n for n in names if n not in kit.rules]
    if unknown:
        raise Fail("--without: unknown rule(s) %s; the kit ships: %s" % (
            ", ".join(unknown), ", ".join(kit.rules)), usage=True)
    return names


def resolve_selection(args, kit, manifest, proj):
    """(profile, without, dropped, notes). Flags decide; with no flags the manifest decides."""
    notes = []
    if args.profile or args.without is not None:
        profile = args.profile or (manifest or {}).get("profile") or "full"
        without = parse_without(args.without, kit)
    elif manifest:
        profile = manifest.get("profile") or "full"
        without = [w for w in manifest.get("without", []) if w in kit.rules]
        # A rule the adopter deleted since install stays dropped; links to it become text.
        for dest in manifest["files"]:
            m = re.match(r"^\.claude/rules/([^/]+)\.md$", dest)
            if m and m.group(1) in kit.rules and m.group(1) not in without \
                    and not os.path.exists(pjoin(proj, dest)):
                without.append(m.group(1))
                notes.append("rule %s was deleted after install: treated as dropped" % m.group(1))
    else:
        profile, without = "full", []
    if profile not in PROFILES:
        raise Fail("unknown profile %r; choose one of: %s" % (profile, ", ".join(PROFILES)),
                   usage=True)
    dropped = sorted(set(r for r in PROFILES[profile] if r in kit.rules) | set(without))
    return profile, sorted(set(without)), dropped, notes


# ---------------------------------------------------------------------------- vcs state

def kit_vcs_state(proj, kit):
    """(state, detail): state is one of submodule, vendored, embedded, symlink, no-repo."""
    top = git(proj, "rev-parse", "--show-toplevel")
    if top is None:
        return "no-repo", None
    if os.path.islink(kit.root.rstrip(os.sep)):
        return "symlink", None
    rel_top = os.path.relpath(os.path.realpath(kit.root), os.path.realpath(top))
    rel_top = rel_top.replace(os.sep, "/")
    staged = git(top, "ls-files", "-s", "--", rel_top) or ""
    gitlink = any(l.startswith("160000 ") and l.split("\t", 1)[-1] == rel_top
                  for l in staged.splitlines())
    paths = git(top, "config", "-f", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$") or ""
    registered = any(l.split(" ", 1)[-1] == rel_top for l in paths.splitlines())
    if gitlink and registered:
        return "submodule", None
    if kit.has_git:
        return "embedded", (rel_top, gitlink)
    return "vendored", None


def embedded_warning(proj, kit, detail):
    rel_top, gitlink = detail
    url = git(kit.root, "remote", "get-url", "origin") or "<kit-url>"
    lines = [
        "WARNING %s/ is an embedded git repository, not a registered submodule." % kit.rel,
        "  A teammate's or CI's clone of this project gets an EMPTY %s/, and every link" % kit.rel,
        "  into it from .claude/, gates/ and .specify/ is dead. Fix it one of two ways:",
        "    submodule: %sgit submodule add %s %s" % (
            "git rm --cached -f -q %s && " % rel_top if gitlink else "", url, rel_top),
        "               (git keeps the clone that is already there and records it properly)",
        "    vendored:  delete %s/.git - a plain copy, upgraded by replacing the directory"
        % kit.rel,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------- applying

class Report(object):
    def __init__(self):
        self.installed, self.unchanged, self.replaced, self.kept = [], [], [], []
        self.offered = []      # (dest, why)
        self.outdated = []     # kit-owned, unmodified, kit changed; default mode left it
        self.removed, self.orphans, self.notes, self.warnings = [], [], [], []
        self.failed = False


def spec_kit_scaffold(proj, data):
    """True if `data` is Spec Kit's own unfilled constitution scaffold (nothing adopter-written)."""
    tmpl = read_bytes(pjoin(proj, ".specify/templates/constitution-template.md"))
    if tmpl is not None and tmpl == data:
        return True
    rec = read_bytes(pjoin(proj, ".specify/memory/.constitution-template.json"))
    try:
        return bool(rec) and json.loads(rec.decode("utf-8")).get("sha256") == sha256(data)
    except ValueError:
        return False


def in_kit_history(kit, source, data):
    """True if `data` is byte for byte some committed version of kit file `source`."""
    if not kit.has_git or data is None:
        return False
    blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
    log = git(kit.root, "log", "--format=", "--raw", "--no-abbrev", "--", source) or ""
    for line in log.splitlines():
        parts = line.split()
        if len(parts) >= 4 and blob in (parts[2], parts[3]):
            return True
    return False


def history_hint(kit, source, data):
    """If `data` equals some committed version of kit `source`, the adopter changed nothing."""
    if is_markdown(source) or not in_kit_history(kit, source, data):
        return None
    return "identical to the kit's own %s at an earlier version: take the .factory-new" % source


def apply_plan(proj, kit, plan, files, mode, legacy, rep):
    """Write what may be written. `files` is the manifest's map, updated in place."""
    ours = set()
    for it in plan:
        path = pjoin(proj, it.dest)
        rec = files.get(it.dest)
        render_sha = sha256(it.data)
        cur = read_bytes(path)
        entry = {"source": it.source, "sha256": render_sha, "kind": it.kind,
                 "source_sha256": it.source_sha}
        # Same kit source, different rendering: the profile, a dropped rule or the kit's
        # directory changed, not the kit (review 2026-09-29: the old message blamed the kit and
        # sent the adopter to --upgrade, the human-only step).
        render_only = rec is not None and rec.get("source_sha256") == it.source_sha \
            and rec.get("sha256") != render_sha
        if os.path.isdir(path):
            rep.warnings.append("%s is a directory; the kit installs a file there - skipped"
                                % it.dest)
            rep.failed = True
            continue
        if cur is None:
            write_bytes(path, it.data, it.script)
            rep.installed.append(it.dest)
            ours.add(it.dest)
        elif cur == it.data:
            if it.script and not os.access(path, os.X_OK):
                os.chmod(path, 0o755)
            rep.unchanged.append(it.dest)
            ours.add(it.dest)
        elif rec is None and it.dest == CONST_MEMORY and spec_kit_scaffold(proj, cur):
            write_bytes(path, it.data)
            rep.replaced.append(it.dest)
            rep.notes.append("replaced Spec Kit's unfilled constitution scaffold with the kit's")
            ours.add(it.dest)
        elif rec is not None and it.kind == "kit-owned" and sha256(cur) == rec.get("sha256"):
            if mode == "upgrade" or render_only:
                write_bytes(path, it.data, it.script)
                rep.replaced.append(it.dest)
                ours.add(it.dest)
            else:
                offer(path, it.data, it.script)
                rep.outdated.append(it.dest)
                entry["sha256"] = rec["sha256"]  # still unmodified: --upgrade may replace it
                entry["source_sha256"] = rec.get("source_sha256")
        elif rec is not None and rec.get("sha256") == render_sha:
            rep.kept.append(it.dest)  # the adopter's version; this kit version was offered before
        else:
            offer(path, it.data, it.script)
            kit_changed = rec is not None and not render_only
            if rec is None and not legacy:
                why = "was already there"
                if it.kind == "kit-owned" or it.dest.startswith((".claude/rules/",
                                                                 ".claude/agents/")):
                    why += ("; if yours is a different file that only shares the kit's name, "
                            "rename yours to keep both")
            elif rec is None and it.dest in (".claude/hooks/check-careful.py",
                                             ".claude/hooks/check-careful.sh"):
                why = ("no manifest; 1.4.0 replaces the guard wholesale: take the .factory-new, "
                       "then port any local rule to .claude/hooks/careful.json, the only "
                       "extension point since 1.4.0")
            elif rec is None:
                why = "no manifest: cannot tell kit copy from local edit"
            elif render_only:
                why = ("its links changed with the profile or a dropped rule, not the kit: merge "
                       "the link changes")
            elif it.kind == "adopter-filled":
                why = "adopter-filled; the kit's template changed"
            else:
                why = "kit-owned, modified locally"
            hint = history_hint(kit, it.source, cur) if rec is None else None
            rep.offered.append((it.dest, why + ("; " + hint if hint else ""),
                                it.source if kit_changed else None))
        files[it.dest] = entry
        stale = read_bytes(path + NEW)
        if stale is not None and stale == read_bytes(path):
            os.remove(path + NEW)  # nothing left to review
    return ours


def offer(path, data, executable=False):
    # A .factory-new is taken by `mv` (PHASE-0 §2 says so). Written 0644, the moved script lost
    # its execute bit and git ignored the pre-commit hook while --check said OK (review
    # 2026-09-29), so a script's .factory-new is executable too.
    write_bytes(path + NEW, data, executable)


def handle_orphans(proj, plan, files, mode, dropped, rep):
    """Manifest entries this kit version no longer installs."""
    planned = set(it.dest for it in plan)
    for dest in sorted(files):
        if dest in planned:
            continue
        rec, path = files[dest], pjoin(proj, dest)
        cur = read_bytes(path)
        rule = re.match(r"^\.claude/rules/([^/]+)\.md$", dest)
        if cur is None and dest in dict(FLAG_FILES):
            continue  # kept on record so that --check keeps saying the hook or CI job is gone
        if cur is None:
            del files[dest]
        elif rule and rule.group(1) in dropped:
            rep.orphans.append("%s: the profile drops this rule but it is on disk - delete it if "
                               "you mean it (then run --check for links to it)" % dest)
            if mode == "upgrade":
                del files[dest]
        elif rec.get("kind") == "kit-owned" and sha256(cur) == rec.get("sha256"):
            if mode == "upgrade":
                os.remove(path)
                if os.path.exists(path + NEW):
                    os.remove(path + NEW)
                rep.removed.append(dest)
                del files[dest]
            else:
                rep.orphans.append("%s: no longer shipped by the kit; --upgrade removes it" % dest)
        else:
            rep.orphans.append("%s: no longer shipped by the kit; left in place (modified or "
                               "adopter-filled)" % dest)
            if mode == "upgrade":
                del files[dest]


def legacy_duplicate_hooks(proj, kit, mode, before, rep):
    """v1.3.x left a second, unregistered copy of the guard under .claude/skills/careful/hooks/."""
    dup = pjoin(proj, ".claude/skills/careful/hooks")
    if not os.path.isdir(dup):
        return
    left = []
    for f in sorted(os.listdir(dup)):
        p = os.path.join(dup, f)
        data = read_bytes(p) if os.path.isfile(p) else None
        kit_copy = read_bytes(os.path.join(kit.root, "harness", "skills", "careful", "hooks", f))
        # Unmodified = equal to the live copy, to this kit's copy, or to ANY committed kit
        # version (review 2026-09-29: a pristine v1.3.2 copy beside an edited live copy
        # survived every --upgrade, and --check kept saying "run --upgrade").
        same = data is not None and (data == before.get(f) or data == kit_copy or in_kit_history(
            kit, "harness/skills/careful/hooks/" + f, data))
        if mode == "upgrade" and same:
            os.remove(p)
            rep.removed.append(".claude/skills/careful/hooks/" + f)
        else:
            left.append(f)
    if not left and mode == "upgrade":
        os.rmdir(dup)
        return
    msg = (".claude/skills/careful/hooks/ holds an unregistered copy of the guard (%s). Edits "
           "there never reach the live hook in .claude/hooks/; " % ", ".join(left))
    msg += ("these match neither the live copy nor any kit version adopt.py can compare with "
            "(%s/'s git history, when it has one), so treat them as local edits: port any rule "
            "they add to .claude/hooks/careful.json, then delete the directory" % kit.rel
            if mode == "upgrade" else "run --upgrade to remove the unmodified copies")
    rep.warnings.append(msg)


def ensure_gitattributes(proj, rep):
    path = pjoin(proj, ".gitattributes")
    cur = read_bytes(path) or b""
    text = cur.decode("utf-8", "replace")
    lines = text.splitlines()
    migrated = False
    if GITATTRIBUTES_OLD[0] in lines and GITATTRIBUTES_OLD[2] in lines \
            and GITATTRIBUTES_OLD[3] in lines:
        # A pre-release 1.4.0 block: its `gates/** text` also rewrote binaries. Replace it.
        lines = [l for l in lines if l not in GITATTRIBUTES_OLD]
        text = "\n".join(lines) + ("\n" if lines else "")
        migrated = True
    have = set(l.strip() for l in lines)
    rules = [l for l in GITATTRIBUTES if not l.startswith("#")]
    if all(r in have for r in rules) and not migrated:
        return
    add = [l for l in GITATTRIBUTES if l.startswith("#") or l not in have]
    sep = "" if not text or text.endswith("\n") else "\n"
    write_bytes(path, (text + sep + "\n".join(add) + "\n").encode("utf-8"))
    rep.notes.append(".gitattributes: pinned the installed scripts and gate config to LF, by "
                     "extension%s" % (" (replaced the earlier gates/** rule, which also touched "
                                      "binaries)" if migrated else ""))


# ---------------------------------------------------------------------------- auditing

def scan_new_files(proj):
    out = []
    for root in (".claude", "gates", ".specify", ".github/workflows"):
        base = pjoin(proj, root)
        for dirpath, dirs, fnames in os.walk(base):
            dirs[:] = [d for d in dirs if d not in IGNORED_NAMES
                       and not (d == "worktrees" and os.path.basename(dirpath) == ".claude")]
            for f in fnames:
                if f.endswith(NEW):
                    out.append(os.path.relpath(os.path.join(dirpath, f), proj).replace(os.sep, "/"))
    return sorted(out)


def old_constitution_hint(proj, kit, dest, target):
    """A dead link in .specify/memory/ that resolves from the kit's constitution/ directory:
    written for the pre-1.4.0 instructions, which had the adopter save the kit's template there
    unchanged (review 2026-09-29: 9 such links failed --check after a v1.3.2 upgrade)."""
    if kit is None or not dest.startswith(".specify/memory/"):
        return ""
    path = LC.local_path(target)
    if not path:
        return ""
    t = normpath_posix("constitution/" + LC.unquote(path.split("#", 1)[0]))
    if t.startswith("../") or not kit.exists(t):
        return ""
    return (" - written for %s/constitution/, where the kit's template lives (pre-1.4.0 "
            "instructions saved it unchanged); from here it is %s. In the ratified constitution, "
            "re-pointing it is an amendment: the owner approves"
            % (kit.rel, relpath_posix(kit.rel + "/" + t, dest.rsplit("/", 1)[0])))


def audit_disk(proj, strict, kit=None):
    """Links, frontmatter and CR on disk. Returns (errors, warnings).

    `strict(dest)` says whether a problem in project path `dest` (possibly a .factory-new) is
    an error (content the kit is answerable for) or a warning (a file the kit did not write).
    """
    errors, warnings = [], []

    def put(dest, msg):
        (errors if strict(dest) else warnings).append("%s: %s" % (dest, msg))

    cache = {}
    for root in LINK_SCOPE:
        base = pjoin(proj, root)
        if not os.path.isdir(base):
            continue
        for path in LC.markdown_files(base):
            dest = os.path.relpath(path, proj).replace(os.sep, "/")
            elsewhere = LC.base_dir_for(path) != os.path.dirname(os.path.abspath(path))
            for line, target, why in LC.check_file(path, cache):
                put(dest, "line %d: dead link -> %s (%s%s)%s" % (
                    line, target, why, ", resolved from .specify/memory/, where "
                    "/speckit-constitution copies it" if elsewhere else "",
                    old_constitution_hint(proj, kit, dest, target)))
    for root in (".claude/agents", ".claude/rules", ".claude/skills"):
        base = pjoin(proj, root)
        if not os.path.isdir(base):
            continue
        for dirpath, dirs, fnames in os.walk(base):
            for f in fnames:
                dest = os.path.relpath(os.path.join(dirpath, f), proj).replace(os.sep, "/")
                p = frontmatter_problem(dest, read_bytes(os.path.join(dirpath, f)) or b"")
                if p:
                    put(dest, p)
    for root in (".claude/hooks", "gates"):
        base = pjoin(proj, root)
        for dirpath, dirs, fnames in os.walk(base):
            dirs[:] = [d for d in dirs if d not in IGNORED_NAMES]
            for f in fnames:
                if f.endswith(NEW):
                    continue
                dest = os.path.relpath(os.path.join(dirpath, f), proj).replace(os.sep, "/")
                p = cr_problem(dest, read_bytes(os.path.join(dirpath, f)) or b"")
                if p:
                    put(dest, p)
    return errors, warnings


def recorded_extras(proj, files):
    """Flag-installed files stay installed while they exist; one the adopter deleted stays gone."""
    extras = set()
    for dest, extra in FLAG_FILES:
        if dest in files and os.path.exists(pjoin(proj, dest)):
            extras.add(extra)
    return extras


def version_tuple(v):
    m = re.match(r"^\s*v?(\d+)\.(\d+)\.(\d+)", v or "")
    return tuple(int(x) for x in m.groups()) if m else None


def kit_behind(kit, manifest):
    """None, or why factory/ is OLDER than the kit that last installed into this project.

    Review 2026-09-29: a teammate's plain `git pull` leaves the submodule on the old commit;
    --check then said "stale - run --upgrade", and --upgrade put the older guard and gates back
    with a green --check. Version first; for one version, ancestry when the recorded commit is
    known to this clone of the kit.
    """
    if not manifest:
        return None
    mv, kv = version_tuple(manifest.get("kit_version")), version_tuple(kit.version)
    mc = manifest.get("kit_commit")
    said = "%s @ %s" % (manifest.get("kit_version"), (mc or "?")[:7])
    here = "%s @ %s" % (kit.version, (kit.commit or "?")[:7])
    if mv and kv and mv != kv:
        return ("%s/ is kit %s, older than the %s this project last installed" % (
            kit.rel, here, said)) if mv > kv else None
    if mc and kit.commit and mc != kit.commit and kit.has_git \
            and git(kit.root, "cat-file", "-e", mc + "^{commit}") is not None \
            and git(kit.root, "merge-base", "--is-ancestor", kit.commit, mc) is not None:
        return "%s/ is kit %s, behind the %s this project last installed" % (kit.rel, here, said)
    return None


def behind_advice(kit):
    return ("a stale checkout of %s/, not a kit change: run git submodule update --init (a "
            "vendored copy: put the newer release back). Do not run --upgrade: it would install "
            "the older guard and gates. A deliberate rollback is --upgrade --allow-downgrade."
            % kit.rel)


# An unfilled slot in a file the adopter fills: `[PROJECT_NAME]`, `[DOMAIN INVARIANT]`,
# `[BRANCH_MODEL — EXAMPLE: …]`, `[X.Y.Z]`, an agent's `[copy from CLAUDE.md]`. Review 2026-09-29:
# two survived to an accepted feature with --check OK and the chain green. A markdown link's text
# (`[GATES §3](…)`) is not a slot.
PLACEHOLDER_RX = re.compile(
    r"\[copy from CLAUDE\.md\]|\[X\.Y\.Z\]"
    r"|\[[A-Z][A-Z0-9_]+(?:[ _./-][A-Z0-9_]+)*(?:[ \t]*[:—–-][^\[\]]{0,400})?\](?![(\[])")


def placeholder_warnings(proj, files):
    out = []
    for dest in sorted(files):
        if files[dest].get("kind") != "adopter-filled" or not is_markdown(dest):
            continue
        raw = read_bytes(pjoin(proj, dest))
        if raw is None:
            continue
        text = re.sub(r"<!--.*?-->", "", raw.decode("utf-8", "replace"), flags=re.S)
        found = PLACEHOLDER_RX.findall(text)
        if found:
            first = re.sub(r"\s+", " ", found[0])
            out.append("%s: %d unfilled placeholder(s), e.g. %s - fill them (PHASE-0 §2 step 7) "
                       "or mark the part N/A with its reason" % (
                           dest, len(found), first if len(first) <= 50 else first[:47] + "...]"))
    return out


def script_mode_problems(proj, plan):
    """Installed scripts that lost the execute bit on disk or in the index."""
    out = []
    scripts = [it.dest for it in plan if it.script and os.path.isfile(pjoin(proj, it.dest))]
    if os.name != "nt":
        for d in scripts:
            if not os.access(pjoin(proj, d), os.X_OK):
                out.append("%s: not executable (a .factory-new taken by mv?) - chmod +x %s" % (d, d))
    if scripts and git(proj, "rev-parse", "--is-inside-work-tree") == "true":
        staged = git(proj, "ls-files", "-s", "--", *scripts) or ""
        for line in staged.splitlines():
            mode, _, rest = line.partition(" ")
            path = line.split("\t", 1)[-1]
            if mode == "100644":
                out.append("%s: committed without the execute bit (mode 100644), so every clone "
                           "gets a script git and the chain cannot run - git update-index "
                           "--chmod=+x %s" % (path, path))
    return out


def hook_wiring_warning(proj, files, kit_rel):
    """The pre-commit gate is recorded here, but this clone does not run it."""
    if "gates/hooks/pre-commit" not in files or not os.path.isfile(
            pjoin(proj, "gates/hooks/pre-commit")):
        return None
    top = git(proj, "rev-parse", "--show-toplevel")
    if top is None:
        return None
    want = os.path.relpath(pjoin(proj, "gates/hooks"), top).replace(os.sep, "/")
    cur = (git(proj, "config", "--get", "core.hooksPath") or "").rstrip("/")
    if cur == want:
        return None
    return ("gates/hooks/pre-commit is installed but this clone does not run it (core.hooksPath "
            "is %s). core.hooksPath is per clone: run python3 %s/bin/adopt.py "
            "--install-git-hook once in every clone" % (repr(cur) if cur else "unset", kit_rel))


def run_check(proj, kit, manifest, args):
    """--check: writes nothing. Returns the exit code."""
    errors, warnings, info = [], [], []
    trusted_runner = False
    if manifest is None:
        if os.path.isdir(pjoin(proj, ".claude")):
            errors.append("no %s: a pre-1.4.0 adoption (or a hand copy). Run --upgrade: it "
                          "offers every differing file as .factory-new and writes the manifest."
                          % MANIFEST)
        else:
            errors.append("not adopted: no .claude/ here. Run python3 %s/bin/adopt.py" % kit.rel)
        recorded = set()
    else:
        files = manifest["files"]
        recorded = set(files)
        behind = kit_behind(kit, manifest)
        if behind:
            errors.append("%s - %s" % (behind, behind_advice(kit)))
        profile, without, dropped, notes = resolve_selection(
            argparse.Namespace(profile=None, without=None), kit, manifest, proj)
        info.extend(notes)
        plan = build_plan(kit, dropped, recorded_extras(proj, files))
        stale_hidden = 0
        for it in plan:
            rec, path = files.get(it.dest), pjoin(proj, it.dest)
            cur = read_bytes(path)
            if it.dest == "gates/run-chain.sh" and cur is not None and rec is not None:
                trusted_runner = sha256(cur) in (rec.get("sha256"), sha256(it.data))
            if rec is None:
                errors.append("%s: shipped by the kit but not installed here - run --upgrade"
                              % it.dest)
            elif cur is None:
                errors.append("%s: installed, now missing - run adopt.py to restore it" % it.dest)
            elif sha256(it.data) != rec.get("sha256"):
                if behind:
                    stale_hidden += 1
                elif rec.get("source_sha256") == it.source_sha:
                    errors.append("%s: its links no longer match the profile or the rules on disk "
                                  "(a rule deleted or the profile changed) - run python3 "
                                  "%s/bin/adopt.py, not --upgrade" % (it.dest, kit.rel))
                else:
                    errors.append("%s: stale - %s/ changed since the last install or upgrade; "
                                  "run --upgrade" % (it.dest, kit.rel))
            elif it.kind == "kit-owned" and sha256(cur) != rec.get("sha256") \
                    and not os.path.exists(path + NEW):
                if ENFORCEMENT.match(it.dest):
                    errors.append(
                        "%s: differs from the kit's copy, so the %s may be off. Local edits to "
                        "enforcement code are not supported: the guard's rules go in "
                        ".claude/hooks/careful.json, a project gate in its own "
                        "gates/check-<name>.sh. Rename yours if you need it, then a human "
                        "deletes this file and runs python3 %s/bin/adopt.py to restore it" % (
                            it.dest, "guard" if it.dest.startswith(".claude/") else "gate",
                            kit.rel))
                else:
                    warnings.append("%s: kit-owned but modified locally (--upgrade offers a "
                                    ".factory-new instead of replacing it)" % it.dest)
        if stale_hidden:
            info.append("%d file(s) differ from what %s/ would install because %s/ is behind; "
                        "not listed" % (stale_hidden, kit.rel, kit.rel))
        planned = set(it.dest for it in plan)
        for dest in sorted(recorded - planned):
            if os.path.exists(pjoin(proj, dest)):
                errors.append("%s: no longer shipped by the kit - run --upgrade" % dest)
            elif dest in dict(FLAG_FILES):
                warnings.append(
                    "%s: installed by adopt.py %s, now deleted - %s. Reinstall it with that flag; "
                    "if it moved on purpose, remove its entry from %s" % (
                        dest, "--install-git-hook" if dest.startswith("gates/") else "--ci github",
                        "no local refusal of a red commit" if dest.startswith("gates/")
                        else "CI no longer runs the gate chain", MANIFEST))
        hw = hook_wiring_warning(proj, files, kit.rel)
        if hw:
            warnings.append(hw)
        errors.extend(script_mode_problems(proj, plan))
        warnings.extend(placeholder_warnings(proj, files))
        if manifest.get("kit_version") != kit.version and not behind:
            info.append("installed from kit %s; %s/ is now %s" % (
                manifest.get("kit_version"), kit.rel, kit.version))
    pending = scan_new_files(proj)
    for f in pending:
        errors.append("%s: awaiting review" % f)
    if os.path.isdir(pjoin(proj, ".claude/skills/careful/hooks")):
        errors.append(".claude/skills/careful/hooks/: an unregistered second copy of the guard; "
                      "edits there never reach .claude/hooks/. --upgrade removes a copy that "
                      "matches any kit version; one it leaves holds local edits: port any rule "
                      "it adds to .claude/hooks/careful.json, then delete the directory")
    e, w = audit_disk(proj, lambda d: (d[:-len(NEW)] if d.endswith(NEW) else d) in recorded, kit)
    errors.extend(e)
    warnings.extend(w)
    reg = registration_state(proj, kit)
    if reg == "stale":
        errors.append(".claude/settings.json: the careful hook is registered with an older wiring "
                      "than %s/harness/settings.json.template - run --register-guard" % kit.rel)
    elif reg == "unreadable":
        errors.append(".claude/settings.json: not valid JSON, so the guard's wiring cannot be read")
    elif reg == "absent":
        info.append("the careful guard is not registered yet (--register-guard, after the first "
                    "commit)")
    chain_problem = chain_conf_problem(proj) if trusted_runner else None
    if chain_problem:
        errors.append(chain_problem)
    state, detail = kit_vcs_state(proj, kit)
    if state == "embedded":
        warnings.append(embedded_warning(proj, kit, detail))

    say("adopt.py --check  (kit %s at %s/)" % (kit.version, kit.rel))
    for i in info:
        say("  note  " + i)
    for w in warnings:
        say("  WARN  " + w)
    for e in errors:
        say("  FAIL  " + e)
    if pending:
        say("  To review: diff -u <file> <file>.factory-new, merge what applies, delete the "
            ".factory-new.")
    if errors:
        say("check: %d problem(s), %d warning(s)" % (len(errors), len(warnings)))
        return 1
    say("check: OK - %d file(s) match the manifest; links, frontmatter and line endings clean%s"
        % (len(recorded), " (%d warning(s))" % len(warnings) if warnings else ""))
    return 0


def chain_conf_problem(proj):
    """None, or why gates/chain.conf is malformed, as run-chain.sh --list reads it (exit 2).

    --list runs no slot and writes nothing. A red chain (TODO slots) is not a --check problem:
    that is the honest state of every project before feature 001 wires it. Called only when
    gates/run-chain.sh is the kit's own (review 2026-09-29: --check, which writes nothing, ran a
    brownfield project's own run-chain.sh, which ignored --list and appended to a log)."""
    runner, conf = pjoin(proj, "gates/run-chain.sh"), pjoin(proj, "gates/chain.conf")
    if not (os.path.isfile(runner) and os.path.isfile(conf)):
        return None
    try:
        r = subprocess.run(["bash", runner, "--list"], cwd=proj, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None  # no bash here (native Windows without Git Bash): nothing to ask
    if r.returncode != 2:
        return None
    out = r.stdout.decode("utf-8", "replace").strip().splitlines()
    return "gates/chain.conf: run-chain.sh rejects it (exit 2) - %s" % (
        out[-1] if out else "no message")


# ---------------------------------------------------------------------------- post-install actions

def template_hooks(kit):
    tpath = os.path.join(kit.root, "harness", "settings.json.template")
    try:
        with open(tpath, "rb") as fh:
            hooks = json.loads(fh.read().decode("utf-8"))["hooks"]
        if not isinstance(hooks, dict):
            raise ValueError("hooks is not an object")
        return hooks
    except (IOError, OSError, ValueError, KeyError, TypeError) as e:
        raise Fail("cannot read the hooks from %s: %s" % (tpath, e))


def guard_groups(settings_hooks, event):
    return [g for g in settings_hooks.get(event, []) or []
            if isinstance(g, dict) and any(GUARD_MARK in str(h.get("command", ""))
                                           for h in g.get("hooks", []) if isinstance(h, dict))]


def registration_state(proj, kit):
    """absent | current | stale | unreadable: the careful hook in .claude/settings.json."""
    raw = read_bytes(pjoin(proj, ".claude/settings.json"))
    if raw is None or GUARD_MARK.encode() not in raw:
        return "absent"
    try:
        sh = json.loads(raw.decode("utf-8")).get("hooks", {})
        want = template_hooks(kit)
    except (ValueError, AttributeError, Fail):
        return "unreadable"
    for event, groups in want.items():
        if guard_groups(sh, event) != groups:
            return "stale"
    return "current"


def register_guard(proj, kit, rep):
    """Merge the settings template's hooks into .claude/settings.json. Returns False on failure."""
    hooks = template_hooks(kit)
    # Registering strips every existing careful entry and adds the template's. A template that
    # lost either matcher (an edit to factory/, say) would therefore UNregister the guard.
    for tool in ("Bash", "Write", "Edit"):
        if not any(re.search(r"(?:^|\|)%s(?:\||$)" % tool, g.get("matcher") or "")
                   for g in guard_groups(hooks, "PreToolUse")):
            raise Fail("%s/harness/settings.json.template does not register the careful hook for "
                       "%s; registering it would weaken the guard. Not registered."
                       % (kit.rel, tool))
    for f in ("check-careful.sh", "check-careful.py"):
        if not os.path.isfile(pjoin(proj, ".claude/hooks/" + f)):
            raise Fail(".claude/hooks/%s is missing; a registered hook with no script blocks every "
                       "tool call. Run adopt.py without --register-guard first." % f)
    # Smoke-run every command the template registers, the way the host would (Claude Code runs
    # a shell-form hook with sh -c on macOS and Linux, Git Bash on Windows). A broken hook that
    # fails closed blocks every tool call, so it must not be registered.
    shell = "bash" if os.name == "nt" else "sh"
    env = dict(os.environ, CLAUDE_PROJECT_DIR=proj)
    base = {"hook_event_name": "PreToolUse", "cwd": proj}
    probes = ((json.dumps(dict(base, tool_name="Bash", tool_input={"command": "ls"})), "Bash"),
              (json.dumps(dict(base, tool_name="Write", tool_input={
                  "file_path": os.path.join(proj, "README.md"), "content": "x"})), "Write"))
    commands = []
    for event, groups in hooks.items():
        for g in groups:
            for h in g.get("hooks", []):
                if h.get("type") == "command" and h.get("command"):
                    commands.append((g.get("matcher", ""), h["command"]))
    for matcher, command in commands:
        for payload, tool in probes:
            if not re.search(r"(?:^|\|)%s(?:\||$)" % tool, matcher or ""):
                continue
            try:
                r = subprocess.run([shell, "-c", command], cwd=proj, env=env,
                                   input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   universal_newlines=True, timeout=30)
            except OSError:
                raise Fail("%s is not on PATH; the hook command needs it. Not registered." % shell)
            except subprocess.TimeoutExpired:
                raise Fail("the hook command timed out on a benign %s call. Not registered." % tool)
            try:
                decision = json.loads(r.stdout or "{}").get("hookSpecificOutput", {}).get(
                    "permissionDecision")
            except (ValueError, AttributeError):
                decision = None
            denied = decision == "deny"
            if r.returncode != 0 or denied:
                raise Fail("the hook command fails on a benign %s call (exit %d%s): %s\n"
                           "  Registering it would block every tool call. Not registered." % (
                               tool, r.returncode, ", deny" if denied else "",
                               (r.stderr or r.stdout).strip()[:300]))
    spath = pjoin(proj, ".claude/settings.json")
    raw = read_bytes(spath)
    try:
        settings = json.loads(raw.decode("utf-8")) if raw else {}
    except ValueError as e:
        raise Fail(".claude/settings.json is not valid JSON (%s); fix it by hand first" % e)
    if not isinstance(settings, dict) or not isinstance(settings.get("hooks", {}), dict):
        raise Fail(".claude/settings.json: expected an object with a \"hooks\" object")
    before = json.dumps(settings, sort_keys=True)
    sh = settings.setdefault("hooks", {})
    for event, groups in hooks.items():
        if not isinstance(sh.get(event, []), list):
            raise Fail(".claude/settings.json: hooks.%s is not a list; fix it by hand first"
                       % event)
        kept = []
        for g in sh.get(event, []):
            if not isinstance(g, dict) or not isinstance(g.get("hooks", []), list):
                kept.append(g)
                continue
            hs = [h for h in g.get("hooks", [])
                  if not (isinstance(h, dict) and GUARD_MARK in str(h.get("command", "")))]
            if hs:
                g = dict(g)
                g["hooks"] = hs
                kept.append(g)
            elif not g.get("hooks"):
                kept.append(g)
        sh[event] = kept + [json.loads(json.dumps(g)) for g in groups]
    if json.dumps(settings, sort_keys=True) == before:
        rep.notes.append("guard: already registered in .claude/settings.json")
        return True
    write_bytes(spath, (json.dumps(settings, indent=2) + "\n").encode("utf-8"))
    rep.notes.append("guard: registered in .claude/settings.json (other keys kept). Now run the "
                     "two live probes in .claude/skills/careful/SKILL.md - a registered hook is "
                     "not evidence the host enforces it.")
    return True


def install_git_hook(proj, rep):
    """Point core.hooksPath at gates/hooks when that cannot displace an existing hook."""
    top = git(proj, "rev-parse", "--show-toplevel")
    if top is None:
        rep.warnings.append("git hook: not a git repository; run git init, then --install-git-hook")
        return False
    want = os.path.relpath(pjoin(proj, "gates/hooks"), top).replace(os.sep, "/")
    current = git(proj, "config", "--get", "core.hooksPath")
    manual = ("  Manual step: make your existing pre-commit hook also run ./gates/run-chain.sh "
              "(or move your hooks into gates/hooks/ and run: git config core.hooksPath %s)" % want)
    if current:
        if current.rstrip("/") == want:
            rep.notes.append("git hook: core.hooksPath already %s" % want)
            return True
        rep.warnings.append("git hook: NOT installed - core.hooksPath is already %r.\n%s"
                            % (current, manual))
        return False
    hooks_dir = git(proj, "rev-parse", "--git-path", "hooks")
    existing = []
    if hooks_dir:
        hd = hooks_dir if os.path.isabs(hooks_dir) else os.path.join(proj, hooks_dir)
        if os.path.isdir(hd):
            existing = sorted(f for f in os.listdir(hd) if not f.endswith(".sample"))
    if existing:
        rep.warnings.append("git hook: NOT installed - %s already holds %s, which core.hooksPath "
                            "would silently disable.\n%s"
                            % (hooks_dir, ", ".join(existing), manual))
        return False
    if git(proj, "config", "core.hooksPath", want) is None:
        rep.warnings.append("git hook: git config core.hooksPath %s failed" % want)
        return False
    rep.notes.append("git hook: core.hooksPath = %s (local to this clone: each clone runs "
                     "--install-git-hook once; CI is the check --no-verify cannot skip)" % want)
    return True


# ---------------------------------------------------------------------------- output

def print_report(kit, rep, mode, profile, dropped, old_commit=None, legacy=False):
    say("adopt.py %s  (kit %s at %s/%s, profile %s%s)" % (
        mode, kit.version, kit.rel, " @ " + kit.commit[:7] if kit.commit else "", profile,
        ", rules dropped: " + ", ".join(dropped) if dropped else ""))
    say("  installed %3d   unchanged %3d   replaced %3d   kept %3d   removed %3d" % (
        len(rep.installed), len(rep.unchanged), len(rep.replaced), len(rep.kept), len(rep.removed)))
    for n in rep.notes:
        say("  note  " + n)
    if legacy and rep.installed:
        # Review 2026-09-29: a legacy upgrade re-created a rule the adopter had deleted and
        # seeded a blank constitution beside a ratified one, visible only as "installed 17".
        say("  new in this project (it had no manifest, so the kit cannot tell what you removed "
            "on purpose):")
        for d in rep.installed:
            say("    " + d)
    for r in rep.removed:
        say("  removed  " + r)
    if rep.outdated:
        say("  %d kit-owned file(s) are unmodified but older than %s/ - run --upgrade to replace "
            "them (a .factory-new copy is next to each):" % (len(rep.outdated), kit.rel))
        for d in rep.outdated:
            say("    " + d)
    if rep.offered:
        say("")
        say("REVIEW  %d file(s) differ from what the kit would install; nothing was overwritten."
            % len(rep.offered))
        width = max(len(o[0]) for o in rep.offered)
        for d, why, _src in rep.offered:
            say("  %-*s  (%s)" % (width, d, why))
        say("  For each: diff -u <file> <file>.factory-new, merge what applies, delete the "
            ".factory-new.")
        changed = [src for _d, _w, src in rep.offered if src]
        if changed and old_commit and kit.commit and old_commit != kit.commit and kit.has_git:
            # The diff above mixes your fill (shown as removed) with the kit's change. This is
            # the kit's change alone.
            say("  What the kit itself changed in each (your own edits are not in it):")
            for src in sorted(set(changed)):
                say("    git -C %s diff %s..%s -- %s" % (kit.rel, old_commit[:12],
                                                          kit.commit[:12], src))
    for o in rep.orphans:
        say("  WARN  " + o)
    for w in rep.warnings:
        say("  WARN  " + w)


def next_steps(proj, kit):
    k = kit.rel
    spec = os.path.exists(pjoin(proj, ".specify/init-options.json"))
    settings = read_bytes(pjoin(proj, ".claude/settings.json")) or b""
    guard = GUARD_MARK.encode() in settings
    hooks_path = git(proj, "config", "--get", "core.hooksPath") or ""
    hook = hooks_path.rstrip("/").endswith("gates/hooks")
    ci = os.path.exists(pjoin(proj, ".github/workflows/factory-gates.yml"))
    phase0 = k + ("/model/PHASE-0.md" if kit.exists("model/PHASE-0.md") else "/AI-ONBOARDING.md")
    steps = [
        (spec, ["Spec Kit: uv tool install specify-cli==%s" % TESTED_SPECKIT,
                "specify init --here --force --non-interactive --integration claude",
                "(add --ignore-agent-tools if the claude CLI is not on PATH)"]),
        (None, ["Phase 0: %s - vision, archetype, stack, constitution;" % phase0,
                "the owner approves before any code"]),
        (None, ["fill .claude/CLAUDE.md and each .claude/rules/*.md; delete a rule that does",
                "not apply and re-run adopt.py (it offers your filled files that linked to",
                "it as .factory-new); --check lists what is still unfilled"]),
        (guard, ["adapt .claude/hooks/careful.json, first commit, create the remote,",
                 "then --register-guard"]),
        # adopt.py cannot observe the probes, so this step never shows [done] (review
        # 2026-09-29: "[done]" beside the probes was the registered-is-not-enforced confusion).
        (None, ["the careful skill's two live probes, in a fresh session - a registered",
                "hook is not evidence the host enforces it"]),
        (hook and ci, ["feature 001 (walking skeleton) wires gates/chain.conf, then",
                       "--install-git-hook --ci github; from then on no commit on red"]),
    ]
    say("")
    say("Next (%s/AI-ONBOARDING.md section 2; flags go to python3 %s/bin/adopt.py):" % (k, k))
    for i, (done, lines) in enumerate(steps, 1):
        say("  %d. %s%s" % (i, "[done] " if done else "", lines[0]))
        for more in lines[1:]:
            say("     " + more)
    say("Teammates and CI: git clone --recurse-submodules, or git submodule update --init;")
    say("an empty %s/ means every link into it is dead. Once feature 001 has installed the" % k)
    say("hook, each clone runs python3 %s/bin/adopt.py --install-git-hook once:" % k)
    say("core.hooksPath is per clone, and a clone without it never refuses a red commit.")


# ---------------------------------------------------------------------------- main

def parse_args(argv):
    # allow_abbrev=False: argparse otherwise ran `--upg` as --upgrade, the one step the careful
    # guard asks about, past a guard that matched the full spelling (review 2026-09-29).
    p = argparse.ArgumentParser(
        prog="adopt.py",
        allow_abbrev=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Install the AI Factory Kit into the project in the current directory, merge\n"
                    "it into an existing .claude/, upgrade it, or audit it. The kit is found from\n"
                    "this script's location and must live inside the project.",
        epilog="profiles (rules NOT installed):\n" + "\n".join(
            "  %-9s %s" % (k, ", ".join(v) or "(none)") for k, v in PROFILES.items()) +
        "\n\nNever overwrites a differing file (writes <file>.factory-new); never touches "
        "settings*.json\nexcept via --register-guard, nor Spec Kit's .claude/skills/speckit-*.\n"
        "Exit: 0 done, 1 failure or problems found, 2 usage error.")
    p.add_argument("--profile", choices=list(PROFILES), help="archetype profile (default: full, "
                   "or the one recorded at install)")
    p.add_argument("--without", metavar="RULES", help="comma-separated rules to leave out as well")
    p.add_argument("--install-git-hook", action="store_true",
                   help="install gates/hooks/pre-commit and point core.hooksPath at it when no "
                        "other hook would be displaced")
    p.add_argument("--ci", choices=["github"], help="install .github/workflows/factory-gates.yml "
                   "(never overwritten)")
    p.add_argument("--register-guard", action="store_true",
                   help="merge the careful hook into .claude/settings.json (idempotent)")
    p.add_argument("--upgrade", action="store_true",
                   help="replace unmodified kit-owned files with the current kit's, offer the "
                        "rest as .factory-new, then run --check")
    p.add_argument("--allow-downgrade", action="store_true",
                   help="with --upgrade: install from a kit OLDER than the one this project last "
                        "installed (a deliberate rollback; a stale submodule needs git submodule "
                        "update --init instead)")
    p.add_argument("--check", action="store_true",
                   help="audit only: manifest drift, links, frontmatter, line endings, "
                        "execute bits, placeholders, gates/chain.conf syntax")
    a = p.parse_args(argv)
    if a.check and (a.profile or a.without is not None or a.install_git_hook or a.ci
                    or a.register_guard or a.upgrade or a.allow_downgrade):
        p.error("--check writes nothing and takes no other option")
    if a.allow_downgrade and not a.upgrade:
        p.error("--allow-downgrade goes with --upgrade")
    return a


def main(argv):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    args = parse_args(argv)
    proj = os.getcwd()
    try:
        kit = Kit(KIT, proj)
        manifest = load_manifest(proj)
        if args.check:
            return run_check(proj, kit, manifest, args)
        return install(proj, kit, manifest, args)
    except Fail as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 2 if e.usage else 1


def install(proj, kit, manifest, args):
    mode = "upgrade" if args.upgrade else "install"
    behind = kit_behind(kit, manifest)
    if behind and not (args.upgrade and args.allow_downgrade):
        # Before anything is written: a plain run would also rewrite the manifest to the older
        # kit, and a teammate who committed that would record the downgrade for everyone.
        raise Fail("%s - %s" % (behind, behind_advice(kit)))
    top = git(proj, "rev-parse", "--show-toplevel")
    nested = top is not None and os.path.realpath(top) != os.path.realpath(proj)
    if nested and args.ci:
        sub = os.path.relpath(os.path.realpath(proj), os.path.realpath(top)).replace(os.sep, "/")
        raise Fail("--ci github: this project is %s/ inside the repository %s. GitHub reads "
                   "workflows only from the repository root's .github/workflows/, and the job's "
                   "./gates/run-chain.sh would not resolve from there, so an installed job would "
                   "never run. Copy %s/gates/ci/github-actions.yml to %s/.github/workflows/"
                   "factory-gates.yml by hand and add `defaults: run: working-directory: %s` to "
                   "its job. Nothing was written." % (sub, top, kit.rel, top, sub))
    legacy = manifest is None and os.path.isdir(pjoin(proj, ".claude")) and (
        os.path.exists(pjoin(proj, ".claude/hooks/check-careful.sh"))
        or os.path.exists(pjoin(proj, ".claude/HARNESS.md")))
    profile, without, dropped, notes = resolve_selection(args, kit, manifest, proj)
    files = dict((manifest or {}).get("files", {}))
    extras = recorded_extras(proj, files)
    if args.install_git_hook:
        extras.add("git-hook")
    if args.ci:
        extras.add("ci-github")
    if args.install_git_hook and not kit.exists("gates/hooks/pre-commit"):
        raise Fail("--install-git-hook: this kit has no gates/hooks/pre-commit")
    if args.ci and not kit.exists("gates/ci/github-actions.yml"):
        raise Fail("--ci github: this kit has no gates/ci/github-actions.yml")

    plan = build_plan(kit, dropped, extras)
    # Kit defects stop the run before anything is written.
    defects = []
    for it in plan:
        p = frontmatter_problem(it.dest, it.data) or cr_problem(it.dest, it.data)
        if p:
            defects.append("%s (from %s/%s): %s" % (it.dest, kit.rel, it.source, p))
    if defects:
        raise Fail("the kit would install broken files; nothing was written:\n  " +
                   "\n  ".join(defects))

    rep = Report()
    rep.notes.extend(notes)
    if legacy:
        rep.notes.append("pre-1.4.0 adoption (no manifest): every differing file is offered as "
                         ".factory-new; nothing is replaced this once")
    before_hooks = {}
    hd = pjoin(proj, ".claude/hooks")
    if os.path.isdir(hd):
        for f in os.listdir(hd):
            if os.path.isfile(os.path.join(hd, f)):
                before_hooks[f] = read_bytes(os.path.join(hd, f))

    ours = apply_plan(proj, kit, plan, files, mode, legacy, rep)
    handle_orphans(proj, plan, files, mode, dropped, rep)
    legacy_duplicate_hooks(proj, kit, mode, before_hooks, rep)
    ensure_gitattributes(proj, rep)
    if legacy:
        for d in rep.installed:
            m = re.match(r"^\.claude/rules/([^/]+)\.md$", d)
            if m:
                rep.warnings.append(
                    "%s was not in this project and is now installed. If you had dropped it, "
                    "delete it and re-run with your profile (--profile <p>, or --without %s): "
                    "a project with no manifest has no record of the profile" % (d, m.group(1)))
    if CONST_MEMORY in rep.installed:
        elsewhere = [c for c in ("constitution.md", "CONSTITUTION.md", "docs/constitution.md",
                                 ".specify/constitution.md") if os.path.isfile(pjoin(proj, c))]
        if elsewhere:
            rep.warnings.append(
                "seeded a blank %s (Version [X.Y.Z], which reads as 'not ratified'), but %s "
                "exists. If that is the ratified constitution, move it to %s: every harness link "
                "and every agent reads it there" % (CONST_MEMORY, " and ".join(elsewhere),
                                                     CONST_MEMORY))
    if nested:
        rep.warnings.append(
            "this project root is not the git repository's root (%s). The documented layout is "
            "one project per repository (model/SPEC-FLOW.md); --install-git-hook would set "
            "core.hooksPath for every commit in that whole repository" % top)

    new_manifest = {
        "kit_version": kit.version,
        "kit_commit": kit.commit,
        "kit_dir": kit.rel,
        "profile": profile,
        "without": without,
        "dropped_rules": dropped,
        "files": dict(sorted(files.items())),
    }
    mpath = pjoin(proj, MANIFEST)
    if read_bytes(mpath) != manifest_text(new_manifest):
        write_bytes(mpath, manifest_text(new_manifest))

    ok = not rep.failed
    if args.install_git_hook:
        ok = install_git_hook(proj, rep) and ok
    if args.ci:
        rep.notes.append("CI: .github/workflows/factory-gates.yml runs ./gates/run-chain.sh; the "
                         "runner must be able to fetch the %s/ submodule" % kit.rel)
    if args.register_guard:
        try:
            register_guard(proj, kit, rep)
        except Fail as e:
            rep.warnings.append("guard: NOT registered - %s" % e)
            ok = False

    state, detail = kit_vcs_state(proj, kit)
    if state == "embedded":
        rep.warnings.append(embedded_warning(proj, kit, detail))
    elif state == "symlink":
        rep.warnings.append("%s is a symlink: a teammate's clone gets a dangling link unless the "
                            "same path exists on their machine" % kit.rel)
    if os.path.exists(pjoin(proj, "AGENTS.md")):
        rep.warnings.append("AGENTS.md exists: with .claude/CLAUDE.md present Claude Code reads "
                            "CLAUDE.md instead of it by default. Add a line @../AGENTS.md to "
                            ".claude/CLAUDE.md to keep both.")
    print_report(kit, rep, mode, profile, dropped, (manifest or {}).get("kit_commit"), legacy)

    if mode == "upgrade":
        if any(d.startswith(".claude/hooks/") for d in rep.replaced + rep.installed) or any(
                o[0].startswith(".claude/hooks/") for o in rep.offered):
            say("  note  the guard changed: once every .factory-new under .claude/hooks/ is "
                "taken, run bash .claude/hooks/check-careful.test.sh, then the careful skill's "
                "two live probes")
        say("")
        return run_check(proj, kit, load_manifest(proj), args) or (0 if ok else 1)

    offered = set(o[0] + NEW for o in rep.offered)
    errors, warnings = audit_disk(proj, lambda d: d in ours or d in offered, kit)
    for w in warnings:
        say("  WARN  " + w)
    for e in errors:
        say("  FAIL  " + e)
    if errors:
        say("adopt: FAILED - %d problem(s) in what the kit installed" % len(errors))
        return 1
    say("  OK    links, frontmatter and line endings clean in everything the kit wrote")
    next_steps(proj, kit)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except BrokenPipeError:  # output piped into head: not a failure of the adoption
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)
