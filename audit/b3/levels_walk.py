# M.PROC.023: writes levels.md's file x level rows and intent.md's rows below their headers (agent, 2026-10-27).
# Usage: python3 -I audit/b3/levels_walk.py <tree>. A cell names the test functions that drive a file at a level, each
# joined with review.md's verdict; the old file-level reference search must stay a superset of them, or the walk fails.
import ast
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tokenize
from collections import Counter, defaultdict
from pathlib import Path

tree = Path(sys.argv[1]).resolve()
LEVELS = {
    "L0": [p for g in ("tests_scripts/*.py", "tests_js/*.js") for p in tree.glob(g)],
    "L1": [p for p in tree.glob("tests/test_*.py") if not p.name.startswith("test_digital_twin_")] + list(tree.glob("tests/lwip_host/test_*.py")),
    "L2": list(tree.glob("tests/test_digital_twin_*.py")) + [tree / "scripts/_digital_twin_scenarios.py"],
    "L3": [p for g in ("tests_hardware/flash/*.py", "tests_hardware/device_scripts/*.py") for p in tree.glob(g)],
    "L4": list(tree.glob("tests_hardware/bench/*.py")),
}
# The generated module's own rows also read the two scenario libraries their per-device test files register.
EXTRA = {"L1": [tree / "tests/_sensortask_scenarios.py"], "L2": [tree / "tests/_digital_twin_construction_scenarios.py"]}
TEXT = {lv: {p: p.read_text(encoding="utf-8", errors="replace") for p in ps} for lv, ps in LEVELS.items()}
GENERATED = {p.stem: p.read_text(encoding="utf-8") for p in tree.glob("build/generated_src/sensortask_*.py")}
DEVICES = sorted(p.stem for p in tree.glob("devices/*.toml"))
IMPORTS = re.compile(r"^\s*(?:from (\w+) import|import (\w+))", re.M)
SRC = {p.stem: {a or b for a, b in IMPORTS.findall(p.read_text(encoding="utf-8"))} for p in tree.glob("src/*.py")}
BOOTED: dict[str, set[str]] = {}  # src module -> devices whose generated modules (graph and both entries) reach it
for device in DEVICES:
    todo = [m for stem in (f"sensortask_{device}", f"sensortask_{device}_main", f"sensortask_{device}_main_noautostart") for pair in IMPORTS.findall(GENERATED.get(stem, "")) for m in pair if m in SRC]
    seen: set[str] = set()
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
BASENAMES = Counter(p.name for d in ("src", "buildgen", "toolchain", "scripts", "digital_twin", "js", "tests", "tests_scripts", "tests_hardware", "tests_js", ".github", "html")
                    for p in (tree / d).rglob("*") if p.is_file() and "node_modules" not in p.parts)
COLLIDING = {p.stem for p in tree.glob("digital_twin/*.py") if (tree / "tests" / p.name).exists()}  # tests/ shadows these at L1


def _load(name: str, path: Path) -> "object":
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RF = _load("redflags", tree / "audit/sweeps/redflags.py")
RR = _load("review_rows", tree / "audit/sweeps/review_rows.py")
RECORDS = RF.scan(tree)  # type: ignore[attr-defined]
_VERDICTS = json.loads((tree / "audit/sweeps/review_verdicts.json").read_text(encoding="utf-8"))
VERDICT = {str(r["key"]): RR.row_verdict(r, _VERDICTS)[0] for r in RECORDS}  # type: ignore[attr-defined]
TERMINAL = set(RR.TERMINAL)  # type: ignore[attr-defined]
DATA = json.loads((tree / "audit/b3/levels_data.json").read_text(encoding="utf-8"))
USED: set[str] = set()  # data keys a row consumed; one left over is stale, and the walk fails
BY_FILE: dict[str, list[dict[str, object]]] = defaultdict(list)
for _r in RECORDS:
    BY_FILE[str(_r["file"])].append(_r)


class Piece:
    # A test function (a unit, with its review key) or a helper definition of its file (a carrier candidate).
    def __init__(self, key: str, names: set[str], code: str, idents: set[str], local: set[str], imports: list[tuple[str, str | None]], strings: set[str]) -> None:
        self.key, self.names, self.code, self.idents, self.local, self.imports, self.strings = key, names, code, idents, local, imports, strings


class Analysis:
    def __init__(self, units: list[Piece], defs: list[Piece], twin_path: bool) -> None:
        self.units, self.defs, self.twin_path = units, defs, twin_path


def _blank(buf: list[list[str]], sl: int, sc: int, el: int, ec: int) -> None:
    for ln in range(sl, el + 1):
        row = buf[ln - 1]
        for k in range(sc if ln == sl else 0, min(ec if ln == el else len(row), len(row))):
            if row[k] != "\n":
                row[k] = " "


def _py_info(nodes: "list[ast.AST]", docstrings: set[int]) -> "tuple[set[str], set[str], list[tuple[str, str | None]], set[str]]":
    idents, local, imports, strings = set(), set(), [], set()
    for n in nodes:
        for x in ast.walk(n):
            if isinstance(x, ast.Name):
                idents.add(x.id)
                if isinstance(x.ctx, (ast.Store, ast.Del)):
                    local.add(x.id)
            elif isinstance(x, ast.Attribute):
                idents.add(x.attr)
            elif isinstance(x, ast.arg):
                idents.add(x.arg)
            elif isinstance(x, ast.Import):
                imports += [(a.name, None) for a in x.names]
            elif isinstance(x, ast.ImportFrom):
                imports += [(x.module or "", a.name) for a in x.names]
            elif isinstance(x, ast.Constant) and isinstance(x.value, str) and id(x) not in docstrings:
                strings.add(x.value)
    return idents, local, imports, strings


def _bound(node: ast.AST) -> set[str]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {node.name}
    targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, (ast.AnnAssign, ast.AugAssign)) else []
    return {x.id for t in targets for x in ast.walk(t) if isinstance(x, ast.Name)}


def _stmts(body: "list[ast.stmt]") -> "list[ast.stmt]":
    out: list[ast.stmt] = []
    for s in body:
        if isinstance(s, (ast.If, ast.Try, ast.With)):
            out += _stmts(s.body) + [x for h in getattr(s, "handlers", []) for x in _stmts(h.body)] + _stmts(getattr(s, "orelse", [])) + _stmts(getattr(s, "finalbody", []))
        else:
            out.append(s)
    return out


def analyse_py(rel: str, text: str) -> Analysis:
    try:
        mod = ast.parse(text)
    except SyntaxError:
        return Analysis([], [], False)
    lines = text.splitlines(keepends=True)
    buf = [list(line) for line in lines]
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                _blank(buf, tok.start[0], tok.start[1], tok.end[0], tok.end[1])
    except (tokenize.TokenError, SyntaxError):
        pass
    docstrings: set[int] = set()
    for n in ast.walk(mod):
        body = getattr(n, "body", None)
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            d = body[0].value
            docstrings.add(id(d))
            ch = lambda ln, bc: len(lines[ln - 1].encode("utf-8")[:bc].decode("utf-8", "ignore"))  # noqa: E731
            _blank(buf, d.lineno, ch(d.lineno, d.col_offset), d.end_lineno or d.lineno, ch(d.end_lineno or d.lineno, d.end_col_offset or 0))

    def code(a: int, b: int) -> str:
        return "".join("".join(buf[i]) for i in range(a - 1, min(b, len(buf))))

    by_line = {n.lineno: n for n in ast.walk(mod) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    units, unit_nodes = [], set()
    if rel.startswith("tests_hardware/device_scripts/") and f"{rel}::{Path(rel).stem}" in VERDICT:
        idents, local, imports, strings = _py_info([mod], docstrings)
        units.append(Piece(f"{rel}::{Path(rel).stem}", set(), code(1, len(buf)), idents, set(), imports, strings))
        return Analysis(units, [], False)
    records = BY_FILE.get(rel) or [{"line": n.lineno, "test": n.name} for n in mod.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")]
    for r in records:
        node = by_line.get(int(r["line"]))  # type: ignore[call-overload]
        if node is None:
            continue
        unit_nodes.add(id(node))
        first = min([d.lineno for d in node.decorator_list] + [node.lineno])
        idents, local, imports, strings = _py_info([node], docstrings)
        units.append(Piece(f"{rel}::{r['test']}", set(), code(first, node.end_lineno or node.lineno), idents, local - {a.arg for a in ast.walk(node) if isinstance(a, ast.arg)}, imports, strings))
    defs = []
    for s in _stmts(mod.body):
        if id(s) in unit_nodes:
            continue
        if isinstance(s, (ast.Import, ast.ImportFrom)):
            for a in s.names:
                bound = (a.asname or a.name.split(".")[0]) if isinstance(s, ast.Import) else (a.asname or a.name)
                defs.append(Piece("", {bound}, code(s.lineno, s.end_lineno or s.lineno), set(), set(), [(a.name, None) if isinstance(s, ast.Import) else (s.module or "", a.name)], set()))
        elif isinstance(s, ast.ClassDef):
            members = [m for m in _stmts(s.body) if id(m) not in unit_nodes]
            for m in members:
                if _bound(m):
                    i, _l, im, st = _py_info([m], docstrings)
                    defs.append(Piece("", _bound(m), code(m.lineno, m.end_lineno or m.lineno), i, set(), im, st))
            i, _l, im, st = _py_info(members + s.bases + s.decorator_list, docstrings)
            defs.append(Piece("", {s.name}, "".join(code(m.lineno, m.end_lineno or m.lineno) for m in members), i, set(), im, st))
        elif _bound(s):
            i, _l, im, st = _py_info([s], docstrings)
            defs.append(Piece("", _bound(s), code(getattr(s, "decorator_list", [s])[0].lineno if getattr(s, "decorator_list", None) else s.lineno, s.end_lineno or s.lineno), i, set(), im, st))
    twin_path = bool(re.search(r"sys\.path\.(?:insert|append)\([^)\n]*[\"']digital_twin[\"']", text))
    return Analysis(units, defs, twin_path)


def _js_comments_blanked(text: str) -> str:
    # redflags.js_mask's scanner, blanking comments only: strings stay, since a path in a string is a reference.
    masked, out = RF.js_mask(text), list(text)  # type: ignore[attr-defined]
    i = 0
    while i < len(text):
        if masked[i] == " " and text[i] == "/" and i + 1 < len(text) and text[i + 1] in "/*":
            end = text.find("\n", i) if text[i + 1] == "/" else text.find("*/", i + 2) + 2
            end = len(text) if end < (1 if text[i + 1] == "/" else 2) else end
            if masked[i:end].strip() == "":
                for k in range(i, end):
                    if out[k] != "\n":
                        out[k] = " "
                i = end
                continue
        i += 1
    return "".join(out)


JS_IDENT = re.compile(r"[A-Za-z_$][\w$]*")


def _js_spans(text: str) -> "list[tuple[int, str, int, int]]":
    # redflags.js_tests' own test finder, so each span lines up with its review row (same order, same skips).
    masked, out = RF.js_mask(text), []  # type: ignore[attr-defined]
    for m in re.finditer(r"(?<![\w$.])(it|test)\b", masked):
        j, chain = m.end(), []
        while True:
            k = j
            while k < len(masked) and masked[k] in " \t\n":
                k += 1
            if k < len(masked) and masked[k] == "." and (mm := re.match(r"\.\s*([A-Za-z_$][\w$]*)", masked[k:])):
                chain.append(mm.group(1))
                j = k + mm.end()
                continue
            j = k
            break
        if j >= len(masked) or masked[j] != "(":
            continue
        end = RF.match_close(masked, j)  # type: ignore[attr-defined]
        if set(chain) & {"each", "skipIf", "runIf", "for"}:
            k = end + 1
            while k < len(masked) and masked[k] in " \t\n":
                k += 1
            if k < len(masked) and masked[k] == "(":
                end = RF.match_close(masked, k)  # type: ignore[attr-defined]
        if "todo" in chain:
            continue
        out.append((text.count("\n", 0, m.start()) + 1, m.start(), end))
    return [(line, "", a, b) for line, a, b in out]


def analyse_js(rel: str, text: str) -> Analysis:
    masked, plain = RF.js_mask(text), _js_comments_blanked(text)  # type: ignore[attr-defined]
    recs = [r for r in BY_FILE.get(rel, []) if r["level"] == "web (vitest)"]
    spans = _js_spans(text)
    units = []
    if len(spans) == len(recs) and all(int(r["line"]) == s[0] for r, s in zip(recs, spans)):  # type: ignore[call-overload]
        for r, (_line, _n, a, b) in zip(recs, spans):
            units.append(Piece(str(r["key"]), set(), plain[a : b + 1], set(JS_IDENT.findall(masked[a : b + 1])), set(), [], set()))
    elif recs:
        raise SystemExit(f"levels_walk: {rel}'s test spans do not line up with its review rows")
    covered = [(a, b) for _l, _n, a, b in spans]
    starts = [m.start() for m in re.finditer(r"^(?=[^\s})\]])", masked, re.M)] + [len(text)]
    defs = []
    for s, e in zip(starts, starts[1:]):
        inner = [(a, b) for a, b in covered if s <= a < e]
        seg_m, seg_p = list(masked[s:e]), list(plain[s:e])
        for a, b in inner:
            for k in range(a - s, min(b + 1 - s, e - s)):
                seg_m[k] = seg_p[k] = " "
        m_text, p_text = "".join(seg_m), "".join(seg_p)
        head = m_text.lstrip()
        names: set[str] = set()
        if im := re.match(r"import\s+([\s\S]*?)\s+from\b", head):
            for item in im.group(1).replace("{", ",").replace("}", ",").split(","):
                parts = item.split()
                if parts:
                    names.add(parts[-1])
        elif dm := re.match(r"(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\s*\*?|class|const|let|var)\s*([\w$]+|\{[^}]*\}|\[[^\]]*\])", head):
            names |= set(JS_IDENT.findall(dm.group(1))) - {"as"}
        if inner or not names:  # a describe block or a hook: what its preamble declares or assigns
            names |= set(re.findall(r"\b(?:const|let|var|function|class)\s+([\w$]+)", m_text)) | set(re.findall(r"(?<![\w$.])([\w$]+)\s*=(?![=>])", m_text))
        if names:
            defs.append(Piece("", names, p_text, set(JS_IDENT.findall(m_text)), set(), [], set()))
    return Analysis(units, defs, False)


_ANALYSIS: dict[Path, Analysis] = {}


def analysis(p: Path) -> Analysis:
    if p not in _ANALYSIS:
        rel, text = p.relative_to(tree).as_posix(), p.read_text(encoding="utf-8", errors="replace")
        _ANALYSIS[p] = analyse_js(rel, text) if p.suffix == ".js" else analyse_py(rel, text)
    return _ANALYSIS[p]


class Subject:
    # What counts as a reference to one file: qualified forms anywhere in code, its bare stem only where it names it.
    def __init__(self, rel: str) -> None:
        p = Path(rel)
        self.rel, self.top = rel, p.parts[0]
        self.old = {p.name} | ({p.stem} if p.suffix == ".py" and p.stem not in ("__init__", "conftest") else set())
        qual = {rel}
        if rel.startswith(".github/actions/"):
            self.old = qual = {p.parent.name}
        elif p.suffix == ".py":
            qual |= {rel[:-3], rel[:-3].replace("/", ".")}
        if BASENAMES[p.name] == 1 and not rel.startswith(".github/actions/"):
            qual.add(p.name)
        self.stem = p.stem if p.suffix == ".py" and p.stem not in ("__init__", "conftest") else None
        self.qual = qual
        self.qual_re = re.compile("|".join(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])" for n in sorted(qual)))
        self.bare_string = self.stem is not None and self.top in ("src", "scripts", "toolchain", "digital_twin") and self.stem not in COLLIDING
        self.stem_re = re.compile(r"(?<![\w-])" + re.escape(self.stem or "") + r"(?![\w-])")  # the stem as a word inside a string

    def mentioned(self, code: str) -> bool:
        return any(q in code for q in self.qual) and bool(self.qual_re.search(code))

    def imported(self, mod: str, name: "str | None", twin_path: bool) -> bool:
        if self.stem is None:
            return False
        if self.top == "buildgen":
            return mod in (f"buildgen.{self.stem}",) or mod.startswith(f"buildgen.{self.stem}.") or (mod == "buildgen" and name == self.stem)
        if self.top in ("src", "scripts", "toolchain", "digital_twin") and (self.stem not in COLLIDING or twin_path):
            return mod == self.stem or mod.startswith(self.stem + ".")
        return False

    def hit(self, piece: Piece, twin_path: bool) -> bool:
        return self.mentioned(piece.code) or any(self.imported(m, n, twin_path) for m, n in piece.imports) or (self.bare_string and any(self.stem in x and self.stem_re.search(x) for x in piece.strings))


class Word:
    # A catalog code's name, or one of the generated modules' own reference patterns: a regex over a piece's code.
    def __init__(self, pattern: str, probe: "list[str]") -> None:
        self.rx, self.probe = re.compile(pattern), probe

    def hit(self, piece: Piece, _twin_path: bool) -> bool:
        return any(p in piece.code for p in self.probe) and bool(self.rx.search(piece.code))


def driving(a: Analysis, subj: "Subject | Word") -> list[str]:
    car: set[str] = set()
    hit = [False] * len(a.defs)
    changed = True
    while changed:
        changed = False
        for i, d in enumerate(a.defs):
            if not hit[i] and (subj.hit(d, a.twin_path) or d.idents & car):
                hit[i], changed = True, True
                car |= d.names
    every = "pytestmark" in car
    return [u.key for u in a.units if every or subj.hit(u, a.twin_path) or (u.idents - u.local) & car]


def old_refs(level: str, names: set[str]) -> list[Path]:
    pattern = re.compile("|".join(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])" for n in sorted(names)))
    return sorted((p for p, text in TEXT[level].items() if any(n in text for n in names) and pattern.search(text)), key=lambda p: p.name)


class Cell:
    def __init__(self, keys: list[str], old: list[Path]) -> None:
        self.keys, self.old = keys, old
        self.biting = [k for k in keys if VERDICT.get(k) in TERMINAL]
        self.reason = ""  # why a "-" cell needs no test at its level, from levels_data.json's dash_reasons
        self.hand = 0  # how many of keys levels_data.json names by hand

    @property
    def state(self) -> str:
        return "-" if not self.keys else "bites" if self.biting else "open"

    def text(self) -> str:
        why = f"; {self.reason}" if self.reason else ""
        if not self.old:
            return f"- ({self.reason})" if self.reason else "-"
        if not self.keys:  # a mention no test function drives (a comment, a helper's import, a name shared with another file)
            return "- (mentioned only in " + ", ".join(p.name for p in self.old[:3]) + (" …" if len(self.old) > 3 else "") + why + ")"
        shown = (self.biting or self.keys)[:3]
        files = len({k.split("::")[0] for k in self.keys})
        head = f"{len(self.biting)}/{len(self.keys)} biting in {files} file(s)" if self.biting else "open: " + ", ".join(f"{v or 'no review row'} {n}" for v, n in Counter(VERDICT.get(k) for k in self.keys).items())
        return head + (f" ({self.hand} named by hand)" if self.hand else "") + ": " + ", ".join(Path(k.split("::")[0]).name + "::" + k.split("::", 1)[1] for k in shown) + (" …" if len(self.keys) > 3 else "")


SUPERSET_FAILS: list[str] = []
REACHED: set[str] = set()
DUMP: dict[str, dict[str, list[str]]] = {}  # row -> level -> keys, written only with --dump <path> (outside the tree)


_DRIVING: dict[tuple[Path, str], list[str]] = {}


def driving_cached(p: Path, subj: "Subject | Word") -> list[str]:
    tag = subj.rel if isinstance(subj, Subject) else subj.rx.pattern
    if (p, tag) not in _DRIVING:
        _DRIVING[(p, tag)] = driving(analysis(p), subj)
    return _DRIVING[(p, tag)]


def cell_for(level: str, subj: "Subject | Word", old_names: set[str], extra: bool = False) -> Cell:
    # Every file at the level is searched, not only the old cell's, so the superset check below can fail.
    files = [p for p in sorted(TEXT[level], key=lambda p: p.name) if any(n in TEXT[level][p] for n in old_names)]
    keys = [k for p in files for k in driving_cached(p, subj)]
    if extra:  # the generated modules: no old reference cell to hold them to; the files they were found in stand for it
        keys += [k for p in EXTRA.get(level, []) for k in driving_cached(p, subj)]
        return Cell(keys, sorted({tree / k.split("::")[0] for k in keys}, key=lambda p: p.name))
    old = old_refs(level, old_names)
    stray = {k.split("::")[0] for k in keys} - {p.relative_to(tree).as_posix() for p in old}
    if stray:
        SUPERSET_FAILS.append(f"{level} {sorted(old_names)}: {sorted(stray)}")
    return Cell(keys, old)


def dash_reason(rel: str, level: str) -> str:
    # The first dash_reasons entry whose pattern matches the file and whose levels hold this one; "" when none does.
    for entry in DATA["dash_reasons"]:
        if level in entry["levels"] and re.search(entry["match"], rel):
            USED.add("dash_reasons/" + entry["match"] + "/" + ",".join(entry["levels"]))
            return str(entry["reason"])
    return ""


def curated(keys: "list[str]", where: str) -> Cell:
    # A cell whose functions levels_data.json names: each must be a test the scan knows, or the walk fails.
    missing = [k for k in keys if k not in VERDICT]
    if missing:
        SUPERSET_FAILS.append(f"{where}: levels_data.json names tests the scan does not know: {missing}")
    REACHED.update(keys)
    return Cell(list(keys), sorted({tree / k.split("::")[0] for k in keys}, key=lambda p: p.name))


def keep_header(path: Path) -> str:
    return path.read_text(encoding="utf-8").split("\n## ")[0].rstrip() + "\n"


src_head = subprocess.run(["git", "-C", str(tree), "log", "-1", "--format=%h"], capture_output=True, text=True, check=False).stdout.strip() or "unknown"  # never an empty stamp
rows, gaps, states = [], 0, Counter()
for path in SUBJECTS:
    rel = path.relative_to(tree).as_posix()
    subj = Subject(rel)
    cells = {lv: cell_for(lv, subj, subj.old) for lv in LEVELS}
    REACHED.update(k for c in cells.values() for k in c.keys)
    DUMP[rel] = {lv: c.keys for lv, c in cells.items()}
    for lv, given in DATA["curated_cells"].get(rel, {}).items():  # named by hand where no mechanical reference reaches
        USED.add(f"curated_cells/{rel}/{lv}")
        if isinstance(given, list):
            cells[lv] = curated(cells[lv].keys + [k for k in given if k not in cells[lv].keys], f"{rel} {lv}")
            cells[lv].hand = len(given)
        else:
            cells[lv].reason = given
    for lv, c in cells.items():
        c.reason = c.reason or (dash_reason(rel, lv) if c.state == "-" else "")
    booted = sorted(BOOTED.get(path.stem, ())) if rel.startswith("src/") else []
    note = f"; booted on {len(booted)} device(s) by the generated graph (L2 real chain)" if booted else ""
    gap = not any(c.old for c in cells.values()) and not booted
    gaps += gap
    open_lv = [lv for lv, c in cells.items() if c.state == "open"] + [lv + " '-' with no reason" for lv, c in cells.items() if c.state == "-" and not c.reason and not (lv == "L2" and booted)]
    state = "gap: no test names it" if gap else ("open: " + ", ".join(open_lv)) if open_lv else "closed: every level bites or states why it needs no test"
    states[state.split(":")[0]] += 1
    rows.append(f"| {rel} | {cells['L0'].text()} | {cells['L1'].text()} | {cells['L2'].text()}{note} | {cells['L3'].text()} | {cells['L4'].text()} | {state} |")
# The generated modules, one row per kind: a device name appears only under devices/ (convention), never here.
GEN = {
    "": (r"sensortask_\{|\bsensortask_<device>|\bboot_generated\b|\bload_device\b|\bregister_for_device\b|\b_generated_module\b", ["sensortask_", "boot_generated", "load_device", "register_for_device", "_generated_module"]),
    "_main": (r"\bboot_entry_source\b|sensortask_\{?\w*\}?_main(?![_\w])|\b_main\.py\b", ["boot_entry_source", "_main"]),
    "_main_noautostart": (r"\bboot_entry_noautostart_source\b|_main_noautostart\b", ["noautostart"]),
}
for suffix, (pattern, probe) in GEN.items():
    word = Word(pattern, probe)
    cells = {lv: cell_for(lv, word, set(probe), extra=True) for lv in LEVELS}
    REACHED.update(k for c in cells.values() for k in c.keys)
    DUMP[f"generated{suffix}"] = {lv: c.keys for lv, c in cells.items()}
    for lv, given in DATA["curated_cells"].get(f"generated{suffix}", {}).items():  # named by hand: the boot entry as main.py on silicon
        USED.add(f"curated_cells/generated{suffix}/{lv}")
        if isinstance(given, list):
            cells[lv] = curated(cells[lv].keys + [k for k in given if k not in cells[lv].keys], f"generated{suffix} {lv}")
            cells[lv].hand = len(given)
        else:
            cells[lv].reason = given
    for lv, c in cells.items():
        c.reason = c.reason or (dash_reason(f"build/generated_src/sensortask_<device>{suffix}.py", lv) if c.state == "-" else "")
    open_lv = [lv for lv, c in cells.items() if c.state == "open"] + [lv + " '-' with no reason" for lv, c in cells.items() if c.state == "-" and not c.reason]
    state = ("open: " + ", ".join(open_lv)) if open_lv else "closed: every level bites or states why it needs no test"
    states[state.split(":")[0]] += 1
    rows.append(f"| build/generated_src/sensortask_<device>{suffix}.py ({len(DEVICES)} devices) | {cells['L0'].text()} | {cells['L1'].text()} | {cells['L2'].text()} | {cells['L3'].text()} | {cells['L4'].text()} | {state} |")
lrows = []
for item in DATA["ladder"]:
    cell = curated(item["tests"], "ladder " + item["level"])
    lrows.append(f"| {item['level']} | {cell.text()} | {item['proves']} | {'biting' if cell.biting and len(cell.biting) == len(cell.keys) else 'open: ' + str(len(cell.keys) - len(cell.biting)) + ' not biting'}{'; ' + item['note'] if item.get('note') else ''} |")
nrows = []
for item in DATA["narrowings"]:
    cell = curated(item["covering_tests"], "narrowing " + item["test"])
    nrows.append(f"| {item['test']} | {item['narrowed_to']} | {item['covering_row']} | {cell.text()} | {'closed' if cell.biting else 'open'} |")
levels = tree / "audit/b3/levels.md"
levels.write_text(keep_header(levels) + f"\n## Matrix\n\nBuilt by `audit/b3/levels_walk.py` at `{src_head}` (agent, 2026-10-27): {len(rows)} files, {gaps} named by no test at any level; rows by state: {dict(states)}.\nA cell names the test functions driving the file at that level (its own code, or a helper of its file that does), counted against review.md's verdict: \"k/n biting\" names the biting ones first; \"open\" means no function there is verdicted biting, fixed or justified; \"- (mentioned only in …)\" is a mention no test function drives (a comment, a helper's import, a name another file shares). No-change proof, checked on every run (the walk fails otherwise): each cell's files lie inside the old file-level reference cell. A \"-\" carries its reason (levels_data.json's dash_reasons, first match); a row is closed when every level bites or states its reason.\n\n| file | L0 | L1 | L2 | L3 | L4 | gap → action |\n|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n\n## Multi-chunk SET ladder (A.U35.22 (1))\n\n" + DATA["ladder_intro"] + "\n\n| level | tests | proves | state |\n|---|---|---|---|\n" + "\n".join(lrows) + "\n\n## Single-device narrowings\n\n" + DATA["narrowings_intro"] + "\n\n| test | narrowed to | covering row | covering tests | state |\n|---|---|---|---|---|\n" + "\n".join(nrows) + "\n", encoding="utf-8")

irows, istates = [], Counter()
for path in sorted(tree.glob("src/*.py")):
    text = path.read_text(encoding="utf-8")
    subj = Subject(path.relative_to(tree).as_posix())
    direct_file = tree / "tests" / f"test_{path.stem}.py"
    direct = [k for k in (driving_cached(direct_file, subj) if direct_file.exists() else []) if VERDICT.get(k) in TERMINAL]
    chain = cell_for("L2", subj, subj.old)
    chain_ok = bool(chain.biting) or bool(BOOTED.get(path.stem))
    raises, excepts = len(re.findall(r"^\s*raise\b", text, re.M)), len(re.findall(r"^\s*except\b", text, re.M))
    row_gap = "" if direct and chain_ok else "gap: " + ("no biting direct test " if not direct else "") + ("no biting L2 function and not booted" if not chain_ok else "")
    istates["gap" if row_gap else "biting"] += 1
    irows.append(f"| module | {path.name} | direct row (tests/test_{path.stem}.py) / real-chain row (an L2 function, or booted) | {path.name}: {raises} raise, {excepts} except sites | {len(direct)} biting / {len(chain.biting)} L2 biting{', booted on ' + str(len(BOOTED.get(path.stem, ()))) if BOOTED.get(path.stem) else ''} | {row_gap} |")
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r"_(ERR|WRN)_([A-Z0-9_]+) = const\((\d+)\)", line)
        if not m:
            continue
        kind, name, num = m.groups()
        word = Word(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", [name])
        found = []
        for lv in LEVELS:
            c = cell_for(lv, word, {name})
            mod_ok = {p.relative_to(tree).as_posix() for p in c.old if driving_cached(p, subj) or any(subj.hit(d, analysis(p).twin_path) for d in analysis(p).defs)}
            c2 = Cell([k for k in c.keys if k.split("::")[0] in mod_ok], c.old)
            REACHED.update(c2.keys)
            if c2.keys or c.old:
                found.append(f"{lv} {c2.text()}")
        biting = any(" biting in " in f for f in found)
        istates["biting" if biting else "gap"] += 1
        note_key = f"{path.name} {'E' if kind == 'ERR' else 'W'} {name}"
        note = DATA["intent_notes"].get(note_key, "")
        USED.add(f"intent_notes/{note_key}") if note else None
        irows.append(f"| function | {path.name} | {'E' if kind == 'ERR' else 'W'} {name} ({num}) | src/{path.name}:{n} | {'; '.join(found) or '-'} | {note if biting else 'gap: no biting test function names the code and drives the module' + ('; ' + note if note else '')} |")
os.chdir(tree)  # tests/_schema_cases.py reads src/ paths relative to the tree, as the test runner does
sys.path.insert(0, str(tree / "tests"))
CASES = _load("_schema_cases", tree / "tests/_schema_cases.py")
SENSORS = ("bmp3xx", "scd30", "sgp40", "isl29125")
PLANTS = DATA["schema_plants"]
srows, sstates = [], Counter()
for driver in SENSORS:
    src = f"src/asy_{driver}_driver.py"
    lines = (tree / src).read_text(encoding="utf-8").splitlines()
    spec = DATA["schema_tests"][driver]
    for field in CASES.declared_fields(src):  # type: ignore[attr-defined]
        key = spec["comp"] if field[0] in spec.get("comp_fields", ()) else spec["put"]
        line = next(n for n, text in enumerate(lines, 1) if f'("{field[0]}", "{field[1]}"' in text)
        for label, value, inside in CASES.domain_cases(field):  # type: ignore[attr-defined]
            row = f"{field[0]}: {label}"
            bit = sorted(name for name, plant in PLANTS.items() if row in plant["rows"].get(driver, ()))
            verdict = VERDICT.get(key)
            REACHED.add(key)
            ok = verdict in TERMINAL and bool(bit)
            sstates["biting" if ok else "open"] += 1
            srows.append(f"| function | asy_{driver}_driver.py | {field[0]} ({field[1]}): {label} `{value!r}` → {'taken' if inside else 'refused'} | {src}:{line} | L1 {Path(key.split('::')[0]).name}::{key.split('::', 1)[1]} ({verdict or 'no review row'}) | {'biting: fails under ' + ', '.join(bit) if ok else 'open: ' + ('no plant fails this case' if not bit else str(verdict))} |")
LIMIT_TAG = re.compile(r"^# @limits (\w+) (?:in \{([^}]*)\}|(\S+)\.\.(\S+))\s*$", re.M)
for driver in SENSORS:
    src = f"src/asy_{driver}_driver.py"
    text = (tree / src).read_text(encoding="utf-8")
    for m in LIMIT_TAG.finditer(text):
        name, line = m.group(1), text[: m.start()].count("\n") + 1
        if m.group(2):
            choices = sorted(int(x, 0) for x in m.group(2).split(","))
            lcases = [("below the set's smallest", choices[0] - 1, False), ("the set's smallest", choices[0], True), ("the set's largest", choices[-1], True), ("above the set's largest", choices[-1] + 1, False)]
            lcases += [("a non-member inside the set's span", v, False) for v in range(choices[0], choices[-1]) if v not in choices][:1]
        else:
            low, high = int(m.group(3)), int(m.group(4))
            lcases = [("below the minimum", low - 1, False), ("the minimum", low, True), ("the maximum", high, True), ("above the maximum", high + 1, False)]
        lcases.append(("None: the device TOML leaves the key out (TOML has no null)", None, True))
        spec = DATA["limits_tests"][f"{driver}.{name}"]
        USED.add(f"limits_tests/{driver}.{name}")
        for label, value, inside in lcases:
            group = "omitted" if value is None else "taken" if inside else "refused"
            cell = curated(spec[group], f"limits {driver}.{name} {group}")
            ok = bool(cell.keys) and len(cell.biting) == len(cell.keys)
            sstates["biting" if ok else "open"] += 1
            srows.append(f"| function | asy_{driver}_driver.py | constructor `{name}` (`# @limits`): {label}{'' if value is None else f' `{value:#x}`' if name == 'address' else f' `{value}`'} → {'built' if inside else 'refused by the build'} | {src}:{line} | L0 {cell.text()} | {'biting' if ok else 'open'}{'; ' + spec['notes'][group] if spec.get('notes', {}).get(group) else ''} |")

SCENARIO_FILE = "scripts/_digital_twin_scenarios.py"
SCEN: dict[str, tuple[tuple[str, ...], str]] = {}
for node in ast.parse((tree / SCENARIO_FILE).read_text(encoding="utf-8")).body:
    for deco in getattr(node, "decorator_list", []):
        if isinstance(deco, ast.Call) and getattr(deco.func, "id", "") == "scenario" and deco.args and isinstance(deco.args[0], ast.Constant):
            kw = {k.arg: ast.literal_eval(k.value) for k in deco.keywords if k.arg in ("drivers", "first_device")}
            SCEN[str(deco.args[0].value)] = (tuple(kw.get("drivers", ())), str(kw.get("first_device", "")))
DEV_DRIVERS = {d: set(re.findall(r'^driver = "(\w+)"', (tree / "devices" / f"{d}.toml").read_text(encoding="utf-8"), re.M)) for d in DEVICES}
PER_DEVICE_FILES = {p.relative_to(tree).as_posix() for p in tree.glob("tests/test_*.py") if re.search(r"^PER_DEVICE = True$", p.read_text(encoding="utf-8"), re.M)}


def devices_of(key: str) -> "set[str] | None":
    # The generated devices a test runs its body on; None for one device the file picks for it (SPECIFICATION.md E.2.1).
    file, name = key.split("::", 1)
    if file == SCENARIO_FILE:
        drivers, first = SCEN[name]
        return None if first else {d for d in DEVICES if set(drivers) <= DEV_DRIVERS[d]}
    if file == "tests/_digital_twin_construction_scenarios.py" or (file in PER_DEVICE_FILES and file not in DATA["picking_files"]):
        return set(DEVICES)
    return None


def scope_text(keys: "list[str]") -> "tuple[str, bool]":
    # The devices the biting ones among `keys` cover together, and whether that is every generated device.
    covered: set[str] = set()
    picked = False
    for k in keys:
        if VERDICT.get(k) in TERMINAL:
            got = devices_of(k)
            covered |= got or set()
            picked = picked or got is None
    every = covered == set(DEVICES)
    text = "every device" if every else f"{len(covered)} of {len(DEVICES)} devices" + (" + a picked device" if picked else "") if covered else "a picked device (E.2.1)" if picked else "no device"
    return text, every


GEN_L2 = set(DUMP["generated"]["L2"])
frows, fstates = [], Counter()
for path in sorted(tree.glob("src/*.py")):
    mod = path.stem
    consumers = sorted(c for c, imported in SRC.items() if mod in imported and c in BOOTED)
    direct_gen = any(mod in {a or b for a, b in IMPORTS.findall(GENERATED.get(f"sensortask_{d}", ""))} for d in DEVICES)
    keys = [k for k in DUMP[f"src/{path.name}"]["L2"] if k in GEN_L2 and VERDICT.get(k) in TERMINAL]
    through = "itself"
    if not keys:
        for c in consumers:
            keys = [k for k in DUMP[f"src/{c}.py"]["L2"] if k in GEN_L2 and VERDICT.get(k) in TERMINAL]
            if keys:
                through = c + ".py"
                break
    REACHED.update(keys)
    booted = sorted(BOOTED.get(mod, ()))
    covered = set().union(*[devices_of(k) or set() for k in keys])
    picked = any(devices_of(k) is None for k in keys)
    scope = f"{len(covered & set(booted))} of the {len(booted)} booting devices" + (" + a picked device" if picked else "")
    ok = bool(keys) and bool(booted)
    fstates["biting" if ok else "gap"] += 1
    who = ", ".join(c + ".py" for c in consumers) + (", " if consumers and direct_gen else "") + ("the generated module" if direct_gen else "")
    shown = ", ".join(Path(k.split("::")[0]).name + "::" + k.split("::", 1)[1] for k in keys[:2]) + (" …" if len(keys) > 2 else "")
    frows.append(f"| functional | {path.name} | real consumer: {who or 'none in the generated graph'}; booted on {len(booted)} device(s) | the generated graph's import chain | L2 {len(keys)} biting, through {through}: {shown or '-'}; {scope} | {'biting' if ok else 'gap: no L2 function drives it in a generated graph'} |")

ROUTES = sorted({(r["method"], r["path"]) for d in DEVICES for r in json.loads((tree / f"build/generated_src/api/{d}.json").read_text(encoding="utf-8"))["routes"]})


class AllOf:
    # Every pattern in one piece's code (its own, or a helper's of its file): a route's method and its path.
    def __init__(self, patterns: "list[str]") -> None:
        self.rxs = [re.compile(x) for x in patterns]
        self.tag = "&".join(patterns)

    def hit(self, piece: Piece, _twin_path: bool) -> bool:
        return all(x.search(piece.code) for x in self.rxs)


L2_FILES = [*LEVELS["L2"], *EXTRA["L2"]]
syrows, systates = [], Counter()
for method, route in ROUTES:
    subj_r = AllOf([f'"{method}"', f'"{re.escape(route)}"'])
    keys = sorted({k for p in L2_FILES if route in p.read_text(encoding="utf-8", errors="replace") for k in driving(analysis(p), subj_r)})  # type: ignore[arg-type]
    keys += [k for k in DATA["route_tests"].get(f"{method} {route}", []) if k not in keys]
    USED.add(f"route_tests/{method} {route}") if f"{method} {route}" in DATA["route_tests"] else None
    cell = curated(keys, f"route {method} {route}")
    scope, every = scope_text(keys)
    ok = bool(cell.biting) and every
    systates["biting" if ok else "open"] += 1
    syrows.append(f"| system | REST | {method} {route} | build/generated_src/api/<device>.json | L2 {cell.text()}; {scope} | {'biting on every device' if ok else 'open: not on every device'} |")
for item in DATA["system_rows"]:
    cell = curated(item["tests"], "system " + item["feature"])
    scope, every = scope_text(item["tests"])
    applies = item.get("applies", "every device")
    ok = bool(cell.biting) and (every or applies != "every device")
    systates["biting" if ok else "open"] += 1
    syrows.append(f"| system | {item['area']} | {item['feature']} | {item['source']} | {cell.text()}; {scope} | {('biting' if ok else 'open') + ('; ' + item['note'] if item.get('note') else '')} |")

intent = tree / "audit/b3/intent.md"
intent.write_text(keep_header(intent) + f"\n## Items\n\nBuilt by `audit/b3/levels_walk.py` at `{src_head}` (agent, 2026-10-27): per module its direct and real-chain rows, then each catalog code\nit defines with the test functions naming it in a file that drives the module, joined with review.md's verdict; rows by state: {dict(istates)}.\n\n| layer | module | intent item | source | biting tests (level) | gap → action |\n|---|---|---|---|---|---|\n" + "\n".join(irows) + "\n\n## Schema bounds (function layer)\n\n" + DATA["schema_intro"] + f" Rows by state: {dict(sstates)}.\n\n| layer | module | intent item | source | biting tests (level) | gap → action |\n|---|---|---|---|---|---|\n" + "\n".join(srows) + "\n\n## Functional integration\n\n" + DATA["functional_intro"] + f" Rows by state: {dict(fstates)}.\n\n| layer | module | intent item | source | biting tests (level) | gap → action |\n|---|---|---|---|---|---|\n" + "\n".join(frows) + "\n\n## System integration\n\n" + DATA["system_intro"] + f" Rows by state: {dict(systates)}.\n\n| layer | area | intent item | source | biting tests (level); devices | gap → action |\n|---|---|---|---|---|---|\n" + "\n".join(syrows) + "\n", encoding="utf-8")
if "--dump" in sys.argv:
    Path(sys.argv[sys.argv.index("--dump") + 1]).write_text(json.dumps({"rows": DUMP, "unreached": sorted(str(r["key"]) for r in RECORDS if str(r["key"]) not in REACHED)}, indent=1), encoding="utf-8")
per_tier = Counter(str(r["level"]) for r in RECORDS if str(r["key"]) not in REACHED)
print(len(rows), "files,", gaps, "gaps, rows", dict(states), ";", len(irows), "intent rows", dict(istates), "; schema", dict(sstates), "; functional", dict(fstates), "; system", dict(systates), "; unreached test functions", sum(per_tier.values()), dict(per_tier))
STALE = [f"intent_notes/{k}" for k in DATA["intent_notes"] if f"intent_notes/{k}" not in USED]
STALE += ["dash_reasons/" + e["match"] + "/" + ",".join(e["levels"]) for e in DATA["dash_reasons"] if "dash_reasons/" + e["match"] + "/" + ",".join(e["levels"]) not in USED]
STALE += [f"curated_cells/{row}/{lv}" for row, cells in DATA["curated_cells"].items() for lv in cells if f"curated_cells/{row}/{lv}" not in USED]
STALE += [f"limits_tests/{k}" for k in DATA["limits_tests"] if f"limits_tests/{k}" not in USED]
STALE += [f"route_tests/{k}" for k in DATA["route_tests"] if f"route_tests/{k}" not in USED]
if STALE:
    print("STALE DATA (levels_data.json names a row the walk did not render):\n" + "\n".join(STALE))
    sys.exit(1)
if SUPERSET_FAILS:
    print("SUPERSET FAILS:\n" + "\n".join(SUPERSET_FAILS))
    sys.exit(1)
print("superset: every function-level cell's files are inside the old reference cell")
