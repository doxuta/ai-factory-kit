#!/usr/bin/env python3
"""Relative-link checker for Markdown: every relative link must resolve on disk.

Usage:  python3 bin/check-links.py <root>...     (a root is a directory or a single file)
Exit:   0 every relative link resolves; 1 at least one dead link; 2 usage error

Checks files named *.md, *.md.template and *.md.factory-new. bin/adopt.py imports this file
for its post-install check and for --check; the kit's CI runs it on the kit root.

Why it exists: the kit says broken cross-links are bugs, and until v1.4.0 the only checker
lived inside adopt.py and looked at .claude/ alone. The adopted constitution had 9 of 9 links
dead (.specify/memory/ was never checked). An adopter who deleted the two rules that did not
fit their project was left with 6 dead links, and the only checker was a function inside a
script that refused to run a second time. A checker nobody can run on its own runs once.

BLIND TO - what a green run does NOT prove:
  - #anchors and ?queries: the file must exist; the heading inside it is not checked.
  - Links inside inline code spans, fenced code blocks and a YAML frontmatter block at the top
    of the file: they are not links once rendered, so they are skipped.
  - External links (http:, https:, mailto:, any other scheme, //host) and site-absolute /paths.
  - Raw HTML (<a href>, <img src>), links split across lines, and bare paths in prose or in
    HTML comments ("I POINT TO: ../HARNESS.md" is text, not a link).
  - Prose section references ("GATES section 4"): only the file part of a link is checked.
  - Directories named .git, node_modules, __pycache__, .venv and venv, and Claude Code's
    worktree checkouts under .claude/worktrees/, are not walked.
A dead link whose case differs from the file on disk IS reported: it resolves on macOS and
Windows and dies on a Linux CI runner.
"""
import os
import re
import sys
from urllib.parse import unquote

MD_SUFFIXES = (".md", ".md.template", ".md.factory-new")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}

# [text](target) and ![alt](target), with an optional "title". The text may hold one level of
# nested brackets. Code spans are masked to NUL before this runs, so `]` inside code is inert.
INLINE = re.compile(
    r"(?P<bang>!?)\[(?P<text>(?:[^\[\]\n]|\[[^\[\]\n]*\])*)\]"
    r"\((?P<pre>[ \t]*)(?P<target><[^<>\n]*>|[^\s()<>]*(?:\([^\s()]*\)[^\s()<>]*)*)"
    r"(?P<title>[ \t]+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^()\n]*\)))?[ \t]*\)"
)
# [label]: target   (a reference definition, up to three spaces of indent)
REFDEF = re.compile(r"^(?P<lead> {0,3}\[[^\]\n]+\]:[ \t]*)(?P<target><[^<>\n]*>|\S+)", re.M)
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def _mask_spans(line):
    """Replace inline code spans (backtick runs and their content) with NUL, same length."""
    out = list(line)
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if c == "\\":
            i += 2
            continue
        if c != "`":
            i += 1
            continue
        j = i
        while j < n and line[j] == "`":
            j += 1
        run, k, close = j - i, j, -1
        while k < n:
            if line[k] != "`":
                k += 1
                continue
            e = k
            while e < n and line[e] == "`":
                e += 1
            if e - k == run:
                close = e
                break
            k = e
        if close < 0:  # an unmatched run is literal text
            i = j
            continue
        for x in range(i, close):
            out[x] = "\0"
        i = close
    return "".join(out)


def mask_code(text):
    """Return `text` with frontmatter, fenced code and inline code spans replaced by NUL.

    Same length, newlines kept, so every offset into the result is an offset into `text`.
    """
    lines = text.split("\n")
    # Frontmatter only when a closing fence exists; a lone leading "---" is a thematic break.
    front = lines[0].rstrip() == "---" and any(l.rstrip() in ("---", "...") for l in lines[1:])
    out, fence = [], None
    for i, line in enumerate(lines):
        if front:  # YAML frontmatter: data for a loader, not rendered Markdown
            if i > 0 and line.rstrip() in ("---", "..."):
                front = False
            out.append("\0" * len(line))
            continue
        if fence:
            m = FENCE_CLOSE.match(line)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1]:
                fence = None
            out.append("\0" * len(line))
            continue
        m = FENCE_OPEN.match(line)
        if m:
            fence = (m.group(1)[0], len(m.group(1)))
            out.append("\0" * len(line))
            continue
        out.append(_mask_spans(line))
    return "\n".join(out)


class Link(object):
    """One link occurrence. Offsets index the original text."""

    __slots__ = ("start", "end", "tstart", "tend", "text", "target", "line", "ref", "image")

    def __init__(self, start, end, tstart, tend, text, target, line, ref, image):
        self.start, self.end, self.tstart, self.tend = start, end, tstart, tend
        self.text, self.target, self.line, self.ref, self.image = text, target, line, ref, image


def find_links(text):
    """Every inline link, image and reference definition outside code, in document order."""
    masked = mask_code(text)
    found = []
    for m in INLINE.finditer(masked):
        bracket = m.start() + len(m.group("bang"))
        if bracket > 0 and masked[bracket - 1] == "\\":
            continue  # \[ is an escaped bracket, not a link
        found.append(Link(m.start(), m.end(), m.start("target"), m.end("target"),
                          text[m.start("text"):m.end("text")], m.group("target"),
                          text.count("\n", 0, m.start()) + 1, False, bool(m.group("bang"))))
    for m in REFDEF.finditer(masked):
        found.append(Link(m.start(), m.end(), m.start("target"), m.end("target"), "",
                          m.group("target"), text.count("\n", 0, m.start()) + 1, True, False))
    found.sort(key=lambda l: l.start)
    return found


def local_path(target):
    """The filesystem part of a relative link target, or None when there is nothing to check."""
    raw = target[1:-1] if target.startswith("<") and target.endswith(">") else target
    if not raw or raw.startswith(("#", "/")) or SCHEME.match(raw):
        return None
    path = re.split(r"[#?]", raw, 1)[0]
    return unquote(path) if path else None


def exists_exact(path, cache):
    """os.path.exists, but every component must match the directory listing's case too."""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return False
    parent, name = os.path.split(path)
    while name:
        if parent not in cache:
            try:
                cache[parent] = set(os.listdir(parent))
            except OSError:
                cache[parent] = None
        entries = cache[parent]
        if entries is not None and name not in entries:
            return False
        parent, name = os.path.split(parent)
    return True


def check_text(text, base_dir, cache=None):
    """Dead relative links in `text`, resolved against `base_dir`: [(line, target, why)]."""
    cache = {} if cache is None else cache
    dead = []
    for link in find_links(text):
        path = local_path(link.target)
        if path is None:
            continue
        full = os.path.normpath(os.path.join(base_dir, path))
        if exists_exact(full, cache):
            continue
        why = "case differs from the file on disk" if os.path.exists(full) else "no such file"
        dead.append((link.line, link.target, why))
    return dead


def check_file(path, cache=None):
    """Dead relative links in one file: [(line, target, why)]."""
    with open(path, "rb") as fh:
        text = fh.read().decode("utf-8", "replace")
    return check_text(text, os.path.dirname(os.path.abspath(path)), cache)


def is_markdown(name):
    return name.endswith(MD_SUFFIXES)


def markdown_files(root):
    """Every Markdown file under `root` (or `root` itself), sorted, skipping SKIP_DIRS."""
    if os.path.isfile(root):
        return [root] if is_markdown(root) else []
    out = []
    for dirpath, dirs, files in os.walk(root):
        keep = []
        for d in dirs:
            if d in SKIP_DIRS:
                continue
            if d == "worktrees" and os.path.basename(dirpath) == ".claude":
                continue
            keep.append(d)
        dirs[:] = sorted(keep)
        out.extend(os.path.join(dirpath, f) for f in sorted(files) if is_markdown(f))
    return out


def count_links(path):
    with open(path, "rb") as fh:
        text = fh.read().decode("utf-8", "replace")
    return sum(1 for l in find_links(text) if local_path(l.target) is not None)


def check(roots):
    """Returns (dead, files_checked, links_checked); dead is [(file, line, target, why)]."""
    cache, dead, nfiles, nlinks = {}, [], 0, 0
    for root in roots:
        for path in markdown_files(root):
            nfiles += 1
            nlinks += count_links(path)
            dead.extend((path, line, target, why) for line, target, why in check_file(path, cache))
    return dead, nfiles, nlinks


def main(argv):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if not argv:
        print("usage: python3 check-links.py <root>...", file=sys.stderr)
        return 2
    missing = [r for r in argv if not os.path.exists(r)]
    if missing:
        for r in missing:
            print("check-links: no such file or directory: %s" % r, file=sys.stderr)
        return 2
    dead, nfiles, nlinks = check(argv)
    for path, line, target, why in dead:
        print("%s:%d: dead link -> %s (%s)" % (os.path.relpath(path), line, target, why))
    print("check-links: %d file(s), %d relative link(s), %d dead" % (nfiles, nlinks, len(dead)))
    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
