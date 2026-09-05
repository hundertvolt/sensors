"""Backend-agnostic REST-round-trip assertion helpers shared by mock (test_sensortask_wozi.py) and
digital-twin (test_digital_twin_sensortask_integration.py) tests, and by the flash/bench live-system
hardware tests (tests_hardware/) - see HARDWARE_TEST_PLAN.md §2.2/§4 for why exactly these two checks
(and no others) were pulled out: the only genuine near-duplicate assertion *shapes* found scanning
mock vs. twin, not a general parametrization of every REST test. Flat module (not a `_shared/`
subpackage) to match this directory's own existing convention for shared-but-nonpublic test modules
(_fram_chip_fake.py, _coverage_runner.py) and avoid relying on MicroPython Unix-port package-import
support. Pure dict/assert logic plus drain_json_response_body() below (plain iteration only, no
real I/O) - portable unmodified to tests_hardware/'s CPython/pytest runner too, since nothing here
touches anything MicroPython- or CPython-specific."""

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any


def assert_named_modules_constructed(module: "Any", names: "tuple[str, ...]") -> None:
    """Shared shape for a "build_system() wired up every long-lived object" check: each backend
    passes its own module namespace (always the real `sensortask_wozi` module - mock in-process,
    twin against real twin buses) and its own applicable name tuple. The two callers' name tuples
    differ by one entry (`webserver` - see call sites for why), which is why this takes the tuple as
    a parameter rather than hardcoding one shared list."""
    for name in names:
        assert hasattr(module, name), f"{module.__name__}.{name} was not constructed"
        assert getattr(module, name) is not None


def assert_sensor_payload_not_self_wrapped(payload: "dict[str, Any]", expected_names: "set[str]") -> None:
    """Shared shape for GET /measurements and GET /sensors: every real driver's own
    get_dict_data()/get_dict_cfg() already returns a {name: {...}} self-wrapped shape, and
    src/asy_webserver_service.py's _get_measurements()/_get_sensors() used to index that by name
    again, producing {"SCD30": {"SCD30": {...}}} for every sensor (see its own comments there for
    the full account of the real bug this regression-guards). Checking only top-level keys doesn't
    catch that - this checks each sensor's own value isn't re-wrapped and isn't empty."""
    assert set(payload.keys()) == expected_names
    for name, fields in payload.items():
        assert name not in fields, f"{name}'s own value is still self-wrapped: {fields!r}"
        assert fields, f"{name} returned no fields at all"


def drain_json_response_body(body: "Any") -> bytes:
    """GET /status now streams its JSON body from a plain list of already-json.dumps()-encoded
    fragments (asy_webserver_service.py's _get_status()/_build_status_pieces() - one small
    json.dumps() per already-independent source instead of one big buffer, see BACKLOG.md's Microdot
    generator-streaming finding) instead of returning a plain dict for Response.__init__ to
    json.dumps() up front. Deliberately not an `async def ... yield` "async generator": confirmed
    directly against the pinned MicroPython interpreter that syntax produces a broken runtime object
    (no __aiter__/__anext__, and driving it past a real await via plain next() segfaults - see
    SPECIFICATION.md Part F.1) - the real body is therefore a plain, synchronous list_iterator, no
    different from any other iterable this function already has to handle. res.body is a plain
    iterator for that one route (still plain bytes for every dict/list-returning route, handled here
    too so call sites don't need to branch) - drain it back into one bytes object the way a real
    client naturally would by reading the connection until Microdot's own HTTP/1.0 close (confirmed
    no keep-alive handling anywhere in ext/microdot.py), so tests can keep asserting on
    json.loads(...) of one complete body exactly as before."""
    if isinstance(body, bytes):
        return body
    chunks = []
    for chunk in body:
        chunks.append(chunk.encode() if isinstance(chunk, str) else chunk)
    return b"".join(chunks)
