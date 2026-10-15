# Reorders a class's methods into a given order (scratch tool). usage: reorder.py file class m1,m2,...
import ast, sys
path, cls, order = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
src = open(path).read()
lines = src.split("\n")
tree = ast.parse(src)
node = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == cls)
methods = [m for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
assert [m for m in node.body if not isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))] == [], "non-method member"
assert sorted(order) == sorted(m.name for m in methods), (order, [m.name for m in methods])
# block of each method: from its first line (decorators) to the line before the next method's start (or class end)
starts = [ (m.decorator_list[0].lineno if m.decorator_list else m.lineno) for m in methods ]
# include comment lines directly above a method (same indent) in its block
first = starts[0]
end = node.end_lineno
blocks = {}
for i, m in enumerate(methods):
    s = starts[i]
    e = (starts[i + 1] - 1) if i + 1 < len(methods) else end
    blk = lines[s - 1:e]
    while blk and blk[-1].strip() == "":
        blk.pop()
    blocks[m.name] = blk
new = []
for j, name in enumerate(order):
    if j:
        new.append("")
    new.extend(blocks[name])
lines[first - 1:end] = new
open(path, "w").write("\n".join(lines))
