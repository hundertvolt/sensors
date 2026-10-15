"""Generate every device module and definitions from a given tree into an out dir (fixed build date)."""
import sys
from pathlib import Path
tree = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(tree))
from buildgen.generate import generate_device
from buildgen.definitions import definitions_for_toml
import json
for toml in sorted((tree / "devices").glob("*.toml")):
    r = generate_device(toml, tree / "src", tree / "ext", build_date="2026-01-01")
    (out / f"sensortask_{toml.stem}.py").write_text(r.module_source)
    (out / f"{toml.stem}_boot.py").write_text(r.boot_entry_source)
    (out / f"{toml.stem}_frozen.txt").write_text("\n".join(sorted(r.frozen_modules)))
    try:
        d = definitions_for_toml(toml, tree / "src")
        (out / f"{toml.stem}_defs.json").write_text(json.dumps(d, indent=1, sort_keys=True))
    except TypeError as e:
        print("defs sig", e)
print("ok")
