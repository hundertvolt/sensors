import re, sys, zlib
data = open(sys.argv[1], "rb").read()
out = []
for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
    try:
        s = zlib.decompress(m.group(1))
    except Exception:
        continue
    for t in re.findall(rb"\[(.*?)\]\s*TJ|\((.*?)\)\s*Tj|<([0-9A-Fa-f]+)>\s*Tj", s, re.S):
        if t[0]:
            parts = re.findall(rb"\((.*?)(?<!\\)\)|<([0-9A-Fa-f]+)>", t[0])
            for p in parts:
                if p[0]:
                    out.append(p[0])
                else:
                    out.append(bytes.fromhex(p[1].decode()))
        elif t[1]:
            out.append(t[1])
        else:
            out.append(bytes.fromhex(t[2].decode()))
        out.append(b" ")
    out.append(b"\n")
raw = b"".join(out)
shift = int(sys.argv[2]) if len(sys.argv) > 2 else 0
txt = "".join(chr(b + shift) if 0 < b + shift < 0x110000 and b not in (10, 32) else chr(b) for b in raw)
print(txt)
