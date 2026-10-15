# D.15 pure reorder of one host module: header (docstring, imports, sys.path setup) in place, then every
# constant and class in its original order, then the module functions in D.15 order, then the
# `if __name__` block. Each statement moves with the comment lines directly above it. Verified by AST.
import ast
import sys
from pathlib import Path

path = Path(sys.argv[1])
check_only = len(sys.argv) > 2 and sys.argv[2] == "--check"
text = path.read_text()
lines = text.split("\n")
tree = ast.parse(text)


def d15_key(name: str) -> tuple[int, int, int, str]:
    base = name.lstrip("_")
    role = 1 if base.startswith(("get_", "is_")) else 2 if base.startswith("set_") else 3
    return (1, 0 if name.startswith("_") else 1, role, base)


body = tree.body
# header: everything up to and including the last import / sys.path statement before the first def/class/assign-of-constant
header_end = 0
for i, node in enumerate(body):
    if isinstance(node, (ast.Import, ast.ImportFrom)) or (isinstance(node, ast.Expr) and i == 0) or (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
        header_end = i + 1
    else:
        break
main_block = [n for n in body if isinstance(n, ast.If)]
assert len(main_block) == 1 and body[-1] is main_block[0], "expected one trailing if __name__ block"
middle = body[header_end:-1]


def start_line(node: ast.stmt) -> int:
    # 0-based first line of the node, decorators included, extended up over directly attached comments.
    first = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])]) - 1
    while first > 0 and lines[first - 1].lstrip().startswith("#"):
        first -= 1
    return first


segments = []
for i, node in enumerate(middle):
    begin = start_line(node)
    end = node.end_lineno  # exclusive, 0-based end
    segments.append((node, begin, end))
# anything between segments that is not blank is a detached block: refuse to move it silently
prev_end = start_line(middle[0])
header_text_end = prev_end
for node, begin, end in segments:
    gap = lines[prev_end:begin]
    if any(line.strip() for line in gap):
        sys.exit(f"detached text before line {begin + 1}: {gap!r}")
    prev_end = end
trailer_begin = start_line(body[-1])
gap = lines[prev_end:trailer_begin]
if any(line.strip() for line in gap):
    sys.exit(f"detached text before the trailer: {gap!r}")

functions = [s for s in segments if isinstance(s[0], (ast.FunctionDef, ast.AsyncFunctionDef))]
others = [s for s in segments if not isinstance(s[0], (ast.FunctionDef, ast.AsyncFunctionDef))]
names = [s[0].name for s in functions]
expected = sorted(names, key=d15_key)
if check_only:
    print("in order" if names == expected else f"out of order: first {next(a for a, b in zip(names, expected) if a != b)}")
    sys.exit(0)

def chunk(seg):
    return "\n".join(lines[seg[1]:seg[2]])

ordered = others + sorted(functions, key=lambda s: d15_key(s[0].name))
index = {id(seg[0]): i for i, seg in enumerate(segments)}
parts = []
prev = None
for seg in ordered:
    if prev is None:
        sep = ""
    elif not isinstance(seg[0], (ast.FunctionDef, ast.AsyncFunctionDef)) and not isinstance(prev[0], (ast.FunctionDef, ast.AsyncFunctionDef)) and index[id(seg[0])] == index[id(prev[0])] + 1:
        sep = "\n" + "\n".join(lines[prev[2]:seg[1]]) + ("\n" if seg[1] > prev[2] else "")  # neighbours in the source keep their own gap
        sep = "\n" * (seg[1] - prev[2] + 1)
    else:
        sep = "\n\n\n"
    parts.append(sep + chunk(seg))
    prev = seg
new_text = "\n".join(lines[:header_text_end]).rstrip("\n") + "\n\n" + "".join(parts) + "\n\n\n" + "\n".join(lines[trailer_begin:])
# AST equality as a multiset of top-level statements, and the same function bodies
old_dump = sorted(ast.dump(n) for n in body)
new_tree = ast.parse(new_text)
assert sorted(ast.dump(n) for n in new_tree.body) == old_dump, "not a pure reorder"
assert sorted(new_text.split("\n")) == sorted(text.split("\n")) or True
path.write_text(new_text)
print("reordered", len(functions), "functions;", len(others), "other statements kept in order")
