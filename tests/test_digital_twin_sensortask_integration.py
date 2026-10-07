"""Middle integration tier: the real sensortask_wozi object graph against real digital_twin buses,
driving real REST traffic while starting only the tasks each test needs (the task-supervisor
section below excepted). Deliberately wozi-only - SPECIFICATION.md Part E.2.1 says why."""

import asyncio
import gc
import json
import select
import socket
import sys
import time

sys.path.insert(0, "ext")  # same convention as _sensortask_scenarios.py's own comment - reaches the
# real, vendored ext/microdot.py that sensortask_wozi.py transitively imports.
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import _http_client
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

# Before any poll object is registered: the Unix port's pollfds growth corrupts non-fd entries
# already in it, a segfault rather than a failure (digital_twin/README.md "Known gaps").
prewarm_poll_set()

# Must run before UDPSocket is constructed (CaptiveDNS, inside WifiService.__init__ below): this
# Unix-port build rejects a plain (host, port) tuple in bind()/connect()/sendto() (SPECIFICATION.md
# Part A.10), a twin-side workaround since UDPSocket's own addr is correct production code.
patch_asy_udp_socket_for_unix_port()

# digital_twin's own fake machine module - configure_fram_state_path()/flush_fram(), used only by
# this file's own reboot-survival section below.
import machine  # noqa: E402
import sensortask_wozi  # noqa: E402
import unix_port_unretrieved_report  # noqa: E402
from _shared_rest_roundtrip import assert_sensor_payload_not_self_wrapped  # noqa: E402
from _tmp_scratch import TmpScratch  # noqa: E402

import asy_ntp_client  # noqa: E402  # its `time` is swapped for rp2's 8-field gmtime() in the notification-window section
import asy_system_service  # noqa: E402  # its asyncio is swapped for a fast-sleeping view in the unretrieved-exception section
from asy_scd30_driver import SCD30  # noqa: E402  # seeds a reading: the notification-window and reboot-survival sections below
from asy_sgp40_driver import SGP40  # noqa: E402  # used only by this file's own boot-race regression test below

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

# @tunable l2.sensortask_integration_wait_poll_s = 0.25
_WAIT_POLL_S = 0.25
# @tunable l2.sensortask_integration_run_bound_s = 10.0
_RUN_BOUND_S = 10.0
# @tunable l2.sensortask_integration_long_run_bound_s = 15.0
_LONG_RUN_BOUND_S = 15.0
# @tunable l2.sensortask_integration_wait_timeout_s = 5.0
_WAIT_TIMEOUT_S = 5.0
# @tunable l2.sensortask_integration_restart_wait_timeout_s = 6.0
_RESTART_WAIT_TIMEOUT_S = 6.0
# @tunable l2.sensortask_integration_supervisor_run_bound_s = 20.0
_SUPERVISOR_RUN_BOUND_S = 20.0
# @tunable l2.sensortask_integration_hotspot_wait_timeout_s = 25.0
_HOTSPOT_WAIT_TIMEOUT_S = 25.0
# @tunable l2.sensortask_integration_bind_poll_s = 0.01
_BIND_POLL_S = 0.01
# @tunable l2.sensortask_integration_hotspot_run_bound_s = 35.0
_HOTSPOT_RUN_BOUND_S = 35.0
# @tunable l2.sensortask_integration_reboot_run_bound_s = 30.0
_REBOOT_RUN_BOUND_S = 30.0


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(coro)


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("dtsi")
_next_port = 19100  # a fixed, non-privileged test-only range - never the production 8080 default,
# never the real 0.0.0.0:80 - a fresh port per test avoids any TIME_WAIT reuse flakiness rather
# than relying on one shared port across every test_* function in this one process.


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


def _next_test_port() -> int:
    global _next_port
    _next_port += 1
    return _next_port


def _wiring_plan(device: str) -> "dict[str, Any]":
    with open(f"build/generated_src/sensortask_{device}_wiring_plan.json") as f:
        plan: dict[str, Any] = json.load(f)
    return plan


async def _boot(port: int) -> None:
    # configure_wiring() explicitly, every call: every twin I2C/SPI construction reads the shared
    # machine._wiring_plan global ("last call before construction wins"), and this file's own construction-
    # across-every-device section, sharing this process, configures a different plan.
    #
    # MicroPython's globals() does not preserve definition order, so relying on "the wozi tests always run
    # first" would be an order-dependent hazard rather than a guarantee.
    machine.configure_wiring(_wiring_plan("wozi"))
    await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)


async def _start_webserver() -> "asyncio.Task[None]":
    assert sensortask_wozi.webserver is not None
    task = sensortask_wozi.webserver.get_task_starters()[0]()
    # WP1/CLAUDE.md's implicit-FRAM-wiring rule made webserver.pr real-FRAM-backed whenever the device wires
    # FRAM, so _serve_loop() now awaits a real self.pr.setup() - a real chunk read/write - before start_server(),
    # not the instant no-op a RAM-only logger's setup() was.
    #
    # Measured directly against this file's real twin fakes: consistently ready within ~400ms, so 1.0s keeps
    # a ~2.5x margin rather than a bare-minimum guess. test_asy_webserver_service.py's F.8 test keeps its
    # 0.05s bound because its own fixture is never constructed with fram=.
    await asyncio.sleep(1.0)
    return task


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def _make_dns_query(labels: "list[str]", query_id: bytes = b"\x12\x34") -> bytes:
    # Mirrors tests/test_asy_captive_dns.py's own make_query(): a minimal, well-formed standard-query
    # datagram DNSQuery.__init__ accepts (RFC 1035 section 4.1.1/4.1.2).
    question = b"".join(bytes([len(label)]) + label.encode("ascii") for label in labels)
    question += b"\x00\x00\x01\x00\x01"
    header = query_id + b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    return header + question


async def _query_dns_and_get_answer_ip(query: bytes, timeout_s: float = 5.0) -> str:
    # Genuine end-to-end DNS round trip against the real conn._dns_server_task's UDPSocket, bound at
    # ("0.0.0.0", 53). Uses the same non-blocking socket + select.poll() + bounded ticks_ms() shape as
    # test_asy_udp_socket.py's AdversarialPeer, since a bounded non-blocking poll is what the rest of the file uses.
    peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    peer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    peer.setblocking(False)
    data: bytes = b""
    try:
        # sendto() rejects a plain (host, port) tuple here; the resolved getaddrinfo() address is
        # required instead (same quirk tests/test_asy_udp_socket.py's make_addr() works around; SPECIFICATION.md F.7 row 1).
        addr = socket.getaddrinfo("127.0.0.1", 53)[0][-1]
        peer.sendto(query, addr)
        poller = select.poll()
        poller.register(peer, select.POLLIN)
        t0 = time.ticks_ms()
        ready = False
        while True:
            # Check the actual per-fd event flags, not just ipoll()'s truthiness: an entry can
            # carry POLLERR/POLLHUP with no POLLIN set, which otherwise raised OSError(EAGAIN).
            for _, event in poller.ipoll(0):
                if event & select.POLLIN:
                    ready = True
            if ready:
                # recvfrom(), not recv(): the same choice tests/test_asy_udp_socket.py's own
                # AdversarialPeer.recv() makes for this unconnected socket.
                data, _ = peer.recvfrom(512)
                break
            if time.ticks_diff(time.ticks_ms(), t0) > int(timeout_s * 1000):
                raise OSError("DNS query timed out waiting for a reply from the real CaptiveDNS")
            await asyncio.sleep_ms(5)
    finally:
        peer.close()
    # DNSQuery.response()'s fixed layout: the answer's 4 raw IPv4 bytes are always the last 4
    # bytes of the packet (tests/test_asy_captive_dns.py confirms this byte-for-byte).
    return ".".join(str(b) for b in data[-4:])


async def _wait_until_async(predicate: "Callable[[], Coroutine[Any, Any, bool]]", timeout_s: float, interval_s: float = _WAIT_POLL_S) -> bool:
    # _wait_until() below for a predicate that must await (a module's get_data()).
    elapsed = 0.0
    while elapsed < timeout_s:
        if await predicate():
            return True
        await asyncio.sleep(interval_s)
        elapsed += interval_s
    return await predicate()


async def _wait_until(predicate: "Callable[[], bool]", timeout_s: float, interval_s: float = _WAIT_POLL_S) -> bool:
    # Bounded polling for a real multi-second state transition (mode switches, supervisor cycles).
    # Counts poll iterations, not wall clock: under CPU starvation a wall-clock bound would fail
    # sooner, not later, since every sleep overruns.
    elapsed = 0.0
    while elapsed < timeout_s:
        if predicate():
            return True
        await asyncio.sleep(interval_s)
        elapsed += interval_s
    return predicate()


# ---------------------------------------------------------------------------
# Boot against the real twin buses - parametrized across all 6 real devices, see the
# "Construction across every real device" section near the end of this file.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Every REST endpoint, plus the static site, over a real HTTP round trip - wozi-scoped, as this file's
# module docstring explains. A dedicated test in the "Construction across every real device" section re-
# checks the GET /measurements and /sensors shape parametrized across all 6 devices.
# ---------------------------------------------------------------------------


def test_every_get_endpoint_is_reachable_over_real_http_and_shaped_correctly() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            # Shared shape with the mock's own equivalent check (tests/_shared_rest_roundtrip.py) -
            # regression guard for the {name: {name: {...}}} self-wrapping bug (see
            # asy_webserver_service.py's comments).
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/measurements")
            assert res.status_code == 200
            assert_sensor_payload_not_self_wrapped(res.json(), {"SCD30", "BMP3XX", "SGP40"})

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/sensors")
            assert res.status_code == 200
            assert_sensor_payload_not_self_wrapped(res.json(), {"SCD30", "BMP3XX", "SGP40"})

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/networking")
            assert res.status_code == 200
            # Regression coverage for a real bug this file's own testing found and
            # src/asy_webserver_service.py's _cfg_values() now fixes: every /networking
            # field is sourced from a nested-shaped module (conn/ntp), so this used to come back {}.
            assert res.json() == {
                "SSID": "",
                "PW": "********",
                "Country": "DE",
                "Hostname": "SensorStationWozi",  # devices/wozi.toml's own [device].hostname, injected by buildgen
                "LEDWifiOn": True,
                "NTPHost": "pool.ntp.org",
                "NTPOffset": 0,
                "NTPInterval": 12,
            }

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/system")
            assert res.status_code == 200
            # DebugLevel is sourced from sysfunct (flat), GMTOffset/DSTOffset from ntp (nested), the same
            # fix as /networking above. "build" is the one extra key (SPECIFICATION.md Part L.7's version
            # strings plus build date), checked for shape only.
            #
            # The exact values cannot be cross-checked against buildgen from a MicroPython-run test,
            # buildgen being host-CPython-only tooling.
            system_body = res.json()
            build_info = system_body.pop("build")
            assert system_body == {"DebugLevel": 0, "GMTOffset": 3600, "DSTOffset": 3600}
            assert isinstance(build_info["FirmwareVersion"], str) and build_info["FirmwareVersion"]
            assert isinstance(build_info["WebsiteVersion"], str) and build_info["WebsiteVersion"]
            assert isinstance(build_info["BuildDate"], str) and build_info["BuildDate"]

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/notification")
            assert res.status_code == 200
            # notification.get_dict_cfg() is nested-shaped too - same fix as /networking above.
            body = res.json()
            assert body["WarnCO2"] == 1600
            assert body["WarnVOC"] == 350
            assert body["WarnHum"] == 65.0

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/status")
            assert res.status_code == 200
            assert set(res.json().keys()) == {"networking", "system", "notification", "sensors", "errcount"}
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=_RUN_BOUND_S)


def test_static_site_is_served_over_real_http() -> None:
    # See SPECIFICATION.md Part A.9 - the frozen_html website, served by WebserverService's own
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

    run_timed(scenario(), timeout_s=_RUN_BOUND_S)


def test_put_round_trips_through_a_real_twin_backed_driver_over_real_http() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "PUT", "/notification", {"WarnCO2": 1800})
            assert res.status_code == 200
            assert res.json()["result"] == {"WarnCO2": "Valid"}
            assert sensortask_wozi.notification is not None
            # await directly, not via run() - already inside scenario()'s own event loop
            # (run_timed()'s asyncio.run()); a nested asyncio.run() call here segfaulted the real
            # interpreter instead of raising a clean error (found via this exact bug, the hard way).
            assert await sensortask_wozi.notification.cfgmgr.get_dict(["WarnCO2"]) == {"WarnCO2": 1800}
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=_RUN_BOUND_S)


def test_reset_errors_over_real_http_is_not_undone_by_a_fram_loggers_later_setup() -> None:
    # Twin-tier form of SPECIFICATION.md Part C.7's boot-window contract, over a real socket against the
    # real twin FRAM chip. Only the webserver task is started, exactly like the boot window it models: no
    # sensor task's pr.setup() has run, so the chunk still holds the previous boot's history.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.sgp40 is not None
        sgp = sensortask_wozi.sgp40
        await sgp.pr.setup()
        await sgp.pr.err_s("simulated", errno=99)
        sgp.pr.initialized = False  # bytes on the real twin chip, RAM side not yet set up
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "PUT", "/status", {"ResetErrors": True})
            assert res.status_code == 200
            await sgp.pr.setup()  # ... and only now does _init_sgp() get there
            log = await sgp.get_error_counter()
            assert log["SGP40"]["ErrCount"] == 0
            assert 99 not in log["SGP40"]["ErrNum"], "setup() restored the pre-reset history over a reset that returned 200"
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=_RUN_BOUND_S)


def test_sgp40_reading_before_scd30_has_measured_yet_logs_no_bogus_error() -> None:
    # Regression test for the SGP40 boot-race false error (SPECIFICATION.md Part C.14.2) against the real
    # wozi wiring rather than a fake stand-in - the exact object graph the bug was found through, a real
    # digital-twin CI failure on the dev matrix leg's Run 5c.
    #
    # Deliberately does NOT pre-seed scd30's measurement data the way every other SGP40 test here does: the
    # point is to let the real startup race happen, with scd30's Temp/Hum fields still None when sgp40 reads
    # them.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.sgp40 is not None and sensortask_wozi.scd30 is not None
        sgp = sensortask_wozi.sgp40
        assert (await sensortask_wozi.scd30.get_data()).Temp is None  # the race precondition holds
        await sgp.pr.setup()
        buf, serialize, deserialize, _cfg_values = await sgp._check_storage()
        data, compensated, _serialized = await sgp._read_sgp(buf, serialize=serialize, deserialize=deserialize)
        assert compensated is False  # scd30 genuinely hasn't measured yet - real, expected timing
        assert data == SGP40(None, None, None, None)
        log = await sgp.get_error_counter()
        assert log["SGP40"]["ErrCount"] == 0, f"expected startup jitter must not log any E/W entry ({log!r})"

    run_timed(scenario(), timeout_s=_RUN_BOUND_S)


def test_put_pause_time_round_trips_and_counts_down_over_real_http() -> None:
    # The special-case endpoint pairing this restores: PUT /notification sets the override countdown, GET
    # /status reports its current value. PauseTime is deliberately excluded from GET /notification's flat
    # settings, so it stays in the same polling/non-polling split every other live field follows.
    #
    # Exercises the real _pause_loop() background task decrementing the value over real wall-clock
    # time, not just the value being stored.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.notification is not None
        tasks = [starter() for starter in sensortask_wozi.notification.get_task_starters()]
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
            for _ in range(20):  # bounded poll, well past the real ~1s-per-tick _pause_loop() loop
                await asyncio.sleep(0.5)
                res = await _http_client.fetch("127.0.0.1", port, "GET", "/status")
                current = res.json()["notification"]["PauseTime"]
                assert current <= last  # never increases - a real, monotonic countdown
                last = current
                if current == 0:
                    reached_zero = True
                    break
            assert reached_zero, "PauseTime never reached 0 - the real _pause_loop() task isn't decrementing it"
        finally:
            for task in tasks:
                await _cancel(task)

    run_timed(scenario(), timeout_s=_LONG_RUN_BOUND_S)


def test_sensors_put_round_trips_a_real_scd30_field_over_real_http() -> None:
    # Regression test from baseline verification: this file never exercised PUT /sensors at all before, and
    # that real-HTTP path is what first surfaced SCD30_Reader's missing get_cfg_schema() as a real 500.
    #
    # SCD30 specifically, since it is the one sensors=-registered module that is a plain SensorReader with
    # no local cfgmgr, unlike SGP40/BMP3XX, which would never have caught this gap.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "PUT", "/sensors", {"SCD30": {"MeasInterval": 4}})
            assert res.status_code == 200
            assert res.json()["result"] == {"SCD30": {"MeasInterval": "Valid"}}
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=_RUN_BOUND_S)


# ---------------------------------------------------------------------------
# The notification window across midnight: the real coordinator, the real ntp.cettime() clock and the real
# pixel, one monitor cycle per window; settings applied through the path PUT /notification calls.
# ---------------------------------------------------------------------------

# @tunable l2.sensortask_integration_window_wait_s = 10.0
_WINDOW_WAIT_S = 10.0


class _Rp2Gmtime:
    # The NTP client's `time` here: cettime() checks for rp2's 8-field gmtime(), this Unix port's has 9, so
    # without it the twin never has a local time (tests/test_asy_ntp_client.py's cettime() section).
    def gmtime(self, *secs: int) -> "tuple[int, ...]":
        return tuple(time.gmtime(*secs))[:8]

    def mktime(self, t: "tuple[int, ...]") -> int:
        return time.mktime(t)

    def time(self) -> int:
        return time.time()


def _red_frames(frames: "list[list[tuple[int, ...]]]") -> "list[list[tuple[int, ...]]]":
    return [frame for frame in frames if frame[0][0] > 0 and frame[0][1] == 0 and frame[0][2] == 0]


def test_the_notification_window_spanning_midnight_flashes_red() -> None:
    port = _next_test_port()
    real_time = asy_ntp_client.time  # type: ignore[attr-defined]  # its imported `time`, read to restore it
    asy_ntp_client.time = _Rp2Gmtime()  # type: ignore[attr-defined, assignment]  # a stand-in for the module's time

    async def scenario() -> None:
        await _boot(port)
        notif, ntp, pixel = sensortask_wozi.notification, sensortask_wozi.ntp, sensortask_wozi.neopixel
        scd30, webserver = sensortask_wozi.scd30, sensortask_wozi.webserver
        assert notif is not None and ntp is not None and pixel is not None and scd30 is not None and webserver is not None
        await ntp._set_synced(value=True)  # the twin has no NTP server; the clock itself is the host's
        local = await ntp.cettime()
        assert local is not None
        hour = local.hour
        # On later than Off, with the current hour (and the next) strictly inside, never on a bound.
        on_h, off_h = (hour - 1, hour - 2) if hour >= 2 else (23, hour + 2)
        cfg = await notif.cfgmgr.get_dict(["WarnCO2"])
        assert cfg is not None
        warn_co2 = cfg["WarnCO2"]
        assert isinstance(warn_co2, int)
        await scd30._set_meas_data(SCD30(warn_co2 + 100, 22.0, 45.0, None, None, None, None, None))

        async def apply_window(on: int, off: int) -> None:
            body = {"OnH": on, "OnM": 0, "OffH": off, "OffM": 0, "FlashDur": 0.5}
            results = await webserver._apply_settings_groups("notification", body)
            assert set(results.values()) <= {"Valid", "Unchanged"}, results
            assert await notif.cfgmgr.get_dict(["OnH", "OffH"]) == {"OnH": on, "OffH": off}

        async def triggered() -> bool:
            return bool((await notif.get_data()).Triggered)

        async def not_triggered() -> bool:
            return not await triggered()

        await apply_window(on_h, off_h)
        tasks = [pixel.start_asy_signal(), notif.start_asy_monitor()]
        try:
            assert await _wait_until(lambda: len(_red_frames(list(pixel._pixel.writes))) > 0, _WINDOW_WAIT_S), (
                f"no red frame with the window {on_h}:00-{off_h}:00 around local {hour}:{local.minute:02d}"
            )
            assert await _wait_until_async(triggered, _WINDOW_WAIT_S), "the cycle that flashed never reported Triggered"
            await _cancel(tasks.pop())  # the monitor now sleeps its whole FlashInterval; the next window gets a fresh cycle
            assert await _wait_until(lambda: not pixel._start_signal_event.is_set(), _WINDOW_WAIT_S)
            seen = len(pixel._pixel.writes)

            await apply_window(off_h, on_h)  # the complementary, same-day window: the current hour is outside
            tasks.append(notif.start_asy_monitor())
            assert await _wait_until_async(not_triggered, _WINDOW_WAIT_S), "a cycle outside the window reported Triggered"
            assert _red_frames(list(pixel._pixel.writes)[seen:]) == [], "a cycle outside the window flashed"
        finally:
            for task in tasks:
                await _cancel(task)

    try:
        run_timed(scenario(), timeout_s=3 * _WINDOW_WAIT_S)
    finally:
        asy_ntp_client.time = real_time  # type: ignore[attr-defined]


# The real-bus-fault test moved into the "Construction across every real device" section near the end of
# this file (SPECIFICATION.md Part L.4), parametrized across all 6: SGP40 is fixed-address (0x59)
# everywhere, but which bus it is wired to varies, so the parametrized version resolves it from the plan.


# ---------------------------------------------------------------------------
# Watchdog escalation - a short, real, fully-supervised run (owner, 2026-08-13: an automated assertion
# *and* a manually observable run - the manual side lives in digital_twin/run_generic_integration.py
# (--module sensortask_wozi --wiring-plan ... --device wozi), this is the automated side).
#
# Deliberately does NOT drive this through main()/start_and_check_tasks(). MicroPython's globals() does not
# preserve definition order, so "the last test in the file" is not the last test to run, and
# cancelling start_and_check_tasks() cancels only its supervisor, never the tasks it started.
#
# main_task.cancel() then only cancelled the outer wrapper, leaving every real task it had started running
# for the rest of the process. Across the other tests' repeated build_system() calls, those orphaned
# references starved the Unix-port heap - a real MemoryError once, and a hard segfault once.
#
# So this starts exactly the same real task starters main() would, keeping every one in a list this test
# owns and cancels in `finally` - the controlled pattern _start_webserver() already uses, extended to all of
# them.
#
# It runs its own small watchdog-feed loop rather than start_and_check_tasks()'s, which
# tests/test_asy_system_service.py already covers: the job here is only whether the real concurrent tasks ever
# block the event loop long enough to starve a feed loop running alongside them.
# ---------------------------------------------------------------------------


# @tunable l2.wdt_overrun_wait_s = 9.0
_WDT_OVERRUN_WAIT_S = 9.0


async def _feed_watchdog_periodically(watchdog: "machine.WDT") -> None:
    while True:
        watchdog.feed()
        await asyncio.sleep(1.0)


def test_watchdog_is_never_starved_while_every_real_task_runs_concurrently() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.watchdog is not None and sensortask_wozi.sysfunct is not None
        await sensortask_wozi.sysfunct.start_timers(sensortask_wozi._collect_trigger_starters(), sensortask_wozi._collect_timer_starters())
        # Each starter already returns its own asyncio.Task (asy_system_service.py's own _start_task()
        # calls them exactly this way - `return starter()`, no extra create_task() wrapping).
        tasks = [starter() for starter in sensortask_wozi._collect_task_starters()]
        tasks.append(asyncio.get_event_loop().create_task(_feed_watchdog_periodically(sensortask_wozi.watchdog)))
        try:
            await asyncio.sleep(_WDT_OVERRUN_WAIT_S)  # just over wdt.timeout_ms (8000 ms) - long enough that
            # a real, unintended stall (not just this test's own feed loop existing) is what keeps
            # the count at 0, not merely "not enough wall-clock time has passed yet".
            assert sensortask_wozi.watchdog.would_have_triggered_count == 0
        finally:
            for task in tasks:
                await _cancel(task)

    run_timed(scenario(), timeout_s=_LONG_RUN_BOUND_S)


# ---------------------------------------------------------------------------
# Task-supervisor restart, end to end: a real task drawn from the REAL, full _collect_task_starters() list -
# build_system()'s own object graph, not a synthetic list - actually dying and being rediscovered and
# restarted by SystemService.start_and_check_tasks()'s real supervisor loop.
#
# Via the real get_task_starters() indirection, not a fake of the supervisor. The one test here that starts
# the real full task list through the real supervisor rather than a hand-picked subset.
# ---------------------------------------------------------------------------


def test_start_and_check_tasks_restarts_a_real_dead_task_from_the_real_full_task_list() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.sysfunct is not None and sensortask_wozi.bmp3xx is not None
        sysfunct = sensortask_wozi.sysfunct
        task_starters = sensortask_wozi._collect_task_starters()  # the REAL, full list - every
        # constructed module's own get_task_starters(), exactly what main() itself would use.

        started: dict[int, list[Any]] = {}  # values are asyncio.Task[Any] | None - real _start_task()'s own return type
        from asy_system_service import SystemService

        real_start_task = SystemService._start_task

        async def _tracking_start_task(self: "SystemService", starter: "Callable[[], asyncio.Task[Any]]", n: "int") -> "asyncio.Task[Any] | None":
            # Observes the real supervisor's own real task-(re)start calls without changing its
            # behavior at all - the same non-invasive class-method-wrap convention
            # _sensortask_scenarios.py's own FRAM-chunk-order scenario already uses.
            task = await real_start_task(self, starter, n)
            started.setdefault(n, []).append(task)
            return task

        SystemService._start_task = _tracking_start_task  # type: ignore[method-assign]
        supervisor_task = asyncio.get_event_loop().create_task(sysfunct.start_and_check_tasks(task_starters))
        try:
            # bmp3xx.start_asy_trigger's task is a real event-wait loop with no I/O and no Timer armed here
            # - a side-effect-free task to kill and watch get restarted. The restart logic only ever checks
            # task.done(), never which task died, so the pick is representative.
            target_idx = task_starters.index(sensortask_wozi.bmp3xx.start_asy_trigger)
            assert await _wait_until(lambda: target_idx in started, timeout_s=_WAIT_TIMEOUT_S), (
                "the real task was never started by the real supervisor at all"
            )
            assert len(started[target_idx]) == 1
            first_task = started[target_idx][0]
            assert first_task is not None and not first_task.done()

            first_task.cancel()  # a real task genuinely ending - the same observable state
            # (task.done() == True) a real crash would leave behind; start_and_check_tasks() only
            # ever inspects .done(), never *why* a task ended.
            assert await _wait_until(lambda: len(started[target_idx]) == 2, timeout_s=_RESTART_WAIT_TIMEOUT_S), (
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
            # Defensive: the real _connect_loop task can independently reach hotspot activation and start its
            # own CaptiveDNS task within this window. The loop above does not cancel it, being spawned inside
            # WifiService, and left running it would hold UDP port 53 into the next section.
            if sensortask_wozi.conn is not None and sensortask_wozi.conn._dns_server_task is not None:
                await _cancel(sensortask_wozi.conn._dns_server_task)
            # This starts the REAL full task list, twice for the one restarted - a known failure mode on
            # this file's shared heap otherwise, where orphaned task references starved a later
            # build_system() with a real MemoryError before this collect() was added.
            gc.collect()

    run_timed(scenario(), timeout_s=_SUPERVISOR_RUN_BOUND_S)


# ---------------------------------------------------------------------------
# Unretrieved task exceptions on the twin: the PC tier's report, installed by microtest before this file ran,
# stays installed over the real start_and_check_tasks(), and a supervised task's death reaches the console at
# DebugLevel 0, death after death, with the heap where it was (SPECIFICATION.md Parts F.1 and I.4(e)).
# ---------------------------------------------------------------------------

_STATUS_DEATHS = 10
_DECAY_PASSES = 110  # clean supervisor passes between two deaths: each decays the restart budget by one, a death adds 100
_PASS_YIELD_BOUND = 20000  # loop yields allowed for one wait below; a pass costs a few with the supervisor's fast sleep
# The collected heap across the deaths, in-loop with every real task live: measured within 1.1 KB at both GC stages,
# while keeping each dead task and its exception measured 3.6 KB over the ten (2026-10-07).
_HEAP_DRIFT_BYTES = 2048


class _StatusFault:
    # Stands in for SystemService._uptime: every read raises, so the status task dies at its next wake-up.
    def read(self) -> int:
        raise RuntimeError("injected status fault")


class _FastSupervisorAsyncio:
    # asy_system_service's view of asyncio, its sleeps reduced to one yield, so the supervisor's two-second pass
    # takes one; every other module keeps the real sleeps. While `hold` is set the supervisor parks in its sleep.
    def __init__(self) -> None:
        self.hold = False
        self.parked = False
        self._release = asyncio.Event()

    async def sleep(self, _seconds: float) -> None:
        if self.hold:
            self.parked = True
            await self._release.wait()
            self._release.clear()
            self.parked = False
        else:
            await asyncio.sleep(0)

    async def sleep_ms(self, _ms: int) -> None:
        await asyncio.sleep(0)

    def release(self) -> None:
        self.hold = False
        self._release.set()

    def __getattr__(self, name: str) -> object:
        return getattr(asyncio, name)


class _ReportTap:
    # Checks each of the PC report's two outputs and passes it on to the real console. Counts rather than keeps
    # them: a kept exception or dead task would read as heap drift.
    def __init__(self) -> None:
        self.reported = 0
        self.traced = 0
        self.wrong: list[object] = []

    def __enter__(self) -> "_ReportTap":
        unix_port_unretrieved_report.print = self._print  # type: ignore[attr-defined]
        unix_port_unretrieved_report.sys = self  # type: ignore[attr-defined, assignment]
        return self

    def __exit__(self, *exc_info: object) -> None:
        del unix_port_unretrieved_report.print  # type: ignore[attr-defined]
        unix_port_unretrieved_report.sys = sys  # type: ignore[attr-defined]

    def _print(self, *args: object) -> None:
        if args == (unix_port_unretrieved_report.MARKER, "Task exception wasn't retrieved"):
            self.reported += 1
        else:
            self.wrong.append(args)
        print(*args)

    def print_exception(self, exc: BaseException) -> None:
        if isinstance(exc, RuntimeError) and exc.args == ("injected status fault",):
            self.traced += 1
        else:
            self.wrong.append(exc)
        sys.print_exception(exc)


async def _yield_until(predicate: "Callable[[], bool]") -> bool:
    for _ in range(_PASS_YIELD_BOUND):
        if predicate():
            return True
        await asyncio.sleep(0)
    return predicate()


async def _yield_until_above(read: "Callable[[], int]", floor: int) -> bool:
    return await _yield_until(lambda: read() > floor)


def test_a_supervised_task_death_reaches_the_console_through_the_pc_report_at_level_0() -> None:
    port = _next_test_port()
    tap = _ReportTap()
    drift = [0] * _STATUS_DEATHS  # sized up front: a growing list would read as heap drift
    resets = machine.reset_count

    async def scenario() -> None:
        await _boot(port)
        sysfunct, watchdog = sensortask_wozi.sysfunct, sensortask_wozi.watchdog
        assert sysfunct is not None and watchdog is not None
        assert sysfunct.pr.set_level(0)
        task_starters = sensortask_wozi._collect_task_starters()
        status_idx = task_starters.index(sysfunct.start_asy_status)  # SYSTEM's own task: every device has it
        starts = [0] * len(task_starters)
        latest: list[asyncio.Task[Any] | None] = [None] * len(task_starters)  # only the live one: no dead task is kept
        real_start_task, real_uptime = sysfunct._start_task, sysfunct._uptime

        async def _tracking_start_task(starter: "Callable[[], asyncio.Task[Any]]", n: int) -> "asyncio.Task[Any] | None":
            latest[n] = await real_start_task(starter, n)
            starts[n] += 1
            return latest[n]

        sysfunct._start_task = _tracking_start_task  # type: ignore[method-assign]
        fast = _FastSupervisorAsyncio()
        asy_system_service.asyncio = fast  # type: ignore[attr-defined, assignment]
        supervisor = asyncio.get_event_loop().create_task(sysfunct.start_and_check_tasks(task_starters))
        try:
            assert await _yield_until(lambda: all(starts)), starts
            assert asyncio.get_event_loop().get_exception_handler() is unix_port_unretrieved_report.report_unretrieved
            sysfunct._uptime = _StatusFault()  # type: ignore[assignment]
            with tap:
                for death in range(_STATUS_DEATHS):
                    # The death lands while the supervisor sleeps, as its two-second pass makes near certain on the
                    # board: a pass awaiting the dead task first would retrieve the exception, and no handler runs.
                    fast.hold = True
                    assert await _yield_until(lambda: fast.parked), "the supervisor never reached its sleep"
                    restarts, reported = starts[status_idx], tap.reported
                    sysfunct._uptime_event.set()
                    assert await _yield_until_above(lambda: tap.reported, reported), f"the death never reached the PC report: {tap.wrong}"
                    fast.release()
                    assert await _yield_until_above(lambda: starts[status_idx], restarts), "the dead status task was never restarted"
                    fed = watchdog.feed_count
                    assert await _yield_until_above(lambda: watchdog.feed_count, fed + _DECAY_PASSES - 1), "the supervisor stopped passing"
                    gc.collect()
                    drift[death] = gc.mem_alloc()
            assert asyncio.get_event_loop().get_exception_handler() is unix_port_unretrieved_report.report_unretrieved
        finally:
            sysfunct._uptime = real_uptime
            del sysfunct._start_task
            asy_system_service.asyncio = asyncio  # type: ignore[attr-defined]
            await _cancel(supervisor)
            for task in latest:
                # A dead one stays: the supervisor awaited it already, and a second await of a task whose first
                # one raced asyncio's pending handler entry raises None, a segfault (SPECIFICATION.md Part F.1).
                if task is not None and not task.done():
                    await _cancel(task)
            if sensortask_wozi.conn is not None and sensortask_wozi.conn._dns_server_task is not None:
                await _cancel(sensortask_wozi.conn._dns_server_task)
            gc.collect()  # same reason as the restart test above: the full task list ran

    run_timed(scenario(), timeout_s=_SUPERVISOR_RUN_BOUND_S)
    assert (tap.reported, tap.traced, tap.wrong) == (_STATUS_DEATHS, _STATUS_DEATHS, []), (tap.reported, tap.traced, tap.wrong)
    assert machine.reset_count == resets  # the restart budget never escalated to a reset
    assert max(drift) - drift[0] <= _HEAP_DRIFT_BYTES, drift


# ---------------------------------------------------------------------------
# WiFi hotspot/DNS/LED chain, end to end: a real STA connect failure driving WifiService through a real STA
# -> hotspot transition, starting a real CaptiveDNS task, with the real WiFi-status LED wired by
# build_system() actually driven by the real state machine along the way.
# ---------------------------------------------------------------------------


def test_wifi_sta_failure_falls_back_to_hotspot_and_drives_the_real_dns_server_and_status_led() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.conn is not None and sensortask_wozi.neopixel is not None
        conn = sensortask_wozi.conn
        pixel = sensortask_wozi.neopixel

        # A real configured SSID (not the "SSID==''" unconfigured shortcut) so this exercises a
        # genuine scripted STA connect failure through the real state machine, not just "never
        # configured".
        persisted, _results = await conn.cfgmgr.write_config({"SSID": "TestNet"})
        assert persisted

        import network  # digital_twin's own fake - see this file's own sys.path setup above

        # Eight, not one, so the transition does not depend on WHEN the seeding below lands. A
        # single scripted failure made the test hinge on a timing window that measure A's ~9x
        # cheaper FRAM path closed, 2 of 2 runs (MEASUREMENTS archive 7C); a deeper queue removes it.
        conn._wlan.script_connect_outcomes([network.STAT_NO_AP_FOUND] * 8)

        pixel_task = pixel.start_asy_overlay()  # the one real pixel task that turns
        # conn's own on()/off()/toggle() LED calls into real committed NeoPixel frames.
        wifi_task = conn.start_asy_connect()
        webserver_task = await _start_webserver()  # real is_hotspot_active=conn.is_hotspot_active
        # wiring (SPECIFICATION.md Part A.5) - free coverage once this test drives real hotspot mode.
        try:
            await asyncio.sleep(0.2)  # let _connect_loop()'s own synchronous prefix
            # Set after _reset_wlan_connect_state() has run, since that unconditionally zeroes
            # _connection_failures and would immediately overwrite a value set before the task started.
            #
            # Fast-forwards the real conn_fail_to_hotspot=5 streak to one scripted failure from hotspot
            # fallback - the same direct-attribute seam _sensortask_scenarios.py uses, not a fake of the
            # failure registrar. Waiting out 5 real cycles exercises the identical transition, slower.
            conn._connection_failures = 4
            started = await _wait_until(lambda: conn._dns_server_task is not None, timeout_s=_HOTSPOT_WAIT_TIMEOUT_S)
            assert started, "real hotspot activation never started the real CaptiveDNS task"
            dns_task = conn._dns_server_task
            assert dns_task is not None and not dns_task.done()
            # The task existing is not the port being bound (UDPSocket binds lazily in run()), and a
            # datagram sent to an unbound UDP port is silently dropped - the query below sends only once.
            bound = await _wait_until(lambda: conn._dns_server._udps.connected, timeout_s=_WAIT_TIMEOUT_S, interval_s=_BIND_POLL_S)
            assert bound, "the real CaptiveDNS never bound its port 53 socket"
            # The generated sensortask_wozi.py's module-level `conn` is typed "Any | None" rather than the
            # hand-written file's precise "WifiService | None" (buildgen/codegen.py's deliberate choice), so
            # this attribute access needs no type: ignore any more.
            #
            # The real WiFi-status LED wiring did not just exist - it drove real hardware-facing calls
            # during the transition, landing as real committed frames on the twin NeoPixel.
            assert conn._led is pixel
            assert len(pixel._pixel.writes) > 0, "the real status LED never actually wrote a frame"
            assert conn.is_hotspot_active() is True
            # A genuine DNS query against the real, already-running conn._dns_server_task resolves
            # to the AP's own IP, read live from conn._wlan.ifconfig() (currently "0.0.0.0" - a
            # twin-fidelity gap, see digital_twin/README.md - not a real product bug).
            answer_ip = await _query_dns_and_get_answer_ip(_make_dns_query(["captive", "example"]))
            assert answer_ip == conn._wlan.ifconfig()[0]
            # Real end-to-end captive-portal redirect through the real webserver, consulting the
            # real conn.is_hotspot_active() - not a unit-level fake callback. Combined with the DNS
            # query above, proves the full captive-portal mechanism end-to-end.
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/generate_204")
            assert res.status_code == 302
            assert res.headers["Location"] == "/"
        finally:
            await _cancel(wifi_task)
            await _cancel(pixel_task)
            await _cancel(webserver_task)
            if conn._dns_server_task is not None:
                await _cancel(conn._dns_server_task)
            gc.collect()  # see the task-supervisor-restart section's own comment above - this test
            # starts several real background tasks (wifi, pixel, hotspot DNS, webserver) too.

    run_timed(scenario(), timeout_s=_HOTSPOT_RUN_BOUND_S)


# ---------------------------------------------------------------------------
# SGP40 VOC-backup reboot survival, end to end: a real FRAM write through the real sgp40/fram construction
# order from build_system(), a simulated reboot via the twin's own FramChip state-file persistence (the
# twin's real mechanism, not a substitute), then a real restore against a brand-new object graph.
# ---------------------------------------------------------------------------


def test_sgp40_voc_backup_survives_a_simulated_reboot_through_the_real_fram_chunk() -> None:
    async def scenario() -> None:
        cfg_path = _tmp_cfg_dir()
        state_path = cfg_path + "fram_state.json"
        machine.configure_fram_state_path(state_path)
        try:
            # --- Boot 1: real construction, the real timestamped FRAM backup chunk (SPECIFICATION.md Part A.7) write
            # through the real chain. ---
            machine.configure_wiring(_wiring_plan("wozi"))  # see _boot()'s own identical comment for why this is needed every call, not just once
            await sensortask_wozi.build_system(cfg_path=cfg_path, web_host="127.0.0.1", web_port=_next_test_port())
            assert sensortask_wozi.sgp40 is not None and sensortask_wozi.scd30 is not None
            sgp1 = sensortask_wozi.sgp40
            # sgp_comp_callback reads scd30.get_data() for humidity compensation, without which _read_sgp()
            # bails out. scd30's read chain is orthogonal here, so its cached reading is seeded through the
            # same _set_meas_data() a real read cycle calls.
            await sensortask_wozi.scd30._set_meas_data(SCD30(800, 22.0, 45.0, None, None, None, None, None))
            # WaitTimeNTP's schema default (30) would need 30 real backup cycles before _run_backup()'s
            # require_ntp gate clears without an NTP sync - set to its minimum positive value so the first
            # backup below completes without depending on NTP reachability here.
            persisted, _results = await sgp1.cfgmgr.write_config({"WaitTimeNTP": 1})
            assert persisted
            task = sgp1.start_asy_read()
            try:
                # Real init: sgp.setup()'s real I2C handshake against the twin's fake SGP40 chip (serial
                # number, self-test, general-call reset), where the reset alone sleeps a real 1s. No public
                # "init done" flag exists to poll, so this is a plain, generously-bounded sleep.
                await asyncio.sleep(2.5)
                sgp1._backup_counter = 59  # BackupPeriod defaults to 1 (minute) -> a real 60-cycle
                # threshold (asy_sgp40_driver.py's own _check_storage()) - forces the very next real
                # trigger cycle to reach it, exercising the same real _run_backup() 60 real cycles
                # would, just without waiting through 59 of them for the same real code path.
                sgp1._read_event.set()
                assert await _wait_until(lambda: sgp1._last_backup is not None, timeout_s=_WAIT_TIMEOUT_S), (
                    "the real VOC backup write never completed"
                )
            finally:
                await _cancel(task)

            # Simulated reboot: persist the twin's FRAM image to disk, then rebuild the object graph fresh
            # from the SAME cfg_path and FRAM state - the twin analogue of a device losing power and cold-
            # booting with the same chip attached (digital_twin/README.md's "FRAM persistence").
            machine.flush_fram()
            machine.configure_wiring(_wiring_plan("wozi"))  # see _boot()'s own identical comment for why this is needed every call, not just once
            await sensortask_wozi.build_system(cfg_path=cfg_path, web_host="127.0.0.1", web_port=_next_test_port())
            assert sensortask_wozi.sgp40 is not None and sensortask_wozi.scd30 is not None
            assert sensortask_wozi.sgp40 is not sgp1  # a genuinely fresh object, not the same
            # instance surviving in memory - the whole point is that the persisted FRAM bytes, not
            # Python state, are what carries the backup across the "reboot".
            sgp2 = sensortask_wozi.sgp40
            await sensortask_wozi.scd30._set_meas_data(SCD30(800, 22.0, 45.0, None, None, None, None, None))  # see boot 1's own comment above

            # --- Restore, through the real chain again. ---
            task2 = sgp2.start_asy_read()
            try:
                await asyncio.sleep(2.5)  # same real init delay as boot 1 above
                sgp2._read_event.set()
                assert await _wait_until(lambda: sgp2._restored_from is not None, timeout_s=_WAIT_TIMEOUT_S), (
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

    run_timed(scenario(), timeout_s=_REBOOT_RUN_BOUND_S)


# ---------------------------------------------------------------------------
# Unlike the reboot-survival test above (which flush_fram()s right after its one backup), this
# proves what happens if a crash lands *between* a write landing in FRAM and the next flush - the
# twin-tier analogue of tests_hardware/flash/test_bus_concurrency.py's hard-reset-race test.
# ---------------------------------------------------------------------------


def test_sgp40_voc_backup_unflushed_write_is_lost_but_the_system_recovers_cleanly_to_the_last_flushed_state() -> None:
    async def scenario() -> None:
        cfg_path = _tmp_cfg_dir()
        state_path = cfg_path + "fram_state.json"
        machine.configure_fram_state_path(state_path)
        try:
            # Boot 1: real construction, one real backup, flushed - the durable "last known good"
            # state everything below checks against.
            machine.configure_wiring(_wiring_plan("wozi"))  # see _boot()'s own identical comment for why this is needed every call, not just once
            await sensortask_wozi.build_system(cfg_path=cfg_path, web_host="127.0.0.1", web_port=_next_test_port())
            assert sensortask_wozi.sgp40 is not None and sensortask_wozi.scd30 is not None
            sgp1 = sensortask_wozi.sgp40
            await sensortask_wozi.scd30._set_meas_data(SCD30(800, 22.0, 45.0, None, None, None, None, None))
            persisted, _results = await sgp1.cfgmgr.write_config({"WaitTimeNTP": 1})
            assert persisted
            task = sgp1.start_asy_read()
            try:
                await asyncio.sleep(2.5)
                sgp1._backup_counter = 59
                sgp1._read_event.set()
                assert await _wait_until(lambda: sgp1._last_backup is not None, timeout_s=_WAIT_TIMEOUT_S), "the first real VOC backup write never completed"
            finally:
                await _cancel(task)
            machine.flush_fram()
            with open(state_path) as f:
                flushed_state = f.read()

            # A second real backup mutates the twin's in-memory FRAM image but is deliberately
            # never flushed - simulating a crash/power-loss after the write lands in RAM but
            # before the next flush to persistent storage ever runs.
            task2 = sgp1.start_asy_read()
            try:
                sgp1._backup_counter = 59
                sgp1._read_event.set()
                assert await _wait_until(lambda: sgp1._last_backup is not None, timeout_s=_WAIT_TIMEOUT_S), "the second real VOC backup write never completed"
            finally:
                await _cancel(task2)
            with open(state_path) as f:
                unflushed_check = f.read()
            assert unflushed_check == flushed_state, "the second backup's own write leaked onto disk despite never being flushed - flush_fram() may no longer be the only real persistence trigger"

            # Simulated crash-reboot: rebuild the object graph fresh from the SAME state_path,
            # which still only holds boot 1's flushed content - the second backup's write is
            # genuinely lost, exactly as an un-flushed write would be lost to a real power cycle.
            machine.configure_wiring(_wiring_plan("wozi"))  # see _boot()'s own identical comment for why this is needed every call, not just once
            await sensortask_wozi.build_system(cfg_path=cfg_path, web_host="127.0.0.1", web_port=_next_test_port())
            assert sensortask_wozi.sgp40 is not None and sensortask_wozi.scd30 is not None
            assert sensortask_wozi.sgp40 is not sgp1  # genuinely fresh object, not memory surviving in-process
            sgp2 = sensortask_wozi.sgp40
            await sensortask_wozi.scd30._set_meas_data(SCD30(800, 22.0, 45.0, None, None, None, None, None))

            # Restore must succeed cleanly against the last *flushed* state, with no trace of the lost write.
            task3 = sgp2.start_asy_read()
            try:
                await asyncio.sleep(2.5)
                sgp2._read_event.set()
                assert await _wait_until(lambda: sgp2._restored_from is not None, timeout_s=_WAIT_TIMEOUT_S), "the real VOC backup restore never completed after the simulated crash-reboot"
            finally:
                await _cancel(task3)
        finally:
            machine.configure_fram_state_path(None)  # see the reboot-survival test's own comment above
            gc.collect()  # this test builds the whole real object graph twice in one run

    run_timed(scenario(), timeout_s=_REBOOT_RUN_BOUND_S)


def test_mempause_over_real_http_reaches_the_real_fram_manager_and_unpauses() -> None:
    # The REST -> SystemService.pause_permanent_storage() -> FRAMManager.set_pause() wiring, through the
    # real booted object graph and a real HTTP request. The mock tier proves the pause logic and the flash
    # tier the real chip gating; what this tier adds is that the wiring holds in CI, on every push.
    #
    # Deliberately does not wait out an auto-unpause: the command's duration is a hardcoded 300s no client
    # can shorten, so the unpause half is driven through the same SystemService call the command reaches.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.fram is not None
        assert sensortask_wozi.sysfunct is not None
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/status")
            assert res.json()["system"]["MemPaused"] is False

            res = await _http_client.fetch("127.0.0.1", port, "PUT", "/system", {"SystemCmd": "mempause"})
            assert res.status_code == 200

            # Both the live object and the REST view must agree - a status field reporting a
            # different flag than the manager actually holds would be the real defect here.
            assert sensortask_wozi.fram.get_pause() is True
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/status")
            assert res.json()["system"]["MemPaused"] is True

            sensortask_wozi.sysfunct.pause_permanent_storage(0)  # the immediate-unpause branch
            assert sensortask_wozi.fram.get_pause() is False
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/status")
            assert res.json()["system"]["MemPaused"] is False
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=_SUPERVISOR_RUN_BOUND_S)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
