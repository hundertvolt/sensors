"""Read-only: print rows of a b3 record table whose chosen column matches (or, with !, does not match) a regex."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
from _tables import show, tables  # noqa: E402

REPO, REF = sys.argv[1], sys.argv[2]
for spec in sys.argv[3:]:
    name, tline, col, pat, width = spec.split("::")
    neg = pat.startswith("!")
    rx = re.compile(pat[1:] if neg else pat)
    for line, _s, header, rows in tables(show(f"audit/b3/{name}.md")):
        if line != int(tline):
            continue
        hits = [r for r in rows if bool(rx.search(r[int(col)] if int(col) < len(r) else "")) != neg]
        print(f"=== {name} L{line} col {col} {'not ' if neg else ''}/{rx.pattern}/: {len(hits)} rows")
        for r in hits:
            print("  " + " | ".join(c[: int(width)] for c in r))
