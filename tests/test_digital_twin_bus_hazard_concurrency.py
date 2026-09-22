"""Digital-twin tier: boots the real sensortask_wozi.py/sensortask_dev.py object graphs against the
real digital_twin buses and proves SPECIFICATION.md Part C.8's locking model holds under genuine
concurrent load; Part C.8 also covers this file's own device-scope rationale."""

import asyncio
import json
import sys

sys.path.insert(0, "ext")  # same convention as test_digital_twin_sensortask_integration.py's own comment
sys.path.insert(0, "digital_twin")

import _http_client
import machine
from _tmp_scratch import TmpScratch
from unix_port_poll_prewarm import prewarm_poll_set

# Required of any entry point booting a sensortask_* module under the twin, and this file now also
# drives real client connections at the ceiling: growing the Unix port's pollfds array corrupts
# non-fd poll objects already in it, which is a segfault, not a test failure.
prewarm_poll_set()

import sensortask_dev  # noqa: E402 - must follow the prewarm above, which is the point of it
import sensortask_wozi  # noqa: E402

from crc_checks import CRC8  # noqa: E402 - same reason as the two device imports above

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Container, Coroutine
    from types import ModuleType
    from typing import Any, TypeVar

    from machine import WDT

    from asy_wifi_service import AsyConnTime

    T = TypeVar("T")


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("dtbh")
_next_port = 19400  # own range, avoids TIME_WAIT/port collision with the 19100+ range in
# test_digital_twin_sensortask_integration.py, should both ever share one process.


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


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


async def _feed_watchdog_periodically(watchdog: "WDT") -> None:
    while True:
        watchdog.feed()
        await asyncio.sleep(1.0)


_GENERAL_CALL_ENTRY = ("writeto", 0x00, b"\x06", True)

# Which get_data() field, per driver, proves that driver produced a real reading under load - the twin
# tier's much smaller analogue of tests/_bus_hazard_catalog.py's mock-tier adapters, used by the TOML-driven
# pass in _run_real_task_graph_and_assert_healthy() below (Part C.8).
#
# A new driver added to a device's own i2c1 needs an entry here before it gets this generic check - see the
# fail-loud assert there.
_I2C_DRIVER_HEALTH_FIELD: "dict[str, str]" = {"scd30": "CO2", "sgp40": "VOC", "bmp3xx": "Pres", "isl29125": "Lux"}


async def _api_burst_at_the_ceiling(module: "ModuleType", host: str, port: int) -> "list[object]":
    """A full ceiling's worth of concurrent REST requests, derived from the build under test.
    CLAUDE.md's four-tier bus-hazard rule wants API load and bus traffic together, and a raised
    max_connections means more of both at once - so the burst scales with the ceiling."""
    assert module.webserver is not None
    ceiling: int = module.webserver._max_connections

    async def one(path: str) -> object:
        try:
            res = await _http_client.fetch(host, port, "GET", path)
        except OSError:
            return "rejected"  # the documented reject-when-full outcome, not a failure here
        else:
            return res.status_code

    paths = ("/measurements", "/sensors", "/status", "/system")
    return list(await asyncio.gather(*(one(paths[i % len(paths)]) for i in range(ceiling))))


async def _run_real_task_graph_and_assert_healthy(module: "ModuleType", shared_bus_log: "Container[object]", run_seconds: float, api_port: "int | None" = None) -> None:
    # Shared scenario body for both variants: starts the real timer/task starters build_system()
    # itself would, then asserts the run produced fresh data from every sensor and never starved
    # the watchdog - not just "didn't crash".
    assert module.watchdog is not None and module.sysfunct is not None
    assert module.sgp40 is not None and module.bmp3xx is not None and module.scd30 is not None
    assert module.fram is not None
    await module.sysfunct.start_timers(module._collect_timer_starters())
    tasks = [starter() for starter in module._collect_task_starters()]
    tasks.append(asyncio.get_event_loop().create_task(_feed_watchdog_periodically(module.watchdog)))
    try:
        if api_port is not None:
            # Mid-run, not before or after: the point is a full ceiling of REST work landing while
            # the sensor tasks are genuinely mid-transaction on the shared bus.
            await asyncio.sleep(run_seconds / 2)
            api_results = await _api_burst_at_the_ceiling(module, "127.0.0.1", api_port)
            assert api_results.count(200) >= 1, api_results
            assert all(r in (200, "rejected") for r in api_results), api_results
            await asyncio.sleep(run_seconds / 2)
        else:
            await asyncio.sleep(run_seconds)
        assert module.watchdog.would_have_triggered_count == 0

        sgp_data = await module.sgp40.get_data()
        bmp_data = await module.bmp3xx.get_data()
        scd_data = await module.scd30.get_data()
        assert sgp_data.VOC is not None, "SGP40 never produced real data under concurrent bus load"
        assert bmp_data.Pres is not None, "BMP3xx never produced real data under concurrent bus load"
        assert scd_data.CO2 is not None, "SCD30 never produced real data under concurrent bus load"
        # dev-only: the ISL29125 shares i2c1 with both of the above AND drives its own INT pin
        # concurrently, so it is the one sensor here whose reads can be interleaved with an
        # interrupt-triggered extra cycle of its own (wozi never carries this instance at all).
        isl29125 = getattr(module, "isl29125", None)
        if isl29125 is not None:
            isl_data = await isl29125.get_data()
            assert isl_data.Lux is not None, "ISL29125 never produced real data under concurrent bus load"
            assert isl_data.RangeAct is not None, "ISL29125 reported a sample with no range attached"
        # FRAM has its own dedicated SPI bus (no interleaving hazard here) but must stay healthy
        # through concurrent sensor error-log/backup writes onto it.
        assert module.fram.fram.initialized is True, "FRAM dropped out of the initialized state during concurrent bus load"
        assert await module.fram.fram.verify_present(), "FRAM did not respond to a device-ID re-probe after concurrent bus load"

        # SGP40_I2C._reset()'s general-call broadcast (SPECIFICATION.md Part C.8) must actually have
        # fired at least once, landing concurrently with its bus-sharing sibling's own startup.
        assert _GENERAL_CALL_ENTRY in shared_bus_log, "SGP40's general-call reset never fired during this run - test isn't exercising the real hazard window"

        # TOML-driven pass (SPECIFICATION.md Part C.8): a second, cheap look at the same
        # already-booted graph, from the real wiring-plan JSON's own i2c1 membership rather than the
        # hardcoded list above - runs alongside it, staying correct if that membership changes.
        device = module.__name__[len("sensortask_") :]  # "sensortask_dev" -> "dev" - str.removeprefix() isn't used here since it's unproven under this MicroPython target
        with open(f"build/generated_src/sensortask_{device}_wiring_plan.json") as f:
            plan: dict[str, Any] = json.load(f)
        for bus_name, attachments in plan["buses"].items():
            for attachment in attachments:
                driver = attachment["driver"]
                field = _I2C_DRIVER_HEALTH_FIELD.get(driver)
                assert field is not None, f"no health-check field known for driver {driver!r} - add one to _I2C_DRIVER_HEALTH_FIELD before it can get generated digital-twin bus-hazard coverage"
                data = await getattr(module, driver).get_data()
                assert getattr(data, field) is not None, f"{driver!r} never produced real data (missing {field!r}) under concurrent bus load, per the TOML-driven {bus_name} membership check"
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
    # dev's SCD30+SGP40+ISL29125-on-i2c1 grouping also gets real-hardware proof
    # (tests_hardware/flash/test_bus_concurrency.py); this gives it fast, every-push CI coverage too.
    machine.configure_i2c_wiring("dev")
    port = _next_test_port()

    async def scenario() -> None:
        await sensortask_dev.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert sensortask_dev.i2c1 is not None and sensortask_dev.i2c1._i2c is not None
        await _run_real_task_graph_and_assert_healthy(sensortask_dev, sensortask_dev.i2c1._i2c.log, run_seconds=9.0)

    run_timed(scenario(), timeout_s=20.0)


def test_wozi_real_task_graph_survives_a_full_ceiling_api_burst_during_bus_load() -> None:
    # The twin leg of CLAUDE.md's four-tier bus-hazard rule for the raised connection ceiling:
    # max_connections concurrent REST requests landing while every sensor task is on the bus.
    machine.configure_i2c_wiring("wozi")
    port = _next_test_port()

    async def scenario() -> None:
        await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert sensortask_wozi.i2c1 is not None and sensortask_wozi.i2c1._i2c is not None
        await _run_real_task_graph_and_assert_healthy(sensortask_wozi, sensortask_wozi.i2c1._i2c.log, run_seconds=9.0, api_port=port)

    run_timed(scenario(), timeout_s=40.0)


def test_dev_real_task_graph_survives_a_full_ceiling_api_burst_during_bus_load() -> None:
    # dev's own three-driver i2c1 grouping under the same combined load; its real-hardware
    # counterpart is tests_hardware/bench/test_bus_concurrency_under_api_load.py.
    machine.configure_i2c_wiring("dev")
    port = _next_test_port()

    async def scenario() -> None:
        await sensortask_dev.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert sensortask_dev.i2c1 is not None and sensortask_dev.i2c1._i2c is not None
        await _run_real_task_graph_and_assert_healthy(sensortask_dev, sensortask_dev.i2c1._i2c.log, run_seconds=9.0, api_port=port)

    run_timed(scenario(), timeout_s=40.0)


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


def test_wozi_fram_chunk_loop_absorbs_a_transient_spi_rx_overrun() -> None:
    # Twin-tier form of the live-path mock tests in test_asy_fram_manager.py: the same fault, but against
    # the real twin bus and a chunk allocated from the real booted manager. One overrun costs nothing, _read
    # chunk-reading block 1 when block 0 fails.
    #
    # A persistent one degrades to None instead of propagating, and leaves the chunk marked BUSY by design -
    # destructive readout, SPECIFICATION.md Part A.4.
    machine.configure_i2c_wiring("wozi")
    port = _next_test_port()

    async def scenario() -> None:
        await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert sensortask_wozi.fram is not None
        manager = sensortask_wozi.fram
        bus = manager.fram._spidev.spi._spi
        assert bus is not None
        chunk = manager.get_chunk(40, crc=CRC8())  # 41 B with the CRC byte - over the 32 B DMA threshold
        assert chunk is not None
        payload = bytes(range(40))
        assert await chunk.write(payload)

        bus.rx_overrun_remaining = 1  # one transient glitch, then the bus recovers
        assert await chunk.read() == bytearray(payload), "a single RX overrun should be absorbed by the block-1 copy"
        assert bus.rx_overrun_remaining == 0, "the injected overrun never actually fired"

        bus.rx_overrun = True  # persistent: both copies unreadable
        assert await chunk.read() is None, "an unrecoverable overrun must degrade, not propagate"
        bus.rx_overrun = False
        assert await chunk.read() is None, "an interrupted read deliberately keeps the chunk unreadable until rewritten"
        assert await chunk.write(payload), "a write is what clears the stuck BUSY status bytes"
        assert await chunk.read() == bytearray(payload)

    run_timed(scenario(), timeout_s=20.0)


async def _wait_established_then_flap_once(conn: "AsyConnTime") -> None:
    # A single disconnect, not repeated flapping: the ESTABLISHED retry branch is a genuine, non-fast-
    # forwardable 60s sleep (Part E.5.1), so repeated flapping is not CI-time-reasonable here.
    # tests_hardware/bench/test_network_resilience.py covers that on real hardware instead.
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
    # Deliberately does NOT reuse _run_real_task_graph_and_assert_healthy(): its shared_bus_log check
    # assumes a short window that never wraps the twin I2C fake's bounded log deque, and at this test's much
    # longer duration that entry is evicted by ordinary traffic - a false negative on a proven property.
    machine.configure_i2c_wiring("wozi")
    port = _next_test_port()

    async def scenario() -> None:
        module = sensortask_wozi
        await module.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert module.conn is not None
        assert module.watchdog is not None and module.sysfunct is not None
        assert module.sgp40 is not None and module.bmp3xx is not None and module.scd30 is not None
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
            sgp_data = await module.sgp40.get_data()
            bmp_data = await module.bmp3xx.get_data()
            scd_data = await module.scd30.get_data()
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


def test_wozi_storage_pause_gates_the_real_twin_chip_and_override_still_reaches_it() -> None:
    # Twin-tier parity for the chunk-level gating the mock tier proves against a fake bus and the flash tier
    # against the real chip: the same claims, through the real booted manager on the twin bus. The
    # discriminating check reads the chip back with override_pause - a refused write would show new bytes.
    machine.configure_i2c_wiring("wozi")

    async def scenario() -> None:
        await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=_next_test_port())
        assert sensortask_wozi.fram is not None
        manager = sensortask_wozi.fram
        chunk = manager.get_chunk(16, crc=CRC8())
        assert chunk is not None
        first, second = bytes(range(16)), bytes(range(100, 116))
        assert await chunk.write(first)

        manager.set_pause(value=True)
        assert await chunk.write(second) is False
        assert bytes(await chunk.read(override_pause=True) or b"") == first, "the refused write still reached the twin chip"
        assert await chunk.read() is None

        assert await chunk.write(second, override_pause=True) is True
        assert bytes(await chunk.read(override_pause=True) or b"") == second

        manager.set_pause(value=False)
        assert await chunk.write(first) is True
        assert bytes(await chunk.read() or b"") == first

    run_timed(scenario(), timeout_s=20.0)


def test_wozi_write_protect_blocks_reads_too_and_the_data_survives_it() -> None:
    # Twin-tier parity for the mock tier's pair of write-protect tests, and the accepted, intended behavior
    # the flash tier confirms against real silicon: _read_chunk() has to WRITE a transient busy marker
    # before reading, so write protection gates read() as well as write().
    #
    # Different in kind from the pause gate above - that refuses before the bus, this at the chip - and,
    # crucially, non-destructive: the bytes come back once it is cleared.
    machine.configure_i2c_wiring("wozi")

    async def scenario() -> None:
        await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=_next_test_port())
        assert sensortask_wozi.fram is not None
        manager = sensortask_wozi.fram
        chunk = manager.get_chunk(16, crc=CRC8())
        assert chunk is not None
        payload = bytes(range(16))
        assert await chunk.write(payload)

        assert await manager.fram.set_write_protected(value=True) is True
        assert await manager.fram.get_write_protected() is True
        assert await chunk.write(bytes(range(100, 116))) is False
        assert await chunk.read() is None, "a write-protected chunk read succeeded - the busy-marker write cannot have happened"
        # override_pause only bypasses the manager's own pause flag, never the chip's protection.
        assert await chunk.read(override_pause=True) is None

        assert await manager.fram.set_write_protected(value=False) is True
        assert bytes(await chunk.read() or b"") == payload, "the refusal damaged the stored bytes - it is supposed to be an access gate only"

    run_timed(scenario(), timeout_s=20.0)


def test_wozi_storage_pause_short_circuits_before_the_bus_so_an_injected_fault_survives() -> None:
    # Twin-tier form of test_asy_fram_manager.py's ordering test: _read() consults the pause flag before
    # touching SPI, so a queued overrun must still be there afterwards. Uses the bus-level
    # rx_overrun_remaining knob, the only one modelling 1.29's 32-byte DMA threshold (Part F.5.2).
    machine.configure_i2c_wiring("wozi")

    async def scenario() -> None:
        await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=_next_test_port())
        assert sensortask_wozi.fram is not None
        manager = sensortask_wozi.fram
        bus = manager.fram._spidev.spi._spi
        assert bus is not None
        chunk = manager.get_chunk(40, crc=CRC8())  # over the 32 B DMA threshold, so an overrun is reachable
        assert chunk is not None
        payload = bytes(range(40))
        assert await chunk.write(payload)

        bus.rx_overrun_remaining = 1
        manager.set_pause(value=True)
        assert await chunk.read() is None  # refused by the gate
        assert bus.rx_overrun_remaining == 1, "the paused read reached the bus and consumed the injected overrun"

        manager.set_pause(value=False)
        assert await chunk.read() == bytearray(payload)  # absorbed by the block-1 copy
        assert bus.rx_overrun_remaining == 0, "the overrun never fired once the bus was genuinely reachable"

    run_timed(scenario(), timeout_s=20.0)


def test_wozi_storage_pause_does_not_survive_a_simulated_reboot() -> None:
    # AsyFramManager.__init__ sets _pause = False and nothing restores it from FRAM, so the pause is RAM-
    # only. The bench tier proves this against a real reboot; this is the CI-gated counterpart, using the
    # same state-file reboot mechanism the SGP40 backup-survival test uses.
    #
    # That shared mechanism is what makes the contrast meaningful: chunk bytes do carry across this same
    # boundary, the pause flag does not.
    machine.configure_i2c_wiring("wozi")

    async def scenario() -> None:
        cfg_path = _tmp_cfg_dir()
        machine.configure_fram_state_path(cfg_path + "fram_state.json")
        try:
            await sensortask_wozi.build_system(cfg_path=cfg_path, web_host="127.0.0.1", web_port=_next_test_port())
            assert sensortask_wozi.fram is not None
            chunk = sensortask_wozi.fram.get_chunk(16, crc=CRC8())
            assert chunk is not None
            payload = bytes(range(16))
            assert await chunk.write(payload)
            sensortask_wozi.fram.set_pause(value=True)
            assert sensortask_wozi.fram.get_pause() is True
            machine.flush_fram()

            await sensortask_wozi.build_system(cfg_path=cfg_path, web_host="127.0.0.1", web_port=_next_test_port())
            assert sensortask_wozi.fram is not None
            assert sensortask_wozi.fram.get_pause() is False, "the pause flag survived a reboot - it is supposed to be RAM-only"
            chunk2 = sensortask_wozi.fram.get_chunk(16, crc=CRC8())
            assert chunk2 is not None
            assert bytes(await chunk2.read() or b"") == payload, "the chunk bytes should survive the same reboot the pause flag does not"
        finally:
            machine.configure_fram_state_path(None)

    run_timed(scenario(), timeout_s=30.0)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
