# M.PROC.023: writes levels.md's file x level rows and intent.md's catalog-code rows below their headers, by reference search.
# Usage: python3 -I audit/b3/levels_walk.py <tree>. A reference is a whole-word mention; the campaign checks each cell bites.
import re, subprocess, sys
from pathlib import Path

tree = Path(sys.argv[1])
LEVELS = {
    "L0": [p for g in ("tests_scripts/*.py", "tests_js/*.js") for p in tree.glob(g)],
    "L1": [p for p in tree.glob("tests/test_*.py") if not p.name.startswith("test_digital_twin_")] + list(tree.glob("tests/lwip_host/test_*.py")),
    "L2": list(tree.glob("tests/test_digital_twin_*.py")) + [tree / "scripts/_digital_twin_scenarios.py"],
    "L3": [p for g in ("tests_hardware/flash/*.py", "tests_hardware/device_scripts/*.py") for p in tree.glob(g)],
    "L4": list(tree.glob("tests_hardware/bench/*.py")),
}
TEXT = {lv: {p: p.read_text(encoding="utf-8", errors="replace") for p in ps} for lv, ps in LEVELS.items()}
GENERATED = {p.stem: p.read_text(encoding="utf-8") for p in tree.glob("build/generated_src/sensortask_*.py")}
IMPORTS = re.compile(r"^\s*(?:from (\w+) import|import (\w+))", re.M)
SRC = {p.stem: {a or b for a, b in IMPORTS.findall(p.read_text(encoding="utf-8"))} for p in tree.glob("src/*.py")}
BOOTED = {}  # src module -> devices whose generated module reaches it through imports
for device, text in GENERATED.items():
    todo = [m for pair in IMPORTS.findall(text) for m in pair if m in SRC]
    seen = set()
    while todo:
        m = todo.pop()
        if m not in seen:
            seen.add(m)
            todo += [n for n in SRC[m] if n in SRC]
    for m in seen:
        BOOTED.setdefault(m, set()).add(device)
SUBJECTS = [*sorted(tree.glob("src/*.py")), *sorted(tree.glob("buildgen/*.py")),
            *sorted(tree.glob("toolchain/*.py")), *sorted(p for p in tree.glob("scripts/*") if p.is_file()), *sorted(tree.glob("digital_twin/*.py")),
            *sorted(tree.glob("js/**/*.js")), *sorted(tree.glob(".github/workflows/*.yml")), *sorted(tree.glob(".github/actions/*/action.yml"))]


def refs(level, names):
    pattern = re.compile("|".join(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])" for n in names))
    return sorted(p.name for p, text in TEXT[level].items() if pattern.search(text))


def cell(found):
    return "-" if not found else f"{len(found)}: " + ", ".join(found[:3]) + (" …" if len(found) > 3 else "")


def keep_header(path):
    return path.read_text(encoding="utf-8").split("\n## ")[0].rstrip() + "\n"


src_head = subprocess.run(["git", "-C", str(tree), "log", "-1", "--format=%h"], capture_output=True, text=True, check=False).stdout.strip() or "unknown"  # never an empty stamp
rows, gaps = [], 0
for path in SUBJECTS:
    rel = path.relative_to(tree).as_posix()
    names = {path.name} | ({path.stem} if path.suffix == ".py" and path.stem not in ("__init__", "conftest") else set())
    if rel.startswith(".github/actions/"):
        names = {path.parent.name}
    found = {lv: refs(lv, names) for lv in LEVELS}
    booted = sorted(BOOTED.get(path.stem, ())) if rel.startswith("src/") else []
    note = f"booted on {len(booted)} device(s) by the twin CI (L2 real chain)" if booted else ""
    gap = "" if any(found.values()) or booted else "gap: no test names it"
    gaps += bool(gap)
    rows.append(f"| {rel} | {cell(found['L0'])} | {cell(found['L1'])} | {cell(found['L2'])}{'; ' + note if note else ''} | {cell(found['L3'])} | {cell(found['L4'])} | {gap or 'open: confirm the cells bite (review.md)'} |")
# The generated modules, one row per kind: a device name appears only under devices/ (convention), never here.
for suffix, l1, l2, rest in (("", "tests/test_sensortask.py, every device (through tests/_generated_module.py)", "the twin CI boots it for every device (run_digital_twin_ci.sh <device>)", "open: confirm the cells bite (review.md)"),
                             ("_main", "-", "-", "open: the firmware entry point, reached on silicon (L3/L4) and by the firmware build; confirm the L0 cell"),
                             ("_main_noautostart", "-", "-", "open: the no-autostart entry point; confirm its L0 and L3 cells")):
    n = sum(1 for d in GENERATED if not d.endswith(("_main", "_main_noautostart"))) if suffix == "" else sum(1 for d in GENERATED if d.endswith(suffix) and not (suffix == "_main" and d.endswith("_noautostart")))
    rows.append(f"| build/generated_src/sensortask_<device>{suffix}.py ({n} devices) | - | {l1} | {l2} | - | - | {rest} |")
levels = tree / "audit/b3/levels.md"
levels.write_text(keep_header(levels) + f"\n## Matrix\n\nBuilt by `audit/b3/levels_walk.py` at `{src_head}` (agent, 2026-10-22): {len(rows)} files, {gaps} named by no test at any level. A cell is the\ntest files mentioning the file at that level; whether each bites is review.md's. The multi-chunk SET ladder (A.U35.22 (1)) is open.\n\n| file | L0 | L1 | L2 | L3 | L4 | gap → action |\n|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n", encoding="utf-8")

irows = []
for path in sorted(tree.glob("src/*.py")):
    text = path.read_text(encoding="utf-8")
    direct = (tree / "tests" / f"test_{path.stem}.py").exists()
    chain = bool(refs("L2", {path.stem})) or bool(BOOTED.get(path.stem))
    raises, excepts = len(re.findall(r"^\s*raise\b", text, re.M)), len(re.findall(r"^\s*except\b", text, re.M))
    irows.append(f"| module | {path.name} | direct row (tests/test_{path.stem}.py) / real-chain row (L2 mention or booted) | {path.name}: {raises} raise, {excepts} except sites | {'yes' if direct else '-'} / {'yes' if chain else '-'} | {'' if direct and chain else 'gap: ' + ('no direct file ' if not direct else '') + ('no L2 mention' if not chain else '')} |")
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r"_(ERR|WRN)_([A-Z0-9_]+) = const\((\d+)\)", line)
        if not m:
            continue
        kind, name, num = m.groups()
        hits = [f"{lv} {cell(refs(lv, {name}))}" for lv in LEVELS if refs(lv, {name})]
        irows.append(f"| function | {path.name} | {'E' if kind == 'ERR' else 'W'} {name} ({num}) | src/{path.name}:{n} | {'; '.join(hits) or '-'} | {'' if hits else 'gap: no test names the code'} |")
intent = tree / "audit/b3/intent.md"
intent.write_text(keep_header(intent) + f"\n## Items\n\nBuilt by `audit/b3/levels_walk.py` at `{src_head}` (agent, 2026-10-22): per module its direct and real-chain rows, then each catalog code\nit defines with the tests naming it. Schema bounds, `None` and NaN/±inf rows, and the functional and system integration layers, are open.\n\n| layer | module | intent item | source | biting tests (level) | gap → action |\n|---|---|---|---|---|---|\n" + "\n".join(irows) + "\n", encoding="utf-8")
print(len(rows), "files,", gaps, "gaps;", len(irows), "intent rows,", sum("gap:" in r for r in irows), "intent gaps")
