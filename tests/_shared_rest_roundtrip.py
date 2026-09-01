"""Backend-agnostic REST-round-trip assertion helpers shared by mock (test_sensortask_wozi.py) and
digital-twin (test_digital_twin_sensortask_integration.py) tests, and by the flash/bench live-system
hardware tests (tests_hardware/) - see HARDWARE_TEST_PLAN.md §2.2/§4 for why exactly these two checks
(and no others) were pulled out: the only genuine near-duplicate assertion *shapes* found scanning
mock vs. twin, not a general parametrization of every REST test. Flat module (not a `_shared/`
subpackage) to match this directory's own existing convention for shared-but-nonpublic test modules
(_fram_chip_fake.py, _coverage_runner.py) and avoid relying on MicroPython Unix-port package-import
support. Pure dict/assert logic only, no I/O - portable unmodified to tests_hardware/'s CPython/pytest
runner too, since neither function touches anything MicroPython- or CPython-specific."""

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
