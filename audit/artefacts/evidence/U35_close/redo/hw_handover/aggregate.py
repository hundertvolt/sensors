"""Folds every long run's `SUM L` lines into one line per measurement: counts summed, worst/max values maxed, and for
each error count a rate against its own transactions (zero events give the 95 % bound 3/n). CPython, no packages;
usage: python3 aggregate.py PATH... (a log directory's *.log files, or any text file such as HANDBACK.md)."""

import re
import sys
from pathlib import Path

IDENT = ("chip", "phase", "op", "dir", "threshold", "period_ms")
TOTAL = ("n", "probes", "bytes_ok", "dns", "ntp", "samples_in_burst", "samples_outside", "connects", "windows")
OWN = {"dns_fail": "dns", "ntp_fail": "ntp", "connect_fail": "connects", "dev_in_burst": "samples_in_burst", "dev_outside": "samples_outside"}


def fold(lines: list[str]) -> list[str]:
    groups: dict[tuple, dict[str, int]] = {}
    runs: dict[tuple, int] = {}
    for line in lines:
        line = line.strip()
        if not line.startswith("SUM L "):
            continue
        name, *pairs = line[6:].split()
        kv = dict(p.split("=", 1) for p in pairs if "=" in p)
        key = (name, *[f"{k}={kv[k]}" for k in IDENT if k in kv])
        g = groups.setdefault(key, {})
        runs[key] = runs.get(key, 0) + 1
        for k, v in kv.items():
            if k in IDENT or not re.fullmatch(r"-?\d+", v):
                continue
            n = int(v)
            g[k] = max(g.get(k, n), n) if ("worst" in k or "max" in k) else g.get(k, 0) + n
    out = []
    for key, g in sorted(groups.items()):
        total = next((g[k] for k in TOTAL if k in g), 0)
        parts = [f"{k}={v}" for k, v in g.items()]
        if "fires" in g and "expected" in g:
            parts.append(f"dropped={g['expected'] - g['fires']}")
        rates = []
        for k in ("eio", "etimedout", "other", "bad", "oserrors", "mismatches", *OWN):
            den = g.get(OWN[k], 0) if k in OWN else total
            if k in g and den:
                rates.append(f"{k}_rate={g[k] / den:.2e}" if g[k] else f"{k}_rate<{3 / den:.1e}")
        out.append(" ".join([*key, f"runs={runs[key]}", *parts, *rates]))
    return out


if __name__ == "__main__":
    text: list[str] = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        for f in sorted(p.glob("*.log")) if p.is_dir() else [p]:
            text += f.read_text(errors="replace").splitlines()
    print("\n".join(fold(text)))
