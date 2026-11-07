"""A-C review fold: resolve `[fold Fnn M_FILE]` tokens to the M-IDs that file's fold ledger lists for item Fnn.

Run from the repo root: `python3 audit/sweeps/fold_tokens.py [--write]`. Without --write it only reports.
"""
import glob
import re
import sys

ROOT = "audit/consolidation"
TOKEN = re.compile(r"\[fold (F\d\d) (M_[A-Z_]+)\]")
ROW = re.compile(r"^\|\s*(F\d\d)\s*\|(.*)\|\s*([^|]*?)\s*\|\s*$")
MFULL = re.compile(r"M\.([A-Z][A-Z_]*[A-Z])\.(\d+)")
MCONT = re.compile(r"(?:,|/|and)\s*\.(\d{3})\b")
SKIP = ("none", "dropped")


def ledger(path):
    """{Fnn: [M-IDs]} from the file's '## A-C review fold' section; rows whose action is none/dropped give nothing."""
    out, inside = {}, False
    prefix = "M." + path.split("/M_")[1][:-3]
    for ln in open(path):
        if ln.startswith("## "):
            inside = ln.startswith("## A-C review fold")
            continue
        m = ROW.match(ln) if inside else None
        if not m:
            continue
        item, ids, action = m.group(1), m.group(2), m.group(3).lower()
        if action.startswith(SKIP):
            continue
        found = []
        for full in MFULL.finditer(ids):
            fid = f"M.{full.group(1)}.{full.group(2)}"
            if fid.startswith(prefix + ".") and fid not in found:
                found.append(fid)
        for cont in MCONT.finditer(ids):
            fid = f"{prefix}.{cont.group(1)}"
            if fid not in found:
                found.append(fid)
        out.setdefault(item, [])
        out[item] += [f for f in found if f not in out[item]]
    return out


def main(write):
    files = sorted(glob.glob(f"{ROOT}/M_*.md"))
    ledgers = {p.split("/")[-1][:-3]: ledger(p) for p in files}
    unresolved, count = [], 0
    for p in files:
        text = open(p).read()

        def sub(m):
            nonlocal count
            item, target = m.group(1), m.group(2)
            ids = ledgers.get(target, {}).get(item, [])
            if not ids:
                unresolved.append((p, m.group(0)))
                return m.group(0)
            count += 1
            return ", ".join(ids) + f" (fold {item})"

        new = TOKEN.sub(sub, text)
        if write and new != text:
            open(p, "w").write(new)
    print(f"tokens resolved: {count}; unresolved: {len(unresolved)}")
    for p, t in unresolved:
        print(f"  UNRESOLVED {p}: {t}")


if __name__ == "__main__":
    main("--write" in sys.argv)
