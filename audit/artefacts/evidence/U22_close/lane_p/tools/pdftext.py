import re, sys, zlib
data = open(sys.argv[1], "rb").read()
out = []
for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
    raw = m.group(1)
    try:
        dec = zlib.decompress(raw)
    except Exception:
        continue
    # text show operators: (..) Tj, [..] TJ, <hex> Tj
    for t in re.finditer(rb"\[(.*?)\]\s*TJ|<([0-9A-Fa-f]+)>\s*Tj|\((.*?)\)\s*Tj", dec, re.S):
        if t.group(1) is not None:
            parts = re.findall(rb"<([0-9A-Fa-f]+)>|\(((?:\\.|[^\\)])*)\)", t.group(1))
            s = b""
            for h, l in parts:
                s += bytes.fromhex(h.decode()) if h else l
        elif t.group(2) is not None:
            s = bytes.fromhex(t.group(2).decode())
        else:
            s = t.group(3)
        out.append(s)
    out.append(b"\n")
shift = int(sys.argv[2]) if len(sys.argv) > 2 else 0
text = b"".join(out).replace(b"\x00", b"")
print("".join(chr(b + shift) if 32 <= b + shift < 127 else ("\n" if b == 10 else "?") for b in text))
