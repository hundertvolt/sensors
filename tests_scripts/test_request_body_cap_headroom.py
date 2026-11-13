"""Guard for SPECIFICATION.md Part I.6: the largest body any device's own schema can legitimately
produce must still fit under `max_content_length`. Nothing else checks this, and every new driver
grows it: one more sensor makes its device's `/sensors` body larger by that sensor's own settings."""

# Derived, never hardcoded, on both sides: the cap is read out of src/ and the schema out of the
# real buildgen model, so a cap change and a schema change are each caught by the same assertion.
# The hardware tier's W3 checks the same property on silicon but cannot run in CI.

import ast
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import tomllib
from _devices import DEVICE_NAMES, device_toml

from buildgen.definitions import definitions_for_toml

if TYPE_CHECKING:
    from collections.abc import Mapping

    from buildgen.jsontypes import JsonDict, JsonValue

# The widest JSON number a double round-trips to, so no legitimate numeric field can exceed it.
# Deliberately an upper bound rather than the field's own min/max: a client may send any number of
# decimals within range, and the schema does not bound that.
_MAX_JSON_NUMBER = len("-1.2345678901234567e+308")

# Only /sensors nests its body per group ({"SCD30": {...}}); asy_webserver_service.py's own comment
# calls the rest "flat settings endpoints", which take {field: value} directly.
_NESTED_ROUTES = frozenset({"/sensors"})

# The measured maximum per declared driver set (each device's [[instance]] drivers, sorted), pinned so
# growth shows as a failure to read rather than passing silently. A new driver or a widened string bound SHOULD fail this.
_EXPECTED_LARGEST = {
    ("fram", "neopixel", "notification", "scd30", "sgp40"): 678,
    ("bmp3xx", "fram", "neopixel", "notification", "scd30", "sgp40"): 743,
    ("bmp3xx", "fram", "isl29125", "neopixel", "notification", "scd30", "sgp40", "uart_link", "uart_link"): 1080,
}


def _drivers(device: str) -> "tuple[str, ...]":
    instances = tomllib.loads(device_toml(device).read_text(encoding="utf-8")).get("instance", [])
    return tuple(sorted(str(i["driver"]) for i in instances))


def _cap_from_src(repo_root: Path) -> int:
    # `ServingLimits`' shipped `max_content_length`: `_DEFAULT_MAX_CONTENT_LENGTH = const(<int>)`, read out of the source.
    tree = ast.parse((repo_root / "src" / "asy_webserver_service.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_DEFAULT_MAX_CONTENT_LENGTH" for t in node.targets):
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "const" and len(value.args) == 1:
                value = value.args[0]
            assert isinstance(value, ast.Constant) and isinstance(value.value, int), f"_DEFAULT_MAX_CONTENT_LENGTH is {ast.unparse(node.value)}, not an int literal"
            return value.value
    raise AssertionError("_DEFAULT_MAX_CONTENT_LENGTH is no longer readable from src/asy_webserver_service.py")


def _dicts(value: "JsonValue") -> "list[JsonDict]":
    # A definitions list whose every entry is an object, as the schema requires.
    assert isinstance(value, list), value
    assert all(isinstance(item, dict) for item in value), value
    return [item for item in value if isinstance(item, dict)]


def _field_bound(field: "Mapping[str, JsonValue]") -> int:
    kind = field.get("kind")
    if kind == "string":
        max_length = field.get("maxLength", 0)
        assert isinstance(max_length, int), max_length
        return max_length + 2  # the two quotes
    if kind == "toggle":
        return len("false")
    if kind == "enum":
        return max(len(json.dumps(option["value"])) for option in _dicts(field["options"]))
    if kind == "number":
        return _MAX_JSON_NUMBER
    if kind == "composite":
        return sum(len(json.dumps(s["key"])) + 1 + _field_bound(s) + 1 for s in _dicts(field["subFields"])) + 1
    raise AssertionError(f"unhandled writable field kind {kind!r} - teach this guard about it rather than skipping it")


def _largest_put_body(section: "Mapping[str, JsonValue]") -> int:
    # Bytes of the largest body this section's PUT route can legitimately be sent.
    per_group: dict[str, int] = {}
    for group in _dicts(section.get("groups", [])):
        cost = sum(
            len(json.dumps(f["key"])) + 1 + _field_bound(f) + 1
            for f in _dicts(group.get("fields", []))
            if f.get("kind") not in (None, "readonly")
        )
        if cost:
            per_group[str(group["key"])] = cost
    if not per_group:
        return 0
    rest = section.get("rest", {})
    assert isinstance(rest, dict)
    if rest.get("put") in _NESTED_ROUTES:
        return sum(len(json.dumps(k)) + 1 + (v + 1) + 1 for k, v in per_group.items()) + 2
    return sum(per_group.values()) + 2


def _put_sections(repo_root: Path, device: str) -> "list[tuple[str, int]]":
    definitions = json.loads(json.dumps(definitions_for_toml(device_toml(device), repo_root / "src")))
    sections = definitions["sections"]
    assert isinstance(sections, list)
    return [(s["rest"]["put"], _largest_put_body(s)) for s in sections if "put" in s.get("rest", {}) and _largest_put_body(s)]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_no_route_can_be_sent_a_legitimate_body_the_cap_would_reject(repo_root: Path, device: str) -> None:
    # The requirement itself. Lowering a cap only ever risks refusing something real, so this is
    # the direction that matters - and it is checked per ROUTE, since only the largest one binds.
    cap = _cap_from_src(repo_root)
    offenders = [(route, size) for route, size in _put_sections(repo_root, device) if size > cap]
    assert not offenders, (
        f"{device}: {len(offenders)} PUT route(s) can be sent a schema-legitimate body larger than "
        f"max_content_length={cap}, so a real config push would be answered 413: {offenders}. "
        f"Part I.6's premise has moved - re-derive the cap, do not widen this test."
    )


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_largest_legitimate_body_is_the_pinned_one(repo_root: Path, device: str) -> None:
    # Growth is the real hazard here, and it is silent: every added driver or widened string bound
    # moves this number a little, and only the last one would ever cross the cap. Pinned so each
    # step is deliberate, the same way the persistence-write guard pins its own allowlists.
    largest = max(size for _route, size in _put_sections(repo_root, device))
    cap = _cap_from_src(repo_root)
    pinned = _EXPECTED_LARGEST.get(_drivers(device))
    assert largest == pinned, (
        f"{device}'s largest schema-permitted PUT body moved from {pinned} to {largest} B "
        f"against a {cap} B cap ({cap / largest:.2f}x headroom). Update _EXPECTED_LARGEST deliberately, "
        f"and check SPECIFICATION.md Part I.6's quoted figure with it."
    )


def test_every_device_is_pinned() -> None:
    # A seventh device's driver set would otherwise be generated, built and shipped while this guard
    # silently never looked at it - the same failure _devices.py itself exists to prevent.
    declared = {_drivers(d) for d in DEVICE_NAMES}
    assert set(_EXPECTED_LARGEST) == declared, f"_EXPECTED_LARGEST does not cover exactly the real devices' driver sets: {sorted(_EXPECTED_LARGEST)} vs {sorted(declared)}"


def test_an_oversized_field_is_actually_caught(repo_root: Path) -> None:
    # Proves the derivation bites rather than merely agreeing with today's schema: the guard above
    # passes trivially if _largest_put_body() ever stops finding fields at all.
    cap = _cap_from_src(repo_root)
    section: JsonDict = {"rest": {"put": "/networking"}, "groups": [{"key": "identity", "fields": [{"key": "Huge", "kind": "string", "maxLength": cap}]}]}
    assert _largest_put_body(section) > cap, "a field alone wider than the cap was not reported as exceeding it"
    empty: JsonDict = {"rest": {"put": "/networking"}, "groups": [{"key": "identity", "fields": [{"key": "Reading", "kind": "readonly"}]}]}
    assert _largest_put_body(empty) == 0, "a section with no writable field must contribute nothing, not an empty-body constant"
