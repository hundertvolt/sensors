"""Allover pass 2: annotate plan section-5 topics and seeds whose pass-2 status is not plain work."""
import collections
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAN = ROOT.parent / "PROJECT_AUDIT_PLAN.md"
AREA_GROUP = {"HW": "G1", "TEST": "G2", "SENS": "G3", "ALGO": "G3", "BUS": "G3", "LED": "G3", "PLAT": "G4", "MEM": "G4",
              "PERF": "G4", "CORE": "G5", "STOR": "G5", "XCUT": "G5", "SEC": "G5", "UART": "G6", "NET": "G6", "REST": "G6",
              "TWIN": "G7", "WEB": "G7", "GEN": "G8", "TOOL": "G8", "SCR": "G8", "CI": "G8", "DOC": "G9", "PAR": "G9",
              "LIC": "G9", "ENV": "G10"}


def statuses():
    """ID -> (group, requirements, status, annotation), taken from the group that owns the ID's area."""
    got = {}
    for p in sorted((ROOT / "pass2").glob("G*.md")):
        sec = p.read_text().split("\n## 5 ", 1)[1].split("\n## 6 ", 1)[0]
        for line in sec.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
            if len(cells) < 3:
                continue
            for i in re.findall(r"\b[A-Z]{2,5}\.[TS]\d{2}\b", cells[0]):
                if AREA_GROUP.get(i.split(".")[0]) == p.stem or i not in got:
                    got[i] = (p.stem, cells[1], cells[2].strip("` ").split(" ")[0].lower(), cells[3] if len(cells) > 3 else "")
    return got


def main():
    got = statuses()
    lines = PLAN.read_text().split("\n")
    start = re.compile(r"^- (?:\[[ x~]\] )?\*\*([A-Z]{2,5}\.[TS]\d{2})\*\*")
    count = collections.Counter()
    i = 0
    while i < len(lines):
        m = start.match(lines[i])
        if not m:
            i += 1
            continue
        j = i
        while j + 1 < len(lines) and lines[j + 1].startswith("  ") and not start.match(lines[j + 1]):
            j += 1
        grp, reqs, st, ann = got.get(m.group(1), ("", "", "work", ""))
        if st != "work" and "⟨pass 2" not in "".join(lines[i:j + 1]):
            text = f"{st}: {ann}" if ann else st
            lines[j] += f" ⟨pass 2, {text} — {grp}: {reqs}⟩"
            count[st] += 1
        i = j + 1
    PLAN.write_text("\n".join(lines))
    print(dict(count), sum(count.values()))


if __name__ == "__main__":
    main()
