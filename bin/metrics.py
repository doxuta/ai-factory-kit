#!/usr/bin/env python3
"""metrics.py - the numbers model/LEVELS.md calls "the measure that matters", as far as git can
honestly supply them (from the AI Factory Kit).

    python3 factory/bin/metrics.py [--window N] [--since YYYY-MM-DD] [--specs DIR] [--json]

Run it from the project root. It reads `git log` of HEAD (merge commits skipped, oldest first,
topological order) and the frontmatter of specs/*/spec.md. It depends on the commit trailers
defined in gates/GATES.md section 10:

    Spec: 012-payment-qr          on every commit that implements, fixes or amends a spec
                                  (repeat the line for a commit that touches two specs)
    Bug-class: escaped-joint      on the fix commit for a "both ends correct, connection
                                  missing" bug that got past the gates (GATES.md section 4)

It prints four numbers:

  1. Trailer coverage     - non-merge commits that carry a Spec: trailer. Printed first because
                            every number below rests on it.
  2. First-pass land rate - of the feat commits carrying Spec: X, the share NOT followed, within
                            the next N commits (default 10), by a fix or revert commit carrying the
                            same Spec: X. The corrected ones are listed.
  3. Escaped joints       - fix commits carrying Bug-class: escaped-joint, per spec.
  4. Approval latency     - per spec, days from the commit that added specs/<id>/spec.md to its
                            approved_on. A PROXY for owner review time, not the thing itself.

BLIND TO (a number is evidence only of what it counts):
  * COMMITS WITHOUT THE TRAILER. A correction that forgets "Spec:" is invisible, so the land
    rate goes UP when discipline goes down. Read coverage before the rate.
  * SQUASHES AND REWRITTEN HISTORY. A branch squashed into one commit shows its corrections as
    nothing; a rebase reorders what "within N commits" means.
  * THE WINDOW. N commits is arbitrary. A fix 11 commits later is a first-pass land at N=10.
    And one fix counts against every feat of the same spec inside its window: two landings
    followed by one fix are two corrections, even if the fix repaired only one of them.
  * CORRECTIONS UNDER ANOTHER TYPE. A "refactor" or "chore" that repairs a feature is not
    counted; only fix and revert (conventional type, or git's own "Revert ..." subject) are.
  * CLASSIFICATION. Escaped joints are self-reported by whoever writes the fix commit; zero
    means "none reported", not "none happened".
  * REVIEW TIME. git cannot see how long the owner read. Approval latency includes waiting,
    weekends and batching; a spec committed only after approval shows 0 days or less and is
    reported as not measurable.
  * BRANCHES OTHER THAN HEAD, and merge commits (skipped).

A report, not a gate: exit 0 whatever the numbers; 2 when this is not a git repository or git
fails. Python >= 3.8, standard library only. Test: bin/metrics.test.sh.
"""
import argparse
import datetime
import json
import os
import re
import statistics
import subprocess
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

TYPE_RX = re.compile(r"^([a-z]+)(?:\([^)]*\))?!?:\s")
TRAILER_RX = re.compile(r"^([A-Za-z0-9][A-Za-z0-9-]*):[ \t]*(.*?)[ \t]*$")
REC, UNIT = "\x1e", "\x1f"


def git(*args):
    try:
        out = subprocess.run(["git"] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        raise SystemExit("metrics: cannot run git (%s)" % exc)
    if out.returncode != 0:
        return None
    return out.stdout.decode("utf-8", "replace")


def trailers(body):
    """Trailer lines of a commit message: its last paragraph, if every line there is Key: value."""
    paras = [p for p in re.split(r"\n[ \t]*\n", body.strip()) if p.strip()]
    if len(paras) < 2:
        return []
    out = []
    for line in paras[-1].splitlines():
        m = TRAILER_RX.match(line.strip())
        if not m:
            return []
        out.append((m.group(1).lower(), m.group(2)))
    return out


def commit_type(subject):
    if subject.startswith('Revert "'):
        return "revert"
    m = TYPE_RX.match(subject)
    return m.group(1) if m else ""


def load_commits(since):
    args = ["log", "--no-merges", "--topo-order", "--reverse",
            "--format=%H" + UNIT + "%aI" + UNIT + "%s" + UNIT + "%B" + REC]
    if since:
        args.append("--since=%s" % since)
    raw = git(*args)
    if raw is None:
        return None
    commits = []
    for rec in raw.split(REC):
        rec = rec.strip("\n")
        if not rec:
            continue
        sha, date, subject, body = (rec.split(UNIT) + ["", "", ""])[:4]
        tr = trailers(body)
        specs = [v for k, v in tr if k == "spec" and v]
        classes = [v.lower() for k, v in tr if k == "bug-class"]
        commits.append({"sha": sha, "date": date, "subject": subject, "type": commit_type(subject),
                        "specs": specs, "bug_classes": classes})
    return commits


def land_rate(commits, window):
    landed, corrected = 0, []
    for i, c in enumerate(commits):
        if c["type"] != "feat":
            continue
        for spec in c["specs"]:
            landed += 1
            for distance, later in enumerate(commits[i + 1:i + 1 + window], 1):
                if later["type"] in ("fix", "revert") and spec in later["specs"]:
                    corrected.append({"spec": spec, "feat": c["sha"][:7], "feat_subject": c["subject"],
                                      "fix": later["sha"][:7], "fix_subject": later["subject"],
                                      "distance": distance})
                    break
    return landed, corrected


def frontmatter(path):
    try:
        with open(path, encoding="utf-8-sig") as fh:
            lines = fh.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    meta = {}
    for line in lines[1:]:
        if line.strip() in ("---", "..."):
            return meta
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):[ \t]+(.*)$", line)
        if m:
            value = re.sub(r"(^|[ \t])#.*$", "", m.group(2)).strip().strip("'\"")
            meta.setdefault(m.group(1), value)
    return {}


def approval_latency(specs_dir):
    rows = []
    if not os.path.isdir(specs_dir):
        return rows
    for name in sorted(os.listdir(specs_dir)):
        path = os.path.join(specs_dir, name, "spec.md")
        if not os.path.isfile(path):
            continue
        on = frontmatter(path).get("approved_on", "")
        added = git("log", "--follow", "--diff-filter=A", "--format=%aI", "--", path)
        first = added.strip().splitlines()[-1] if added and added.strip() else ""
        row = {"spec": name, "created": first[:10], "approved_on": on, "days": None}
        try:
            created = datetime.date.fromisoformat(first[:10])
            approved = datetime.date.fromisoformat(on)
        except ValueError:
            rows.append(row)
            continue
        days = (approved - created).days
        row["days"] = days if days > 0 else None
        rows.append(row)
    return rows


def main(argv):
    ap = argparse.ArgumentParser(prog="metrics.py", description="First-pass land rate, escaped "
                                 "joints and approval latency from git (see the module docstring).")
    ap.add_argument("--window", type=int, default=10, help="commits after a feat in which a fix "
                    "with the same Spec: counts as its correction (default 10)")
    ap.add_argument("--since", help="only commits after this date (passed to git log --since)")
    ap.add_argument("--specs", default="specs", help="spec directory (default: specs)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv[1:])
    if args.window < 1:
        ap.error("--window must be at least 1")

    head = git("rev-parse", "--short", "HEAD")
    if head is None:
        sys.stderr.write("metrics: not a git repository with at least one commit\n")
        return 2
    commits = load_commits(args.since)
    if commits is None:
        sys.stderr.write("metrics: git log failed\n")
        return 2

    with_spec = [c for c in commits if c["specs"]]
    landed, corrected = land_rate(commits, args.window)
    escaped = {}
    for c in commits:
        if c["type"] == "fix" and "escaped-joint" in c["bug_classes"]:
            for spec in c["specs"] or ["(no Spec: trailer)"]:
                escaped[spec] = escaped.get(spec, 0) + 1
    latency = approval_latency(args.specs)
    measured = [r["days"] for r in latency if r["days"] is not None]

    result = {
        "head": head.strip(), "window": args.window, "since": args.since,
        "commits": len(commits), "commits_with_spec": len(with_spec),
        "feat_landings": landed, "corrected": corrected,
        "first_pass_land_rate": (landed - len(corrected)) / landed if landed else None,
        "escaped_joints": escaped,
        "approval_latency": latency,
        "approval_latency_median_days": statistics.median(measured) if measured else None,
    }
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    def pct(a, b):
        return "%d/%d (%d%%)" % (a, b, round(100.0 * a / b)) if b else "%d/%d" % (a, b)

    print("metrics @ %s - %d non-merge commits%s" % (
        result["head"], len(commits), " since %s" % args.since if args.since else ""))
    print("Trailer coverage      %s carry Spec: - every number below rests on these"
          % pct(len(with_spec), len(commits)))
    if landed:
        print("First-pass land rate  %s feat landings not corrected within %d commits"
              % (pct(landed - len(corrected), landed), args.window))
        for c in corrected:
            print("  corrected  %-24s %s %s  ->  %s %s  (+%d)" % (
                c["spec"], c["feat"], c["feat_subject"][:40], c["fix"], c["fix_subject"][:40],
                c["distance"]))
    else:
        print("First-pass land rate  n/a - no feat commit carries a Spec: trailer yet")
    total_escaped = sum(escaped.values())
    print("Escaped joints        %d reported%s" % (total_escaped, (" (" + ", ".join(
        "%s: %d" % kv for kv in sorted(escaped.items())) + ")") if escaped else ""))
    if measured:
        print("Approval latency      median %s days over %d spec(s); %d not measurable "
              "(a proxy for owner review time)" % (
                  statistics.median(measured), len(measured), len(latency) - len(measured)))
    else:
        print("Approval latency      n/a - no spec has both a creating commit and an approved_on "
              "after it (%d spec(s) looked at)" % len(latency))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
