import re, sys, zlib
data = open(sys.argv[1], "rb").read()
lines = []
for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
    try:
        s = zlib.decompress(m.group(1))
    except Exception:
        continue
    cur = []
    for tok in re.finditer(rb"\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f]+>|T\*|ET", s):
        t = tok.group(0)
        if t in (b"T*", b"ET"):
            if cur:
                lines.append("".join(cur)); cur = []
            continue
        if t.startswith(b"("):
            body = re.sub(rb"\\([()\\])", rb"\1", t[1:-1])
        else:
            body = bytes.fromhex(t[1:-1].decode())
        for i in range(0, len(body) - 1, 2):
            g = body[i] * 256 + body[i + 1]
            cur.append(chr(g + 29) if 32 < g + 29 < 127 else " ")
    if cur:
        lines.append("".join(cur))
print("\n".join(lines))
