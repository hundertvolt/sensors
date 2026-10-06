"""Execution packets: for one unit, every step in work-order order with its merged change and carried action texts.
Lanes group steps whose site files overlap (union-find), so disjoint lanes can be applied by separate agents.
Every packet opens with the silent-failure scan and lists the unit's register deltas; it is refused while one is unfolded.
Usage: step_packet.py <unit> [--outdir DIR] [--lanes]"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "audit"
PATH_RE = re.compile(r"`((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.(?:py|md|js|mjs|ts|toml|ini|yml|yaml|json|sh|html|css|txt|cfg|lock))(?::[0-9][0-9,\- ]*)?`")


def blocks(path, prefix):
    """Map every '### <ID> ...' heading in path to its block text."""
    out, cur, buf = {}, None, []
    for line in path.read_text().splitlines():
        if line.startswith("### " + prefix) or line.startswith("## "):
            if cur:
                out[cur] = "\n".join(buf).rstrip()
            cur, buf = None, []
            if line.startswith("### " + prefix):
                cur = line[4:].split()[0]
                buf = [line]
            continue
        if cur:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf).rstrip()
    return out


def load():
    changes, actions = {}, {}
    for f in sorted((AUDIT / "consolidation").glob("M_*.md")):
        changes.update(blocks(f, "M."))
    for f in sorted((AUDIT / "actions").glob("*.md")):
        actions.update(blocks(f, "A."))
    return changes, actions


def site_files(text):
    m = re.search(r"^- \*\*Site\*\*:(.*?)(?=^- \*\*)", text, re.S | re.M)
    seg = m.group(1) if m else ""
    return sorted({p for p in PATH_RE.findall(seg) if not p.startswith("audit/")} or {"(no file)"})


def register_deltas(unit):
    """Rows of REGISTER.md's parked-delta table whose unit column names this unit, as (row, folded)."""
    rows, inside = [], False
    for line in (AUDIT / "REGISTER.md").read_text().splitlines():
        if line.startswith("## "):
            inside = line.startswith("## Parked deltas")
            continue
        if not inside or not line.startswith("| ") or line.startswith(("| unit |", "|---")):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if unit in re.findall(r"U\d+[A-Z]*\d*", cells[0]):
            rows.append((line, cells[-1].startswith("folded")))
    return rows


def lanes(order, files):
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for group in order:
        fs = [f for c in group for f in files[c]]
        for f in fs[1:]:
            parent[find(f)] = find(fs[0])
    out = {}
    for group in order:
        root = find(files[group[0]][0])
        out.setdefault(root, []).append(group)
    return list(out.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("unit")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--lanes", action="store_true")
    ap.add_argument("--lane-set", default=None, help="comma-separated lane indices; actions printed once at the end")
    a = ap.parse_args()
    wo = json.loads((AUDIT / "order" / "work_order.json").read_text())
    unit = next(u for u in wo["units"] if u["unit"] == a.unit)
    steps = {s["change"]: s for s in wo["steps"] if s["unit"] == a.unit}
    changes, actions = load()
    files = {c: site_files(changes.get(c, "")) for g in unit["order"] for c in g}
    if a.lanes:
        for i, lane in enumerate(lanes(unit["order"], files)):
            fs = sorted({f for g in lane for c in g for f in files[c]})
            print(f"lane {i}: {sum(len(g) for g in lane)} steps, files: {', '.join(fs)}")
        return
    order = unit["order"]
    pos = {tuple(g): n for n, g in enumerate(order, 1)}
    if a.lane_set is not None:
        all_lanes = lanes(order, files)
        order = sorted((g for i in map(int, a.lane_set.split(",")) for g in all_lanes[i]), key=lambda g: pos[tuple(g)])
    deltas = register_deltas(a.unit)
    open_rows = [r for r, folded in deltas if not folded]
    if open_rows:
        raise SystemExit(f"{a.unit}: {len(open_rows)} register delta(s) not yet folded through A-C:\n" + "\n".join(open_rows))
    out, seen = ["# Standing checks (silent_failure_scan.md)\n", (AUDIT / "sweeps" / "silent_failure_scan.md").read_text()], []
    if deltas:
        out.append("\n# Register deltas for this unit (folded; their merged text is in the steps below)\n")
        out += [r for r, _ in deltas]
    for group in order:
        n = pos[tuple(group)]
        if len(group) > 1:
            out.append(f"\n## Step {n}: co-landing group (one commit): {' '.join(group)}\n")
        for c in group:
            s = steps[c]
            head = f"## Step {n}: {c}" if len(group) == 1 else f"### {c}"
            out.append(f"\n{head} — {s['title']}\n")
            out.append(f"Lands here: {', '.join(f'{k} ({v})' for k, v in s['landing'].items()) or 'its own merged text'}\n")
            out.append("Merged change (end state; line numbers are at the A-L HEAD, locate by quoted text):\n")
            out.append(changes.get(c, "(missing)"))
            out.append(f"\nCarried actions (texts at the end): {', '.join(s['carries'])}\n")
            seen += [x for x in s["carries"] if x not in seen]
    out.append("\n# Carried action texts\n")
    for aid in seen:
        out.append(actions.get(aid, "(missing)") + "\n")
    text = "\n".join(out)
    if a.outdir:
        Path(a.outdir).mkdir(parents=True, exist_ok=True)
        name = a.unit + (f"_lanes_{a.lane_set.replace(',', '-')}" if a.lane_set else "")
        (Path(a.outdir) / f"{name}.md").write_text(text)
        print(f"{name}: {sum(len(g) for g in order)} steps, {len(text)} chars")
    else:
        print(text)


if __name__ == "__main__":
    main()
