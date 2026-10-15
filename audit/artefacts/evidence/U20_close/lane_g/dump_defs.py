import json, sys
from pathlib import Path
root = Path(sys.argv[1]); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(root))
from buildgen.definitions import definitions_for_toml
for toml in sorted((root / "devices").glob("*.toml")):
    (out / f"{toml.stem}.json").write_text(json.dumps(definitions_for_toml(toml, root / "src"), indent=1))
