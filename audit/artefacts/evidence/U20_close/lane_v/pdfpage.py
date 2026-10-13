import sys, pypdf
r = pypdf.PdfReader(sys.argv[1])
for i in sys.argv[2:]:
    print(f"=== page index {i}")
    print(r.pages[int(i)].extract_text())
