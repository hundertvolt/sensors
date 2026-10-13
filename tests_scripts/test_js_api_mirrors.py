"""The JS copies of src/'s wire facts (SPECIFICATION.md Part G.2's mirror obligation) equal their sources: js/api-contract.js,
the mock's counter cap, code table, busy and unknown-code texts and DNS bounds, and every device's dispatch-field definitions. Both sides are
read as source (Python by ast, JS by pattern), never imported, and each pin bites on a planted mismatch in a temporary copy."""

import ast
import json
import operator
import re
import shutil
from functools import cache
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.definitions import definitions_for_toml
from buildgen.jsontypes import JsonDict, JsonValue

_REPO_ROOT = Path(__file__).resolve().parent.parent
# Every file a pin reads: the Python sources and the two JS modules that copy them.
_CONFIG_MANAGER = "src/asy_config_manager.py"
_BASE_CLASSES = "src/asy_base_classes.py"
_API_RESPONSE = "src/asy_api_response.py"
_PRINT_LOG = "src/asy_print_log.py"
_WEBSERVER = "src/asy_webserver_service.py"
_DNS_CLIENT = "src/asy_dns_client.py"
_NTP_CLIENT = "src/asy_ntp_client.py"
_CODEGEN = "buildgen/codegen.py"
_CONTRACT = "js/api-contract.js"
_MOCK = "js/mock-server.js"
_READ_FILES = (_CONFIG_MANAGER, _BASE_CLASSES, _API_RESPONSE, _PRINT_LOG, _WEBSERVER, _DNS_CLIENT, _NTP_CLIENT, _CODEGEN, _CONTRACT, _MOCK)
_RESULT_WORDS = ("VALID", "UNCHANGED", "INVALID", "FAILED")
_OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Pow: operator.pow}


def _literal(node: ast.expr, names: "dict[str, ast.expr]", outer: "dict[str, object]") -> object:
    # A module-level value: literals, tuples, lists, dicts, const(...), a name the module or `outer` binds, -x and + - * **.
    if isinstance(node, ast.Constant):
        value: object = node.value
        return value
    if isinstance(node, (ast.Tuple, ast.List)):
        return [_literal(item, names, outer) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {_literal(key, names, outer): _literal(value, names, outer) for key, value in zip(node.keys, node.values, strict=True) if key is not None}
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "const" and len(node.args) == 1:
        return _literal(node.args[0], names, outer)
    if isinstance(node, ast.Name):
        if node.id in outer:
            return outer[node.id]
        return _literal(names[node.id], names, outer)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = _literal(node.operand, names, outer)
        assert isinstance(operand, (int, float)), f"not a number: {ast.unparse(node)}"
        return -operand
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        result: object = _OPERATORS[type(node.op)](_literal(node.left, names, outer), _literal(node.right, names, outer))
        return result
    raise AssertionError(f"not a literal: {ast.unparse(node)}")


def _py_values(path: Path, *names: str, outer: "dict[str, object] | None" = None) -> "dict[str, object]":
    # The named module-level assignments of one Python source, evaluated without importing it.
    assigned: dict[str, ast.expr] = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            assigned[node.targets[0].id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            assigned[node.target.id] = node.value
    missing = [name for name in names if name not in assigned]
    assert not missing, f"{path.name} assigns no {missing}"
    return {name: _literal(assigned[name], assigned, outer or {}) for name in names}


def _gmtime_keys(path: Path) -> "list[object]":
    # The first six keys of the dict the emitted _gmtimestruct_to_dict() returns: the template line after its def line.
    texts = [node.value for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    start = next(i for i, text in enumerate(texts) if text.startswith("def _gmtimestruct_to_dict("))
    returned = next(text for text in texts[start:] if text.strip().startswith("return {"))
    body = ast.parse(returned.strip().removeprefix("return "), mode="eval").body
    assert isinstance(body, ast.Dict), f"_gmtimestruct_to_dict() returns no dict literal: {returned.strip()}"
    keys: list[object] = [key.value for key in body.keys if isinstance(key, ast.Constant)]
    return keys[:6]


def _js_const(text: str, where: str, name: str) -> str:
    # The value text of a top-level `const NAME = <value>;` (an `export` in front and a trailing comment allowed).
    found = re.findall(rf"^(?:export )?const {name} = (.+?);(?:\s*//.*)?$", text, re.MULTILINE)
    assert len(found) == 1, f"{where} declares {name} {len(found)} times - expected exactly once"
    return str(found[0])


def _js_number(value: str) -> object:
    # A JS integer expression read with Python's grammar: both read + - * ** and integer literals alike.
    return _literal(ast.parse(value, mode="eval").body, {}, {})


def _js_code_table(value: str) -> "dict[object, object]":
    # `{ 0: "text", ... }`, never evaluated, as tests_js/_source_constants.js's readObjectConst() reads it.
    return {int(code): text for code, text in re.findall(r'(\d+):\s*"([^"]*)"', value)}


def _js_marker(text: str) -> "dict[str, str]":
    # isUnavailable()'s one key and value, as the function compares them.
    body = text[text.index("export function isUnavailable(") :]
    key = re.search(r'keys\[0\] === "([^"]+)"', body)
    word = re.search(r'\)\.\w+ === "([^"]+)"', body)
    assert key is not None and word is not None, "isUnavailable() compares no key and value literal"
    return {key.group(1): word.group(1)}


def _mirror_pairs(root: Path) -> "list[tuple[str, object, object]]":
    # (pin, the JS copy, its Python source), one per mirrored fact.
    words = _py_values(root / _CONFIG_MANAGER, *_RESULT_WORDS)
    base = _py_values(root / _BASE_CLASSES, "COUNTER_CAP", "UNAVAILABLE")
    response = _py_values(root / _API_RESPONSE, "_STANDARD_CODES", "_UNKNOWN_DESCR")
    server = _py_values(root / _WEBSERVER, "_LED_BUSY_DESCR", "_LIGHT_CMD_FIELDS", "_UNAVAILABLE_TEXT", outer={"UNAVAILABLE": base["UNAVAILABLE"]})
    label_max = _py_values(root / _DNS_CLIENT, "DNS_LABEL_MAX")["DNS_LABEL_MAX"]
    fallback_max = _py_values(root / _NTP_CLIENT, "_DNS_FALLBACK_MAX")["_DNS_FALLBACK_MAX"]
    seconds = server["_LIGHT_CMD_FIELDS"]
    assert isinstance(seconds, list), "_LIGHT_CMD_FIELDS is no tuple of field records"
    contract = (root / _CONTRACT).read_text(encoding="utf-8")
    mock = (root / _MOCK).read_text(encoding="utf-8")
    unknown = re.search(r'STANDARD_CODES\[code\] \?\? "([^"]*)"', mock)
    pairs: list[tuple[str, object, object]] = [(f"{_CONTRACT} {name}", json.loads(_js_const(contract, _CONTRACT, name)), words[name]) for name in _RESULT_WORDS]
    pairs += [
        (f"{_CONTRACT} ERR_COUNT_CAP", _js_number(_js_const(contract, _CONTRACT, "ERR_COUNT_CAP")), _py_values(root / _PRINT_LOG, "_MAX_CNT")["_MAX_CNT"]),
        (f"{_CONTRACT} GMTIME_KEYS", json.loads(_js_const(contract, _CONTRACT, "GMTIME_KEYS")), _gmtime_keys(root / _CODEGEN)),
        (f"{_CONTRACT} isUnavailable()", _js_marker(contract), json.loads(str(server["_UNAVAILABLE_TEXT"]))),
        (f"{_MOCK} COUNTER_CAP", _js_number(_js_const(mock, _MOCK, "COUNTER_CAP")), base["COUNTER_CAP"]),
        (f"{_MOCK} STANDARD_CODES", _js_code_table(_js_const(mock, _MOCK, "STANDARD_CODES")), response["_STANDARD_CODES"]),
        (f"{_MOCK} makeResponse()'s unknown-code text", None if unknown is None else unknown.group(1), response["_UNKNOWN_DESCR"]),
        (f"{_MOCK} LED_BUSY_DESCR", json.loads(_js_const(mock, _MOCK, "LED_BUSY_DESCR")), server["_LED_BUSY_DESCR"]),
        # The seconds member: the last of _LIGHT_CMD_FIELDS, as _dispatch_notification_led() unpacks them.
        (f"{_MOCK} LED_DURATION_MEMBER", json.loads(_js_const(mock, _MOCK, "LED_DURATION_MEMBER")), _record(seconds[-1])[0]),
        (f"{_MOCK} DNS_LABEL_MAX", _js_number(_js_const(mock, _MOCK, "DNS_LABEL_MAX")), label_max),
        (f"{_MOCK} DNS_FALLBACK_MAX", _js_number(_js_const(mock, _MOCK, "DNS_FALLBACK_MAX")), fallback_max),
    ]
    return pairs


def _record(value: object) -> "list[object]":
    assert isinstance(value, list), f"not a field record: {value!r}"
    return value


def _mirror_problems(root: Path) -> "list[str]":
    return [f"{pin}: {copy!r} != {source!r}" for pin, copy, source in _mirror_pairs(root) if copy != source]


def test_every_js_mirror_equals_its_src_source() -> None:
    assert _mirror_problems(_REPO_ROOT) == []


# (file, its text, the planted text, the pin that must report it): one plant per pin.
_PLANTS = (
    (_CONTRACT, 'export const VALID = "Valid";', 'export const VALID = "valid";', f"{_CONTRACT} VALID"),
    (_CONTRACT, 'export const FAILED = "Failed";', 'export const FAILED = "Fail";', f"{_CONTRACT} FAILED"),
    (_CONTRACT, "export const ERR_COUNT_CAP = 65535;", "export const ERR_COUNT_CAP = 65534;", f"{_CONTRACT} ERR_COUNT_CAP"),
    (_CONTRACT, '"Minute", "Second"]', '"Second", "Minute"]', f"{_CONTRACT} GMTIME_KEYS"),
    (_CONTRACT, '=== "unavailable"', '=== "Unavailable"', f"{_CONTRACT} isUnavailable()"),
    (_MOCK, "const COUNTER_CAP = 2 ** 30 - 1;", "const COUNTER_CAP = 2 ** 30;", f"{_MOCK} COUNTER_CAP"),
    (_MOCK, '405: "Method not allowed", ', "", f"{_MOCK} STANDARD_CODES"),
    (_MOCK, '?? "Unknown error"', '?? "Unknown code"', f"{_MOCK} makeResponse()'s unknown-code text"),
    (_MOCK, '"LED busy - retry later"', '"LED busy"', f"{_MOCK} LED_BUSY_DESCR"),
    (_MOCK, 'const LED_DURATION_MEMBER = "T";', 'const LED_DURATION_MEMBER = "R";', f"{_MOCK} LED_DURATION_MEMBER"),
    (_MOCK, "const DNS_LABEL_MAX = 63;", "const DNS_LABEL_MAX = 64;", f"{_MOCK} DNS_LABEL_MAX"),
    (_MOCK, "const DNS_FALLBACK_MAX = 3;", "const DNS_FALLBACK_MAX = 4;", f"{_MOCK} DNS_FALLBACK_MAX"),
    (_PRINT_LOG, "_MAX_CNT = const(0xFFFF)", "_MAX_CNT = const(0xFFFE)", f"{_CONTRACT} ERR_COUNT_CAP"),
    (_CODEGEN, '"Minute": t[4]', '"Min": t[4]', f"{_CONTRACT} GMTIME_KEYS"),
    (_API_RESPONSE, '413: "Payload too large",', '413: "Payload too large", 418: "Teapot",', f"{_MOCK} STANDARD_CODES"),
    (_DNS_CLIENT, "DNS_LABEL_MAX = const(63)", "DNS_LABEL_MAX = const(62)", f"{_MOCK} DNS_LABEL_MAX"),
    (_NTP_CLIENT, "_DNS_FALLBACK_MAX = const(3)", "_DNS_FALLBACK_MAX = const(2)", f"{_MOCK} DNS_FALLBACK_MAX"),
)


@pytest.mark.parametrize(("path", "text", "planted", "pin"), _PLANTS, ids=[f"{plant[0]}:{plant[3]}" for plant in _PLANTS])
def test_a_planted_mismatch_fails_its_pin(tmp_path: Path, path: str, text: str, planted: str, pin: str) -> None:
    for name in _READ_FILES:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_REPO_ROOT / name, tmp_path / name)
    source = (tmp_path / path).read_text(encoding="utf-8")
    assert source.count(text) == 1, f"{path} no longer holds {text!r} once - the plant would bite nothing"
    (tmp_path / path).write_text(source.replace(text, planted), encoding="utf-8")
    assert [problem for problem in _mirror_problems(tmp_path) if problem.startswith(f"{pin}:")], f"planting {planted!r} in {path} left {pin} silent"


def _spells_the_marker(text: str) -> bool:
    # The marker's word alone, or quoted inside a JSON text ('{"error":"unavailable"}'); log prose may use the word.
    return text == "unavailable" or '"unavailable"' in text or "'unavailable'" in text


def _marker_spellings(root: Path) -> "list[str]":
    # Every string literal in src/ spelling the degraded-source marker other than UNAVAILABLE's own definition.
    found: list[str] = []
    for path in sorted((root / "src").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        definition = {
            id(node.value.args[0])
            for node in tree.body
            if path.name == Path(_BASE_CLASSES).name and isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and node.value.args and ast.unparse(node.targets[0]) == "UNAVAILABLE"
        }
        found += [
            f"{path.relative_to(root)}:{node.lineno}: {node.value!r}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and _spells_the_marker(node.value) and id(node) not in definition
        ]
    return found


def test_src_spells_the_unavailable_marker_only_through_unavailable() -> None:
    assert _marker_spellings(_REPO_ROOT) == [], "build the marker from asy_base_classes.UNAVAILABLE, never a second spelling"


def test_the_marker_spelling_scan_bites(tmp_path: Path) -> None:
    shutil.copytree(_REPO_ROOT / "src", tmp_path / "src")
    (tmp_path / "src" / "asy_planted.py").write_text('def degraded() -> dict[str, str]:\n    return {"error": "unavailable"}\n', encoding="utf-8")
    assert _marker_spellings(tmp_path) == ["src/asy_planted.py:2: 'unavailable'"]


@cache
def _definitions(device: str) -> JsonDict:
    return definitions_for_toml(device_toml(device), _REPO_ROOT / "src")


def _fields(definitions: JsonDict, key: str) -> "list[JsonDict]":
    # Every action (dispatch) field `key` of any section and group: the status page's readonly PauseTime is none.
    sections = definitions["sections"]
    assert isinstance(sections, list)
    found: list[JsonDict] = []
    for section in sections:
        assert isinstance(section, dict) and isinstance(section["groups"], list)
        for group in section["groups"]:
            assert isinstance(group, dict)
            fields = group.get("fields", [])
            assert isinstance(fields, list)
            found += [field for field in fields if isinstance(field, dict) and field.get("key") == key and field.get("dispatch") is True]
    return found


def _bounds(field: JsonDict) -> "list[JsonValue]":
    # A number field as the server's schema record states it: name, type, min, max.
    return [field.get("key"), "float" if field.get("float") is True else "int", field.get("min"), field.get("max")]


def _dispatch_problems(definitions: JsonDict, root: Path) -> "list[str]":
    # The generated dispatch fields against the server's own tables, which the mock derives its rules from.
    server = _py_values(root / _WEBSERVER, "_SYSTEM_CMDS", "_PAUSE_TIME_FIELD", "_LIGHT_CMD_FIELDS")
    problems: list[str] = []
    for field in _fields(definitions, "SystemCmd"):
        options = field.get("options")
        values = sorted(str(option.get("value")) for option in options if isinstance(option, dict)) if isinstance(options, list) else []
        if values != sorted(str(word) for word in _record(server["_SYSTEM_CMDS"])):
            problems.append(f"SystemCmd options {values} != _SYSTEM_CMDS")
    pause = _record(server["_PAUSE_TIME_FIELD"])
    problems += [f"PauseTime {_bounds(field)} != _PAUSE_TIME_FIELD" for field in _fields(definitions, "PauseTime") if _bounds(field) != [pause[0], pause[1], pause[3], pause[4]]]
    led = [[record[0], record[1], record[3], record[4]] for record in map(_record, _record(server["_LIGHT_CMD_FIELDS"]))]
    for field in _fields(definitions, "LightCmdLED"):
        members = field.get("subFields")
        found = [_bounds(member) for member in members if isinstance(member, dict)] if isinstance(members, list) else []
        if found != led:
            problems.append(f"LightCmdLED sub-fields {found} != _LIGHT_CMD_FIELDS")
    return problems


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_dispatch_field_follows_the_server_tables(device: str) -> None:
    assert _dispatch_problems(_definitions(device), _REPO_ROOT) == []


def test_the_dispatch_fields_are_checked_on_some_device() -> None:
    # Not vacuous: each of the three fields appears on at least one real device.
    for key in ("SystemCmd", "PauseTime", "LightCmdLED"):
        assert any(_fields(_definitions(device), key) for device in DEVICE_NAMES), f"no device's definitions carry {key}"


@pytest.mark.parametrize(
    ("key", "member", "planted", "named"),
    [("SystemCmd", "options", [{"value": "reboot", "label": "Reboot"}], "SystemCmd options"), ("PauseTime", "max", 7200, "PauseTime"), ("LightCmdLED", "subFields", [], "LightCmdLED sub-fields")],
)
def test_the_dispatch_check_bites(key: str, member: str, planted: JsonValue, named: str) -> None:
    device = next(device for device in DEVICE_NAMES if _fields(_definitions(device), key))
    definitions = json.loads(json.dumps(_definitions(device)))
    assert isinstance(definitions, dict)
    for field in _fields(definitions, key):
        field[member] = planted
    assert [problem for problem in _dispatch_problems(definitions, _REPO_ROOT) if problem.startswith(named)]
