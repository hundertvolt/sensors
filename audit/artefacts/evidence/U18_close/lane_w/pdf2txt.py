import sys

import pypdf

r = pypdf.PdfReader(sys.argv[1])
if r.is_encrypted:
    r.decrypt("")
open(sys.argv[2], "w").write("\n".join((p.extract_text() or "") for p in r.pages))
