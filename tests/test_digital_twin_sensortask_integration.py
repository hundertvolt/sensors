"""Middle integration tier: builds the real sensortask_wozi object graph against the real digital_twin buses and drives real REST traffic over a real socket, but only ever starts the specific tasks each test needs - never the full start_and_check_tasks() supervisor, with one deliberate exception (the task-supervisor-restart section below, whose whole point is that real supervisor loop). See digital_twin/README.md's "Swapping the twin in" section for the full account, including the sys.path.insert(0, "digital_twin") mechanism and a real bug this tier already found."""

import asyncio
import gc
import os
import sys

sys.path.insert(0, "ext")  # same convention as test_sensortask_wozi.py's own comment - reaches the
# real, vendored ext/microdot.py that sensortask_wozi.py transitively imports.
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import _http_client  # noqa: E402

# digital_twin's own fake machine module - configure_fram_state_path()/flush_fram(), used only by
# this file's own reboot-survival section below.
import machine  # noqa: E402

import sensortask_wozi  # noqa: E402
from asy_scd30_driver import SCD30  # noqa: E402  # used only by this file's own reboot-survival section below

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
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


async def _wait_until(predicate: "Callable[[], bool]", timeout_s: float, interval_s: float = 0.25) -> bool:
    # Bounded polling helper for the sections below that drive a real background task through a
    # real multi-second state transition (mode switches, supervisor check cycles) rather than
    # guessing a single fixed sleep duration.
    elapsed = 0.0
    while elapsed < timeout_s:
        if predicate():
            return True
        await asyncio.sleep(interval_s)
        elapsed += interval_s
    return predicate()


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


def test_put_pause_time_round_trips_and_counts_down_over_real_http() -> None:
    # The special-case endpoint pairing this restores: PUT /notification (the settings/command
    # endpoint) sets the override countdown, GET /status (the live/polling endpoint) reports its
    # current value - PauseTime is deliberately excluded from GET /notification's flat settings (see
    # tests/test_asy_webserver_service.py's own test_notification_get_is_flat_settings_only_no_live_fields),
    # so it stays in the same polling/non-polling split every other live field already follows. This
    # exercises the real auto_led_override() background task actually decrementing the value over
    # real wall-clock time, not just the value being stored.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.notify_service is not None
        tasks = [starter() for starter in sensortask_wozi.notify_service.get_task_starters()]
        tasks.append(await _start_webserver())
        try:
            res = await _http_client.fetch("127.0.0.1", port, "PUT", "/notification", {"PauseTime": 3})
            assert res.status_code == 200
            assert res.json()["result"] == {"PauseTime": "Valid"}

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/notification")
            assert "PauseTime" not in res.json()  # live value, never a flat setting

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/status")
            first = res.json()["notification"]["PauseTime"]
            assert first > 0

            last = first
            reached_zero = False
            for _ in range(20):  # bounded poll, well past the real ~1s-per-tick auto_led_override() loop
                await asyncio.sleep(0.5)
                res = await _http_client.fetch("127.0.0.1", port, "GET", "/status")
                current = res.json()["notification"]["PauseTime"]
                assert current <= last  # never increases - a real, monotonic countdown
                last = current
                if current == 0:
                    reached_zero = True
                    break
            assert reached_zero, "PauseTime never reached 0 - the real auto_led_override() task isn't decrementing it"
        finally:
            for task in tasks:
                await _cancel(task)

    run_timed(scenario(), timeout_s=15.0)


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


# ---------------------------------------------------------------------------
# Task-supervisor restart, end-to-end (BACKLOG.md "Whole-system integration test scope") - a real
# task drawn from the REAL, full _collect_task_starters() list (build_system()'s own real object
# graph, not a hand-built/synthetic task list) actually dying and being rediscovered/restarted by
# SystemService.start_and_check_tasks()'s own real supervisor loop, via the real get_task_starters()
# indirection - not a fake of the supervisor itself. The one test in this file that starts the real
# full task list through the real supervisor rather than a hand-picked subset (see this file's own
# module docstring).
# ---------------------------------------------------------------------------


def test_start_and_check_tasks_restarts_a_real_dead_task_from_the_real_full_task_list() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.sysfunct is not None and sensortask_wozi.bmp_reader is not None
        sysfunct = sensortask_wozi.sysfunct
        task_starters = sensortask_wozi._collect_task_starters()  # the REAL, full list - every
        # constructed module's own get_task_starters(), exactly what main() itself would use.

        started: dict[int, list[Any]] = {}  # values are asyncio.Task[Any] | None - real _start_task()'s own return type
        from system_service import SystemService

        real_start_task = SystemService._start_task

        async def _tracking_start_task(self: "Any", starter: "Any", n: "int") -> "Any":
            # Observes the real supervisor's own real task-(re)start calls without changing its
            # behavior at all - the same non-invasive class-method-wrap convention
            # test_sensortask_wozi.py's own FRAM-chunk-order test already uses.
            task = await real_start_task(self, starter, n)
            started.setdefault(n, []).append(task)
            return task

        SystemService._start_task = _tracking_start_task  # type: ignore[method-assign]
        supervisor_task = asyncio.get_event_loop().create_task(sysfunct.start_and_check_tasks(task_starters))
        try:
            # bmp_reader.start_asy_trigger's own task (_base_trigger()) is just a real event-wait
            # loop with no I/O and no Timer armed in this test (start_timers() was never called) -
            # a real, side-effect-free task to kill and watch get restarted. The real restart logic
            # itself (start_and_check_tasks()) never inspects which task died or why, only
            # task.done(), so this pick is representative of any real task in the list.
            target_idx = task_starters.index(sensortask_wozi.bmp_reader.start_asy_trigger)
            assert await _wait_until(lambda: target_idx in started, timeout_s=5.0), (
                "the real task was never started by the real supervisor at all"
            )
            assert len(started[target_idx]) == 1
            first_task = started[target_idx][0]
            assert first_task is not None and not first_task.done()

            first_task.cancel()  # a real task genuinely ending - the same observable state
            # (task.done() == True) a real crash would leave behind; start_and_check_tasks() only
            # ever inspects .done(), never *why* a task ended.
            assert await _wait_until(lambda: len(started[target_idx]) == 2, timeout_s=6.0), (
                "start_and_check_tasks() never rediscovered and restarted the real dead task"
            )
            second_task = started[target_idx][1]
            assert second_task is not None
            assert second_task is not first_task
            assert not second_task.done()
        finally:
            SystemService._start_task = real_start_task  # type: ignore[method-assign]
            await _cancel(supervisor_task)  # only cancels the outer wrapper (see this file's own
            # watchdog-section comment above) - every real started task is cancelled individually
            # below too.
            for tasks in started.values():
                for task in tasks:
                    if task is not None:
                        await _cancel(task)
            # Defensive: the real, unmodified wlan_connect task (started as part of the real full
            # list above) can independently reach real hotspot activation and start its own real
            # DNSServer task within this test's own window - not cancelled by the loop above since
            # it's spawned internally by AsyConnTime, not through _start_task(). Left running, it
            # would hold real UDP port 53 into the next section's own test.
            if sensortask_wozi.conn is not None and sensortask_wozi.conn.dns_server_task is not None:
                await _cancel(sensortask_wozi.conn.dns_server_task)
            # This test starts the REAL full task list (every registered task, twice for the one
            # that gets restarted) - a known real failure mode on this file's own shared per-process
            # heap otherwise (see the watchdog section's own comment above: orphaned task references
            # from one test starved a later test's build_system() with a real MemoryError before an
            # explicit collect() here was added).
            gc.collect()

    run_timed(scenario(), timeout_s=20.0)


# ---------------------------------------------------------------------------
# WiFi hotspot/DNS/LED chain, end-to-end (BACKLOG.md "Whole-system integration test scope") - a real
# STA connect failure driving AsyConnTime through a real STA -> hotspot mode transition, starting a
# real DNSServer task, with the real WiFi-status LED (conn.set_ext_led(pixel), build_system()'s own
# construction step 13) actually driven by the real state machine along the way.
# ---------------------------------------------------------------------------


def test_wifi_sta_failure_falls_back_to_hotspot_and_drives_the_real_dns_server_and_status_led() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.conn is not None and sensortask_wozi.pixel is not None
        conn = sensortask_wozi.conn
        pixel = sensortask_wozi.pixel

        # A real configured SSID (not the "SSID==''" unconfigured shortcut) so this exercises a
        # genuine scripted STA connect failure through the real state machine, not just "never
        # configured".
        persisted, _results = await conn.cfgmgr.write_config({"SSID": "TestNet"}, conn.get_cfg_schema())
        assert persisted

        import network  # digital_twin's own fake - see this file's own sys.path setup above

        conn.wlan.script_connect_outcomes([network.STAT_NO_AP_FOUND])

        pixel_task = pixel.start_asy_neopixel_led_overl()  # the one real pixel task that turns
        # conn's own on()/off()/toggle() LED calls into real committed NeoPixel frames.
        wifi_task = conn.start_asy_wlan_connect()
        try:
            await asyncio.sleep(0.2)  # let wlan_connect()'s own synchronous prefix
            # (_reset_wlan_connect_state(), which unconditionally zeroes connection_failures) run
            # first - setting the field before the task got a chance to start would just be
            # immediately overwritten once it did.
            # Fast-forwards the real conn_fail_to_hotspot=5 streak (sensortask_wozi.py's own real
            # construction call) to "one real scripted failure away from hotspot fallback" - the
            # same direct-attribute test-seam convention test_sensortask_wozi.py's own
            # test_webserver_networking_put_ntp_fields_forces_a_resync() already uses
            # (`sensortask_wozi.ntp.ntp_retries = 3`), not a fake of
            # _register_sta_connection_failure() itself. Waiting out 5 real scripted-failure cycles
            # (each with its own real wifi_refresh_sec sleep) would exercise the identical real
            # transition, just far slower.
            conn.connection_failures = 4
            started = await _wait_until(lambda: conn.dns_server_task is not None, timeout_s=25.0)
            assert started, "real hotspot activation never started the real DNSServer task"
            assert not conn.dns_server_task.done()  # type: ignore[union-attr]  # started == True above
            # The real WiFi-status LED wiring didn't just exist - it actually drove real
            # hardware-facing calls during the transition (poll-time toggles, the on-failure
            # _led_off()), landing as real committed frames on the real (twin) NeoPixel.
            assert conn.led is pixel
            assert len(pixel.pixel.writes) > 0, "the real status LED never actually wrote a frame"
        finally:
            await _cancel(wifi_task)
            await _cancel(pixel_task)
            if conn.dns_server_task is not None:
                await _cancel(conn.dns_server_task)
            gc.collect()  # see the task-supervisor-restart section's own comment above - this test
            # starts several real background tasks (wifi, pixel, hotspot DNS) too.

    run_timed(scenario(), timeout_s=35.0)


# ---------------------------------------------------------------------------
# SGP40 VOC-backup reboot survival, end-to-end (BACKLOG.md "Whole-system integration test scope") -
# a real FRAM write through the real sgp_reader/fram construction order from build_system(), a
# simulated reboot via digital_twin's own FramChip state-file persistence (digital_twin/machine.py's
# configure_fram_state_path()/flush_fram() - the twin's real reboot-survival mechanism, not a
# hand-rolled substitute), then a real restore against a brand-new build_system() object graph.
# ---------------------------------------------------------------------------


def test_sgp40_voc_backup_survives_a_simulated_reboot_through_the_real_fram_chunk() -> None:
    async def scenario() -> None:
        cfg_path = _tmp_cfg_dir()
        state_path = cfg_path + "fram_state.json"
        machine.configure_fram_state_path(state_path)
        try:
            # --- Boot 1: real construction, real FRAM chunk 3 (SPECIFICATION.md Part A.7) write
            # through the real chain. ---
            await sensortask_wozi.build_system(cfg_path=cfg_path, web_host="127.0.0.1", web_port=_next_test_port())
            assert sensortask_wozi.sgp_reader is not None and sensortask_wozi.scd_reader is not None
            sgp1 = sensortask_wozi.sgp_reader
            # sgp_comp_callback (sensortask_wozi.py's own real construction wiring) reads
            # scd_reader.get_data() for humidity compensation - real _read_sgp() bails out (no
            # measurement, no backup) without it. scd_reader's own read chain is orthogonal to what
            # this chain tests, so this seeds its real cached reading directly via the same
            # _set_meas_data() a real read cycle itself calls (test_asy_scd30_driver.py's own
            # established precedent for reaching this exact seam), rather than also driving a real
            # SCD30 IRQ-triggered read cycle just to satisfy an unrelated dependency.
            await sensortask_wozi.scd_reader._set_meas_data(SCD30(800, 22.0, 45.0, None, None, None))
            # WaitTimeNTP's schema default (30) would need 30 real backup-triggering cycles before
            # _run_backup()'s own require_ntp gate ever clears without a real NTP sync (asy_sgp40_driver.py's
            # own voc_write countdown) - set to its minimum positive value so the very first real
            # backup below can complete without depending on real NTP reachability in this sandbox.
            persisted, _results = await sgp1.cfgmgr.write_config({"WaitTimeNTP": 1}, sgp1.get_cfg_schema())
            assert persisted
            task = sgp1.start_asy_read()
            try:
                # Real init: sgp.setup()'s own real I2C handshake against the twin's fake SGP40 chip
                # (serial number + self-test + general-call reset, asy_sgp40_driver.py's own
                # SGP40_I2C.initialize()/_reset()) - the reset alone sleeps a real 1s; no public
                # "init done" flag exists to poll, so this is a plain, generously-bounded sleep.
                await asyncio.sleep(2.5)
                sgp1.backup_counter = 59  # BackupPeriod defaults to 1 (minute) -> a real 60-cycle
                # threshold (asy_sgp40_driver.py's own _check_storage()) - forces the very next real
                # trigger cycle to reach it, exercising the same real _run_backup() 60 real cycles
                # would, just without waiting through 59 of them for the same real code path.
                sgp1.trigger_event.set()
                assert await _wait_until(lambda: sgp1.last_backup is not None, timeout_s=5.0), (
                    "the real VOC backup write never completed"
                )
            finally:
                await _cancel(task)

            # --- Simulated reboot: persist the twin's FRAM image to disk, then rebuild the whole
            # real object graph fresh from the SAME cfg_path/FRAM state - the digital-twin analogue
            # of a real device losing power and cold-booting with the same physical FRAM chip still
            # attached (digital_twin/README.md's "FRAM persistence" section). ---
            machine.flush_fram()
            await sensortask_wozi.build_system(cfg_path=cfg_path, web_host="127.0.0.1", web_port=_next_test_port())
            assert sensortask_wozi.sgp_reader is not None and sensortask_wozi.scd_reader is not None
            assert sensortask_wozi.sgp_reader is not sgp1  # a genuinely fresh object, not the same
            # instance surviving in memory - the whole point is that the persisted FRAM bytes, not
            # Python state, are what carries the backup across the "reboot".
            sgp2 = sensortask_wozi.sgp_reader
            await sensortask_wozi.scd_reader._set_meas_data(SCD30(800, 22.0, 45.0, None, None, None))  # see boot 1's own comment above

            # --- Restore, through the real chain again. ---
            task2 = sgp2.start_asy_read()
            try:
                await asyncio.sleep(2.5)  # same real init delay as boot 1 above
                sgp2.trigger_event.set()
                assert await _wait_until(lambda: sgp2.restored_from is not None, timeout_s=5.0), (
                    "the real VOC backup restore never completed after the simulated reboot"
                )
            finally:
                await _cancel(task2)
        finally:
            machine.configure_fram_state_path(None)  # module-level, process-wide - must not leak
            # into any other test in this file regardless of run order (MicroPython's globals()
            # doesn't preserve definition order - see this file's own watchdog-section comment).
            gc.collect()  # see the task-supervisor-restart section's own comment above - this test
            # builds the whole real object graph twice in one run.

    run_timed(scenario(), timeout_s=30.0)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
