"""js/definitions.js keeps its own copies of three bounds (the schema major, the decimals and poll-interval ceilings)
and of the field-format set, as do js/field-format.js's renderer and a tests_js leaf check, none able to import
buildgen/. Read as text and pinned to their sources (the test_request_timeout_ceiling.py pattern: never imported)."""

import ast
import operator
import re
from pathlib import Path

from buildgen.definitions import SCHEMA_VERSION
from buildgen.web_tag import _FORMATS, _MAX_DECIMALS

_TESTS_SCRIPTS = Path(__file__).resolve().parent
_DEFINITIONS_JS = _TESTS_SCRIPTS.parent / "js" / "definitions.js"
_FIELD_FORMAT_JS = _TESTS_SCRIPTS.parent / "js" / "field-format.js"
_LEAF_CHECK_JS = _TESTS_SCRIPTS.parent / "tests_js" / "definitions-mockdata-coverage.test.js"
_SHAPE_CHECK = _TESTS_SCRIPTS / "test_buildgen_definitions.py"
_OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Pow: operator.pow}


def _int_expression(node: ast.expr) -> int:
    # An integer literal or +, -, * and ** over them: the one syntax both languages read the same way.
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        value: int = _OPERATORS[type(node.op)](_int_expression(node.left), _int_expression(node.right))
        return value
    raise AssertionError(f"not an integer expression: {ast.unparse(node)}")


def _js_compared_formats(text: str) -> set[str]:
    # Every string a `field.format === "<string>"` comparison in the module's text tests for.
    return set(re.findall(r'\bfield\.format === "([^"\n]*)"', text))


def _js_expression_const(text: str, name: str) -> int:
    found = re.findall(rf"^(?:export )?const {name} = ([0-9 *+-]+);$", text, re.MULTILINE)
    assert len(found) == 1, f"js/definitions.js declares {name} {len(found)} times as an integer expression - expected exactly once"
    return _int_expression(ast.parse(found[0], mode="eval").body)


def _js_format_disjunction(text: str, name: str) -> set[str]:
    # A top-level `function NAME(field)` whose one statement returns `field.format === "<string>" || ...`.
    term = r'field\.format === "[^"\n]*"'
    found = re.findall(rf"^function {name}\(field\) {{\n    return ({term}(?: \|\| {term})*);\n}}$", text, re.MULTILINE)
    assert len(found) == 1, f"{name} is declared {len(found)} times as a disjunction of format tests - expected exactly once"
    formats = re.findall(r'"([^"]*)"', found[0])
    assert len(set(formats)) == len(formats), f"a repeated format: {found[0]}"
    return set(formats)


def _js_int_const(text: str, name: str) -> int:
    # A top-level `const NAME = <int>;` or `export const NAME = <int>;` in the module's text.
    found = re.findall(rf"^(?:export )?const {name} = (\d+);$", text, re.MULTILINE)
    assert len(found) == 1, f"js/definitions.js declares {name} {len(found)} times as an integer constant - expected exactly once"
    return int(found[0])


def _js_map_keys(text: str, name: str) -> set[str]:
    # A top-level `const NAME = new Map([...]);` whose entries are `["<string>", <identifier>],`, one per line.
    entry = r'    \["[^"\n]*", [A-Za-z_$][\w$]*\],\n'
    found = re.findall(rf"^(?:export )?const {name} = new Map\(\[\n((?:{entry})+)\]\);$", text, re.MULTILINE)
    assert len(found) == 1, f"{name} is declared {len(found)} times as a Map of string keys - expected exactly once"
    keys = re.findall(r'\["([^"]*)"', found[0])
    assert len(set(keys)) == len(keys), f"a repeated key: {found[0]}"
    return set(keys)


def _js_string_set(text: str, name: str) -> set[str]:
    # A top-level `const NAME = new Set([...]);` of double-quoted strings, whose list is also a Python literal.
    found = re.findall(rf"^(?:export )?const {name} = new Set\((\[[^\]]*\])\);$", text, re.MULTILINE)
    assert len(found) == 1, f"js/definitions.js declares {name} {len(found)} times as a set literal - expected exactly once"
    return _strings(ast.parse(found[0], mode="eval").body)


def _python_module_int(path: Path, name: str) -> int:
    # The module-level `NAME = <integer expression>` of a test module, read by ast: no test module is imported.
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and [ast.unparse(target) for target in node.targets] == [name]:
            return _int_expression(node.value)
    raise AssertionError(f"{path.name} defines no {name}")


def _python_module_strings(path: Path, name: str) -> set[str]:
    # The module-level `NAME = (<string literals>)` of a test module, read by ast like _python_module_int.
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and [ast.unparse(target) for target in node.targets] == [name]:
            return _strings(node.value)
    raise AssertionError(f"{path.name} defines no {name}")


def _strings(node: ast.expr) -> set[str]:
    # A list or tuple display of string literals, none repeated: a repeat would hide in the set the pins compare.
    assert isinstance(node, ast.List | ast.Tuple), f"not a list of string literals: {ast.unparse(node)}"
    values = [item.value for item in node.elts if isinstance(item, ast.Constant) and isinstance(item.value, str)]
    assert len(values) == len(node.elts), f"not a list of string literals: {ast.unparse(node)}"
    assert len(set(values)) == len(values), f"a repeated string: {ast.unparse(node)}"
    return set(values)


def test_the_supported_schema_major_is_the_generators() -> None:
    assert _js_int_const(_DEFINITIONS_JS.read_text(encoding="utf-8"), "SUPPORTED_SCHEMA_MAJOR") == int(SCHEMA_VERSION.split(".")[0])


def test_the_decimals_ceiling_is_the_tag_parsers() -> None:
    assert _js_int_const(_DEFINITIONS_JS.read_text(encoding="utf-8"), "MAX_DECIMALS") == _MAX_DECIMALS


def test_the_poll_interval_ceiling_is_the_python_shape_checks() -> None:
    # setTimeout's own ceiling, which both validators hold every poll interval to.
    js_value = _js_expression_const(_DEFINITIONS_JS.read_text(encoding="utf-8"), "MAX_POLL_INTERVAL_MS")
    assert js_value == _python_module_int(_SHAPE_CHECK, "_MAX_POLL_INTERVAL_MS") == 2**31 - 1


def test_the_field_formats_are_the_tag_parsers_and_the_python_shape_checks() -> None:
    # The tag parser emits a format, and both validators accept it on a readonly field: one set, three copies.
    js_formats = _js_string_set(_DEFINITIONS_JS.read_text(encoding="utf-8"), "FIELD_FORMATS")
    assert js_formats == _FORMATS == _python_module_strings(_SHAPE_CHECK, "_FIELD_FORMATS")


def test_the_renderers_formats_and_the_leaf_checks_object_formats_are_the_field_formats() -> None:
    # formatFieldValue() reads an object format through RECORD_FORMATTERS and any other by its own `===` branch, and the
    # tests_js leaf check exempts the object formats: a format either one misses renders as "[object Object]".
    renderer = _FIELD_FORMAT_JS.read_text(encoding="utf-8")
    record_formats = _js_map_keys(renderer, "RECORD_FORMATTERS")
    branched = _js_compared_formats(renderer)
    assert not record_formats & branched, f"formats both in RECORD_FORMATTERS and branched on: {sorted(record_formats & branched)}"
    assert record_formats | branched == _js_string_set(_DEFINITIONS_JS.read_text(encoding="utf-8"), "FIELD_FORMATS")
    assert _js_format_disjunction(_LEAF_CHECK_JS.read_text(encoding="utf-8"), "isObjectFormat") == record_formats


def test_the_constant_reader_takes_both_declaration_forms_and_nothing_else() -> None:
    assert _js_int_const("export const A = 1;\n", "A") == 1
    assert _js_int_const("const A = 100;\n", "A") == 100
    assert not re.findall(r"^(?:export )?const A = (\d+);$", "let A = 1;\n    const A = 2;\n", re.MULTILINE)


def test_the_expression_reader_evaluates_integer_arithmetic_and_refuses_anything_else() -> None:
    assert _js_expression_const("const A = 2 ** 31 - 1;\n", "A") == 2147483647
    assert _python_module_int(_SHAPE_CHECK, "_MAX_POLL_INTERVAL_MS") == 2147483647
    for refused in ("2 / 1", "abs(1)", "1.5", "True"):
        try:
            _int_expression(ast.parse(refused, mode="eval").body)
        except AssertionError:
            continue
        raise AssertionError(f"{refused} was read as an integer expression")


def test_the_string_set_reader_takes_string_literals_once_each_and_refuses_anything_else() -> None:
    assert _js_string_set('const A = new Set(["x", "y"]);\n', "A") == {"x", "y"}
    for refused in ('["x", 1]', '["x", "x"]', "[x]", '{"x"}'):
        try:
            _strings(ast.parse(refused, mode="eval").body)
        except AssertionError:
            continue
        raise AssertionError(f"{refused} was read as a list of distinct string literals")


def test_the_format_readers_take_their_one_shape_and_refuse_anything_else() -> None:
    assert _js_map_keys('const A = new Map([\n    ["x", f],\n    ["y", g],\n]);\n', "A") == {"x", "y"}
    assert _js_format_disjunction('function a(field) {\n    return field.format === "x" || field.format === "y";\n}\n', "a") == {"x", "y"}
    assert _js_compared_formats('if (field.format === "x" && other.format === "z") {}\n') == {"x"}
    refused = [
        (_js_map_keys, 'const A = new Map([\n    ["x", f],\n    [y, g],\n]);\n'),  # a key that is no string literal
        (_js_map_keys, 'const A = new Map([\n    ["x", f],\n    ["x", g],\n]);\n'),  # a repeated key
        (_js_format_disjunction, 'function A(field) {\n    return field.format === "x" || field.kind === "y";\n}\n'),
        (_js_format_disjunction, 'function A(field) {\n    return field.format === "x" || field.format === "x";\n}\n'),
    ]
    for reader, text in refused:
        try:
            reader(text, "A")
        except AssertionError:
            continue
        raise AssertionError(f"{reader.__name__} read {text!r}")
