# M.PROC.025: walks every call and raise in the seven never-raise modules and writes raising.md's rows below its header.
# Usage: python3 -I audit/b3/raising_walk.py <tree> audit/b3/raising.md [--check] (re-run on the integration head). Audit only.
# Hand verdicts: raising_verdicts/<module>.json, one file per module (raises by function, calls by "function::callee").
import ast, collections, hashlib, json, os, subprocess, sys
from pathlib import Path
MODULES = ["asy_base_classes.py", "asy_config_manager.py", "asy_print_log.py", "asy_system_service.py", "asy_fram_manager.py", "asy_fram_driver.py", "math_helpers.py"]
BROAD = {"Exception", "BaseException", "*"}
VERDICTS = Path(__file__).resolve().parent / "raising_verdicts"
E51_START = "## Unreachable raises (rendered by `audit/b3/raising_walk.py` from `audit/b3/raising_verdicts/`)"
E51_END = "## Uncovered lines"

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
    def visit_Lambda(self, n):  # its own scope as a nested def: the body runs later (a Timer callback), outside the enclosing try
        for d in n.args.defaults + [d for d in n.args.kw_defaults if d is not None]: self.visit(d)
        self.fn.append(self.fn[-1] + ".<lambda>")
        saved, self.handlers = self.handlers, []
        self.visit(n.body)
        self.handlers = saved; self.fn.pop()
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


def load_verdicts():  # module -> {"raises": {function: entry}, "calls": {"function::callee": entry}}; a missing file is empty
    out = {}
    for m in MODULES:
        path = VERDICTS / (m[:-3] + ".json")
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        out[m] = {"raises": data.get("raises", {}), "calls": data.get("calls", {}), "conventions": data.get("conventions", "")}
    return out


# A transitive call resolves to its callee's own rows: a receiver below names the classes it can be, a bare name a module function.
RECEIVERS = {"self.pr": ("asy_print_log.py", ("PrintLog", "PrintLogHistory", "PrintLogHistoryStore")), "self._uptime": ("asy_base_classes.py", ("TickSeconds",)),
             "self._boot_signature": ("asy_base_classes.py", ("LockedValue",)), "buf": ("asy_base_classes.py", ("RegionBuffer",))}
TERMINAL = ("handled", "unreachable", "inherently safe", "defect")


def callee_targets(callee, qualnames):  # [(module, qualname)] a callee can run, or [] when the walk cannot name it
    recv, _, name = callee.rpartition(".")
    if not recv:
        return [(m, name) for m in MODULES if name in qualnames[m]]
    mod, classes = RECEIVERS.get(recv, (None, ()))
    return [(mod, f"{c}.{name}") for c in classes if f"{c}.{name}" in qualnames.get(mod, ())]


RULES = [  # (callee test, can raise, verdict): first match wins; "open" rows need the campaign's per-site proof
    (lambda c: c == "const", "nothing at run time", "unreachable: folded at compile time (py/compile.c, MICROPY_COMP_CONST)"),
    (lambda c: c.startswith("time.ticks_"), "TypeError only for a non-int argument", "inherently safe: small-int arguments (extmod/modtime.c:150-196)"),
    (lambda c: c in ("bytearray", "bytes", "memoryview", "dict.fromkeys", "list", "dict", "set", "tuple", "str", "asyncio.Lock", "asyncio.Event", "asyncio.create_task", "asyncio.sleep", "asyncio.ThreadSafeFlag"), "MemoryError (py/gc.c gc_alloc via m_malloc_fail)", "open: setup-only or run-time allocation decides (I.4)"),
    (lambda c: c.startswith("struct."), "ValueError/TypeError on a bad format or short buffer (py/modstruct.c)", "open: format and buffer size proof"),
    (lambda c: c.startswith("json."), "OSError/MemoryError/ValueError/TypeError (extmod/modjson.c)", "open"),
    (lambda c: c == "open" or c.startswith("os."), "OSError (extmod/vfs*.c)", "open"),
    (lambda c: c in ("len", "isinstance", "type", "min", "max", "range", "enumerate", "bool", "int", "float", "abs", "round", "super", "print", "hasattr", "getattr", "zip", "sorted", "repr", "divmod", "iter", "next", "id", "callable", "issubclass"), "TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c)", "open: operand-type proof"),
]


def e51_section(unreachable):  # the e51.md block for every hand "unreachable" verdict, placed just above its sweep table
    out = [E51_START, "", "One row per raise or call group a `raising_verdicts/` file gives \"unreachable\" (A.U35.36): the class it could raise",
           "cannot occur there, by the proof given; the last column names the `except` around it, if any (a branch E.5.1 then registers).", "",
           "| site | function | call or raise | can raise (pinned source) | why it cannot | enclosing narrow except |", "|---|---|---|---|---|---|"]
    out += unreachable
    return "\n".join(out + ["", E51_END, ""])


def src_tree_id(tree):  # git's tree id of the working tree's src/ (tracked and untracked, ignored left out), so the commit
    # carrying a render records the id that render names: `git rev-parse <commit>:src` prints it (agent, 2026-10-27).
    rels = subprocess.run(["git", "-C", str(tree), "ls-files", "-z", "-co", "--exclude-standard", "--", "src"], capture_output=True, check=True).stdout.decode().split("\0")
    root = {}
    for rel in rels:
        if rel and os.path.lexists(tree / rel):
            *dirs, name = rel.split("/")
            node = root
            for d in dirs:
                node = node.setdefault(d, {})
            node[name] = tree / rel
    def obj(kind, body):
        return hashlib.sha1(kind + b" %d\0" % len(body) + body).digest()
    def tree_obj(node):  # entries sorted as git sorts them: a subtree's name compares with a trailing "/"
        items = []
        for name, v in node.items():
            if isinstance(v, dict):
                items.append((name + "/", b"40000", name, tree_obj(v)))
            elif v.is_symlink():
                items.append((name, b"120000", name, obj(b"blob", os.readlink(v).encode())))
            else:
                items.append((name, b"100755" if v.stat().st_mode & 0o100 else b"100644", name, obj(b"blob", v.read_bytes())))
        return obj(b"tree", b"".join(mode + b" " + name.encode() + b"\0" + sha for _, mode, name, sha in sorted(items)))
    return tree_obj(root.get("src", {})).hex()


def splice_e51(text, section):  # replaces (or inserts) the block inside e51.md's header, which e51_sweep.py's render keeps
    header, sep, rest = text.partition("\n| file:line range")
    if E51_START in header:
        before, _, after = header.partition(E51_START)
        header = before + after.partition(E51_END + "\n")[2]
    return header.rstrip("\n") + "\n\n" + section.rstrip("\n") + "\n" + sep + rest


def main():
    tree, out = Path(sys.argv[1]), Path(sys.argv[2])
    check = "--check" in sys.argv[3:]
    verdicts = load_verdicts()
    defined, qualnames = set(), {}
    for m in MODULES:
        tree_ast = ast.parse((tree / "src" / m).read_text(encoding="utf-8"))
        Walk(m).visit(tree_ast)
        defined |= {n.name for n in ast.walk(tree_ast) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        qualnames[m] = {f"{c.name}.{f.name}" for c in tree_ast.body if isinstance(c, ast.ClassDef) for f in c.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}
        qualnames[m] |= {f.name for f in tree_ast.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}
    groups = collections.OrderedDict()
    for r in rows:
        if r["kind"] != "call" or r["broad"]:
            continue
        callee = r["text"].split("(")[0]
        own = f"{r['fn']}::{callee}" in verdicts[r["mod"]]["calls"]  # a hand verdict splits its function's calls out
        groups.setdefault((r["mod"], callee, r["fn"] if own else None), []).append(r)
    used = {(mod, f"{fn}::{callee}") for mod, callee, fn in groups if fn is not None}
    used |= {(r["mod"], r["fn"]) for r in rows if r["kind"] == "raise"}
    stale = [f"{m} {k}" for m in MODULES for part in ("raises", "calls") for k in verdicts[m][part] if (m, k) not in used]
    def base_verdict(key):  # (can raise, verdict word, proof) from the hand file or RULES, before a transitive group resolves
        mod, callee, fn = key
        if fn is not None:
            entry = verdicts[mod]["calls"][f"{fn}::{callee}"]
            return entry["can_raise"], entry["verdict"], entry["proof"]
        rule = next(((what, verdict) for test, what, verdict in RULES if test(callee)), None)
        if rule is None and callee.split(".")[-1] in defined:
            rule = ("what the callee raises", "transitive: the callee's own rows here")
        what, verdict = rule or ("not classified", "open")
        return what, verdict.split(":")[0], verdict.partition(": ")[2] or "-"

    memo, cycles = {}, []
    def target_words(tmod, q, seen):  # every verdict word of q's own rows: its raises and its call groups, nested defs excluded
        words = [verdicts[tmod]["raises"].get(q, {"verdict": "open"})["verdict"] for r in rows if (r["mod"], r["kind"], r["fn"]) == (tmod, "raise", q)]
        return words + [resolved(k, seen)[1] for k, rs in groups.items() if k[0] == tmod and any(r["fn"] == q for r in rs)]
    def resolved(key, seen=frozenset()):
        if key in memo:
            return memo[key]
        what, word, proof = base_verdict(key)
        if word == "transitive":
            if key in seen:
                cycles.append(key)
                return what, word, "a call cycle"
            targets = callee_targets(key[1], qualnames)
            per = {t: collections.Counter(target_words(*t, seen | {key})) for t in targets}
            left = [f"{m[:-3]} {q}" for (m, q), ws in per.items() if set(ws) - set(TERMINAL)]
            if targets and not left:
                total = sum(per.values(), collections.Counter())
                named = ", ".join(f"{m[:-3]} {q}" for m, q in targets)
                what, word = "what the callee raises (its rows)", "handled"
                proof = f"resolved against the callee's rows: {named}, every one terminal ({', '.join(f'{k} {v}' for k, v in sorted(total.items())) or 'none'}); what leaves it is caught where this file's conventions place this function's caller"
            else:
                proof = "the walk cannot name the callee" if not targets else "left open in the callee: " + ", ".join(left)
        memo[key] = (what, word, proof)
        return memo[key]

    lines, counts, unreachable = [], collections.Counter(), []
    for (mod, callee, fn), rs in groups.items():
        sites = ", ".join(f":{r['line']}" for r in rs[:12]) + (f" (+{len(rs) - 12})" if len(rs) > 12 else "")
        narrow = sorted({n for r in rs for names, _ in r["caught"] for n in names})
        what, word, proof = resolved((mod, callee, fn))
        if fn is not None and word == "unreachable":
            guards = sorted({f"{'/'.join(names)} (:{', :'.join(map(str, hl))})" for r in rs for names, hl in r["caught"]})
            unreachable.append(f"| `src/{mod}{sites.split(',')[0]}` | {fn} | `{callee}` at {sites} | {what} | {proof} | {'; '.join(guards) or 'none'} |")
        counts[word] += len(rs)
        lines.append(f"| {mod}{sites.split(',')[0]} | {rs[0]['fn']}{' +' + str(len({r['fn'] for r in rs}) - 1) if len({r['fn'] for r in rs}) > 1 else ''} | `{callee}` at {sites}{'; narrow except ' + '/'.join(narrow) if narrow else ''} | {what} | {word} | {proof} |")
    by_line = {(r["mod"], r["line"]): r for r in rows}
    raises = [r for r in rows if r["kind"] == "raise"]
    text = out.read_text(encoding="utf-8").split("\n## Walk summary")[0].split("\n| module:line")[0].rstrip() + "\n"  # the header alone: re-runs stay idempotent
    summary = collections.Counter((r["mod"], r["kind"], "broad" if r["broad"] else ("narrow" if r["caught"] else "none")) for r in rows)
    head = src_tree_id(tree)[:12]
    body = [text, "## Walk summary", "", f"Walked over the `src/` tree `{head}` (git's tree id, from the working tree) by `audit/b3/raising_walk.py` (agent, 2026-10-22). Re-run it on the integration head: lanes P",
            "and Y edit four of these modules in U35. A row left \"open\" needs its per-site proof from the pinned source in the B3 campaign.", "", "Sites per module (call or raise) by the `try` enclosing them: inside one catching `Exception` (broad), inside one",
            "catching named classes only (narrow), or none. Broad sites are handled by construction; the rows below are the rest.", "",
            "| module | calls broad | calls narrow | calls none | raises |", "|---|---|---|---|---|"]
    for m in MODULES:
        body.append(f"| {m} | {summary[(m, 'call', 'broad')]} | {summary[(m, 'call', 'narrow')]} | {summary[(m, 'call', 'none')]} | {sum(v for k, v in summary.items() if k[0] == m and k[1] == 'raise')} |")
    body += ["", "Rows outside a broad `try`, by verdict: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + ".", "",
             "## Shared classes (each verdict file's `conventions`)", "", "What every row of a module shares, stated once in its verdict file and not repeated per row.", ""]
    body += [f"- `{m}`: {verdicts[m]['conventions']}" for m in MODULES if verdicts[m]["conventions"]]
    body += ["", "## Raises", "", "| module:line | function | call or raise | can raise (pinned source) | verdict | proof or action |", "|---|---|---|---|---|---|"]
    for r in raises:
        entry = verdicts[r["mod"]]["raises"].get(r["fn"], {"verdict": "open", "proof": "-"})
        shown = "raise" if r["text"].startswith("raise ") else "raise " + r["text"]
        body.append(f"| {r['mod']}:{r['line']} | {r['fn']} | `{shown}` | the raise itself | {entry['verdict']} | {entry['proof']} |")
        if entry["verdict"] == "unreachable":
            unreachable.append(f"| `src/{r['mod']}:{r['line']}` | {r['fn']} | `{shown}` | the raise itself | {entry['proof']} | - |")
    body += ["", "## Calls outside a broad try (grouped by module and callee)", "", "| module:line | function | call or raise | can raise (pinned source) | verdict | proof or action |", "|---|---|---|---|---|---|"]
    body += lines
    rendered = "\n".join(body) + "\n"
    e51 = out.with_name("e51.md")
    e51_old = e51.read_text(encoding="utf-8") if e51.exists() else None
    e51_new = splice_e51(e51_old, e51_section(unreachable)) if e51_old is not None and (unreachable or E51_START in e51_old) else e51_old
    if unreachable and e51_old is None:
        stale.append(f"no {e51} to hold the {len(unreachable)} unreachable rows")
    stale += [f"{m} {c} in {fn or 'module'}: a call cycle the resolution cannot settle" for m, c, fn in cycles]
    if stale:
        print("stale or unplaceable verdicts (nothing written):\n  " + "\n  ".join(stale))
        sys.exit(1)
    if check:
        problems = [f"{p} is not the current render" for p, old, new in ((out, out.read_text(encoding="utf-8"), rendered), (e51, e51_old, e51_new)) if old != new]
        print("\n".join(problems) or "check: raising.md and e51.md's block are the current render")
        sys.exit(1 if problems else 0)
    out.write_text(rendered, encoding="utf-8")
    if e51_new != e51_old:
        e51.write_text(e51_new, encoding="utf-8")
    print(len(rows), "sites;", len(lines), "groups;", dict(counts))
    for key in (("asy_base_classes.py", 519), ("asy_base_classes.py", 700), ("asy_fram_manager.py", 828)):
        r = by_line.get(key)
        print(key, r and (r["broad"], r["caught"]))


main()
