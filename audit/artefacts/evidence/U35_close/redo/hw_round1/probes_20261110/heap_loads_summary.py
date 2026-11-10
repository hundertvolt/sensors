"""heap_loads_summary.py CONSOLE: per phase of snap58_heap_loads.py, the 1 s samples' min / median / last mem_free and largest
free block (mem_info's "max free sz" x 16 B), and each AFTER's collected readings."""
import re
import sys
from collections import defaultdict

lines = open(sys.argv[1], errors="replace").read().splitlines()
samples = defaultdict(list)
after = []
pending = None
for ln in lines:
    m = re.match(r"S (\S+) t_s (\d+) free (\d+)", ln)
    if m:
        pending = ("S", m.group(1), int(m.group(2)), int(m.group(3)))
        continue
    m = re.match(r"AFTER (\d+) collected free (\d+)", ln)
    if m:
        pending = ("A", int(m.group(1)), int(m.group(2)))
        continue
    m = re.search(r"max free sz: (\d+)", ln)
    if m and pending:
        big = int(m.group(1)) * 16
        if pending[0] == "S":
            samples[pending[1]].append((pending[2], pending[3], big))
        else:
            after.append((pending[1], pending[2], big))
        pending = None


def mid(v):
    v = sorted(v)
    return v[len(v) // 2]


for tag in sorted(samples, key=lambda t: (int(t[-1]) if t[-1].isdigit() else -1, t)):
    s = samples[tag]
    fr = [x[1] for x in s]
    bg = [x[2] for x in s]
    print("%-6s n %3d t_s %4d-%4d  free min %6d med %6d last %6d | largest min %6d med %6d last %6d" % (
        tag, len(s), s[0][0], s[-1][0], min(fr), mid(fr), fr[-1], min(bg), mid(bg), bg[-1]))
for n, free, big in after:
    print("AFTER %d (one gc.collect after the 120 s idle): free %6d largest %6d" % (n, free, big))
