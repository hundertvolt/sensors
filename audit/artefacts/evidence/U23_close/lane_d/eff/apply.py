"""Apply the caching edit to a copy of test_buildgen_definitions.py given as argv[1]."""
import re
import sys
from pathlib import Path

p = Path(sys.argv[1])
s = p.read_text()
s = s.replace("import copy\nimport json\n", "import copy\nimport functools\nimport json\n", 1)
old = '''def _generate(repo_root: Path, src_dir: Path, device: str) -> "dict[str, Any]":
    return _read(definitions_for_toml(repo_root / "devices" / f"{device}.toml", src_dir))
'''
new = '''@functools.cache
def _definitions_text(toml_path: Path, src_dir: Path) -> str:
    # One generation per device file and source tree, kept as JSON text so every caller parses its own copy.
    return json.dumps(definitions_for_toml(toml_path, src_dir))


@functools.cache
def _module_source(toml_path: Path, src_dir: Path, ext_dir: Path) -> str:
    return generate_device(toml_path, src_dir, ext_dir).module_source


def _generate(repo_root: Path, src_dir: Path, device: str) -> "dict[str, Any]":
    parsed: dict[str, Any] = json.loads(_definitions_text(repo_root / "devices" / f"{device}.toml", src_dir))
    return parsed
'''
assert s.count(old) == 1
s = s.replace(old, new)
n_before = s.count("generate_device(")
s = s.replace('generate_device(device_toml(device), src_dir, repo_root / "ext").module_source', '_module_source(device_toml(device), src_dir, repo_root / "ext")')
s = s.replace('generate_device(toml_path, src_dir, repo_root / "ext").module_source', '_module_source(toml_path, src_dir, repo_root / "ext")')
print("generate_device calls:", n_before, "->", s.count("generate_device("))
print("definitions_for_toml calls:", s.count("definitions_for_toml("))
p.write_text(s)
