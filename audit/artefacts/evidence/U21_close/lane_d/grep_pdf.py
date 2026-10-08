import re, sys, zlib
data = open(sys.argv[1], "rb").read()
pat = sys.argv[2].encode()
hits = 0
for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
    try:
        s = zlib.decompress(m.group(1))
    except Exception:
        continue
    # crude text: join TJ/Tj strings
    texts = re.findall(rb"\(((?:\\.|[^\\)])*)\)", s)
    t = b"".join(texts)
    if pat.lower() in t.lower():
        i = t.lower().find(pat.lower())
        print(t[max(0, i-100): i+1600].decode("latin-1"))
        print("=====")
        hits += 1
        if hits > 5: break
print("hits", hits)
