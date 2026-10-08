import sys, pypdf, re
r = pypdf.PdfReader(sys.argv[1])
pat = re.compile(sys.argv[2])
lo = int(sys.argv[3]) if len(sys.argv) > 3 else 0
hi = int(sys.argv[4]) if len(sys.argv) > 4 else len(r.pages) - 1
for i in range(lo, hi + 1):
    t = r.pages[i].extract_text() or ""
    for m in pat.finditer(t):
        s = max(0, m.start() - 400); e = min(len(t), m.end() + 400)
        print(f"=== page index {i}:\n{t[s:e]}\n")
