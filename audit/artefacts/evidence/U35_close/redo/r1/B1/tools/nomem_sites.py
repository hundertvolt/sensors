"""Lists each err_nomem()-reaching call with its enclosing function, to tell construction-time sites apart."""
import ast, sys, pathlib
CALLS = {"err_nomem", "_report", "_nomem"}
for p in sorted(pathlib.Path(sys.argv[1]).glob("*.py")):
    tree = ast.parse(p.read_text())
    for fn in ast.walk(tree):
        if isinstance(fn, ast.ClassDef):
            for f in fn.body:
                if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for n in ast.walk(f):
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in CALLS:
                            print(f"{p.name}:{n.lineno} {fn.name}.{f.name}")
        elif isinstance(fn, ast.Module):
            for f in fn.body:
                if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for n in ast.walk(f):
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in CALLS:
                            print(f"{p.name}:{n.lineno} {f.name}")
