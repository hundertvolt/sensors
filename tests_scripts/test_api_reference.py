"""The generated per-device REST reference (buildgen.api_reference, SPECIFICATION.md A.8): byte-identical over two
generations, every ROUTES entry and no other route, every `@web` field under its route, the source's result words
and envelope codes; and a build that cannot read its route table or meets an unregistered route fails loudly."""

import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen import api_reference
from buildgen.api_reference import api_reference_json, generate_api_reference
from buildgen.errors import BuildError, BuildInternalError
from buildgen.generate import generate_device
from buildgen.graph import build_construction_order
from buildgen.model import DeviceModel
from buildgen.validate import build_model
from buildgen.web_tag import SELF_GROUP, parse_web_tags

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
_WEBSERVER = "asy_webserver_service.py"
# The tagged services every device has, never [[instance]] entries (buildgen/definitions.py scans the same three).
_MANDATORY_TAGGED = ("asy_wifi_service.py", "asy_ntp_client.py", "asy_system_service.py")
# The legacy firmware's API routes (each device module under legacy/firmware/modules/): "none of them needs to
# stay. The reference for us is the new API." (owner, 2026-09-26)
_LEGACY_ROUTES = (
    ("GET", "/net/status"), ("GET", "/net/config"), ("PUT", "/net/cmd"),
    ("GET", "/time/status"), ("GET", "/time/config"), ("PUT", "/time/cmd"),
    ("GET", "/sensors/status"), ("GET", "/sensors/config"), ("PUT", "/sensors/cmd"),
    ("GET", "/led/status"), ("GET", "/led/config"), ("PUT", "/led/cmd"),
    ("GET", "/system/status"), ("PUT", "/system/cmd"),
)
_GOOD_FIELD = {"key": "F", "kind": "number"}  # a definitions field the malformed-shape cases extend
# Two generations in fresh interpreters under different hash seeds: a set's order differs between them.
_GENERATE = (
    "import json, sys; from pathlib import Path; sys.path.insert(0, sys.argv[1])\n"
    "from buildgen.api_reference import api_reference_json, generate_api_reference\n"
    "from buildgen.graph import build_construction_order\nfrom buildgen.validate import build_model\n"
    "root = Path(sys.argv[1]); out = {}\n"
    "for device in sys.argv[2:]:\n"
    "    model = build_model(root / 'devices' / f'{device}.toml', root / 'src'); build_construction_order(model)\n"
    "    out[device] = api_reference_json(generate_api_reference(model, root / 'src'))\n"
    "print(json.dumps(out))\n"
)


def _assert_rule(error: BuildError, rule: str) -> None:
    # Every build error names the rule it broke and carries its fix in the message (SPECIFICATION.md L.5).
    assert error.rule == rule, error.rule
    assert error.fix and str(error).endswith(f" - fix: {error.fix}"), str(error)


def _expected_fields(model: DeviceModel) -> "tuple[set[tuple[str, str, str, str]], set[tuple[str, str, str, str]], set[Path]]":
    # (method, path, group, key) of every @web tag the device's sources carry, present and absent, and the files read:
    # GET reports a tag unless dispatch or defaultValue (H.5), PUT takes it unless readonly; maintenance is <name>_<field>.
    sources: list[tuple[Path, str, str | None]] = [(_SRC / name, name, None) for name in _MANDATORY_TAGGED]
    sources += [(spec.driver_info.source_path, spec.label, spec.resolved_name) for spec in model.instances.values() if spec.driver_info is not None]
    expected: set[tuple[str, str, str, str]] = set()
    absent: set[tuple[str, str, str, str]] = set()
    for path, label, resolved in sources:
        for tag in parse_web_tags(path, model.device, label):
            if tag.hidden is not None:
                continue  # off every route: test_a_hidden_field_is_on_no_route checks it
            group, key = tag.submit_group, tag.field_name
            if tag.section == "status" or tag.submit_group == SELF_GROUP:
                assert resolved is not None, f"{path}: {tag.field_name} is keyed by its instance, but {path.name} has none"
                group, key = ("sensors", f"{resolved}_{key}") if tag.section == "status" else (resolved, key)
            for method, applies in (("GET", not tag.dispatch and tag.default_value is None), ("PUT", tag.kind != "readonly")):
                (expected if applies else absent).add((method, f"/{tag.section}", group, key))
    return expected, absent, {path for path, _label, _resolved in sources}


def _generated_function(device: str, name: str) -> ast.AsyncFunctionDef:
    tree = ast.parse(generate_device(device_toml(device), _SRC, _REPO_ROOT / "ext").module_source)
    return next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == name)


def _groups(route: "dict[str, object]") -> "list[dict[str, object]]":
    groups = route["groups"]
    assert isinstance(groups, list)
    return groups


def _model(device: str, src_dir: Path = _SRC) -> DeviceModel:
    model = build_model(device_toml(device), src_dir)
    build_construction_order(model)
    return model


def _route(reference: "dict[str, object]", method: str, path: str) -> "dict[str, object]":
    return next(route for route in _routes(reference) if (route["method"], route["path"]) == (method, path))


def _routes(reference: "dict[str, object]") -> "list[dict[str, object]]":
    routes = reference["routes"]
    assert isinstance(routes, list)
    return routes


def _src_literal(filename: str, name: str) -> object:
    # A module-level literal of a src/ file, read here on its own rather than through the module under test.
    for node in ast.parse((_SRC / filename).read_text(encoding="utf-8")).body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name and node.value is not None:
            return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"src/{filename} defines no {name}")


def _src_routes() -> "list[tuple[str, str]]":
    rows = _src_literal(_WEBSERVER, "ROUTES")
    assert isinstance(rows, tuple)
    return [(method, path) for method, path, _handler in rows]


def _src_with(tmp_path: Path, filename: str, old: str, new: str) -> Path:
    # A copy of src/ with one edit to one file; the edit must apply, or the test would pass vacuously.
    src_dir = tmp_path / "src"
    shutil.copytree(_SRC, src_dir)
    text = (src_dir / filename).read_text(encoding="utf-8")
    assert old in text, f"src/{filename} no longer holds {old!r}"
    (src_dir / filename).write_text(text.replace(old, new, 1), encoding="utf-8")
    return src_dir


@pytest.fixture(scope="module")
def generations() -> "tuple[dict[str, str], dict[str, str]]":
    runs = []
    for seed in ("1", "2"):
        done = subprocess.run([sys.executable, "-I", "-c", _GENERATE, str(_REPO_ROOT), *DEVICE_NAMES], env={**os.environ, "PYTHONHASHSEED": seed}, capture_output=True, text=True, check=False)
        assert done.returncode == 0, done.stderr
        runs.append(json.loads(done.stdout))
    return runs[0], runs[1]


@pytest.fixture(scope="module")
def references(generations: "tuple[dict[str, str], dict[str, str]]") -> "dict[str, dict[str, object]]":
    return {device: json.loads(text) for device, text in generations[0].items()}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_two_generations_are_byte_identical(generations: "tuple[dict[str, str], dict[str, str]]", device: str) -> None:
    first, second = generations
    assert first[device] == second[device]
    assert first[device] == api_reference_json(generate_api_reference(_model(device), _SRC)), "the in-process generation differs from a fresh interpreter's"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_routes_are_exactly_the_route_table_and_no_legacy_path(references: "dict[str, dict[str, object]]", device: str) -> None:
    listed = [(route["method"], route["path"]) for route in _routes(references[device])]
    assert listed == _src_routes()
    assert not set(listed) & set(_LEGACY_ROUTES)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_web_field_appears_under_its_route_and_nowhere_it_is_not_carried(references: "dict[str, dict[str, object]]", device: str) -> None:
    expected, absent, _files = _expected_fields(_model(device))
    present: set[tuple[str, str, str, str]] = set()
    for route in _routes(references[device]):
        for group in _groups(route):
            fields = group.get("fields", [])
            assert isinstance(fields, list)
            present |= {(str(route["method"]), str(route["path"]), str(group["key"]), str(field["key"])) for field in fields}
    assert expected, f"{device}: no @web field found - the scan read nothing"
    assert not expected - present, f"{device}: @web fields missing from their route: {sorted(expected - present)}"
    assert not absent & present, f"{device}: @web fields listed where the route never carries them: {sorted(absent & present)}"


def test_every_tagged_source_is_one_some_device_reads() -> None:
    # A newly page-tagged src/ file outside every device's sources would leave its fields unchecked above; a hidden
    # tag is on no route, so it needs no reader.
    read: set[Path] = set()
    for device in DEVICE_NAMES:
        read |= _expected_fields(_model(device))[2]
    tagged = {path for path in _SRC.glob("*.py") if any(tag.hidden is None for tag in parse_web_tags(path, "scan", path.stem))}
    assert tagged <= read, f"tagged sources no device reads: {sorted(p.name for p in tagged - read)}"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_status_route_lists_every_error_history_module(references: "dict[str, dict[str, object]]", device: str) -> None:
    # The captive DNS history the Networking page shows is read from GET /status's errcount (js/render.js).
    errcount = next(group for group in _groups(_route(references[device], "GET", "/status")) if group["key"] == "errcount")
    modules = errcount["modules"]
    assert isinstance(modules, list)
    assert {"DNSSRV", "WEBSERVER", "SYSTEM", "CFGMGR_SYSTEM"} <= set(modules)
    assert len(modules) == len(set(modules))
    assert not any(group["key"] == "dnsErrors" for route in _routes(references[device]) for group in _groups(route))


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_result_words_and_envelope_codes_are_the_sources(references: "dict[str, dict[str, object]]", device: str) -> None:
    codes = _src_literal("asy_api_response.py", "_STANDARD_CODES")
    assert isinstance(codes, dict)
    assert references[device]["resultWords"] == ["Valid", "Unchanged", "Invalid", "Failed"]
    assert references[device]["envelopeCodes"] == {str(code): text for code, text in codes.items()}
    assert references[device]["device"] == device


def test_a_route_the_definitions_name_but_the_table_lacks_fails_the_build(tmp_path: Path) -> None:
    src_dir = _src_with(tmp_path, _WEBSERVER, '    ("PUT", "/sensors", "_put_sensors"),\n', "")
    with pytest.raises(BuildError, match=r"PUT /sensors") as caught:
        generate_api_reference(_model(DEVICE_NAMES[0], src_dir), src_dir)
    _assert_rule(caught.value, "api.route-unregistered")


@pytest.mark.parametrize(
    ("old", "new", "reason", "rule"),
    [
        ("ROUTES = (", "ROUTES_GONE = (", r"no longer defines ROUTES", "api.source-name-missing"),
        ("ROUTES = (", "ROUTES = () + (", r"ROUTES is no longer a plain literal", "api.source-not-literal"),
        ("ROUTES = (", 'ROUTES = "rows"\n_ROUTES_ROWS = (', r"ROUTES is a str, not a tuple of rows", "api.routes-not-tuple"),
        ('    ("GET", "/measurements", "_get_measurements"),', '    ("POST", "/measurements", "_get_measurements"),', r"ROUTES row \('POST'", "api.routes-row-malformed"),
        ('    ("GET", "/measurements", "_get_measurements"),', '    ("GET", "measurements", "_get_measurements"),', r"ROUTES row \('GET', 'measurements'", "api.routes-row-malformed"),
        ('    ("GET", "/measurements", "_get_measurements"),', '    ("GET", "/measurements"),', r"ROUTES row \('GET', '/measurements'\)", "api.routes-row-malformed"),
        ('    ("GET", "/sensors", "_get_sensors"),', '    ("GET", "/measurements", "_get_sensors"),', r"ROUTES lists GET /measurements twice", "api.routes-duplicate"),
    ],
    ids=["missing", "not-a-literal", "not-a-tuple", "unknown-method", "relative-path", "short-row", "duplicate"],
)
def test_an_unreadable_route_table_fails_the_build(tmp_path: Path, old: str, new: str, reason: str, rule: str) -> None:
    src_dir = _src_with(tmp_path, _WEBSERVER, old, new)
    with pytest.raises(BuildError, match=reason) as caught:
        generate_api_reference(_model(DEVICE_NAMES[0], src_dir), src_dir)
    _assert_rule(caught.value, rule)


@pytest.mark.parametrize(
    ("filename", "old", "new", "name", "rule"),
    [
        ("asy_config_manager.py", 'FAILED: "Final" = "Failed"', 'FAILED: "Final" = 4', "FAILED", "api.result-word-not-string"),
        ("asy_config_manager.py", 'VALID: "Final" = "Valid"', 'VALIDATED: "Final" = "Valid"', "VALID", "api.source-name-missing"),
        ("asy_api_response.py", "_STANDARD_CODES: dict[int, str] = {", "_STANDARD_CODES: dict[int, str] = {999: 999, ", "_STANDARD_CODES", "api.envelope-codes-malformed"),
        ("asy_api_response.py", "_STANDARD_CODES: dict[int, str] = {", '_STANDARD_CODES: dict[int, str] = {[1]: "x", ', "_STANDARD_CODES is no longer a plain literal", "api.source-not-literal"),
        ("asy_api_response.py", "_STANDARD_CODES: dict[int, str] = {", "_STANDARD_CODES: dict[int, str] = {)", "cannot read .* for its _STANDARD_CODES", "api.source-unreadable"),
    ],
    ids=["word-not-a-string", "word-missing", "code-text-not-a-string", "unhashable-key", "syntax-error"],
)
def test_an_unreadable_result_word_or_code_fails_the_build(tmp_path: Path, filename: str, old: str, new: str, name: str, rule: str) -> None:
    src_dir = _src_with(tmp_path, filename, old, new)
    with pytest.raises(BuildError, match=name) as caught:
        generate_api_reference(_model(DEVICE_NAMES[0], src_dir), src_dir)
    _assert_rule(caught.value, rule)


@pytest.mark.parametrize(
    ("definitions", "what"),
    [
        ({"sections": {}}, "sections"),
        ({"sections": [{"key": "sensors", "rest": ["/sensors"], "groups": []}]}, "rest"),
        ({"sections": [{"key": "sensors", "rest": {"get": "/sensors"}, "groups": [{"key": "G", "fields": [{**_GOOD_FIELD, "options": "x"}]}]}]}, "options"),
        ({"sections": [{"key": "sensors", "rest": {"get": "/sensors"}, "groups": [{"key": "G", "fields": [{**_GOOD_FIELD, "subFields": [1]}]}]}]}, "subFields"),
        ({"sections": [{"key": "status", "rest": {"get": "/status"}, "groups": [{"key": "errcount", "kind": "errcount", "modules": None}]}]}, "modules"),
    ],
    ids=["sections", "rest", "options", "sub-fields", "modules"],
)
def test_a_malformed_definitions_shape_fails_the_build(monkeypatch: pytest.MonkeyPatch, definitions: "dict[str, object]", what: str) -> None:
    # The definitions generator's own output is checked as it is read, never trusted into a wrong reference.
    monkeypatch.setattr(api_reference, "generate_definitions", lambda _model, _src_dir: definitions)
    with pytest.raises(BuildInternalError, match=f"the definitions' {what} is not"):
        generate_api_reference(_model(DEVICE_NAMES[0]), _SRC)


@pytest.mark.parametrize("where", ["field", "sub-field"])
def test_a_field_key_the_reference_does_not_classify_fails_the_build(monkeypatch: pytest.MonkeyPatch, where: str) -> None:
    # Every definitions key is an API fact or the page's own: a new one is classified, never dropped unseen.
    field: dict[str, object] = {**_GOOD_FIELD, "pattern": "^x$"}
    if where == "sub-field":
        field = {"key": "C", "kind": "composite", "subFields": [field]}
    definitions = {"sections": [{"key": "sensors", "rest": {"put": "/sensors"}, "groups": [{"key": "G", "fields": [field]}]}]}
    monkeypatch.setattr(api_reference, "generate_definitions", lambda _model, _src_dir: definitions)
    with pytest.raises(BuildError, match=r"'pattern'.*neither an API fact nor the page's own") as caught:
        generate_api_reference(_model(DEVICE_NAMES[0]), _SRC)
    _assert_rule(caught.value, "api.field-key-unclassified")


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_a_string_shape_the_server_checks_is_an_api_fact(references: "dict[str, dict[str, object]]", device: str) -> None:
    # asy_wifi_service.py refuses a Hostname that is not a host label, so its shape is part of the value domain.
    identity = next(group for group in _groups(_route(references[device], "PUT", "/networking")) if group["key"] == "identity")
    fields = identity["fields"]
    assert isinstance(fields, list)
    assert {field["key"]: field.get("shape") for field in fields}["Hostname"] == "hostLabel"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_status_route_lists_the_system_keys_the_device_publishes(references: "dict[str, dict[str, object]]", device: str) -> None:
    # Guard: GET /status's system group names exactly the keys the generated _system_status() returns.
    system = next(group for group in _groups(_route(references[device], "GET", "/status")) if group["key"] == "system")
    fields = system["fields"]
    assert isinstance(fields, list)
    returned = next(node.value for node in ast.walk(_generated_function(device, "_system_status")) if isinstance(node, ast.Return))
    assert isinstance(returned, ast.Dict)
    assert [field["key"] for field in fields] == [key.value for key in returned.keys if isinstance(key, ast.Constant)]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_system_route_offers_the_words_the_server_accepts(references: "dict[str, dict[str, object]]", device: str) -> None:
    # Guard: PUT /system's SystemCmd options are asy_webserver_service.py's _SYSTEM_CMDS, in its order.
    command = next(group for group in _groups(_route(references[device], "PUT", "/system")) if group["key"] == "command")
    fields = command["fields"]
    assert isinstance(fields, list)
    (field,) = fields
    served = next(node.value for node in ast.parse((_SRC / _WEBSERVER).read_text(encoding="utf-8")).body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_SYSTEM_CMDS" for t in node.targets))
    assert isinstance(served, ast.Call)
    assert field["options"] == list(ast.literal_eval(served.args[0]))


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_a_hidden_field_is_on_no_route(references: "dict[str, dict[str, object]]", device: str) -> None:
    # An instance's hidden= fields appear in none of its own groups, nor as its maintenance rows.
    model = _model(device)
    shown: list[str] = []
    for spec in model.instances.values():
        if spec.driver_info is None:
            continue
        hidden = {tag.field_name for tag in parse_web_tags(spec.driver_info.source_path, device, spec.label) if tag.hidden is not None}
        for route in _routes(references[device]):
            for group in _groups(route):
                fields = group.get("fields", [])
                assert isinstance(fields, list)
                keys = {field["key"] for field in fields}
                own = keys & hidden if group["key"] == spec.resolved_name else set()
                shown += sorted(f"{route['method']} {route['path']} {group['key']}.{key}" for key in own | (keys & {f"{spec.resolved_name}_{name}" for name in hidden}))
    assert not shown, shown
