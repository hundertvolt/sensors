"""Guard for SPECIFICATION.md Part I.6: the largest body any device's own schema can legitimately
produce must still fit under `max_content_length`. Nothing else checks this, and every new driver
grows it - dev's `/sensors` is 338 B larger than wozi's purely for carrying one more sensor."""

# Derived, never hardcoded, on both sides: the cap is read out of src/ and the schema out of the
# real buildgen model, so a cap change and a schema change are each caught by the same assertion.
# The hardware tier's W3 checks the same property on silicon but cannot run in CI.

import ast
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from _devices import DEVICE_NAMES

from buildgen.definitions import generate_definitions
from buildgen.validate import build_model

if TYPE_CHECKING:
    from collections.abc import Mapping

# The widest JSON number a double round-trips to, so no legitimate numeric field can exceed it.
# Deliberately an upper bound rather than the field's own min/max: a client may send any number of
# decimals within range, and the schema does not bound that.
_MAX_JSON_NUMBER = len("-1.2345678901234567e+308")

# Only /sensors nests its body per group ({"SCD30": {...}}); asy_webserver_service.py's own comment
# calls the rest "flat settings endpoints", which take {field: value} directly.
_NESTED_ROUTES = frozenset({"/sensors"})

# The measured maximum per device, pinned so that growth is deliberate and visible rather than
# silent. A new driver or a widened string bound SHOULD fail this - update it and read the margin.
_EXPECTED_LARGEST = {
    "arzi": 1312,
    "dev": 1312,
    "grkizi": 1312,
    "klkizi": 1312,
    "schlafzi": 1312,
    "wozi": 1312,
}


def _cap_from_src(repo_root: Path) -> int:
    """`WebserverService.__init__`'s own `max_content_length` default, read out of the source."""
    tree = ast.parse((repo_root / "src" / "asy_webserver_service.py").read_text())
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "WebserverService"):
        for fn in (n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"):
            args = fn.args
            for name, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
                if name.arg == "max_content_length" and isinstance(default, ast.Constant):
                    assert isinstance(default.value, int), f"max_content_length's default is {default.value!r}, not an int"
                    return default.value
            offset = len(args.args) - len(args.defaults)
            for index, default in enumerate(args.defaults):
                if args.args[offset + index].arg == "max_content_length" and isinstance(default, ast.Constant):
                    assert isinstance(default.value, int), f"max_content_length's default is {default.value!r}, not an int"
                    return default.value
    raise AssertionError("max_content_length's default is no longer readable from WebserverService.__init__")


def _field_bound(field: "Mapping[str, Any]") -> int:
    kind = field.get("kind")
    if kind == "string":
        return int(field.get("maxLength", 0)) + 2  # the two quotes
    if kind == "toggle":
        return len("false")
    if kind == "enum":
        options = field["options"]
        assert isinstance(options, list)
        return max(len(json.dumps(option["value"])) for option in options)
    if kind == "number":
        return _MAX_JSON_NUMBER
    if kind == "composite":
        sub = field["subFields"]
        assert isinstance(sub, list)
        return sum(len(json.dumps(s["key"])) + 1 + _field_bound(s) + 1 for s in sub) + 1
    raise AssertionError(f"unhandled writable field kind {kind!r} - teach this guard about it rather than skipping it")


def _largest_put_body(section: "Mapping[str, Any]") -> int:
    """Bytes of the largest body this section's PUT route can legitimately be sent."""
    groups = section.get("groups", [])
    assert isinstance(groups, list)
    per_group: dict[str, int] = {}
    for group in groups:
        cost = sum(
            len(json.dumps(f["key"])) + 1 + _field_bound(f) + 1
            for f in group.get("fields", [])
            if f.get("kind") not in (None, "readonly")
        )
        if cost:
            per_group[group["key"]] = cost
    if not per_group:
        return 0
    rest = section.get("rest", {})
    assert isinstance(rest, dict)
    if rest.get("put") in _NESTED_ROUTES:
        return sum(len(json.dumps(k)) + 1 + (v + 1) + 1 for k, v in per_group.items()) + 2
    return sum(per_group.values()) + 2


def _put_sections(repo_root: Path, device: str) -> "list[tuple[str, int]]":
    model = build_model(repo_root / "devices" / f"{device}.toml", repo_root / "src")
    definitions = generate_definitions(model, repo_root / "src")
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
    assert largest == _EXPECTED_LARGEST[device], (
        f"{device}'s largest schema-permitted PUT body moved from {_EXPECTED_LARGEST[device]} to {largest} B "
        f"against a {cap} B cap ({cap / largest:.2f}x headroom). Update _EXPECTED_LARGEST deliberately, "
        f"and check SPECIFICATION.md Part I.6's quoted figure with it."
    )


def test_every_device_is_pinned(repo_root: Path) -> None:
    # A seventh device would otherwise be generated, built and shipped while this guard silently
    # never looked at it - the same failure _devices.py itself exists to prevent.
    assert sorted(_EXPECTED_LARGEST) == sorted(DEVICE_NAMES), f"_EXPECTED_LARGEST does not cover exactly the real device set: {sorted(_EXPECTED_LARGEST)} vs {sorted(DEVICE_NAMES)}"


def test_an_oversized_field_is_actually_caught(repo_root: Path) -> None:
    # Proves the derivation bites rather than merely agreeing with today's schema: the guard above
    # passes trivially if _largest_put_body() ever stops finding fields at all.
    cap = _cap_from_src(repo_root)
    section = {"rest": {"put": "/networking"}, "groups": [{"key": "identity", "fields": [{"key": "Huge", "kind": "string", "maxLength": cap}]}]}
    assert _largest_put_body(section) > cap, "a field alone wider than the cap was not reported as exceeding it"
    empty = {"rest": {"put": "/networking"}, "groups": [{"key": "identity", "fields": [{"key": "Reading", "kind": "readonly"}]}]}
    assert _largest_put_body(empty) == 0, "a section with no writable field must contribute nothing, not an empty-body constant"
