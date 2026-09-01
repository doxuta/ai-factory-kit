#!/bin/bash
# check-plan-sync.sh — generic doc-consistency gate (from the AI Factory Kit).
# Two independent jobs — and deliberately SELF-GLOBBING: a gate that hard-points at one
# file becomes a hostage-taker the day that file must move or die (see gates/GATES.md §6).
#
#  1. PLAN SYNC — for EVERY docs/*-plan.md that carries the progress format
#     (header bars "M2 [✅⬜] 1/4" + table rows "| ✅ | M2-T1 |"), verify the
#     header matches the table. A plan being git-rm'd (after its content is
#     absorbed into specs/NNN-*/) simply drops out of the glob — the gate is
#     never orphaned by a doc deletion. Plans without the format are skipped.
#  2. BLUEPRINT — when docs/ARCHITECTURE.md exists: it must not still mark a
#     milestone ⬜ that a plan reports complete (overstate), and its roadmap rows
#     must not understate code that exists on disk (sentinel check). When the
#     file is absent these checks SKIP (plan checks above still run).
#
# Exit 1 on any mismatch. Usage:  bash gates/check-plan-sync.sh [docs-dir]
set -euo pipefail
DOCS="${1:-docs}"   # pass your docs dir; default ./docs

python3 - "$DOCS" <<'PY'
import glob, os, re, sys

docs_dir = sys.argv[1]
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
    mt = re.search(r"(?:Tổng|Total):\s*\*?\*?\s*(\d+)/(\d+)", text)
    if mt and (int(mt.group(1)), int(mt.group(2))) != (gt_done, gt_total):
        problems.append(f"{name} Tổng: header says {mt.group(1)}/{mt.group(2)} but the table counts {gt_done}/{gt_total}  <- DRIFT")
    summary.append(f"{name} {gt_done}/{gt_total} (" +
                   "; ".join(f"{m} {done.get(m,0)}/{total.get(m,0)}" for m in sorted(total)) + ")")

# ---- Job 2: MASTER BLUEPRINT checks — unconditional, plan-independent ----
arch_path = os.path.join(docs_dir, "ARCHITECTURE.md")
if not os.path.exists(arch_path):
    pass  # no blueprint in this project -> blueprint checks skip (plan checks above still ran)
else:
    arch = open(arch_path, encoding="utf-8").read()

    # Overstate: a plan reports a milestone fully done but the blueprint still marks it ⬜.
    for name in sorted(all_total):
        done, total = all_done[name], all_total[name]
        for m in sorted(total):
            if total[m] > 0 and done.get(m, 0) == total[m] and re.search(rf"\b{m}\b\s*⬜", arch):
                problems.append(f"ARCHITECTURE.md still marks {m} ⬜ but {name} reports {done[m]}/{total[m]} done  <- BLUEPRINT DRIFT")

    # GATE-01 understate: sentinel package exists on disk but the §6 EPIC cell is still pure ⬜.
    platform_root = os.path.dirname(docs_dir)
    # Map "roadmap row number" -> "sentinel package that proves the code exists".
    # FILL THIS for your project (empty = the understate check is skipped):
    epic_sentinels = {
        # "4": "internal/workflow",
    }
    for num, sub in sorted(epic_sentinels.items()):
        if not os.path.isdir(os.path.join(platform_root, sub)):
            continue  # not built yet → ⬜ is honest, skip
        row = re.search(rf"^\|\s*\*\*{num}\.\s[^|]*\|[^|]*\|([^|]*)\|", arch, re.MULTILINE)
        if not row:
            problems.append(f"blueprint: no row for section {num} in ARCHITECTURE.md to cross-check")
            continue
        if "✅" not in row.group(1) and "🟡" not in row.group(1):
            problems.append(
                f"blueprint row {num}: code `{sub}/` exists but the status cell is still ⬜ (understate)  <- DRIFT")

if problems:
    print("❌ DOC-SYNC DRIFT — fix the header to match the table:")
    for p in problems:
        print("   •", p)
    sys.exit(1)
blue = "blueprint checks ran" if os.path.exists(arch_path) else "blueprint checks skipped — no ARCHITECTURE.md"
print("✅ Docs in sync — " + ("; ".join(summary) if summary else "0 plans in format") + f" ({blue})")
PY
