"""Rewrap lines [a, b] (1-based, inclusive) of a Markdown file at width 100, keeping the first line's prefix and the
continuation indent of the second line."""
import sys, textwrap
from pathlib import Path
path, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
width = int(sys.argv[4]) if len(sys.argv) > 4 else 100
lines = Path(path).read_text().split("\n")
block = lines[a - 1:b]
first = block[0]
lead = first[: len(first) - len(first.lstrip())]
cont = (block[1][: len(block[1]) - len(block[1].lstrip())]) if len(block) > 1 else lead
text = " ".join(l.strip() for l in block)
# first-line marker ("- ") kept as part of text; initial indent = lead
out = textwrap.wrap(text, width=width, initial_indent=lead, subsequent_indent=cont, break_long_words=False, break_on_hyphens=False)
lines[a - 1:b] = out
Path(path).write_text("\n".join(lines))
print("\n".join(out))
