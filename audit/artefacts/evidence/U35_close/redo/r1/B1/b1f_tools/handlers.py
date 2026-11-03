"""B1 falsifier: list every broad handler and every MemoryError-catching handler in src/ and build/generated_src/."""
import ast
import sys
from pathlib import Path

W = Path(sys.argv[1])
BROAD = {"Exception", "BaseException", "RuntimeError"}
LOGM = {"err", "err_nomem", "err_s", "wrn", "wrn_s", "one", "evt", "all", "_err"}


def names(h):
    if h.type is None:
        return ["<bare>"]
    ks = h.type.elts if isinstance(h.type, ast.Tuple) else [h.type]
    return [ast.unparse(k) for k in ks]


def owner_map(tree):
    out = {}

    def visit(node, cur):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[ch] = cur
                visit(ch, ch.name)
            else:
                out[ch] = cur
                visit(ch, cur)

    visit(tree, "<module>")
    return out


files = sorted((W / "src").glob("*.py")) + sorted((W / "build" / "generated_src").glob("*.py"))
print("FILES", len(files))
for p in files:
    rel = p.relative_to(W)
    tree = ast.parse(p.read_text())
    own = owner_map(tree)
    for n in ast.walk(tree):
        if not isinstance(n, ast.ExceptHandler):
            continue
        ks = names(n)
        broad = any(k in BROAD for k in ks) or ks == ["<bare>"]
        mem = any(k == "MemoryError" for k in ks)
        if not (broad or mem):
            continue
        # every logger call in the whole handler body (nested too), and whether it passes the bound name
        calls = []
        for s_i, s in enumerate(n.body):
            for c in ast.walk(s):
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr in LOGM:
                    passes = n.name is not None and any(isinstance(a, ast.Name) and a.id == n.name for a in c.args)
                    calls.append((s_i, isinstance(s, ast.Expr), ast.unparse(c.func), passes))
        first = ast.unparse(n.body[0]).splitlines()[0][:90]
        tag = ("BROAD" if broad else "") + ("+MEM" if mem else "")
        print(f"{tag}\t{rel}:{n.lineno}\t{own.get(n)}\t{'/'.join(ks)} as {n.name}\tfirst={first!r}")
        for c in calls:
            print(f"\t\tstmt#{c[0]} top_expr={c[1]} call={c[2]} passes_e={c[3]}")
        # statements before the first passing top-level log that can leave the handler
        firstlog = next((c[0] for c in calls if c[1] and c[3]), None)
        if firstlog:
            for s in n.body[:firstlog]:
                for x in ast.walk(s):
                    if isinstance(x, (ast.Return, ast.Continue, ast.Break, ast.Raise, ast.Await)):
                        print(f"\t\t!! before the log: {type(x).__name__}: {ast.unparse(s).splitlines()[0][:80]}")
                        break
print("PRINTS in generated:")
for p in sorted((W / "build" / "generated_src").glob("*.py")):
    for i, line in enumerate(p.read_text().splitlines(), 1):
        if "print(" in line or "print_exception" in line:
            print(f"\t{p.name}:{i}: {line.strip()[:120]}")
