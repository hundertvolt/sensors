import sys
from pathlib import Path
root = Path(sys.argv[1]); sys.path[:0] = [str(root), str(root / "tests_scripts")]
import test_toml_schema_contract as t
for table, key, req in sorted(t._build_rows(root / "src")):
    print(f"| `{table}` | `{key}` | {'yes' if req else 'no'} | | |")
