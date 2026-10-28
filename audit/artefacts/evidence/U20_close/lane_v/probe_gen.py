import sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/tests_scripts")
from _toml_fixtures import base_doc, write_doc
from buildgen.generate import generate_device
from buildgen.validate import build_model
tmp = Path(sys.argv[2]); tmp.mkdir(exist_ok=True)
src = Path(sys.argv[1]) / "src"
doc = base_doc()
doc["instance"][1]["wiring"]["temperature_source"] = {"default": True, "temperature": 20}
doc["instance"][4]["wiring"]["signal_sink"] = {"default": True}
del doc["instance"][4]["wiring"]["warn_co2"]
r = generate_device(write_doc(tmp, "fixture", doc), src)
for line in r.module_source.splitlines():
    if "SGP40_Reader(" in line or "NotificationService(" in line or "WifiService(" in line or "SystemService(" in line:
        print(line.strip()[:300])
m = build_model(write_doc(tmp, "fixture", base_doc()), src)
print([(t.field, t.op, t.value) for t in m.instances[("scd30","")].requires_tags])
