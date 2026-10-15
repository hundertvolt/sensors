"""js/definitions.js keeps its own copies of three bounds - the schema major it accepts, the decimals ceiling and the
poll-interval ceiling - since the browser cannot import buildgen/ or a test. Read as text and pinned to their sources
here (the test_request_timeout_ceiling.py pattern: the source read, never imported)."""

import ast
import operator
import re
from pathlib import Path

from buildgen.definitions import SCHEMA_VERSION
from buildgen.web_tag import _MAX_DECIMALS

_TESTS_SCRIPTS = Path(__file__).resolve().parent
_DEFINITIONS_JS = _TESTS_SCRIPTS.parent / "js" / "definitions.js"
_SHAPE_CHECK = _TESTS_SCRIPTS / "test_buildgen_definitions.py"
_OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Pow: operator.pow}


def _js_int_const(text: str, name: str) -> int:
    # A top-level `const NAME = <int>;` or `export const NAME = <int>;` in the module's text.
    found = re.findall(rf"^(?:export )?const {name} = (\d+);$", text, re.MULTILINE)
    assert len(found) == 1, f"js/definitions.js declares {name} {len(found)} times as an integer constant - expected exactly once"
    return int(found[0])


def _int_expression(node: ast.expr) -> int:
    # An integer literal or +, -, * and ** over them: the one syntax both languages read the same way.
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        value: int = _OPERATORS[type(node.op)](_int_expression(node.left), _int_expression(node.right))
        return value
    raise AssertionError(f"not an integer expression: {ast.unparse(node)}")


def _js_expression_const(text: str, name: str) -> int:
    found = re.findall(rf"^(?:export )?const {name} = ([0-9 *+-]+);$", text, re.MULTILINE)
    assert len(found) == 1, f"js/definitions.js declares {name} {len(found)} times as an integer expression - expected exactly once"
    return _int_expression(ast.parse(found[0], mode="eval").body)


def _python_module_int(path: Path, name: str) -> int:
    # The module-level `NAME = <integer expression>` of a test module, read by ast: no test module is imported.
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and [ast.unparse(target) for target in node.targets] == [name]:
            return _int_expression(node.value)
    raise AssertionError(f"{path.name} defines no {name}")


def test_the_supported_schema_major_is_the_generators() -> None:
    assert _js_int_const(_DEFINITIONS_JS.read_text(encoding="utf-8"), "SUPPORTED_SCHEMA_MAJOR") == int(SCHEMA_VERSION.split(".")[0])


def test_the_decimals_ceiling_is_the_tag_parsers() -> None:
    assert _js_int_const(_DEFINITIONS_JS.read_text(encoding="utf-8"), "MAX_DECIMALS") == _MAX_DECIMALS


def test_the_poll_interval_ceiling_is_the_python_shape_checks() -> None:
    # setTimeout's own ceiling, which both validators hold every poll interval to.
    js_value = _js_expression_const(_DEFINITIONS_JS.read_text(encoding="utf-8"), "MAX_POLL_INTERVAL_MS")
    assert js_value == _python_module_int(_SHAPE_CHECK, "_MAX_POLL_INTERVAL_MS") == 2**31 - 1


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
