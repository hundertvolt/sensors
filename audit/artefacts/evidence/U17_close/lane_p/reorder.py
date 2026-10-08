import ast, sys
def d15_key(name):
    if name.startswith("__") and name.endswith("__"):
        return (0, 0 if name == "__init__" else 1, 0, name)
    base = name.lstrip("_")
    role = 1 if base.startswith(("get_", "is_")) else 2 if base.startswith("set_") else 3
    return (1, 0 if name.startswith("_") else 1, role, base)
path = sys.argv[1]
src = open(path).read()
lines = src.splitlines(keepends=True)
tree = ast.parse(src)
def start(n, floor):
    s = (n.decorator_list[0].lineno if n.decorator_list else n.lineno) - 1
    while s - 1 >= floor and lines[s - 1].strip().startswith("#"):
        s -= 1
    return s
def chunk(n, floor):
    return "".join(lines[start(n, floor): n.end_lineno]).rstrip("\n") + "\n"
defs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
first = tree.body.index(defs[0])
assert tree.body[first:] == defs
head = "".join(lines[: start(defs[0], 0)]).rstrip("\n") + "\n"
def cls_text(c):
    meths = [d for d in c.body if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert c.body[-len(meths):] == meths
    pre_end = start(meths[0], c.lineno)
    pre = "".join(lines[start(c, 0): pre_end])
    parts = []
    prev_end = pre_end
    for d in meths:
        parts.append((d.name, chunk(d, prev_end)))
        prev_end = d.end_lineno
    parts.sort(key=lambda p: d15_key(p[0]))
    return pre + "\n".join(t for _, t in parts)
classes = [cls_text(c) for c in defs if isinstance(c, ast.ClassDef)]
funcs = sorted(((d.name, chunk(d, 0)) for d in defs if not isinstance(d, ast.ClassDef)), key=lambda p: d15_key(p[0]))
open(path, "w").write(head + "\n\n" + "\n\n".join(classes + [t for _, t in funcs]))
