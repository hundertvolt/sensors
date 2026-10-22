import ast, sys
def key(name):
    if name.startswith("__") and name.endswith("__"):
        return (0, 0 if name == "__init__" else 1, 0, name)
    base = name.lstrip("_")
    role = 1 if base.startswith(("get_", "is_")) else 2 if base.startswith("set_") else 3
    return (1, 0 if name.startswith("_") else 1, role, base)
for p in sys.argv[1:]:
    t = ast.parse(open(p).read())
    roots=[]
    for node in t.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            roots.extend([*node.decorator_list,*node.args.defaults,*(d for d in node.args.kw_defaults if d is not None)])
        elif isinstance(node, ast.ClassDef):
            roots.extend([*node.decorator_list,*node.bases,*(s for s in node.body if not isinstance(s,(ast.FunctionDef,ast.AsyncFunctionDef)))])
        else:
            roots.append(node)
    it={n.id for r in roots for n in ast.walk(r) if isinstance(n,ast.Name)}
    names=[n.name for n in t.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name not in it]
    exp=sorted(names,key=key)
    print(p, "OK" if names==exp else f"OUT: first {next(a for a,b in zip(names,exp) if a!=b)} vs {next(b for a,b in zip(names,exp) if a!=b)}")
