"""Backend-agnostic REST-round-trip assertion helpers shared by mock and digital-twin tests
(and tests_hardware/'s CPython runner). Flat module, not a `_shared/` subpackage, matching this
directory's existing convention for shared-but-nonpublic test modules."""

import sys

# Scoped to this one import: left on the path, digital_twin/'s machine/network fakes could shadow tests/' own.
sys.path.insert(0, "digital_twin")
from _strict_json import check_strict_json

sys.path.pop(0)

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Iterable
    from types import ModuleType
    from typing import Any


def assert_named_modules_constructed(module: "ModuleType", names: "tuple[str, ...]") -> None:
    """Shared "build_system() wired up every long-lived object" check. Takes the name tuple as a
    parameter since the two callers' tuples differ by one entry (`webserver`)."""
    for name in names:
        assert hasattr(module, name), f"{module.__name__}.{name} was not constructed"
        assert getattr(module, name) is not None


def assert_sensor_payload_not_self_wrapped(payload: "dict[str, Any]", expected_names: "set[str]") -> None:
    """Regression guard for GET /measurements and /sensors: checks each sensor's own value isn't
    re-wrapped (was {"SCD30": {"SCD30": {...}}}, see asy_webserver_service.py) and isn't empty."""
    assert set(payload.keys()) == expected_names
    for name, fields in payload.items():
        assert name not in fields, f"{name}'s own value is still self-wrapped: {fields!r}"
        assert fields, f"{name} returned no fields at all"


def drain_json_response_body(body: "bytes | Iterable[str | bytes]") -> bytes:
    """Drains a response body - plain bytes, or the synchronous list_iterator some streamed
    routes use (see SPECIFICATION.md Part F.1) - into one bytes object, checked as strict JSON
    first: the interpreter's own json.loads() would accept a streamed body's separator slip."""
    drained = body if isinstance(body, bytes) else b"".join(chunk.encode() if isinstance(chunk, str) else chunk for chunk in body)
    check_strict_json(drained)
    return drained
