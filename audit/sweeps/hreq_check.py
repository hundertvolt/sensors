"""Check harvest pass 1: every catalog item ID is placed in some audit/hreq/G*.md file."""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ITEM = re.compile(r"^- \*\*([A-Z]+)\.N(\d+)\*\*", re.M)
REF = re.compile(r"\b([A-Z]+)\.N(\d+)(?:\s*[-–]\s*(?:\1\.)?N?(\d+))?")


def catalog_ids():
    ids = set()
    for p in (ROOT / "harvest").glob("*.md"):
        ids |= {(a, int(n)) for a, n in ITEM.findall(p.read_text())}
    return ids


def placed_ids(files):
    ids = set()
    for p in files:
        for area, lo, hi in REF.findall(p.read_text()):
            top = int(hi) if hi else int(lo)
            ids |= {(area, n) for n in range(int(lo), top + 1)}
    return ids


def main():
    files = sorted((ROOT / "hreq").glob("G*.md"))
    want, got = catalog_ids(), placed_ids(files)
    missing = sorted(want - got)
    by_area = {}
    for a, n in missing:
        by_area.setdefault(a, []).append(n)
    print(f"catalog items {len(want)}, placed {len(want & got)}, missing {len(missing)}, unknown refs {len(got - want)}")
    for a, ns in sorted(by_area.items()):
        print(f"  {a}: {len(ns)} missing, e.g. " + ", ".join(f"N{n:03d}" for n in ns[:12]))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
