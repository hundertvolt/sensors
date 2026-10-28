import sys, tempfile
from pathlib import Path
sys.path.insert(0, "tests_scripts"); sys.path.insert(0, ".")
from _toml_fixtures import base_doc, write_doc
from buildgen.generate import main
doc = base_doc()
doc["instance"][1]["name_ext"] = "a-b"
d = Path(tempfile.mkdtemp(dir="/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u20c"))
print(main([str(write_doc(d, "nameext", doc))]))
