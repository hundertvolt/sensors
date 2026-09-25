"""Shared scenario library: digital-twin-tier construction/wiring/REST across all 6 real devices
(SPECIFICATION.md Part L.4), fast, no real wall-clock waits. Not a test file - the export is
register_for_device(); SPECIFICATION.md Part E.2.1 has the per-device split and why it exists."""

import asyncio
import json
import sys

sys.path.insert(0, "ext")  # same convention as tests/_sensortask_scenarios.py's own comment
sys.path.insert(0, "digital_twin")  # see tests/test_digital_twin_sgp40.py's own comment for why

import _http_client
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

# Before any poll object is registered: the Unix port's pollfds growth corrupts non-fd entries
# already in it, a segfault rather than a failure (digital_twin/README.md "Known gaps").
prewarm_poll_set()

# Must run before AsyUDPSocket is constructed (DNSServer, inside AsyConnTime.__init__, built for
# every device below) - same reasoning as tests/test_digital_twin_sensortask_integration.py's own
# identical call.
patch_asy_udp_socket_for_unix_port()

import machine  # noqa: E402
from _shared_rest_roundtrip import assert_named_modules_constructed, assert_sensor_payload_not_self_wrapped  # noqa: E402
from _tmp_scratch import TmpScratch  # noqa: E402

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


# Every real device (devices/*.toml) - buildgen generates each one's own module + wiring plan into
# build/generated_src/ before scripts/test.sh ever runs this file (scripts/_generate_sensortask_modules.py).
_DEVICES = ("wozi", "dev", "arzi", "klkizi", "grkizi", "schlafzi")


def _wiring_plan(device: str) -> "dict[str, Any]":
    with open(f"build/generated_src/sensortask_{device}_wiring_plan.json") as f:
        plan: dict[str, Any] = json.load(f)
    return plan


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# Per-test config-file isolation via tests/_tmp_scratch.py - own scratch key and port range per device,
# distinct from test_digital_twin_sensortask_integration.py's 19100+/"dtsi", which keeps its own wozi-only
# heavy tests, and from every other twin-tier file's claimed range (19300+, 19400+, 19700+).
_PORT_BASE_BY_DEVICE = {device: 19500 + 10 * i for i, device in enumerate(_DEVICES)}

_scratch: "TmpScratch | None" = None
_next_port = 0


def _tmp_cfg_dir() -> str:
    assert _scratch is not None, "register_for_device() must run before any scenario calls _tmp_cfg_dir()"
    return _scratch.dir()


def _next_test_port() -> int:
    global _next_port
    assert _next_port != 0, "register_for_device() must run before any scenario calls _next_test_port()"
    _next_port += 1
    return _next_port


_PARAM_SCENARIOS: "list[tuple[str, Callable[[str], None]]]" = []


def _register_param(name: str) -> "Callable[[Callable[[str], None]], Callable[[str], None]]":
    def deco(fn: "Callable[[str], None]") -> "Callable[[str], None]":
        _PARAM_SCENARIOS.append((name, fn))
        return fn

    return deco


async def _boot_device(port: int, device: str) -> "Any":
    machine.configure_wiring(_wiring_plan(device))
    module = __import__(f"sensortask_{device}")
    await module.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
    return module


def _present_optional_instances(module: "Any", device: str) -> "tuple[str, ...]":
    # Derived from the wiring plan's pre-construction "instances" list, not the built module's attributes -
    # see tests/_sensortask_scenarios.py's identical helper for why: a construction bug that silently drops
    # a declared driver reads back as though the device never had it, which getattr cannot tell apart.
    plan_instances = set(_wiring_plan(device)["instances"])
    all_names = ("scd30", "sgp40", "bmp3xx", "isl29125", "neopixel", "notification")
    present = tuple(name for name in all_names if name in plan_instances)
    for name in all_names:
        if name in present:
            assert getattr(module, name, None) is not None, f"{name} is in devices/{device}.toml's own instances but build_system() never constructed it"
        else:
            # The reverse direction matters too - see tests/_sensortask_scenarios.py's own identical
            # check for why (a wiring plan that silently under-reports a driver must not let this
            # check quietly agree with it and stop testing a real, live object).
            assert getattr(module, name, None) is None, f"{name} is NOT in devices/{device}.toml's own instances, but build_system() constructed it anyway"
    return present


@_register_param("build_system_boots_against_the_real_twin_buses_without_exception")
def _scenario_boots_against_real_twin_buses(device: str) -> None:
    # Confirms every FRAM chunk (SPECIFICATION.md Part A.7) allocates cleanly against the twin's
    # real FramChip, not just tests/machine.py's fake. Shared shape with the mock's own equivalent
    # test (tests/_shared_rest_roundtrip.py); adds "webserver" since this file exercises real HTTP.
    async def scenario() -> None:
        module = await _boot_device(_next_test_port(), device)
        mandatory = ("conn", "ntp", "i2c0", "i2c1", "spi0", "fram", "sysfunct", "neopixel", "notification", "webserver", "watchdog")
        assert_named_modules_constructed(module, mandatory + _present_optional_instances(module, device))

    run_timed(scenario(), timeout_s=10.0)


@_register_param("get_measurements_and_sensors_are_reachable_and_shaped_correctly")
def _scenario_measurements_and_sensors_shape(device: str) -> None:
    # Shared shape with the mock's own equivalent check (tests/_shared_rest_roundtrip.py) -
    # regression guard for the {name: {name: {...}}} self-wrapping bug (see
    # asy_webserver_service.py's comments), over a real socket against the real twin.
    port = _next_test_port()

    async def scenario() -> None:
        module = await _boot_device(port, device)
        task = module.webserver.get_task_starters()[0]()
        # See test_digital_twin_sensortask_integration.py's own _start_webserver() comment: WP1
        # made webserver.pr real-FRAM-backed on every real device, so _run() now awaits a real
        # self.pr.setup() before start_server()/bind - measured at ~400ms here too.
        await asyncio.sleep(1.0)
        try:
            expected = {name.upper() for name in _present_optional_instances(module, device) if name in ("scd30", "sgp40", "bmp3xx", "isl29125")}
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/measurements")
            assert res.status_code == 200
            assert_sensor_payload_not_self_wrapped(res.json(), expected)

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/sensors")
            assert res.status_code == 200
            assert_sensor_payload_not_self_wrapped(res.json(), expected)
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=10.0)


@_register_param("a_real_bus_fault_degrades_to_a_clean_response_not_a_crash")
def _scenario_bus_fault_degrades(device: str) -> None:
    # A concrete example of the "might point us to oversights" value owner decision 10 called out: a real
    # twin-injected I2C fault flowing through the real driver, the real webserver and a real HTTP response,
    # which no tests/machine.py-backed test can do, that fake having no comparable fault surface.
    port = _next_test_port()

    async def scenario() -> None:
        module = await _boot_device(port, device)
        import errno

        # SGP40 is fixed-address (0x59) on every real device (buildgen.twin_wiring.FIXED_ADDRESSES),
        # but which bus it's actually wired to varies by device (wozi/dev already differ from each
        # other) - resolved here from the device's own real wiring plan, never assumed to be i2c1.
        plan = _wiring_plan(device)
        sgp40_bus_name = next(bus_name for bus_name, attachments in plan["buses"].items() if any(a["driver"] == "sgp40" for a in attachments))
        bus = getattr(module, sgp40_bus_name)
        # asy_i2c_driver.I2C wraps the real machine.I2C at its private _i2c attribute, and the twin's chip-
        # fake registry lives on that wrapped object, not the wrapper. Only None before init() runs, which
        # __init__ calls unconditionally - set by now, just not statically provable from the type.
        assert bus._i2c is not None
        sgp40_chip = bus._i2c.devices[0x59]
        # A handful is enough: this test makes exactly one HTTP request, and the Unix-port heap is small
        # enough that a needlessly large `times`, each entry queued separately, measurably adds to this
        # file's cumulative memory pressure across its several real build_system() calls.
        sgp40_chip.fault.inject_fault("writeto", OSError(errno.EIO, "test-injected"), times=5)
        task = module.webserver.get_task_starters()[0]()
        # See test_digital_twin_sensortask_integration.py's own _start_webserver() comment: WP1
        # made webserver.pr real-FRAM-backed on every real device, so _run() now awaits a real
        # self.pr.setup() before start_server()/bind - measured at ~400ms here too.
        await asyncio.sleep(1.0)
        try:
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/measurements")
            assert res.status_code == 200  # never a 500 - a sensor read failure degrades to
            # whatever get_dict_data() already returns for a not-yet-successfully-read sensor, not
            # an unhandled exception reaching the HTTP layer.
            assert "SGP40" in res.json()
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=10.0)


# ---------------------------------------------------------------------------
# Registration: one test_<scenario> per scenario, for whichever single device the caller names -
# microtest.py discovers every callable in globals() named test_*, the only parametrization mechanism
# available here (Part E.1).
#
# fn is bound as a default-argument value rather than read from the loop variable, or every generated test
# would share the same last-iteration fn.
# ---------------------------------------------------------------------------


def register_for_device(device: str) -> "dict[str, Callable[[], None]]":
    global _scratch, _next_port
    assert device in _DEVICES, f"{device!r} is not one of this module's own real devices {_DEVICES!r}"
    _scratch = TmpScratch(f"dtcs_{device}")
    _next_port = _PORT_BASE_BY_DEVICE[device]

    tests: dict[str, Callable[[], None]] = {}
    for scenario_name, scenario_fn in _PARAM_SCENARIOS:

        def _make_test(fn: "Callable[[str], None]" = scenario_fn) -> "Callable[[], None]":
            def test() -> None:
                fn(device)

            return test

        tests[f"test_{scenario_name}"] = _make_test()
    return tests
