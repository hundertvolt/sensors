"""Wall-clock consumers across an RTC step on the twin (the RTC is the wall clock, as on rp2): reader TS, backup age,
NTP's cettime and staleness, and a real sync against the local NTP responder. Each case runs on one device
tests/_twin_devices.py picks; the L1 suites cover every module."""

import asyncio
import json
import sys
import time

sys.path.insert(0, "ext")  # the vendored ext/microdot.py every generated device module imports
sys.path.insert(0, "digital_twin")  # the twin's machine, network and neopixel fakes, ahead of tests/'s own
sys.path.insert(0, "digital_twin/unixport")  # the responder's and the UDP shim's fake-free directory

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

prewarm_poll_set()  # before any poll object is registered (digital_twin/README.md "Known gaps")
patch_asy_udp_socket_for_unix_port()  # before any UDPSocket is constructed (digital_twin/README.md "_unix_port_udp_addr_shim.py")

import _wall_clock  # noqa: E402 - imported after the prewarm and the UDP shim
import machine  # noqa: E402 - imported after the prewarm and the UDP shim
import microtest  # noqa: E402 - imported after the prewarm and the UDP shim
import network  # noqa: E402 - imported after the prewarm and the UDP shim
import run_generic_integration  # noqa: E402 - imported after the prewarm and the UDP shim
from _async_harness import cancel, cancel_all, run_timed  # noqa: E402 - imported after the prewarm and the UDP shim
from _digital_twin_construction_scenarios import load_device  # noqa: E402 - imported after the prewarm and the UDP shim
from _error_codes import code  # noqa: E402 - imported after the prewarm and the UDP shim
from _generated_module import ERROR_LEVEL, boot_entry_watchdog, write_error_level_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _ntp_responder import NtpResponder  # noqa: E402 - imported after the prewarm and the UDP shim
from _offline_ntp_config import write_offline_ntp_config, write_responder_ntp_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _port_bands import PortAllocator  # noqa: E402 - imported after the prewarm and the UDP shim
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_devices import device_with, generated_devices, wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim
from _udp_port_redirect import redirect_udp_port  # noqa: E402 - imported after the prewarm and the UDP shim

import asy_base_classes  # noqa: E402 - imported after the prewarm and the UDP shim
import asy_ntp_client  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_config_manager import config_filename  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_scd30_driver import SCD30  # noqa: E402 - imported after the prewarm and the UDP shim

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from types import ModuleType
    from typing import TypeVar

    from launch import _Plan

    T = TypeVar("T")

# @tunable l2.clock_jump_wait_timeout_s = 20.0
_WAIT_TIMEOUT_S = 20.0
_POLL_MS = 50  # how often a wait below looks again
_TICKS_TO_RETRY = 4  # check ticks fired by hand toward the next attempt (tests/test_digital_twin_ntp.py's count)
_SSID = "TestNet"
_SCD30_READING = SCD30(800, 22.0, 45.0, None, None, None, None, None)  # the compensation the SGP40 reads first
_DST_START = _wall_clock.epoch_seconds(2026, 3, 29, 1, 0, 0)  # the last Sunday of March, 01:00 UTC: CET to CEST
_RP2_BOOT_CLOCK = _wall_clock.epoch_seconds(2021, 1, 1, 0, 0, 0)  # rp2's RTC at power-up (ports/rp2/main.c:141-145)

_scratch = TmpScratch("dt_clock_jump")
_PORTS = PortAllocator("test_digital_twin_clock_jump")
microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)


async def _set_clock(module: "ModuleType") -> None:
    # The clock as an NTP sync leaves it (_handle_ntp_sync_success()): Synced, the clock valid for UTCTime and the
    # VOC backups, and every utc_now() a real time from here on.
    await module.ntp._set_synced(value=True)
    module.ntp._clock_valid = True
    asy_base_classes.set_utc_valid()


async def _boot(device: str, cfg_path: "str | None" = None) -> "ModuleType":
    # A new board on the device's plan, built and set up as its boot entry does (offline NTP config), the wall clock
    # installed over the loaded product modules (the runner's own line).
    module = load_device(device)
    plan = wiring_plan(device)
    machine.reset_peripherals()
    network.reset_interfaces()
    machine.configure_wiring(plan)
    cfg = cfg_path if cfg_path is not None else _scratch.dir()
    write_offline_ntp_config(cfg)
    write_error_level_config(cfg)
    await module.build_system(watchdog=boot_entry_watchdog(module, device), cfg_path=cfg, debug=ERROR_LEVEL, web_host="127.0.0.1", web_port=0)
    runner_plan: _Plan = cast("_Plan", plan)
    run_generic_integration._wire_uart_crossover(module, runner_plan)  # before the setups (CLAUDE.md "Known hang cause")
    await module.sysfunct.run_setups(module._collect_setups())
    _wall_clock.install(run_generic_integration.product_modules())
    return module


def _booted(device: str, responder: NtpResponder, scenario: "Callable[[ModuleType], Coroutine[object, object, T]]") -> "T":
    # The device's real main() beside the responder (tests/test_digital_twin_ntp.py's shape): the responder's config, a
    # station to join, the product's port 123 mapped to the responder's and the wall clock installed.
    cfg_path = _scratch.dir()
    machine.reset_peripherals()
    network.reset_test_state()
    machine.configure_wiring(wiring_plan(device))
    write_responder_ntp_config(cfg_path)
    write_error_level_config(cfg_path)
    with open(config_filename(cfg_path, "WIFI"), "w") as f:
        f.write(json.dumps({"SSID": _SSID}))
    module = load_device(device)
    _wall_clock.install(run_generic_integration.product_modules())
    earlier = getattr(module, "webserver", None)  # an earlier boot's, until main() constructs its own (the last one)

    async def built() -> bool:
        return getattr(module, "webserver", None) not in (None, earlier)

    async def whole() -> "T":
        with redirect_udp_port(asy_ntp_client, 123, responder.port):
            boot = module.main(watchdog=boot_entry_watchdog(module, device), cfg_path=cfg_path, debug=ERROR_LEVEL, web_host="127.0.0.1", web_port=0)
            tasks = [asyncio.create_task(responder.serve()), asyncio.create_task(boot)]
            try:
                await _until(built, "no construction")
                return await scenario(module)
            finally:
                await cancel_all(tasks)

    try:
        return run_timed(whole(), 3 * _WAIT_TIMEOUT_S)
    finally:
        responder.close()


def _clock() -> "_wall_clock.WallClock":
    clock = _wall_clock.installed()
    assert clock is not None, "no wall clock installed"
    return clock


async def _ticks_to_attempt(module: "ModuleType", responder: NtpResponder) -> None:
    # Fires the client's check tick, as its 10 s timer does, until the responder takes a request.
    before = responder.requests
    for _ in range(_TICKS_TO_RETRY):
        module.ntp._ntp_timer_trigger_event.set()
        await asyncio.sleep_ms(_POLL_MS)
        if responder.requests > before:
            return
    raise AssertionError(f"no attempt within {_TICKS_TO_RETRY} check ticks")


async def _until(holds: "Callable[[], Coroutine[object, object, bool]]", what: str) -> None:
    for _ in range(int(_WAIT_TIMEOUT_S * 1000) // _POLL_MS):
        if await holds():
            return
        await asyncio.sleep_ms(_POLL_MS)
    raise AssertionError(f"{what} within {_WAIT_TIMEOUT_S} s")


def test_a_reader_stamps_each_sample_with_the_clock_as_stepped() -> None:
    # A step back an hour and forward a day: the next cycle's TS is the stepped clock's (a reader stamps from the RTC,
    # never from its own count). One BMP3XX, the reader the plans pick.
    device = device_with("bmp3xx")

    async def scenario() -> "list[tuple[int, object]]":
        module = await _boot(device)
        await _set_clock(module)
        reader = module.bmp3xx
        tasks = [starter() for starter in reader.get_task_starters()]
        for starter in reader.get_trigger_starters():
            starter()
        seen: list[tuple[int, object]] = []
        try:
            for step in (0, -3600, 86400):
                _clock().step(step)
                before = reader._datastruct

                async def fresh(before: object = before) -> bool:
                    return reader._datastruct is not before and reader._datastruct.TS is not None

                await _until(fresh, "no BMP3XX sample after the step")
                seen.append((_clock().time(), reader._datastruct.TS))
        finally:
            await cancel_all(tasks)
        return seen

    for wall, stamp in run_timed(scenario(), 3 * _WAIT_TIMEOUT_S):
        assert isinstance(stamp, int) and abs(stamp - wall) <= 1, f"{device}: a sample stamped {stamp} under a clock reading {wall}"


def test_a_backup_dated_after_a_backward_step_is_expired_under_a_max_age_and_kept_under_none() -> None:
    # One timestamped SGP40 backup, then the clock stepped back two hours: its age is negative, which BackupMaxAge 60
    # refuses as expired (one W SGP_BACKUP_AGE) and 0 ("use every backup") keeps (asy_sgp40_driver.py's age check).
    device = device_with("sgp40", "fram")
    cfg_path = _scratch.dir()
    machine.configure_fram_state_path(cfg_path + "fram_state.json")

    async def backed_up() -> int:
        module = await _boot(device, cfg_path)
        await _set_clock(module)
        await module.scd30._set_meas_data(_SCD30_READING)
        sgp = module.sgp40
        assert (await sgp.cfgmgr.write_config({"WaitTimeNTP": 0}))[0]
        task = sgp.start_asy_read()
        try:

            async def initialised() -> bool:
                return bool(sgp._voc_init == 1)

            await _until(initialised, "no SGP40 init")
            sgp._backup_counter = 59  # BackupPeriod 1 (minute): the next cycle backs up
            sgp._read_event.set()

            async def written() -> bool:
                return (await sgp.get_mem_status())[0] is not None

            await _until(written, "no backup written")
        finally:
            await cancel(task)
        stamp = (await sgp.get_mem_status())[0]
        assert isinstance(stamp, int)
        machine.flush_fram()
        return stamp

    async def restored(max_age: int) -> "tuple[object, list[int]]":
        module = await _boot(device, cfg_path)
        await _set_clock(module)
        _clock().step(-7200)
        await module.scd30._set_meas_data(_SCD30_READING)
        sgp = module.sgp40
        assert (await sgp.cfgmgr.write_config({"BackupMaxAge": max_age}))[0]
        task = sgp.start_asy_read()
        try:

            async def initialised() -> bool:
                return bool(sgp._voc_init == 1)

            await _until(initialised, "no SGP40 init")
            sgp._read_event.set()

            async def decided() -> bool:
                entry = (await sgp.get_error_counter())["SGP40"]
                return (await sgp.get_mem_status())[1] is not None or code("W", "SGP_BACKUP_AGE") in list(entry["ErrNum"])

            await _until(decided, "the restore neither ran nor was refused")
        finally:
            await cancel(task)
        entry = (await sgp.get_error_counter())["SGP40"]
        return (await sgp.get_mem_status())[1], [entry["ErrNum"][i] for i in range(len(entry["ErrNum"])) if entry["ErrType"][i] == "W"]

    stamp = run_timed(backed_up(), 3 * _WAIT_TIMEOUT_S)
    refused, warnings = run_timed(restored(60), 3 * _WAIT_TIMEOUT_S)
    assert (refused, warnings.count(code("W", "SGP_BACKUP_AGE"))) == (None, 1), (refused, warnings)
    kept, _warnings = run_timed(restored(0), 3 * _WAIT_TIMEOUT_S)
    assert kept == stamp, f"BackupMaxAge 0 restored {kept}, not the backup of {stamp}"


def test_cettime_follows_the_clock_across_the_march_switch_both_ways() -> None:
    # Stepped to 00:59 UTC of the switch day, across 01:00 and back: cettime() answers CET, then CEST, then CET.
    device = generated_devices()[0]

    async def scenario() -> "list[tuple[int, int]]":
        module = await _boot(device)
        await _set_clock(module)
        offsets = await module.ntp.cfgmgr.get_dict(["GMTOffset", "DSTOffset"])
        assert offsets is not None
        cet, cest = offsets["GMTOffset"], offsets["GMTOffset"] + offsets["DSTOffset"]
        clock = _clock()
        clock.set_wall(_DST_START - 60)
        seen: list[tuple[int, int]] = []
        for step, expected in ((0, cet), (120, cest), (-120, cet)):
            clock.step(step)
            local = await module.ntp.cettime()
            assert local is not None, "cettime() answered nothing on a set clock"
            seen.append((_wall_clock.epoch_seconds(*local[:6]) - clock.time(), cast("int", expected)))
        return seen

    for got, expected in run_timed(scenario(), _WAIT_TIMEOUT_S):
        assert abs(got - expected) <= 1, f"cettime() offset {got}, not {expected}"


def test_a_year_forward_then_two_back_leave_sync_and_its_age_on_the_ticks() -> None:
    # Synced against the responder at t0, the clock stepped a year forward and two back: Synced holds and LastSyncAge
    # counts the ticks since t0 only (its age is measured, never read off the wall clock).
    async def scenario(module: "ModuleType") -> "tuple[object, object, int]":
        await _until(module.ntp.ntp_issynced, "no first sync")
        t0 = time.ticks_ms()
        _clock().step(365 * 86400)
        _clock().step(-2 * 365 * 86400)

        async def aged() -> bool:
            age = (await module.ntp.get_data()).LastSyncAge
            return age is not None and age >= 2

        await _until(aged, "LastSyncAge never counted")
        data = await module.ntp.get_data()
        return data.Synced, data.LastSyncAge, time.ticks_diff(time.ticks_ms(), t0) // 1000

    synced, age, elapsed = _booted(generated_devices()[0], NtpResponder(_PORTS.next()), scenario)
    assert synced is True, "a clock step cleared Synced"
    assert isinstance(age, int) and abs(age - elapsed) <= 1, f"LastSyncAge {age} after {elapsed} s of ticks"


def test_the_first_sync_sets_a_boot_default_clock_and_restarts_its_age() -> None:
    # The responder silent through the boot, the clock at rp2's power-up default; then serving: the client's next
    # attempt (its own retry path) sets the clock to the served time and LastSyncAge starts from 0.
    responder = NtpResponder(_PORTS.next())
    responder.mode = "silent"

    async def scenario(module: "ModuleType") -> "tuple[int, int, object]":
        async def backed_off() -> bool:  # the boot's own attempt over, as tests/test_digital_twin_ntp.py waits it out
            return bool(module.ntp._retry_wait_s == 2 * module.ntp._retry_s)

        _clock().set_wall(_RP2_BOOT_CLOCK)
        await _until(backed_off, "the boot's attempt never failed and doubled its step")
        responder.mode = "serve"
        await _ticks_to_attempt(module, responder)
        await _until(module.ntp.ntp_issynced, "no sync after the responder returned")
        return _clock().time(), int(time.time()), (await module.ntp.get_data()).LastSyncAge

    wall, host, age = _booted(generated_devices()[0], responder, scenario)
    assert abs(wall - host) <= 1, f"the sync left the clock at {wall}, not the served {host}"
    assert age in (0, 1), f"LastSyncAge {age} right after the sync"


def test_an_ntp_offset_change_clears_synced_and_the_next_sync_applies_it() -> None:
    # NTPOffset changed through the client's own config-apply path: Synced false at once, and the next sync sets the
    # clock to the served time shifted by the offset.
    offset = 3600

    async def scenario(module: "ModuleType") -> "tuple[bool, int, int]":
        await _until(module.ntp.ntp_issynced, "no first sync")
        results = await module.webserver._apply_settings_groups("networking", {"NTPOffset": offset})
        assert results == {"NTPOffset": "Valid"}, results
        cleared = not await module.ntp.ntp_issynced()
        await _until(module.ntp.ntp_issynced, "no sync under the new offset")
        return cleared, _clock().time(), int(time.time())

    cleared, wall, host = _booted(generated_devices()[0], NtpResponder(_PORTS.next()), scenario)
    assert cleared, "the offset change left Synced true"
    assert abs(wall - (host + offset)) <= 1, f"the clock reads {wall}, not the served time shifted by {offset}"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
