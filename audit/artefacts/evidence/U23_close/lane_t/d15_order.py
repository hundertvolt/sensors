"""Reorders a js/ module's top-level functions per SPEC D.15: the preamble (imports, typedefs, constants) stays,
then non-exported functions, then exported ones; getters (get*/is*), setters (set*), others; alphabetical (ASCII)."""
import re
import sys

path = sys.argv[1]
src = open(path).read()
lines = src.split("\n")
# A chunk starts at a top-level "/**" (or "//" comment run) directly followed by a top-level function.
starts = []
i = 0
while i < len(lines):
    m = re.match(r"^(export )?(async )?function (\w+)", lines[i])
    if m:
        j = i
        while j > 0 and (lines[j - 1].startswith((" *", "/**", "//")) or lines[j - 1] == " */"):
            j -= 1
        starts.append((j, i, m.group(3), bool(m.group(1))))
    i += 1
preamble = "\n".join(lines[: starts[0][0]])
chunks = []
for k, (j, i, name, exported) in enumerate(starts):
    end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
    body = "\n".join(lines[j:end]).rstrip("\n")
    chunks.append((name, exported, body))

def role(name):
    if re.match(r"^(get|is)[A-Z]", name):
        return 2
    if re.match(r"^set[A-Z]", name):
        return 3
    return 4

ordered = sorted(chunks, key=lambda c: (c[1], role(c[0]), c[0]))
out = preamble.rstrip("\n") + "\n\n" + "\n\n".join(c[2] for c in ordered) + "\n"
if sorted(out.split("\n")) != sorted((src.rstrip("\n") + "\n").split("\n")):
    # only blank-line differences are allowed
    a = [l for l in out.split("\n") if l.strip()]
    b = [l for l in src.split("\n") if l.strip()]
    assert sorted(a) == sorted(b), "content changed"
open(path, "w").write(out)
print([c[0] for c in ordered])
