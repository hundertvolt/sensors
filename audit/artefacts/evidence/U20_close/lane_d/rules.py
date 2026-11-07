import ast, sys, pathlib, collections
root = pathlib.Path(sys.argv[1]); extra = sys.argv[2:]
ids = collections.defaultdict(set)
files = sorted((root/"buildgen").glob("*.py"))
paths = [(f.name, f.read_text()) for f in files if f.name != "validate.py" or not extra]
for e in extra: paths.append(("validate.py", pathlib.Path(e).read_text()))
for name, text in paths:
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.keyword) and node.arg == "rule" and isinstance(node.value, ast.Constant):
            ids[node.value.value].add(name)
for k in sorted(ids): print(k, sorted(ids[k]))
print(len(ids), file=sys.stderr)
