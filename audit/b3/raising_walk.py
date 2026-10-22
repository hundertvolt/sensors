# M.PROC.025: walks every call and raise in the seven never-raise modules and writes raising.md's rows below its header.
# Usage: python3 -I audit/b3/raising_walk.py <tree> audit/b3/raising.md (re-run on the integration head). Audit only.
import ast, collections, subprocess, sys
from pathlib import Path
MODULES = ["asy_base_classes.py", "asy_config_manager.py", "asy_print_log.py", "asy_system_service.py", "asy_fram_manager.py", "asy_fram_driver.py", "math_helpers.py"]
BROAD = {"Exception", "BaseException", "*"}

def handler_names(h):
    if h.type is None: return {"*"}
    t = h.type
    elts = t.elts if isinstance(t, ast.Tuple) else [t]
    return {ast.unparse(e).split(".")[-1] for e in elts}

rows = []
class Walk(ast.NodeVisitor):
    def __init__(self, mod): self.mod, self.fn, self.handlers = mod, ["<module>"], []
    def visit_FunctionDef(self, n):
        self.fn.append(n.name if self.fn == ["<module>"] else self.fn[-1] + "." + n.name)
        saved, self.handlers = self.handlers, []  # a nested def runs later, outside the enclosing try
        for s in n.body: self.visit(s)
        self.handlers = saved; self.fn.pop()
    visit_AsyncFunctionDef = visit_FunctionDef
    def visit_ClassDef(self, n):
        self.fn.append(n.name)
        for s in n.body: self.visit(s)
        self.fn.pop()
    def visit_Try(self, n):
        names = set().union(*(handler_names(h) for h in n.handlers)) if n.handlers else set()
        lines = [h.lineno for h in n.handlers]
        self.handlers.append((names, lines))
        for s in n.body: self.visit(s)
        self.handlers.pop()
        for part in (n.handlers, n.orelse, n.finalbody):
            for s in part: self.visit(s)
    visit_TryStar = visit_Try
    def record(self, n, kind, text):
        caught = [(sorted(names), lines) for names, lines in self.handlers if names]
        broad = any(names & BROAD for names, _ in self.handlers)
        rows.append({"mod": self.mod, "line": n.lineno, "fn": self.fn[-1], "kind": kind, "text": text[:90], "caught": caught, "broad": broad})
    def visit_Call(self, n):
        self.record(n, "call", ast.unparse(n.func))
        self.generic_visit(n)
    def visit_Raise(self, n):
        self.record(n, "raise", ast.unparse(n.exc) if n.exc else "raise (re-raise)")
        self.generic_visit(n)


RAISES = {  # function -> (verdict, proof), read at f3fff0e (agent, 2026-10-22)
    "_checked_write_results": ("handled", "both callers sit in a try catching Exception: asy_base_classes.py:507 (except :508) and :689 (except :690); the raise is that try's logged failure, as its comment says"),
    "FRAM_SPI.__aenter__": ("inherently safe", "cleanup then re-raise: a BaseException (a cancel) while waiting for the bus lock releases the session lock first; a cancellation must propagate"),
    "FRAM_SPI._check_device_id": ("exempt (setup)", "one-time identification error, outside M.PROC.025's scope; reached from FRAM_SPI.setup(), whose one caller asy_fram_manager.py:795 sits in a try catching Exception (except :796)"),
    "FRAM_SPI.setup": ("exempt (setup)", "one-time setup error, outside M.PROC.025's scope; the one caller asy_fram_manager.py:795 sits in a try catching Exception (except :796)"),
}
RULES = [  # (callee test, can raise, verdict): first match wins; "open" rows need the campaign's per-site proof
    (lambda c: c == "const", "nothing at run time", "unreachable: folded at compile time (py/compile.c, MICROPY_COMP_CONST)"),
    (lambda c: c.startswith("time.ticks_"), "TypeError only for a non-int argument", "inherently safe: small-int arguments (extmod/modtime.c:150-196)"),
    (lambda c: c in ("bytearray", "bytes", "memoryview", "dict.fromkeys", "list", "dict", "set", "tuple", "str", "asyncio.Lock", "asyncio.Event", "asyncio.create_task", "asyncio.sleep", "asyncio.ThreadSafeFlag"), "MemoryError (py/gc.c gc_alloc via m_malloc_fail)", "open: setup-only or run-time allocation decides (I.4)"),
    (lambda c: c.startswith("struct."), "ValueError/TypeError on a bad format or short buffer (py/modstruct.c)", "open: format and buffer size proof"),
    (lambda c: c.startswith("json."), "OSError/MemoryError/ValueError/TypeError (extmod/modjson.c)", "open"),
    (lambda c: c == "open" or c.startswith("os."), "OSError (extmod/vfs*.c)", "open"),
    (lambda c: c in ("len", "isinstance", "type", "min", "max", "range", "enumerate", "bool", "int", "float", "abs", "round", "super", "print", "hasattr", "getattr", "zip", "sorted", "repr", "divmod", "iter", "next", "id", "callable", "issubclass"), "TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c)", "open: operand-type proof"),
]

def main():
    tree, out = Path(sys.argv[1]), Path(sys.argv[2])
    defined = set()
    for m in MODULES:
        tree_ast = ast.parse((tree / "src" / m).read_text(encoding="utf-8"))
        Walk(m).visit(tree_ast)
        defined |= {n.name for n in ast.walk(tree_ast) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    groups = collections.OrderedDict()
    for r in rows:
        if r["kind"] != "call" or r["broad"]:
            continue
        callee = r["text"].split("(")[0]
        groups.setdefault((r["mod"], callee), []).append(r)
    lines, counts = [], collections.Counter()
    for (mod, callee), rs in groups.items():
        last = callee.split(".")[-1]
        rule = next(((what, verdict) for test, what, verdict in RULES if test(callee)), None)
        if rule is None and last in defined:
            rule = ("what the callee raises", "transitive: the callee's own rows here")
        what, verdict = rule or ("not classified", "open")
        narrow = sorted({n for r in rs for names, _ in r["caught"] for n in names})
        sites = ", ".join(f":{r['line']}" for r in rs[:12]) + (f" (+{len(rs) - 12})" if len(rs) > 12 else "")
        counts[verdict.split(":")[0]] += len(rs)
        lines.append(f"| {mod}{sites.split(',')[0]} | {rs[0]['fn']}{' +' + str(len({r['fn'] for r in rs}) - 1) if len({r['fn'] for r in rs}) > 1 else ''} | `{callee}` at {sites}{'; narrow except ' + '/'.join(narrow) if narrow else ''} | {what} | {verdict.split(':')[0]} | {verdict.partition(': ')[2] or '-'} |")
    by_line = {(r["mod"], r["line"]): r for r in rows}
    raises = [r for r in rows if r["kind"] == "raise"]
    text = out.read_text(encoding="utf-8").split("\n## Walk summary")[0].split("\n| module:line")[0].rstrip() + "\n"  # the header alone: re-runs stay idempotent
    summary = collections.Counter((r["mod"], r["kind"], "broad" if r["broad"] else ("narrow" if r["caught"] else "none")) for r in rows)
    head = subprocess.run(["git", "-C", str(tree), "log", "-1", "--format=%h", "--", "src"], capture_output=True, text=True, check=False).stdout.strip() or "unknown"
    body = [text, "## Walk summary", "", f"Walked over `src/` as of `{head}` by `audit/b3/raising_walk.py` (agent, 2026-10-22). Re-run it on the integration head: lanes P",
            "and Y edit four of these modules in U35. A row left \"open\" needs its per-site proof from the pinned source in the B3 campaign.", "", "Sites per module (call or raise) by the `try` enclosing them: inside one catching `Exception` (broad), inside one",
            "catching named classes only (narrow), or none. Broad sites are handled by construction; the rows below are the rest.", "",
            "| module | calls broad | calls narrow | calls none | raises |", "|---|---|---|---|---|"]
    for m in MODULES:
        body.append(f"| {m} | {summary[(m, 'call', 'broad')]} | {summary[(m, 'call', 'narrow')]} | {summary[(m, 'call', 'none')]} | {sum(v for k, v in summary.items() if k[0] == m and k[1] == 'raise')} |")
    body += ["", "Rows outside a broad `try`, by verdict: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + ".", "",
             "## Raises", "", "| module:line | function | call or raise | can raise (pinned source) | verdict | proof or action |", "|---|---|---|---|---|---|"]
    for r in raises:
        verdict, proof = RAISES.get(r["fn"], ("open", "-"))
        shown = "raise" if r["text"].startswith("raise ") else "raise " + r["text"]
        body.append(f"| {r['mod']}:{r['line']} | {r['fn']} | `{shown}` | the raise itself | {verdict} | {proof} |")
    body += ["", "## Calls outside a broad try (grouped by module and callee)", "", "| module:line | function | call or raise | can raise (pinned source) | verdict | proof or action |", "|---|---|---|---|---|---|"]
    body += lines
    out.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(len(rows), "sites;", len(lines), "groups;", dict(counts))
    for key in (("asy_base_classes.py", 507), ("asy_base_classes.py", 689), ("asy_fram_manager.py", 795)):
        r = by_line.get(key)
        print(key, r and (r["broad"], r["caught"]))


main()
