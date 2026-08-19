"""Integration tier (owner decision 10, "middle
integration tests... might point us to oversights in the regular unit tests"): builds the real
src/sensortask_wozi.py object graph against the real digital_twin buses (not tests/machine.py's
fakes - Step 3's own simulator, real-time Timers/randomized-but-plausible sensor values) and drives
real REST traffic against it over a real socket (owner decision 2: "full HTTP, real sockets, real
server", same as the real system) - not app.dispatch_request() bypass, which
tests/test_sensortask_wozi.py's own existing suite already covers in full depth against
tests/machine.py, and is deliberately not duplicated here.

Sits between tests/test_digital_twin_*.py's own per-chip unit tests (Step 3, unaware
sensortask_wozi.py even exists) and digital_twin/run_wozi_integration.py's full end-to-end
soak/manual entry point (Step 5's own dedicated, separately-invoked script - see that module's own
docstring for why it can't live here): every test in this file starts only the specific tasks it
actually needs, always keeping an explicit reference to each one it starts and cancelling every one
of them again in its own `finally` before the next test runs - never
sensortask_wozi.main()/start_and_check_tasks() (see the watchdog test's own comment below for the
real, hard-won reason why: MicroPython's globals() does not preserve test-definition order, so
nothing here can assume "the last test written" is "the last test run", and an orphaned background
task from one test is free to corrupt every test after it, in whatever order that turns out to be).
This file's whole point is quick, everyday regression coverage of the twin+webserver wiring, not a
soak.

Reaches digital_twin's own machine/network fakes via the same per-file sys.path.insert(0,
"digital_twin") trick tests/test_digital_twin_launch.py already uses - confirmed safe to combine
with scripts/test.sh's own default "src:tests:frozen_modules:.frozen" MICROPYPATH (the insert-at-
position-0 ordering deterministically wins over the later "tests" segment within this one process;
digital_twin/README.md's own "never together" warning is about the separate *production*
MICROPYPATH invocation never carrying a "tests" segment at all, not about this per-file pattern -
see digital_twin/README.md for the full reasoning). No fram_storage fake swap
(unlike tests/test_sensortask_wozi.py's own asy_spi_driver._SPI = FakeMB85RS64V) - the twin's own
machine.SPI already wires a real FramChip automatically (asy_spi_driver.py wraps machine.SPI
unchanged, per this twin's own "bus construction stays as-is" convention), and every test here
runs FRAM in-memory-only (machine.configure_fram_state_path() is never called - its own module-level
default is already None), matching every other automated test file's own ephemeral-state convention
rather than digital_twin/run_wozi_integration.py's deliberately persistent default.
"""

import asyncio
import os
import sys

sys.path.insert(0, "ext")  # same convention as test_sensortask_wozi.py's own comment - reaches the
# real, vendored ext/microdot.py that sensortask_wozi.py transitively imports.
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import _http_client  # noqa: E402

import sensortask_wozi  # noqa: E402

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(coro)


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


# ---------------------------------------------------------------------------
# Per-test config-file isolation - same _tmp_cfg_dir()/_sweep_stale_tmp_dirs() shape every other
# test file uses (see tests/test_sensortask_wozi.py's own comment for the full root-cause story on
# why the sweep is required, not just the fresh-directory-name counter alone).
# ---------------------------------------------------------------------------

_TMP_DIR = "tests/_tmp"
_next_dir = 0
_next_port = 19100  # a fixed, non-privileged test-only range - never the production 8080 default,
# never the real 0.0.0.0:80 - a fresh port per test avoids any TIME_WAIT reuse flakiness rather
# than relying on one shared port across every test_* function in this one process.


def _sweep_stale_tmp_dirs(prefix: str) -> None:
    try:
        entries = os.listdir(_TMP_DIR)
    except OSError:
        return
    for entry in entries:
        if not entry.startswith(prefix):
            continue
        dir_path = _TMP_DIR + "/" + entry
        try:
            for filename in os.listdir(dir_path):
                try:
                    os.remove(dir_path + "/" + filename)
                except OSError:
                    pass
            os.rmdir(dir_path)
        except OSError:
            pass


_sweep_stale_tmp_dirs("dtsi_")


def _tmp_cfg_dir() -> str:
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    _next_dir += 1
    path = _TMP_DIR + "/dtsi_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass
    return path + "/"


def _next_test_port() -> int:
    global _next_port
    _next_port += 1
    return _next_port


async def _boot(port: int) -> None:
    await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)


async def _start_webserver() -> "asyncio.Task[None]":
    assert sensortask_wozi.webserver is not None
    task = sensortask_wozi.webserver.get_task_starters()[0]()
    await asyncio.sleep(0.1)  # let _run() actually reach start_server()/bind - same bound
    # test_asy_webserver_service.py's own F.8 test uses for the identical real-socket startup race.
    return task


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# Boot against the real twin buses.
# ---------------------------------------------------------------------------


def test_build_system_boots_against_the_real_twin_buses_without_exception() -> None:
    # Confirms every FRAM chunk (see SPECIFICATION.md Part A.7 for the five-chunk order) still allocates cleanly
    # against the twin's own real FramChip, not just tests/machine.py's fake - a real gap nothing
    # before this file ever exercised (Step 1/2's own tests/test_sensortask_wozi.py never touches
    # digital_twin at all).
    run(_boot(_next_test_port()))
    for name in (
        "conn",
        "ntp",
        "i2c0",
        "i2c1",
        "spi0",
        "fram",
        "sysfunct",
        "sgp_reader",
        "bmp_reader",
        "scd_reader",
        "pixel",
        "notify_service",
        "webserver",
        "watchdog",
    ):
        assert getattr(sensortask_wozi, name) is not None, f"sensortask_wozi.{name} was not constructed"


# ---------------------------------------------------------------------------
# Every REST endpoint (+ the Step 4 static site) reachable over a real HTTP round trip.
# ---------------------------------------------------------------------------


def test_every_get_endpoint_is_reachable_over_real_http_and_shaped_correctly() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/measurements")
            assert res.status_code == 200
            measurements = res.json()
            assert set(measurements.keys()) == {"SCD30", "BMP3XX", "SGP40"}
            # Regression coverage for a real bug found via a real user report against the real
            # assembled system (not caught here before, since this only ever checked top-level keys):
            # every real driver's own get_dict_data() already returns a {name: {...}} self-wrapped
            # shape, and _get_measurements() used to index that by name again, producing
            # {"SCD30": {"SCD30": {...}}} for every sensor - see src/asy_webserver_service.py's own
            # _get_measurements()/_get_sensors() comments for the full account.
            for name, fields in measurements.items():
                assert name not in fields, f"{name}'s own value is still self-wrapped: {fields!r}"
                assert fields, f"{name} returned no fields at all"

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/sensors")
            assert res.status_code == 200
            sensors = res.json()
            assert set(sensors.keys()) == {"SCD30", "BMP3XX", "SGP40"}
            for name, fields in sensors.items():
                assert name not in fields, f"{name}'s own value is still self-wrapped: {fields!r}"
                assert fields, f"{name} returned no fields at all"

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/networking")
            assert res.status_code == 200
            # Regression coverage for a real bug this file's own testing found and
            # src/asy_webserver_service.py's _flatten_cfg_values() now fixes: every /networking
            # field is sourced from a nested-shaped module (conn/ntp), so this used to come back {}.
            assert res.json() == {
                "SSID": "",
                "PW": "********",
                "Country": "DE",
                "Hostname": "SensorNode",
                "LedWifiOn": True,
                "NTP_Host": "pool.ntp.org",
                "NTP_Offset_S": 0,
                "NTP_Interv_H": 12,
            }

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/system")
            assert res.status_code == 200
            # DebugLevel is sourced from sysfunct (flat) - GMTOffset/DSTOffset from ntp (nested),
            # same fix as /networking above.
            assert res.json() == {"DebugLevel": 0, "GMTOffset": 3600, "DSTOffset": 3600}

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/notification")
            assert res.status_code == 200
            # notify_service.get_dict_cfg() is nested-shaped too - same fix as /networking above.
            body = res.json()
            assert body["WarnCO2"] == 1600
            assert body["WarnVOC"] == 350
            assert body["WarnHum"] == 65.0

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/status")
            assert res.status_code == 200
            assert set(res.json().keys()) == {"networking", "system", "notification", "sensors", "errcount"}
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=10.0)


def test_static_site_stub_is_served_over_real_http() -> None:
    # See SPECIFICATION.md Part A.9 - the frozen_html website stub, served by WebserverService's own
    # generic "/" route (registered last, after every API route above - a real API route must never
    # be shadowed by the wildcard, per tests/test_asy_webserver_service.py's own Section G).
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/")
            assert res.status_code == 200
            assert len(res.body) > 0
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=10.0)


def test_put_round_trips_through_a_real_twin_backed_driver_over_real_http() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "PUT", "/notification", {"WarnCO2": 1800})
            assert res.status_code == 200
            assert res.json()["result"] == {"WarnCO2": "Valid"}
            assert sensortask_wozi.notify_service is not None
            # await directly, not via run() - already inside scenario()'s own event loop
            # (run_timed()'s asyncio.run()); a nested asyncio.run() call here segfaulted the real
            # interpreter instead of raising a clean error (found via this exact bug, the hard way).
            assert await sensortask_wozi.notify_service.cfgmgr.get_dict(["WarnCO2"]) == {"WarnCO2": 1800}
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=10.0)


def test_sensors_put_round_trips_a_real_scd30_field_over_real_http() -> None:
    # Regression test from baseline verification: this whole file
    # never exercised PUT /sensors at all before (only PUT /notification, above) - the exact real,
    # real-HTTP path that first surfaced SCD30_Reader's missing get_cfg_schema() (a real 500) when
    # this session ran the assembled system live against the twin. SCD30 specifically, since it's
    # the one sensors=-registered module that's a plain SensorReader (no local cfgmgr - params live
    # on the sensor itself), unlike SGP40/BMP3XX which are SensorReaderConfig subclasses and would
    # never have caught this particular gap.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "PUT", "/sensors", {"SCD30": {"MeasInt": 4}})
            assert res.status_code == 200
            assert res.json()["result"] == {"SCD30": {"MeasInt": "Valid"}}
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=10.0)


def test_a_real_bus_fault_degrades_to_a_clean_response_not_a_crash() -> None:
    # A concrete example of the "might point us to oversights" value owner decision 10 called out:
    # this exercises a real twin-injected I2C fault flowing all the way through the real driver ->
    # real webserver -> a real HTTP response, something no existing tests/machine.py-backed test can
    # do (tests/machine.py has no comparable fault-injection surface wired to sensortask_wozi.py).
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.i2c1 is not None
        import errno

        # asy_i2c_driver.I2C wraps the real machine.I2C at its own private _i2c attribute (confirmed
        # directly against src/asy_i2c_driver.py's __init__) - the twin's own chip-fake registry
        # (.devices) lives on that wrapped object, not on the wrapper itself. Only None before
        # init() runs (__init__ calls it itself, unconditionally) - always set by now, just not
        # statically provable from the type alone.
        assert sensortask_wozi.i2c1._i2c is not None
        sgp40_chip = sensortask_wozi.i2c1._i2c.devices[0x59]
        # A handful is enough - this test makes exactly one HTTP request, and the real Unix-port
        # heap is small enough that a needlessly large `times` (each queued as its own list entry)
        # measurably adds to this file's own cumulative memory pressure across its several real
        # build_system() calls.
        sgp40_chip.fault.inject_fault("writeto", OSError(errno.EIO, "test-injected"), times=5)
        task = await _start_webserver()
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
# Watchdog escalation - a short, real, fully-supervised run (owner decision 7: automated assertion
# *and* manually observable - the manual side lives in digital_twin/run_wozi_integration.py, this
# is the automated side).
#
# Deliberately does NOT drive this through sensortask_wozi.main()/start_and_check_tasks(): a real
# regression found while building this file - MicroPython's globals() does not preserve
# definition order (confirmed directly: this file's own test_* functions ran in a different order
# than written), so "the last test in the file" is not actually "the last test to run", and
# start_and_check_tasks() keeps its own started tasks in a local variable with no way for a caller
# to reach and cancel them - main_task.cancel() only ever cancelled the *outer* wrapper coroutine,
# leaving every real task it had started (webserver server, sensor timers, WDT countdown, ...)
# running in the background for the rest of this process. Across the other tests' own repeated
# build_system() calls (each allocating a fresh 8KB FramChip, fresh ConfigManagers, ...), those
# orphaned tasks' lingering references were enough to starve the Unix-port heap - a real
# MemoryError once, and a hard interpreter segfault once (with a `run()`-inside-`run()` bug of this
# file's own stacked on top - see git history for the full story). Fix: start exactly the same real
# task starters sensortask_wozi.main() itself would, but keep every one of them in a list this test
# owns and explicitly cancels in `finally` - the same controlled pattern _start_webserver() already
# uses above, just extended to every task instead of one. Runs its own small watchdog-feed loop
# rather than start_and_check_tasks()'s own (already covered by tests/test_system_service.py) -
# this test's own job is only "does the real, twin-backed object graph's real concurrent tasks ever
# block the event loop long enough to starve a feed loop running alongside them", which needs the
# real tasks running for real but not that specific feed implementation.
# ---------------------------------------------------------------------------


async def _feed_watchdog_periodically(watchdog: "Any") -> None:
    while True:
        watchdog.feed()
        await asyncio.sleep(1.0)


def test_watchdog_is_never_starved_while_every_real_task_runs_concurrently() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.watchdog is not None and sensortask_wozi.sysfunct is not None
        await sensortask_wozi.sysfunct.start_timers(sensortask_wozi._collect_timer_starters())
        # Each starter already returns its own asyncio.Task (system_service.py's own _start_task()
        # calls them exactly this way - `return starter()`, no extra create_task() wrapping).
        tasks = [starter() for starter in sensortask_wozi._collect_task_starters()]
        tasks.append(asyncio.get_event_loop().create_task(_feed_watchdog_periodically(sensortask_wozi.watchdog)))
        try:
            await asyncio.sleep(9.0)  # just over the hardcoded 8000ms WDT timeout - long enough that
            # a real, unintended stall (not just this test's own feed loop existing) is what keeps
            # the count at 0, not merely "not enough wall-clock time has passed yet".
            assert sensortask_wozi.watchdog.would_have_triggered_count == 0
        finally:
            for task in tasks:
                await _cancel(task)

    run_timed(scenario(), timeout_s=15.0)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
