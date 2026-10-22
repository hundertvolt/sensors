"""Product values the hardware levels copy are read or cited: an upper-case name in tests_hardware/ bound to a number
equal to a src/ _VAL_* bound or default (or a notification signal's) of a field its name shares a word with fails,
unless a `# source:` comment cites where it comes from; a tagged tunable is pinned by the register instead."""

import ast
import re
from functools import cache
from pathlib import Path

from buildgen.schema_ast import extract_field_schemas
from buildgen.signals import WARN_SIGNALS

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CONSTANT_NAME = re.compile(r"_?[A-Z][A-Z0-9_]*")
_MIN_WORD = 3


def _words(name: str) -> "frozenset[str]":
    # CamelCase and snake_case split into lower-case words of at least three letters.
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return frozenset(w.lower() for w in re.split(r"[_\W]+", spaced) if len(w) >= _MIN_WORD)


@cache
def product_values(src: Path = _REPO_ROOT / "src") -> "dict[float, list[tuple[str, frozenset[str]]]]":
    # Number -> (where it is declared, the field's words) for every _VAL_* min, max and default and every signal's.
    found: dict[float, list[tuple[str, frozenset[str]]]] = {}
    for path in sorted(src.glob("*.py")):
        for field, (_kind, default, low, high, _special) in extract_field_schemas(path).items():
            for role, value in (("default", default), ("min", low), ("max", high)):
                if isinstance(value, int | float) and not isinstance(value, bool):
                    found.setdefault(float(value), []).append((f"src/{path.name} {field} {role}", _words(field)))
    for signal in WARN_SIGNALS.values():
        for role, value in (("default", signal.default), ("min", signal.min), ("max", signal.max)):
            if isinstance(value, int | float) and not isinstance(value, bool):
                found.setdefault(float(value), []).append((f"buildgen/signals.py {signal.name} {role}", _words(signal.name)))
    return found


def copies(path: Path, values: "dict[float, list[tuple[str, frozenset[str]]]]") -> "list[str]":
    lines = path.read_text(encoding="utf-8").splitlines()
    found: list[str] = []
    for node in ast.walk(ast.parse("\n".join(lines))):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, int | float) and not isinstance(node.value.value, bool)):
            continue
        context = lines[node.lineno - 1] + (lines[node.lineno - 2] if node.lineno > 1 else "")
        if "# source:" in context or "@tunable" in context:
            continue
        for target in [t for t in node.targets if isinstance(t, ast.Name) and _CONSTANT_NAME.fullmatch(t.id)]:
            owners = [owner for owner, words in values.get(float(node.value.value), []) if words & _words(target.id)]
            found += [f"{path.name}:{node.lineno} {target.id} = {node.value.value!r} copies {owners[0]}"] if owners else []
    return found


def test_no_hardware_module_copies_a_product_value_uncited() -> None:
    found = [line for path in sorted((_REPO_ROOT / "tests_hardware").rglob("*.py")) for line in copies(path, product_values())]
    assert not found, "read these from src/ (or cite them with a `# source:` comment a source-reading test pins):\n  " + "\n  ".join(found)


def test_the_copy_check_bites(tmp_path: Path) -> None:
    module = tmp_path / "copy.py"
    module.write_text("DEBUG_LEVEL_MAX = 5\n_STEPS = 5\nLEVEL = 5  # source: src/asy_system_service.py _VAL_DEBUG_LEVEL max\n# @tunable l4.x = 5\nDEBUG_LEVEL_TOP = 5\n", encoding="utf-8")
    assert copies(module, product_values()) == ["copy.py:1 DEBUG_LEVEL_MAX = 5 copies src/asy_system_service.py DebugLevel max"]
