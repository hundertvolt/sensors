import ast, sys
src = open(sys.argv[1]).read()
lines = src.splitlines()
tree = ast.parse(src)
names = set(sys.argv[2:])
for fn in tree.body:
    if isinstance(fn, ast.FunctionDef) and fn.name in names:
        start = fn.decorator_list[0].lineno if fn.decorator_list else fn.lineno
        print("\n".join(lines[start-1:fn.end_lineno])); print("-----")
