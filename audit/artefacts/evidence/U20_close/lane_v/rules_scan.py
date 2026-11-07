import ast, sys, collections
path = sys.argv[1]
tree = ast.parse(open(path).read())
rules = collections.Counter(); bad = []
for n in ast.walk(tree):
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "BuildError":
        kw = {k.arg: k.value for k in n.keywords}
        r = kw.get("rule"); f = kw.get("fix")
        if not (isinstance(r, ast.Constant) and isinstance(r.value, str)) or f is None:
            bad.append(n.lineno)
        else:
            rules[r.value] += 1
print("sites:", sum(rules.values()), "bad:", bad)
for r, c in sorted(rules.items()):
    print(f"{r}\t{c}")
