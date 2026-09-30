#!/usr/bin/env python3
"""check-specs.py - the one reader of the spec corpus behind three gates (from the AI Factory Kit).

    python3 gates/check-specs.py corpus   [specs-dir]  # doc-sync, spec-corpus mode (check-plan-sync.sh)
    python3 gates/check-specs.py approval [specs-dir]  # check-spec-approval.sh
    python3 gates/check-specs.py numbers  [specs-dir]  # check-spec-numbers.sh

You normally run it through those three wrappers; each carries its own BLIND TO block. It exists
as one file so that the three gates cannot disagree about what a spec says: one frontmatter
parser, one task-checkbox parser, one acceptance-record parser.

Formats it reads (the contract; model/SPEC-FLOW.md explains them for humans):

  specs/<id>/spec.md        YAML frontmatter at line 1: "---", then "key: value" lines, then "---".
                            Required: feature (= the directory name), status, epic. Once status
                            is not draft: approved_by, approved_on (YYYY-MM-DD). superseded adds
                            superseded_by: <id>. Inline "# comments" are stripped. No PyYAML:
                            nested YAML (indented lines, lists) is skipped, never interpreted.
  status                    draft | approved | accepted | released | superseded
                            (legacy "shipped" is read as accepted)
  specs/<id>/tasks.md       Spec Kit checklist lines "- [ ] T001 ..." / "- [x] T001 ..." ("[X]"
                            counts as checked; "*", "+" and "1." list markers count too). A line containing "(deferred ->" or "(deferred →"
                            does not block acceptance. Lines inside ``` fences and <!-- comments -->
                            are not tasks. Rows of the 1.3.x table ("| ✅ | M1-T1 |", "| ⬜ | …")
                            are read as tasks too, with a warning to convert them; a tasks.md
                            with no task in either format is red once status is past draft.
  [NEEDS CLARIFICATION …]   in spec.md, outside comments, fences and code spans: red in approval
                            mode once status is past draft (superseded excepted).
  specs/<id>/acceptance.md  "# Acceptance — <id>", then accepted_on, accepted_by, run_as and
                            "result: pass" as "key: value" lines. Required once status is
                            accepted, released or shipped.
  directory names           NNN-<name> (3+ digits) or YYYYMMDD-HHMMSS-<name> (Spec Kit --timestamp).

With no specs-dir argument a missing ./specs is "nothing to check yet" (exit 0): a fresh project
has no specs. A specs-dir you NAME that does not exist is a wiring error (exit 1).

Exit: 0 green (warnings allowed) · 1 red · 2 usage error.
Two-direction tests: check-plan-sync.test.sh, check-spec-approval.test.sh, check-spec-numbers.test.sh.
Python >= 3.8, standard library only.
"""
import datetime
import os
import re
import sys

for _stream in (sys.stdout, sys.stderr):
    # A Windows console or pipe may use a legacy code page: print "?" instead of crashing on the
    # marks below, which would turn a green run red for a reason unrelated to the specs.
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

STATUSES = ("draft", "approved", "accepted", "released", "superseded", "shipped")
DONE = ("accepted", "released", "shipped")
REQUIRED = ("feature", "status", "epic")

KEY_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)[ \t]*:(.*)$")
TASK_LINE = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+\[([ xX])\](?:[ \t]+(.*))?$")
TASK_ID = re.compile(r"\bT\d{3,}\b")
LEGACY_ID = re.compile(r"\bM\d+-T\d+\b")
DEFERRED = re.compile(r"\(deferred[ \t]*(?:→|->)", re.IGNORECASE)
FENCE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLACEHOLDER = re.compile(r"^(?:<[^>]*>|\[[^\]]*\]|tbd|todo|\?+|-+|none|n/?a)$", re.IGNORECASE)
NA_ALONE = re.compile(r"^n/?a[\s\-—–:,.(]*$", re.IGNORECASE)
SEQ_DIR = re.compile(r"^(\d{3,})-.+")
TS_DIR = re.compile(r"^(\d{8}-\d{6})-.+")
ACC_HEADING = re.compile(r"^#[ \t]+Acceptance\b[ \t]*[—–:-]*[ \t]*(\S*)")
ACC_KEYS = ("accepted_on", "accepted_by", "run_as", "result")
ACC_KEY_LINE = re.compile(r"^(accepted_on|accepted_by|run_as|result)[ \t]*:(.*)$")
# The 1.3.x task format: a status column of ✅/⬜ and an M<n>-T<n> id. Read as tasks (so an open
# ⬜ row still blocks acceptance and a ✅ row on a draft is still work ahead of approval) and
# reported, because only the checklist is the format Spec Kit writes. Review 2026-09-29: before
# this a migrated 1.3.x spec was "shipped" with an open ⬜ row and both gates were green.
LEGACY_ROW = re.compile("^[ \t]*\\|[ \t]*(\u2705|\u2b1c)[ \t]*\\|[ \t]*(M\\d+-T\\d+)\\b(.*)$")
# An open clarification Spec Kit's /speckit-specify leaves for /speckit-clarify to resolve.
CLARIFY = re.compile(r"\[NEEDS CLARIFICATION\b[^\]]*\]?", re.IGNORECASE)


class Spec(object):
    """One specs/<id>/ directory, parsed once."""

    def __init__(self, root, name):
        self.name = name
        self.dir = os.path.join(root, name)
        self.problems = []   # red
        self.warnings = []   # printed, not red
        self.meta = None     # dict when the frontmatter parsed
        self.has_spec = os.path.isfile(os.path.join(self.dir, "spec.md"))
        self.tasks = None    # list of (lineno, checked, deferred, text) when tasks.md exists
        self.legacy_rows = 0  # of those, rows in the 1.3.x ✅/⬜ table format
        self.clarify = []    # line numbers of open [NEEDS CLARIFICATION] markers in spec.md
        if self.has_spec:
            self.meta = self._frontmatter(os.path.join(self.dir, "spec.md"))
            body = self._read(os.path.join(self.dir, "spec.md"), "spec.md") if self.meta else None
            if body is not None:
                self.clarify = open_clarifications(body)
        tasks_path = os.path.join(self.dir, "tasks.md")
        if os.path.isfile(tasks_path):
            text = self._read(tasks_path, "tasks.md")
            if text is not None:
                self.tasks, self.legacy_rows = parse_tasks(text)

    # -- helpers -------------------------------------------------------------------------
    def _read(self, path, label):
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError as exc:
            self.problems.append("%s: cannot read (%s)" % (label, exc.strerror))
            return None
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            self.problems.append("%s: not valid UTF-8" % label)
            return None

    def _frontmatter(self, path):
        text = self._read(path, "spec.md")
        if text is None:
            return None
        if text.startswith("\ufeff"):
            self.warnings.append("spec.md starts with a UTF-8 byte-order mark; some frontmatter "
                                 "readers then miss the frontmatter - save it without the BOM")
            text = text[1:]
        lines = [ln.rstrip("\r") for ln in text.split("\n")]
        if not lines or lines[0].rstrip() != "---":
            where = misplaced_frontmatter(lines)
            if where:
                self.problems.append("spec.md: the frontmatter is not at line 1 (found at line %d) "
                                     "- move the '---' block to the very top, no comment or fence "
                                     "above it" % where)
            else:
                self.problems.append("spec.md: no frontmatter - line 1 must be '---', then "
                                     "feature/status/epic lines, then '---'")
            return None
        meta, seen = {}, set()
        for idx in range(1, len(lines)):
            line = lines[idx]
            lineno = idx + 1
            if line.rstrip() in ("---", "..."):
                return meta
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line[:1] in (" ", "\t") or line.startswith("- "):
                continue   # nested YAML / list item: not one of our scalar keys
            m = KEY_LINE.match(line)
            if not m:
                self.problems.append("spec.md line %d: %r is not a 'key: value' line" % (lineno, line))
                continue
            key, rest = m.group(1), m.group(2)
            if rest and rest[:1] not in (" ", "\t"):
                self.problems.append("spec.md line %d: %r - YAML needs a space after the colon"
                                     % (lineno, line))
                continue
            value = yaml_scalar(rest)
            if value is None:
                self.problems.append("spec.md line %d: unterminated quote in %r" % (lineno, line))
                continue
            if key in seen:
                self.problems.append("spec.md line %d: duplicate key %r - which one is true?"
                                     % (lineno, key))
                continue
            seen.add(key)
            meta[key] = value
        self.problems.append("spec.md: the frontmatter opened at line 1 is never closed with '---'")
        return None

    def status(self):
        return (self.meta or {}).get("status", "")

    def counts(self):
        """(checked, open_blocking, open_deferred, open_ids)"""
        checked, blocking, deferred, ids = 0, 0, 0, []
        for lineno, is_checked, is_deferred, text in self.tasks or []:
            if is_checked:
                checked += 1
            elif is_deferred:
                deferred += 1
            else:
                blocking += 1
                tid = TASK_ID.search(text or "") or LEGACY_ID.search(text or "")
                ids.append(tid.group(0) if tid else "line %d" % lineno)
        return checked, blocking, deferred, ids


def yaml_scalar(rest):
    """The value part of a 'key: value' line: quotes honoured, inline '# comment' stripped."""
    s = rest.strip()
    if s[:1] in ("'", '"'):
        end = s.find(s[0], 1)
        if end == -1:
            return None
        tail = s[end + 1:].strip()
        if tail and not tail.startswith("#"):
            return None
        return s[1:end].strip()
    if s.startswith("#"):
        return ""
    m = re.search(r"[ \t]#", s)
    if m:
        s = s[:m.start()]
    return s.strip()


def misplaced_frontmatter(lines):
    """Line number of a frontmatter-looking block that is not at line 1, else 0."""
    for idx, line in enumerate(lines[:60]):
        stripped = line.strip()
        if stripped in ("---", "```yaml", "```yml") and idx > 0:
            window = lines[idx + 1:idx + 8]
            if any(re.match(r"^(feature|status|epic)[ \t]*:", w) for w in window):
                return idx + 1
    return 0


def strip_comments(text):
    """Blank out <!-- ... --> spans, keeping line numbers."""
    return re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)


def parse_tasks(text):
    """([(lineno, checked, deferred, text)], number of those in the 1.3.x table format)."""
    out, fence, legacy = [], None, 0
    for idx, line in enumerate(strip_comments(text).split("\n")):
        line = line.rstrip("\r")
        f = FENCE.match(line)
        if f:
            mark = f.group(1)[0]
            if fence is None:
                fence = mark
            elif fence == mark:
                fence = None
            continue
        if fence:
            continue
        m = TASK_LINE.match(line)
        if m:
            text_part = m.group(2) or ""
            out.append((idx + 1, m.group(1) in ("x", "X"), bool(DEFERRED.search(text_part)),
                        text_part))
            continue
        m = LEGACY_ROW.match(line)
        if m:
            legacy += 1
            text_part = m.group(2) + m.group(3)
            out.append((idx + 1, m.group(1) == "\u2705", bool(DEFERRED.search(text_part)),
                        text_part))
    return out, legacy


def open_clarifications(text):
    """Line numbers of [NEEDS CLARIFICATION ...] markers outside comments, fences and code spans."""
    out, fence = [], None
    for idx, line in enumerate(strip_comments(text).split("\n")):
        f = FENCE.match(line)
        if f:
            mark = f.group(1)[0]
            fence = mark if fence is None else (None if fence == mark else fence)
            continue
        if fence:
            continue
        if CLARIFY.search(re.sub(r"`[^`]*`", "", line)):
            out.append(idx + 1)
    return out


def is_placeholder(value):
    return (not value) or bool(PLACEHOLDER.match(value.strip()))


def parse_date(value):
    if not value or not DATE.match(value):
        return None
    try:
        return datetime.date(int(value[0:4]), int(value[5:7]), int(value[8:10]))
    except ValueError:
        return None


def plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


# ------------------------------------------------------------------------------ corpus scan

def load(specs_dir):
    names = sorted(n for n in os.listdir(specs_dir)
                   if not n.startswith(".") and os.path.isdir(os.path.join(specs_dir, n)))
    return [Spec(specs_dir, n) for n in names]


def check_corpus(specs):
    """Structure + task/status consistency. Returns (problems, warnings, summary)."""
    problems, warnings = [], []
    by_status, checked_all, total_all, deferred_all = {}, 0, 0, 0
    names = set(s.name for s in specs)
    for s in specs:
        p = lambda msg, s=s: problems.append("%s/%s" % (s.name, msg))
        w = lambda msg, s=s: warnings.append("%s/%s" % (s.name, msg))
        if not s.has_spec:
            p(": no spec.md - a feature directory holds its spec; move anything else out of specs/")
            continue
        for msg in s.problems:
            p(msg)
        for msg in s.warnings:
            w(msg)
        if s.meta is None:
            continue
        for key in REQUIRED:
            if not s.meta.get(key):
                p("spec.md: frontmatter has no %s:" % key)
            elif key != "status" and is_placeholder(s.meta[key]):
                p("spec.md: %s: is still a placeholder (%r)" % (key, s.meta[key]))
        feature, status = s.meta.get("feature", ""), s.meta.get("status", "")
        if feature and feature != s.name:
            p("spec.md: feature: %s does not match the directory name %s" % (feature, s.name))
        if status and status not in STATUSES:
            hint = " (lowercase: %s)" % status.lower() if status.lower() in STATUSES else ""
            p("spec.md: unknown status %r%s - one of %s" % (status, hint, " | ".join(STATUSES[:5])))
        if status == "superseded":
            by = s.meta.get("superseded_by", "")
            if not by:
                p("spec.md: status is superseded but there is no superseded_by: <id>")
            elif by not in names:
                p("spec.md: superseded_by: %s names no directory under specs/" % by)
        by_status[status or "?"] = by_status.get(status or "?", 0) + 1
        checked, blocking, deferred, ids = s.counts()
        total = checked + blocking + deferred
        if s.legacy_rows:
            msg = ("tasks.md: %s in the 1.3.x table format (| \u2705 | M1-T1 |) - read as tasks here, "
                   "but Spec Kit and this kit write '- [ ] T001' checklist lines: convert them "
                   "(GATES.md section 7, 'Upgrading from 1.3.x')" % plural(s.legacy_rows, "row"))
            w(msg)
        if s.tasks is not None and not s.tasks and status not in ("draft", "superseded", ""):
            p("tasks.md: holds no task at all ('- [ ] T001 ...' lines) while status is %s - a "
              "tasks file in another format is invisible to this gate, so it cannot tell whether "
              "the work is done. Convert it, or delete an empty tasks.md" % status)
        checked_all += checked
        total_all += total
        deferred_all += deferred
        if status in DONE and blocking:
            shown = ", ".join(ids[:5]) + (", ..." if len(ids) > 5 else "")
            p("tasks.md: status is %s but %s still open (%s) - finish it, mark it "
              "'(deferred -> <where>)', or set status back to approved"
              % (status, "1 task is" if blocking == 1 else "%d tasks are" % blocking, shown))
        if status in ("draft", "approved") and checked and not blocking:
            w("tasks.md: every task is checked%s but status is still %s - once the acceptance run "
              "is recorded in acceptance.md, set status: accepted"
              % (" or deferred" if deferred else "", status))
    order = [st for st in STATUSES if st in by_status] + sorted(
        st for st in by_status if st not in STATUSES)
    summary = "%s (%s); %d/%d tasks checked%s" % (
        plural(len(specs), "spec"),
        ", ".join("%s %d" % (st, by_status[st]) for st in order) or "none parsed",
        checked_all, total_all,
        ", %d deferred" % deferred_all if deferred_all else "")
    return problems, warnings, summary


def check_approval(specs):
    """Approval and acceptance records. Returns (problems, warnings, summary)."""
    problems, warnings = [], []
    tally = {"draft": 0, "approved": 0, "done": 0, "superseded": 0}
    for s in specs:
        p = lambda msg, s=s: problems.append("%s/%s" % (s.name, msg))
        if not s.has_spec:
            p(": no spec.md, so no status - this gate cannot tell whether work here was approved")
            continue
        if s.meta is None:
            why = re.sub(r"^spec\.md(?: line \d+)?: ", "", s.problems[0]) if s.problems else "?"
            p("spec.md: cannot read the status (%s)" % why)
            continue
        if s.problems:
            # A duplicate key, a malformed line, an unreadable tasks.md: the status or the task
            # count this gate would act on is not trustworthy, so it fails closed.
            for msg in s.problems:
                p(msg)
            continue
        status = s.status()
        if status not in STATUSES:
            p("spec.md: %s - this gate cannot tell what was approved" % (
                "no status:" if not status else "status %r is not one of %s"
                % (status, " | ".join(STATUSES[:5]))))
            continue
        checked, blocking, deferred, ids = s.counts()
        if status == "draft":
            tally["draft"] += 1
            if checked:
                p("tasks.md: %s checked while status is draft - no implementation before the owner "
                  "approves the spec (HARD-GATE). Get the approval, then record status: approved, "
                  "approved_by and approved_on" % plural(checked, "task"))
            continue
        if s.clarify and status != "superseded":
            shown = ", ".join(str(n) for n in s.clarify[:5]) + (", ..." if len(s.clarify) > 5 else "")
            p("spec.md: status is %s but %s still open (line %s) - an approved spec answers "
              "its questions first: resolve them (/speckit-clarify) and date the answers in "
              "Clarifications, or set status back to draft" % (
                  status, "1 [NEEDS CLARIFICATION] marker is" if len(s.clarify) == 1
                  else "%d [NEEDS CLARIFICATION] markers are" % len(s.clarify), shown))
        by, on = s.meta.get("approved_by", ""), s.meta.get("approved_on", "")
        if is_placeholder(by):
            p("spec.md: status is %s but approved_by is %s" % (
                status, "missing" if not by else "a placeholder (%r)" % by))
        approved = parse_date(on)
        if not on:
            p("spec.md: status is %s but approved_on is missing (YYYY-MM-DD)" % status)
        elif approved is None:
            p("spec.md: approved_on %r is not a YYYY-MM-DD date" % on)
        if status == "superseded":
            tally["superseded"] += 1
            continue
        if status == "approved":
            tally["approved"] += 1
            continue
        tally["done"] += 1
        for msg in acceptance_problems(s, status, approved):
            p(msg)
    summary = "%s: %d draft, %d approved, %d accepted/released with acceptance.md, %d superseded" % (
        plural(len(specs), "spec"), tally["draft"], tally["approved"], tally["done"],
        tally["superseded"])
    return problems, warnings, summary


def acceptance_problems(s, status, approved):
    path = os.path.join(s.dir, "acceptance.md")
    if not os.path.isfile(path):
        return ["acceptance.md: missing - status %s needs the record of an acceptance run by "
                "someone other than the builder (GATES.md section 3)" % status]
    try:
        with open(path, "rb") as fh:
            text = fh.read().decode("utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return ["acceptance.md: unreadable or not valid UTF-8"]
    out, found, heading = [], {}, None
    fence = None
    for idx, line in enumerate(strip_comments(text).split("\n")):
        line = line.rstrip("\r")
        f = FENCE.match(line)
        if f:
            mark = f.group(1)[0]
            fence = mark if fence is None else (None if fence == mark else fence)
            continue
        if fence:
            continue
        h = ACC_HEADING.match(line)
        if h and heading is None:
            heading = h.group(1)
            continue
        m = ACC_KEY_LINE.match(line)
        if m:
            key = m.group(1)
            if key in found:
                out.append("acceptance.md line %d: duplicate %s: - which one is true?" % (idx + 1, key))
                continue
            found[key] = m.group(2).strip()
    if heading is None:
        out.append("acceptance.md: no '# Acceptance — %s' heading" % s.name)
    elif heading != s.name:
        out.append("acceptance.md: the heading names %r, not %s - copied from another spec?"
                   % (heading, s.name))
    for key in ACC_KEYS:
        if key not in found:
            out.append("acceptance.md: no %s: line" % key)
    if "accepted_on" in found:
        acc = parse_date(found["accepted_on"])
        if acc is None:
            out.append("acceptance.md: accepted_on %r is not a YYYY-MM-DD date" % found["accepted_on"])
        elif approved is not None and acc < approved:
            out.append("acceptance.md: accepted_on %s is before approved_on %s"
                       % (found["accepted_on"], approved.isoformat()))
    if "accepted_by" in found and is_placeholder(found["accepted_by"]):
        out.append("acceptance.md: accepted_by is empty or a placeholder (%r)" % found["accepted_by"])
    if "run_as" in found:
        run_as = found["run_as"]
        if NA_ALONE.match(run_as):
            out.append("acceptance.md: run_as %r needs its reason, e.g. "
                       "'n/a — no authorization boundary'" % run_as)
        elif is_placeholder(run_as):
            out.append("acceptance.md: run_as is empty or a placeholder (%r)" % run_as)
    if "result" in found and found["result"] != "pass":
        out.append("acceptance.md: result is %r, not pass" % found["result"])
    return out


def check_numbers(specs_dir):
    problems, seq, ts = [], {}, {}
    names = sorted(n for n in os.listdir(specs_dir)
                   if not n.startswith(".") and os.path.isdir(os.path.join(specs_dir, n)))
    for n in names:
        m = TS_DIR.match(n)
        if m:
            ts.setdefault(m.group(1), []).append(n)
            continue
        m = SEQ_DIR.match(n)
        if m:
            seq.setdefault(int(m.group(1)), []).append(n)
            continue
        problems.append("%s: not an NNN-<name> or YYYYMMDD-HHMMSS-<name> directory - the roadmap "
                        "sorts by that prefix; rename it or move it out of specs/" % n)
    for key, group in sorted(seq.items()):
        if len(group) > 1:
            problems.append("number %03d is used by %s - parallel branches each took the next "
                            "number and git merged both without a conflict. Renumber the later one "
                            "(git mv, then its feature: line); use timestamp numbering while "
                            "several branches create specs" % (key, " and ".join(group)))
    for key, group in sorted(ts.items()):
        if len(group) > 1:
            problems.append("timestamp %s is used by %s - rename one" % (key, " and ".join(group)))
    summary = "%d spec %s (%d sequential, %d timestamp)" % (
        len(names), "directory" if len(names) == 1 else "directories",
        sum(len(g) for g in seq.values()), sum(len(g) for g in ts.values()))
    return problems, [], summary


# ------------------------------------------------------------------------------ main

HEADLINE = {
    "corpus": ("Specs in sync", "SPEC DRIFT - the specs disagree with their own tasks and names:"),
    "approval": ("Spec approvals recorded", "SPEC APPROVAL - work ran ahead of its approval or acceptance record:"),
    "numbers": ("Spec numbers unique", "SPEC NUMBERS - two specs share an identity, or a directory has none:"),
}


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help") or argv[1] not in HEADLINE:
        sys.stdout.write(__doc__)
        return 0 if len(argv) > 1 and argv[1] in ("-h", "--help") else 2
    mode = argv[1]
    if len(argv) > 3:
        print("usage: check-specs.py %s [specs-dir]" % mode)
        return 2
    named = len(argv) == 3
    specs_dir = argv[2] if named else "specs"
    if not os.path.isdir(specs_dir):
        if named:
            print("❌ specs dir not found: %r - check the argument you wired into the gate chain"
                  % specs_dir)
            return 1
        print("✅ nothing to check yet (no specs/)")
        return 0
    if mode == "numbers":
        problems, warnings, summary = check_numbers(specs_dir)
    else:
        specs = load(specs_dir)
        if not specs:
            print("✅ nothing to check yet (%s holds no feature directories)" % specs_dir)
            return 0
        problems, warnings, summary = (check_corpus if mode == "corpus" else check_approval)(specs)
    for w in warnings:
        print("⚠️  %s" % w)
    ok, bad = HEADLINE[mode]
    if problems:
        print("❌ %s" % bad)
        for msg in problems:
            print("   • %s" % msg)
        return 1
    print("✅ %s - %s" % (ok, summary))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
