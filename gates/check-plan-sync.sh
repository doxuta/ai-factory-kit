#!/bin/bash
# check-plan-sync.sh — generic doc-consistency gate (from the AI Factory Kit).
# Two modes — and deliberately SELF-GLOBBING: a gate that hard-points at one
# file becomes a hostage-taker the day that file must move or die (see gates/GATES.md §6).
#
#   bash gates/check-plan-sync.sh              # default: auto-detect (below)
#   bash gates/check-plan-sync.sh <docs-dir>   # docs mode on that dir
#   bash gates/check-plan-sync.sh --specs [<specs-dir>]   # spec-corpus mode on that dir
#
# DEFAULT (no argument), run from the project root:
#   specs/ exists  -> spec-corpus mode on ./specs
#   docs/  exists  -> docs mode on ./docs as well (both run when both exist)
#   neither        -> "nothing to check yet (no specs/ or docs/)", exit 0
#   A docs/ that holds no *-plan.md in the format below also counts as nothing to check, and
#   says so: the default invocation never prints a bare green over an empty scope.
#
# SPEC-CORPUS MODE — every specs/<id>/ (the parser is gates/check-specs.py, shared with
# check-spec-approval.sh, so the two gates cannot read a spec differently). RED when:
#   * spec.md is missing, or its frontmatter is missing, not at line 1, or unclosed;
#   * feature:, status: or epic: is missing; status is not draft | approved | accepted |
#     released | superseded (legacy shipped = accepted); feature: differs from the dir name;
#   * status is superseded without superseded_by: <an existing spec dir>;
#   * status is accepted/released/shipped while tasks.md still has an unchecked "- [ ]" task
#     (or an open "| ⬜ | M1-T2 |" row of the 1.3.x table) not marked "(deferred -> <where>)";
#   * status is past draft and tasks.md exists but holds no task in either format.
#   WARNS (exit 0) when every task is checked but status is still draft or approved, and on
#   every 1.3.x table row (read as a task, but convert it: GATES.md §7).
#
# DOCS MODE — the original job, unchanged for any dir that holds plans:
#  1. PLAN SYNC — for EVERY <docs>/*-plan.md that carries the progress format
#     (header bars "M2 [✅⬜] 1/4" + table rows "| ✅ | M2-T1 |"), verify the
#     header matches the table (and a "Total: n/m" or "Tổng: n/m" line, if present).
#     A plan being git-rm'd simply drops out of the glob — the gate is never
#     orphaned by a doc deletion. Plans without the format are skipped.
#  2. BLUEPRINT (optional) — when <docs>/ARCHITECTURE.md exists, it must not mark a
#     milestone open ("M3 ⬜" anywhere in the file) that a plan reports complete.
#     Absent file -> skipped. That is the whole blueprint format; nothing else in it is read.
#     (v1.3.x also carried an "understate" check keyed to one private project's roadmap
#     table through an epic_sentinels map an adopter had to fill INSIDE this script. It was
#     inert unless edited, and this script is now kit-owned and guarded, so it was removed in
#     1.4.0. If you had filled that map, keep your copy as its own gate — an extra slot in
#     gates/chain.conf.)
#   A docs dir that holds no formatted plan but does hold Spec Kit feature dirs
#   (<dir>/*/spec.md) is RED: that is a specs dir wired into docs mode, which would check
#   nothing. Use no argument, or --specs <dir>.
#
# Exit 1 on any mismatch or wiring error, 0 when in sync.
#
# BLIND TO (GATES.md §4 — a green gate is evidence only of what it actually checks):
#   * WORK. A ticked "- [x]" box or a "✅" cell is a claim. Neither mode reads code or runs a
#     test; a box ticked over work nobody did passes. Acceptance evidence is
#     check-spec-approval.sh's job (acceptance.md), and even that only checks the record exists.
#   * DELETED TASKS. A task removed from tasks.md (or hidden in an HTML comment or a code
#     fence) is not open any more, as far as this gate can see.
#   * TASKS IN ANY OTHER FORMAT. Only "- [ ] T001" checklist lines and 1.3.x "| ✅ | M1-T1 |"
#     rows are tasks. A prose list, a table with other columns or a task in another file is
#     invisible; one checklist line beside them is enough to make the rest unseen.
#   * OPEN QUESTIONS. [NEEDS CLARIFICATION] markers are check-spec-approval.sh's job.
#   * WHETHER A DEFERRAL IS REAL. "(deferred -> 014-export)" unblocks acceptance; the gate does
#     not check that 014-export exists or mentions the task. Review does.
#   * APPROVAL. Who approved what is check-spec-approval.sh; duplicate numbers are
#     check-spec-numbers.sh. This gate does not repeat them.
#   * PLANS WITHOUT THE FORMAT (docs mode). A *-plan.md missing the "M2 [✅⬜] 1/4" header
#     bars is SKIPPED, not failed. Renaming a plan out of `*-plan.md` removes it silently.
#   * MILESTONES NOT IN THE TABLE, and milestone ids across plans (M1 in two plans is one
#     "M1" to the blueprint check).
#   * EVERY OTHER DOC. README, CHANGELOG, the constitution: unchecked.
#   * ITSELF. Its own two-direction test is gates/check-plan-sync.test.sh — run it after
#     any edit here, or you are shipping a gate whose red direction nobody has seen.
# It DOES fail loudly when a dir you NAME is missing or mistyped, so a wrong path can no
# longer look like a clean bill of health.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

docs_mode() { # docs_mode <docs-dir> <auto:0|1>
python3 - "$1" "$2" <<'PY'
import glob, os, re, sys

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(errors="replace")  # legacy code page: print "?", do not crash
    except (AttributeError, ValueError):
        pass

docs_dir, auto = sys.argv[1], sys.argv[2] == "1"
# A mistyped or moved docs dir used to exit 0 with "0 plans in format" — indistinguishable
# from a clean run, and the chain reads exit status only. An adopter whose docs live in `doc/`
# or a monorepo subdir would have wired a gate that is green forever. "Dir exists but holds no
# formatted plan" stays green and says so; "dir is not there" is a wiring error and fails.
if not os.path.isdir(docs_dir):
    print(f"❌ docs dir not found: {docs_dir!r} — check the argument you wired into the gate chain")
    sys.exit(1)

problems = []
summary = []

# ---- Job 1: per-plan header↔table sync (auto-discovered) ----
all_done = {}   # plan basename -> {milestone: done}
all_total = {}  # plan basename -> {milestone: total}
for plan_path in sorted(glob.glob(os.path.join(docs_dir, "*-plan.md"))):
    text = open(plan_path, encoding="utf-8").read()
    name = os.path.basename(plan_path)

    done, total = {}, {}
    for status, task in re.findall(r"^\|\s*([✅⬜])\s*\|\s*(M\d+-T\d+)", text, re.MULTILINE):
        m = task.split("-")[0]
        total[m] = total.get(m, 0) + 1
        if status == "✅":
            done[m] = done.get(m, 0) + 1
    if not total:
        continue  # plan without the progress format — not covered by this gate
    all_done[name], all_total[name] = done, total

    header = {}
    for m, count, tot in re.findall(r"^(M\d+)\s*\[[^\]]*\]\s*(\d+)/(\d+)", text, re.MULTILINE):
        header[m] = (int(count), int(tot))

    for m in sorted(set(total) | set(header)):
        d, t = done.get(m, 0), total.get(m, 0)
        if m not in header:
            problems.append(f"{name} {m}: table counts {d}/{t} but the header has no progress bar")
            continue
        if header[m] != (d, t):
            problems.append(f"{name} {m}: header says {header[m][0]}/{header[m][1]} but the table counts {d}/{t}  <- DRIFT")

    gt_done, gt_total = sum(done.values()), sum(total.values())
    mt = re.search(r"(Tổng|Total):\s*\*?\*?\s*(\d+)/(\d+)", text)
    if mt and (int(mt.group(2)), int(mt.group(3))) != (gt_done, gt_total):
        problems.append(f"{name} {mt.group(1)}: header says {mt.group(2)}/{mt.group(3)} but the table counts {gt_done}/{gt_total}  <- DRIFT")
    summary.append(f"{name} {gt_done}/{gt_total} (" +
                   "; ".join(f"{m} {done.get(m,0)}/{total.get(m,0)}" for m in sorted(total)) + ")")

# ---- Job 2 (optional): BLUEPRINT overstate — runs only when <docs>/ARCHITECTURE.md exists ----
arch_path = os.path.join(docs_dir, "ARCHITECTURE.md")
if os.path.exists(arch_path):
    arch = open(arch_path, encoding="utf-8").read()
    # Overstate: a plan reports a milestone fully done but the blueprint still marks it ⬜.
    for name in sorted(all_total):
        done, total = all_done[name], all_total[name]
        for m in sorted(total):
            if total[m] > 0 and done.get(m, 0) == total[m] and re.search(rf"\b{m}\b\s*⬜", arch):
                problems.append(f"ARCHITECTURE.md still marks {m} ⬜ but {name} reports {done[m]}/{total[m]} done  <- BLUEPRINT DRIFT")

if problems:
    print("❌ DOC-SYNC DRIFT — fix the header to match the table:")
    for p in problems:
        print("   •", p)
    sys.exit(1)

if not summary:
    # No plan in format. If this dir is really a Spec Kit specs dir, docs mode checks nothing
    # while the specs could be in any state: measured in a 2026-09 adoption run, where
    # `check-plan-sync.sh specs` printed "0 plans in format" and exited 0 over a spec marked
    # shipped with an unfinished task.
    feature_dirs = [d for d in sorted(os.listdir(docs_dir))
                    if os.path.isfile(os.path.join(docs_dir, d, "spec.md"))]
    if feature_dirs:
        print(f"❌ {docs_dir!r} holds {len(feature_dirs)} spec feature dir(s) ({feature_dirs[0]}, ...) "
              "and no *-plan.md in format — docs mode would check nothing here. Run the gate with "
              f"no argument (it finds ./specs), or with --specs {docs_dir}")
        sys.exit(1)
    if auto:
        print(f"✅ nothing to check yet in {docs_dir}/ (no *-plan.md in the progress format)")
        sys.exit(0)

blue = "blueprint checks ran" if os.path.exists(arch_path) else "blueprint checks skipped — no ARCHITECTURE.md"
print("✅ Docs in sync — " + ("; ".join(summary) if summary else "0 plans in format") + f" ({blue})")
PY
}

case "${1:-}" in
  -h|--help)
    sed -n '2,/^set -euo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  --specs)
    if [ "$#" -gt 2 ]; then echo "usage: check-plan-sync.sh --specs [<specs-dir>]" >&2; exit 2; fi
    exec python3 "$HERE/check-specs.py" corpus "${2:-specs}"
    ;;
  -*)
    echo "check-plan-sync.sh: unknown option '$1' (try --help)" >&2
    exit 2
    ;;
esac

if [ "$#" -gt 1 ]; then
  echo "usage: check-plan-sync.sh [<docs-dir> | --specs [<specs-dir>]]" >&2
  exit 2
fi

if [ "$#" -eq 1 ]; then
  docs_mode "$1" 0
  exit $?
fi

# No argument: auto-detect from the current directory (run-chain.sh runs from the project root).
rc=0
ran=0
if [ -d specs ]; then
  ran=1
  python3 "$HERE/check-specs.py" corpus || rc=1
fi
if [ -d docs ]; then
  ran=1
  docs_mode docs 1 || rc=1
fi
if [ "$ran" -eq 0 ]; then
  echo "✅ nothing to check yet (no specs/ or docs/)"
fi
exit "$rc"
