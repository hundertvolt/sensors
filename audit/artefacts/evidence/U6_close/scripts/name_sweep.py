import ast, builtins, sys
from pathlib import Path
for p in sorted(Path(sys.argv[1]).glob("sensortask_*.py")):
    tree = ast.parse(p.read_text())
    top = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): top.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names: top.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                for x in ast.walk(t):
                    if isinstance(x, ast.Name): top.add(x.id)
        elif isinstance(n, ast.If):  # TYPE_CHECKING blocks
            for m in ast.walk(n):
                if isinstance(m, (ast.Import, ast.ImportFrom)):
                    for a in m.names: top.add((a.asname or a.name).split(".")[0])
    bad = set()
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)): continue
        local = {a.arg for a in fn.args.args + fn.args.kwonlyargs}
        for x in ast.walk(fn):
            if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store): local.add(x.id)
            if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x is not fn: local.add(x.name)
            if isinstance(x, ast.Global): local.update(x.names)
            if isinstance(x, ast.ExceptHandler) and x.name: local.add(x.name)
            if isinstance(x, ast.comprehension):
                for y in ast.walk(x.target):
                    if isinstance(y, ast.Name): local.add(y.id)
        for x in ast.walk(fn):
            if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load) and x.id not in local and x.id not in top and not hasattr(builtins, x.id):
                bad.add(x.id)
    print(p.name, sorted(bad) or "clean")
