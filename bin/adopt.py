#!/usr/bin/env python3
"""Vendor the kit into a project, correctly, and prove it.

Run from the project root, with the kit already cloned at ./factory:

    python3 factory/bin/adopt.py

Replaces the hand-run copy-and-sed recipe that used to live in AI-ONBOARDING.md §2. That
recipe was wrong in three independent ways, all found by audit on 2026-09-10:

  1. It sed-ed `.claude/CLAUDE.md`, which does not exist — `harness/` ships
     `CLAUDE.md.template`, and the rename happened two steps LATER in the doc. Hard error,
     step 2 of 6, on every adoption.
  2. Its link rewrite matched only `../../`, so depth-3 skill files were mangled
     (`../../../gates/GATES.md` -> `../../factory/../gates/GATES.md`) and depth-1 files were
     never rewritten at all. 20 of 82 links broken, silently.
  3. `sed -i ''` is BSD-only; it errors on Linux.

The rule the old recipe missed: inside the copied harness, only the prefix that ESCAPES the
harness tree may be rewritten. A file `d` directories deep under `.claude/` reaches the kit
root with exactly `../` * d; anything shorter is an intra-harness link that is already correct
and must be left alone. That is why one global substitution can never be right.

Exits non-zero if any relative link in the result is dead, so a broken adoption cannot pass
silently — README.md says broken cross-links are bugs, and this makes the kit prove it.
"""
import os
import re
import shutil
import sys

LINK = re.compile(r"(\]\()([^)\s]+)(\))")


def rewrite_depth(text, depth):
    """Prefix `factory/` onto exactly the links that escape the harness tree."""
    escape = "../" * depth

    def sub(m):
        target = m.group(2)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return m.group(0)
        # Only the exact escaping depth. A deeper run of ../ cannot occur (it would leave the
        # project); a shallower one is intra-harness and already correct.
        if depth and target.startswith(escape) and not target.startswith(escape + "../"):
            return m.group(1) + escape + "factory/" + target[len(escape):] + m.group(3)
        return m.group(0)

    return LINK.sub(sub, text)


def check_links(root):
    """Every relative markdown link under `root` must resolve. Returns the broken ones."""
    broken = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if not f.endswith(".md"):
                continue
            p = os.path.join(dirpath, f)
            with open(p, encoding="utf-8") as fh:
                for i, line in enumerate(fh, 1):
                    for m in LINK.finditer(line):
                        t = m.group(2)
                        if t.startswith(("http://", "https://", "mailto:", "#")):
                            continue
                        t = t.split("#")[0]
                        if not t:
                            continue
                        if not os.path.exists(os.path.normpath(os.path.join(dirpath, t))):
                            broken.append(f"{os.path.relpath(p, root)}:{i} -> {m.group(2)}")
    return broken


def main():
    proj = os.getcwd()
    kit = os.path.join(proj, "factory")
    if not os.path.isdir(os.path.join(kit, "harness")):
        sys.exit("ERROR: run this from the project root, with the kit cloned at ./factory")

    dest = os.path.join(proj, ".claude")
    if os.path.exists(dest):
        sys.exit(f"ERROR: {dest} already exists. Move it aside first — this script will not "
                 f"merge into an existing harness.")

    shutil.copytree(os.path.join(kit, "harness"), dest)

    # The template becomes the project's always-loaded context file. Renaming it HERE means
    # the link rewrite below sees the file at its final path and depth.
    tmpl = os.path.join(dest, "CLAUDE.md.template")
    if os.path.exists(tmpl):
        os.rename(tmpl, os.path.join(dest, "CLAUDE.md"))

    rewritten = 0
    for dirpath, _dirs, files in os.walk(dest):
        depth = 0 if dirpath == dest else len(os.path.relpath(dirpath, dest).split(os.sep))
        for f in files:
            if not f.endswith(".md"):
                continue
            p = os.path.join(dirpath, f)
            with open(p, encoding="utf-8") as fh:
                before = fh.read()
            after = rewrite_depth(before, depth + 1)  # +1: a file sits one level below its dir's parent
            if after != before:
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(after)
                rewritten += 1

    # The guardrail. Copying the docs without this is how an adopter ends up reading
    # "your last line of defense" about a hook they never installed.
    hooks_src = os.path.join(dest, "skills", "careful", "hooks")
    hooks_dst = os.path.join(dest, "hooks")
    if os.path.isdir(hooks_src):
        os.makedirs(hooks_dst, exist_ok=True)
        for f in os.listdir(hooks_src):
            shutil.copy2(os.path.join(hooks_src, f), os.path.join(hooks_dst, f))
        for f in os.listdir(hooks_dst):
            if f.endswith((".sh", ".py")):
                os.chmod(os.path.join(hooks_dst, f), 0o755)

    gates = os.path.join(proj, "gates")
    os.makedirs(gates, exist_ok=True)
    for f in ("check-plan-sync.sh", "check-plan-sync.test.sh"):
        src = os.path.join(kit, "gates", f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(gates, f))
            os.chmod(os.path.join(gates, f), 0o755)

    broken = check_links(dest)
    print(f"copied  : {os.path.relpath(dest, proj)}/  ({rewritten} files had links rewritten)")
    print(f"hooks   : {os.path.relpath(hooks_dst, proj)}/  (register them — see .claude/settings.json.template)")
    print(f"gates   : {os.path.relpath(gates, proj)}/")
    if broken:
        print(f"\n❌ {len(broken)} broken relative link(s) in the copied harness:")
        for b in broken:
            print("   ", b)
        sys.exit(1)
    print("\n✅ every relative link in the copied harness resolves")
    print("\nNext: fill .claude/CLAUDE.md, write .specify/memory/constitution.md, "
          "merge .claude/settings.json.template into your host's settings, "
          "then run the careful skill's two live probes.")


if __name__ == "__main__":
    main()
