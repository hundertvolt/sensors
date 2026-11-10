"""The ISL29125 constants the twin keeps apart from the driver agree with it: the chip fake's register map and bits, and
the copies in its two test files that test_const_mirrors.py cannot see (a different name, or a value derived from
the driver's). Every copy is read by AST, never imported, and any disagreement fails."""

import ast

import pytest
from _repo_scan import REPO_ROOT

_DRIVER = "src/asy_isl29125_driver.py"
_CHIP = "digital_twin/_isl29125_chip.py"
_CHIP_TESTS = "tests/test_digital_twin_isl29125.py"
_AUTORANGE_TESTS = "tests/test_digital_twin_isl29125_autorange.py"

# Each copy's name in its file and the driver const() it copies. CONFIG3 is not compared: the driver writes no CONFIG3
# register of its own, while the fake models it (agent, 2026-10-14).
_CHIP_COPIES = {
    "_DEVICE_ID": "_DEVICE_ID",
    "_REG_DEVICE_ID": "_REGISTER_DEVICE_ID",
    "_REG_CONFIG1": "_REGISTER_CONFIG1",
    "_REG_CONFIG2": "_REGISTER_CONFIG2",
    "_REG_THRESH_LOW_L": "_REGISTER_THRESHOLDS",
    "_REG_STATUS": "_REGISTER_STATUS",
    "_REG_DATA": "_REGISTER_DATA",
    "_CONFIG1_RNG": "_CONFIG1_RNG",
    "_CONFIG1_BITS": "_CONFIG1_BITS",
    "_STATUS_RGBTHF": "_STATUS_RGBTHF",
    "_STATUS_CONVENF": "_STATUS_CONVENF",
    "_STATUS_BOUTF": "_STATUS_BOUTF",
    "_STATUS_RGBCF_SHIFT": "_STATUS_RGBCF_SHIFT",
    "_FS_LOW_LUX": "_RANGE_LOW_LUX",
}
_CHIP_TEST_COPIES = {
    "_ADDR_ID": "_REGISTER_DEVICE_ID",
    "_ADDR_CONFIG1": "_REGISTER_CONFIG1",
    "_ADDR_CONFIG2": "_REGISTER_CONFIG2",
    "_ADDR_THRESH": "_REGISTER_THRESHOLDS",
    "_ADDR_STATUS": "_REGISTER_STATUS",
    "_ADDR_DATA": "_REGISTER_DATA",
    "_RNG_HIGH": "_CONFIG1_RNG",
    "_BITS_12": "_CONFIG1_BITS",
}


def _auto_range_thresh_default(driver: "dict[str, ast.expr]") -> float:
    # The default field of the driver's AutoRangeThresh schema row, a percentage of the range's full scale.
    row = driver["_VAL_AUTO_RANGE_THRESH"]
    assert isinstance(row, ast.Tuple)
    field = row.elts[0]
    assert isinstance(field, ast.Tuple)
    return _number(field.elts[2])


def _bindings(source: str) -> "dict[str, ast.expr]":
    # Every module-level `NAME = value` (a const() call unwrapped to its argument).
    found: dict[str, ast.expr] = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "const":
                value = value.args[0]
            found[node.targets[0].id] = value
    return found


def _chip_gain_ratio_default(source: str) -> float:
    # ISL29125Chip.__init__'s gain_ratio default: the per-instance ratio the autorange test expects the driver to learn.
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            names = [arg.arg for arg in node.args.args]
            if "gain_ratio" in names:
                defaults = node.args.defaults
                return _number(defaults[names.index("gain_ratio") - (len(names) - len(defaults))])
    raise AssertionError(f"{_CHIP}: no __init__ with a gain_ratio default")


def _literal(bindings: "dict[str, ast.expr]", name: str) -> float:
    return _number(bindings[name])


def _number(node: ast.expr) -> float:
    # A numeric literal, or a sum or product of them (the drift a test plants is one).
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mult)):
        left, right = _number(node.left), _number(node.right)
        return left + right if isinstance(node.op, ast.Add) else left * right
    raise AssertionError(f"not a numeric literal: {ast.unparse(node)}")


def _sources() -> "dict[str, str]":
    return {path: (REPO_ROOT / path).read_text(encoding="utf-8") for path in (_DRIVER, _CHIP, _CHIP_TESTS, _AUTORANGE_TESTS)}


def copy_problems(sources: "dict[str, str]") -> "list[str]":
    # Each disagreement between a copy and the driver, as "<file>: <copy> = <value>, the driver's <name> = <value>".
    driver, chip = _bindings(sources[_DRIVER]), _bindings(sources[_CHIP])
    chip_tests, autorange = _bindings(sources[_CHIP_TESTS]), _bindings(sources[_AUTORANGE_TESTS])
    problems: list[str] = []
    for file, copies, bindings in ((_CHIP, _CHIP_COPIES, chip), (_CHIP_TESTS, _CHIP_TEST_COPIES, chip_tests)):
        for copy, original in copies.items():
            ours, theirs = _literal(bindings, copy), _literal(driver, original)
            if ours != theirs:
                problems.append(f"{file}: {copy} = {ours!r}, the driver's {original} = {theirs!r}")
    rgbcf_mask = _literal(chip_tests, "_STATUS_RGBCF_MASK")
    if rgbcf_mask != 0x03 << int(_literal(driver, "_STATUS_RGBCF_SHIFT")):  # B5:B4, two bits at the driver's shift
        problems.append(f"{_CHIP_TESTS}: _STATUS_RGBCF_MASK = {rgbcf_mask!r} is not the two bits at the driver's _STATUS_RGBCF_SHIFT")
    gain_ratio = _literal(autorange, "_CHIP_GAIN_RATIO")
    if gain_ratio != _chip_gain_ratio_default(sources[_CHIP]):
        problems.append(f"{_AUTORANGE_TESTS}: _CHIP_GAIN_RATIO = {gain_ratio!r} is not the chip fake's gain_ratio default")
    switch_up = _literal(autorange, "_SWITCH_UP_LUX")
    expected = _auto_range_thresh_default(driver) / 100 * _literal(driver, "_RANGE_LOW_LUX")
    if abs(switch_up - expected) > 1e-9:
        problems.append(f"{_AUTORANGE_TESTS}: _SWITCH_UP_LUX = {switch_up!r}, the driver's AutoRangeThresh default of _RANGE_LOW_LUX = {expected!r}")
    return problems


def test_the_twin_copies_of_the_isl29125_constants_equal_the_driver() -> None:
    assert copy_problems(_sources()) == []


def test_every_compared_copy_is_one_test_const_mirrors_cannot_see() -> None:
    # A test-file copy named like a driver const() is test_const_mirrors.py's: listing it here too would check it twice.
    driver = _bindings(_sources()[_DRIVER])
    assert not set(_CHIP_TEST_COPIES) & set(driver), sorted(set(_CHIP_TEST_COPIES) & set(driver))


_PLANTS = [(_CHIP, name) for name in sorted(_CHIP_COPIES)] + [(_CHIP_TESTS, name) for name in sorted(_CHIP_TEST_COPIES)]
_PLANTS += [(_CHIP_TESTS, "_STATUS_RGBCF_MASK"), (_AUTORANGE_TESTS, "_CHIP_GAIN_RATIO"), (_AUTORANGE_TESTS, "_SWITCH_UP_LUX")]


@pytest.mark.parametrize(("file", "name"), _PLANTS)
def test_a_planted_drift_of_each_copy_fails(file: str, name: str) -> None:
    sources = _sources()
    lines = sources[file].split("\n")
    (index,) = [i for i, line in enumerate(lines) if line.startswith(f"{name} = ")]
    lines[index] = lines[index].replace(" = ", " = 1 + ", 1)
    sources[file] = "\n".join(lines)
    problems = copy_problems(sources)
    assert len(problems) == 1, problems
    assert name in problems[0], problems


def test_the_chip_fakes_gain_ratio_default_is_read_from_its_signature() -> None:
    source = "class ISL29125Chip:\n    def __init__(self, gain_ratio: float = 3.5) -> None:\n        pass\n"
    assert _chip_gain_ratio_default(source) == 3.5
