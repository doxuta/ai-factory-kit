#!/usr/bin/env bash
# check-spec-numbers.sh — no two specs share a number (from the AI Factory Kit).
# Chain slot: spec-numbers (gates/chain.conf).
#
#   ./gates/check-spec-numbers.sh [<specs-dir>]     # default ./specs, run from the project root
#
# RED when two directories under specs/ carry the same prefix, or when a directory carries
# neither accepted prefix:
#   NNN-<name>              sequential, 3+ digits (001-, 042-, 1000-); compared as numbers, so
#                           007-a and 0007-b collide
#   YYYYMMDD-HHMMSS-<name>  Spec Kit's --timestamp / feature_numbering: timestamp
# Sequential and timestamp directories may coexist (a project that switched numbering midway).
# Hidden directories and plain files in specs/ are ignored.
# No ./specs yet -> "nothing to check yet", exit 0. A <specs-dir> you name that is missing -> 1.
#
# Why this exists: Spec Kit's sequential numbering looks only at the local specs/ directory.
# Measured in the 2026-09 audit: two branches from one base each ran create-new-feature and
# both got 002; after the merge, specs/ held 002-login-page and 002-payment-export and git
# reported no conflict. The roadmap sorts by that number and every tool addresses a feature
# by it. Remedy on red: renumber the later one (git mv, then its feature: line), and switch to
# timestamp numbering while more than one branch creates specs at a time.
#
# BLIND TO:
#   * COLLISIONS NOT YET MERGED. Two open branches that both hold 003-x are each green until
#     they meet; only the merge (or CI on the merge result) sees both.
#   * WHAT IS INSIDE a directory — that is check-plan-sync.sh (feature: = dir name) and
#     check-spec-approval.sh.
#   * DUPLICATE SUBJECTS under different numbers (two specs for one feature).
#   * ITSELF. Two-direction test: gates/check-spec-numbers.test.sh.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
case "${1:-}" in
  -h|--help) sed -n '2,/^set -euo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 0 ;;
  -*) echo "check-spec-numbers.sh: unknown option '$1' (try --help)" >&2; exit 2 ;;
esac
if [ "$#" -gt 1 ]; then echo "usage: check-spec-numbers.sh [<specs-dir>]" >&2; exit 2; fi
exec python3 "$HERE/check-specs.py" numbers ${1+"$@"}
