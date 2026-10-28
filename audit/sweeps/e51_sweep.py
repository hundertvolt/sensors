"""Every src/ line one `scripts/test.sh --coverage` run did not execute, grouped by site with its enclosing function and
the condition that reaches it, joined with e51_verdicts.json's classes into audit/b3/e51.md (A.U35.41, A.U35.04).
`<venv>/bin/python3 -I audit/sweeps/e51_sweep.py [--data .coverage | --hits H.json (default: e51_hits.json, the run's src/ lines)] [--sites OUT] [--kinds] [--render] [--check] [--self-test]`."""

from __future__ import annotations

import argparse
import ast
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERDICTS = ROOT / "audit/sweeps/e51_verdicts.json"
TABLE = ROOT / "audit/b3/e51.md"

CLASSES = {
    "a": "reachable and untested: a direct test owed",
    "b": "guard of an overridable extension point or a documented runtime failure: kept",
    "c": "type-narrowing re-check: kept, stated in place",
    "d": "real feature not yet used by the product: kept",
    "e": "truly unreachable, not a feature or guard: removal proposed",
}

# Tracer false negatives (SPECIFICATION.md E.5.1, first paragraph), each counted only when its own evidence holds.
ARTIFACTS = {
    "private_const": "a `_NAME = const(...)` assignment, folded away at parse time (py/parse.c); counted when its module ran",
    "decorated_def": "a decorated def's own line: the event lands on the decorator line; counted when a decorator line ran",
    "while_true": "a bare `while True:` header (an unconditional jump); counted when its body ran",
    "pass_in_if": "a `pass` that is an `if` body fires no event; counted when its `if` header ran (the branch itself is unseen)",
    "typing_only": "an `if TYPE_CHECKING:` body, which never runs on MicroPython (typing has no runtime presence)",
    "elif_leaf_test": "an `elif` whose test is a bare name (or and/or/not of them): compiled by c_if_cond with no struct node, so no line is set (py/compile.c:400, :2841); counted when its branch or what follows it ran",
    "bare_annotation": "a value-less `x: T` in a class or module body compiles to no bytecode (py/compile.c:2029-2033); counted when its body ran",
}


def _blocks(node: ast.AST) -> list[tuple[str, list[ast.stmt], ast.AST]]:
    # Each statement list a node owns, with the kind of entry that reaches it and the node its condition reads.
    if isinstance(node, ast.Module):
        return [("module", node.body, node)]
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return [("def", node.body, node)]
    if isinstance(node, ast.ClassDef):
        return [("class", node.body, node)]
    if isinstance(node, ast.If):
        return [("if", node.body, node), ("else", node.orelse, node)]
    if isinstance(node, (ast.For, ast.AsyncFor)):
        return [("for", node.body, node), ("loop-else", node.orelse, node)]
    if isinstance(node, ast.While):
        return [("while", node.body, node), ("loop-else", node.orelse, node)]
    if isinstance(node, (ast.With, ast.AsyncWith)):
        return [("with", node.body, node)]
    if isinstance(node, ast.Try):
        return [("try", node.body, node), *[("except", h.body, h) for h in node.handlers], ("try-else", node.orelse, node), ("finally", node.finalbody, node)]
    if isinstance(node, ast.Match):
        return [("case", c.body, c) for c in node.cases]
    return []


def _span(node: ast.stmt) -> range:
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    return range(start, (node.end_lineno or node.lineno) + 1)


def _is_private_const(node: ast.stmt) -> bool:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.value, ast.Call):
        return False
    target, func = node.targets[0], node.value.func
    named = (isinstance(func, ast.Name) and func.id == "const") or (isinstance(func, ast.Attribute) and func.attr == "const")
    return isinstance(target, ast.Name) and target.id.startswith("_") and named


def _leafy(test: ast.expr) -> bool:
    if isinstance(test, ast.BoolOp):
        return all(_leafy(v) for v in test.values)
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return _leafy(test.operand)
    return isinstance(test, ast.Name)


def artifact_lines(tree: ast.Module, source: list[str], hit: set[int]) -> dict[int, str]:
    out: dict[int, str] = {}
    for parent in ast.walk(tree):
        if isinstance(parent, ast.If) and isinstance(parent.test, ast.Name) and parent.test.id == "TYPE_CHECKING" and parent.lineno in hit:
            out.update({line: "typing_only" for stmt in parent.body for line in _span(stmt)})
        for kind, block, _ctx in _blocks(parent):
            for node in block:
                if _is_private_const(node) and hit:
                    out[node.lineno] = "private_const"
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and any(d.lineno in hit for d in node.decorator_list):
                    out[node.lineno] = "decorated_def"
                elif isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value is True and any(line in hit for b in node.body for line in _span(b)):
                    out[node.lineno] = "while_true"
                elif isinstance(node, ast.Pass) and kind == "if" and parent.lineno in hit:  # type: ignore[attr-defined]
                    out[node.lineno] = "pass_in_if"
                elif isinstance(node, ast.If) and kind == "else" and source[node.lineno - 1].lstrip().startswith("elif") and _leafy(node.test) and any(line in hit for b in node.body + node.orelse for line in _span(b)):
                    out[node.lineno] = "elif_leaf_test"
                elif isinstance(node, ast.AnnAssign) and node.value is None and kind in ("class", "module") and any(line in hit for b in block for line in _span(b)):
                    out[node.lineno] = "bare_annotation"
    return out


def _terminates(block: list[ast.stmt]) -> bool:
    return bool(block) and isinstance(block[-1], (ast.Return, ast.Raise, ast.Continue, ast.Break))


def _entry(kind: str, ctx: ast.AST) -> str:
    u = ast.unparse
    texts = {
        "if": lambda c: f"`{u(c.test)}` true",
        "else": lambda c: f"`{u(c.test)}` false",
        "for": lambda c: f"`for {u(c.target)} in {u(c.iter)}` iterates",
        "while": lambda c: f"`while {u(c.test)}` iterates",
        "loop-else": lambda _c: "the loop ends without `break`",
        "with": lambda c: f"`with {', '.join(u(i) for i in c.items)}` runs its body",
        "try": lambda _c: "the `try` body runs",
        "except": lambda c: f"`except {u(c.type)}` catches" if c.type is not None else "a bare `except` catches",
        "try-else": lambda _c: "the `try` body raises nothing",
        "finally": lambda _c: "the `finally` body runs",
        "case": lambda c: f"`case {u(c.pattern)}` matches",
        "def": lambda c: f"`{c.name}` is called",
        "class": lambda c: f"class `{c.name}`'s body runs",
        "module": lambda _c: "the module is imported",
    }
    return texts[kind](ctx)


def _after(prev: ast.stmt, source: list[str]) -> str:
    # A run that starts after a live statement: reached when that statement falls through.
    tests: list[str] = []
    node: ast.stmt = prev
    while isinstance(node, ast.If) and _terminates(node.body):
        tests.append(f"`{ast.unparse(node.test)}` false")
        if not node.orelse:
            return ", ".join(tests)
        if len(node.orelse) != 1 or not isinstance(node.orelse[0], ast.If):
            break
        node = node.orelse[0]
    return f"`{source[prev.lineno - 1].strip()}` falls through"


def build_sites(rel: str, tree: ast.Module, source: list[str], statements: set[int], missing: set[int]) -> list[dict[str, object]]:
    sites: list[dict[str, object]] = []
    seen: dict[str, int] = {}

    def state(stmt: ast.stmt) -> str:
        lines = [line for line in _span(stmt) if line in statements]
        if not lines:
            return "neutral"
        return "dead" if all(line in missing for line in lines) else "live"

    def walk(kind: str, block: list[ast.stmt], ctx: ast.AST, qual: str) -> None:
        states = [state(s) for s in block]
        i = 0
        while i < len(block):
            if states[i] != "dead":
                node = block[i]
                inner = f"{qual}.{node.name}" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else qual
                inner = inner.removeprefix("<module>.")
                for k, b, c in _blocks(node):
                    walk(k, b, c, inner)
                i += 1
                continue
            j = i
            while j + 1 < len(block) and states[j + 1] in ("dead", "neutral"):
                j += 1
            while states[j] == "neutral":
                j -= 1
            lines = sorted(line for s in block[i : j + 1] for line in _span(s) if line in missing)
            if kind == "except" and isinstance(ctx, ast.ExceptHandler) and ctx.lineno in missing:
                lines.insert(0, ctx.lineno)
            prev = next((block[k] for k in range(i - 1, -1, -1) if states[k] != "neutral"), None)
            cond = _entry(kind, ctx) if prev is None else _after(prev, source)
            key = f"{rel}::{qual}::{cond}::{source[lines[0] - 1].strip()}"
            seen[key] = seen.get(key, 0) + 1
            key += f"#{seen[key]}" if seen[key] > 1 else ""
            span = f"{lines[0]}" if lines[0] == lines[-1] else f"{lines[0]}-{lines[-1]}"
            sites.append({"key": key, "file": rel, "qualname": qual, "condition": cond, "lines": lines, "range": span})
            i = j + 1

    walk("module", tree.body, tree, "<module>")
    placed = {line for s in sites for line in s["lines"]}  # type: ignore[attr-defined]
    for line in sorted(missing - placed):
        key = f"{rel}::orphan::{source[line - 1].strip()}"
        sites.append({"key": key, "file": rel, "qualname": "?", "condition": "a missed line inside a live statement", "lines": [line], "range": f"{line}"})
    return sites


def check(sites: list[dict[str, object]], verdicts: dict[str, dict[str, str]]) -> list[str]:
    problems: list[str] = []
    keys = {str(s["key"]) for s in sites}
    problems += [f"no verdict: {k}" for k in sorted(keys - verdicts.keys())]
    problems += [f"stale verdict (no such site): {k}" for k in sorted(verdicts.keys() - keys)]
    for k in sorted(keys & verdicts.keys()):
        v = verdicts[k]
        if v.get("class") not in CLASSES:
            problems.append(f"bad class {v.get('class')!r}: {k}")
        problems += [f"empty {field}: {k}" for field in ("verdict", "proof", "action") if not str(v.get(field, "")).strip()]
    return problems


def _hits_to_data(hits: dict[str, list[int]], root: Path, data_path: Path) -> None:
    import coverage  # noqa: PLC0415 - the venv's pinned coverage.py, the report's own analysis

    data = coverage.CoverageData(basename=str(data_path))
    data.add_lines({str(root / rel): sorted(set(lines)) for rel, lines in hits.items()})
    data.write()


def analyse(data_path: Path, root: Path, scope: str = "src") -> dict[str, tuple[set[int], set[int]]]:
    import coverage  # noqa: PLC0415

    cov = coverage.Coverage(data_file=str(data_path), config_file=False)
    cov.load()
    out: dict[str, tuple[set[int], set[int]]] = {}
    for path in sorted((root / scope).glob("**/*.py")):
        _, statements, _excluded, missing, _ = cov.analysis2(str(path))
        out[str(path.relative_to(root))] = (set(statements), set(missing))
    return out


def sweep(data_path: Path, root: Path) -> tuple[list[dict[str, object]], dict[str, list[str]], dict[str, list[int]]]:
    sites: list[dict[str, object]] = []
    artifacts: dict[str, list[str]] = {kind: [] for kind in ARTIFACTS}
    kinds: dict[str, list[int]] = {}
    for rel, (statements, missing) in analyse(data_path, root).items():
        text = (root / rel).read_text(encoding="utf-8")
        tree = ast.parse(text)
        source = text.splitlines()
        hit = statements - missing
        for line, kind in sorted(artifact_lines(tree, source, hit).items()):
            if line in missing:
                artifacts[kind].append(f"{rel}:{line}")
                missing = missing - {line}
        for node in ast.walk(tree):
            if isinstance(node, ast.stmt) and node.lineno in statements:
                tally = kinds.setdefault(type(node).__name__, [0, 0])
                tally[0 if node.lineno in hit else 1] += 1
        sites.extend(build_sites(rel, tree, source, statements, missing))
    return sites, artifacts, kinds


def render(sites: list[dict[str, object]], artifacts: dict[str, list[str]], verdicts: dict[str, dict[str, str]], header: str) -> str:
    rows = [header.rstrip("\n"), "", "| file:line range | function | reached when | class | verdict | proof or test | action |", "|---|---|---|---|---|---|---|"]
    for site in sites:
        v = verdicts.get(str(site["key"]), {})
        cells = [f"`{site['file']}:{site['range']}`", f"`{site['qualname']}`", str(site["condition"]), v.get("class", "OPEN"), v.get("verdict", ""), v.get("proof", ""), v.get("action", "")]
        rows.append("| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
    rows += ["", "## Tracer false negatives (executed, never recorded: E.5.1's first paragraph, plus elif_leaf_test and bare_annotation)", "", "| kind | lines | evidence |", "|---|---|---|"]
    for kind, where in artifacts.items():
        rows.append(f"| {kind} | {len(where)} | {ARTIFACTS[kind]} |")
    counts = {c: sum(1 for s in sites if verdicts.get(str(s["key"]), {}).get("class") == c) for c in CLASSES}
    rows += ["", "Sites per class: " + ", ".join(f"({c}) {n}" for c, n in counts.items()) + f"; {len(sites)} sites in all.", ""]
    return "\n".join(rows)


_SAMPLE = """from micropython import const

_A = const(1)
B = const(2)


class K:
    @staticmethod
    def s(x):
        if x:
            return 1
        return 2

    def m(self, y):
        try:
            y.go()
        except OSError:
            y.fail()
            return None
        while True:
            if y.done():
                pass
                break
        return y


def never(z):
    a = z + 1
    return a


def fall(v):
    if v > 0:
        return v
    w = -v
    return w


def chain(a, b):
    if a:
        r = 1
    elif b:
        r = 2
    else:
        r = 3
    return r


class Ann:
    x: int
    y = 1
"""
_UNRUN = """from micropython import const

_Z = const(3)


def g():
    return _Z
"""
_HITS = {"src/sample.py": [1, 4, 7, 8, 10, 11, 14, 15, 16, 21, 23, 24, 27, 32, 33, 34, 39, 40, 41, 43, 46, 49, 51]}
_EXPECT_SITES = [
    ("src/sample.py", "K.s", "`x` false", [12]),
    ("src/sample.py", "K.m", "`except OSError` catches", [17, 18, 19]),
    ("src/sample.py", "never", "`never` is called", [28, 29]),
    ("src/sample.py", "fall", "`v > 0` false", [35, 36]),
    ("src/sample.py", "chain", "`b` false", [45]),
    ("src/unrun.py", "<module>", "the module is imported", [1, 3, 6, 7]),
]
_EXPECT_ARTIFACTS = {"private_const": ["src/sample.py:3"], "decorated_def": ["src/sample.py:9"], "while_true": ["src/sample.py:20"], "pass_in_if": ["src/sample.py:22"], "typing_only": [], "elif_leaf_test": ["src/sample.py:42"], "bare_annotation": ["src/sample.py:50"]}


def self_test() -> int:
    bad: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "src/sample.py").write_text(_SAMPLE, encoding="utf-8")
        (root / "src/unrun.py").write_text(_UNRUN, encoding="utf-8")
        _hits_to_data(_HITS, root, root / ".coverage")
        try:
            sites, artifacts, _ = sweep(root / ".coverage", root)
        except NotImplementedError:
            print("self-test: FAIL - the sweep is not implemented")
            return 1
    got = [(s["file"], s["qualname"], s["condition"], s["lines"]) for s in sites]
    for want in _EXPECT_SITES:
        if want not in got:
            bad.append(f"missing site {want}")
    bad += [f"unexpected site {g}" for g in got if g not in _EXPECT_SITES]
    if artifacts != _EXPECT_ARTIFACTS:
        bad.append(f"artifacts {artifacts} != {_EXPECT_ARTIFACTS}")
    keys = [str(s["key"]) for s in sites]
    full = {k: {"class": "a", "verdict": "owed", "proof": "p", "action": "t"} for k in keys}
    if check(sites, full):
        bad.append(f"a complete verdict set fails check: {check(sites, full)}")
    probes = {
        "missing verdict": {k: v for k, v in full.items() if k != keys[0]},
        "stale verdict": {**full, "src/gone.py::f::c::x": {"class": "e", "verdict": "v", "proof": "p", "action": "a"}},
        "bad class": {**full, keys[1]: {"class": "z", "verdict": "v", "proof": "p", "action": "a"}},
        "empty proof": {**full, keys[2]: {"class": "b", "verdict": "v", "proof": "", "action": "a"}},
    }
    bad += [f"check passes a {name}" for name, verdicts in probes.items() if not check(sites, verdicts)]
    print("\n".join(bad) or f"self-test: {len(_EXPECT_SITES)} sites, {len(_EXPECT_ARTIFACTS)} artifact kinds and {len(probes)} check probes pass")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path)
    ap.add_argument("--hits", type=Path, default=ROOT / "audit/sweeps/e51_hits.json")
    ap.add_argument("--sites", type=Path)
    ap.add_argument("--kinds", action="store_true")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    with tempfile.TemporaryDirectory() as tmp:
        data = args.data
        if args.data is None:
            data = Path(tmp) / ".coverage"
            _hits_to_data(json.loads(args.hits.read_text(encoding="utf-8")), ROOT, data)
        sites, artifacts, kinds = sweep(data, ROOT)
    if args.sites:
        args.sites.write_text(json.dumps({"sites": sites, "artifacts": artifacts}, indent=1) + "\n", encoding="utf-8")
    if args.kinds:
        for name, (h, m) in sorted(kinds.items()):
            print(f"{name:16} hit {h:6} missed {m:6}")
    verdicts = json.loads(VERDICTS.read_text(encoding="utf-8")) if VERDICTS.exists() else {}
    header = TABLE.read_text(encoding="utf-8").split("\n| file:line range")[0]
    text = render(sites, artifacts, verdicts, header)
    if args.render:
        TABLE.write_text(text, encoding="utf-8")
    print(f"{len(sites)} sites, {sum(len(s['lines']) for s in sites)} lines; artifacts " + ", ".join(f"{k} {len(v)}" for k, v in artifacts.items()))  # type: ignore[arg-type]
    if args.check:
        problems = check(sites, verdicts)
        if TABLE.read_text(encoding="utf-8") != text:
            problems.append("audit/b3/e51.md is not the render of the current sweep and verdicts")
        print("\n".join(problems) or "check: every site has its verdict")
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
