"""Digital-twin tier: boots the REAL sensortask_wozi.py and sensortask_dev.py object graphs (full
build_system() + the real task/timer starters, matching test_digital_twin_sensortask_integration.py's
own test_watchdog_is_never_starved_while_every_real_task_runs_concurrently pattern) against the real
digital_twin buses, and proves SPECIFICATION.md Part C.8's locking model holds under genuine
concurrent load - at twin speed/determinism, not real hardware. Complements
tests_hardware/flash/test_bus_concurrency.py (real hardware, dev variant only, since wozi is never
physically flashed per CLAUDE.md's hard rule) and tests/test_bus_hazard_multi_device.py (fast mock
bus, no real chip-protocol fidelity): this is the only tier that can exercise wozi's own real
SGP40+BMP3xx pairing at all, since wozi never touches real silicon.

Bus topology exercised here (both real, current wirings - see sensortask_wozi.py/sensortask_dev.py's
own construction comments and digital_twin/machine.py's _wire_i2c_devices(), the canonical
per-variant topology declaration used by both this file and the twin itself):
  - wozi (default profile): i2c1 = SGP40 + BMP3xx sharing a bus; i2c0 = SCD30 alone.
  - dev:                    i2c1 = SCD30 + SGP40 sharing a bus; i2c0 = BMP3xx alone.

**Standing rule - read before adding a new bus-facing device to src/ or a new variant to
sensortask_*.py:** add a matching boot+concurrency test here for the new topology too, and update
digital_twin/machine.py's own _wire_i2c_devices() first (this file's own boot will otherwise fail
loudly with a NAK, not silently miss coverage) - see SPECIFICATION.md Part C.8's own note on this.
"""

import asyncio
import sys

sys.path.insert(0, "ext")  # same convention as test_digital_twin_sensortask_integration.py's own comment
sys.path.insert(0, "digital_twin")

import machine  # noqa: E402

import sensortask_dev  # noqa: E402
import sensortask_wozi  # noqa: E402

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


_TMP_DIR = "tests/_tmp"
_next_dir = 0
_next_port = 19400  # a fresh, non-privileged, test-file-local range - avoids any TIME_WAIT/port
# collision with test_digital_twin_sensortask_integration.py's own 19100+ range in the (unlikely,
# since each tests/test_*.py file is its own Unix-port process) event both ever ran in one process.


def _sweep_stale_tmp_dirs(prefix: str) -> None:
    import os

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


_sweep_stale_tmp_dirs("dtbh_")


def _tmp_cfg_dir() -> str:
    import os

    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    _next_dir += 1
    path = _TMP_DIR + "/dtbh_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass
    return path + "/"


def _next_test_port() -> int:
    global _next_port
    _next_port += 1
    return _next_port


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _feed_watchdog_periodically(watchdog: "Any") -> None:
    while True:
        watchdog.feed()
        await asyncio.sleep(1.0)


_GENERAL_CALL_ENTRY = ("writeto", 0x00, b"\x06", True)


async def _run_real_task_graph_and_assert_healthy(module: "Any", shared_bus_log: "Any", run_seconds: float) -> None:
    # Shared scenario body for both variants below - starts the exact real timer/task starters
    # build_system() itself would (module._collect_task_starters()/_collect_timer_starters()),
    # matching test_watchdog_is_never_starved_while_every_real_task_runs_concurrently's own proven
    # pattern, then asserts the real concurrent run produced fresh data from every sensor and never
    # starved the watchdog - not just "didn't crash".
    assert module.watchdog is not None and module.sysfunct is not None
    assert module.sgp_reader is not None and module.bmp_reader is not None and module.scd_reader is not None
    assert module.fram is not None
    await module.sysfunct.start_timers(module._collect_timer_starters())
    tasks = [starter() for starter in module._collect_task_starters()]
    tasks.append(asyncio.get_event_loop().create_task(_feed_watchdog_periodically(module.watchdog)))
    try:
        await asyncio.sleep(run_seconds)
        assert module.watchdog.would_have_triggered_count == 0

        sgp_data = await module.sgp_reader.get_data()
        bmp_data = await module.bmp_reader.get_data()
        scd_data = await module.scd_reader.get_data()
        assert sgp_data.VOC is not None, "SGP40 never produced real data under concurrent bus load"
        assert bmp_data.Pres is not None, "BMP3xx never produced real data under concurrent bus load"
        assert scd_data.CO2 is not None, "SCD30 never produced real data under concurrent bus load"
        # FRAM shares no bus with anything else (its own dedicated SPI bus - see this module's own
        # docstring), so it has no cross-device interleaving hazard to prove here, but it must have
        # stayed genuinely healthy (still initialized, still answering) through a run that also
        # concurrently drove every sensor's own real error-log/backup writes onto it - the same
        # "not just didn't crash" bar this function already holds every other module to.
        assert module.fram.fram.initialized is True, "FRAM dropped out of the initialized state during concurrent bus load"
        assert await module.fram.fram.verify_present(), "FRAM did not respond to a device-ID re-probe after concurrent bus load"

        # The real SGP40_I2C._reset() general-call broadcast (SPECIFICATION.md Part C.8's "Known
        # structural gap" finding) must have actually fired at least once during this run (SGP40's
        # own real startup path always calls it), landing concurrently with its bus-sharing
        # sibling's own real startup/running - proof the whole system stays healthy through that,
        # not just that the broadcast is theoretically harmless in isolation.
        assert _GENERAL_CALL_ENTRY in shared_bus_log, "SGP40's general-call reset never fired during this run - test isn't exercising the real hazard window"
    finally:
        for task in tasks:
            await _cancel(task)


def test_wozi_real_task_graph_survives_concurrent_bus_load_including_a_real_general_call() -> None:
    # wozi's real, production wiring: SGP40 + BMP3xx share i2c1 (never SCD30, on i2c0 alone) - the
    # one pairing real hardware can never confirm, since wozi is never physically flashed
    # (CLAUDE.md's hard rule) - this twin run is the actual, complete verification for it.
    machine.configure_i2c_wiring("wozi")
    port = _next_test_port()

    async def scenario() -> None:
        await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert sensortask_wozi.i2c1 is not None and sensortask_wozi.i2c1._i2c is not None
        await _run_real_task_graph_and_assert_healthy(sensortask_wozi, sensortask_wozi.i2c1._i2c.log, run_seconds=9.0)

    run_timed(scenario(), timeout_s=20.0)


def test_dev_real_task_graph_survives_concurrent_bus_load_including_a_real_general_call() -> None:
    # dev's real bench wiring: SCD30 + SGP40 share i2c1 (BMP3xx alone on i2c0) - the pairing
    # tests_hardware/flash/test_bus_concurrency.py exercises on real hardware; this twin run gives
    # the same pairing fast, deterministic, every-CI-push coverage alongside that real-hardware proof.
    machine.configure_i2c_wiring("dev")
    port = _next_test_port()

    async def scenario() -> None:
        await sensortask_dev.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert sensortask_dev.i2c1 is not None and sensortask_dev.i2c1._i2c is not None
        await _run_real_task_graph_and_assert_healthy(sensortask_dev, sensortask_dev.i2c1._i2c.log, run_seconds=9.0)

    run_timed(scenario(), timeout_s=20.0)


def test_wozi_fram_recovers_after_an_injected_spi_write_fault() -> None:
    # wozi specifically (not dev) for the same reason test_wozi_real_task_graph_survives_... above
    # uses wozi's own real wiring: wozi is never physically flashed (CLAUDE.md's hard rule), so this
    # twin run is FRAM's own *only* real-fault-then-recovery verification for that variant. dev's
    # own equivalent gets its real-hardware proof from
    # tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py instead - see
    # that script's own docstring for why the real-hardware fault shape (a CS-pin race) differs from
    # this twin-level one (a raised exception from the injected fault hook) but both exercise the
    # same underlying question: does one failed FRAM operation leave the driver wedged for the next
    # one, or does it cleanly recover.
    machine.configure_i2c_wiring("wozi")
    port = _next_test_port()

    async def scenario() -> None:
        await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert sensortask_wozi.fram is not None
        fram_spi = sensortask_wozi.fram.fram
        assert fram_spi._spidev.spi._spi is not None
        chip = fram_spi._spidev.spi._spi.device
        assert chip is not None
        assert fram_spi.initialized is True

        chip.fault.inject_fault("write", OSError(5))
        raised: BaseException | None = None
        async with fram_spi:
            try:
                await fram_spi.set_values(b"\x01\x02\x03\x04", addr_start=0x100)
            except OSError as e:
                raised = e
        # REAL FINDING, confirmed directly (not assumed): unlike this codebase's I2C drivers, which
        # generally catch/translate a NAK into a clean False return, FRAM_SPI._write() has no
        # try/except of its own around the underlying SPI call - a genuine SPI-level failure
        # propagates straight out of set_values() as a raw exception. This is not a gap in
        # production: AsyFramManager's own real callers already wrap every get_values()/
        # set_values() call in a broad `except Exception` (confirmed directly in
        # asy_fram_manager.py) - the protection lives one layer up, not inside FRAM_SPI itself. This
        # test exercises FRAM_SPI directly, matching the mock tier's own precedent of testing raw
        # driver classes rather than their manager, so it must itself catch what
        # AsyFramManager normally would.
        assert raised is not None, "expected the injected SPI fault to propagate as a raised exception from set_values()"

        # Recovery: FaultInjector raises before FramChip.write() ever touches any simulated chip
        # state (digital_twin/_fram_chip.py's own write()/readinto() call maybe_raise() first,
        # before any opcode/data handling) - the chip itself was never actually disturbed, so a
        # fresh verify_present() must succeed cleanly, and the driver must go on to work completely
        # normally afterward, proving one failed operation doesn't leave FRAM_SPI itself wedged.
        # Deliberately NOT wrapped in `async with fram_spi:` - verify_present() self-acquires the
        # same outer lock internally (its own docstring: asyncio.Lock isn't reentrant), unlike
        # get_values()/set_values() which require the caller to already hold it.
        assert await fram_spi.verify_present(), "verify_present() failed to recover after one injected SPI write fault"

        buf = bytearray(4)
        async with fram_spi:
            ok = await fram_spi.set_values(b"\x01\x02\x03\x04", addr_start=0x100)
            assert ok, "set_values() failed on a clean retry after recovery"
            ok = await fram_spi.get_values(buf, addr_start=0x100)
            assert ok and bytes(buf) == b"\x01\x02\x03\x04", f"get_values() returned {bytes(buf)!r} on a clean retry after recovery, expected b'\\x01\\x02\\x03\\x04'"

    run_timed(scenario(), timeout_s=20.0)


def test_wozi_fram_recovers_after_an_injected_spi_read_fault() -> None:
    # Read-side sibling of test_wozi_fram_recovers_after_an_injected_spi_write_fault above -
    # previously missing (a tier-coverage gap: the real-hardware CS-hijack script covers both a
    # write and a read race, but this twin-level exception-injection form only ever covered write).
    # Not a redundant mirror: _read_address() (FRAM_SPI's own real read primitive, used by
    # get_values() and by verify_present()'s own RDID probe) has no try/except of its own either -
    # confirmed directly, same shape as _write()'s already-documented gap - so a genuine SPI-level
    # read failure is real, distinct code from the write path, and needs its own proof that
    # AsyFramManager's one-layer-up broad `except Exception` is what actually protects it, not
    # FRAM_SPI itself.
    machine.configure_i2c_wiring("wozi")
    port = _next_test_port()

    async def scenario() -> None:
        await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert sensortask_wozi.fram is not None
        fram_spi = sensortask_wozi.fram.fram
        assert fram_spi._spidev.spi._spi is not None
        chip = fram_spi._spidev.spi._spi.device
        assert chip is not None
        assert fram_spi.initialized is True

        # Seed real, known bytes first, through a clean round trip - so a "recovered" read below
        # can be checked against real prior content, not just "returned without raising".
        async with fram_spi:
            ok = await fram_spi.set_values(b"\x05\x06\x07\x08", addr_start=0x200)
            assert ok, "seed write before the fault-injection scenario failed"

        chip.fault.inject_fault("readinto", OSError(5))
        buf = bytearray(4)
        raised: BaseException | None = None
        async with fram_spi:
            try:
                await fram_spi.get_values(buf, addr_start=0x200)
            except OSError as e:
                raised = e
        assert raised is not None, "expected the injected SPI fault to propagate as a raised exception from get_values()"

        # Recovery: same reasoning as the write test above - FaultInjector raises before FramChip.
        # readinto() ever touches simulated chip state, so the chip itself was never disturbed.
        assert await fram_spi.verify_present(), "verify_present() failed to recover after one injected SPI read fault"

        async with fram_spi:
            ok = await fram_spi.get_values(buf, addr_start=0x200)
            assert ok and bytes(buf) == b"\x05\x06\x07\x08", f"get_values() returned {bytes(buf)!r} on a clean retry after recovery, expected the real pre-fault seeded content b'\\x05\\x06\\x07\\x08'"

    run_timed(scenario(), timeout_s=20.0)


async def _wait_established_then_flap_once(conn: "Any") -> None:
    # A single real established-connection disconnect, not repeated flapping - see this test's own
    # module-level comment for why: asy_wifi_service.py's own _on_sta_disconnected() ESTABLISHED
    # branch is a genuine, non-fast-forwardable 60s asyncio.sleep() even at twin speed (this suite
    # never fast-forwards time - SPECIFICATION.md Part E.5.1), so repeated flapping isn't a
    # reasonable CI-time proof at this tier; tests_hardware/bench/test_network_resilience.py's own
    # real, fast repeated-flap technique is what actually exercises that shape, on real hardware
    # where it demonstrably behaves differently (see BACKLOG.md's own real timing account).
    while not conn.wlan.isconnected():
        await asyncio.sleep(0.5)
    conn.wlan.disconnect()
    while not conn.wlan.isconnected():
        await asyncio.sleep(1.0)


def test_wozi_survives_concurrent_bus_load_and_a_real_established_wifi_disconnect() -> None:
    # Recombination test (2026-09-04, project owner's own explicit request): proves the real, fully-
    # wired system - not just the isolated AsyConnTime class (tests/test_asy_wifi_service.py's own
    # test_status_getters_return_locked_defaults_during_a_real_concurrent_outage_retry, mock tier,
    # which uses a synthetic pre-acquired lock, not a real competing task) - tolerates a genuine 60s
    # wifi_mode_lock hold (the real ESTABLISHED-branch retry) while real concurrent bus load is
    # simultaneously in flight, through the exact same real object graph
    # test_wozi_real_task_graph_survives_concurrent_bus_load_including_a_real_general_call already
    # proves healthy under a clean network. Real ~70s test time - unavoidable, see
    # _wait_established_then_flap_once()'s own comment.
    #
    # Deliberately does NOT reuse _run_real_task_graph_and_assert_healthy() above: a REAL FINDING
    # from this test's own first draft - that helper's shared_bus_log check
    # (_GENERAL_CALL_ENTRY in shared_bus_log) assumes its own short ~9s run window never wraps the
    # twin I2C fake's bounded log deque (digital_twin/machine.py's own _LOG_MAXLEN); at this test's
    # much longer ~75s real duration (unavoidable - see above), the one-time general-call entry from
    # SGP40's own startup gets evicted by ordinary bus traffic long before the run ends, long after
    # actually happening - a false negative on an orthogonal property this test isn't about (already
    # proven, short-duration, by the sibling test above). This test inlines its own leaner health
    # check instead, without that specific assertion.
    machine.configure_i2c_wiring("wozi")
    port = _next_test_port()

    async def scenario() -> None:
        module = sensortask_wozi
        await module.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert module.conn is not None
        assert module.watchdog is not None and module.sysfunct is not None
        assert module.sgp_reader is not None and module.bmp_reader is not None and module.scd_reader is not None
        assert module.fram is not None
        # A real configured SSID (not the "SSID==''" unconfigured shortcut) - same technique
        # test_wifi_sta_failure_falls_back_to_hotspot_and_drives_the_real_dns_server_and_status_led
        # (test_digital_twin_sensortask_integration.py) already uses, written before the task graph
        # starts below so the wifi task's very first connect attempt sees it.
        persisted, _results = await module.conn.cfgmgr.write_config({"SSID": "TestNet"}, module.conn.get_cfg_schema())
        assert persisted

        await module.sysfunct.start_timers(module._collect_timer_starters())
        tasks = [starter() for starter in module._collect_task_starters()]
        tasks.append(asyncio.get_event_loop().create_task(_feed_watchdog_periodically(module.watchdog)))
        flap_task = asyncio.get_event_loop().create_task(_wait_established_then_flap_once(module.conn))
        try:
            await asyncio.sleep(75.0)
            assert module.watchdog.would_have_triggered_count == 0
            sgp_data = await module.sgp_reader.get_data()
            bmp_data = await module.bmp_reader.get_data()
            scd_data = await module.scd_reader.get_data()
            assert sgp_data.VOC is not None, "SGP40 never produced real data under concurrent bus load + a real wifi disconnect"
            assert bmp_data.Pres is not None, "BMP3xx never produced real data under concurrent bus load + a real wifi disconnect"
            assert scd_data.CO2 is not None, "SCD30 never produced real data under concurrent bus load + a real wifi disconnect"
            assert module.fram.fram.initialized is True
            assert await module.fram.fram.verify_present()
            assert module.conn.wlan.isconnected() is True, "WiFi never recovered from the real established-connection disconnect within the real 60s retry window"
        finally:
            await _cancel(flap_task)
            for task in tasks:
                await _cancel(task)

    run_timed(scenario(), timeout_s=95.0)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
