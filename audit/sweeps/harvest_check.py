"""Re-check every harvest catalog item's anchor and quote against one commit.

Usage: harvest_check.py SHA [CATALOG...]  (default: audit/harvest/*.md). Prints per-status counts and every
item whose quote is not at its anchor; exit 0. Same matching rule as harvest_merge.py's check_anchor().
"""

import collections
import glob
import re
import subprocess
import sys

ITEM = re.compile(r"^- \*\*([A-Z]+\.N\d{3,4})\*\* (.*?) ·(?: (.*))?$")
_files = {}


def lines_of(sha, path):
    key = (sha, path)
    if key not in _files:
        r = subprocess.run(["git", "show", f"{sha}:{path}"], capture_output=True, text=True, check=False)
        _files[key] = r.stdout.split("\n") if r.returncode == 0 else None
    return _files[key]


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[`*_>#]|\\", "", s)).strip().lower()


def items(paths):
    for p in paths:
        cur = None
        for line in open(p, encoding="utf-8"):
            m = ITEM.match(line)
            if m:
                if cur:
                    yield cur
                cur = {"id": m[1], "kind": m[2], "text": (m[3] or "").strip(), "file": p}
            elif cur and line.startswith("  ") and line.strip():
                cur["text"] += " " + line.strip()
            elif cur:
                yield cur
                cur = None
        if cur:
            yield cur


def check(sha, it):
    parts = it["text"].split(" — ", 2)
    anchor, quote = parts[0], parts[1] if len(parts) > 1 else ""
    m = re.match(r"`?([\w./ -]+?\.[\w]+):(\d[\d,\s-]*)", anchor)
    if not m:
        return "not-a-file", None
    path, nums = m[1].strip(), [int(x) for x in re.findall(r"\d+", m[2])]
    L = lines_of(sha, path)
    if L is None:
        return "file-missing", None
    frags = re.findall(r'"([^"]{12,})"', quote) or [quote.strip().strip('"')]
    frags = [norm(y) for f in frags for y in re.split(r"…|\.\.\.|\[\.\.\.\]", f)]
    frags = [f for f in frags if len(f) >= 12]
    oob = any(n < 1 or n > len(L) + 1 for n in nums)
    if not frags:
        return ("out-of-bounds" if oob else "no-quote"), None
    frag = max(frags, key=len)[:40]
    lo, hi = min(nums), max(nums)
    if frag in norm(" ".join(L[max(0, lo - 6):min(len(L), hi + 5)])):
        return ("out-of-bounds" if oob else "ok"), None
    hits = [i + 1 for i in range(len(L)) if frag in norm(" ".join(L[i:i + 3]))]
    if hits:
        return "moved", min(hits, key=lambda h: abs(h - lo))
    return ("out-of-bounds" if oob else "quote-not-found"), None


if __name__ == "__main__":
    sha = sys.argv[1]
    paths = sys.argv[2:] or sorted(glob.glob("audit/harvest/*.md"))
    c = collections.Counter()
    for it in items(paths):
        s, at = check(sha, it)
        c[s] += 1
        if s not in ("ok", "not-a-file", "no-quote"):
            tagged = "quote not" in it["text"]
            print(f"{s:16} {it['id']:10} {'[tagged] ' if tagged else ''}{it['text'][:110]}{f'  -> line {at}' if at else ''}")
    print(dict(c))
