#!/usr/bin/env bash
# check-spec-approval.sh — the spec-approval HARD-GATE and the acceptance record, as a script
# (from the AI Factory Kit). Chain slot: spec-approval (gates/chain.conf).
#
#   ./gates/check-spec-approval.sh [<specs-dir>]     # default ./specs, run from the project root
#
# RED when, for any specs/<id>/:
#   * tasks.md has a checked task ("- [x]" / "- [X]") while spec.md says status: draft —
#     implementation started before the owner approved the spec;
#   * status is anything but draft and approved_by or approved_on (YYYY-MM-DD) is missing,
#     malformed or a placeholder ("<name>", "[OWNER]", "TBD", ...);
#   * status is accepted, released or (legacy) shipped and specs/<id>/acceptance.md is missing
#     or invalid: it needs the heading "# Acceptance — <id>", accepted_on (a date, not before
#     approved_on), accepted_by, run_as ("n/a" only with its reason) and "result: pass";
#   * spec.md is missing, its frontmatter is unreadable, or status is unknown — this gate
#     cannot tell what was approved, so it does not guess.
# No ./specs yet -> "nothing to check yet", exit 0. A <specs-dir> you name that is missing -> 1.
# The parser is gates/check-specs.py, shared with check-plan-sync.sh.
#
# Why this exists: Spec Kit pauses for spec approval only under `specify workflow run`; on the
# per-command path (/speckit-specify, /speckit-plan, ...) nothing reads or records approval, so
# the HARD-GATE rested on the agent's goodwill (audit finding, 2026-09). Recording approval in
# frontmatter makes it checkable; this gate checks it on every commit.
#
# BLIND TO:
#   * WHO REALLY APPROVED. approved_by is a name somebody typed. The gate proves a record
#     exists and is dated, not that the owner said yes — an agent can type the owner's name.
#     Review (and git blame on the approval line) is what catches that.
#   * WHO REALLY ACCEPTED. It cannot tell the builder from anyone else; accepted_by "never the
#     builder" is a rule for people, and run_as is only as true as whoever wrote it.
#   * THE ACCEPTANCE RUN ITSELF. It reads the record, never re-runs quickstart.md.
#   * CODE WRITTEN BEFORE APPROVAL WITHOUT TICKING A TASK. It sees checkboxes, not source
#     files. Work done on a draft spec but left unticked passes until someone ticks it.
#   * SPECS OUTSIDE <specs-dir>, and anything not in spec.md / tasks.md / acceptance.md.
#   * ITSELF. Two-direction test: gates/check-spec-approval.test.sh.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
case "${1:-}" in
  -h|--help) sed -n '2,/^set -euo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 0 ;;
  -*) echo "check-spec-approval.sh: unknown option '$1' (try --help)" >&2; exit 2 ;;
esac
if [ "$#" -gt 1 ]; then echo "usage: check-spec-approval.sh [<specs-dir>]" >&2; exit 2; fi
exec python3 "$HERE/check-specs.py" approval ${1+"$@"}
