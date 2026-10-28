import ast, sys
tree = ast.parse(open(sys.argv[1]).read())
for fn in tree.body:
    if isinstance(fn, ast.FunctionDef) and fn.name.startswith("test_"):
        has = any(isinstance(n, ast.Assert) for n in ast.walk(fn)) or any(
            isinstance(n, ast.Attribute) and n.attr == "raises" for n in ast.walk(fn))
        if not has:
            print(fn.lineno, fn.name)
