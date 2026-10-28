"""Every test's record with A.U35.03/A.U35.37's red flags, each a named, separately counted candidate, never a verdict.
`python3 -I audit/sweeps/redflags.py [--json PATH] [--self-test]`; review_rows.py renders the records with
review_verdicts.json into audit/b3/review.md (agent, 2026-10-26)."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FLAGS = {
    "no_assertion": "no credited assertion: an assert, a raised AssertionError or pytest.raises/fail in the test or a test-side helper it calls (a raise of anything else, or any raise in the code under test, is never credit)",
    "weak_only": "every assertion is is-not-None / isinstance / callable / hasattr",
    "cannot_fail": "an assertion that cannot fail (a truthy constant, both sides identical, `or <truthy constant>`, len >= 0)",
    "canned_return": "re-asserts a stand-in's canned value: the assert reads back the exact path the test scripted",
    "except_pass": "a broad except (bare, Exception, BaseException, AssertionError) or suppress() that only passes",
    "log_existence_only": "a persisted-log assertion on existence only (in / any / >= 1 / truthiness), with no exact comparison of a log value",
    "loop_vacuous": "every assertion sits in a loop, or an all(), over a computed iterable no assertion checks non-empty",
    "wide_tolerance": "a tolerance or band wide enough to pass almost anything",
    "name_overclaims": "the name claims a raise that neither the body nor a helper checks for",
    "helper_swallows": "a test-side helper the test calls catches broadly and only passes or returns None",
    "same_callee": "expected and actual come from a call of the same name",
    "ns_seed_text": "normal-situation seed text: 'legitimately', 'benign', 'may appear' or 'tolerat' in the test",
    "ns_count_bound": "normal-situation scan: an error/warning count compared with <, <= or in (...)",
    "ns_allow_list": "normal-situation scan: a non-empty allow-list argument to a log helper",
    "ns_code_in_set": "normal-situation scan: an errno/wrnno compared against an in (...) set",
    "setup_credit_only": "credited only through helpers whose names say setup, not a check (their assertions may guard the rig, not the behaviour)",
    "hw_no_log": "a hardware test whose body and helpers name no log (the bench fixture and the flash logs fact are CRr2's)",
}

CANNOT_SEE = [
    "Whether a credited assertion executes: an assert in an untaken branch, in a callback that never runs, or after an early return is credited.",
    "Credit through pytest fixtures (a fixture's own assertion fails the test, but the scan credits only the test and the helpers it calls).",
    "Helpers reached through data the scan cannot resolve statically: a callable from a parameter, an object built elsewhere, a method name shared by several classes (any match credits).",
    "Canned values passed through the code under test and asserted on its output (only a read-back of the scripted path itself is flagged).",
    "A scripted value inside a bound it cannot leave, unless the bound itself is wide (wide_tolerance); an expected value copied from the code under test by any means but a same-named call.",
    "Strength against faults: a test the planted-fault record shows catching nothing is weak however it reads (faults.md, A.U35.04).",
    "tests_js: no AST. The scan masks strings, comments, regex and template literals, credits an `expect(`/`assert` in the it()/test() body or a same-named tests_js function it calls (shadowing ignored), and sees no helper imported from js/; an expect in a callback is credited whether or not it runs.",
    "Device scripts: their facts are asserted by the host tests that run them; their rows are CRr2's.",
]

TRIVIAL = {0, 1, -1, 2, True, False, None, "", 0.0, 1.0}
BROAD = {"Exception", "BaseException", "AssertionError"}
LOGISH = re.compile(r"errcount|err_count|error_log|errlog|\bhistory\b|\bentries\b|wrnno|errno|\blogged\b", re.I)
COUNTISH = re.compile(r"errcount|err_count|errcnt|error_count|warn(ing)?_count|wrn_?count|\bcount\b.*\b(E|W)\b", re.I)
CODEISH = re.compile(r"errno|wrnno", re.I)
ALLOWISH = re.compile(r"^(allow|tolerat|ignore|accept|benign)", re.I)
LOG_HELPER = re.compile(r"log|err|entr|warn", re.I)
CHECKISH = re.compile(r"assert|expect|check|verify|status|refus|reject|accept|confirm|clean|silent|trace|pass_through|spends|held|default|judge|same|equal|match|ok\b|_ok|parse", re.I)
SEED = re.compile(r"legitimately|benign|may (legitimately )?appear|tolerat", re.I)
HW_LOG = re.compile(r"errcount|error_log|errlog|log_clean|logged|new_entries|new_logged|ErrCount|ResetErrors|_log\b|logs?\b", re.I)
RAISE_NAME = re.compile(r"(^|_)(re_?)?rais(es|ing|ed)(_|$)")
NO_RAISE_NAME = re.compile(r"(never|not|no|without|nothing|doesnt|dont|no_longer|instead_of|or)_rais|rais\w*_nothing|_rais(es|ing)?_nothing")
DEPTH = 4

HELPER_PATTERNS = [
    ("tests", lambda n: n == "microtest.py" or n.startswith(("_", "test_"))),
    ("tests_scripts", lambda _n: True),
    ("tests_hardware", lambda _n: True),
    ("tests_hardware/flash", lambda _n: True),
    ("tests_hardware/bench", lambda _n: True),
    ("tests_hardware/manual", lambda _n: True),
]
SCENARIO_FILES = {"tests/_sensortask_scenarios.py": "_register", "tests/_digital_twin_construction_scenarios.py": "_register_param", "scripts/_digital_twin_scenarios.py": "scenario"}
SEARCH_DIRS = ["tests", "tests_scripts", "tests_hardware", "tests_hardware/manual", "scripts"]


def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{dotted(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        return dotted(node.func) + "()"
    if isinstance(node, ast.Subscript):
        return dotted(node.value) + "[]"
    return "?"


def fstring_regex(node: ast.JoinedStr) -> "re.Pattern[str]":
    parts = [re.escape(v.value) if isinstance(v, ast.Constant) else ".*" for v in node.values]
    return re.compile("^" + "".join(parts) + "$")


class Mod:
    # One parsed file: its module-level functions, classes, imports and function-holding literals.
    def __init__(self, path: str, src: str) -> None:
        self.path = path
        self.src = src
        self.lines = src.splitlines()
        self.tree = ast.parse(src, path)
        self.funcs: dict[str, ast.AST] = {}
        self.classes: dict[str, dict[str, ast.AST]] = {}
        self.imports: dict[str, tuple[str, str | None]] = {}
        self.tables: dict[str, list[ast.AST]] = {}
        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.funcs[node.name] = node
            elif isinstance(node, ast.ClassDef):
                self.classes[node.name] = {m.name: m for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
            elif isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.value, (ast.Dict, ast.List, ast.Tuple)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    if isinstance(t, ast.Name):
                        self.tables[t.id] = table_entries(node.value)
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.imports[a.asname or a.name.split(".")[0]] = (a.name if a.asname else a.name.split(".")[0], None)
            elif isinstance(node, ast.ImportFrom) and node.module:
                for a in node.names:
                    self.imports[a.asname or a.name] = (node.module, a.name)


def table_entries(node: ast.AST) -> "list[ast.AST]":
    # The callables a dict/list/tuple literal holds: its Name and Attribute elements, nested containers flattened.
    if isinstance(node, (ast.Name, ast.Attribute)):
        return [node]
    items = node.values if isinstance(node, ast.Dict) else node.elts if isinstance(node, (ast.List, ast.Tuple)) else []
    return [e for item in items for e in table_entries(item)]


class Universe:
    # Every scanned file and every test-side helper file, from disk or (self-test) from a mapping.
    def __init__(self, sources: dict[str, str]) -> None:
        self.sources = sources
        self.mods: dict[str, Mod | None] = {}
        self.helpers = {p for p in sources if is_helper(p)}

    def mod(self, path: str) -> "Mod | None":
        if path not in self.mods:
            try:
                self.mods[path] = Mod(path, self.sources[path]) if path in self.sources else None
            except SyntaxError:
                self.mods[path] = None
        return self.mods[path]

    def module_path(self, name: str, near: str) -> "str | None":
        here = near.rsplit("/", 1)[0]
        stem = name.replace(".", "/") + ".py"
        for cand in [stem, f"{here}/{stem}"] + [f"{d}/{stem}" for d in SEARCH_DIRS]:
            if cand in self.helpers:
                return cand
        return None


def is_helper(path: str) -> bool:
    if path in SCENARIO_FILES or not path.endswith(".py"):
        return path in SCENARIO_FILES
    d, _, n = path.rpartition("/")
    return any(d == pd and ok(n) for pd, ok in HELPER_PATTERNS)


def walk_own(node: ast.AST) -> "list[ast.AST]":
    # ast.walk(node) in its own order, never a decorator's nodes: a marker's reason or arguments are no part of what it runs.
    skip = {id(n) for d in getattr(node, "decorator_list", []) for n in ast.walk(d)}
    return [n for n in ast.walk(node) if id(n) not in skip]


class Scan:
    # One test body's credits, callees and flags.
    def __init__(self, uni: Universe, mod: Mod, node: ast.AST, cls: str | None) -> None:
        self.uni, self.mod, self.node, self.cls = uni, mod, node, cls
        self.direct: list[str] = []
        self.via: list[str] = []
        self.helpers: list[tuple[Mod, ast.AST, str | None]] = []
        self._seen: set[tuple[str, int]] = set()
        self._direct: set[tuple[str, int]] = set()  # the test's own callees: walked as direct, wherever else they are reached
        self._walk_credit(mod, node, cls, 0, top=True)

    def _resolve(self, mod: Mod, f: ast.AST, cls: str | None, local: set[str]) -> "list[tuple[Mod, ast.AST, str | None]]":
        out: list[tuple[Mod, ast.AST, str | None]] = []
        if isinstance(f, ast.Name):
            if f.id in local:
                return out
            if f.id in mod.funcs:
                return [(mod, mod.funcs[f.id], None)]
            if f.id in mod.classes and "__init__" in mod.classes[f.id]:
                return [(mod, mod.classes[f.id]["__init__"], f.id)]
            if f.id in mod.tables:
                for entry in mod.tables[f.id]:
                    if not (isinstance(entry, ast.Name) and entry.id == f.id):
                        out += self._resolve(mod, entry, cls, local)
                return out
            if f.id in mod.imports:
                modname, attr = mod.imports[f.id]
                target = self.uni.module_path(modname, mod.path)
                tmod = self.uni.mod(target) if target else None
                if tmod and attr:
                    if attr in tmod.funcs:
                        return [(tmod, tmod.funcs[attr], None)]
                    if attr in tmod.classes and "__init__" in tmod.classes[attr]:
                        return [(tmod, tmod.classes[attr]["__init__"], attr)]
            return out
        if isinstance(f, ast.Attribute):
            if isinstance(f.value, ast.Name) and f.value.id in ("self", "cls") and cls and f.attr in mod.classes.get(cls, {}):
                return [(mod, mod.classes[cls][f.attr], cls)]
            tmod = self._module_of(mod, f.value)
            if tmod is not None:
                if f.attr in tmod.tables:
                    return [r for e in tmod.tables[f.attr] for r in self._resolve(tmod, e, None, set())]
                if f.attr in tmod.funcs:
                    return [(tmod, tmod.funcs[f.attr], None)]
                return out
            for m in self._near_mods(mod):
                for cname, members in m.classes.items():
                    if f.attr in members:
                        out.append((m, members[f.attr], cname))
            return out[:6]
        if isinstance(f, ast.Subscript):
            if isinstance(f.value, ast.Name) and f.value.id in mod.tables:
                return self._resolve(mod, f.value, cls, local)
            if isinstance(f.slice, ast.JoinedStr):
                return self._by_pattern(mod, fstring_regex(f.slice))
            if isinstance(f.slice, ast.Constant) and isinstance(f.slice.value, str):
                return self._resolve(mod, ast.Name(id=f.slice.value), cls, local)
            return out
        if isinstance(f, ast.Call) and isinstance(f.func, ast.Name) and f.func.id == "getattr" and len(f.args) >= 2:
            key = f.args[1]
            if isinstance(key, ast.JoinedStr):
                return self._by_pattern(mod, fstring_regex(key))
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                return self._resolve(mod, ast.Attribute(value=f.args[0], attr=key.value), cls, local)
        return out

    def _module_of(self, mod: Mod, node: ast.AST) -> "Mod | None":
        # The helper module a local name stands for (`import x as m`, `from pkg import module`), or None.
        if not (isinstance(node, ast.Name) and node.id in mod.imports):
            return None
        modname, attr = mod.imports[node.id]
        target = self.uni.module_path(modname if attr is None else f"{modname}.{attr}", mod.path)
        return self.uni.mod(target) if target else None

    def _near_mods(self, mod: Mod) -> "list[Mod]":
        mods = [mod]
        for modname, attr in mod.imports.values():
            for name in (modname, f"{modname}.{attr}") if attr else (modname,):
                target = self.uni.module_path(name, mod.path)
                tmod = self.uni.mod(target) if target else None
                if tmod and tmod not in mods:
                    mods.append(tmod)
        return mods

    def _by_pattern(self, mod: Mod, pattern: "re.Pattern[str]") -> "list[tuple[Mod, ast.AST, str | None]]":
        return [(m, fn, None) for m in self._near_mods(mod) for name, fn in m.funcs.items() if pattern.match(name)]

    def _walk_credit(self, mod: Mod, node: ast.AST, cls: str | None, depth: int, top: bool) -> bool:
        found = False
        local = {n.name for n in walk_own(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and n is not node and hasattr(n, "name")}
        for n in walk_own(node):
            kind = credit_kind(mod, n)
            if kind:
                found = True
                if top:
                    self.direct.append(f"{kind}:{n.lineno}")
        if depth >= DEPTH:
            return found
        loops: dict[str, list[tuple[Mod, ast.AST, str | None]]] = {}
        for n in walk_own(node):
            if isinstance(n, (ast.For, ast.AsyncFor)) and isinstance(n.target, ast.Name):
                loops[n.target.id] = self._resolve(mod, n.iter, cls, set())
        calls = [n for n in walk_own(node) if isinstance(n, ast.Call)]
        if top:
            for n in calls:
                for tmod, fn, _tcls in self._resolve(mod, n.func, cls, local):
                    self._direct.add((tmod.path, fn.lineno))
        for n in calls:
            if isinstance(n.func, ast.Name) and n.func.id in loops:
                targets = list(loops[n.func.id])
            else:
                targets = self._resolve(mod, n.func, cls, local)
            for a in list(n.args) + [k.value for k in n.keywords]:
                if isinstance(a, (ast.Name, ast.Attribute)):
                    targets += self._resolve(mod, a, cls, local)
            for tmod, fn, tcls in targets:
                key = (tmod.path, fn.lineno)
                if top:
                    self._direct.add(key)
                elif key in self._direct:
                    continue
                if key in self._seen or fn is node:
                    continue
                self._seen.add(key)
                self.helpers.append((tmod, fn, tcls))
                if self._walk_credit(tmod, fn, tcls, depth + 1, top=False):
                    found = True
                    if top or depth == 0:
                        self.via.append(f"{fn.name}@{tmod.path}:{fn.lineno}")
                    else:
                        self.via.append(fn.name)
        return found


def credit_kind(mod: Mod, n: ast.AST) -> "str | None":
    if isinstance(n, ast.Assert):
        return "assert"
    if isinstance(n, ast.Raise) and n.exc is not None:
        exc = n.exc.func if isinstance(n.exc, ast.Call) else n.exc
        if isinstance(exc, ast.Name) and exc.id == "AssertionError":
            return "AssertionError"
    if isinstance(n, ast.Call):
        name = dotted(n.func)
        if name in ("pytest.raises", "pytest.fail") or (name in ("raises", "fail") and mod.imports.get(name, ("", ""))[0] == "pytest"):
            return name
    return None


def literal(node: ast.AST) -> "object":
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, (int, float)):
        return -node.operand.value
    return ...


def is_literal_iter(node: ast.AST) -> bool:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
        return len(node.elts if not isinstance(node, ast.Dict) else node.keys) > 0
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        return len(node.value) > 0
    if isinstance(node, ast.Call) and dotted(node.func) in ("range", "enumerate", "zip", "sorted", "reversed") and node.args:
        return all(is_literal_iter(a) or isinstance(literal(a), int) and literal(a) > 0 for a in node.args)
    return False


def parents(root: ast.AST) -> "dict[ast.AST, ast.AST]":
    out: dict[ast.AST, ast.AST] = {}
    for p in ast.walk(root):
        for c in ast.iter_child_nodes(p):
            out[c] = p
    return out


def broad_handler(h: ast.ExceptHandler) -> bool:
    types = [] if h.type is None else (h.type.elts if isinstance(h.type, ast.Tuple) else [h.type])
    broad = h.type is None or any(isinstance(t, ast.Name) and t.id in BROAD for t in types)
    inert = all(isinstance(s, (ast.Pass, ast.Continue)) or isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) or isinstance(s, ast.Return) and s.value is None for s in h.body)
    return broad and inert


def py_flags(uni: Universe, mod: Mod, node: ast.AST, cls: str | None, name: str, level: str) -> "tuple[list[list[object]], str]":
    sc = Scan(uni, mod, node, cls)
    flags: list[list[object]] = []
    seg = "\n".join(mod.lines[node.lineno - 1 : node.end_lineno])  # from the def line: a decorator's text is not the body's
    asserts = [n for n in ast.walk(node) if isinstance(n, ast.Assert)]
    credit = "direct" if sc.direct else "helper" if sc.via else "none"
    if credit == "none":
        raises = sorted({dotted(n.exc.func if isinstance(n.exc, ast.Call) else n.exc) for n in ast.walk(node) if isinstance(n, ast.Raise) and n.exc is not None})
        flags.append(["no_assertion", node.lineno, "raises " + ", ".join(raises) if raises else "nothing credited"])
    if credit == "helper" and not any(CHECKISH.search(v.split("@")[0]) for v in sc.via if "@" in v):
        flags.append(["setup_credit_only", node.lineno, ", ".join(v.split("@")[0] for v in sc.via if "@" in v)[:80]])
    if asserts and not sc.via and all(weak_assert(a.test) for a in asserts) and len(sc.direct) == len(asserts):
        flags.append(["weak_only", asserts[0].lineno, ast.unparse(asserts[0].test)[:80]])
    for a in asserts:
        why = cannot_fail(a.test)
        if why:
            flags.append(["cannot_fail", a.lineno, why])
    scripted = scripted_paths(node)
    for a in asserts:
        for side, lit in eq_sides(a.test):
            if dotted(side) in scripted and scripted[dotted(side)] == lit:
                flags.append(["canned_return", a.lineno, f"{dotted(side)} == {lit!r}"])
    for n in ast.walk(node):
        if isinstance(n, ast.ExceptHandler) and broad_handler(n):
            flags.append(["except_pass", n.lineno, "except " + (ast.unparse(n.type) if n.type else "") + ": pass"])
        elif isinstance(n, ast.Call) and dotted(n.func).endswith("suppress") and any(isinstance(x, ast.Name) and x.id in BROAD for x in n.args):
            flags.append(["except_pass", n.lineno, ast.unparse(n)[:80]])
    log_asserts = [a for a in asserts if LOGISH.search(ast.unparse(a.test))]
    if log_asserts and not any(exact_compare(a.test) for a in log_asserts) and all(existence_only(a.test) for a in log_asserts):
        flags.append(["log_existence_only", log_asserts[0].lineno, ast.unparse(log_asserts[0].test)[:80]])
    if asserts and not sc.via:
        par = parents(node)
        vac = [a for a in asserts if in_computed_loop(a, par, node)]
        if len(vac) == len(asserts):
            flags.append(["loop_vacuous", asserts[0].lineno, ast.unparse(asserts[0].test)[:80]])
    for n in ast.walk(node):
        why = wide(n)
        if why:
            flags.append(["wide_tolerance", n.lineno, why])
    if RAISE_NAME.search(name) and not NO_RAISE_NAME.search(name) and not checks_raise(node, sc):
        flags.append(["name_overclaims", node.lineno, "no raise check"])
    for hmod, hfn, _c in sc.helpers:
        for n in ast.walk(hfn):
            if isinstance(n, ast.ExceptHandler) and broad_handler(n):
                flags.append(["helper_swallows", node.lineno, f"{hfn.name}@{hmod.path}:{n.lineno}"])
                break
    for a in asserts:
        t = a.test
        if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq) and isinstance(t.left, ast.Call) and isinstance(t.comparators[0], ast.Call):
            lf, rf = dotted(t.left.func).rsplit(".", 1)[-1], dotted(t.comparators[0].func).rsplit(".", 1)[-1]
            if lf == rf and lf not in ("len", "list", "sorted", "set", "tuple", "dict", "str", "int", "bytes", "float", "repr", "type", "bytearray", "frozenset"):
                flags.append(["same_callee", a.lineno, ast.unparse(t)[:80]])
    flags += ns_flags(node, seg, node.lineno)
    if level.startswith(("flash", "bench")) and not HW_LOG.search(seg) and not any(HW_LOG.search(h.name) for _m, h, _c in sc.helpers):
        flags.append(["hw_no_log", node.lineno, ""])
    return dedupe(flags), credit if credit != "helper" else "helper:" + ",".join(v.split("@")[0] for v in sc.via[:4])


def dedupe(flags: "list[list[object]]") -> "list[list[object]]":
    seen, out = set(), []
    for f in flags:
        k = (f[0], f[1], f[2])
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


def weak_assert(t: ast.AST) -> bool:
    if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.IsNot) and literal(t.comparators[0]) is None:
        return True
    return isinstance(t, ast.Call) and dotted(t.func) in ("isinstance", "callable", "hasattr")


def cannot_fail(t: ast.AST) -> "str | None":
    lit = literal(t)
    if lit is not ... and lit:
        return f"assert {lit!r}"
    if isinstance(t, ast.BoolOp) and isinstance(t.op, ast.Or) and any(literal(v) is not ... and literal(v) for v in t.values):
        return "or <truthy constant>"
    if isinstance(t, ast.Compare) and len(t.ops) == 1:
        left, right, op = t.left, t.comparators[0], t.ops[0]
        if isinstance(op, (ast.Eq, ast.Is, ast.LtE, ast.GtE)) and ast.dump(left) == ast.dump(right) and not any(isinstance(x, ast.Call) for x in ast.walk(left)):
            return "both sides identical: " + ast.unparse(t)[:60]
        if isinstance(op, ast.GtE) and isinstance(left, ast.Call) and dotted(left.func) == "len" and literal(right) == 0:
            return "len(...) >= 0"
    if isinstance(t, ast.Call) and dotted(t.func) == "isinstance" and len(t.args) == 2 and dotted(t.args[1]) == "object":
        return "isinstance(x, object)"
    return None


def scripted_paths(node: ast.AST) -> "dict[str, object]":
    # Literal values the test writes onto an attribute or key path (never a subscript's index), by dotted path.
    out: dict[str, object] = {}
    for n in ast.walk(node):
        if isinstance(n, ast.Assign):
            lit = literal(n.value)
            if lit is ... or lit in TRIVIAL or isinstance(lit, str) and len(lit) < 3:
                continue
            for t in n.targets:
                if isinstance(t, ast.Attribute):
                    out[dotted(t)] = lit
                    if t.attr == "return_value":
                        out[dotted(t.value) + "()"] = lit
    return out


def eq_sides(t: ast.AST) -> "list[tuple[ast.AST, object]]":
    if not (isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq)):
        return []
    left, right = t.left, t.comparators[0]
    out = []
    if literal(right) is not ... and literal(left) is ...:
        out.append((left, literal(right)))
    if literal(left) is not ... and literal(right) is ...:
        out.append((right, literal(left)))
    return [(s, v) for s, v in out if isinstance(s, (ast.Attribute, ast.Call))]


def exact_compare(t: ast.AST) -> bool:
    return any(isinstance(n, ast.Compare) and any(isinstance(o, (ast.Eq, ast.NotEq, ast.NotIn, ast.IsNot, ast.Is)) for o in n.ops) and not all(isinstance(o, ast.IsNot) for o in n.ops) for n in ast.walk(t)) or isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not)


def existence_only(t: ast.AST) -> bool:
    if isinstance(t, (ast.Name, ast.Attribute, ast.Subscript)):
        return True
    if isinstance(t, ast.Call) and dotted(t.func) in ("any", "bool", "len"):
        return True
    if isinstance(t, ast.Compare) and len(t.ops) == 1:
        op, right = t.ops[0], literal(t.comparators[0])
        if isinstance(op, ast.In):
            return True
        if isinstance(op, (ast.Gt, ast.NotEq)) and right == 0 or isinstance(op, ast.GtE) and right == 1:
            return True
    return False


def in_computed_loop(a: ast.AST, par: "dict[ast.AST, ast.AST]", root: ast.AST) -> bool:
    if isinstance(a.test, ast.Call) and dotted(a.test.func) == "all" and a.test.args and isinstance(a.test.args[0], (ast.GeneratorExp, ast.ListComp)):
        gens = a.test.args[0].generators
        if gens and not is_literal_iter(gens[0].iter):
            return True
    p = par.get(a)
    while p is not None and p is not root:
        if isinstance(p, (ast.For, ast.AsyncFor)) and not is_literal_iter(p.iter):
            return True
        if isinstance(p, ast.While):
            return True
        p = par.get(p)
    return False


def wide(n: ast.AST) -> "str | None":
    if isinstance(n, ast.Call):
        name = dotted(n.func)
        kw = {k.arg: literal(k.value) for k in n.keywords}
        if name.endswith("approx") or name.endswith("isclose"):
            rel = kw.get("rel", kw.get("rel_tol", ...))
            if isinstance(rel, (int, float)) and rel >= 0.5:
                return f"{name} rel={rel}"
            absv, base = kw.get("abs", kw.get("abs_tol", ...)), literal(n.args[0]) if n.args else ...
            if isinstance(absv, (int, float)) and isinstance(base, (int, float)) and base and absv >= abs(base):
                return f"{name} abs={absv} >= |{base}|"
    if isinstance(n, ast.Compare) and len(n.ops) == 2 and all(isinstance(o, (ast.Lt, ast.LtE)) for o in n.ops):
        lo, hi = literal(n.left), literal(n.comparators[1])
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and not isinstance(lo, bool):
            if lo > 0 and hi / lo >= 100 or lo <= 0 < hi and hi >= 10000 or lo < 0 < hi and -lo >= 10000:
                return f"band {lo}..{hi}"
    return None


def checks_raise(node: ast.AST, sc: Scan) -> bool:
    for fn in [node] + [h for _m, h, _c in sc.helpers]:
        for n in ast.walk(fn):
            if isinstance(n, ast.ExceptHandler) or isinstance(n, ast.Call) and "rais" in dotted(n.func).lower():
                return True
    return False


def ns_flags(node: ast.AST, seg: str, start: int) -> "list[list[object]]":
    out: list[list[object]] = []
    m = SEED.search(seg)
    if m:
        out.append(["ns_seed_text", start + seg[: m.start()].count("\n"), m.group(0)])
    for n in walk_own(node):
        if isinstance(n, ast.Compare):
            text = ast.unparse(n)
            sides = [n.left] + list(n.comparators)
            in_set = any(isinstance(o, ast.In) for o in n.ops) and any(isinstance(c, (ast.Tuple, ast.List, ast.Set)) and c.elts and all(literal(e) is not ... or isinstance(e, ast.Tuple) for e in c.elts) for c in n.comparators)
            if COUNTISH.search(ast.unparse(sides[0])) and (any(isinstance(o, (ast.Lt, ast.LtE)) for o in n.ops) or in_set):
                out.append(["ns_count_bound", n.lineno, text[:80]])
            if in_set and CODEISH.search(ast.unparse(sides[0])):
                out.append(["ns_code_in_set", n.lineno, text[:80]])
        elif isinstance(n, ast.Call):
            for k in n.keywords:
                if k.arg and ALLOWISH.match(k.arg) and LOG_HELPER.search(dotted(n.func)) and not (isinstance(k.value, (ast.Tuple, ast.List, ast.Set)) and not k.value.elts) and literal(k.value) in (..., True):
                    out.append(["ns_allow_list", n.lineno, f"{dotted(n.func)}({k.arg}={ast.unparse(k.value)[:40]})"])
    return out


def level_of(path: str) -> str:
    if path.startswith("tests/test_digital_twin_"):
        return "twin (MicroPython)"
    if path.startswith("tests/"):
        return "unit (MicroPython)"
    if path.startswith("tests_scripts/"):
        return "host (pytest)"
    for d in ("flash", "bench", "manual"):
        if path.startswith(f"tests_hardware/{d}/"):
            return f"{d} (hardware)"
    return "?"


def py_tests(uni: Universe, path: str) -> "list[dict[str, object]]":
    mod = uni.mod(path)
    if mod is None:
        return [{"file": path, "line": 1, "test": "<unparsable>", "level": level_of(path), "flags": [["no_assertion", 1, "file does not parse"]], "credit": "none"}]
    found: list[tuple[str, ast.AST, str | None, str]] = []
    if path in SCENARIO_FILES:
        deco_name = SCENARIO_FILES[path]
        for node in mod.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for d in node.decorator_list:
                    if isinstance(d, ast.Call) and dotted(d.func) == deco_name and d.args and isinstance(d.args[0], ast.Constant):
                        found.append((str(d.args[0].value), node, None, "twin scenario"))
    elif path.startswith("tests_hardware/manual/"):
        for node in mod.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(isinstance(d, ast.Call) and dotted(d.func) == "register" for d in node.decorator_list):
                found.append((node.name, node, None, "manual (hardware)"))
    else:
        level = level_of(path)
        for node in mod.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                found.append((node.name, node, None, level))
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test") and not path.startswith("tests/"):
                for m in node.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name.startswith("test_"):
                        found.append((f"{node.name}.{m.name}", m, node.name, level))
        for outer in ast.walk(mod.tree):
            if not isinstance(outer, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            inner = {n.name: n for n in ast.walk(outer) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
            for n in ast.walk(outer):
                if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Subscript) and dotted(n.targets[0].value) == "globals()" and isinstance(n.value, ast.Name) and n.value.id in inner:
                    found.append((ast.unparse(n.targets[0].slice), inner[n.value.id], None, level))
    out = []
    for name, node, cls, level in found:
        flags, credit = py_flags(uni, mod, node, cls, name, level)
        out.append({"file": path, "line": node.lineno, "test": name, "level": level, "flags": flags, "credit": credit})
    return out


# ---- tests_js ----

def js_mask(text: str) -> str:
    # Strings, comments, regex and template literals blanked (newlines and delimiters kept), so braces and calls match.
    out, i, n, prev = list(text), 0, len(text), ""
    def blank(a: int, b: int) -> None:
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = " "
    while i < n:
        c, nxt = text[i], text[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
        elif c == "/" and nxt == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            blank(i, j)
            i = j
        elif c in "'\"`" or c == "/" and (prev in "(,=:[!&|?{};+-*%<>~^" or prev == ""):
            j, depth, cls = i + 1, 0, False
            while j < n:
                ch = text[j]
                if ch == "\\":
                    j += 2
                    continue
                if c == "`" and ch == "$" and j + 1 < n and text[j + 1] == "{":
                    depth += 1
                elif c == "`" and ch == "}" and depth:
                    depth -= 1
                elif c == "/" and ch == "[":
                    cls = True
                elif c == "/" and ch == "]":
                    cls = False
                elif ch == c and not depth and not cls:
                    break
                elif ch == "\n" and c in "'\"/":
                    break
                j += 1
            blank(i + 1, j)
            i = j + 1
            prev = "a"
        else:
            if not c.isspace():
                prev = c if not (c.isalnum() or c in "_$") else "a"
                if c.isalpha():
                    m = re.match(r"[A-Za-z_$][\w$]*", text[i:])
                    if m and m.group(0) in ("return", "typeof", "case", "in", "of", "yield", "await"):
                        prev = "("
                    i += len(m.group(0)) if m else 1
                    continue
            i += 1
    return "".join(out)


def match_close(masked: str, i: int, open_: str = "(", close: str = ")") -> int:
    depth = 0
    for j in range(i, len(masked)):
        if masked[j] == open_:
            depth += 1
        elif masked[j] == close:
            depth -= 1
            if depth == 0:
                return j
    return len(masked) - 1


JS_CREDIT = re.compile(r"\bexpect\s*[.(]|\bassert\s*[.(]")
JS_CALL = re.compile(r"(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(")
JS_WEAK = re.compile(r"\.(toBeDefined|toBeTruthy|toBeInstanceOf|toBeTypeOf|not\.toBeNull|not\.toBeUndefined)\s*\(")
JS_MATCHER = re.compile(r"\bexpect\s*\(")


def js_helpers(files: "dict[str, str]") -> "dict[str, list[str]]":
    out: dict[str, list[str]] = {}
    for _path, text in files.items():
        masked = js_mask(text)
        for m in re.finditer(r"(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\(|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b[^(]*\(|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)", masked):
            name = m.group(1) or m.group(2)
            if m.group(1) or m.group(0).endswith("("):
                j = masked.find("{", match_close(masked, m.end() - 1))
            else:
                j = m.end()
                while j < len(masked) and masked[j] in " \t\n":
                    j += 1
            if j >= 0 and j < len(masked) and masked[j] == "{":
                body = masked[j : match_close(masked, j, "{", "}") + 1]
            else:
                body = masked[j : masked.find("\n", j)] if j >= 0 else ""
            out.setdefault(name, []).append(body)
    return out


def js_credit(body: str, helpers: "dict[str, list[str]]", seen: "set[str]", depth: int = 0) -> "list[str]":
    if JS_CREDIT.search(body):
        return ["direct"]
    if depth >= DEPTH:
        return []
    for m in JS_CALL.finditer(body):
        name = m.group(1)
        if name in seen or name not in helpers:
            continue
        seen.add(name)
        for hb in helpers[name]:
            if js_credit(hb, helpers, seen, depth + 1):
                return [name]
    return []


def js_tests(path: str, text: str, helpers: "dict[str, list[str]]") -> "list[dict[str, object]]":
    masked, out = js_mask(text), []
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
        end = match_close(masked, j)
        if set(chain) & {"each", "skipIf", "runIf", "for"}:
            k = end + 1
            while k < len(masked) and masked[k] in " \t\n":
                k += 1
            if k < len(masked) and masked[k] == "(":
                j, end = k, match_close(masked, k)
        k = j + 1
        while text[k] in " \t\n":
            k += 1
        name = text[k + 1 : text.find(text[k], k + 1)] if text[k] in "'\"`" else text[k : masked.find(",", k)].strip()[:60]
        body, raw = masked[j + 1 : end], text[j + 1 : end]
        line = text.count("\n", 0, m.start()) + 1
        flags: list[list[object]] = []
        credit = js_credit(body, helpers, set())
        if "todo" in chain:
            continue
        if not credit:
            flags.append(["no_assertion", line, "no expect/assert"])
        else:
            expects = [x.start() for x in JS_MATCHER.finditer(body)]
            if expects and credit == ["direct"] and all(JS_WEAK.search(body[e : match_close(body, body.find("(", e)) + 40]) for e in expects):
                flags.append(["weak_only", line, "every expect is a presence matcher"])
        for x in re.finditer(r"\bexpect\s*\(\s*(true|false|null|undefined|-?\d[\d.]*|'[^']*'|\"[^\"]*\")\s*\)", raw):
            flags.append(["cannot_fail", line + raw[: x.start()].count("\n"), x.group(0)])
        for x in re.finditer(r"catch\s*(\([^)]*\))?\s*\{\s*\}|\.catch\(\s*\(\s*\)\s*=>\s*(\{\s*\}|undefined|null)\s*\)", body):
            flags.append(["except_pass", line + body[: x.start()].count("\n"), x.group(0)[:40]])
        m2 = SEED.search(raw)
        if m2:
            flags.append(["ns_seed_text", line + raw[: m2.start()].count("\n"), m2.group(0)])
        out.append({"file": path, "line": line, "test": name, "level": "web (vitest)", "flags": flags, "credit": "direct" if credit == ["direct"] else "helper" if credit else "none"})
    return out


def collect(root: Path) -> "dict[str, str]":
    pats = ["tests/*.py", "tests_scripts/*.py", "tests_hardware/*.py", "tests_hardware/flash/*.py", "tests_hardware/bench/*.py", "tests_hardware/manual/*.py", "scripts/_digital_twin_scenarios.py", "tests_js/*.js"]
    return {str(p.relative_to(root)): p.read_text(encoding="utf-8") for pat in pats for p in sorted(root.glob(pat))}


def scan(root: Path = ROOT, sources: "dict[str, str] | None" = None) -> "list[dict[str, object]]":
    sources = collect(root) if sources is None else sources
    uni = Universe({p: s for p, s in sources.items() if p.endswith(".py")})
    records: list[dict[str, object]] = []
    for path in sorted(sources):
        d, _, n = path.rpartition("/")
        if path.endswith(".py") and (path in SCENARIO_FILES or n.startswith("test_") and d in ("tests", "tests_scripts", "tests_hardware/flash", "tests_hardware/bench") or d == "tests_hardware/manual" and n.startswith("manual_")):
            records += py_tests(uni, path)
    jsfiles = {p: s for p, s in sources.items() if p.endswith(".js")}
    helpers = js_helpers(jsfiles)
    for path in sorted(p for p in jsfiles if p.endswith(".test.js")):
        records += js_tests(path, jsfiles[path], helpers)
    if sources is not None and (root / "tests_hardware/device_scripts").is_dir():
        for p in sorted((root / "tests_hardware/device_scripts").glob("*.py")):
            if not p.name.startswith("_"):
                records.append({"file": str(p.relative_to(root)), "line": 1, "test": p.stem, "level": "device script", "flags": [], "credit": "n/a"})
    for r in records:
        r["key"] = f"{r['file']}::{r['test']}"
    return records


# ---- detector tests (the known false-flag shapes stay candidates' business, never verdicts) ----

_SELF = {
    "tests/_helpers_fake.py": "def fact_ok(facts, key):\n    assert facts[f'{key}_ok'] == 1\n\ndef _check_alpha(x):\n    assert x\n\nALL_CHECKS = (_check_alpha,)\n",
    "tests/test_shapes.py": """
from _helpers_fake import fact_ok
import _helpers_fake as hf
from asy_under_test import validate

CHECKS = {"a": hf.fact_ok}

def _check_one(x):
    assert x == 3

def test_fstring_key_helper_is_credited():
    fact_ok({"rx_ok": 1}, "rx")

def test_subscript_index_is_no_literal():
    fake.value = 37
    entries = [0] * 40
    assert entries[37] == 37
    assert entries[10] in (5, 10)

def test_canned_readback_is_flagged():
    fake.reading = 4242
    assert fake.reading == 4242

def test_dispatch_through_a_table_is_credited():
    CHECKS["a"]({"x_ok": 1}, "x")

def test_globals_fstring_dispatch_is_credited():
    globals()[f"_check_{'one'}"](3)

def test_getattr_fstring_dispatch_is_credited():
    getattr(hf, f"_check_{'alpha'}")(True)

def test_an_error_thrown_in_the_test_is_no_credit():
    if validate(1) != 2:
        raise RuntimeError("wrong")

def test_an_error_thrown_by_the_code_under_test_is_no_credit():
    validate(1)

def test_an_assertion_error_thrown_is_credit():
    raise AssertionError("x")

def test_weak():
    assert validate(1) is not None

def test_swallowed():
    try:
        validate(2)
    except Exception:
        pass
    assert True

def test_loop_over_computed():
    for e in validate(3):
        assert e == 1

def test_log_presence():
    assert any(e for e in validate.entries)

def test_raises_value_error():
    validate(5)

def test_a_loop_over_an_imported_check_table_is_credited():
    for check in hf.ALL_CHECKS:
        check(1)

def test_two_calls_compared_are_no_tautology():
    assert validate(1) is validate(1)

def test_one_name_compared_with_itself_is():
    x = validate(1)
    assert x == x

def test_accepted_code():
    assert validate.errno in (5, 10)
""",
    "tests/asy_under_test.py": "def validate(x):\n    assert x\n    raise ValueError(x)\n",
    "tests_hardware/bench/test_hw_shapes.py": """
import pytest

@pytest.mark.provokes_log("the burst is refused, logged in errcount", ("WEBSERVER", "W", "HTTP_REFUSED"))
def test_a_decorator_naming_the_log_is_no_log_read():
    assert fetch() == 200

@pytest.mark.provokes_log("a retry may legitimately appear", ("WEBSERVER", "W", "HTTP_REFUSED"))
def test_seed_words_in_a_decorator_are_not_the_bodys():
    assert errcount_entry(read(), "WEBSERVER")["counter"] == 0
""",
    "tests_js/a.test.js": "function check(v) { expect(v).toBe(1); }\nit('direct', () => { expect(f()).toBe(2); });\nit('via helper', () => { check(1); });\nit('none // tricky', () => { const s = \"expect(x)\"; f(s); });\nit.each([1, 2])('each %s', (v) => { expect(v).toBeDefined(); });\n",
}

_EXPECT = {
    "test_fstring_key_helper_is_credited": set(),
    "test_subscript_index_is_no_literal": set(),
    "test_canned_readback_is_flagged": {"canned_return"},
    "test_dispatch_through_a_table_is_credited": set(),
    "test_globals_fstring_dispatch_is_credited": set(),
    "test_getattr_fstring_dispatch_is_credited": set(),
    "test_an_error_thrown_in_the_test_is_no_credit": {"no_assertion"},
    "test_an_error_thrown_by_the_code_under_test_is_no_credit": {"no_assertion"},
    "test_an_assertion_error_thrown_is_credit": set(),
    "test_weak": {"weak_only"},
    "test_swallowed": {"except_pass", "cannot_fail"},
    "test_loop_over_computed": {"loop_vacuous"},
    "test_log_presence": {"log_existence_only"},
    "test_raises_value_error": {"no_assertion", "name_overclaims"},
    "test_a_loop_over_an_imported_check_table_is_credited": set(),
    "test_two_calls_compared_are_no_tautology": set(),
    "test_one_name_compared_with_itself_is": {"cannot_fail"},
    "test_accepted_code": {"ns_code_in_set", "log_existence_only"},
    "test_a_decorator_naming_the_log_is_no_log_read": {"hw_no_log"},
    "test_seed_words_in_a_decorator_are_not_the_bodys": set(),
    "direct": set(),
    "via helper": set(),
    "none // tricky": {"no_assertion"},
    "each %s": {"weak_only"},
}


def self_test() -> int:
    got = {r["test"]: {f[0] for f in r["flags"]} for r in scan(Path("/nonexistent"), _SELF)}
    bad = [f"{name}: expected {sorted(want)}, got {sorted(got.get(name, {'<missing>'}))}" for name, want in _EXPECT.items() if got.get(name) != want]
    bad += [f"unexpected record {name}" for name in got if name not in _EXPECT]
    print("\n".join(bad) or f"self-test: {len(_EXPECT)} detector cases pass")
    return 1 if bad else 0


def main(argv: "list[str]") -> int:
    if "--self-test" in argv:
        return self_test()
    records = scan()
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps(records, indent=0), encoding="utf-8")
    flagged = [r for r in records if r["flags"]]
    print(f"{len(records)} tests, {len(flagged)} flagged")
    for flag in FLAGS:
        print(f"  {flag}: {sum(1 for r in records if any(f[0] == flag for f in r['flags']))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
