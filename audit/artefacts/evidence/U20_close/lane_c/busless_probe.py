import sys
from pathlib import Path
sys.path.insert(0, "tests_scripts"); sys.path.insert(0, ".")
from _toml_fixtures import base_doc, write_doc
from buildgen.generate import generate_device
doc = base_doc()
del doc["bus"]
doc["instance"] = [i for i in doc["instance"] if i["driver"] == "neopixel"]
del doc["instance"][0]["wiring"]
del doc["device"]["wiring"]["fram_target"]
import tempfile
d = Path(tempfile.mkdtemp(dir="/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u20c"))
p = write_doc(d, "busless", doc)
print(p.read_text())
try:
    r = generate_device(p, Path("src"), Path("ext"))
    print("generated OK")
except Exception as e:
    print(type(e).__name__, e)
