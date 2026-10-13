import importlib.util, json, sys
from pathlib import Path
wt = Path(sys.argv[1]); sys.path[:0] = [str(wt), str(wt / "tests_scripts")]
spec = importlib.util.spec_from_file_location("head_defs", sys.argv[2]); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
cases = json.loads((wt / "tests_scripts/definitions_shape_cases.json").read_text())
bad = [c["name"] for c in cases if (mod._shape_problems(c["definitions"]) == []) != c["valid"]]
print(f"{len(bad)} of {len(cases)} disagree with HEAD's _shape_problems():"); print("\n".join(bad))
