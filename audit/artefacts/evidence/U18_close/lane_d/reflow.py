"""Reflow the paragraph (or list item) containing a marker string to a given width."""
import sys, textwrap
path, marker, width = sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 100
lines = open(path, encoding='utf-8').read().split('\n')
idx = [i for i, l in enumerate(lines) if marker in l]
assert len(idx) == 1, idx
i = idx[0]
def is_break(l):
    s = l.strip()
    return s == '' or s.startswith(('|', '#', '```', '<!--'))
indent = len(lines[i]) - len(lines[i].lstrip())
# walk up to paragraph start: a line starting a list item at <= indent, or after a blank
start = i
while start > 0 and not is_break(lines[start - 1]):
    cur = lines[start]
    if cur.lstrip().startswith(('- ', '* ')) and (len(cur) - len(cur.lstrip())) <= indent:
        break
    start -= 1
end = i
while end + 1 < len(lines) and not is_break(lines[end + 1]) and not lines[end + 1].lstrip().startswith(('- ', '* ')):
    end += 1
first = lines[start]
lead = first[: len(first) - len(first.lstrip())]
bullet = ''
body_first = first.lstrip()
if body_first.startswith(('- ', '* ')):
    bullet = body_first[:2]
    body_first = body_first[2:]
cont = lead + (' ' * len(bullet))
text = ' '.join([body_first] + [l.strip() for l in lines[start + 1:end + 1]])
wrapped = textwrap.wrap(text, width=width, initial_indent=lead + bullet, subsequent_indent=cont, break_long_words=False, break_on_hyphens=False)
lines[start:end + 1] = wrapped
open(path, 'w', encoding='utf-8').write('\n'.join(lines))
print(f'reflowed {path}:{start+1}-{end+1} -> {len(wrapped)} lines')
