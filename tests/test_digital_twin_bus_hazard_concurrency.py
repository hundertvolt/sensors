"""Digital-twin tier: boots the REAL sensortask_wozi.py/sensortask_dev.py object graphs against the
real digital_twin buses and proves SPECIFICATION.md Part C.8's locking model holds under genuine
concurrent load. Bus topology and the standing rule for adding a new device/variant: Part C.8."""

import asyncio
import sys

sys.path.insert(0, "ext")  # same convention as test_digital_twin_sensortask_integration.py's own comment
sys.path.insert(0, "digital_twin")

import machine

import sensortask_dev
import sensortask_wozi

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
_next_port = 19400  # own range, avoids TIME_WAIT/port collision with the 19100+ range in
# test_digital_twin_sensortask_integration.py, should both ever share one process.


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
    # Shared scenario body for both variants: starts the real timer/task starters build_system()
    # itself would, then asserts the run produced fresh data from every sensor and never starved
    # the watchdog - not just "didn't crash".
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
        # FRAM has its own dedicated SPI bus (no interleaving hazard here) but must stay healthy
        # through concurrent sensor error-log/backup writes onto it.
        assert module.fram.fram.initialized is True, "FRAM dropped out of the initialized state during concurrent bus load"
        assert await module.fram.fram.verify_present(), "FRAM did not respond to a device-ID re-probe after concurrent bus load"

        # SGP40_I2C._reset()'s general-call broadcast (SPECIFICATION.md Part C.8) must actually have
        # fired at least once, landing concurrently with its bus-sharing sibling's own startup.
        assert _GENERAL_CALL_ENTRY in shared_bus_log, "SGP40's general-call reset never fired during this run - test isn't exercising the real hazard window"
    finally:
        for task in tasks:
            await _cancel(task)


def test_wozi_real_task_graph_survives_concurrent_bus_load_including_a_real_general_call() -> None:
    # wozi's own SGP40+BMP3xx-on-i2c1 pairing can never be confirmed on real hardware (wozi is
    # never physically flashed - CLAUDE.md), so this twin run is its actual verification.
    machine.configure_i2c_wiring("wozi")
    port = _next_test_port()

    async def scenario() -> None:
        await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert sensortask_wozi.i2c1 is not None and sensortask_wozi.i2c1._i2c is not None
        await _run_real_task_graph_and_assert_healthy(sensortask_wozi, sensortask_wozi.i2c1._i2c.log, run_seconds=9.0)

    run_timed(scenario(), timeout_s=20.0)


def test_dev_real_task_graph_survives_concurrent_bus_load_including_a_real_general_call() -> None:
    # dev's SCD30+SGP40-on-i2c1 pairing also gets real-hardware proof
    # (tests_hardware/flash/test_bus_concurrency.py); this gives it fast, every-push CI coverage too.
    machine.configure_i2c_wiring("dev")
    port = _next_test_port()

    async def scenario() -> None:
        await sensortask_dev.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert sensortask_dev.i2c1 is not None and sensortask_dev.i2c1._i2c is not None
        await _run_real_task_graph_and_assert_healthy(sensortask_dev, sensortask_dev.i2c1._i2c.log, run_seconds=9.0)

    run_timed(scenario(), timeout_s=20.0)


def test_wozi_fram_recovers_after_an_injected_spi_write_fault() -> None:
    # wozi is never physically flashed, so this twin run is FRAM's only fault-then-recovery
    # verification for it; dev's equivalent is real-hardware, in
    # tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py.
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
        # FRAM_SPI._write() has no try/except of its own (unlike the I2C drivers); a SPI-level
        # failure propagates raw from set_values(). Protection lives one layer up in
        # AsyFramManager (see SPECIFICATION.md Part A.4), so this test catches it itself.
        assert raised is not None, "expected the injected SPI fault to propagate as a raised exception from set_values()"

        # Recovery: the fault fires before any simulated chip state is touched, so the chip was
        # never disturbed - verify_present() must succeed cleanly. Not wrapped in `async with
        # fram_spi:` since verify_present() self-acquires that (non-reentrant) lock internally.
        assert await fram_spi.verify_present(), "verify_present() failed to recover after one injected SPI write fault"

        buf = bytearray(4)
        async with fram_spi:
            ok = await fram_spi.set_values(b"\x01\x02\x03\x04", addr_start=0x100)
            assert ok, "set_values() failed on a clean retry after recovery"
            ok = await fram_spi.get_values(buf, addr_start=0x100)
            assert ok and bytes(buf) == b"\x01\x02\x03\x04", f"get_values() returned {bytes(buf)!r} on a clean retry after recovery, expected b'\\x01\\x02\\x03\\x04'"

    run_timed(scenario(), timeout_s=20.0)


def test_wozi_fram_recovers_after_an_injected_spi_read_fault() -> None:
    # Read-side sibling of the write-fault test above: _read_address() has the same no-try/except
    # gap as _write(), so the read path needs its own proof that recovery still works.
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
    # A single disconnect, not repeated flapping: the ESTABLISHED retry branch is a genuine,
    # non-fast-forwardable 60s sleep (SPECIFICATION.md Part E.5.1), so repeated flapping isn't
    # CI-time-reasonable here - tests_hardware/bench/test_network_resilience.py covers that on
    # real hardware instead.
    while not conn.wlan.isconnected():
        await asyncio.sleep(0.5)
    conn.wlan.disconnect()
    while not conn.wlan.isconnected():
        await asyncio.sleep(1.0)


def test_wozi_survives_concurrent_bus_load_and_a_real_established_wifi_disconnect() -> None:
    # Proves the real, fully-wired system tolerates a genuine 60s wifi_mode_lock hold (the real
    # ESTABLISHED-branch retry) while concurrent bus load is in flight. Real ~75s test time is
    # unavoidable (see _wait_established_then_flap_once()).
    #
    # Deliberately does NOT reuse _run_real_task_graph_and_assert_healthy() above: its
    # shared_bus_log/_GENERAL_CALL_ENTRY check assumes a short run window that never wraps the
    # twin I2C fake's bounded log deque - at this test's much longer duration that entry gets
    # evicted by ordinary traffic, a false negative on a property already proven by the sibling
    # test above. This test inlines its own leaner health check instead.
    machine.configure_i2c_wiring("wozi")
    port = _next_test_port()

    async def scenario() -> None:
        module = sensortask_wozi
        await module.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert module.conn is not None
        assert module.watchdog is not None and module.sysfunct is not None
        assert module.sgp_reader is not None and module.bmp_reader is not None and module.scd_reader is not None
        assert module.fram is not None
        # A real configured SSID, written before the task graph starts so the wifi task's first
        # connect attempt sees it (same technique as test_digital_twin_sensortask_integration.py's
        # test_wifi_sta_failure_falls_back_to_hotspot_and_drives_the_real_dns_server_and_status_led).
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
