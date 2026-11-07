import sys, pypdf
r = pypdf.PdfReader(sys.argv[1])
if r.is_encrypted:
    r.decrypt("")
lo, hi = int(sys.argv[2]), int(sys.argv[3])
for i in range(lo, hi + 1):
    t = r.pages[i].extract_text() or ""
    if "Table 279" in t or "Function" in t:
        print(f"=== page index {i}")
        print(t)
