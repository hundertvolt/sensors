import ast, gzip, sys, re
src = open(sys.argv[1]).read()
tree = ast.parse(src)
blobs = {}
for n in tree.body:
    if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and n.value.args:
        v = ast.literal_eval(n.value.args[0])
        blobs[n.targets[0].id] = v
for k, v in blobs.items():
    if isinstance(v, bytes) and v[:2] == b"\x1f\x8b":
        t = gzip.decompress(v).decode("utf-8", "replace")
        m = re.search(r'"device"\s*:\s*\{[^}]*\}', t)
        if m: print(k, m.group(0)[:200])
