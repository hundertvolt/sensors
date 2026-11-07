"""Read-only: value counts of chosen columns of b3 record tables (git show input), truncated for grouping."""
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
from _tables import show, tables  # noqa: E402

REPO, REF = sys.argv[1], sys.argv[2]
SPECS = sys.argv[3:]  # name:tableline:colindex[:width]


def norm(v, width):
    v = re.sub(r"`[^`]*`", "`x`", v)
    v = re.sub(r"\d+", "N", v)
    return v[:width]


for spec in SPECS:
    parts = spec.split(":")
    name, tline, col = parts[0], int(parts[1]), int(parts[2])
    width = int(parts[3]) if len(parts) > 3 else 40
    found = tables(show(f"audit/b3/{name}.md"))
    if tline == 0 and found:
        tline = max(found, key=lambda t: len(t[3]))[0]
    for line, _section, header, rows in found:
        if line != tline:
            continue
        c = collections.Counter(norm(r[col] if col < len(r) else "<missing>", width) for r in rows)
        print(f"=== {name} L{line} col {col} '{header[col]}' rows={len(rows)} distinct={len(c)}")
        for v, n in c.most_common(25):
            print(f"  {n:5d}  {v}")
