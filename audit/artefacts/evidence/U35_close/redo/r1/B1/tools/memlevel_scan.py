"""Lists log calls inside handlers that can catch a MemoryError and pass the exception, by the call's method."""
import ast, sys, pathlib
BROAD = {"Exception", "BaseException", "MemoryError"}
LEVEL = {"err": 1, "err_s": 1, "err_nomem": 1, "_err": 1, "wrn": 2, "wrn_s": 2, "one": 3, "evt": 4, "all": 5}
def names(t):
    if t is None: return {"BaseException"}
    if isinstance(t, ast.Name): return {t.id}
    if isinstance(t, ast.Attribute): return {t.attr}
    if isinstance(t, ast.Tuple): return set().union(*(names(e) for e in t.elts))
    return set()
for p in sorted(pathlib.Path(sys.argv[1]).glob("*.py")):
    tree = ast.parse(p.read_text())
    for h in ast.walk(tree):
        if not isinstance(h, ast.ExceptHandler) or not (names(h.type) & BROAD) or not h.name: continue
        for n in ast.walk(h):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in LEVEL and LEVEL[n.func.attr] > 1:
                if any(isinstance(a, ast.Name) and a.id == h.name for a in n.args):
                    print(f"{p.name}:{n.lineno} {n.func.attr} catches {sorted(names(h.type))}")
