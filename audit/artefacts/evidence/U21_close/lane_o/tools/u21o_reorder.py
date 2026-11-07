# D.15 pure reorder of a test file's module-level helpers (test functions exempt): every module
# constant moves up (original order, its own comments with it), then the helpers in D.15 order.
import ast, re, sys
from pathlib import Path

def key(name):
    base = name.lstrip("_")
    role = 1 if base.startswith(("get_", "is_")) else 2 if base.startswith("set_") else 3
    return (0 if name.startswith("_") else 1, role, base)

path = Path(sys.argv[1])
src = path.read_text()
lines = src.split("\n")
tree = ast.parse(src)
body = tree.body
first_def = next(i for i, n in enumerate(body) if isinstance(n, (ast.FunctionDef, ast.ClassDef)))

def segment(n):
    start = (n.decorator_list[0].lineno if getattr(n, "decorator_list", None) else n.lineno)
    while start > 1 and lines[start - 2].startswith("#") and not lines[start - 2].startswith("# ---"):
        start -= 1
    return start, n.end_lineno

moving_consts = [n for n in body[first_def:] if isinstance(n, (ast.Assign, ast.AnnAssign))]
helpers = [n for n in body if isinstance(n, ast.FunctionDef) and not n.name.startswith("test_")]
moved = moving_consts + helpers
taken = set()
for n in moved:
    a, b = segment(n)
    taken.update(range(a, b + 1))
insert_at = segment(body[first_def])[0]  # the moved block goes right before the first definition
const_text = "\n\n".join("\n".join(lines[a - 1:b]) for a, b in map(segment, moving_consts))
helper_text = "\n\n\n".join("\n".join(lines[a - 1:b]) for a, b in map(segment, sorted(helpers, key=lambda n: key(n.name))))
out = []
for no, line in enumerate(lines, 1):
    if no == insert_at:
        out.extend([const_text, "", "", helper_text, "", ""])
    if no not in taken:
        out.append(line)
text = re.sub(r"\n{4,}", "\n\n\n", "\n".join(out))
# a banner left with nothing but blank lines before the next banner would be a dangling heading
path.write_text(text)
print("moved", len(moving_consts), "constants and", len(helpers), "helpers; order:", [n.name for n in sorted(helpers, key=lambda n: key(n.name))])
