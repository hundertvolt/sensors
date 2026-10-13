import sys
sys.path.insert(0, sys.argv[3])
import pypdf
src, out = sys.argv[1], sys.argv[2]
r = pypdf.PdfReader(src)
with open(out, "w", encoding="utf-8") as f:
    for i, p in enumerate(r.pages):
        f.write(f"\n=== page {i+1} ===\n")
        f.write(p.extract_text() or "")
print(len(r.pages))
