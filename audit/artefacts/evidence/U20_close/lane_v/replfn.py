"""Replace whole top-level test functions (decorators included) by name with the bodies in a spec file."""
import ast, sys, re
target, spec = sys.argv[1], sys.argv[2]
src = open(target).read()
lines = src.splitlines(keepends=True)
tree = ast.parse(src)
blocks = re.split(r"^# ==== (\w+)\n", open(spec).read(), flags=re.M)[1:]
new = dict(zip(blocks[0::2], blocks[1::2]))
spans = {}
for fn in tree.body:
    if isinstance(fn, ast.FunctionDef) and fn.name in new:
        start = fn.decorator_list[0].lineno if fn.decorator_list else fn.lineno
        spans[fn.name] = (start, fn.end_lineno)
missing = set(new) - set(spans)
assert not missing, missing
for name, (a, b) in sorted(spans.items(), key=lambda kv: -kv[1][0]):
    lines[a - 1:b] = [new[name].rstrip("\n") + "\n"]
open(target, "w").write("".join(lines))
print("replaced", len(spans))
