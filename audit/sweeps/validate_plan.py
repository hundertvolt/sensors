"""Plan validators V1 (file ownership), V3 (path:line anchors in bounds) and V4 (IDs) for PROJECT_AUDIT_PLAN.md.

Usage: validate_plan.py [--anchor-sha SHA]  (default 0615eba, the planning baseline). Exit 1 on any failure.
"""

import argparse
import re
import subprocess
import sys

from owner_of import classify

PLAN = "PROJECT_AUDIT_PLAN.md"
AREAS = "XCUT CORE ALGO BUS SENS STOR UART NET REST LED GEN TOOL SCR CI WEB TEST TWIN HW SEC MEM PERF PLAT PAR DOC LIC ENV".split()
EXT = r"py|md|sh|toml|js|mjs|json|yml|yaml|ini|txt|css|html|cfg"
REF_RE = re.compile(r"([\w./-]+\.(?:" + EXT + r")):(\d+)((?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)")
CONT_RE = re.compile(r"`:(\d+)((?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)`")
UPSTREAM = ("py/", "extmod/", "ports/", "shared/", "lib/", "drivers/", "src/freezeFS.py")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def v1():
    bad = []
    for p in filter(None, git("ls-files").stdout.split("\n")):
        c = classify(p)
        if len(c) != 1:
            bad.append(f"{p}: {c or 'unowned'}")
    return bad


def numbers(first, rest):
    out = []
    for part in [first + rest.split(",")[0]] + rest.split(",")[1:]:
        part = part.strip()
        if part:
            out += [int(x) for x in part.split("-") if x]
    return out


def v3(sha):
    tracked = set(git("ls-tree", "-r", "--name-only", sha).stdout.split("\n"))
    by_base = {}
    for t in tracked:
        by_base.setdefault(t.rsplit("/", 1)[-1], []).append(t)
    sizes, bad, skipped, checked = {}, [], set(), 0

    def resolve(p):
        if p in tracked:
            return p
        if p.startswith(UPSTREAM):
            return None
        cands = [c for c in by_base.get(p.rsplit("/", 1)[-1], []) if c.endswith("/" + p) or "/" not in p]
        src = [c for c in cands if c.startswith("src/")]
        return (src or (cands if len(cands) == 1 else []) or [None])[0]

    for block in re.split(r"\n(?=\s*- |\s*\n|\|)", open(PLAN).read()):
        last = None
        for m in re.finditer(REF_RE.pattern + "|" + CONT_RE.pattern, block):
            if m.group(1):
                path, first, rest = m.group(1), m.group(2), m.group(3) or ""
                last = resolve(path)
                if last is None:
                    skipped.add(path)
                    continue
            elif last is not None:
                first, rest = m.group(4), m.group(5) or ""
            else:
                continue
            if last not in sizes:
                sizes[last] = git("show", f"{sha}:{last}").stdout.count("\n") + 1
            for n in numbers(first, rest):
                checked += 1
                if not 1 <= n <= sizes[last]:
                    bad.append(f"{last}:{n} beyond {sizes[last]} lines")
    return bad, checked, sorted(skipped)


def v4():
    text = open(PLAN).read()
    ids = "|".join(AREAS)
    defined = re.findall(r"^\s*- (?:\[[ x~]\] )?\*\*((?:" + ids + r")\.[STN]\d\d)\*\*", text, re.M)
    refs = set(re.findall(r"\b((?:" + ids + r")\.[STN]\d\d)\b", text))
    bad = [f"{d} defined {defined.count(d)} times" for d in sorted(set(defined)) if defined.count(d) > 1]
    bad += [f"{r} referenced, never defined" for r in sorted(refs - set(defined))]
    bad += [f"PQ{n} out of range" for n in sorted({int(n) for n in re.findall(r"\bPQ(\d+)\b", text)}) if not 1 <= n <= 10]
    return bad, len(defined)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchor-sha", default="0615eba")
    sha = ap.parse_args().anchor_sha
    b1 = v1()
    b3, n3, skip = v3(sha)
    b4, n4 = v4()
    print(f"V1 ownership: {len(b1)} problems")
    print(f"V3 anchors at {sha}: {n3} line refs checked, {len(b3)} out of bounds; unresolved names (upstream/other): {', '.join(skip)}")
    print(f"V4 IDs: {n4} defined, {len(b4)} problems")
    for line in b1 + b3 + b4:
        print("  " + line)
    sys.exit(1 if b1 or b3 or b4 else 0)
