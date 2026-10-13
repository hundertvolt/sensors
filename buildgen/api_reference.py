"""Generates a device's REST API reference (SPECIFICATION.md Part A.8): every route `asy_webserver_service.ROUTES`
registers, with its fields from the device's website definitions, plus the four result words and the envelope's
code texts, each read from `src/` by AST (buildgen never imports it). Written per device by the generator script."""

import ast
import json
from pathlib import Path

from buildgen.definitions import generate_definitions
from buildgen.errors import BuildError, BuildInternalError
from buildgen.jsontypes import JsonDict, JsonValue
from buildgen.model import DeviceModel
from buildgen.source_ast import parse_source

_WEBSERVER = "asy_webserver_service.py"
_CONFIG_MANAGER = "asy_config_manager.py"
_API_RESPONSE = "asy_api_response.py"
_METHODS = ("GET", "PUT")
_RESULT_WORD_NAMES = ("VALID", "UNCHANGED", "INVALID", "FAILED")
_ROUTE_ROW_LEN = 3  # (method, path, handler name)
# A field's API facts (its value domain, readonly vs settable, dispatch-only) and the page's own keys: every
# definitions key is one or the other (options and subFields are reduced to their facts), so none drops unseen.
_FIELD_FACTS = frozenset({
    "key", "kind", "unit", "min", "max", "minLength", "maxLength", "byteLength", "shape", "float",
    "specialValues", "path", "format", "codes", "mask", "dispatch", "alwaysExecuted",
})
_PAGE_ONLY = frozenset({"label", "description", "onLabel", "offLabel", "defaultValue", "decimals"})
# GET /status publishes every module's error history under this key; the page also shows a slice of it
# elsewhere (the captive DNS history on Networking), so every errcount group's modules are listed here.
_ERRCOUNT_GROUP = "errcount"


def _field_facts(field: JsonDict, device: str) -> JsonDict:
    unclassified = sorted(set(field) - _FIELD_FACTS - _PAGE_ONLY - {"options", "subFields"})
    if unclassified:
        raise BuildError(
            device, f"definitions field {field.get('key')!r} carries {unclassified}, neither an API fact nor the page's own - classify each in buildgen/api_reference.py",
            rule="api.field-key-unclassified", fix="add each key to _FIELD_FACTS (an API fact) or _PAGE_ONLY (the page's own) in buildgen/api_reference.py",
        )
    facts: JsonDict = {name: value for name, value in field.items() if name in _FIELD_FACTS}
    if "options" in field:
        facts["options"] = [option["value"] for option in _items(field["options"], "options", device)]
    if "subFields" in field:
        facts["subFields"] = [_field_facts(sub, device) for sub in _items(field["subFields"], "subFields", device)]
    return facts


def _items(value: JsonValue, what: str, device: str) -> "list[JsonDict]":
    # A definitions list of objects; any other shape is a definitions generator fault, named here.
    if not (isinstance(value, list) and all(isinstance(item, dict) for item in value)):
        raise BuildInternalError(f"[{device}] the definitions' {what} is not a list of objects: {value!r}")
    return [item for item in value if isinstance(item, dict)]


def _mapping(value: JsonValue, what: str, device: str) -> JsonDict:
    if isinstance(value, dict):
        return value
    raise BuildInternalError(f"[{device}] the definitions' {what} is not an object: {value!r}")


def _module_literal(src_dir: Path, filename: str, name: str, device: str) -> object:
    # One module-level `NAME = <literal>` (annotated or not, `const()` unwrapped) of a src/ file, by AST.
    path = src_dir / filename
    try:
        tree = parse_source(path.read_text(encoding="utf-8"), str(path))
    except (OSError, SyntaxError) as e:
        raise BuildError(
            device, f"cannot read {path} for its {name}: {e}", field=name,
            rule="api.source-unreadable", fix=f"check that --src-dir holds a {path.name} that parses",
        ) from e
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == name for target in targets):
            continue
        value = node.value
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "const" and len(value.args) == 1:
            value = value.args[0]
        try:
            literal: object = ast.literal_eval(value)
        except (TypeError, ValueError) as e:  # TypeError: a container literal that cannot be built, an unhashable key
            raise BuildError(
                device, f"{path}: {name} is no longer a plain literal ({e}) - the REST reference reads it by AST", field=name,
                rule="api.source-not-literal", fix=f"write {name} in {path.name} as a plain literal (const() allowed)",
            ) from e
        return literal
    raise BuildError(
        device, f"{path} no longer defines {name} at module level - the REST reference reads it by AST", field=name,
        rule="api.source-name-missing", fix=f"define {name} at module level in {path.name}, or follow its rename in buildgen/api_reference.py",
    )


def _read_result_words(src_dir: Path, device: str) -> "list[JsonValue]":
    words: list[JsonValue] = []
    for name in _RESULT_WORD_NAMES:
        word = _module_literal(src_dir, _CONFIG_MANAGER, name, device)
        if not isinstance(word, str):
            raise BuildError(
                device, f"{src_dir / _CONFIG_MANAGER}: {name} is {word!r}, not a result word string", field=name,
                rule="api.result-word-not-string", fix=f"bind {name} in {_CONFIG_MANAGER} to its result word, a string",
            )
        words.append(word)
    return words


def _read_routes(src_dir: Path, device: str) -> "list[tuple[str, str]]":
    # ROUTES' (method, path) pairs in registration order; a row of any other shape, or a repeat, fails here.
    rows = _module_literal(src_dir, _WEBSERVER, "ROUTES", device)
    if not isinstance(rows, tuple):
        raise BuildError(
            device, f"{src_dir / _WEBSERVER}: ROUTES is a {type(rows).__name__}, not a tuple of rows", field="ROUTES",
            rule="api.routes-not-tuple", fix="write ROUTES as a tuple of (method, path, handler name) rows",
        )
    routes: list[tuple[str, str]] = []
    for row in rows:
        if not (isinstance(row, tuple) and len(row) == _ROUTE_ROW_LEN and all(isinstance(part, str) for part in row) and row[0] in _METHODS and row[1].startswith("/")):
            raise BuildError(
                device, f"{src_dir / _WEBSERVER}: ROUTES row {row!r} is not (a method of {_METHODS}, '/<path>', a handler name)", field="ROUTES",
                rule="api.routes-row-malformed", fix='write the row as ("GET" or "PUT", "/<path>", "<handler name>")',
            )
        if (row[0], row[1]) in routes:
            raise BuildError(
                device, f"{src_dir / _WEBSERVER}: ROUTES lists {row[0]} {row[1]} twice", field="ROUTES",
                rule="api.routes-duplicate", fix=f"list {row[0]} {row[1]} once in ROUTES",
            )
        routes.append((row[0], row[1]))
    return routes


def _read_standard_codes(src_dir: Path, device: str) -> JsonDict:
    codes = _module_literal(src_dir, _API_RESPONSE, "_STANDARD_CODES", device)
    if not (isinstance(codes, dict) and all(isinstance(code, int) and isinstance(text, str) for code, text in codes.items())):
        raise BuildError(
            device, f"{src_dir / _API_RESPONSE}: _STANDARD_CODES is not an {{int: str}} literal: {codes!r}", field="_STANDARD_CODES",
            rule="api.envelope-codes-malformed", fix="write _STANDARD_CODES as a literal mapping each int code to its text",
        )
    return {str(code): str(text) for code, text in sorted(codes.items())}


def _route_groups(method: str, section: "JsonDict | None", errcount_modules: "list[JsonValue]", device: str) -> "list[JsonValue]":
    # A GET answers every field but a dispatch-only one and one GET never reports (a defaultValue, H.5); a PUT
    # takes every field but a readonly one. A route no section describes (no such service) has no groups.
    if section is None:
        return []
    groups: list[JsonValue] = []
    for group in _items(section["groups"], "groups", device):
        if group.get("kind") == "errcount":
            if method == "GET" and group["key"] == _ERRCOUNT_GROUP:
                groups.append({"key": _ERRCOUNT_GROUP, "modules": errcount_modules})
            continue
        fields = _items(group["fields"], "fields", device)
        wanted = [field for field in fields if not field.get("dispatch") and "defaultValue" not in field] if method == "GET" else [field for field in fields if field["kind"] != "readonly"]
        if wanted:
            groups.append({"key": group["key"], "fields": [_field_facts(field, device) for field in wanted]})
    return groups


def api_reference_json(reference: JsonDict) -> str:
    # The one serialisation every writer and check uses: sorted keys, list order kept, no timestamp.
    return json.dumps(reference, indent=2, sort_keys=True)


def generate_api_reference(model: DeviceModel, src_dir: Path) -> JsonDict:
    # `model` validated and in construction order, as for generate_definitions(). A definitions section naming a
    # route the table does not register fails the build: the page would call an API the device lacks.
    routes = _read_routes(src_dir, model.device)
    by_route: dict[tuple[str, str], JsonDict] = {}
    errcount_groups: list[tuple[JsonValue, list[JsonDict]]] = []
    for section in _items(generate_definitions(model, src_dir)["sections"], "sections", model.device):
        for method, path in _mapping(section["rest"], "rest", model.device).items():
            route = (method.upper(), str(path))
            if route not in routes:
                raise BuildError(
                    model.device, f"definitions section {section['key']!r} names {route[0]} {route[1]}, which ROUTES in {src_dir / _WEBSERVER} does not register",
                    rule="api.route-unregistered", fix=f"register {route[0]} {route[1]} in ROUTES, or drop it from the section's rest",
                )
            by_route[route] = section
        errcount_groups += [(group["key"], _items(group["modules"], "modules", model.device)) for group in _items(section["groups"], "groups", model.device) if group.get("kind") == "errcount"]
    errcount_modules: list[JsonValue] = []
    for _key, modules in sorted(errcount_groups, key=lambda key_modules: key_modules[0] != _ERRCOUNT_GROUP):
        for module in modules:
            if module["key"] not in errcount_modules:
                errcount_modules.append(module["key"])
    return {
        "device": model.device,
        "envelopeCodes": _read_standard_codes(src_dir, model.device),
        "resultWords": _read_result_words(src_dir, model.device),
        "routes": [{"method": method, "path": path, "groups": _route_groups(method, by_route.get((method, path)), errcount_modules, model.device)} for method, path in routes],
    }
