# ci_durations.py <ci log>: per-file wall time from "== Running tests/<f>.py" to "[<f>] N/N passed", per attempt.
import re, sys
from datetime import datetime
start, out = {}, []
ts = lambda l: datetime.strptime(l[:26], "%Y-%m-%dT%H:%M:%S.%f")
for l in open(sys.argv[1], errors="replace"):
    m = re.search(r"== Running tests/(\w+)\.py", l)
    if m: start[m.group(1)] = ts(l); continue
    m = re.search(r"exceeded (\d+)s on attempt", l)
    m2 = re.search(r"\[(\w+)\] \d+/\d+ passed", l)
    if m2 and m2.group(1) in start:
        out.append(((ts(l) - start[m2.group(1)]).total_seconds(), m2.group(1), l[:19]))
for d, f, t in sorted(out, reverse=True)[:12]: print(f"{d:7.1f}s {f} (ended {t})")
