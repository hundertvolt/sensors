"""The twin's local NTP responder and a generated device syncing against it: the responder's replies and knobs, a first
sync, an outage and its recovery, and each failure reply reaching the client's catalog code (SPECIFICATION.md C.7.2)."""

import asyncio
import json
import select
import socket
import struct
import sys
import time

sys.path.insert(0, "ext")  # the vendored ext/microdot.py that every generated device module imports
sys.path.insert(0, "digital_twin")  # the twin's machine, network and neopixel fakes, ahead of tests/'s own
sys.path.insert(0, "digital_twin/unixport")  # the responder's and the UDP shim's fake-free directory

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

prewarm_poll_set()  # before any poll object is registered (unix_port_poll_prewarm.py)
patch_asy_udp_socket_for_unix_port()  # before any UDPSocket exists (_unix_port_udp_addr_shim.py)

import _ntp_responder  # noqa: E402 - imported after the prewarm and the UDP shim
import _twin_common  # noqa: E402 - imported after the prewarm and the UDP shim
import _unix_port_udp_addr_shim  # noqa: E402 - imported after the prewarm and the UDP shim
import _wall_clock  # noqa: E402 - imported after the prewarm and the UDP shim
import machine  # noqa: E402 - imported after the prewarm and the UDP shim
import microtest  # noqa: E402 - imported after the prewarm and the UDP shim
import network  # noqa: E402 - imported after the prewarm and the UDP shim
import run_generic_integration as runner  # noqa: E402 - imported after the prewarm and the UDP shim
from _async_harness import cancel_all, run_timed  # noqa: E402 - imported after the prewarm and the UDP shim
from _digital_twin_construction_scenarios import load_device  # noqa: E402 - imported after the prewarm and the UDP shim
from _error_codes import code  # noqa: E402 - imported after the prewarm and the UDP shim
from _generated_module import boot_entry_watchdog  # noqa: E402 - imported after the prewarm and the UDP shim
from _ntp_responder import NtpResponder  # noqa: E402 - imported after the prewarm and the UDP shim
from _offline_ntp_config import write_responder_ntp_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _port_bands import PortAllocator  # noqa: E402 - imported after the prewarm and the UDP shim
from _src_const import src_const, src_int  # noqa: E402 - imported after the prewarm and the UDP shim
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_devices import device_with, generated_devices, wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim
from _udp_port_redirect import redirect_udp_port  # noqa: E402 - imported after the prewarm and the UDP shim

import asy_ntp_client  # noqa: E402 - imported after the prewarm and the UDP shim
import asy_udp_socket  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_config_manager import config_filename  # noqa: E402 - imported after the prewarm and the UDP shim

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from types import ModuleType
    from typing import TypeVar

    T = TypeVar("T")

microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)

# @tunable l2.ntp_reply_wait_ms = 1000
_REPLY_WAIT_MS = 1000  # a reply on loopback arrives within one responder poll; the bound only ends a lost one
_POLL_MS = 5
# @tunable l2.ntp_run_bound_s = 10.0
_RUN_BOUND_S = 10.0
_REQUEST = b"\x1b" + bytes(47)  # the product's request: LI 0, VN 3, mode 3 (src/asy_ntp_client.py _NTP_REQUEST)

_PORTS = PortAllocator("test_digital_twin_ntp")


async def _ask(port: int, request: bytes = _REQUEST) -> "bytes | None":
    # One request from a plain loopback client; the reply, or None once the wait passed with none.
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.setblocking(False)
    poller = select.poll()
    poller.register(client, select.POLLIN)
    try:
        client.sendto(request, socket.getaddrinfo("127.0.0.1", port)[0][-1])
        for _ in range(_REPLY_WAIT_MS // _POLL_MS):
            if any(event & select.POLLIN for _obj, event in poller.ipoll(0)):
                return client.recv(64)
            await asyncio.sleep_ms(_POLL_MS)
        return None
    finally:
        client.close()


def _booted(device: str, responder: NtpResponder, scenario: "Callable[[ModuleType], Coroutine[object, object, T]]", cfg_path: str, fram_state: "str | None" = None) -> "T":
    # The device's real main() as its boot entry runs it, beside the responder: the config the twin's runner writes,
    # a station to join, the product's port 123 mapped to the responder's and the wall clock installed.
    machine.reset_peripherals()  # a second boot of one test builds its buses again, and finds its radio restarted
    network.reset_test_state()
    machine.configure_fram_state_path(fram_state)
    machine.configure_wiring(wiring_plan(device))
    write_responder_ntp_config(cfg_path)
    with open(config_filename(cfg_path, "WIFI"), "w") as f:
        f.write(json.dumps({"SSID": _SSID}))
    module = load_device(device)
    _wall_clock.install(runner.product_modules())
    earlier = getattr(module, "webserver", None)  # an earlier boot's, until main() constructs its own (the last one)

    async def built() -> bool:
        return getattr(module, "webserver", None) not in (None, earlier)

    async def whole() -> "T":
        with redirect_udp_port(asy_ntp_client, 123, responder.port):
            boot = module.main(watchdog=boot_entry_watchdog(module, device), cfg_path=cfg_path, web_host="127.0.0.1", web_port=0)
            tasks = [asyncio.create_task(responder.serve()), asyncio.create_task(boot)]
            try:
                await _until(built, "no construction")
                return await scenario(module)
            finally:
                await cancel_all(tasks)

    try:
        return run_timed(whole(), 2 * _SYNC_WAIT_TIMEOUT_S)
    finally:
        responder.close()


async def _log(module: "ModuleType", name: str = "NTP") -> "tuple[int, list[int]]":
    # (ErrCount, the used ring slots oldest first) of one module's log.
    entry = (await getattr(module, name.lower()).get_error_counter())[name]
    return entry["ErrCount"], [n for n, kind in zip(entry["ErrNum"], entry["ErrType"]) if kind != "N"]


# ---------------------------------------------------------------------------
# The responder alone: one request over loopback per case
# ---------------------------------------------------------------------------


def test_a_request_gets_a_synchronised_server_reply_at_the_hosts_utc() -> None:
    reply = _served(NtpResponder(_PORTS.next()))
    assert reply is not None and len(reply) == 48, reply
    assert (reply[0] >> 6, (reply[0] >> 3) & 7, reply[0] & 7, reply[1]) == (0, 3, 4, 1)  # LI 0, VN 3, mode 4, stratum 1
    assert abs(_transmit_s(reply) - int(time.time())) <= 2


def test_offset_s_shifts_the_served_time_exactly() -> None:
    responder = NtpResponder(_PORTS.next())
    responder.offset_s = 3600
    reply = _served(responder)
    assert reply is not None
    assert abs(_transmit_s(reply) - int(time.time()) - 3600) <= 2


def test_each_failure_mode_answers_as_its_name_says() -> None:
    floor = src_const("src/asy_ntp_client.py", "_NTP_MIN_PLAUSIBLE_UNIX_TIME")
    assert isinstance(floor, int)
    for mode in ("silent", "unsync", "short", "implausible"):
        responder = NtpResponder(_PORTS.next())
        responder.mode = mode
        reply = _served(responder)
        if mode == "silent":
            assert reply is None, reply
            assert responder.requests == 1  # taken, never answered: an outage
            continue
        assert reply is not None, mode
        if mode == "unsync":
            assert (reply[0] >> 6, reply[1]) == (3, 0), reply[:2]  # LI 3, stratum 0: a Kiss-of-Death reply
        elif mode == "short":
            assert len(reply) == 47
        else:
            assert len(reply) == 48 and _transmit_s(reply) < floor


def test_a_datagram_that_is_no_client_request_is_counted_and_unanswered() -> None:
    responder = NtpResponder(_PORTS.next())
    assert _served(responder, b"\x1c" + bytes(47)) is None  # a mode-4 datagram, not a request
    assert (responder.requests, responder.ignored) == (0, 1)


def test_the_request_counter_saturates_at_the_projects_cap() -> None:
    assert _ntp_responder._COUNTER_CAP == _twin_common.COUNTER_CAP
    responder = NtpResponder(_PORTS.next())
    responder.requests = _twin_common.COUNTER_CAP
    assert _served(responder) is not None
    assert responder.requests == _twin_common.COUNTER_CAP


def test_the_epoch_delta_is_the_clients_own() -> None:
    assert src_const("src/asy_ntp_client.py", "_NTP_EPOCH_DELTA") == _ntp_responder._NTP_EPOCH_DELTA


def test_serving_never_starves_a_task_beside_it() -> None:
    responder = NtpResponder(_PORTS.next())

    async def scenario() -> int:
        task = asyncio.create_task(responder.serve())
        ticks = 0
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < 200:
            await asyncio.sleep_ms(1)
            ticks += 1
        task.cancel()
        return ticks

    try:
        ticks = run_timed(scenario(), _RUN_BOUND_S)
    finally:
        responder.close()
    assert ticks >= 50, ticks  # a 1 ms ticker over 200 ms: the responder's rounds never hold the loop


def test_a_second_responder_on_a_held_port_waits_and_takes_it_once_freed() -> None:
    # One responder per port in a namespace: a second one never answers the holder's clients, and takes the port once
    # the holder closes it, so concurrent runs of one fixed port (the product's 123) serialise instead of interleaving.
    port = _PORTS.next()
    first, second = NtpResponder(port), NtpResponder(port)

    async def scenario() -> "tuple[bytes | None, bytes | None]":
        tasks = [asyncio.create_task(first.serve()), asyncio.create_task(second.serve())]
        held = await _ask(port)
        first.close()
        for _ in range(_REPLY_WAIT_MS // _POLL_MS):  # a datagram sent before the take finds no socket and is dropped
            if second.holding:
                break
            await asyncio.sleep_ms(_POLL_MS)
        taken = await _ask(port)
        for task in tasks:
            task.cancel()
        return held, taken

    try:
        assert first.holding and not second.holding
        held, taken = run_timed(scenario(), _RUN_BOUND_S)
    finally:
        first.close()
        second.close()
    assert held is not None and taken is not None
    assert (first.requests, second.requests) == (1, 1), (first.requests, second.requests)


# ---------------------------------------------------------------------------
# The UDP shim's destination guard: a booted twin's UDP traffic stays on loopback and TEST-NET-1
# ---------------------------------------------------------------------------


def _red_frames(pixel: object) -> int:
    return sum(1 for frame in pixel._pixel.writes if frame[0][0] > 0 and frame[0][1] == 0 and frame[0][2] == 0)  # type: ignore[attr-defined]


def test_a_public_destination_is_refused_counted_and_fails_on_the_products_own_path() -> None:
    before = _unix_port_udp_addr_shim.public_destinations_refused
    assert _write_to(("pool.ntp.org", 123)) is None  # no lookup and no datagram: connect() fails inside src/'s try
    assert _unix_port_udp_addr_shim.public_destinations_refused == before + 1
    assert _unix_port_udp_addr_shim.last_refused == ("pool.ntp.org", 123)


def test_a_malformed_or_public_literal_is_refused_the_same_way() -> None:
    for host in ("127.0.0.256", "192.0.2", "8.8.8.8"):
        before = _unix_port_udp_addr_shim.public_destinations_refused
        assert _write_to((host, 53)) is None, host
        assert _unix_port_udp_addr_shim.public_destinations_refused == before + 1, host


def test_a_send_to_a_refused_address_fails_on_the_products_own_path() -> None:
    async def scenario() -> "int | None":
        sock = asy_udp_socket.UDPSocket(("127.0.0.1", _PORTS.next()), mode="server")
        try:
            return await sock.sendto(b"x", ("1.1.1.1", 53), timeout_ms=100)
        finally:
            await sock.disconnect()

    before = _unix_port_udp_addr_shim.public_destinations_refused
    assert run_timed(scenario(), _RUN_BOUND_S) is None
    assert _unix_port_udp_addr_shim.public_destinations_refused == before + 1



# ---------------------------------------------------------------------------
# A generated device booted against the responder: the boot's first sync, an outage and its recovery, each failure
# ---------------------------------------------------------------------------

# @tunable l2.ntp_sync_wait_timeout_s = 20.0
_SYNC_WAIT_TIMEOUT_S = 20.0  # the network up, one product fetch timeout (5 s), a check tick (10 s) if it came up late
_SYNC_POLL_MS = 50
_TICKS_TO_RETRY = 4  # check ticks fired by hand toward the next attempt: the backoff steps reached here, 20 s and 40 s
_CHECK_S: int = src_int("src/asy_ntp_client.py", "_NTP_CHECK_INTERV")
_SSID = "TestNet"
_scratch = TmpScratch("digital_twin_ntp")


def _served(responder: NtpResponder, request: bytes = _REQUEST) -> "bytes | None":
    # The reply to one request while the responder serves beside it.
    async def scenario() -> "bytes | None":
        task = asyncio.create_task(responder.serve())
        try:
            return await _ask(responder.port, request)
        finally:
            task.cancel()

    try:
        return run_timed(scenario(), _RUN_BOUND_S)
    finally:
        responder.close()


async def _ticks_to_attempt(module: "ModuleType", responder: NtpResponder) -> int:
    # Fires the client's check tick, as its 10 s timer does, until the responder takes a request; how many it took.
    before = responder.requests
    for ticks in range(1, _TICKS_TO_RETRY + 1):
        module.ntp._ntp_timer_trigger_event.set()
        await asyncio.sleep_ms(_SYNC_POLL_MS)
        if responder.requests > before:
            return ticks
    raise AssertionError(f"no attempt within {_TICKS_TO_RETRY} check ticks")


def _transmit_s(reply: bytes) -> int:
    seconds: int = struct.unpack("!I", reply[40:44])[0]
    return seconds - _ntp_responder._NTP_EPOCH_DELTA


async def _until(holds: "Callable[[], Coroutine[object, object, bool]]", what: str) -> None:
    for _ in range(int(_SYNC_WAIT_TIMEOUT_S * 1000) // _SYNC_POLL_MS):
        if await holds():
            return
        await asyncio.sleep_ms(_SYNC_POLL_MS)
    raise AssertionError(f"{what} within {_SYNC_WAIT_TIMEOUT_S} s")


def _write_to(addr: "tuple[str, int]") -> "int | None":
    # One client write through the product's own UDPSocket; None is its handled failure.
    async def scenario() -> "int | None":
        sock = asy_udp_socket.UDPSocket(addr)
        try:
            return await sock.write(b"x", timeout_ms=100)
        finally:
            await sock.disconnect()

    return run_timed(scenario(), _RUN_BOUND_S)


def test_a_booted_device_syncs_at_its_first_sync_with_a_clean_log() -> None:
    # The in-process mirror of the normal-boot check: synced, the product's wall clock on the host's UTC, no entry.
    async def scenario(module: "ModuleType") -> "tuple[int, tuple[int, list[int]]]":
        clock = _wall_clock.installed()
        assert clock is not None
        clock.step(-86400)  # a wrong boot clock, which only the sync puts right
        await _until(module.ntp.ntp_issynced, "no first sync")
        return clock.time(), await _log(module)

    wall, log = _booted(generated_devices()[0], NtpResponder(_PORTS.next()), scenario, _scratch.dir())
    assert abs(wall - int(time.time())) <= 2, wall
    assert log == (0, []), log


def test_an_outage_from_boot_backs_off_and_a_returning_responder_syncs_within_the_step() -> None:
    responder = NtpResponder(_PORTS.next())
    responder.mode = "silent"

    async def scenario(module: "ModuleType") -> "tuple[bool, tuple[int, list[int]], int, int]":
        async def failed() -> bool:
            return (await _log(module))[0] >= 1

        async def backed_off() -> bool:
            return bool(module.ntp._retry_wait_s == 2 * module.ntp._retry_s)

        await _until(failed, "the boot's attempt never failed")
        await _until(backed_off, "the failed unsynced attempt never doubled the step (C.7.2)")
        synced, log, step = await module.ntp.ntp_issynced(), await _log(module), module.ntp._retry_wait_s
        responder.mode = "serve"
        ticks = await _ticks_to_attempt(module, responder)
        await _until(module.ntp.ntp_issynced, "no sync after the responder returned")
        return synced, log, step, ticks

    synced, log, step, ticks = _booted(generated_devices()[0], responder, scenario, _scratch.dir())
    assert (synced, log) == (False, (1, [code("E", "NTP_NO_REPLY")])), (synced, log)
    assert ticks <= step // _CHECK_S, (ticks, step)  # the next attempt within that step


def test_an_sgp40_restore_waits_out_the_outage_and_follows_the_sync() -> None:
    # A timestamped backup from a synced first boot; the second boots into an outage, WaitTimeNTP at its default.
    device = device_with("sgp40", "fram")
    cfg_path = _scratch.dir()
    fram_state = cfg_path + "fram_state.json"

    async def backed_up(module: "ModuleType") -> int:
        async def reading() -> bool:  # past the reader's init, which zeroes the backup counter, and compensated
            return (await module.sgp40.get_data()).Raw is not None and (await module.scd30.get_data()).Hum is not None

        await _until(module.ntp.ntp_issynced, "no first sync")
        await _until(reading, "no SGP40 and SCD30 reading")
        module.sgp40._backup_counter = 59  # the next read cycle reaches the 60-cycle BackupPeriod

        async def written() -> bool:
            return (await module.sgp40.get_mem_status())[0] is not None

        await _until(written, "no backup written")
        stamp: int = (await module.sgp40.get_mem_status())[0]
        return stamp

    stamp = _booted(device, NtpResponder(_PORTS.next()), backed_up, cfg_path, fram_state)
    machine.flush_fram()
    responder = NtpResponder(_PORTS.next())
    responder.mode = "silent"

    async def restored(module: "ModuleType") -> "tuple[object, object, tuple[int, list[int]]]":
        async def failed() -> bool:
            return (await _log(module))[0] >= 1

        await _until(failed, "the boot's attempt never failed")
        waiting = (await module.sgp40.get_mem_status())[1]
        responder.mode = "serve"
        await _ticks_to_attempt(module, responder)

        async def done() -> bool:
            return (await module.sgp40.get_mem_status())[1] is not None

        await _until(done, "no restore after the sync")
        return waiting, (await module.sgp40.get_mem_status())[1], await _log(module, "SGP40")

    waiting, restored_from, sgp_log = _booted(device, responder, restored, cfg_path, fram_state)
    assert waiting is None  # no restore while the responder was silent
    assert restored_from == stamp, (restored_from, stamp)
    assert sgp_log == (0, []), sgp_log  # the wait and a timestamped restore print only


def test_each_failing_reply_leaves_synced_false_with_its_catalog_code() -> None:
    responder = NtpResponder(_PORTS.next())
    responder.mode = "unsync"

    async def scenario(module: "ModuleType") -> "list[tuple[bool, tuple[int, list[int]]]]":
        seen = []
        for count, mode in enumerate(("unsync", "short", "implausible"), 1):
            if count > 1:
                responder.mode = mode
                await _ticks_to_attempt(module, responder)

            async def failed(count: int = count) -> bool:
                return (await _log(module))[0] >= count

            await _until(failed, f"no {mode} failure")
            seen.append((await module.ntp.ntp_issynced(), await _log(module)))
        return seen

    seen = _booted(generated_devices()[0], responder, scenario, _scratch.dir())
    unsync, malformed, implausible = code("W", "NTP_UNSYNC_REPLY"), code("E", "NTP_MALFORMED"), code("E", "NTP_IMPLAUSIBLE")
    assert seen == [(False, (1, [unsync])), (False, (2, [unsync, malformed])), (False, (3, [unsync, malformed, implausible]))], seen


def test_a_lost_sync_keeps_the_local_time_and_the_alert_flashing() -> None:
    # Synced, then the responder silent and the settings hook's resync: the clock was set this boot, so the local time
    # and an alert above its threshold go on (the notification window around the current hour, WarnCO2 below any CO2).
    responder = NtpResponder(_PORTS.next())

    async def scenario(module: "ModuleType") -> "tuple[bool, object, int, bool]":
        notif, ntp = module.notification, module.ntp  # this boot's: _booted() waited out the construction
        await _until(ntp.ntp_issynced, "no first sync")
        local = await ntp.cettime()
        assert local is not None
        on_h, off_h = (local.hour - 1, local.hour - 2) if local.hour >= 2 else (23, local.hour + 2)
        body = {"OnH": on_h, "OnM": 0, "OffH": off_h, "OffM": 0, "FlashDur": 0.5, "WarnCO2": 1}
        results = await module.webserver._apply_settings_groups("notification", body)
        assert set(results.values()) <= {"Valid", "Unchanged"}, results

        async def measured() -> bool:
            return (await module.scd30.get_data()).CO2 is not None

        await _until(measured, "no CO2 reading")
        responder.mode = "silent"
        await ntp.ntp_force_sync()  # the networking group's post-PUT hook: Synced false until the next success
        lost = await ntp.ntp_issynced()
        before = _red_frames(module.neopixel)
        task = notif.start_asy_monitor()  # one fresh monitor cycle, the boot's own sleeping out its FlashInterval
        try:
            async def flashed() -> bool:
                return _red_frames(module.neopixel) > before and bool((await notif.get_data()).Triggered)

            await _until(flashed, "no flash once the sync was lost")
        finally:
            await cancel_all([task])
        return lost, await ntp.cettime(), _red_frames(module.neopixel) - before, await ntp.ntp_issynced()

    lost, local, flashes, synced = _booted(device_with("notification", "scd30"), responder, scenario, _scratch.dir())
    assert lost is False and synced is False
    assert local is not None  # cettime() still answers
    assert flashes > 0


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
