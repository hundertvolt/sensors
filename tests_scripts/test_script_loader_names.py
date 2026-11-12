"""A tests_hardware module loaded for one test takes a name of its own: load_script_module() registers its name in
sys.modules, so the bare name would replace the module every later `import <name>` in the same session binds, and a
test holding the first copy then compares exception classes and patches against a module nobody else reads."""

import ast
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
_HARDWARE = _SCRIPTS.parent / "tests_hardware"


def bare_name_loads(source: str, stems: "set[str]") -> list[int]:
    # Lines of load_script_module(path, "<name>") calls whose name is one a plain import in the session also binds.
    calls = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call)]
    named = [c for c in calls if (c.func.id if isinstance(c.func, ast.Name) else getattr(c.func, "attr", "")) == "load_script_module"]
    return [c.lineno for c in named if len(c.args) > 1 and isinstance(c.args[1], ast.Constant) and c.args[1].value in stems]


def test_no_test_loads_a_hardware_module_under_its_importable_name() -> None:
    stems = {path.stem for path in _HARDWARE.glob("*.py")}
    assert "harness" in stems, f"no tests_hardware module found under {_HARDWARE} - the scan reads nothing"
    found = {path.name: lines for path in sorted(_SCRIPTS.glob("*.py")) if (lines := bare_name_loads(path.read_text(encoding="utf-8"), stems))}
    assert not found, f"load_script_module() under a tests_hardware module's own name (file: lines) - give the copy a name of its own: {found}"


def test_the_scan_sees_a_bare_name_and_passes_a_private_one() -> None:
    assert bare_name_loads('m = load_script_module(p, "harness")\n', {"harness"}) == [1]
    assert bare_name_loads('m = _script_loader.load_script_module(p, "harness")\n', {"harness"}) == [1]
    assert bare_name_loads('m = load_script_module(p, "harness_for_this_test")\n', {"harness"}) == []
