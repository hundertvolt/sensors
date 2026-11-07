import sys
import tempfile
from pathlib import Path
root = Path.cwd()
sys.path[:0] = [str(root), str(root / "tests_scripts")]
from _toml_fixtures import base_doc, write_doc
from buildgen.validate import build_model
doc = base_doc()
doc["instance"][0]["wiring"] = "fram"
with tempfile.TemporaryDirectory() as d:
    try:
        build_model(write_doc(Path(d), "dev", doc), root / "src")
    except Exception as e:
        print(type(e).__name__, "|", e, "|", getattr(e, "rule", None))
