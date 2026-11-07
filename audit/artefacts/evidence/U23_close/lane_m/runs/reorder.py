"""Reorders a JS module's top-level functions per D.15: constants and typedefs first (as found), then non-exported
functions (getters is*/get* first, then others), then exported ones, each group alphabetical (ASCII)."""
import re, sys
path = sys.argv[1]
text = open(path).read()
lines = text.split('\n')
# split into top-level items: an item = leading comment block + declaration until the line before the next item
decl = re.compile(r'^(export )?(async )?(function|const) ')
starts = []
i = 0
n = len(lines)
# find declaration lines
decl_lines = [k for k, l in enumerate(lines) if decl.match(l)]
# attach leading comments: walk back over comment/JSDoc lines (not blank)
items = []
prev_end = None
first_item_start = None
for k in decl_lines:
    s = k
    while s > 0 and (lines[s-1].startswith('//') or lines[s-1].startswith('/**') or lines[s-1].startswith(' *')):
        s -= 1
    items.append([s, k])
# typedef-only blocks (JSDoc not followed by a declaration) are standalone items too
jsdoc_blocks = []
k = 0
while k < n:
    if lines[k] == '/**':
        e = k
        while lines[e] != ' */':
            e += 1
        nxt = e + 1
        if nxt < n and not decl.match(lines[nxt]):
            jsdoc_blocks.append([k, e])
        k = e + 1
    else:
        k += 1
# header: first jsdoc block at line 0 is the module header; keep everything before the first item/typedef (after header) as prefix
cands = sorted([(s, 'decl', d) for s, d in items] + [(s, 'typedef', e) for s, e in jsdoc_blocks if s != 0])
prefix_end = cands[0][0]
prefix = lines[:prefix_end]
chunks = []
for idx, (s, kind, d) in enumerate(cands):
    end = cands[idx+1][0] if idx + 1 < len(cands) else n
    body = lines[s:end]
    while body and body[-1] == '':
        body.pop()
    chunks.append((kind, d, '\n'.join(body)))
def name_of(chunk):
    kind, d, body = chunk
    if kind == 'typedef':
        return None
    m = re.match(r'^(export )?(async )?(function|const) (\w+)', lines[d])
    return m.group(1) is not None, m.group(3), m.group(4)
consts = [c for c in chunks if c[0] == 'typedef' or name_of(c)[1] == 'const']
funcs = [c for c in chunks if c[0] == 'decl' and name_of(c)[1] == 'function']
def key(c):
    exported, _, name = name_of(c)
    getter = bool(re.match(r'^(is|get)[A-Z]', name))
    return (exported, 0 if getter else 1, name)
funcs.sort(key=key)
out = '\n'.join(prefix).rstrip('\n') + '\n\n' + '\n\n'.join(c[2] for c in consts + funcs) + '\n'
before = sorted(c[2] for c in chunks)
after_chunks = consts + funcs
assert sorted(c[2] for c in after_chunks) == before
open(path, 'w').write(out)
for c in consts + funcs:
    print(c[0], name_of(c) if c[0] == 'decl' else c[2].split('\n')[1][:60])
