"""WifiService: connect and reconnect, the hotspot fallback and its stations, LED handling, the persisted config and the
network snapshot, against the network fake."""

import asyncio
import json
import os
import select
import socket
import sys

sys.path.insert(0, "digital_twin/unixport")  # the Unix-port UDP address shim (SPECIFICATION.md F.7 row 1)

import machine
import network
from _async_harness import cancel, run
from _error_codes import code
from _fake_time import DrivenTime, tick
from _fake_timer_arm import RaiseOnArm
from _fast_sleep import FastAsyncSleep
from _port_bands import PortAllocator
from _recording_print import record_prints
from _src_const import src_int
from _src_schema import src_schema
from _tmp_scratch import TmpScratch
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from machine import Timer

import asy_base_classes
import asy_wifi_service
from asy_api_response import handle_set_cmd
from asy_print_log import LogConfig
from asy_udp_socket import UDPSocket
from asy_wifi_service import WIFI, WifiConfig, WifiService

# UDPSocket takes plain (host, port) tuples; on this Unix build the shim resolves them (once, class-wide).
patch_asy_udp_socket_for_unix_port()

def _src_pattern(name: str) -> "tuple[int, int]":
    # One LED pattern's (on, off) milliseconds: _src_pattern("HOTSPOT") reads _LED_HOTSPOT_ON_MS and _LED_HOTSPOT_OFF_MS.
    return src_int("src/asy_wifi_service.py", "_LED_" + name + "_ON_MS"), src_int("src/asy_wifi_service.py", "_LED_" + name + "_OFF_MS")


# Read from source: const() folds them out of the module (tests/_src_const.py), each by the typed reader of the type
# the tests use it as.
_PHASE_STA_SEEKING: int = src_int("src/asy_wifi_service.py", "_PHASE_STA_SEEKING")
_PHASE_STA_ESTABLISHED: int = src_int("src/asy_wifi_service.py", "_PHASE_STA_ESTABLISHED")
_PHASE_HOTSPOT: int = src_int("src/asy_wifi_service.py", "_PHASE_HOTSPOT")
_PHASE_DEACTIVATED: int = src_int("src/asy_wifi_service.py", "_PHASE_DEACTIVATED")
_PHASE_SILENT: int = src_int("src/asy_wifi_service.py", "_PHASE_SILENT")
_STATIONS_UNSET: int = src_int("src/asy_wifi_service.py", "_STATIONS_UNSET")
_VAL_SSID: "cm.ConfigSchema" = src_schema("src/asy_wifi_service.py", "_VAL_SSID")
_VAL_PW: "cm.ConfigSchema" = src_schema("src/asy_wifi_service.py", "_VAL_PW")
_VAL_COUNTRY: "cm.ConfigSchema" = src_schema("src/asy_wifi_service.py", "_VAL_COUNTRY")
_VAL_HOSTNAME: "cm.ConfigSchema" = src_schema("src/asy_wifi_service.py", "_VAL_HOSTNAME")
_VAL_LED_WIFI_ON: "cm.ConfigSchema" = src_schema("src/asy_wifi_service.py", "_VAL_LED_WIFI_ON")
_VAL_HOTSPOT_PW: "cm.ConfigSchema" = src_schema("src/asy_wifi_service.py", "_VAL_HOTSPOT_PW")
_STA_DISCONNECT_POLL_MS: int = src_int("src/asy_wifi_service.py", "_STA_DISCONNECT_POLL_MS")
_STA_CONNECT_POLL_MS: int = src_int("src/asy_wifi_service.py", "_STA_CONNECT_POLL_MS")
_STA_CONNECT_POLL_ITERS: int = src_int("src/asy_wifi_service.py", "_STA_CONNECT_POLL_ITERS")
_HOTSPOT_STATIONS_SETTLE_MS: int = src_int("src/asy_wifi_service.py", "_HOTSPOT_STATIONS_SETTLE_MS")
_STA_DISCONNECT_WAIT_ITERS: int = src_int("src/asy_wifi_service.py", "_STA_DISCONNECT_WAIT_ITERS")
_STA_RETRY_AFTER_LOSS_S: int = src_int("src/asy_wifi_service.py", "_STA_RETRY_AFTER_LOSS_S")
_STAT_JOINED_NO_IP: int = src_int("src/asy_wifi_service.py", "_STAT_JOINED_NO_IP")

# @tunable l1.asy_wifi_service_connect_bound_s = 2.0
_CONNECT_BOUND_S = 2.0
# @tunable l1.asy_wifi_service_sent_poll_ms = 10
_SENT_POLL_MS = 10
# @tunable l1.asy_wifi_service_sent_poll_tries = 100
_SENT_POLL_TRIES = 100
# @tunable l1.asy_wifi_service_off_subnet_wait_s = 0.2
_OFF_SUBNET_WAIT_S = 0.2
# @tunable l1.asy_wifi_service_connect_poll_ms = 50
_CONNECT_POLL_MS = 50
# @tunable l1.asy_wifi_service_connect_poll_tries = 200
_CONNECT_POLL_TRIES = 200
# @tunable l1.asy_wifi_service_phase_poll_ms = 20
_PHASE_POLL_MS = 20
# @tunable l1.asy_wifi_service_phase_poll_tries = 100
_PHASE_POLL_TRIES = 100
# @tunable l1.asy_wifi_service_flash_cancel_bound_s = 1
_FLASH_CANCEL_BOUND_S = 1

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Literal, Protocol

    from _protocols import WLANLike
    from typing_extensions import Self

    import asy_config_manager as cm
    from asy_base_classes import PushFct
    from asy_config_manager import CfgValue, WriteValidity
    from asy_print_log import ErrorLog

    class _FakeWLAN(WLANLike, Protocol):
        # The fake's test-only names this file reads and sets: mypy resolves `network` to the board stub, which has
        # none of them (tests/network.py is outside the main pass, B.15).
        if_id: int
        _active: bool
        _connected: bool
        _status: int | None
        _ifconfig: tuple[str, str, str, str]
        _stations: list[tuple[bytes, ...]]
        _rssi: int
        raise_on: dict[str, BaseException]
        config_calls: list[dict[str, object]]
        connect_calls: list[tuple[str | None, str | None]]
        status_calls: list[str | None]
        disconnect_called: bool
        deinit_called: bool


async def _push(callback: "PushFct", value: "CfgValue") -> bool:
    # A push callback is typed to return an Awaitable (asy_base_classes' PushFct); run() takes a coroutine.
    return await callback(value)


def _last_err(counter: "ErrorLog", field: 'Literal["ErrNum", "ErrType"]') -> "int | str":
    # ErrNum/ErrType are list-shaped once _error_check() has run at least once - same helper as
    # test_asy_ntp_client.py's own, scoped to this file's "WIFI" key instead of "NTP".
    value = counter["WIFI"][field]
    assert isinstance(value, list)
    return value[-1]


def _used_slots(counter: "ErrorLog", name: str = "WIFI") -> "list[int]":
    # The ring's used slots, oldest first ("N" marks an unused one).
    nums, types = counter[name]["ErrNum"], counter[name]["ErrType"]
    return [nums[i] for i in range(len(nums)) if types[i] != "N"]


def _wlan(client: WifiService) -> "_FakeWLAN":
    return client._wlan  # type: ignore[return-value]  # the fake, which mypy sees as the board stub's WLAN


def _on_the_ap(client: WifiService) -> "_FakeWLAN":
    # The AP selected through the product's own mode switch (its settle sleeps one yield each): status("stations")
    # answers on the AP only (extmod/network_cyw43.c:371-388, v1.29.0).
    with FastAsyncSleep():
        assert run(client._select_wifi_mode(network.AP_IF)) is True
    return _wlan(client)


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("wifi")


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


class _FakeLED:
    # Structurally satisfies asy_wifi_service.py's LEDControl Protocol (on/off/toggle) with no real
    # GPIO pin, same spirit as the fake network.WLAN. raise_on models a genuinely misbehaving
    # caller-injected ext_led, which _led_on()/_led_off()/_led_toggle() must degrade against.
    def __init__(self) -> None:
        self.on_calls = 0
        self.off_calls = 0
        self.toggle_calls = 0
        # Latest lit/unlit state, on top of the call counters: a cancelled flash task must leave the LED as
        # its canceller set it, which a pair of counters can only show indirectly.
        # None until the first on()/off()/toggle() - a real LED's power-on state isn't ours to claim.
        self.state: bool | None = None
        self.raise_on: dict[str, Exception] = {}

    def off(self) -> None:
        exc = self.raise_on.get("off")
        if exc is not None:
            raise exc
        self.off_calls += 1
        self.state = False

    def on(self) -> None:
        exc = self.raise_on.get("on")
        if exc is not None:
            raise exc
        self.on_calls += 1
        self.state = True

    def toggle(self) -> None:
        exc = self.raise_on.get("toggle")
        if exc is not None:
            raise exc
        self.toggle_calls += 1
        self.state = not self.state


def _make_client(
    conn_fail_to_hotspot: int = 5,
    ext_led: "_FakeLED | None" = None,
    hotspot_time_min: int = 5,
    max_module_error: int = 5,
    cfg_path: "str | None" = None,
    debug: "int | None" = None,
) -> WifiService:
    if cfg_path is None:
        cfg_path = _tmp_cfg_dir()
    client = WifiService(
        WifiConfig("SensorNode", "12345678", conn_fail_to_hotspot, hotspot_time_min),
        ext_led=ext_led,
        max_module_error=max_module_error,
        cfg_path=cfg_path,
        log=LogConfig(None, 10, debug),
    )
    run(client.cfgmgr.setup())
    return client


def _make_client_with_json(  # parameters/defaults mirror _make_client() above, minus its cfg_path
    json_text: str,
    conn_fail_to_hotspot: int = 5,
    ext_led: "_FakeLED | None" = None,
    hotspot_time_min: int = 5,
    max_module_error: int = 5,
    debug: "int | None" = None,
) -> WifiService:
    cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_WIFI.cfg", "w") as f:
        f.write(json_text)
    return _make_client(
        conn_fail_to_hotspot=conn_fail_to_hotspot,
        ext_led=ext_led,
        hotspot_time_min=hotspot_time_min,
        max_module_error=max_module_error,
        cfg_path=cfg_path,
        debug=debug,
    )


def _make_invalid_cfg_client() -> WifiService:
    # A directory where ConfigManager expects a plain file - same technique as
    # test_asy_ntp_client.py's own _make_invalid_cfg_client().
    cfg_path = _tmp_cfg_dir()
    os.mkdir(cfg_path + "config_WIFI.cfg")
    return _make_client(cfg_path=cfg_path)


_VALID_JSON = (
    '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", '
    '"Hostname": "TestNode", "LEDWifiOn": false}'
)


def _stored_json(*, led_on: bool) -> str:
    # _VALID_JSON's network settings with LEDWifiOn as given: every connect attempt re-reads the stored LED setting.
    return _VALID_JSON.replace('"LEDWifiOn": false', '"LEDWifiOn": true') if led_on else _VALID_JSON


def _silent_client(*, led: "_FakeLED | None" = None, led_on: bool = False, hotspot_time_min: int = 1) -> WifiService:
    # A configured unit already silent, as its second streak leaves it. The watcher's flag parks on an asyncio.Event
    # (_ParkedFlag), so a parked watcher never waits through select.poll() over a non-fd object.
    client = _make_client_with_json(_stored_json(led_on=led_on), ext_led=led, hotspot_time_min=hotspot_time_min)
    run(client.pr.setup())
    client._hotspot_timeout_trigger_event = _ParkedFlag()  # type: ignore[assignment]  # see _ParkedFlag
    client._conn_phase = _PHASE_SILENT
    return client


def _joins(client: WifiService) -> None:
    # The selected STA links on its next connect(), as a router back in range lets it.
    radio = _wlan(client)
    record = radio.connect

    def connect(ssid: str, pw: str) -> None:
        record(ssid, pw)
        radio._status, radio._connected = network.STAT_GOT_IP, True

    radio.connect = connect  # type: ignore[assignment, method-assign]  # the fake radio joins as a router in range lets it


async def _fire_period(client: WifiService) -> None:
    # One silent period with the watcher running: an iteration (arming the period if it is not running), the timer's
    # soft callback, the watcher's wake, then the iteration that serves the attempt.
    await client._run_silent_mode()
    client._hotspot_timer.trigger()
    await _drive(2)
    await client._run_silent_mode()


# ---------------------------------------------------------------------------
# __init__ / get_task_starters / get_timer_starters (SPECIFICATION.md Part C.9)
# ---------------------------------------------------------------------------


def test_init_creates_an_sta_mode_wlan_by_default() -> None:
    client = _make_client()
    assert _wlan(client).if_id == network.STA_IF


def test_init_creates_its_own_config_file_with_schema_defaults() -> None:
    client = _make_client()
    values = run(client.cfgmgr.get_dict(["SSID", "PW", "Country", "Hostname", "LEDWifiOn"]))
    assert values is not None
    assert values == {"SSID": "", "PW": "", "Country": "DE", "Hostname": "SensorNode", "LEDWifiOn": True}


def test_a_per_device_hostname_and_hotspot_password_replace_the_shared_defaults() -> None:
    # buildgen passes devices/*.toml's own [device].hostname/hotspot_password here. Before this
    # existed the two TOML fields were validated and then reached nothing, so every device booted
    # as "SensorNode" whatever its own file said.
    client = WifiService(WifiConfig("SensorStationTest", "hunter2hunter2", 5, 5), cfg_path=_tmp_cfg_dir())
    run(client.cfgmgr.setup())
    values = run(client.cfgmgr.get_dict(["Hostname", "HotspotPW"]))
    assert values == {"Hostname": "SensorStationTest", "HotspotPW": "hunter2hunter2"}


def test_an_injected_value_still_goes_through_the_schema_bounds() -> None:
    # Only the default moves - the validation rungs are the same ones a REST PUT hits, so a build
    # that injected a 3-character hotspot password must not produce a device the CYW43 cannot bring
    # up. It falls back to the schema's own default rather than accepting it.
    client = WifiService(WifiConfig("", "short", 5, 5), cfg_path=_tmp_cfg_dir())  # too short, which is the point of the test
    run(client.cfgmgr.setup())
    values = run(client.cfgmgr.get_dict(["Hostname", "HotspotPW"]))
    assert values == {"Hostname": "SensorNode", "HotspotPW": "12345678"}


def test_get_task_starters_returns_wlan_connect_uptime_counter_and_hotspot_watcher() -> None:
    client = _make_client()
    starters = client.get_task_starters()
    assert starters == [client.start_asy_connect, client.start_asy_uptime, client.start_asy_hotspot_timeout]


def test_get_timer_starters_returns_the_counter_timer() -> None:
    client = _make_client()
    assert client.get_timer_starters() == [client.start_uptime_timer]


def test_start_counter_timer_arms_periodic_1s() -> None:
    client = _make_client()
    assert client._tick_armed is None  # not attempted yet: a test or tool that starts only the tasks
    client.start_uptime_timer()
    assert client._counter_timer.mode == Timer.PERIODIC
    assert client._counter_timer.period == 1000
    assert client._tick_armed is True


def test_start_counter_timer_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    client = _make_client()
    with RaiseOnArm():
        client.start_uptime_timer()  # must not raise despite the timer failing to arm
    assert client._counter_timer.period == -1  # never actually armed
    assert client._tick_armed is False  # recorded, so _connect_loop() retries it


def test_start_counter_timer_degrades_gracefully_on_a_memory_error() -> None:
    # Sibling of the OSError test above, for the other arm of start_uptime_timer()'s own
    # `except (OSError, MemoryError)`: a real alarm allocation can fail with MemoryError instead,
    # which is not an OSError subclass - same graceful degradation must hold either way.
    client = _make_client()
    with RaiseOnArm(MemoryError):
        client.start_uptime_timer()  # must not raise despite the timer failing to arm
    assert client._counter_timer.period == -1  # never actually armed
    assert client._tick_armed is False


def _no_sta(client: WifiService, *, failing: bool = False) -> None:
    # Replaces the STA branch of _connect_loop() with a no-op, or with one that fails every iteration.
    async def sta() -> None:
        if failing:
            client._hw_op_failed = True

    client._run_sta_mode = sta  # type: ignore[method-assign]  # the branch is not under test


def test_a_failed_tick_arm_is_retried_by_the_next_loop_iteration() -> None:
    # The snapshot and NTP's DHCP DNS hang on this tick, so a failed arm is retried each iteration and a
    # failed retry persists one TIMER entry and counts toward the give-up streak.
    client = _make_client()
    run(client.pr.setup())
    with RaiseOnArm():
        client.start_uptime_timer()
    _no_sta(client)

    async def scenario() -> "tuple[bool | None, bool | None]":
        task = asyncio.create_task(client._connect_loop())
        with RaiseOnArm():
            for _ in range(4):  # one iteration: the re-arm fails again
                await asyncio.sleep(0)
        still_failing = client._tick_armed
        for _ in range(4):  # the next iteration: the pool has room again
            await asyncio.sleep(0)
        rearmed = client._tick_armed
        await cancel(task)
        return still_failing, rearmed

    with FastAsyncSleep():
        still_failing, rearmed = run(scenario())
    assert (still_failing, rearmed) == (False, True)
    assert client._counter_timer.period == 1000
    log = run(client.get_error_counter())
    assert code("E", "TIMER") in _used_slots(log)


def test_a_refused_tick_prints_the_arm_line_once_per_episode() -> None:
    # The first refused arm prints the helper's line; each later pass's re-arm inside that episode is quiet, the pass's
    # own persisted entry being its record.
    client = _make_client()
    run(client.pr.setup())
    client.pr.set_level(5)
    _no_sta(client)

    async def scenario() -> None:
        task = asyncio.create_task(client._connect_loop())
        for _ in range(12):  # several iterations, every re-arm refused
            await asyncio.sleep(0)
        await cancel(task)

    with record_prints() as recorder, FastAsyncSleep(), RaiseOnArm():
        client.start_uptime_timer()
        run(scenario())
    passes = [ln for ln in recorder.lines if "WiFi uptime timer not armed" in ln]
    assert len(passes) >= 2, recorder.lines
    armed = [ln[:4] for ln in recorder.lines if "Could not arm" in ln]
    assert armed == [("WIFI", "Could not arm", "WiFi uptime", "timer:")], armed


def test_max_failed_rearms_end_the_loop() -> None:
    # A re-arm that keeps failing escalates: the streak ends the task, and the supervisor takes the next step.
    client = _make_client(max_module_error=2)
    run(client.pr.setup())
    _no_sta(client)
    client._tick_armed = False

    async def scenario() -> bool:
        task = asyncio.create_task(client._connect_loop())
        with RaiseOnArm():
            await asyncio.wait_for(task, _CONNECT_BOUND_S)
        return task.done()

    with FastAsyncSleep():
        assert run(scenario()) is True
    kept = _used_slots(run(client.get_error_counter()))
    assert code("E", "TIMER") in kept and code("E", "WLAN_GIVE_UP") in kept, kept


def test_an_unreadable_status_keeps_the_link_state_and_uptime() -> None:
    # Unreadable is unknown, not down: the link state, the uptime and the published snapshot stand, and
    # one warning slot counts how many ticks were unreadable.
    with DrivenTime(asy_base_classes) as clock:
        client = _make_client()
        run(client.pr.setup())
        _wlan(client)._status = network.STAT_GOT_IP
        _wlan(client)._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "10.0.0.53")

        async def scenario() -> "tuple[int, WIFI, bool, int, WIFI, int]":
            task = asyncio.create_task(client._uptime_loop())
            await asyncio.sleep(0)
            for _ in range(3):
                clock.advance(1000)
                await tick(client._time_counter_trigger_event)
            before = await client.get_data()
            _wlan(client).raise_on["status"] = OSError("simulated status failure")
            for _ in range(2):
                clock.advance(1000)
                await tick(client._time_counter_trigger_event)
            during = (client._wifi_connected, await client.get_wifi_uptime(), await client.get_data())
            del _wlan(client).raise_on["status"]
            clock.advance(1000)
            await tick(client._time_counter_trigger_event)
            after = await client.get_wifi_uptime()
            await cancel(task)
            return 3, before, during[0], during[1], during[2], after

        counted, before, connected, uptime, snapshot, after = run(scenario())
    assert connected is True
    assert uptime == counted + 2  # not reset: the link time kept counting from the kept start
    assert snapshot == before
    assert after == counted + 3
    log = run(client.get_error_counter())
    assert _used_slots(log) == [code("W", "WLAN_STATUS_UNREADABLE")]
    assert log["WIFI"]["ErrCount"] == 2


def test_debug_level_propagates_to_the_inherited_pr_logger() -> None:
    print("(expected) debug=3 makes the fresh ConfigManager below log its normal first-use config-file creation")
    client = _make_client(debug=3)
    assert client.pr.level == 3


# ---------------------------------------------------------------------------
# get_dict_cfg / get_error_counter - the base-class getter quartet (SPECIFICATION.md Part C.4.2)
# ---------------------------------------------------------------------------


def test_get_dict_cfg_masks_the_password() -> None:
    # the /networking GET masks PW (SPEC A.8), and HotspotPW the same way
    client = _make_client_with_json(_VALID_JSON)
    result = run(client.get_dict_cfg())
    assert result["WIFI"]["PW"] == "********"
    assert result["WIFI"]["HotspotPW"] == "********"
    assert result["WIFI"]["SSID"] == "MyNetwork"


def test_a_stored_overlong_ssid_reads_back_as_the_default_with_no_log() -> None:
    # GET shows the value the radio uses: a stored 33-byte SSID runs on its default "", and reading it is no event.
    client = _client_with_stored({"SSID": "ä" * 16 + "x"})
    run(client.pr.setup())
    assert run(client.cfgmgr.get_dict(["SSID"])) == {"SSID": "ä" * 16 + "x"}  # stored as it is
    assert run(client.get_dict_cfg())["WIFI"]["SSID"] == ""
    assert run(client.get_error_counter())["WIFI"]["ErrCount"] == 0


def test_a_resubmitted_password_mask_is_stored_and_connects_with_it() -> None:
    # Guard (holds at once): no value is excluded on PUT, the mask string included (owner, 2026-09-29).
    client = _client_with_stored({})
    _no_poll(client)
    assert run(client._set_dict_cfg({"PW": "********"}, client.get_cfg_schema())) == {"PW": "Valid"}
    run(client.cfgmgr.flush_pending())
    assert run(client.cfgmgr.get_dict(["PW"])) == {"PW": "********"}
    run(client._attempt_sta_connect())
    assert _wlan(client).connect_calls == [("HomeNet", "********")]


# ---------------------------------------------------------------------------
# Configuration: every valid field, plus single/multiple invalid recombinations from a real on-disk
# config_WIFI.cfg, through the real ConfigManager this module owns - proving this module's handling
# of per-field defaulting, not re-testing ConfigManager (test_asy_config_manager.py covers that).

# get_dict_cfg()'s _cfg_overlay() hides the real value regardless of validity, so these read the raw
# cached value via client.cfgmgr.get_dict([...]) - the level test_asy_ntp_client.py's own
# config-matrix tests work at too.
# ---------------------------------------------------------------------------

_WIFI_KEYS = ["SSID", "PW", "Country", "Hostname", "LEDWifiOn", "HotspotPW"]
_WIFI_DEFAULTS = {
    "SSID": "",
    "PW": "",
    "Country": "DE",
    "Hostname": "SensorNode",
    "LEDWifiOn": True,
    "HotspotPW": "12345678",
}


def test_config_all_fields_valid_reads_real_values() -> None:
    client = _make_client_with_json(_VALID_JSON)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values == {
        "SSID": "MyNetwork",
        "PW": "supersecret",
        "Country": "US",
        "Hostname": "TestNode",
        "LEDWifiOn": False,
        "HotspotPW": "12345678",
    }


def test_config_ssid_empty_is_valid_not_defaulted() -> None:
    # SSID's own schema min is relaxed to 0 (see asy_wifi_service.py's own schema comment) so the
    # fresh, unconfigured default ("") self-validates - unlike every other str field here.
    json_text = '{"SSID": "", "PW": "supersecret", "Country": "US", "Hostname": "TestNode", "LEDWifiOn": false}'
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["SSID"] == ""
    assert values["PW"] == "supersecret"  # untouched


def test_config_ssid_too_long_falls_back_to_default_ssid_only() -> None:
    json_text = (
        '{"SSID": "' + ("x" * 33) + '", "PW": "supersecret", "Country": "US", '
        '"Hostname": "TestNode", "LEDWifiOn": false}'
    )
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["SSID"] == ""  # defaulted (max 32)
    assert values["PW"] == "supersecret"  # untouched


def test_config_pw_too_long_falls_back_to_default_pw_only() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "' + ("x" * 64) + '", "Country": "US", '
        '"Hostname": "TestNode", "LEDWifiOn": false}'
    )
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["PW"] == ""  # defaulted (max 63)
    assert values["SSID"] == "MyNetwork"  # untouched


def test_config_country_too_long_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "USA", '
        '"Hostname": "TestNode", "LEDWifiOn": false}'
    )
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["Country"] == "DE"


def test_config_country_too_short_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "U", '
        '"Hostname": "TestNode", "LEDWifiOn": false}'
    )
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["Country"] == "DE"


def test_config_country_wrong_type_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": 12345, '
        '"Hostname": "TestNode", "LEDWifiOn": false}'
    )
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["Country"] == "DE"


def test_config_hostname_empty_falls_back_to_default() -> None:
    json_text = '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", "Hostname": "", "LEDWifiOn": false}'
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["Hostname"] == "SensorNode"  # min 1


def test_config_hostname_too_long_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", '
        '"Hostname": "' + ("h" * 64) + '", "LEDWifiOn": false}'
    )
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["Hostname"] == "SensorNode"  # max 32


def test_config_hostname_one_over_the_real_max_falls_back_to_default() -> None:
    # 33 chars - just past network.hostname()'s real 32-character cap, confirmed against
    # extmod/modnetwork.h at v1.26.1 and at the v1.29.0 pin. _VAL_HOSTNAME's schema max was
    # narrowed to match, so this is now rejected at config-validation time, not by the real call.
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", '
        '"Hostname": "' + ("h" * 33) + '", "LEDWifiOn": false}'
    )
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["Hostname"] == "SensorNode"


def test_config_hostname_at_the_real_max_is_accepted() -> None:
    # The boundary value itself (32 chars) must be accepted, not rejected.
    name = "h" * 32
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", '
        '"Hostname": "' + name + '", "LEDWifiOn": false}'
    )
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["Hostname"] == name


def test_config_led_wifi_on_wrong_type_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", '
        '"Hostname": "TestNode", "LEDWifiOn": "true"}'
    )
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["LEDWifiOn"] is True  # a JSON string isn't a real bool - defaulted


def test_config_multiple_invalid_fields_each_fall_back_independently() -> None:
    json_text = (
        '{"SSID": "' + ("x" * 33) + '", "PW": "supersecret", "Country": 12345, '
        '"Hostname": "TestNode", "LEDWifiOn": false}'
    )
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["SSID"] == ""  # defaulted
    assert values["PW"] == "supersecret"  # untouched
    assert values["Country"] == "DE"  # defaulted
    assert values["Hostname"] == "TestNode"  # untouched
    assert values["LEDWifiOn"] is False  # untouched


def test_config_all_fields_invalid_falls_back_to_every_default() -> None:
    json_text = '{"SSID": null, "PW": 12345, "Country": "", "Hostname": null, "LEDWifiOn": "nope"}'
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values == _WIFI_DEFAULTS


def test_config_missing_file_uses_every_default() -> None:
    client = _make_client()  # fresh directory - no config_WIFI.cfg written, so every default applies
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values == _WIFI_DEFAULTS


def test_config_non_dict_json_uses_every_default() -> None:
    client = _make_client_with_json("[1, 2, 3]")
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values == _WIFI_DEFAULTS


def test_config_malformed_json_syntax_uses_every_default() -> None:
    client = _make_client_with_json("{not json at all")
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values == _WIFI_DEFAULTS


def test_config_returns_none_when_config_manager_itself_is_invalid() -> None:
    client = _make_invalid_cfg_client()
    assert client.cfgmgr.valid is False
    assert run(client.cfgmgr.get_dict(_WIFI_KEYS)) is None


def test_get_dict_cfg_returns_schema_defaults_wrapped_in_wifi_key() -> None:
    # PW comes back "********" even though the real cached default is "" - _cfg_overlay()'s masks are
    # unconditional (see test_get_dict_cfg_masks_the_password above).
    client = _make_client()
    result = run(client.get_dict_cfg())
    expected = dict(_WIFI_DEFAULTS)
    expected["PW"] = "********"
    expected["HotspotPW"] = "********"
    assert result == {"WIFI": expected}


def test_get_dict_cfg_is_the_unavailable_marker_when_config_manager_is_invalid() -> None:
    # With no values to read the GET answers the marker, never a map of nulls; it carries no value, so
    # neither password needs _cfg_overlay()'s mask.
    client = _make_invalid_cfg_client()
    result = run(client.get_dict_cfg())
    assert result == {"WIFI": {"error": "unavailable"}}


def test_get_error_counter_starts_empty_and_records_a_real_error() -> None:
    client = _make_client()
    run(client.pr.setup())
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrCount"] == 0
    run(client.pr.err_s("boom", errno=11))
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrCount"] == 1


# ---------------------------------------------------------------------------
# LED helpers - _led_on()/_led_off()/_led_toggle()/set_wifi_led(). _led_off() is a real-bug
# regression test: its body was once overwritten with a call to itself, which a plain call+assert
# catches, since a recursive _led_off() blows the recursion limit instead of returning cleanly.
# ---------------------------------------------------------------------------


def _led_lines(client: WifiService, call: "Callable[[], None]") -> "list[tuple[object, ...]]":
    # The console lines one LED-helper call prints, errors included (level 1).
    client.pr.set_level(1)
    with record_prints() as recorder:
        call()
    return recorder.lines


def test_led_helpers_are_no_ops_when_no_led_selected() -> None:
    led = _FakeLED()
    client = _make_client(ext_led=led)  # selected only once LEDWifiOn turns it on
    for helper in (client._led_on, client._led_off, client._led_toggle):
        assert _led_lines(client, helper) == []  # must not raise or report despite self._led being None
    assert (led.on_calls, led.off_calls, led.toggle_calls, client._led) == (0, 0, 0, None)


def test_set_wifi_led_true_selects_the_ext_led() -> None:
    led = _FakeLED()
    client = _make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    assert client._led is led


def test_led_on_calls_the_selected_leds_on() -> None:
    led = _FakeLED()
    client = _make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    client._led_on()
    assert led.on_calls == 1


def test_led_off_calls_the_selected_leds_off_and_does_not_recurse() -> None:
    led = _FakeLED()
    client = _make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    client._led_off()
    assert led.off_calls == 1
    assert led.on_calls == 0


def test_led_toggle_calls_the_selected_leds_toggle() -> None:
    led = _FakeLED()
    client = _make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    client._led_toggle()
    assert led.toggle_calls == 1


def test_set_wifi_led_false_turns_the_led_off_and_clears_it() -> None:
    led = _FakeLED()
    client = _make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    run(client.set_wifi_led(status=False))
    assert led.off_calls == 1
    assert client._led is None


def test_each_led_helper_degrades_to_one_console_line_when_a_misbehaving_ext_led_raises() -> None:
    # self._led can be a caller-injected ext_led, not necessarily a real, never-raising Pin - a broken
    # implementation must not crash whatever caller touched the LED; one line reports it, and the next
    # call still reaches the LED.
    for method, text in (("on", "LED on() failed:"), ("off", "LED off() failed:"), ("toggle", "LED toggle() failed:")):
        led = _FakeLED()
        client = _make_client(ext_led=led)
        run(client.set_wifi_led(status=True))
        helper = getattr(client, "_led_" + method)
        led.raise_on[method] = RuntimeError("simulated misbehaving ext_led")
        lines = _led_lines(client, helper)  # must not raise
        assert [line[:2] for line in lines] == [("WIFI", text)], (method, lines)
        del led.raise_on[method]
        helper()
        assert getattr(led, method + "_calls") == 1, method


def test_set_wifi_led_returns_true_uniform_setter_contract() -> None:
    # (owner, 2026-09-26): every setter returns bool (True = applied), not None. set_wifi_led
    # can't actually fail (pure attribute assignment plus _led_off()'s own already-defensive
    # degrade-on-raise), so it's always True - but the contract itself must hold everywhere.
    client = _make_client(ext_led=_FakeLED())
    assert run(client.set_wifi_led(status=True)) is True
    assert run(client.set_wifi_led(status=False)) is True


def test_a_cancelled_flash_leaves_the_led_as_the_canceller_sets_it() -> None:
    # The flash task has no cancel handler: a cancel ends it at its sleep, touching no LED, so the LED
    # stays as the canceller left it - here _reset_wlan_connect_state()'s off, never overridden later.
    led = _FakeLED()
    client = _make_client(ext_led=led)
    run(client.set_wifi_led(status=True))

    async def scenario() -> "tuple[bool | None, bool | None, bool]":
        client._hotspot_client_connected()  # the client pattern starts with its on phase
        flash = client._ledflash
        assert flash is not None
        await asyncio.sleep(0)  # a park: the flash task runs up to its first sleep
        lit = led.state
        client._reset_wlan_connect_state()  # cancels the flash task, then turns the LED off
        for _ in range(4):  # parks: the cancelled task gets every chance to run a handler
            await asyncio.sleep(0)
        try:
            await flash
        except asyncio.CancelledError:
            return lit, led.state, True
        return lit, led.state, False

    with FastAsyncSleep():
        lit, final, cancelled = run(scenario())
    assert lit is True
    assert final is False
    assert cancelled is True


def test_a_raising_led_helper_ends_the_flash_task_with_one_unexpected_entry() -> None:
    # The flash task is unsupervised, so its top persists an unexpected end. The real _led_on() absorbs
    # the LED's own raise, so the top is reached through a replaced helper.
    client = _make_client(ext_led=_FakeLED())
    run(client.pr.setup())
    run(client.set_wifi_led(status=True))

    def boom() -> None:
        raise RuntimeError("simulated flash helper fault")

    client._led_on = boom  # type: ignore[method-assign]  # replaced on this instance only

    async def scenario() -> bool:
        task = asyncio.create_task(client._flash_led(*_src_pattern("HOTSPOT")))
        for _ in range(10):  # bounded: the task ends on its first round
            await asyncio.sleep(0)
            if task.done():
                break
        return task.done()

    with FastAsyncSleep():
        assert run(scenario()) is True
    log = run(client.get_error_counter())
    assert _used_slots(log) == [code("E", "UNEXPECTED")]
    assert log["WIFI"]["ErrCount"] == 1


# ---------------------------------------------------------------------------
# LED patterns: one flash task, created only through _run_led_pattern(); every pattern obeys LEDWifiOn
# (silent while it is off). The phases are read from the recorded sleep_ms() requests, in milliseconds.
# ---------------------------------------------------------------------------


async def _drive(steps: int = 8) -> None:
    for _ in range(steps):  # parks: each one lets a fast-slept flash task run one phase
        await asyncio.sleep(0)


async def _until(done: "Callable[[], bool]", tries: int = 200) -> bool:
    # A condition wait bounded by yields: under _FastAsyncSleep every sleep is one yield, so no wall clock is involved.
    for _ in range(tries):
        if done():
            return True
        await asyncio.sleep(0)
    return done()


async def _stop_flash(client: WifiService) -> None:
    flash = client._ledflash
    assert flash is not None, "no flash task ran"
    await cancel(flash)
    client._ledflash = None


def _lit_client(*, led_on: bool = True) -> "tuple[WifiService, _FakeLED]":
    led = _FakeLED()
    client = _make_client(ext_led=led, hotspot_time_min=1)
    run(client.set_wifi_led(status=led_on))
    return client, led


def test_the_hotspot_pattern_is_on_2900_off_100() -> None:
    # Each phase is one sleep_ms() of an int: a phase allocates no float.
    client, led = _lit_client()
    fast = FastAsyncSleep()

    async def scenario() -> "list[int]":
        await client._hotspot_client_absent()
        await _drive()
        phases = fast.ms_of(client._ledflash)
        await _stop_flash(client)
        return phases

    with fast:
        phases = run(scenario())
    assert phases[:4] == list(_src_pattern("HOTSPOT")) * 2
    assert led.on_calls >= 2 and led.off_calls >= 1


def test_a_station_on_the_hotspot_runs_its_own_pattern() -> None:
    # A phone holding the AP shows an even slow blink, never a steady light that looks like a working home link.
    client, led = _lit_client()
    fast = FastAsyncSleep()

    async def scenario() -> "list[int]":
        client._hotspot_client_connected()
        await _drive()
        phases = fast.ms_of(client._ledflash)
        await _stop_flash(client)
        return phases

    with fast:
        phases = run(scenario())
    assert phases[:4] == list(_src_pattern("HOTSPOT_CLIENT")) * 2
    assert led.on_calls >= 2 and led.off_calls >= 1


def test_the_client_leaving_restores_the_hotspot_pattern() -> None:
    client, _led = _lit_client()
    fast = FastAsyncSleep()

    async def scenario() -> "tuple[list[int], bool]":
        client._hotspot_client_connected()
        await _drive()
        client_flash = client._ledflash
        await client._hotspot_client_absent()
        await _drive()
        phases = fast.ms_of(client._ledflash)
        await _stop_flash(client)
        return phases, client_flash is not None and client_flash.done()

    with fast:
        phases, swapped = run(scenario())
    assert phases[:4] == list(_src_pattern("HOTSPOT")) * 2
    assert swapped is True, "the client pattern's task was left running beside the hotspot pattern's"


def test_asking_for_the_running_pattern_keeps_its_task() -> None:
    client, _led = _lit_client()

    async def scenario() -> "tuple[bool, bool, bool, bool]":
        await client._hotspot_client_absent()
        first = client._ledflash
        await client._hotspot_client_absent()
        client._hotspot_client_connected()
        second = client._ledflash
        client._hotspot_client_connected()
        kept = (client._ledflash is second, first is not None and first is not second)
        await _drive(2)
        alive = second is not None and not second.done()
        await _stop_flash(client)
        return kept[0], kept[1], alive, first is not None and first.done()

    with FastAsyncSleep():
        assert run(scenario()) == (True, True, True, True)


def test_a_flash_task_that_ended_on_a_fault_is_started_again_by_the_next_request() -> None:
    # A pattern whose task already ended (its top persisted UNEXPECTED) is not "running": asking for it again,
    # as every hotspot and deactivated tick does, starts a fresh task instead of keeping a dead one.
    client, led = _lit_client()
    run(client.pr.setup())
    real_on = client._led_on

    def boom() -> None:
        raise RuntimeError("simulated flash helper fault")

    async def scenario() -> "tuple[bool, bool]":
        client._led_on = boom  # type: ignore[method-assign]  # replaced on this instance only
        await client._hotspot_client_absent()
        await _drive(2)
        first = client._ledflash
        ended = first is not None and first.done()
        client._led_on = real_on  # type: ignore[method-assign]  # the fault is gone
        await client._hotspot_client_absent()
        await _drive(2)
        lit = led.on_calls > 0
        await _stop_flash(client)
        return ended, lit

    with FastAsyncSleep():
        assert run(scenario()) == (True, True)
    assert _used_slots(run(client.get_error_counter())) == [code("E", "UNEXPECTED")]


def test_the_client_pattern_with_the_wifi_led_off_stays_dark() -> None:
    client, led = _lit_client(led_on=False)

    async def scenario() -> None:
        client._hotspot_client_connected()
        await _drive()
        await _stop_flash(client)

    with FastAsyncSleep():
        run(scenario())
    assert (led.on_calls, led.off_calls, led.toggle_calls) == (0, 0, 0)


def _deactivated_client(*, led_on: bool) -> "tuple[WifiService, _FakeLED]":
    # LEDWifiOn as stored, the phase already deactivated (it survives the loop's restart reset).
    led = _FakeLED()
    client = _make_client_with_json('{"LEDWifiOn": ' + ("true" if led_on else "false") + "}", ext_led=led)
    client._conn_phase = _PHASE_DEACTIVATED
    return client, led


def test_deactivated_with_the_led_enabled_blinks_100_on_2900_off() -> None:
    client, led = _deactivated_client(led_on=True)
    fast = FastAsyncSleep()

    async def scenario() -> "list[int]":
        task = asyncio.create_task(client._connect_loop())
        await _drive(12)
        phases = fast.ms_of(client._ledflash)
        await cancel(task)
        await _stop_flash(client)
        return phases

    with fast:
        phases = run(scenario())
    assert phases[:4] == list(_src_pattern("DEACTIVATED")) * 2
    assert led.on_calls >= 2 and led.off_calls >= 1


def test_deactivated_with_the_led_disabled_stays_dark() -> None:
    client, led = _deactivated_client(led_on=False)

    async def scenario() -> None:
        task = asyncio.create_task(client._connect_loop())
        await _drive(12)
        await cancel(task)
        await _stop_flash(client)

    with FastAsyncSleep():
        run(scenario())
    assert (led.on_calls, led.off_calls, led.toggle_calls) == (0, 0, 0)


def test_turning_the_wifi_led_on_while_deactivated_starts_its_pattern() -> None:
    # The setting changes through the LEDWifiOn config-apply path; the running pattern lights from its next phase.
    client, led = _deactivated_client(led_on=False)

    async def scenario() -> "tuple[int, WriteValidity]":
        task = asyncio.create_task(client._connect_loop())
        await _drive(6)
        dark = led.on_calls
        results = await client._set_dict_cfg({"LEDWifiOn": True}, client.get_cfg_schema())
        await _drive(6)
        await cancel(task)
        await _stop_flash(client)
        return dark, results

    with FastAsyncSleep():
        dark, results = run(scenario())
    assert results == {"LEDWifiOn": "Valid"}
    assert dark == 0
    assert led.on_calls >= 1 and led.off_calls >= 1


def test_turning_the_wifi_led_off_mid_pattern_goes_dark() -> None:
    client, led = _deactivated_client(led_on=True)

    async def scenario() -> "tuple[WriteValidity, tuple[int, int, int]]":
        task = asyncio.create_task(client._connect_loop())
        await _drive(6)
        results = await client._set_dict_cfg({"LEDWifiOn": False}, client.get_cfg_schema())
        after = (led.on_calls, led.off_calls, led.toggle_calls)
        await _drive(6)
        await cancel(task)
        await _stop_flash(client)
        return results, after

    with FastAsyncSleep():
        results, after = run(scenario())
    assert results == {"LEDWifiOn": "Valid"}
    assert led.state is False  # the setter's own off
    assert (led.on_calls, led.off_calls, led.toggle_calls) == after, "the pattern kept lighting a disabled LED"


def _silent_led_run(*, led_on: bool) -> "tuple[_FakeLED, list[tuple[int, int, int]]]":
    # A seeking unit, lit, goes silent; one attempt polls without a verdict; then a period links. Returns the
    # (on, off, toggle) counts after the entry, after the attempt and the setter, and after the link.
    led = _FakeLED()
    client = _make_client_with_json(_stored_json(led_on=led_on), conn_fail_to_hotspot=1, ext_led=led)
    run(client.pr.setup())
    run(client.set_wifi_led(status=led_on))
    client._hotspot_timeout_trigger_event = _ParkedFlag()  # type: ignore[assignment]  # see _ParkedFlag
    client._hotspot_started_once = True
    client._led_on()  # lit, as a seeking unit's poll can leave it
    _wlan(client)._status = network.STAT_CONNECTING  # every poll of the attempt toggles, as a real one does
    counts: list[tuple[int, int, int]] = []

    def snap() -> None:
        counts.append((led.on_calls, led.off_calls, led.toggle_calls))

    async def scenario() -> None:
        watcher = client.start_asy_hotspot_timeout()
        await client._register_sta_connection_failure()
        snap()
        await _fire_period(client)
        await client.set_wifi_led(status=True)  # recorded, lighting nothing while silent
        snap()
        _joins(client)
        await _fire_period(client)
        snap()
        await cancel(watcher)

    with FastAsyncSleep():
        run(scenario())
    assert client._conn_phase == _PHASE_STA_ESTABLISHED, client._conn_phase
    return led, counts


def test_the_silent_mode_keeps_the_led_dark_until_a_link() -> None:
    # Dark whatever LEDWifiOn says, until a link (owner, 2026-10-08: "The WiFi LED stays dark, even if it is activated,
    # being completely silent in that mode. It should look like turned off."); _led_off() still acts.
    led, counts = _silent_led_run(led_on=True)
    entered, attempted, linked = counts
    assert entered == (1, 1, 0), "the entry turns the lit LED off once"
    assert (attempted[0], attempted[2]) == (1, 0), "the attempt's poll or the setter lit the LED while silent"
    assert linked[0] == 2 and led.state is True, "the link lights the LED as LEDWifiOn says"
    led, counts = _silent_led_run(led_on=False)
    assert [(on, toggle) for on, _off, toggle in counts] == [(0, 0)] * 3 and led.state is not True


def test_no_led_helper_lights_while_silent() -> None:
    # Each helper the silent mode guards lights nothing, and no flash task starts whichever pattern is asked for;
    # _led_off() still acts.
    client, led = _lit_client()
    client._conn_phase = _PHASE_SILENT
    client._led_on()
    client._led_toggle()
    for name in ("HOTSPOT", "HOTSPOT_CLIENT", "DEACTIVATED"):
        client._run_led_pattern(*_src_pattern(name))
        assert client._ledflash is None, name
    client._led_off()
    assert (led.on_calls, led.toggle_calls, led.off_calls, led.state) == (0, 0, 1, False)


def test_turning_the_wifi_led_on_while_silent_lights_nothing_until_the_link() -> None:
    # The LEDWifiOn push while silent stores and selects the LED but lights nothing, not even through a period's
    # attempt; the setting shows from the first link.
    led = _FakeLED()
    client = _silent_client(led=led)
    _wlan(client)._status = network.STAT_CONNECTING  # the failing attempt polls its full window, toggling each poll

    async def scenario() -> "tuple[WriteValidity, int, int]":
        watcher = client.start_asy_hotspot_timeout()
        results = await client._set_dict_cfg({"LEDWifiOn": True}, client.get_cfg_schema())
        await _fire_period(client)
        dark = led.on_calls + led.toggle_calls
        _joins(client)
        await _fire_period(client)
        await cancel(watcher)
        return results, dark, led.on_calls

    with FastAsyncSleep():
        results, dark, lit = run(scenario())
    assert results == {"LEDWifiOn": "Valid"} and client._led is led
    assert dark == 0, "the push or the attempt lit the LED while silent"
    assert (client._conn_phase, lit, led.state) == (_PHASE_STA_ESTABLISHED, 1, True)


# ---------------------------------------------------------------------------
# _push_wifi_led / self._push_callbacks - the generic setter dispatch's per-field live-push
# registration (asy_base_classes.py's _set_dict_cfg), registered once at construction (project
# decision), not passed per-call.
# ---------------------------------------------------------------------------


def test_push_wifi_led_reports_success_for_a_well_typed_no_op() -> None:
    # A push whose value type checks out reports success even when the setter changes nothing.
    client = _make_client(ext_led=_FakeLED())
    assert run(client._push_wifi_led(False)) is True  # the LED is already off
    assert run(client._push_wifi_led(False)) is True
    assert run(client._push_wifi_led(True)) is True
    assert run(client._push_wifi_led(True)) is True  # already on


def test_led_wifi_on_push_callback_is_registered_at_construction() -> None:
    client = _make_client(ext_led=_FakeLED())
    assert "LEDWifiOn" in client._push_callbacks


def test_push_callbacks_registered_for_led_wifi_on_only() -> None:
    # Exhaustive, not just "LEDWifiOn is present": SSID/PW/Country/Hostname are persist-only and
    # must have no push entry; the external LED arrives at construction, never through a setter.
    client = _make_client(ext_led=_FakeLED())
    assert set(client._push_callbacks) == {"LEDWifiOn"}


def test_led_wifi_on_push_callback_applies_the_value_through_set_wifi_led() -> None:
    led = _FakeLED()
    client = _make_client(ext_led=led)
    callback = client._push_callbacks["LEDWifiOn"]
    assert run(_push(callback, True)) is True
    assert client._led is led


def test_led_wifi_on_push_narrowing_arm_returns_false_for_a_non_bool() -> None:
    # _set_dict_cfg only ever invokes a push callback with an already schema-validated value (real
    # bool, by construction) - this guards the type for the checker and as defense-in-depth, not
    # because a real caller can reach it with the wrong type.
    client = _make_client(ext_led=_FakeLED())
    callback = client._push_callbacks["LEDWifiOn"]
    assert run(_push(callback, "not a bool")) is False
    assert run(_push(callback, 1)) is False


def test_set_dict_cfg_led_wifi_on_end_to_end_persists_and_pushes() -> None:
    # Full integration: the generic dispatch persists LEDWifiOn to config_WIFI.cfg *and* pushes it
    # live through set_wifi_led, in one call - exactly the shape a future REST endpoint will use.
    led = _FakeLED()
    client = _make_client(ext_led=led)
    results = run(client._set_dict_cfg({"LEDWifiOn": False}, client.get_cfg_schema()))
    assert results == {"LEDWifiOn": "Valid"}
    assert client._led is None  # pushed: turned off and cleared
    assert run(client.cfgmgr.get_dict(["LEDWifiOn"])) == {"LEDWifiOn": False}  # persisted too


def test_set_dict_cfg_multiple_invalid_fields_reported_independently() -> None:
    # Mirrors asy_ntp_client.py's own multi-invalid _set_dict_cfg coverage - this driver had no
    # multi-field _set_dict_cfg test beyond the single-field LEDWifiOn one above, despite four
    # persist-only string fields each with their own min/max/special validation.
    led = _FakeLED()
    client = _make_client(ext_led=led)
    results = run(
        client._set_dict_cfg(
            # LEDWifiOn's schema default is True - False here is a real change, not the "Unchanged"
            # no-push outcome True would trivially produce.
            {"Hostname": "NewHost", "PW": "short", "Country": "United States", "LEDWifiOn": False},
            client.get_cfg_schema(),
        ),
    )
    assert results == {"Hostname": "Valid", "PW": "Invalid", "Country": "Invalid", "LEDWifiOn": "Valid"}
    assert client._led is None  # pushed: LEDWifiOn=False turns the LED off and clears it
    stored = run(client.cfgmgr.get_dict(["Hostname", "PW", "Country"]))
    assert stored == {"Hostname": "NewHost", "PW": "", "Country": "DE"}  # both invalid, left at their defaults


# ---------------------------------------------------------------------------
# _VAL_PW bounds - WPA2-PSK ASCII passphrase spec (8-63 chars if used; empty is its own distinct
# "open network, no security" case, not just a short/weak password) - see CLAUDE.md/SPECIFICATION.md
# for the reasoning; SSID's own 0-32 bound was already correct and needed no change.
# ---------------------------------------------------------------------------


def test_pw_empty_string_is_valid_via_the_open_network_special_bypass() -> None:
    client = _make_client_with_json(
        '{"SSID": "MyNetwork", "PW": "", "Country": "US", "Hostname": "TestNode", "LEDWifiOn": false}',
    )
    values = run(client.cfgmgr.get_dict(["PW"]))
    assert values == {"PW": ""}


def test_pw_below_wpa2_minimum_length_falls_back_to_default() -> None:
    # 7 characters - one short of WPA2-PSK's real 8-character minimum - is neither the empty-string
    # special case nor a valid in-range password, so it's rejected like any other out-of-range value.
    json_text = '{"SSID": "MyNetwork", "PW": "short12", "Country": "US", "Hostname": "TestNode", "LEDWifiOn": false}'
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(["PW"]))
    assert values == {"PW": ""}  # defaulted, not the too-short value


def test_pw_at_wpa2_minimum_length_is_accepted() -> None:
    json_text = '{"SSID": "MyNetwork", "PW": "exactly8", "Country": "US", "Hostname": "TestNode", "LEDWifiOn": false}'
    client = _make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(["PW"]))
    assert values == {"PW": "exactly8"}


def test_write_config_pw_below_minimum_is_marked_invalid_not_silently_dropped() -> None:
    client = _make_client()
    ok, results = run(client.cfgmgr.write_config({"PW": "short"}))
    assert ok is True
    assert results == {"PW": "Invalid"}
    assert run(client.cfgmgr.get_dict(["PW"])) == {"PW": ""}  # untouched default


def test_write_config_pw_empty_string_is_valid_and_resets_to_open_network() -> None:
    client = _make_client_with_json(_VALID_JSON)  # starts with a real "supersecret" password
    ok, results = run(client.cfgmgr.write_config({"PW": ""}))
    assert ok is True
    assert results == {"PW": "Valid"}
    assert run(client.cfgmgr.get_dict(["PW"])) == {"PW": ""}


# ---------------------------------------------------------------------------
# wifi_mode_lock is taken with `async with`: released on every exit, a raise and a cancel included
# ---------------------------------------------------------------------------


def test_locked_wlan_status_releases_the_lock_even_if_the_status_read_raises() -> None:
    # Both of these finally bodies read as uncovered, which SPECIFICATION.md Part E.5.1 calls out
    # as a real missing test rather than a tracer artefact: a finally only fires a trace event when
    # something actually passes through it. A wedged wifi_mode_lock stalls every later mode change.
    client = _make_client()

    def boom() -> int:
        raise RuntimeError("simulated status read fault")

    client._wlan_status_or_none = boom  # type: ignore[method-assign]  # deliberate monkeypatch

    async def scenario() -> bool:
        try:
            await client._locked_wlan_status()
        except RuntimeError:
            return True
        return False

    assert run(scenario()) is True
    assert not client.wifi_mode_lock.locked(), "the wifi mode lock leaked when the status read raised"


def test_get_hotspot_stations_releases_the_lock_when_cancelled_mid_call() -> None:
    # The other finally, reached the way it really would be: this one awaits a settle sleep while
    # holding the lock, so a supervisor-driven cancellation can land inside the critical section.
    client = _make_client()

    async def scenario() -> None:
        task = asyncio.create_task(client._get_hotspot_stations())
        await asyncio.sleep(0)  # a park: the call takes the lock and reaches its settle sleep, checked below
        assert client.wifi_mode_lock.locked(), "the call did not take the lock, so this proves nothing"
        await cancel(task)

    run(scenario())
    assert not client.wifi_mode_lock.locked(), "the wifi mode lock leaked on cancellation"


def test_get_hotspot_stations_settles_once_in_milliseconds_before_the_query() -> None:
    client = _make_client()
    fast = FastAsyncSleep()
    wlan = _wlan(client)
    real_status = wlan.status
    settled_at_query: list[list[int]] = []  # the call's settles so far, at each stations query

    def status(*params: str) -> object:
        if params == ("stations",):
            settled_at_query.append(fast.ms_of(asyncio.current_task()))
        return real_status(*params)

    async def scenario() -> "list[int]":
        await client._get_hotspot_stations()
        return fast.ms_of(asyncio.current_task())

    wlan.status = status  # type: ignore[method-assign]  # records each stations query, the fake's own status() answering
    with fast:
        assert run(scenario()) == [_HOTSPOT_STATIONS_SETTLE_MS]
    assert settled_at_query == [[_HOTSPOT_STATIONS_SETTLE_MS]], settled_at_query


def test_handle_reconnect_trigger_cancels_a_running_ledflash_task() -> None:
    # The hotspot LED flasher is a real task; a reconnect that left it running would keep blinking
    # the hotspot pattern after the mode change, and leak the task for the rest of the uptime.
    client = _make_client(hotspot_time_min=1)
    run(client._hotspot_client_absent())  # arms the shutoff timer and starts a real _ledflash task

    async def scenario() -> "asyncio.Task[None]":
        await asyncio.sleep(0)  # a park: the flash task starts
        flash = client._ledflash
        assert flash is not None, "no _ledflash task to cancel, so this proves nothing"
        await client._handle_reconnect_trigger()
        await asyncio.sleep(0)  # a park: the cancelled task runs to its end; done() below checks it
        return flash

    with FastAsyncSleep():  # the trigger's caller grace and settle waits
        flash = run(scenario())
    assert client._ledflash is None, "_handle_reconnect_trigger() left its _ledflash reference behind"
    # done(), not cancelled(): MicroPython's Task has no cancelled() at all (see typings/).
    assert flash.done(), "the _ledflash task was dropped rather than cancelled"


# ---------------------------------------------------------------------------
# get_data()/get_dict_data() - the cached-reading convention: backed by _uptime_loop()'s 1Hz push
# (_update_wifi_snapshot()), not a live lock-aware query - see get_data()'s own comment on why.
# ---------------------------------------------------------------------------


def test_get_data_reflects_the_initial_never_connected_state() -> None:
    client = _make_client()
    assert run(client.get_data()) == WIFI(None, None, None, None, None, None, None, None)


def test_get_data_returns_the_cached_snapshot_not_a_live_query() -> None:
    client = _make_client()
    snapshot = WIFI(Mode="STA", Connected=True, IP="10.0.0.5", Subnet="255.255.255.0", Gateway="10.0.0.1", DNS="10.0.0.53", RSSI=-61, TS=12345)
    run(client._set_meas_data(snapshot))
    assert run(client.get_data()) == snapshot


def test_get_dict_data_wraps_get_data_under_the_wifi_key() -> None:
    client = _make_client()
    run(client._set_meas_data(WIFI(Mode="AP", Connected=False, IP=None, Subnet=None, Gateway=None, DNS=None, RSSI=None, TS=999)))
    dict_data = run(client.get_dict_data())
    assert dict_data == {"WIFI": {"Mode": "AP", "Connected": False, "IP": None, "Subnet": None, "Gateway": None, "DNS": None, "RSSI": None, "TS": 999}}


# ---------------------------------------------------------------------------
# _update_wifi_snapshot() - one 8-field WIFI tuple per _uptime_loop() tick, the radio read once; every
# networking getter answers from it, never from the radio (SPECIFICATION.md C.8)
# ---------------------------------------------------------------------------


def _record_calls(wlan: object, method: str) -> "list[tuple[object, ...]]":
    # Wraps one WLAN-fake method so a test sees every call the code made; tests/network.py records none.
    real = getattr(wlan, method)
    calls: list[tuple[object, ...]] = []

    def recorded(*args: object) -> object:
        calls.append(args)
        return real(*args)

    setattr(wlan, method, recorded)
    return calls


def test_update_wifi_snapshot_sta_mode_reports_the_four_addresses_and_the_rssi() -> None:
    client = _make_client()
    _wlan(client)._ifconfig = ("192.168.1.42", "255.255.255.0", "192.168.1.1", "192.168.1.53")
    _wlan(client)._rssi = -61
    ifconfig_calls = _record_calls(_wlan(client), "ifconfig")
    status_calls = _record_calls(_wlan(client), "status")
    run(client._update_wifi_snapshot(connected=True))
    data = run(client.get_data())
    assert (data.Mode, data.Connected, data.RSSI) == ("STA", True, -61)
    assert (data.IP, data.Subnet, data.Gateway, data.DNS) == ("192.168.1.42", "255.255.255.0", "192.168.1.1", "192.168.1.53")
    assert len(ifconfig_calls) == 1, "one ifconfig() read per snapshot"
    assert status_calls == [("rssi",)], "one rssi read, only while STA has a link"


def test_hotspot_snapshot_has_no_rssi() -> None:
    # status("rssi") raises ValueError("STA required") outside STA (extmod/network_cyw43.c, v1.29.0), so
    # the snapshot never asks once the AP interface is selected - not even while the AP reports a link.
    client = _make_client()
    with FastAsyncSleep():
        run(client._switch_wlan_mode(network.AP_IF))
    client._conn_phase = _PHASE_HOTSPOT
    _wlan(client)._ifconfig = ("192.168.4.1", "255.255.255.0", "192.168.4.1", "0.0.0.0")
    status_calls = _record_calls(_wlan(client), "status")
    run(client._update_wifi_snapshot(connected=True))
    data = run(client.get_data())
    assert (data.Mode, data.Connected, data.IP, data.RSSI) == ("AP", True, "192.168.4.1", None)
    assert status_calls == []


def test_a_snapshot_without_a_link_has_no_rssi_and_no_dhcp_dns() -> None:
    client = _make_client()
    _wlan(client)._ifconfig = ("0.0.0.0", "255.255.255.0", "0.0.0.0", "0.0.0.0")
    status_calls = _record_calls(_wlan(client), "status")
    run(client._update_wifi_snapshot(connected=False))
    data = run(client.get_data())
    assert (data.Mode, data.Connected, data.RSSI) == ("STA", False, None)
    assert status_calls == []
    assert client.get_dns_server_ip() is None


def test_deactivated_snapshot_makes_no_radio_call() -> None:
    client = _make_client()
    _wlan(client)._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "10.0.0.53")
    run(client._update_wifi_snapshot(connected=True))  # a DHCP DNS held from before
    client._conn_phase = _PHASE_DEACTIVATED
    ifconfig_calls = _record_calls(_wlan(client), "ifconfig")
    status_calls = _record_calls(_wlan(client), "status")
    run(client._update_wifi_snapshot(connected=False))
    data = run(client.get_data())
    assert (data.Mode, data.Connected) == ("STA", False)
    assert (data.IP, data.Subnet, data.Gateway, data.DNS, data.RSSI) == (None, None, None, None, None)
    assert ifconfig_calls == [] and status_calls == []
    assert client.get_dns_server_ip() is None


def test_update_wifi_snapshot_degrades_to_none_addresses_when_ifconfig_raises() -> None:
    client = _make_client()
    _wlan(client).raise_on["ifconfig"] = OSError("simulated ifconfig failure")
    run(client._update_wifi_snapshot(connected=True))  # must not raise
    data = run(client.get_data())
    assert (data.IP, data.Subnet, data.Gateway, data.DNS) == (None, None, None, None)
    assert (data.Connected, data.RSSI) == (True, -50)  # the rest of the snapshot is unaffected
    assert client.get_dns_server_ip() is None


def test_a_failed_rssi_read_publishes_none_and_keeps_the_rest() -> None:
    client = _make_client()
    _wlan(client)._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "10.0.0.53")
    _wlan(client).raise_on["status"] = OSError("simulated rssi failure")
    run(client._update_wifi_snapshot(connected=True))  # must not raise
    data = run(client.get_data())
    assert (data.IP, data.DNS, data.RSSI) == ("10.0.0.5", "10.0.0.53", None)


def test_get_dns_server_ip_returns_the_dhcp_dns_of_the_last_snapshot() -> None:
    client = _make_client()
    _wlan(client)._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "192.168.1.1")
    assert client.get_dns_server_ip() is None  # no snapshot yet
    run(client._update_wifi_snapshot(connected=True))
    assert client.get_dns_server_ip() == "192.168.1.1"


def test_get_dns_server_ip_returns_the_last_snapshot_value_while_the_lock_is_held() -> None:
    # The DNS server NTP needs is never lost because WiFi holds the lock when NTP samples it.
    client = _make_client()
    _wlan(client)._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "192.168.1.1")
    run(client._update_wifi_snapshot(connected=True))
    run(client.wifi_mode_lock.acquire())
    try:
        assert client.get_dns_server_ip() == "192.168.1.1"
    finally:
        client.wifi_mode_lock.release()


def test_get_dns_server_ip_reads_no_radio() -> None:
    client = _make_client()
    _wlan(client)._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "192.168.1.1")
    run(client._update_wifi_snapshot(connected=True))
    _wlan(client).raise_on["ifconfig"] = OSError("a getter that read the radio would see this")
    ifconfig_calls = _record_calls(_wlan(client), "ifconfig")
    assert client.get_dns_server_ip() == "192.168.1.1"
    assert ifconfig_calls == []


# ---------------------------------------------------------------------------
# _uptime_loop() - short-circuits while deactivated, pushes a fresh snapshot every tick otherwise,
# and counts the measured link time (TickSeconds) while connected, zero otherwise
# ---------------------------------------------------------------------------


def test_uptime_loop_short_circuits_and_zeroes_uptime_while_deactivated() -> None:
    with DrivenTime(asy_base_classes) as clock:
        client = _make_client()
        client._conn_phase = _PHASE_DEACTIVATED

        async def scenario() -> "tuple[int, bool | None]":
            task = asyncio.create_task(client._uptime_loop())
            for _ in range(2):
                clock.advance(1000)
                await tick(client._time_counter_trigger_event)
            uptime = await client.get_wifi_uptime()
            data = await client.get_data()
            await cancel(task)
            return uptime, data.Connected

        uptime, connected = run(scenario())
    assert uptime == 0
    assert connected is False


def test_uptime_loop_counts_measured_seconds_while_connected() -> None:
    with DrivenTime(asy_base_classes) as clock:
        client = _make_client()
        _wlan(client)._status = network.STAT_GOT_IP

        async def scenario() -> int:
            task = asyncio.create_task(client._uptime_loop())
            await asyncio.sleep(0)
            for _ in range(3):
                clock.advance(1000)
                await tick(client._time_counter_trigger_event)
            uptime = await client.get_wifi_uptime()
            await cancel(task)
            return uptime

        assert run(scenario()) == 3


def test_a_delayed_wake_advances_uptime_by_the_measured_time() -> None:
    # One wake-up 2.5 s after the last: the uptime grows by the 2 whole seconds that passed, not by 1
    # per wake-up, so a dropped or late soft-Timer callback costs latency only (SPECIFICATION.md C.9).
    with DrivenTime(asy_base_classes) as clock:
        client = _make_client()
        _wlan(client)._status = network.STAT_GOT_IP

        async def scenario() -> int:
            task = asyncio.create_task(client._uptime_loop())
            await asyncio.sleep(0)
            clock.advance(2500)
            await tick(client._time_counter_trigger_event)
            uptime = await client.get_wifi_uptime()
            await cancel(task)
            return uptime

        assert run(scenario()) == 2


def test_uptime_loop_resets_uptime_while_not_connected() -> None:
    with DrivenTime(asy_base_classes) as clock:
        client = _make_client()
        _wlan(client)._status = network.STAT_IDLE

        async def scenario() -> int:
            task = asyncio.create_task(client._uptime_loop())
            for _ in range(2):
                clock.advance(1000)
                await tick(client._time_counter_trigger_event)
            uptime = await client.get_wifi_uptime()
            await cancel(task)
            return uptime

        assert run(scenario()) == 0


# ---------------------------------------------------------------------------
# Observation-tier helpers: a status/isconnected/ifconfig *query* failing degrades silently
# (returns a safe sentinel) instead of raising or feeding get_error_counter()
# ---------------------------------------------------------------------------


def test_wlan_status_or_none_returns_the_real_status() -> None:
    client = _make_client()
    _wlan(client)._status = network.STAT_CONNECTING
    assert client._wlan_status_or_none() == network.STAT_CONNECTING


def test_wlan_status_or_none_returns_none_on_exception() -> None:
    client = _make_client()
    _wlan(client).raise_on["status"] = OSError("simulated")
    assert client._wlan_status_or_none() is None


def test_wlan_isconnected_or_false_returns_false_on_exception() -> None:
    client = _make_client()
    _wlan(client).raise_on["isconnected"] = OSError("simulated")
    assert client._wlan_isconnected_or_false() is False


def _available_locked(client: WifiService) -> bool:
    # network_available_locked() under the lock its caller must hold, as NTPClient calls it.
    async def held() -> bool:
        async with client.wifi_mode_lock:
            return client.network_available_locked()

    return run(held())


def test_network_available_true_only_in_sta_mode_with_an_ip() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_STA_SEEKING
    _wlan(client)._status = network.STAT_GOT_IP
    assert _available_locked(client) is True


def test_network_available_false_in_hotspot_mode_even_with_an_ip() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_HOTSPOT
    _wlan(client)._status = network.STAT_GOT_IP
    assert _available_locked(client) is False


def test_network_available_false_on_a_status_exception() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_STA_SEEKING
    _wlan(client).raise_on["status"] = OSError("simulated")
    assert _available_locked(client) is False  # degrades via _wlan_status_or_none(), not a raise


# ---------------------------------------------------------------------------
# is_hotspot_active() - lock-free getter for asy_webserver_service.py's captive-portal redirect
# fallback (SPECIFICATION.md Part A.5). All five _conn_phase values are exercised: a regression
# narrowed to, say, _PHASE_DEACTIVATED or _PHASE_SILENT alone would slip past a two-case test.
# ---------------------------------------------------------------------------


def test_is_hotspot_active_true_in_hotspot_phase() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_HOTSPOT
    assert client.is_hotspot_active() is True


def test_is_hotspot_active_false_in_sta_seeking_phase() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_STA_SEEKING
    assert client.is_hotspot_active() is False


def test_is_hotspot_active_false_in_sta_established_phase() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_STA_ESTABLISHED
    assert client.is_hotspot_active() is False


def test_is_hotspot_active_false_in_deactivated_phase() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_DEACTIVATED
    assert client.is_hotspot_active() is False


def test_is_hotspot_active_false_in_silent_phase() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_SILENT
    assert client.is_hotspot_active() is False


def test_is_hotspot_active_dynamic_mode_switch_reflects_live_state_not_cached() -> None:
    # Dynamic-mode-switch coverage: a plain int-compare getter with no caching must track
    # _conn_phase live on the SAME client instance across repeated calls. Every other test above
    # uses a fresh _make_client() per phase, which alone wouldn't catch a memoization bug.
    client = _make_client()
    for phase, expected in (
        (_PHASE_STA_SEEKING, False),
        (_PHASE_HOTSPOT, True),
        (_PHASE_STA_ESTABLISHED, False),
        (_PHASE_HOTSPOT, True),
        (_PHASE_DEACTIVATED, False),
        (_PHASE_HOTSPOT, True),
        (_PHASE_SILENT, False),
    ):
        client._conn_phase = phase
        assert client.is_hotspot_active() is expected, f"phase {phase} -> expected {expected}"


# ---------------------------------------------------------------------------
# Compound scenario: an established connection's outage retry (_on_sta_disconnected()'s
# _STA_RETRY_AFTER_LOSS_S wait) is in flight while a REST-facing getter runs in a second task - the
# shape GET /status or GET /networking sees during a live 60 s retry window.
# ---------------------------------------------------------------------------


def test_status_getters_return_the_last_snapshot_during_an_outage_retry() -> None:
    client = _make_client(conn_fail_to_hotspot=2)
    _wlan(client)._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "10.0.0.53")
    run(client._update_wifi_snapshot(connected=True))  # the last tick before the outage
    snapshot = run(client.get_data())
    client._conn_phase = _PHASE_STA_ESTABLISHED
    _wlan(client)._connected = False
    _wlan(client).raise_on["ifconfig"] = OSError("a getter that read the radio would see this")

    async def no_attempt() -> None:
        return None  # the connect attempt is not under test: the retry wait after it is

    client._attempt_sta_connect = no_attempt  # type: ignore[method-assign]  # a test double

    async def scenario() -> "tuple[tuple[WIFI, str | None, bool], bool, bool]":
        task = asyncio.create_task(client._run_sta_mode())
        for _ in range(10):
            await asyncio.sleep(0)
        answers = (await client.get_data(), client.get_dns_server_ip(), client.is_hotspot_active())
        still_waiting = not task.done()
        taken = False
        if not client.wifi_mode_lock.locked():  # an NTP attempt would take the lock at once
            async with client.wifi_mode_lock:
                taken = True
        await cancel(task)
        return answers, still_waiting, taken

    answers, still_waiting, taken = run(scenario())
    assert still_waiting is True, "the 60 s retry wait finished early - the getters were not read during it"
    assert answers == (snapshot, "10.0.0.53", False)
    assert taken is True, "the retry wait held wifi_mode_lock"
    # The ESTABLISHED branch is a patient retry, never an escalation toward the hotspot.
    assert client._connection_failures == 0


def test_reconnect_wifi_sets_the_trigger_and_tears_down_hotspot_bookkeeping() -> None:
    client = _make_client(hotspot_time_min=1)
    run(client._hotspot_client_absent())  # arms _hotspot_timer + starts a real _ledflash task

    async def scenario() -> "tuple[bool, bool, bool]":
        await asyncio.sleep(0)
        ledflash_before = client._ledflash
        client.reconnect_wifi()
        ledflash_cleared = (ledflash_before is not None) and (client._ledflash is None)
        assert ledflash_before is not None
        await cancel(ledflash_before)  # let the cancellation actually settle
        return client._reconn_wifi, client._hotspot_timer_running, ledflash_cleared

    reconn, timer_running, ledflash_cleared = run(scenario())
    assert reconn is True
    assert client._reconnect_fresh is True  # the settings hook: the next iteration lands in the fresh-boot state
    assert timer_running is False
    assert ledflash_cleared is True


# ---------------------------------------------------------------------------
# _hotspot_client_connected() / _hotspot_client_absent() - the hotspot auto-shutoff timer
# ---------------------------------------------------------------------------


def test_hotspot_client_connected_stops_the_shutoff_timer_and_starts_the_client_pattern() -> None:
    led = _FakeLED()
    client = _make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    client._hotspot_timer.init(period=5000, mode=Timer.ONE_SHOT, callback=lambda _b: None)

    async def scenario() -> None:
        client._hotspot_client_connected()
        await asyncio.sleep(0)  # a park: the pattern's task runs its first, lit phase
        await _stop_flash(client)

    run(scenario())
    assert client._hotspot_timer.deinit_called is True
    assert client._led_pattern == _src_pattern("HOTSPOT_CLIENT")
    assert led.on_calls == 1


def test_hotspot_client_absent_arms_the_shutoff_timer_once() -> None:
    client = _make_client(hotspot_time_min=1)
    run(client._hotspot_client_absent())
    assert client._hotspot_timer_running is True
    assert client._hotspot_timer.mode == Timer.PERIODIC  # C.9: a dropped fire is re-fired next period
    assert client._hotspot_timer.period == 60000  # hotspot_time_min=1 -> 60000ms


def test_hotspot_client_absent_shutoff_timer_fires_reconnect() -> None:
    # The Timer callback itself only sets _hotspot_timeout_trigger_event (no business logic inside
    # the IRQ callback, see C.9) - _hotspot_timeout_loop() is the coroutine that actually ends the
    # window (_on_hotspot_window_end()) once woken by that flag.
    client = _make_client(hotspot_time_min=1)
    run(client._hotspot_client_absent())

    async def scenario() -> bool:
        watcher = client.start_asy_hotspot_timeout()
        client._hotspot_timer.trigger()
        await asyncio.sleep(0)
        result = client._reconn_wifi
        await cancel(watcher)
        return result

    assert run(scenario()) is True


def test_hotspot_timeout_watcher_ends_the_window_when_woken() -> None:
    # The window's end, not the settings hook: the reconnect is set without the fresh-boot flag.
    client = _make_client(hotspot_time_min=1)
    run(client._hotspot_client_absent())  # arms _hotspot_timer + starts a real _ledflash task
    ledflash_before = client._ledflash

    async def scenario() -> "tuple[bool, bool]":
        watcher = client.start_asy_hotspot_timeout()
        client._hotspot_timeout_trigger_event.set()
        await asyncio.sleep(0)
        result = (client._reconn_wifi, client._reconnect_fresh)
        await cancel(watcher)
        assert ledflash_before is not None
        await cancel(ledflash_before)  # the window end already cancelled it - let it settle
        return result

    assert run(scenario()) == (True, False)
    assert client._ledflash is None and client._hotspot_timer_running is False


def test_a_dropped_hotspot_timer_fire_is_recovered_by_the_next_period() -> None:
    # The soft-callback drop (Part F.1): the first period's fire never reaches the flag. PERIODIC
    # keeps the timer armed, so the next period's fire still reconnects - no backstop needed.
    client = _make_client(hotspot_time_min=1)
    run(client._hotspot_client_absent())
    timer = client._hotspot_timer

    async def scenario() -> "tuple[bool, bool]":
        watcher = client.start_asy_hotspot_timeout()
        timer.drop()  # period 1's callback is lost
        await asyncio.sleep(0)
        after_drop = client._reconn_wifi
        timer.trigger()  # period 2
        for _ in range(5):  # a watcher already parked in wait() wakes through the poller, not at once
            await asyncio.sleep(0)
        result = client._reconn_wifi
        await cancel(watcher)
        return after_drop, result

    assert run(scenario()) == (False, True)


def test_the_first_delivered_hotspot_fire_stops_the_periodic_timer() -> None:
    # The window end deinits the timer, so PERIODIC never turns into a reconnect every period.
    client = _make_client(hotspot_time_min=1)
    run(client._hotspot_client_absent())
    timer = client._hotspot_timer

    async def scenario() -> None:
        watcher = client.start_asy_hotspot_timeout()
        timer.trigger()
        await asyncio.sleep(0)
        await cancel(watcher)

    run(scenario())
    assert timer.deinit_called is True
    assert client._hotspot_timer_running is False
    assert timer.callback is None  # nothing left to fire


def test_the_watcher_dispatches_by_phase() -> None:
    # Silent: a wake marks one connect attempt due and sets no reconnect, a second wake while it is due adds none.
    # Any other phase: the wake ends the window, the reconnect set without the fresh-boot flag.
    client = _silent_client()
    _wlan(client)._status = network.STAT_NO_AP_FOUND

    async def wakes(times: int) -> None:
        for _ in range(times):
            client._hotspot_timeout_trigger_event.set()
            await _drive(2)

    async def scenario() -> "tuple[tuple[bool, bool], int, list[tuple[int, bool, bool, bool]]]":
        watcher = client.start_asy_hotspot_timeout()
        await asyncio.sleep(0)  # a park: the watcher waits on its flag
        await wakes(2)
        due = (client._silent_attempt_due, client._reconn_wifi)
        for _ in range(2):  # one attempt for both wakes, none for the second iteration
            await client._run_silent_mode()
        attempts = len(_wlan(client).connect_calls)
        others = []
        for phase in (_PHASE_HOTSPOT, _PHASE_STA_SEEKING, _PHASE_STA_ESTABLISHED, _PHASE_DEACTIVATED):
            client._conn_phase = phase
            client._reconn_wifi = False
            await client._arm_hotspot_timer()
            await wakes(1)
            others.append((phase, client._reconn_wifi, client._reconnect_fresh, client._hotspot_timer_running))
        await cancel(watcher)
        return due, attempts, others

    with FastAsyncSleep():
        due, attempts, others = run(scenario())
    assert due == (True, False)
    assert attempts == 1
    assert others == [(other[0], True, False, False) for other in others], others
    assert client._silent_attempt_due is False


def test_the_window_end_keeps_its_meaning() -> None:
    # The window's end retries the stored network once more with the hotspot already used: a failed streak then goes
    # silent (owner, 2026-10-08: "Entering the hotspot mode only through a reboot, as is.").
    client = _make_client(conn_fail_to_hotspot=2, hotspot_time_min=1)
    run(client.pr.setup())
    client._hotspot_timeout_trigger_event = _ParkedFlag()  # type: ignore[assignment]  # see _ParkedFlag
    client._conn_phase = _PHASE_HOTSPOT
    client._hotspot_started_once = True
    run(client._hotspot_client_absent())  # the window runs, its pattern flashing

    async def select(mode: int) -> bool:
        return mode >= 0

    client._select_wifi_mode = select  # type: ignore[method-assign]  # the mode switch is not under test

    async def scenario() -> "tuple[bool, bool, bool, bool]":
        watcher = client.start_asy_hotspot_timeout()
        await asyncio.sleep(0)  # a park: the watcher waits on its flag
        client._hotspot_timer.trigger()
        await _drive(2)
        await cancel(watcher)
        return client._reconn_wifi, client._reconnect_fresh, client._hotspot_timer_running, client._ledflash is None

    with FastAsyncSleep():
        assert run(scenario()) == (True, False, False, True)
        run(client._handle_reconnect_trigger())
    assert (client._conn_phase, client._hotspot_started_once) == (_PHASE_STA_SEEKING, True)
    for _ in range(2):
        run(client._register_sta_connection_failure())
    assert client._conn_phase == _PHASE_SILENT


def _fresh_boot_state(client: WifiService) -> "tuple[int, bool, int, bool, bool, bool]":
    # (failures, hotspot used once, phase, reconnect pending, fresh flag pending, period or window timer running)
    return (
        client._connection_failures, client._hotspot_started_once, client._conn_phase, client._reconn_wifi,
        client._reconnect_fresh, client._hotspot_timer_running,
    )


def test_a_settings_trigger_beside_a_window_end_wins() -> None:
    # Both pending, in either order: the settings hook's fresh-boot state wins over the window end's kept hotspot use.
    for settings_first in (True, False):
        client = _make_client(conn_fail_to_hotspot=2, hotspot_time_min=1)
        client._conn_phase = _PHASE_HOTSPOT
        client._hotspot_started_once = True
        client._connection_failures = 1

        async def select(mode: int) -> bool:
            return mode >= 0

        client._select_wifi_mode = select  # type: ignore[method-assign]  # the mode switch is not under test
        if settings_first:
            client.reconnect_wifi()
            client._on_hotspot_window_end()
        else:
            client._on_hotspot_window_end()
            client.reconnect_wifi()
        with FastAsyncSleep():
            run(client._handle_reconnect_trigger())
        assert _fresh_boot_state(client) == (0, False, _PHASE_STA_SEEKING, False, False, False), settings_first


def test_the_identity_hook_lands_in_the_fresh_boot_state() -> None:
    # Any credentials change lands where a fresh boot starts (owner, 2026-10-08: "Any change of credentials, no matter
    # from which side, lands in the same mode as "initial connection attempt after a fresh boot"."), from each state, the
    # window end's own streak (seeking with the hotspot already used) included.
    for source in (_PHASE_HOTSPOT, _PHASE_SILENT, _PHASE_STA_ESTABLISHED, _PHASE_STA_SEEKING):
        client = _make_client_with_json(_VALID_JSON, conn_fail_to_hotspot=2, hotspot_time_min=1)
        run(client.pr.setup())
        client._conn_phase = source
        client._hotspot_started_once = True
        client._connection_failures = 1
        timer = client._hotspot_timer
        if source in (_PHASE_HOTSPOT, _PHASE_SILENT):
            run(client._arm_hotspot_timer())  # the hotspot's window, or the silent period
        client.reconnect_wifi()  # the identity group's post hook, as a PUT through the request path calls it
        with FastAsyncSleep():
            run(client._handle_reconnect_trigger())
        assert _fresh_boot_state(client) == (0, False, _PHASE_STA_SEEKING, False, False, False), source
        assert timer.callback is None, source
        for _ in range(2):  # a fresh streak failing opens the hotspot once more, never the silent mode
            run(client._register_sta_connection_failure())
        assert client._conn_phase == _PHASE_HOTSPOT, source


def test_repeated_absent_ticks_neither_rearm_the_timer_nor_log_anything() -> None:
    # The old ONE_SHOT backstop counted these ticks and persisted errno 19 past 2x hotspot_time;
    # with PERIODIC there is nothing to count and nothing to log (errno 19 is retired, C.7.1).
    client = _make_client(hotspot_time_min=1)
    run(client.pr.setup())
    run(client._hotspot_client_absent())
    armed = client._hotspot_timer.callback
    for _ in range(50):  # ~4 minutes of 5s ticks, past the old 24-tick threshold
        run(client._hotspot_client_absent())
    assert client._hotspot_timer.callback is armed
    assert client._reconn_wifi is False  # only the timer ends hotspot mode, never the tick count
    assert run(client.get_error_counter())["WIFI"]["ErrCount"] == 0


def test_hotspot_client_absent_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    client = _make_client(hotspot_time_min=1)
    run(client.pr.setup())
    with RaiseOnArm():
        run(client._hotspot_client_absent())  # must not raise despite the timer failing to arm
    assert client._hotspot_timer_running is False  # left False so the next cycle retries arming it
    assert _used_slots(run(client.get_error_counter())) == [code("E", "TIMER")]  # a hotspot that never times out is evidence


def test_hotspot_client_absent_degrades_gracefully_on_a_memory_error() -> None:
    # Sibling of the OSError test above, for the other arm of _hotspot_client_absent()'s own
    # `except (OSError, MemoryError)` - _hotspot_timer_running stays False either way, so the next
    # refresh cycle retries arming it rather than getting stuck.
    client = _make_client(hotspot_time_min=1)
    run(client.pr.setup())
    with RaiseOnArm(MemoryError):
        run(client._hotspot_client_absent())  # must not raise despite the timer failing to arm
    assert client._hotspot_timer_running is False  # left False so the next cycle retries arming it
    assert _used_slots(run(client.get_error_counter())) == [code("E", "TIMER")]


def _failed_window_arm_case(exc: "type[BaseException]") -> None:
    # Two no-client ticks whose window arm raises, then one with room in the alarm pool; each starts with the flag
    # cleared, as _connect_loop() starts an iteration.
    client = _make_client(hotspot_time_min=1)
    run(client.pr.setup())

    async def scenario() -> "list[tuple[bool, bool]]":
        seen = []
        for exhausted in (True, True, False):
            client._hw_op_failed = False
            if exhausted:
                with RaiseOnArm(exc):
                    await client._hotspot_client_absent()
            else:
                await client._hotspot_client_absent()
            seen.append((client._hw_op_failed, client._hotspot_timer_running))
        await _stop_flash(client)
        return seen

    assert run(scenario()) == [(True, False), (True, False), (False, True)], exc
    log = run(client.get_error_counter())
    assert _used_slots(log) == [code("E", "TIMER")] and log["WIFI"]["ErrCount"] == 2, (exc, log)
    assert len(client._hotspot_timer.arms) == 1, exc


def test_a_failed_window_arm_is_the_iterations_hardware_failure() -> None:
    # Alarm-pool exhaustion (ENOMEM) and an allocation failure each persist one TIMER entry and mark the iteration's
    # hardware failure, as the silent mode's period arm does; the next tick arms the window once the pool has room.
    _failed_window_arm_case(OSError)
    _failed_window_arm_case(MemoryError)


def _window_line_case(exc: "type[BaseException]") -> None:
    # The console lines of three no-client ticks at the event level: a failed arm, then an arm with room in the alarm
    # pool, then a tick with the window already running.
    client = _make_client(hotspot_time_min=1)
    run(client.pr.setup())
    client.pr.set_level(4)

    async def scenario() -> "list[list[tuple[object, ...]]]":
        ticks = []
        for exhausted in (True, False, False):
            with record_prints() as recorder:
                if exhausted:
                    with RaiseOnArm(exc):
                        await client._hotspot_client_absent()
                else:
                    await client._hotspot_client_absent()
            ticks.append(recorder.lines)
        await _stop_flash(client)
        return ticks

    failed, armed, running = run(scenario())
    assert [line[:2] for line in failed] == [("WIFI", "Could not start hotspot timer:")], (exc, failed)
    assert (armed, running) == ([("WIFI", "No client connected - hotspot timer started")], []), (exc, armed, running)


def test_the_window_started_line_follows_a_successful_arm_only() -> None:
    # A failed arm prints its own error and nothing more, its persisted TIMER entry being the record; the started line
    # comes once the window is armed, never before the arm's result is known.
    _window_line_case(OSError)
    _window_line_case(MemoryError)


def test_hotspot_client_absent_starts_the_led_flash_task() -> None:
    client = _make_client()

    async def scenario() -> None:
        await client._hotspot_client_absent()
        assert client._ledflash is not None
        await cancel(client._ledflash)

    run(scenario())


# ---------------------------------------------------------------------------
# "Attempt" operations - a mode switch, hotspot activation, a connect trigger, polling connect
# status, the disconnect-wait: each persists a real errno via pr.err_s() and sets
# self._hw_op_failed on a genuine exception, independent of the AP-reachability-driven fallback.
# ---------------------------------------------------------------------------


def test_switch_wlan_mode_exception_sets_hw_op_failed_and_persists_wlan_mode_switch() -> None:
    client = _make_client()
    run(client.pr.setup())
    _wlan(client).raise_on["disconnect"] = RuntimeError("simulated hardware fault")
    assert run(client._select_wifi_mode(network.AP_IF)) is False  # the failed switch reported to its caller
    assert client._hw_op_failed is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "WLAN_MODE_SWITCH")
    assert _last_err(counter, "ErrType") == "E"


def test_activate_hotspot_ap_exception_sets_hw_op_failed_and_persists_wlan_ap_start() -> None:
    client = _make_client()
    run(client.pr.setup())
    _wlan(client).raise_on["config"] = RuntimeError("simulated hardware fault")
    run(client._activate_hotspot_ap("DE", "TestHost", "12345678"))
    assert client._hw_op_failed is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "WLAN_AP_START")
    assert _last_err(counter, "ErrType") == "E"


def test_activate_hotspot_ap_success_configures_and_activates_the_ap() -> None:
    client = _make_client()

    async def scenario() -> None:
        await client._activate_hotspot_ap("US", "MyHost", "12345678")
        assert client._hw_op_failed is False
        assert _wlan(client)._active is True
        assert {"essid": "MyHost", "password": "12345678"} in _wlan(client).config_calls
        assert client._dns_server_task is not None
        await cancel(client._dns_server_task)

    run(scenario())


def test_trigger_sta_connect_exception_sets_hw_op_failed_and_persists_wlan_sta_start() -> None:
    client = _make_client()
    run(client.pr.setup())
    _wlan(client).raise_on["connect"] = RuntimeError("simulated hardware fault")
    result = run(client._trigger_sta_connect("ssid", "pw", "DE", "host"))
    assert result is False
    assert client._hw_op_failed is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "WLAN_STA_START")
    assert _last_err(counter, "ErrType") == "E"


def test_trigger_sta_connect_success_returns_true_and_records_the_attempt() -> None:
    client = _make_client()
    result = run(client._trigger_sta_connect("MySSID", "MyPW", "DE", "host"))
    assert result is True
    assert client._hw_op_failed is False
    assert _wlan(client).connect_calls == [("MySSID", "MyPW")]
    assert _wlan(client)._active is True


def test_poll_sta_connect_status_exception_sets_hw_op_failed_and_persists_wlan_sta_poll() -> None:
    client = _make_client()
    run(client.pr.setup())
    _wlan(client).raise_on["status"] = RuntimeError("simulated hardware fault")
    run(client._poll_sta_connect_status())
    assert client._hw_op_failed is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "WLAN_STA_POLL")
    assert _last_err(counter, "ErrType") == "E"


def test_poll_sta_connect_status_wrong_password_persists_wlan_auth_failed() -> None:
    # cyw43 reports any failed AUTH event or key exchange as BADAUTH: the text claims no more than that.
    client = _make_client()
    run(client.pr.setup())
    _wlan(client)._status = network.STAT_WRONG_PASSWORD
    lines = _poll_printing(client)
    assert ("WIFI", "WLAN authentication or handshake failed") in lines, lines
    assert client._hw_op_failed is False  # a real connect outcome, not a hardware/driver failure
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("W", "WLAN_AUTH_FAILED")
    assert _last_err(counter, "ErrType") == "W"


def test_poll_sta_connect_status_no_ap_found_persists_wlan_no_ap() -> None:
    client = _make_client()
    run(client.pr.setup())
    _wlan(client)._status = network.STAT_NO_AP_FOUND
    run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("W", "WLAN_NO_AP")
    assert _last_err(counter, "ErrType") == "W"


def test_poll_sta_connect_status_connect_fail_persists_wlan_connect_failed() -> None:
    client = _make_client()
    run(client.pr.setup())
    _wlan(client)._status = network.STAT_CONNECT_FAIL
    run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("W", "WLAN_CONNECT_FAILED")
    assert _last_err(counter, "ErrType") == "W"


def test_poll_sta_connect_status_undefined_state_persists_wlan_status_unknown() -> None:
    client = _make_client()
    run(client.pr.setup())
    _wlan(client)._status = 12345  # not any real/defined network.STAT_* value
    run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("W", "WLAN_STATUS_UNKNOWN")
    assert _last_err(counter, "ErrType") == "W"


# A repeated connect verdict is one code: one slot, every attempt counted (C.7.1's central rule).


def test_a_repeated_connect_verdict_spends_one_slot_however_often_the_outage_retries() -> None:
    client = _make_client()
    run(client.pr.setup())
    _wlan(client)._status = network.STAT_NO_AP_FOUND
    for _attempt in range(10):
        run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    assert _used_slots(counter) == [code("W", "WLAN_NO_AP")], "ten retries must not spend ten slots"
    assert counter["WIFI"]["ErrCount"] == 10, "...and must still be counted: ten failed attempts are ten events"


def test_a_different_verdict_in_the_same_outage_still_persists() -> None:
    client = _make_client()
    run(client.pr.setup())
    for status in (network.STAT_NO_AP_FOUND, network.STAT_NO_AP_FOUND, network.STAT_WRONG_PASSWORD):
        _wlan(client)._status = status
        run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    # Two distinct verdicts on one outage, each evidence of what the link did: both keep a slot.
    assert _used_slots(counter) == [code("W", "WLAN_NO_AP"), code("W", "WLAN_AUTH_FAILED")]


def test_a_recurrence_after_recovery_stays_one_slot() -> None:
    client = _make_client()
    run(client.pr.setup())
    _wlan(client)._status = network.STAT_NO_AP_FOUND
    run(client._poll_sta_connect_status())
    client._on_sta_connected()
    run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    assert _used_slots(counter) == [code("W", "WLAN_NO_AP")]
    assert counter["WIFI"]["ErrCount"] == 2


def test_disconnect_sta_and_wait_exception_sets_hw_op_failed_and_persists_wlan_sta_disconnect() -> None:
    client = _make_client()
    run(client.pr.setup())
    _wlan(client).raise_on["disconnect"] = RuntimeError("simulated hardware fault")
    run(client._disconnect_sta_and_wait())
    assert client._hw_op_failed is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "WLAN_STA_DISCONNECT")
    assert _last_err(counter, "ErrType") == "E"


def test_disconnect_sta_and_wait_returns_immediately_when_already_disconnected() -> None:
    client = _make_client()
    _wlan(client)._connected = False
    run(client._disconnect_sta_and_wait())
    assert client._hw_op_failed is False
    assert _wlan(client).disconnect_called is True


def test_disconnect_sta_and_wait_times_out_instead_of_hanging_forever() -> None:
    # A driver that never confirms disconnection (isconnected() always True) must not hang _connect_loop()
    # forever: the wait is bounded by _STA_DISCONNECT_WAIT_ITERS x _STA_DISCONNECT_POLL_MS, each step a yield here.

    # The fake WLAN's disconnect() normally clears _connected as a side effect; overridden here to
    # a no-op so isconnected() keeps reporting True throughout.
    client = _make_client()
    run(client.pr.setup())
    _wlan(client)._connected = True
    _wlan(client).disconnect = lambda: setattr(_wlan(client), "disconnect_called", True)  # type: ignore[method-assign]  # keeps the link up
    fast = FastAsyncSleep()

    async def scenario() -> "list[int]":
        await client._disconnect_sta_and_wait()
        return fast.ms_of(asyncio.current_task())

    with fast:
        steps = run(scenario())
    assert steps == [_STA_DISCONNECT_POLL_MS] * _STA_DISCONNECT_WAIT_ITERS
    assert client._hw_op_failed is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "TIMEOUT")
    assert _last_err(counter, "ErrType") == "E"


# ---------------------------------------------------------------------------
# _print_wlan_diagnostics() / _on_sta_connected() / _on_sta_disconnected() /
# _register_sta_connection_failure() / _handle_sta_connection_result() - previously untested
# STA-mode connect/disconnect bookkeeping helpers
# ---------------------------------------------------------------------------


def test_print_wlan_diagnostics_does_not_raise_on_success() -> None:
    print(
        "(expected) debug=5 makes the fresh ConfigManager below log its normal first-use config-file "
        "creation, then the real WLAN diagnostics dump below is the point of this test",
    )
    client = _make_client(debug=5)  # DebugLevel 5 (SPEC A.8) - pr.all() actually prints, not gated off
    _wlan(client)._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "8.8.8.8")
    client._print_wlan_diagnostics()  # must not raise


def test_print_wlan_diagnostics_degrades_gracefully_when_ifconfig_raises() -> None:
    print("(expected) debug=5 makes the fresh ConfigManager below log its normal first-use config-file creation")
    client = _make_client(debug=5)
    _wlan(client).raise_on["ifconfig"] = RuntimeError("simulated hardware fault")
    print("(expected) simulating a hardware fault - the following 'WLAN diagnostic read failed' is intentional")
    client._print_wlan_diagnostics()  # must not raise


def test_on_sta_connected_updates_state_and_turns_led_on() -> None:
    led = _FakeLED()
    client = _make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    client._connection_failures = 3
    client._on_sta_connected()
    assert client._conn_phase == _PHASE_STA_ESTABLISHED
    assert client._connection_failures == 0
    assert led.on_calls == 1


def test_register_sta_connection_failure_increments_below_threshold() -> None:
    client = _make_client(conn_fail_to_hotspot=3)
    run(client._register_sta_connection_failure())
    assert client._connection_failures == 1
    assert client._conn_phase == _PHASE_STA_SEEKING


def test_register_sta_connection_failure_switches_to_hotspot_at_threshold() -> None:
    client = _make_client(conn_fail_to_hotspot=2)
    client._connection_failures = 1  # one below threshold already
    client._hotspot_started_once = False
    run(client._register_sta_connection_failure())
    assert client._connection_failures == 0
    assert client._conn_phase == _PHASE_HOTSPOT


def test_register_sta_connection_failure_goes_silent_when_hotspot_already_tried() -> None:
    client = _make_client(conn_fail_to_hotspot=2)
    run(client.pr.setup())
    client._connection_failures = 1
    client._hotspot_started_once = True
    run(client._register_sta_connection_failure())
    assert client._conn_phase == _PHASE_SILENT


def test_on_sta_disconnected_registers_failure_when_never_connected() -> None:
    client = _make_client(conn_fail_to_hotspot=3)
    client._conn_phase = _PHASE_STA_SEEKING
    run(client._on_sta_disconnected())
    assert client._connection_failures == 1


def test_on_sta_disconnected_retries_after_a_minute_when_previously_connected() -> None:
    # _PHASE_STA_ESTABLISHED reports the retry as due; _run_sta_mode() then sleeps _STA_RETRY_AFTER_LOSS_S
    # after releasing wifi_mode_lock, so NTP, the uptime tick and a reconnect are never held up by the wait.
    client = _make_client(conn_fail_to_hotspot=2)
    client._conn_phase = _PHASE_STA_ESTABLISHED
    slept: list[tuple[object, float, bool]] = []
    real_sleep = asyncio.sleep

    async def watched(seconds: float) -> None:
        slept.append((asyncio.current_task(), seconds, client.wifi_mode_lock.locked()))
        await real_sleep(0)

    async def no_attempt() -> None:
        return None

    client._attempt_sta_connect = no_attempt  # type: ignore[method-assign]  # the attempt is not under test

    async def scenario() -> "tuple[bool, list[tuple[float, bool]], list[tuple[float, bool]]]":
        me = asyncio.current_task()
        due = await client._on_sta_disconnected()
        inside = [(t, held) for owner, t, held in slept if owner is me]
        await client._run_sta_mode()
        return due, inside, [(t, held) for owner, t, held in slept if owner is me]

    asyncio.sleep = watched  # type: ignore[assignment]  # restored below
    try:
        due, inside, waited = run(scenario())
    finally:
        asyncio.sleep = real_sleep
    assert due is True
    assert inside == [], "the retry wait ran inside _on_sta_disconnected(), under its caller's lock"
    assert waited == [(float(_STA_RETRY_AFTER_LOSS_S), False)]
    assert client._connection_failures == 0  # never reached _register_sta_connection_failure()


def test_handle_sta_connection_result_connected_calls_on_sta_connected() -> None:
    client = _make_client()
    _wlan(client)._connected = True
    assert run(client._handle_sta_connection_result()) is False  # connected: no retry wait due
    assert client._conn_phase == _PHASE_STA_ESTABLISHED


def test_handle_sta_connection_result_disconnected_calls_on_sta_disconnected() -> None:
    client = _make_client(conn_fail_to_hotspot=3)
    _wlan(client)._connected = False
    client._conn_phase = _PHASE_STA_SEEKING
    assert run(client._handle_sta_connection_result()) is False  # a failure counted, no retry wait
    assert client._connection_failures == 1


# ---------------------------------------------------------------------------
# Missing configuration - logged in both layers: CFGMGR_WIFI's refused read, and WIFI's own entry for
# running on its fallback
# ---------------------------------------------------------------------------


def test_apply_initial_led_config_missing_config_logs_in_both_layers_and_deactivates() -> None:
    # With the configuration unreadable, LEDWifiOn takes its schema default (on), so the deactivated
    # pattern shows - the same fallback every unreadable config value takes.
    cfg_path = _tmp_cfg_dir()
    os.mkdir(cfg_path + "config_WIFI.cfg")
    client = _make_client(cfg_path=cfg_path, ext_led=_FakeLED())
    run(client.pr.setup())
    run(client._apply_initial_led_config())
    assert client._conn_phase == _PHASE_DEACTIVATED
    assert client._led is not None
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("W", "CFG_READ")
    assert _last_err(counter, "ErrType") == "W"
    assert _used_slots(run(client.cfgmgr.get_error_counter()), "CFGMGR_WIFI")[-1] == code("E", "CFG_NOT_VALID")


def test_apply_initial_led_config_valid_config_does_not_deactivate() -> None:
    client = _make_client()
    run(client._apply_initial_led_config())
    assert client._conn_phase != _PHASE_DEACTIVATED


def test_a_settings_change_cannot_reach_the_no_configuration_state() -> None:
    # An unreadable store refuses every write, so the request path never runs the settings hook there; called anyway,
    # the hook changes nothing: the phase stays, the radio stays unused and the no-configuration pattern runs on.
    client = _make_invalid_cfg_client()
    run(client.pr.setup())
    results = run(handle_set_cmd(client, {"SSID": "MyNetwork"}, client.get_cfg_schema(), post_fct=client.reconnect_wifi))
    assert "Valid" not in results.values() and client._reconn_wifi is False, results
    first = _wlan(client)

    async def scenario() -> "tuple[bool, bool]":
        loop = asyncio.create_task(client._connect_loop())
        await _until(lambda: client._ledflash is not None)
        client.reconnect_wifi()
        cancelled = client._ledflash is None
        await _until(lambda: client._ledflash is not None)
        await cancel(loop)
        restarted = client._led_pattern == _src_pattern("DEACTIVATED")
        await _stop_flash(client)
        return cancelled, restarted

    with FastAsyncSleep(), _CountedWLAN() as wlan:
        cancelled, restarted = run(scenario())
    assert client._conn_phase == _PHASE_DEACTIVATED
    assert (wlan.built, first.connect_calls, first.disconnect_called) == ([], [], False)
    assert cancelled and restarted, "the no-configuration pattern did not run on"


def test_start_hotspot_missing_config_logs_in_both_layers() -> None:
    client = _make_invalid_cfg_client()
    run(client.pr.setup())

    async def fake_select(_mode: int) -> None:
        return None  # skips the real mode-switch dance (and its real asyncio.sleep()s) entirely

    client._select_wifi_mode = fake_select  # type: ignore[assignment, method-assign]  # mocked by reassignment
    run(client._start_hotspot())
    assert client._hotspot_started_once is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("W", "CFG_READ")
    assert _last_err(counter, "ErrType") == "W"
    assert _used_slots(run(client.cfgmgr.get_error_counter()), "CFGMGR_WIFI")[-1] == code("E", "CFG_NOT_VALID")


def test_attempt_sta_connect_missing_config_logs_in_both_layers() -> None:
    client = _make_invalid_cfg_client()
    run(client.pr.setup())
    run(client._attempt_sta_connect())
    assert _wlan(client).connect_calls == []  # never reached the real connect attempt
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("W", "CFG_READ")
    assert _last_err(counter, "ErrType") == "W"
    assert _used_slots(run(client.cfgmgr.get_error_counter()), "CFGMGR_WIFI")[-1] == code("E", "CFG_NOT_VALID")


def test_an_empty_ssid_returns_to_the_hotspot_without_a_failure_streak() -> None:
    # No SSID (factory state, or after "Reset to defaults"): nothing to attempt, so no streak - even after
    # the hotspot ran once, an unconfigured unit goes back to its hotspot instead of going silent.
    client = _make_client(conn_fail_to_hotspot=2)  # the default SSID is "" until configured
    run(client.pr.setup())
    client._hotspot_started_once = True
    client.pr.set_level(4)
    with record_prints() as recorder:
        run(client._attempt_sta_connect())
    assert _wlan(client).connect_calls == []
    assert client._connection_failures == 0
    assert client._conn_phase == _PHASE_HOTSPOT
    assert recorder.lines.count(("WIFI", "No SSID configured, hotspot mode")) == 1


def _end_hotspot_window(client: WifiService) -> None:
    # One hotspot window's end as the loop runs it: the hotspot is left, then one STA iteration.
    async def select(mode: int) -> bool:
        return mode >= 0

    client._select_wifi_mode = select  # type: ignore[method-assign]  # the mode switch is not under test
    client._hotspot_started_once = True
    with FastAsyncSleep():
        run(client._leave_hotspot_mode())
        run(client._run_sta_mode())


def test_an_unconfigured_unit_never_goes_silent_over_two_hotspot_windows() -> None:
    client = _make_client(conn_fail_to_hotspot=1)
    run(client.pr.setup())
    for window in range(2):
        client._conn_phase = _PHASE_HOTSPOT
        _end_hotspot_window(client)
        assert client._conn_phase == _PHASE_HOTSPOT, window
        assert client._connection_failures == 0, window
    assert run(client.get_error_counter())["WIFI"]["ErrCount"] == 0


def test_a_configured_ssid_whose_second_streak_fails_goes_silent() -> None:
    # Control, the owner rule (SPECIFICATION.md A.4): a second streak of real STA attempts ends in the silent mode,
    # never with Wi-Fi off (owner, 2026-10-08: "Don't permanently switch WiFi off, only stop retrying to connect.").
    client = _make_client_with_json(_VALID_JSON, conn_fail_to_hotspot=1)
    run(client.pr.setup())
    _wlan(client)._status = network.STAT_NO_AP_FOUND
    client._conn_phase = _PHASE_HOTSPOT
    _end_hotspot_window(client)
    assert len(_wlan(client).connect_calls) == 1
    assert client._conn_phase == _PHASE_SILENT


def test_the_first_streak_persists_its_fallback_and_the_second_its_silent_entry_once() -> None:
    # The two owner-designed transitions leave a trace in the WIFI history, so it says why a unit was offline.
    client = _make_client(conn_fail_to_hotspot=2)
    run(client.pr.setup())
    for _ in range(2):
        run(client._register_sta_connection_failure())
    assert client._conn_phase == _PHASE_HOTSPOT
    assert _used_slots(run(client.get_error_counter())) == [code("W", "WLAN_TO_HOTSPOT")]
    client._conn_phase = _PHASE_STA_SEEKING
    client._hotspot_started_once = True
    with FastAsyncSleep():
        for _ in range(2):
            run(client._register_sta_connection_failure())
    assert client._conn_phase == _PHASE_SILENT
    log = run(client.get_error_counter())
    assert _used_slots(log) == [code("W", "WLAN_TO_HOTSPOT"), code("W", "WLAN_SILENT")]
    _no_sta(client)

    async def silent_iterations() -> None:
        task = asyncio.create_task(client._connect_loop())
        await _drive(12)
        await cancel(task)
        if client._ledflash is not None:
            await _stop_flash(client)

    with FastAsyncSleep():
        run(silent_iterations())
    assert client._conn_phase == _PHASE_SILENT
    assert run(client.get_error_counter()) == log  # further iterations without a period's fire persist nothing


# ---------------------------------------------------------------------------
# The silent mode: a second failed streak after the hotspot ran stops the retries but never switches Wi-Fi off;
# one connect attempt per hotspot_time_min, the LED dark until a link (SPECIFICATION.md A.4).
# ---------------------------------------------------------------------------


def test_a_second_streak_enters_the_silent_mode_once() -> None:
    # Silent, never off (owner, 2026-10-08: "Don't permanently switch WiFi off, only stop retrying to connect."): the
    # radio stays as the failed attempt left it, the flash ends, one WLAN_SILENT entry; later failures add nothing.
    client = _make_client(conn_fail_to_hotspot=2)
    run(client.pr.setup())
    radio = _wlan(client)
    radio._active = True  # as the streak's last attempt left it
    client._hotspot_started_once = True
    client._connection_failures = 1

    async def scenario() -> "asyncio.Task[None] | None":
        client._run_led_pattern(*_src_pattern("HOTSPOT"))  # a running flash task the entry must end
        flash = client._ledflash
        await client._register_sta_connection_failure()
        await asyncio.sleep(0)  # a park: the cancelled flash task ends; done() below checks it
        return flash

    with FastAsyncSleep():
        flash = run(scenario())
    assert client._conn_phase == _PHASE_SILENT
    assert flash is not None and flash.done() and client._ledflash is None
    assert (radio.disconnect_called, radio._active, radio.deinit_called) == (False, True, False), "the radio was switched off"
    log = run(client.get_error_counter())
    assert _used_slots(log) == [code("W", "WLAN_SILENT")] and log["WIFI"]["ErrCount"] == 1
    for _ in range(3):  # failed attempts in the mode: no streak, no retry wait, nothing persisted
        assert run(client._on_sta_disconnected()) is False
    assert (client._conn_phase, client._connection_failures) == (_PHASE_SILENT, 0)
    assert run(client.get_error_counter()) == log


def test_a_silent_period_runs_one_attempt_and_a_link_is_a_normal_connection() -> None:
    # The window's own PERIODIC timer is the period; one fire, one attempt with the stored settings, and a link is an
    # ordinary connection: its timer ends, and a later loss takes the 60 s retry, never the hotspot.
    client = _silent_client(hotspot_time_min=2)
    timer = client._hotspot_timer
    radio = _wlan(client)

    async def scenario() -> "list[tuple[str | None, str | None]]":
        watcher = client.start_asy_hotspot_timeout()
        await client._run_silent_mode()  # arms the period; nothing is due yet
        before = list(radio.connect_calls)
        _joins(client)
        await _fire_period(client)
        await cancel(watcher)
        return before

    with FastAsyncSleep():
        before = run(scenario())
    assert before == []
    assert [arm[1:] for arm in timer.arms] == [(120000, Timer.PERIODIC)]
    assert radio.connect_calls == [("MyNetwork", "supersecret")]
    assert (client._conn_phase, client._connection_failures) == (_PHASE_STA_ESTABLISHED, 0)
    assert (client._hotspot_timer_running, timer.callback) == (False, None), "the link must end the period"
    radio._connected = False  # a later loss
    assert run(client._on_sta_disconnected()) is True
    assert client._conn_phase == _PHASE_STA_ESTABLISHED


def test_a_failed_silent_attempt_stays_silent_without_a_streak() -> None:
    # Uncapped and never escalating (owner, 2026-10-08: "This repeats with the periodicity of the SSID scans if not
    # successful, not capped"): each attempt's verdict persists, one slot counting the run.
    client = _silent_client()
    _wlan(client)._status = network.STAT_NO_AP_FOUND

    async def scenario() -> None:
        watcher = client.start_asy_hotspot_timeout()
        for _ in range(3):
            await _fire_period(client)
        await cancel(watcher)

    with FastAsyncSleep():
        run(scenario())
    assert (client._conn_phase, client._connection_failures) == (_PHASE_SILENT, 0)
    assert len(_wlan(client).connect_calls) == 3
    log = run(client.get_error_counter())
    assert _used_slots(log) == [code("W", "WLAN_NO_AP")] and log["WIFI"]["ErrCount"] == 3


def test_no_attempt_runs_between_periods() -> None:
    # Twelve loop iterations (a minute of 5 s refreshes) with no period's fire: no connect attempt, the period armed.
    client = _silent_client()
    real = client._run_silent_mode
    iterations = [0]

    async def counted() -> bool:
        iterations[0] += 1
        return await real()

    client._run_silent_mode = counted  # type: ignore[method-assign]  # counts the real iterations

    async def scenario() -> None:
        loop = asyncio.create_task(client._connect_loop())
        for _ in range(400):  # bounded: every sleep is one yield here
            if iterations[0] >= 12:
                break
            await asyncio.sleep(0)
        await cancel(loop)

    with FastAsyncSleep():
        run(scenario())
    assert iterations[0] >= 12
    assert _wlan(client).connect_calls == []
    assert (client._conn_phase, client._hotspot_timer_running) == (_PHASE_SILENT, True)


# Error handling, resilience and non-blocking in the silent mode.


def _failed_period_arm_case(exc: "type[BaseException]") -> None:
    # Two iterations whose period arm raises, then one with room in the alarm pool.
    client = _silent_client()

    async def scenario() -> "tuple[bool, bool]":
        with RaiseOnArm(exc):
            await client._run_silent_mode()
            await client._run_silent_mode()
        failed = client._hotspot_timer_running
        await client._run_silent_mode()
        return failed, client._hotspot_timer_running

    assert run(scenario()) == (False, True), exc
    log = run(client.get_error_counter())
    assert _used_slots(log) == [code("E", "TIMER")] and log["WIFI"]["ErrCount"] == 2, (exc, log)
    assert (client._conn_phase, len(client._hotspot_timer.arms)) == (_PHASE_SILENT, 1), exc


def test_a_failed_period_arm_is_persisted_and_retried_in_the_silent_mode() -> None:
    # Alarm-pool exhaustion (ENOMEM) and an allocation failure each persist one TIMER entry per failed arm; the mode
    # stays, and the next iteration arms the period once the pool has room.
    _failed_period_arm_case(OSError)
    _failed_period_arm_case(MemoryError)


class _RaisingConnectWLAN:
    # Every interface built in the block raises from connect(), as a radio whose join command keeps failing does:
    # the device rung's fresh interface fails too, so the hardware streak runs on to its give-up.
    def __enter__(self) -> "Self":
        self._real = network.WLAN
        real = self._real

        def build(if_id: int) -> "_FakeWLAN":
            wlan: _FakeWLAN = real(if_id)  # type: ignore[assignment]  # the fake, which mypy sees as the board stub's WLAN
            wlan.raise_on["connect"] = OSError("simulated join command failure")
            return wlan

        network.WLAN = build  # type: ignore[assignment, misc]  # a module attribute swap, restored on exit
        return self

    def __exit__(self, *exc_info: object) -> None:
        network.WLAN = self._real  # type: ignore[misc]


def test_a_raising_silent_attempt_feeds_the_hardware_streak_and_keeps_the_mode() -> None:
    # A silent attempt is an ordinary attempt: a raising connect() persists WLAN_STA_START and counts toward the
    # hardware streak, which the idle iterations between periods leave as it is, so a radio that never comes up still
    # reaches its device rung and its give-up; both, and the task's restart, keep the silent mode.
    with _RaisingConnectWLAN():
        client = _make_client_with_json(_VALID_JSON, max_module_error=2)
        run(client.pr.setup())
        client._hotspot_timeout_trigger_event = _ParkedFlag()  # type: ignore[assignment]  # see _ParkedFlag
        client._conn_phase = _PHASE_SILENT
        real = client._run_silent_mode
        iterations = [0]

        async def counted() -> bool:
            iterations[0] += 1
            return await real()

        client._run_silent_mode = counted  # type: ignore[method-assign]  # counts the real iterations

        async def idle_then_fire(loop: "asyncio.Task[None]") -> None:
            target = iterations[0] + 6  # six idle iterations, half a minute of refreshes, then the period's fire
            await _until(lambda: iterations[0] >= target or loop.done())
            client._hotspot_timer.trigger()

        async def give_up() -> "tuple[bool, list[int]]":
            watcher = client.start_asy_hotspot_timeout()
            loop = asyncio.create_task(client._connect_loop())
            streak = []
            for _ in range(4):  # the give-up needs max_module_error + 1 failed attempts, each one period apart
                await idle_then_fire(loop)
                await _until(lambda: not client._silent_attempt_due or loop.done())
                streak.append(client._err_cnt_internal)
            await _until(loop.done)
            done = loop.done()
            if not done:
                await cancel(loop)
            await cancel(watcher)
            return done, streak

        with FastAsyncSleep():
            done, streak = run(give_up())
        kept = _used_slots(run(client.get_error_counter()))
        assert done is True, ("the streak never reached its give-up", streak, kept)
        for name in (("E", "WLAN_STA_START"), ("W", "DEVICE_RECOVERY"), ("E", "GIVE_UP"), ("E", "WLAN_GIVE_UP")):
            assert code(*name) in kept, (name, kept)
        assert client._conn_phase == _PHASE_SILENT, "the give-up left the silent mode"
        client._run_silent_mode = real  # type: ignore[method-assign]

        async def restarted() -> None:
            loop = asyncio.create_task(client._connect_loop())
            await _until(lambda: client._hotspot_timer_running)  # the restart's first silent iteration re-arms
            await cancel(loop)

        with FastAsyncSleep():
            run(restarted())
    assert (client._conn_phase, client._hotspot_timer_running) == (_PHASE_SILENT, True), "the restart left the silent mode"


def test_a_silent_period_that_cannot_be_armed_feeds_the_hardware_streak() -> None:
    # With no period armed no attempt is ever due, so each failed arm is the iteration's hardware failure: the streak
    # reaches its device rung and its give-up as a raising connect() does, and the restart keeps the silent mode.
    client = _make_client_with_json(_VALID_JSON, conn_fail_to_hotspot=1, max_module_error=2)
    run(client.pr.setup())
    client._hotspot_started_once = True
    real = client._run_silent_mode
    iterations = [0]

    async def counted() -> bool:
        iterations[0] += 1
        return await real()

    client._run_silent_mode = counted  # type: ignore[method-assign]  # counts the real iterations

    async def give_up() -> bool:
        await client._register_sta_connection_failure()  # the second streak's last failure: silent
        loop = asyncio.create_task(client._connect_loop())
        await _until(loop.done, 400)
        done = loop.done()
        if not done:
            await cancel(loop)
        return done

    with FastAsyncSleep(), RaiseOnArm():  # Timer.init() refuses every arm (ENOMEM)
        done = run(give_up())
    kept = _used_slots(run(client.get_error_counter()))
    assert done is True, ("the streak never reached its give-up", iterations, kept)
    assert iterations[0] == client._err_cnt_internal == client._max_module_error + 1, (iterations, client._err_cnt_internal)
    for name in (("E", "TIMER"), ("W", "DEVICE_RECOVERY"), ("E", "GIVE_UP"), ("E", "WLAN_GIVE_UP")):
        assert code(*name) in kept, (name, kept)
    assert client._conn_phase == _PHASE_SILENT, "the give-up left the silent mode"
    client._run_silent_mode = real  # type: ignore[method-assign]

    async def restarted() -> None:
        loop = asyncio.create_task(client._connect_loop())
        await _until(lambda: client._hotspot_timer_running)  # the pool has room again: the restart arms the period
        await cancel(loop)

    with FastAsyncSleep():
        run(restarted())
    assert (client._conn_phase, client._hotspot_timer_running) == (_PHASE_SILENT, True), "the restart left the silent mode"


def test_500_silent_periods_stay_silent_and_bounded() -> None:
    # Uncapped, and bounded by structure: one arm for every period, one history slot for the whole run, no task or
    # radio interface left behind, however many periods pass (CLAUDE.md's memory rule: a property, not a heap reading).
    client = _make_client_with_json(_VALID_JSON, conn_fail_to_hotspot=1)
    run(client.pr.setup())
    client._hotspot_timeout_trigger_event = _ParkedFlag()  # type: ignore[assignment]  # see _ParkedFlag
    client._hotspot_started_once = True
    _wlan(client)._status = network.STAT_NO_AP_FOUND
    first = _wlan(client)

    async def scenario() -> "tuple[list[int], list[int], int]":
        watcher = client.start_asy_hotspot_timeout()
        await client._register_sta_connection_failure()  # the second streak's last failure: silent
        await _fire_period(client)
        after_one = _used_slots(await client.get_error_counter())
        for _ in range(499):
            await _fire_period(client)
            assert client._conn_phase == _PHASE_SILENT and not client._ap_selected
        after_all = _used_slots(await client.get_error_counter())
        count = (await client.get_error_counter())["WIFI"]["ErrCount"]
        await cancel(watcher)
        return after_one, after_all, count

    with FastAsyncSleep():
        after_one, after_all, count = run(scenario())
    assert len(first.connect_calls) == 500 and _wlan(client) is first
    assert after_one == [code("W", "WLAN_SILENT"), code("W", "WLAN_NO_AP")]
    assert after_all == after_one and count == 501, (after_all, count)
    assert len(client._hotspot_timer.arms) == 1, "the period was re-armed while it ran"
    assert (client._ledflash, client._dns_server_task, client._silent_attempt_due) == (None, None, False)


def test_a_restart_in_the_silent_mode_keeps_it_dark_and_re_arms_the_period() -> None:
    # The restart's reset deinits the period, its own reconnect keeps the phase with the LED dark through the
    # disconnect wait, and the next iteration arms the period again.
    led = _FakeLED()
    client = _silent_client(led=led, led_on=True)
    run(client.set_wifi_led(status=True))
    run(client._run_silent_mode())  # the period runs
    radio = _wlan(client)
    radio._active = True  # as the last silent attempt left the radio
    answers = [True, True, True, True]  # the restart's state read, then three polls of its disconnect wait

    def isconnected() -> bool:
        return answers.pop(0) if answers else False

    radio.isconnected = isconnected  # type: ignore[method-assign]  # the link's answers, scripted
    radio.disconnect = lambda: None  # type: ignore[method-assign]  # the link clears only as isconnected() above says

    async def scenario() -> None:
        loop = asyncio.create_task(client._connect_loop())
        await _until(lambda: len(client._hotspot_timer.arms) == 2)
        await cancel(loop)

    with FastAsyncSleep():
        run(scenario())
    assert client._conn_phase == _PHASE_SILENT
    assert len(client._hotspot_timer.arms) == 2 and client._hotspot_timer_running, "the period was not re-armed"
    assert (led.on_calls, led.toggle_calls) == (0, 0), "the restart lit the LED while silent"
    assert answers == [], "the disconnect wait never polled"


def test_a_restart_in_the_window_end_streak_still_clears_the_hotspot_use() -> None:
    # Guard (the behaviour is unchanged; holds at once): a restart before the window end's streak has failed is a
    # restart from seeking, which starts a fresh streak with the hotspot available, as at a boot (A.4's restart rule).
    client = _make_client(conn_fail_to_hotspot=2)
    client._hotspot_started_once = True
    client._connection_failures = 1
    _no_sta(client)

    async def scenario() -> None:
        loop = asyncio.create_task(client._connect_loop())
        await _drive(4)
        await cancel(loop)

    with FastAsyncSleep():
        run(scenario())
    assert (client._conn_phase, client._hotspot_started_once, client._connection_failures) == (_PHASE_STA_SEEKING, False, 0)


def test_a_dropped_silent_period_fire_is_recovered_by_the_next_period() -> None:
    # The soft-callback drop (Part F.1): the lost fire makes no attempt, and PERIODIC fires the next period, which does.
    client = _silent_client()
    _wlan(client)._status = network.STAT_NO_AP_FOUND
    timer = client._hotspot_timer

    async def scenario() -> "tuple[int, int]":
        watcher = client.start_asy_hotspot_timeout()
        await client._run_silent_mode()  # arms the period
        timer.drop()  # period 1's callback is lost
        await _drive(2)
        await client._run_silent_mode()
        dropped = len(_wlan(client).connect_calls)
        timer.trigger()  # period 2
        await _drive(2)
        await client._run_silent_mode()
        await cancel(watcher)
        return dropped, len(_wlan(client).connect_calls)

    with FastAsyncSleep():
        assert run(scenario()) == (0, 1)


def test_the_first_silent_attempt_waits_one_period_after_the_entry() -> None:
    # A due mark left from an earlier silent spell does not carry over: the entry clears it, so the first attempt
    # still waits for one full period.
    client = _make_client_with_json(_VALID_JSON, conn_fail_to_hotspot=1)
    run(client.pr.setup())
    client._hotspot_started_once = True
    client._silent_attempt_due = True  # a stale mark
    run(client._register_sta_connection_failure())
    with FastAsyncSleep():
        run(client._run_silent_mode())
    assert _wlan(client).connect_calls == [] and client._hotspot_timer_running


def test_the_wifi_service_never_scans() -> None:
    # Guard (holds at once): WLAN.scan() holds the VM up to 10 s (extmod/network_cyw43.c:236-246), past the watchdog.
    with open("src/asy_wifi_service.py") as f:
        assert ".scan(" not in f.read()
    scans: list[tuple[object, ...]] = []

    def scan(*args: object) -> "list[object]":
        scans.append(args)
        return []

    network.WLAN.scan = scan  # type: ignore[assignment, method-assign]  # recorded, so no swallowing except hides a call
    try:
        client = _silent_client()
        _wlan(client)._status = network.STAT_NO_AP_FOUND

        async def scenario() -> None:
            watcher = client.start_asy_hotspot_timeout()
            for _ in range(3):
                await _fire_period(client)
            loop = asyncio.create_task(client._connect_loop())
            await _drive(12)
            await cancel(loop)
            await cancel(watcher)

        with FastAsyncSleep():
            run(scenario())
    finally:
        del network.WLAN.scan
    assert scans == []
    assert len(_wlan(client).connect_calls) == 3


def test_the_silent_wait_holds_no_lock_and_yields() -> None:
    # Between periods another task takes wifi_mode_lock and a counting task advances on every loop iteration; a due
    # attempt holds the lock only for its connect and poll, as every attempt does.
    client = _silent_client()
    _wlan(client)._status = network.STAT_NO_AP_FOUND
    real = client._run_silent_mode
    ticks = [0]
    taken = [0]
    seen: list[tuple[int, int, bool]] = []  # (ticks, lock takes, lock free) at each iteration's start
    held: list[bool] = []
    real_attempt = client._attempt_sta_connect

    async def iteration() -> bool:
        seen.append((ticks[0], taken[0], not client.wifi_mode_lock.locked()))
        return await real()

    async def attempt() -> None:
        held.append(client.wifi_mode_lock.locked())
        await real_attempt()

    client._run_silent_mode = iteration  # type: ignore[method-assign]  # observed, then run
    client._attempt_sta_connect = attempt  # type: ignore[method-assign]  # observed, then run

    async def counter() -> None:
        while True:
            ticks[0] += 1
            await asyncio.sleep(0)

    async def taker() -> None:
        while True:
            async with client.wifi_mode_lock:
                taken[0] += 1
            await asyncio.sleep(0)

    async def scenario() -> None:
        tasks = [asyncio.create_task(counter()), asyncio.create_task(taker()), client.start_asy_hotspot_timeout()]
        loop = asyncio.create_task(client._connect_loop())
        await _until(lambda: len(seen) >= 12, 600)
        client._hotspot_timer.trigger()
        await _until(lambda: len(held) == 1, 600)
        await _until(lambda: len(seen) >= 14, 600)
        for task in [loop] + tasks:
            await cancel(task)

    with FastAsyncSleep():
        run(scenario())
    assert len(seen) >= 14 and all(free for _ticks, _takes, free in seen), seen
    advanced = [seen[i + 1][0] > seen[i][0] and seen[i + 1][1] > seen[i][1] for i in range(len(seen) - 1)]
    assert all(advanced), ("an iteration ran with another task held off", seen)
    assert held == [True], "the attempt ran outside the lock"
    assert len(_wlan(client).connect_calls) == 1 and not client.wifi_mode_lock.locked()


# ---------------------------------------------------------------------------
# The orchestration layer around _connect_loop()'s main loop, previously only exercised indirectly:
# _run_sta_mode, _get_hotspot_stations, _manage_hotspot_stations, _run_hotspot_mode,
# _leave_hotspot_mode, _wait_for_sta_disconnect and _handle_reconnect_trigger.
# ---------------------------------------------------------------------------


def test_run_sta_mode_attempts_connect_when_not_connected() -> None:
    client = _make_client()
    _wlan(client)._connected = False
    attempt_calls = [0]

    async def fake_attempt() -> None:
        attempt_calls[0] += 1

    client._attempt_sta_connect = fake_attempt  # type: ignore[method-assign]  # deliberate monkeypatch
    run(client._run_sta_mode())
    assert attempt_calls[0] == 1
    assert client.wifi_mode_lock.locked() is False  # released despite the attempt being faked out


def test_run_sta_mode_skips_attempt_when_already_connected() -> None:
    client = _make_client()
    _wlan(client)._connected = True
    attempt_calls = [0]

    async def fake_attempt() -> None:
        attempt_calls[0] += 1

    client._attempt_sta_connect = fake_attempt  # type: ignore[method-assign]  # deliberate monkeypatch
    run(client._run_sta_mode())
    assert attempt_calls[0] == 0


def test_run_sta_mode_stays_benign_across_many_cycles_when_isconnected_is_permanently_stuck_true() -> None:
    # Real-hardware finding proven benign at mock tier (test_network_resilience.py, 5/5 trials):
    # the CYW43 firmware can leave isconnected() stuck True for well over 150s after a real outage,
    # and _run_sta_mode()'s `if not self._wlan_isconnected_or_false()` never fires while stuck.

    # Drives the real method across many cycles and proves the steady state stays fully benign: no
    # exception, no _hw_op_failed, no _connection_failures climb, _conn_phase stays ESTABLISHED -
    # CLAUDE.md's power-cycle recovery (owner, 2026-09-04), not a hang or crash.
    client = _make_client(conn_fail_to_hotspot=2)
    client._conn_phase = _PHASE_STA_ESTABLISHED
    _wlan(client)._connected = True

    async def scenario() -> None:
        for _ in range(30):
            await client._run_sta_mode()

    run(scenario())
    assert client._conn_phase == _PHASE_STA_ESTABLISHED
    assert client._connection_failures == 0
    assert client._hw_op_failed is False
    assert _wlan(client).connect_calls == []  # never even attempted an explicit reconnect - matches
    # the real bug's own shape: nothing in this code decides to reconnect while isconnected() lies


def test_run_sta_mode_attempts_a_real_reconnect_on_the_very_first_cycle_once_isconnected_finally_flips_false() -> None:
    # Completes the steady-state test above: once the firmware-level lie clears, self-healing must
    # begin on the very first following cycle, since _wlan_isconnected_or_false() is queried fresh
    # every _run_sta_mode() call and adds no latency of its own.

    # make_client_with_json (a real configured SSID), not make_client: an empty SSID would make
    # _attempt_sta_connect() take the immediate-hotspot shortcut instead of calling wlan.connect().
    client = _make_client_with_json(_VALID_JSON, conn_fail_to_hotspot=2)
    client._conn_phase = _PHASE_STA_ESTABLISHED
    _wlan(client)._connected = True

    async def scenario() -> None:
        for _ in range(10):  # stuck true for a while first, same shape as the steady-state test above
            await client._run_sta_mode()
        assert _wlan(client).connect_calls == []  # confirms nothing attempted yet
        _wlan(client)._connected = False  # the real firmware-level flip, finally happening
        await client._run_sta_mode()  # its connect poll runs its full window: the fake reports IDLE throughout

    with FastAsyncSleep():
        run(scenario())
    assert len(_wlan(client).connect_calls) == 1  # a real reconnect attempt was made on this very
    # first post-flip cycle


def test_get_hotspot_stations_returns_the_real_list_on_success() -> None:
    client = _make_client()
    _on_the_ap(client)._stations = [(b"\xaa\xbb\xcc\xdd\xee\xff",)]
    stations = run(client._get_hotspot_stations())
    assert stations == [(b"\xaa\xbb\xcc\xdd\xee\xff",)]
    assert client.wifi_mode_lock.locked() is False


def test_get_hotspot_stations_answers_none_for_a_failed_query_and_an_empty_list_for_no_client() -> None:
    client = _make_client()
    _on_the_ap(client)
    assert run(client._get_hotspot_stations()) == []  # a real empty list: no client
    _wlan(client)._stations = [(bytes(6),)] * _STATIONS_UNSET
    assert run(client._get_hotspot_stations()) is None  # the chip-down answer: a failed check
    _wlan(client).raise_on["status"] = RuntimeError("simulated hardware fault")
    assert run(client._get_hotspot_stations()) is None  # unknown, never "no client"
    assert client.wifi_mode_lock.locked() is False


def test_a_stations_query_on_the_sta_interface_is_a_failed_check() -> None:
    # cyw43 answers status("stations") on the AP only and raises ValueError("AP required") elsewhere
    # (extmod/network_cyw43.c:371-388, v1.29.0): asked on the STA, the query is a failed check, never "no client".
    client = _make_client()
    assert run(client._get_hotspot_stations()) is None
    assert _wlan(client).status_calls == ["stations"]


def test_get_hotspot_stations_reads_the_unfilled_answer_as_a_failed_check() -> None:
    # A chip that cannot come up leaves status("stations") at its 32-entry buffer, unfilled (cyw43_ctrl.c:717-730,
    # v1.29.0): a failed check like a raise. Any other answer is the list as read: 31 clients, or none.
    client = _make_client()
    radio = _on_the_ap(client)
    answers = []
    for count in (_STATIONS_UNSET, _STATIONS_UNSET - 1, 0):
        radio._stations = [(bytes(6),)] * count
        answers.append(run(client._get_hotspot_stations()))
    radio.raise_on["status"] = OSError("simulated stations failure")
    answers.append(run(client._get_hotspot_stations()))
    assert answers == [None, [(bytes(6),)] * (_STATIONS_UNSET - 1), [], None]


def _failed_stations_case(*, timer_running: bool) -> None:
    # Three failed checks with the window running, or stopped by a client: each runs the absent path once and not the
    # client's, so a window a client stopped is armed once more; one slot counts the failed checks.
    client = _make_client(hotspot_time_min=1)
    run(client.pr.setup())
    if timer_running:
        run(client._hotspot_client_absent())
    else:
        client._hotspot_client_connected()
    transitions: list[str] = []
    real_absent = client._hotspot_client_absent

    def connected() -> None:
        transitions.append("connected")

    async def absent() -> None:
        transitions.append("absent")
        await real_absent()

    client._hotspot_client_connected = connected  # type: ignore[method-assign]  # observed, not run
    client._hotspot_client_absent = absent  # type: ignore[method-assign]  # observed, then run
    _on_the_ap(client).raise_on["status"] = RuntimeError("simulated stations failure")
    for _ in range(3):
        run(client._manage_hotspot_stations())
    assert transitions == ["absent"] * 3, timer_running
    assert client._hotspot_timer_running is True, timer_running
    log = run(client.get_error_counter())
    assert _used_slots(log) == [code("W", "WLAN_STATIONS_UNKNOWN")] and log["WIFI"]["ErrCount"] == 3, (timer_running, log)
    if client._ledflash is not None:
        run(_stop_flash(client))


def test_a_failed_stations_query_counts_as_no_client() -> None:
    # Unconfirmed is no client (owner, 2026-10-08: "yes, record it that way"): a running window keeps running and
    # one a client stopped is armed again, so an unattended unit is never held on its hotspot.
    _failed_stations_case(timer_running=True)
    _failed_stations_case(timer_running=False)


def test_an_unconfirmed_stations_check_counts_as_no_client() -> None:
    # The raise and the unfilled answer each run the absent path (arming the window when none runs), never the
    # client's; one slot counts them. An empty list arms the window with no warning; a listed client stops it.
    client = _make_client(hotspot_time_min=1)
    run(client.pr.setup())
    radio = _on_the_ap(client)
    seen: list[tuple[bool, bool]] = []  # (the hotspot pattern runs, the window runs) after each check

    async def check(answer: "list[tuple[bytes, ...]] | None") -> None:
        if answer is None:
            radio.raise_on["status"] = RuntimeError("simulated stations failure")
        else:
            radio.raise_on.pop("status", None)
            radio._stations = answer
        await client._manage_hotspot_stations()
        seen.append((client._led_pattern == _src_pattern("HOTSPOT"), client._hotspot_timer_running))

    async def scenario() -> "list[int]":
        await check(None)  # raises
        await check([_PHONE])  # a listed client
        await check([(bytes(6),)] * _STATIONS_UNSET)  # the chip-down answer
        await check(None)
        counts = [(await client.get_error_counter())["WIFI"]["ErrCount"]]
        await check([])
        counts.append((await client.get_error_counter())["WIFI"]["ErrCount"])
        await _stop_flash(client)
        return counts

    counts = run(scenario())
    assert seen == [(True, True), (False, False), (True, True), (True, True), (True, True)], seen
    assert counts == [3, 3], "an empty list is no client without a warning"
    assert _used_slots(run(client.get_error_counter())) == [code("W", "WLAN_STATIONS_UNKNOWN")]


def test_a_raising_stations_query_under_a_client_arms_the_window_until_the_next_good_check() -> None:
    # The query raising while a phone is listed counts as no client and arms the window; the next good check, five
    # seconds later on the device, still lists the phone and stops it, so a glitch never ends the window under a client.
    client = _make_client(hotspot_time_min=1)
    run(client.pr.setup())
    radio = _on_the_ap(client)
    radio._stations = [_PHONE]

    async def scenario() -> "list[bool]":
        running = []
        await client._manage_hotspot_stations()
        running.append(client._hotspot_timer_running)
        radio.raise_on["status"] = OSError("simulated stations failure")
        await client._manage_hotspot_stations()
        running.append(client._hotspot_timer_running)
        del radio.raise_on["status"]
        await client._manage_hotspot_stations()
        running.append(client._hotspot_timer_running)
        await _stop_flash(client)
        return running

    assert run(scenario()) == [False, True, False]
    assert client._led_pattern == _src_pattern("HOTSPOT_CLIENT")
    assert _used_slots(run(client.get_error_counter())) == [code("W", "WLAN_STATIONS_UNKNOWN")]


def test_manage_hotspot_stations_with_a_client_connected_stops_the_shutoff_timer() -> None:
    client = _make_client()
    _on_the_ap(client)._stations = [(b"\xaa\xbb\xcc\xdd\xee\xff",)]
    client._hotspot_timer.init(period=5000, mode=Timer.ONE_SHOT, callback=lambda _b: None)
    run(client._manage_hotspot_stations())
    assert client._hotspot_timer.deinit_called is True


def test_manage_hotspot_stations_with_no_client_arms_the_shutoff_timer() -> None:
    client = _make_client(hotspot_time_min=1)
    _on_the_ap(client)._stations = []
    run(client._manage_hotspot_stations())
    assert client._hotspot_timer_running is True


def test_run_hotspot_mode_starts_hotspot_when_no_ip_yet() -> None:
    client = _make_client()
    _wlan(client)._status = network.STAT_IDLE
    start_calls = [0]

    async def fake_start() -> None:
        start_calls[0] += 1

    client._start_hotspot = fake_start  # type: ignore[method-assign]  # deliberate monkeypatch
    run(client._run_hotspot_mode())
    assert start_calls[0] == 1


def test_run_hotspot_mode_re_activates_without_a_mode_switch_when_the_selected_ap_reports_no_link() -> None:
    # An AP that is selected but reports no link is brought up again in place (configured only if inactive),
    # and counts as "no client", so the hotspot timer still returns the unit to STA.
    client = _make_client()
    _on_the_ap(client).active(False)  # the selected AP down: the fake's own link rule answers STAT_IDLE
    calls: list[str] = []

    async def select(mode: int) -> bool:
        calls.append("select")
        return mode >= 0

    async def bring_up() -> None:
        calls.append("bring_up")

    async def absent() -> None:
        calls.append("absent")

    client._select_wifi_mode = select  # type: ignore[method-assign]  # observed, not run
    client._bring_up_hotspot_ap = bring_up  # type: ignore[method-assign]  # observed, not run
    client._hotspot_client_absent = absent  # type: ignore[method-assign]  # observed, not run
    run(client._run_hotspot_mode())
    assert calls == ["bring_up", "absent"]


def test_run_hotspot_mode_manages_stations_once_ip_obtained() -> None:
    client = _make_client()
    _on_the_ap(client).active(True)  # an active AP reports STAT_GOT_IP on its own (cyw43/src/cyw43_lwip.c:300-320)
    manage_calls = [0]

    async def fake_manage() -> None:
        manage_calls[0] += 1

    client._manage_hotspot_stations = fake_manage  # type: ignore[method-assign]  # deliberate monkeypatch
    run(client._run_hotspot_mode())
    assert manage_calls[0] == 1


def test_leave_hotspot_mode_switches_back_to_sta_and_cancels_dns_task() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_HOTSPOT
    select_calls: list[int] = []

    async def fake_select(mode: int) -> bool:
        select_calls.append(mode)
        return True

    client._select_wifi_mode = fake_select  # type: ignore[method-assign]  # deliberate monkeypatch

    async def _sleep_forever() -> None:
        # asyncio.create_task() requires a real coroutine object, not the awaitable
        # asyncio.sleep(...) itself returns on this port - confirmed directly ("TypeError:
        # coroutine expected") - so this thin async def wrapper is the fix, not a style choice.
        await asyncio.sleep(100)

    async def scenario() -> bool:
        client._dns_server_task = asyncio.create_task(_sleep_forever())
        await client._leave_hotspot_mode()
        return (client._conn_phase != _PHASE_HOTSPOT) and (client._dns_server_task is None)

    assert run(scenario()) is True
    assert select_calls == [network.STA_IF]


def test_wait_for_sta_disconnect_acquires_and_releases_the_lock() -> None:
    client = _make_client()
    _wlan(client)._connected = False
    run(client._wait_for_sta_disconnect())
    assert client.wifi_mode_lock.locked() is False
    assert _wlan(client).disconnect_called is True


def test_handle_reconnect_trigger_hotspot_mode_leaves_hotspot() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_HOTSPOT
    leave_calls = [0]

    async def fake_leave() -> None:
        leave_calls[0] += 1

    client._leave_hotspot_mode = fake_leave  # type: ignore[method-assign]  # deliberate monkeypatch
    run(client._handle_reconnect_trigger())
    assert leave_calls[0] == 1
    assert client._reconn_wifi is False


def test_handle_reconnect_trigger_sta_mode_waits_for_disconnect() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_STA_SEEKING
    wait_calls = [0]

    async def fake_wait() -> None:
        wait_calls[0] += 1

    client._wait_for_sta_disconnect = fake_wait  # type: ignore[method-assign]  # deliberate monkeypatch
    run(client._handle_reconnect_trigger())
    assert wait_calls[0] == 1


# ---------------------------------------------------------------------------
# _reset_wlan_connect_state() - runs at the top of every _connect_loop() task (re)start: clears the
# per-run failure bookkeeping, preserves _conn_phase when a restart lands mid-hotspot, and computes
# _reconn_wifi from that phase plus the real WLAN driver state. These isolate it directly.
# ---------------------------------------------------------------------------


def test_reset_wlan_connect_state_preserves_hotspot_phase_across_a_restart() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_HOTSPOT
    client._reset_wlan_connect_state()
    assert client._conn_phase == _PHASE_HOTSPOT


def test_reset_wlan_connect_state_resets_sta_established_to_seeking() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_STA_ESTABLISHED
    client._reset_wlan_connect_state()
    assert client._conn_phase == _PHASE_STA_SEEKING


def test_reset_wlan_connect_state_preserves_deactivated_phase_across_a_restart() -> None:
    # A task restart (e.g. after the _hw_op_failed streak gives up) keeps the no-configuration state: with no
    # readable Wi-Fi configuration the radio stays unused until a reboot (Part A.4), same casing as _PHASE_HOTSPOT.
    client = _make_client()
    client._conn_phase = _PHASE_DEACTIVATED
    client._reset_wlan_connect_state()
    assert client._conn_phase == _PHASE_DEACTIVATED


def test_reset_wlan_connect_state_preserves_silent_phase_across_a_restart() -> None:
    # The silent mode survives a task restart (owner, 2026-10-08: "Entering the hotspot mode only through a reboot,
    # as is."); the restart's own reconnect keeps it too.
    client = _make_client()
    client._conn_phase = _PHASE_SILENT
    _wlan(client)._active = True  # as the last silent attempt left the radio
    client._reset_wlan_connect_state()
    assert (client._conn_phase, client._reconn_wifi) == (_PHASE_SILENT, True)
    with FastAsyncSleep():
        run(client._handle_reconnect_trigger())
    assert client._conn_phase == _PHASE_SILENT


def test_reset_wlan_connect_state_clears_failure_counters_and_hotspot_started_once() -> None:
    client = _make_client()
    client._connection_failures = 3
    client._hotspot_started_once = True
    client._reset_wlan_connect_state()
    assert client._connection_failures == 0
    assert client._hotspot_started_once is False


def test_reset_wlan_connect_state_cancels_ledflash_and_dns_server_task() -> None:
    client = _make_client()

    async def _sleep_forever() -> None:
        await asyncio.sleep(100)

    async def scenario() -> "tuple[bool, bool]":
        client._ledflash = asyncio.create_task(_sleep_forever())
        client._dns_server_task = asyncio.create_task(_sleep_forever())
        client._reset_wlan_connect_state()
        return client._ledflash is None, client._dns_server_task is None

    ledflash_cleared, dns_task_cleared = run(scenario())
    assert ledflash_cleared is True
    assert dns_task_cleared is True


def test_reset_wlan_connect_state_sets_reconn_wifi_true_when_hotspot() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_HOTSPOT
    client._reset_wlan_connect_state()
    assert client._reconn_wifi is True


def test_reset_wlan_connect_state_sets_reconn_wifi_true_when_already_connected() -> None:
    client = _make_client()
    _wlan(client)._connected = True
    client._reset_wlan_connect_state()
    assert client._reconn_wifi is True


def test_reset_wlan_connect_state_sets_reconn_wifi_true_when_wlan_active_but_not_connected() -> None:
    client = _make_client()
    _wlan(client)._active = True
    client._reset_wlan_connect_state()
    assert client._reconn_wifi is True


def test_reset_wlan_connect_state_sets_reconn_wifi_false_when_seeking_and_wlan_is_idle() -> None:
    client = _make_client()
    client._reset_wlan_connect_state()
    assert client._reconn_wifi is False


def test_reset_wlan_connect_state_degrades_to_reconn_wifi_true_on_exception() -> None:
    # A real exception checking wlan.isconnected()/active() at task-start time is rare (once per
    # task (re)start) but must still force a safe reconnect-on-next-iteration default rather than
    # silently under-reacting.
    client = _make_client()
    run(client.pr.setup())
    _wlan(client).raise_on["isconnected"] = RuntimeError("simulated hardware fault")
    client._reset_wlan_connect_state()
    assert client._reconn_wifi is True


def test_reset_wlan_connect_state_turns_the_led_off() -> None:
    led = _FakeLED()
    client = _make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    client._led_on()
    client._reset_wlan_connect_state()
    assert led.off_calls == 1


def test_a_restart_in_hotspot_ends_in_sta_with_a_fresh_streak() -> None:
    # Guard (the behaviour is unchanged; holds at once): the restart keeps HOTSPOT only so the forced
    # reconnect leaves it through _leave_hotspot_mode(), as legacy's own restart did.
    client = _make_client()
    client._conn_phase = _PHASE_HOTSPOT
    client._hotspot_started_once = True
    client._connection_failures = 3
    modes: list[int] = []

    async def select(mode: int) -> bool:
        modes.append(mode)
        return True

    client._select_wifi_mode = select  # type: ignore[method-assign]  # the mode switch is not under test
    _no_sta(client)

    async def sleep_forever() -> None:
        await asyncio.sleep(3600)

    async def scenario() -> "tuple[asyncio.Task[None], asyncio.Task[None]]":
        dns_task = asyncio.create_task(sleep_forever())
        client._dns_server_task = dns_task
        loop = asyncio.create_task(client._connect_loop())
        await _drive(12)  # two loop iterations
        await cancel(loop)
        return dns_task, loop

    with FastAsyncSleep():
        dns_task, _loop = run(scenario())
    assert client._conn_phase == _PHASE_STA_SEEKING
    assert client._hotspot_started_once is False
    assert client._connection_failures == 0
    assert modes == [network.STA_IF]
    assert client._dns_server_task is None and dns_task.done()


# ---------------------------------------------------------------------------
# _connect_loop() - the task-supervisor entry point: pr.setup(), the fresh _err_cnt_internal streak,
# and max_module_error/_error_check() giving up after repeated WLAN-hardware-exception cycles - a
# coarser safety net than the AP-reachability-driven conn_fail_to_hotspot fallback, independent of it.
# ---------------------------------------------------------------------------


def test_setup_runs_both_loggers_in_the_boot_batch() -> None:
    # The boot batch's setup() readies this service's own logger and the captive DNS server's separate
    # one; the connect loop sets up neither (SPECIFICATION.md A.7).
    client = _make_client()
    before = (client.pr.initialized, client._dns_server.pr.initialized)
    assert run(client.setup()) is True
    assert before == (False, False)
    assert (client.pr.initialized, client._dns_server.pr.initialized) == (True, True)

    unset = _make_client()

    async def scenario() -> "tuple[bool, bool]":
        task = asyncio.create_task(unset._connect_loop())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        states = (unset.pr.initialized, unset._dns_server.pr.initialized)
        await cancel(task)
        return states

    with FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario()) == (False, False)


def test_wlan_connect_resets_err_cnt_internal_at_the_start_of_every_run() -> None:
    client = _make_client()
    client._err_cnt_internal = 99

    async def scenario() -> int:
        task = asyncio.create_task(client._connect_loop())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        streak = client._err_cnt_internal
        await cancel(task)
        return streak

    with FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario()) == 0


def test_wlan_connect_skips_the_state_machine_entirely_while_deactivated() -> None:
    client = _make_client()
    sta_calls = [0]

    async def fake_apply_led_cfg() -> None:
        client._conn_phase = _PHASE_DEACTIVATED  # simulates the missing-config path without a real cfg fault

    async def fake_run_sta_mode() -> None:
        sta_calls[0] += 1

    client._apply_initial_led_config = fake_apply_led_cfg  # type: ignore[method-assign]  # deliberate monkeypatch
    client._run_sta_mode = fake_run_sta_mode  # type: ignore[method-assign]  # deliberate monkeypatch

    async def scenario() -> int:
        task = asyncio.create_task(client._connect_loop())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        calls = sta_calls[0]
        await cancel(task)
        return calls

    with FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario()) == 0


def test_wlan_connect_dispatches_to_hotspot_mode_when_conn_phase_is_hotspot() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_HOTSPOT
    hotspot_calls = [0]
    sta_calls = [0]

    async def fake_reconnect() -> None:
        return None  # isolates this test to the phase-dispatch branch, not the reconnect-trigger path

    async def fake_hotspot() -> None:
        hotspot_calls[0] += 1

    async def fake_sta() -> None:
        sta_calls[0] += 1

    client._handle_reconnect_trigger = fake_reconnect  # type: ignore[method-assign]  # deliberate monkeypatch
    client._run_hotspot_mode = fake_hotspot  # type: ignore[method-assign]  # deliberate monkeypatch
    client._run_sta_mode = fake_sta  # type: ignore[method-assign]  # deliberate monkeypatch

    async def scenario() -> "tuple[int, int]":
        task = asyncio.create_task(client._connect_loop())
        for _ in range(4):
            await asyncio.sleep(0)
        calls = hotspot_calls[0], sta_calls[0]
        await cancel(task)
        return calls

    with FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        hotspot_called, sta_called = run(scenario())
    assert hotspot_called >= 1
    assert sta_called == 0


def test_wlan_connect_dispatches_to_sta_mode_when_conn_phase_is_not_hotspot() -> None:
    client = _make_client()
    hotspot_calls = [0]
    sta_calls = [0]

    async def fake_hotspot() -> None:
        hotspot_calls[0] += 1

    async def fake_sta() -> None:
        sta_calls[0] += 1

    client._run_hotspot_mode = fake_hotspot  # type: ignore[method-assign]  # deliberate monkeypatch
    client._run_sta_mode = fake_sta  # type: ignore[method-assign]  # deliberate monkeypatch

    async def scenario() -> "tuple[int, int]":
        task = asyncio.create_task(client._connect_loop())
        for _ in range(4):
            await asyncio.sleep(0)
        calls = hotspot_calls[0], sta_calls[0]
        await cancel(task)
        return calls

    with FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        hotspot_called, sta_called = run(scenario())
    assert sta_called >= 1
    assert hotspot_called == 0


def test_wlan_connect_calls_handle_reconnect_trigger_when_reconn_wifi_is_set() -> None:
    # A task (re)start while the driver still reports connected forces _reconn_wifi=True via
    # _reset_wlan_connect_state() - _connect_loop()'s loop must act on that the very first iteration,
    # not only on one following an explicit reconnect_wifi()/hotspot-timer trigger.
    client = _make_client()
    _wlan(client)._connected = True
    reconnect_calls = [0]

    async def fake_reconnect() -> None:
        reconnect_calls[0] += 1
        client._reconn_wifi = False  # avoid retriggering every loop iteration

    async def fake_sta() -> None:
        return None

    client._handle_reconnect_trigger = fake_reconnect  # type: ignore[method-assign]  # deliberate monkeypatch
    client._run_sta_mode = fake_sta  # type: ignore[method-assign]  # deliberate monkeypatch

    async def scenario() -> int:
        task = asyncio.create_task(client._connect_loop())
        for _ in range(4):
            await asyncio.sleep(0)
        calls = reconnect_calls[0]
        await cancel(task)
        return calls

    with FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario()) == 1


def test_connect_loop_gives_up_after_repeated_hardware_failures_and_persists_both_entries() -> None:
    client = _make_client(max_module_error=2)

    async def failing_run_sta_mode() -> None:
        client._hw_op_failed = True  # simulates a real WLAN-hardware exception every cycle

    client._run_sta_mode = failing_run_sta_mode  # type: ignore[method-assign]  # deliberate monkeypatch

    async def scenario() -> "ErrorLog":
        task = asyncio.create_task(client._connect_loop())
        await asyncio.wait_for(task, _CONNECT_BOUND_S)  # must actually complete, not loop forever
        return await client.get_error_counter()

    with FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        counter = run(scenario())
    kept = _used_slots(counter)
    # The base streak's GIVE_UP, then WIFI's own give-up entry: each layer keeps its own, once.
    assert kept.count(code("E", "GIVE_UP")) == 1 and kept.count(code("E", "WLAN_GIVE_UP")) == 1, kept
    assert _last_err(counter, "ErrNum") == code("E", "WLAN_GIVE_UP")


def test_wlan_connect_never_gives_up_while_repeatedly_succeeding() -> None:
    client = _make_client(max_module_error=2)

    async def succeeding_run_sta_mode() -> None:
        return None  # _hw_op_failed stays False (reset every iteration by _connect_loop() itself)

    client._run_sta_mode = succeeding_run_sta_mode  # type: ignore[method-assign]  # deliberate monkeypatch

    async def scenario() -> bool:
        task = asyncio.create_task(client._connect_loop())
        for _ in range(10):
            await asyncio.sleep(0)
        still_running = not task.done()
        await cancel(task)
        return still_running

    with FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario()) is True


def test_wlan_connect_recovers_the_streak_on_alternating_failure_and_success() -> None:
    # Proves the give-up decision is a genuine streak, not a monotonic lifetime counter: a success
    # decrements _err_cnt_internal (asy_base_classes.py's own _error_check() contract), so failures that
    # never land two-in-a-row must never trip max_module_error=2, however many cycles run in total.
    client = _make_client(max_module_error=2)
    toggle = [True]

    async def alternating_run_sta_mode() -> None:
        client._hw_op_failed = toggle[0]
        toggle[0] = not toggle[0]

    client._run_sta_mode = alternating_run_sta_mode  # type: ignore[method-assign]  # deliberate monkeypatch

    async def scenario() -> bool:
        task = asyncio.create_task(client._connect_loop())
        for _ in range(20):
            await asyncio.sleep(0)
        still_running = not task.done()
        await cancel(task)
        return still_running

    with FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario()) is True


# ---------------------------------------------------------------------------
# The radio rung: the failure streak's participant recovery re-selects the current mode, whose deinit()
# powers the CYW43 off and whose next active(True) reloads its firmware; never while deactivated.
# ---------------------------------------------------------------------------


class _CountedWLAN:
    # Counts the WLAN interfaces constructed (by interface id) for the `with` block.
    def __enter__(self) -> "Self":
        self.built: list[int] = []
        self._real = network.WLAN
        real, built = self._real, self.built

        def counted(if_id: int) -> "network.WLAN":
            built.append(if_id)
            return real(if_id)

        network.WLAN = counted  # type: ignore[assignment, misc]  # a module attribute swap, restored on exit
        return self

    def __exit__(self, *exc_info: object) -> None:
        network.WLAN = self._real  # type: ignore[misc]


async def _failing_iterations(client: WifiService, iterations: int) -> None:
    # Runs _connect_loop() until it has completed `iterations` failing STA iterations, then cancels it.
    _no_sta(client, failing=True)
    task = asyncio.create_task(client._connect_loop())
    for _ in range(200):  # bounded: each iteration's sleeps are single yields
        if client._err_cnt_internal >= iterations:
            break
        await asyncio.sleep(0)
    await _drive(8)  # let the iteration's rung finish its mode switch
    await cancel(task)


def test_two_failed_iterations_re_select_the_radio_once() -> None:
    client = _make_client()
    run(client.pr.setup())
    first = _wlan(client)
    with FastAsyncSleep(), _CountedWLAN() as wlan:
        run(_failing_iterations(client, 4))
    assert wlan.built == [network.STA_IF]  # once per episode, though four iterations failed
    assert first.deinit_called is True
    kept = _used_slots(run(client.get_error_counter()))
    assert kept.count(code("W", "DEVICE_RECOVERY")) == 1, kept


def test_in_hotspot_the_ap_is_re_selected() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_HOTSPOT
    with FastAsyncSleep(), _CountedWLAN() as wlan:
        assert run(client._recover_device()) is True
    assert wlan.built == [network.AP_IF]
    assert client._ap_selected is True


def test_deactivated_makes_no_radio_call() -> None:
    client = _make_client()
    client._conn_phase = _PHASE_DEACTIVATED
    first = _wlan(client)
    with FastAsyncSleep(), _CountedWLAN() as wlan:
        assert run(client._recover_device()) is None  # no participant rung: no radio in use
    assert wlan.built == []
    assert first.deinit_called is False and first.disconnect_called is False


def test_a_raising_deinit_logs_one_mode_switch_entry_and_no_recovery_warning() -> None:
    client = _make_client()
    run(client.pr.setup())
    _wlan(client).raise_on["deinit"] = RuntimeError("simulated hardware fault")
    with FastAsyncSleep(), _CountedWLAN() as wlan:
        run(_failing_iterations(client, 3))
    assert wlan.built == []
    kept = _used_slots(run(client.get_error_counter()))
    assert kept.count(code("E", "WLAN_MODE_SWITCH")) == 1, kept
    assert code("W", "DEVICE_RECOVERY") not in kept, kept


def test_the_radio_rung_fires_again_after_a_restart_and_a_good_iteration() -> None:
    client = _make_client()
    run(client.pr.setup())

    async def one_good_iteration() -> None:
        _no_sta(client)
        task = asyncio.create_task(client._connect_loop())
        await _drive(4)
        await cancel(task)

    with FastAsyncSleep(), _CountedWLAN() as wlan:
        run(_failing_iterations(client, 2))
        run(one_good_iteration())  # a restart, then an iteration without a failure: the episode ends
        run(_failing_iterations(client, 2))
    assert wlan.built == [network.STA_IF, network.STA_IF]


# ---------------------------------------------------------------------------
# Integration tests: real (not mocked) captive DNS server - downstream. _configure_hotspot_ap()
# starts a real CaptiveDNS.run() task over a real UDPSocket, so a genuinely malformed/off-subnet
# datagram is handled end to end rather than in isolation.

# CaptiveDNS.__init__ hardcodes privileged port 53 (no root in CI), redirected here by swapping
# client._dns_server._udps for a fresh UDPSocket on a free ephemeral port before starting the
# hotspot, since CaptiveDNS.run() only ever touches self._udps and never rebuilds it.
# ---------------------------------------------------------------------------

# This file's own band of tests/_port_bands.py, since files run concurrently. A duplicate unicast UDP bind does not
# fail with EADDRINUSE here (both sockets set SO_REUSEADDR, confirmed directly): each datagram reaches one socket only,
# so a collision surfaces as an inexplicable timeout rather than an error.
_PORTS = PortAllocator("asy_wifi_service")


def _make_addr() -> "tuple[str, int]":
    return ("127.0.0.1", _PORTS.next())


def _dns_query_packet(domain: str) -> bytes:
    # Minimal standard-query DNS packet DNSQuery.__init__ can parse: a 12-byte header (opcode bits
    # zero), the QNAME as length-prefixed labels ending in a zero-length label, then
    # QTYPE=A/QCLASS=IN: an A query gets the A record.
    header = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    qname = b"".join(bytes([len(label)]) + label.encode("ascii") for label in domain.split(".")) + b"\x00"
    return header + qname + b"\x00\x01\x00\x01"


async def _start_real_hotspot(client: WifiService, server_addr: "tuple[str, int]") -> None:
    # Same-subnet own_ip/netmask as the test client's own loopback source address, so
    # CaptiveDNS.run()'s subnet filter doesn't reject the test query as off-subnet.
    _wlan(client)._ifconfig = ("127.0.0.1", "255.255.255.0", "127.0.0.1", "127.0.0.1")
    client._dns_server._udps = UDPSocket(server_addr, mode="server")
    await client._activate_hotspot_ap("US", "TestHost", "12345678")


def test_integration_hotspot_captive_dns_ignores_a_malformed_packet_without_crashing() -> None:
    # "Interrupted packet": a datagram far too short to contain a DNS header, sent from a genuine second socket
    # over a real loopback round trip. A well-formed query follows it: its reply is the proof the server read
    # past the malformed one, so no wait margin is involved, and the only reply carries the query's ID.
    client = _make_client()
    server_addr = _make_addr()

    async def scenario() -> "tuple[list[bytes], bool]":
        await _start_real_hotspot(client, server_addr)
        assert client._dns_server_task is not None
        replies: list[bytes] = []
        try:
            for _ in range(_CONNECT_POLL_TRIES):  # bounded: a datagram sent before the bind is simply lost
                if client._dns_server._udps.connected:
                    break
                await asyncio.sleep_ms(_CONNECT_POLL_MS)
            cli = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            cli.setblocking(False)
            # The raw test socket is outside the shim: this Unix build's sendto() takes the resolved sockaddr.
            target = socket.getaddrinfo(*server_addr)[0][-1]
            cli.sendto(b"\x01\x02", target)  # 2 bytes - nowhere near a 12-byte header
            cli.sendto(_dns_query_packet("after.example.com"), target)
            poller = select.poll()
            poller.register(cli, select.POLLIN)
            for _ in range(_SENT_POLL_TRIES):  # bounded: the well-formed query's reply, then nothing more
                if any(event & select.POLLIN for _fd, event in poller.ipoll(0)):
                    replies.append(cli.recv(512))
                elif replies:
                    break
                await asyncio.sleep_ms(_SENT_POLL_MS)
            return replies, not client._dns_server_task.done()  # the malformed packet didn't kill the task
        finally:
            await cancel(client._dns_server_task)

    replies, alive = run(scenario())
    assert [reply[:2] for reply in replies] == [b"\x12\x34"], replies
    assert alive is True


class _ScriptedUDPSocket:
    # Feeds a scripted sequence of (data, addr) pairs to CaptiveDNS.run()'s real recvfrom(): a loopback
    # round trip always arrives from 127.0.0.1, so an AP client's address and an off-subnet source are scripted.
    def __init__(self, script: "list[tuple[bytes, tuple[str, int]]]") -> None:
        self._script = list(script)
        self.sent: list[tuple[bytes, tuple[str, int]]] = []
        self.connected = True  # bound, as UDPSocket reports it

    async def disconnect(self) -> None:
        return None

    async def recvfrom(self, _bufsize: int) -> "tuple[bytes, tuple[str, int]] | tuple[None, None]":
        if not self._script:
            await asyncio.sleep(3600)  # nothing more to deliver - park forever, caller cancels us
        return self._script.pop(0)

    async def sendto(self, data: bytes, addr: "tuple[str, int]") -> int:
        self.sent.append((data, addr))
        return len(data)


def test_integration_hotspot_captive_dns_answers_an_on_subnet_query() -> None:
    client = _make_client()
    fake_udps = _ScriptedUDPSocket([(_dns_query_packet("test.example.com"), ("192.168.4.55", 5353))])
    client._dns_server._udps = fake_udps  # type: ignore[assignment]  # duck-typed fake, same pattern as asy_captive_dns.py's own tests

    async def scenario() -> None:
        task = asyncio.create_task(client._dns_server.run("192.168.4.1", "255.255.255.0"))
        for _ in range(_SENT_POLL_TRIES):
            if fake_udps.sent:
                break
            await asyncio.sleep_ms(_SENT_POLL_MS)
        await cancel(task)

    run(scenario())
    assert len(fake_udps.sent) == 1
    reply, addr = fake_udps.sent[0]
    assert addr == ("192.168.4.55", 5353)
    assert reply[:2] == b"\x12\x34"  # echoes the query's own transaction ID
    assert reply[-4:] == bytes([192, 168, 4, 1])  # resolves to own_ip


def test_integration_hotspot_captive_dns_ignores_an_off_subnet_query() -> None:
    # A well-formed query from an address outside the AP's own subnet must be silently ignored (see
    # CaptiveDNS.run()'s on_subnet check) - proves the filter, not just "any query gets answered".
    client = _make_client()
    fake_udps = _ScriptedUDPSocket([(_dns_query_packet("test.example.com"), ("10.0.0.55", 5353))])
    client._dns_server._udps = fake_udps  # type: ignore[assignment]  # duck-typed fake, same pattern as asy_captive_dns.py's own tests

    async def scenario() -> None:
        task = asyncio.create_task(client._dns_server.run("192.168.4.1", "255.255.255.0"))
        await asyncio.sleep(_OFF_SUBNET_WAIT_S)
        await cancel(task)

    run(scenario())
    assert fake_udps.sent == []


# ---------------------------------------------------------------------------
# Integration tests: the full _connect_loop() task end to end through the fake network.WLAN, proving
# how a real connect success/failure sequence propagates up through get_data()/get_error_counter()
# and _connection_failures/hotspot fallback. Mirrors test_asy_ntp_client.py's own section.
# ---------------------------------------------------------------------------


def test_integration_sta_connect_succeeds_and_propagates_to_get_data() -> None:
    # Simulates a driver reporting a connection established the instant connect() is called;
    # _poll_sta_connect_status() then returns after its first status read.

    # get_data()'s cached snapshot is only ever pushed by _uptime_loop()'s own task, so that is
    # driven here alongside _connect_loop(), exactly like a real task-starter set would.
    client = _make_client_with_json(_VALID_JSON)
    original_connect = _wlan(client).connect

    def fake_connect(ssid: str, pw: str) -> None:
        original_connect(ssid, pw)
        _wlan(client)._status = network.STAT_GOT_IP
        _wlan(client)._connected = True

    _wlan(client).connect = fake_connect  # type: ignore[assignment, method-assign]  # the fake radio joins at once

    async def scenario() -> "tuple[bool, bool | None]":
        connect_task = asyncio.create_task(client._connect_loop())
        counter_task = asyncio.create_task(client._uptime_loop())
        connected_once = False
        for _ in range(_CONNECT_POLL_TRIES):
            client._time_counter_trigger_event.set()
            await asyncio.sleep_ms(_CONNECT_POLL_MS)
            data = await client.get_data()
            if data.Connected:
                connected_once = client._conn_phase == _PHASE_STA_ESTABLISHED
                break
        await cancel(connect_task)
        await cancel(counter_task)
        return connected_once, (await client.get_data()).Connected

    with FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        connected_once, data_connected = run(scenario())
    assert connected_once is True
    assert data_connected is True


def test_integration_repeated_wrong_password_falls_back_to_hotspot_mode() -> None:
    client = _make_client_with_json(_VALID_JSON, conn_fail_to_hotspot=3)
    _wlan(client)._status = network.STAT_WRONG_PASSWORD  # every _poll_sta_connect_status() call sees this

    async def scenario() -> bool:
        task = asyncio.create_task(client._connect_loop())
        for _ in range(_PHASE_POLL_TRIES):
            if client._conn_phase == _PHASE_HOTSPOT:
                break
            await asyncio.sleep_ms(_PHASE_POLL_MS)
        hotspot_reached = client._conn_phase == _PHASE_HOTSPOT
        await cancel(task)
        return hotspot_reached

    with FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario())


_PHONE = (b"\x02\x00\x00\x00\x00\x01",)  # one status("stations") entry: the station's MAC first


class _HotspotRadio:
    # network.WLAN for the block: a STA finds no access point until `router_up`, then joins on connect(); an AP lists
    # `stations`, which the test edits in place. Each interface is one static object (extmod/network_cyw43.c:96-103),
    # wrapped once; a STA construction finds no access point again, as a radio brought back up after deinit() does.
    def __init__(self) -> None:
        self.stations: list[tuple[bytes, ...]] = []
        self.station_checks = 0  # the stations queries the AP has answered
        self.router_up = False
        self.built: list[_FakeWLAN] = []  # the interface each construction answered, in order
        self._joined_before: list[int] = []  # its connect() count when each construction answered it
        self._wrapped: set[int] = set()

    def __enter__(self) -> "Self":
        self._real = network.WLAN
        network.WLAN = self._build  # type: ignore[assignment, misc]  # a module attribute swap, restored on exit
        return self

    def __exit__(self, *exc_info: object) -> None:
        network.WLAN = self._real  # type: ignore[misc]

    def _build(self, if_id: int) -> "_FakeWLAN":
        wlan: _FakeWLAN = self._real(if_id)  # type: ignore[assignment]  # the fake, which mypy sees as the board stub's WLAN
        self.built.append(wlan)
        self._joined_before.append(len(wlan.connect_calls))
        if wlan.if_id == network.STA_IF:
            wlan._status = network.STAT_NO_AP_FOUND
        if wlan.if_id in self._wrapped:
            return wlan
        self._wrapped.add(wlan.if_id)
        if wlan.if_id == network.AP_IF:
            wlan._stations = self.stations
            answer = wlan.status

            def status(*params: str) -> object:  # the call shape as given: a bare status() is the link status
                if params == ("stations",):
                    self.station_checks += 1
                return answer(*params)

            wlan.status = status  # type: ignore[method-assign]  # counts the stations queries
            return wlan
        record = wlan.connect

        def connect(ssid: str, pw: str) -> None:
            record(ssid, pw)
            if self.router_up:
                wlan._status, wlan._connected = network.STAT_GOT_IP, True

        wlan.connect = connect  # type: ignore[assignment, method-assign]  # joins once the router is up
        return wlan

    def joins(self, index: int) -> "list[tuple[str | None, str | None]]":
        # The connect() calls the interface of construction `index` took from that construction on.
        return self.built[index].connect_calls[self._joined_before[index] :]


class _ParkedFlag:
    # The hotspot watcher's flag, self-clearing like asyncio.ThreadSafeFlag, but its waiter parks on an asyncio.Event,
    # so no wait goes through select.poll() over a non-fd object (CLAUDE.md's poller rule).
    def __init__(self) -> None:
        self._event = asyncio.Event()

    def set(self) -> None:
        self._event.set()

    async def wait(self) -> None:
        await self._event.wait()
        self._event.clear()


async def _no_captive_dns(server_ip: str, netmask: str) -> None:
    await asyncio.Event().wait()  # parked until the hotspot is left: the captive DNS server's socket is not under test


async def _next_stations_check(radio: _HotspotRadio) -> bool:
    # Waits until the AP has answered one more stations query than it had when called.
    target = radio.station_checks + 1
    return await _until(lambda: radio.station_checks >= target)


def _hotspot_client(radio: _HotspotRadio, json_text: str = _VALID_JSON, max_module_error: int = 5) -> WifiService:
    # A unit on _HotspotRadio that falls back after one failed attempt, with a one-minute window; the watcher's flag
    # parks on an asyncio.Event and the captive DNS server is stubbed (its socket is not under test).
    client = _make_client_with_json(json_text, conn_fail_to_hotspot=1, hotspot_time_min=1, max_module_error=max_module_error)
    client._hotspot_timeout_trigger_event = _ParkedFlag()  # type: ignore[assignment]  # see _ParkedFlag
    client._dns_server.run = _no_captive_dns  # type: ignore[method-assign]  # its socket is not under test
    return client


async def _stop_all(client: WifiService, *tasks: "asyncio.Task[None]") -> None:
    for task in tasks + (client._ledflash, client._dns_server_task):  # a concatenation: a starred display is a SyntaxError here (Part F.1)
        if task is not None:
            await cancel(task)


def test_integration_a_hotspot_client_holds_the_unit_until_it_leaves_then_the_window_end_retries_sta() -> None:
    # The owner's rule (SPECIFICATION.md A.4): a client keeps the hotspot for as long as it stays; once none is left the
    # window runs and its end retries the stored network, inside the running tasks - no task restart and no reboot.
    with _HotspotRadio() as radio, FastAsyncSleep():
        client = _hotspot_client(radio)
        timer = client._hotspot_timer

        async def scenario() -> None:
            await client.pr.setup()
            loop = asyncio.create_task(client._connect_loop())
            watcher = client.start_asy_hotspot_timeout()
            try:
                # The router is down: the failed attempt brings the hotspot up, whose timer runs while no client is there.
                assert await _until(lambda: client._hotspot_timer_running), "the hotspot never came up with its timer"
                assert (client._conn_phase, client._ap_selected) == (_PHASE_HOTSPOT, True)
                radio.stations.append(_PHONE)
                assert await _next_stations_check(radio)
                assert (client._hotspot_timer_running, timer.callback) == (False, None), "a client must stop the timer"
                for window in range(3):  # three would-be window ends while the phone stays: nothing is armed to fire
                    timer.trigger()
                    assert await _next_stations_check(radio), window
                held = (client._conn_phase, client._ap_selected, client._reconn_wifi, len(radio.built))
                assert held == (_PHASE_HOTSPOT, True, False, 2), "the unit must stay in its hotspot while the client stays"
                arms = len(timer.arms)
                radio.stations.clear()
                assert await _next_stations_check(radio)
                assert client._hotspot_timer_running and len(timer.arms) == arms + 1, "the client's leaving must arm the timer"
                assert (timer.mode, timer.period, client._conn_phase) == (Timer.PERIODIC, 60000, _PHASE_HOTSPOT)
                radio.router_up = True
                timer.trigger()  # the window ends with no client: the soft callback sets the watcher's flag
                assert await _until(lambda: len(radio.built) == 3), "the window's end must leave the hotspot"
                sta = radio.built[2]
                left = (sta.if_id, client._conn_phase, client._ap_selected, client._dns_server_task, radio.joins(2))
                assert left == (network.STA_IF, _PHASE_STA_SEEKING, False, None, []), left
                assert await _until(lambda: client._conn_phase == _PHASE_STA_ESTABLISHED), "STA must be retried"
                assert radio.joins(2) == [("MyNetwork", "supersecret")]  # the stored settings
                assert not loop.done() and client._hotspot_started_once, "no task restart: the same loop carried it"
                kept = _used_slots(await client.get_error_counter())
                assert code("E", "WLAN_GIVE_UP") not in kept and code("W", "WLAN_SILENT") not in kept, kept
            finally:
                await _stop_all(client, loop, watcher)

        reboots = machine.reset_count
        run(scenario())
    assert machine.reset_count == reboots


async def _boot_into_the_hotspot(client: WifiService, radio: _HotspotRadio) -> None:
    # The router is down at boot: the one-attempt streak brings the hotspot up, its window running with no client.
    assert await _until(lambda: client._hotspot_timer_running), "the hotspot never came up with its timer"
    assert (client._conn_phase, client._ap_selected, len(radio.built)) == (_PHASE_HOTSPOT, True, 2)


async def _silent_attempt(client: WifiService, sta: "_FakeWLAN") -> bool:
    # Fires one silent period on the running tasks and waits until its one attempt reached the radio.
    if not await _until(lambda: client._hotspot_timer_running):
        return False
    target = len(sta.connect_calls) + 1
    client._hotspot_timer.trigger()
    return await _until(lambda: len(sta.connect_calls) >= target) and len(sta.connect_calls) == target


def test_integration_a_unit_goes_silent_after_its_second_streak_and_rejoins_when_the_router_returns() -> None:
    # The owner's sequence end to end on the running tasks (owner, 2026-10-08: "If the SSID stored in the configuration
    # is found in the available networks, run one reconnection try"): hotspot, window end, silent, then a link.
    with _HotspotRadio() as radio, FastAsyncSleep():
        client = _hotspot_client(radio)

        async def scenario() -> None:
            await client.pr.setup()
            loop = asyncio.create_task(client._connect_loop())
            watcher = client.start_asy_hotspot_timeout()
            try:
                await _boot_into_the_hotspot(client, radio)
                client._hotspot_timer.trigger()  # the window ends with the router still down
                assert await _until(lambda: client._conn_phase == _PHASE_SILENT), "the second streak must go silent"
                sta = radio.built[2]
                assert sta is radio.built[0]  # one static object per interface (extmod/network_cyw43.c:96-103)
                silent = (len(radio.built), client._ap_selected, client._dns_server_task, client._ledflash)
                assert silent == (3, False, None, None), silent
                for period in range(2):
                    assert await _silent_attempt(client, sta), period
                assert client._conn_phase == _PHASE_SILENT and len(radio.built) == 3, "no hotspot after the silent entry"
                radio.router_up = True
                client._hotspot_timer.trigger()
                assert await _until(lambda: client._conn_phase == _PHASE_STA_ESTABLISHED), "the router's return must link"
                assert radio.joins(2)[-1] == ("MyNetwork", "supersecret") and len(radio.joins(2)) == 4
                assert (client._hotspot_timer_running, client._hotspot_timer.callback) == (False, None)
                assert not loop.done(), "no task restart: the same loop carried it"
                kept = _used_slots(await client.get_error_counter())
                assert code("W", "WLAN_TO_HOTSPOT") in kept and code("W", "WLAN_SILENT") in kept, kept
                assert code("E", "WLAN_GIVE_UP") not in kept, kept
            finally:
                await _stop_all(client, loop, watcher)

        reboots = machine.reset_count
        run(scenario())
    assert machine.reset_count == reboots


def test_integration_new_credentials_over_the_hotspot_reopen_it_once_more() -> None:
    # A wrong credential typed on the hotspot page must not lock the user out (owner, 2026-10-08: "it did not turn WiFi
    # off, but went into hotspot mode once"): the fresh streak fails, the hotspot reopens, and only its end goes silent.
    with _HotspotRadio() as radio, FastAsyncSleep():
        client = _hotspot_client(radio)

        async def scenario() -> None:
            await client.pr.setup()
            loop = asyncio.create_task(client._connect_loop())
            watcher = client.start_asy_hotspot_timeout()
            try:
                await _boot_into_the_hotspot(client, radio)
                ok, results = await client.cfgmgr.write_config({"SSID": "OtherNet", "PW": "othersecret"})
                assert ok and results == {"SSID": "Valid", "PW": "Valid"}, results
                client.reconnect_wifi()  # the identity group's post hook, as the request path calls it
                assert await _until(lambda: len(radio.built) == 4 and client._hotspot_timer_running), "the hotspot must reopen"
                ap = radio.built[3]
                assert radio.joins(2) == [("OtherNet", "othersecret")] and ap.if_id == network.AP_IF
                assert (client._conn_phase, client._hotspot_started_once) == (_PHASE_HOTSPOT, True)
                client._hotspot_timer.trigger()  # the reopened window ends
                assert await _until(lambda: client._conn_phase == _PHASE_SILENT), "its end's streak must go silent"
                assert len(radio.built) == 5 and radio.joins(4) == [("OtherNet", "othersecret")]
            finally:
                await _stop_all(client, loop, watcher)

        run(scenario())


def test_integration_an_unfilled_stations_answer_never_holds_the_hotspot() -> None:
    # A radio whose stations answer stays unfilled cannot keep an unattended unit on its hotspot: the check that
    # follows a client's stop arms the window, and its end leaves the hotspot.
    with _HotspotRadio() as radio, FastAsyncSleep():
        client = _hotspot_client(radio)

        async def scenario() -> None:
            await client.pr.setup()
            loop = asyncio.create_task(client._connect_loop())
            watcher = client.start_asy_hotspot_timeout()
            try:
                await _boot_into_the_hotspot(client, radio)
                radio.stations.append(_PHONE)
                assert await _next_stations_check(radio)
                assert (client._hotspot_timer_running, client._conn_phase) == (False, _PHASE_HOTSPOT), "a listed client must stop the window"
                radio.stations[:] = [(bytes(6),)] * _STATIONS_UNSET  # the chip-down answer, in place
                assert await _next_stations_check(radio)
                assert client._hotspot_timer_running, "the unfilled answer must arm the window"
                client._hotspot_timer.trigger()
                assert await _until(lambda: len(radio.built) == 3), "the window's end must leave the hotspot"
                assert radio.built[2].if_id == network.STA_IF
                kept = _used_slots(await client.get_error_counter())
                assert code("W", "WLAN_STATIONS_UNKNOWN") in kept, kept
            finally:
                await _stop_all(client, loop, watcher)

        run(scenario())


def _observe_absent_ticks(client: WifiService) -> "list[int]":
    # The hardware streak each no-client tick of the hotspot starts from, in order; the tick itself runs unchanged.
    streak: list[int] = []
    real_absent = client._hotspot_client_absent

    async def absent() -> None:
        streak.append(client._err_cnt_internal)
        await real_absent()

    client._hotspot_client_absent = absent  # type: ignore[method-assign]  # observed, then run
    return streak


def test_integration_a_hotspot_window_that_cannot_be_armed_ends_the_task_and_its_restart_retries_sta() -> None:
    # With no window armed the hotspot never ends, so each failed arm is the iteration's hardware failure (owner,
    # 2026-10-13): one step per tick to the give-up, and the restart leaves the hotspot for a fresh STA streak.
    with _HotspotRadio() as radio, FastAsyncSleep():
        client = _hotspot_client(radio, max_module_error=2)
        streak = _observe_absent_ticks(client)

        async def scenario() -> None:
            await client.pr.setup()
            tasks = [asyncio.create_task(client._connect_loop())]
            try:
                assert await _until(tasks[0].done, 400), ("the streak never reached its give-up", streak)
                assert (streak, client._err_cnt_internal) == ([0, 1, 2], 3), (streak, client._err_cnt_internal)
                kept = _used_slots(await client.get_error_counter())
                for name in (("E", "TIMER"), ("W", "DEVICE_RECOVERY"), ("E", "GIVE_UP"), ("E", "WLAN_GIVE_UP")):
                    assert code(*name) in kept, (name, kept)
                assert (client._conn_phase, client._ap_selected, len(radio.built)) == (_PHASE_HOTSPOT, True, 3)
                radio.router_up = True  # back while the alarm pool stays exhausted
                tasks.append(asyncio.create_task(client._connect_loop()))  # the supervisor's restart
                assert await _until(lambda: client._conn_phase == _PHASE_STA_ESTABLISHED), "the restart must retry STA"
                sta = radio.built[3]
                left = (len(radio.built), sta.if_id, radio.joins(3), client._ap_selected, client._dns_server_task)
                assert left == (4, network.STA_IF, [("MyNetwork", "supersecret")], False, None), left
                fresh = (client._err_cnt_internal, client._connection_failures, client._hotspot_started_once)
                assert fresh == (0, 0, False), ("the restart must start a fresh streak with the hotspot available", fresh)
                assert not tasks[1].done()
            finally:
                await _stop_all(client, *tasks)

        with RaiseOnArm():  # Timer.init() refuses every arm (ENOMEM)
            run(scenario())


def test_integration_a_window_arm_that_succeeds_later_heals_the_streak() -> None:
    # Two ticks whose arm fails raise the streak to 2; once the pool has room the next tick arms the window and every
    # clean iteration heals one step, the task running on with its window armed once.
    with _HotspotRadio() as radio, FastAsyncSleep():
        client = _hotspot_client(radio)
        streak = _observe_absent_ticks(client)

        async def scenario() -> None:
            await client.pr.setup()
            loop = asyncio.create_task(client._connect_loop())
            try:
                with RaiseOnArm():
                    assert await _until(lambda: client._err_cnt_internal == 2), ("the failed arms never fed the streak", streak)
                assert await _until(lambda: len(streak) == 6), streak
                assert streak == [0, 1, 2, 1, 0, 0], streak
                running = (loop.done(), client._conn_phase, client._hotspot_timer_running, len(client._hotspot_timer.arms))
                assert running == (False, _PHASE_HOTSPOT, True, 1), running
            finally:
                await _stop_all(client, loop)

        run(scenario())


def test_get_cfg_schema_is_the_schema_in_source() -> None:
    # The one accessor an outside caller reads the schema through: a shared REST helper validates each write by it.
    assert _make_client().get_cfg_schema() == (_VAL_SSID + _VAL_PW + _VAL_COUNTRY + _VAL_HOSTNAME + _VAL_LED_WIFI_ON + _VAL_HOTSPOT_PW)


def test_write_config_via_public_cfg_schema_round_trips_a_real_value() -> None:
    # Proves get_cfg_schema()'s schema is actually usable for a real write, not just structurally equal - the exact
    # call shape api_helpers.py's cmd_post_check() now makes.
    client = _make_client()

    async def scenario() -> "tuple[bool, dict[str, int | float | str | bool | None] | None]":
        written, _ = await client.cfgmgr.write_config({"Hostname": "NewName"})
        data = await client.cfgmgr.get_dict(["Hostname"])
        return written, data

    written, data = run(scenario())
    assert written
    assert data == {"Hostname": "NewName"}


# ---------------------------------------------------------------------------
# Task/timer starter methods (SPECIFICATION.md Part C.9) - get_task_starters()/get_timer_starters()'s
# own shape is already checked above; the starter methods they return were never actually called.
# ---------------------------------------------------------------------------


def test_start_asy_wlan_connect_returns_a_real_task() -> None:
    client = _make_client()

    async def scenario() -> bool:
        task = client.start_asy_connect()
        await asyncio.sleep(0)
        is_task = isinstance(task, asyncio.Task)
        await cancel(task)
        return is_task

    assert run(scenario()) is True


def test_start_asy_uptime_counter_returns_a_real_task() -> None:
    client = _make_client()

    async def scenario() -> bool:
        task = client.start_asy_uptime()
        await asyncio.sleep(0)
        is_task = isinstance(task, asyncio.Task)
        await cancel(task)
        return is_task

    assert run(scenario()) is True


def test_stop_counter_timer_deinits_the_counter_timer() -> None:
    client = _make_client()
    client.start_uptime_timer()
    client.stop_uptime_timer()
    assert client._counter_timer.deinit_called is True


# The snapshot's timestamp is asy_base_classes.utc_now(): None until NTP has set the clock this boot
# ---------------------------------------------------------------------------


def test_the_snapshot_timestamp_is_none_until_the_clock_is_set() -> None:
    client = _make_client()
    try:
        asy_base_classes.set_utc_valid(valid=False)
        run(client._update_wifi_snapshot(connected=True))
        assert run(client.get_data()).TS is None
        assert run(client.get_data()).Mode == "STA"  # the rest of the snapshot is unaffected
        asy_base_classes.set_utc_valid()
        run(client._update_wifi_snapshot(connected=True))
        assert isinstance(run(client.get_data()).TS, int)
    finally:
        asy_base_classes.set_utc_valid(valid=False)


# ---------------------------------------------------------------------------
# _switch_wlan_mode() - only its exception path was exercised above; this drives the real
# deinit/reinit happy path (SPECIFICATION.md Part C.7's "attempt operations" convention).
# ---------------------------------------------------------------------------


def test_switch_wlan_mode_success_deinits_and_recreates_the_wlan() -> None:
    client = _make_client()
    original_wlan = _wlan(client)

    async def scenario() -> bool:
        return await client._select_wifi_mode(network.AP_IF)

    with FastAsyncSleep():
        assert run(scenario()) is True
    assert client._hw_op_failed is False
    assert original_wlan.deinit_called is True
    assert _wlan(client) is not original_wlan  # a fresh WLAN instance replaced it
    assert _wlan(client).if_id == network.AP_IF
    assert run(client.get_wifi_uptime()) == 0


def test_switch_wlan_mode_records_the_selected_interface() -> None:
    # The record the snapshot reads instead of the radio: True only once an AP interface really exists.
    client = _make_client()
    run(client.pr.setup())
    seen = [client._ap_selected]
    with FastAsyncSleep():
        for mode in (network.AP_IF, network.STA_IF, network.AP_IF):
            run(client._switch_wlan_mode(mode))
            seen.append(client._ap_selected)
        _wlan(client).raise_on["deinit"] = RuntimeError("simulated hardware fault")
        run(client._switch_wlan_mode(network.AP_IF))  # fails before the new interface exists
    seen.append(client._ap_selected)
    assert seen == [False, True, False, True, False], "the last: a failed switch must not leave it on a deinitialised AP"


# ---------------------------------------------------------------------------
# _get_hotspot_stations() / _hotspot_client_connected() - the finally-block lock release and the
# "_ledflash already running" cancel branch were never exercised.
# ---------------------------------------------------------------------------


def test_get_hotspot_stations_returns_the_real_station_list() -> None:
    client = _make_client()
    _on_the_ap(client)._stations = [(b"\xaa\xbb\xcc\xdd\xee\xff",), (b"\x01\x02\x03\x04\x05\x06",)]
    stations = run(client._get_hotspot_stations())
    assert stations == [(b"\xaa\xbb\xcc\xdd\xee\xff",), (b"\x01\x02\x03\x04\x05\x06",)]
    assert not client.wifi_mode_lock.locked()  # released via the finally block


def test_hotspot_client_connected_cancels_an_already_running_ledflash_task() -> None:
    client = _make_client()

    async def scenario() -> "tuple[bool, bool]":
        await client._hotspot_client_absent()  # starts a real _ledflash task
        first_flash = client._ledflash
        assert first_flash is not None
        client._hotspot_client_connected()  # must call first_flash.cancel() itself
        done = False
        try:
            await asyncio.wait_for(first_flash, _FLASH_CANCEL_BOUND_S)
        except asyncio.CancelledError:
            done = True
        except asyncio.TimeoutError:
            done = False
        swapped = client._ledflash is not None and client._ledflash is not first_flash  # the client pattern's own task
        await _stop_flash(client)
        return done, swapped

    assert run(scenario()) == (True, True)


# ---------------------------------------------------------------------------
# _poll_sta_connect_status(): IDLE, CONNECTING and joined-without-an-IP are in-progress states, printed
# and polled on; a poll that never leaves them persists one no-verdict warning.
# ---------------------------------------------------------------------------


def _script_status(client: WifiService, statuses: "list[int]") -> "list[tuple[object, ...]]":
    # status() answers each scripted value once, then repeats the last; returns the call record.
    calls: list[tuple[object, ...]] = []

    def status(*args: object) -> int:
        calls.append(args)
        return statuses.pop(0) if len(statuses) > 1 else statuses[0]

    _wlan(client).status = status  # type: ignore[method-assign]  # the scripted link statuses
    return calls


def _poll_printing(client: WifiService) -> "list[tuple[object, ...]]":
    # Runs one poll at full console detail (level 5) and returns the lines it printed.
    client.pr.set_level(5)
    with record_prints() as recorder, FastAsyncSleep():
        run(client._poll_sta_connect_status())
    return recorder.lines


def test_poll_sta_connect_status_prints_each_in_progress_state_and_persists_nothing_once_a_verdict_comes() -> None:
    for state, text in ((network.STAT_IDLE, "WLAN idle"), (network.STAT_CONNECTING, "WLAN connecting"), (_STAT_JOINED_NO_IP, "WLAN obtaining IP")):
        client = _make_client()
        run(client.pr.setup())
        _script_status(client, [state, network.STAT_GOT_IP])
        lines = _poll_printing(client)
        assert ("WIFI", text) in lines, (state, lines)
        assert ("WIFI", "WLAN connection successful") in lines, state
        assert client._hw_op_failed is False
        assert run(client.get_error_counter())["WIFI"]["ErrCount"] == 0, state


def test_a_poll_without_a_verdict_persists_one_warning_naming_the_last_status() -> None:
    # E.g. a DHCP server that never answers: joined, no IP, for the whole poll window.
    for state in (network.STAT_CONNECTING, _STAT_JOINED_NO_IP):
        client = _make_client()
        run(client.pr.setup())
        _script_status(client, [state])
        lines = _poll_printing(client)
        log = run(client.get_error_counter())
        assert _used_slots(log) == [code("W", "WLAN_NO_VERDICT")] and log["WIFI"]["ErrCount"] == 1, (state, log)
        assert ("WIFI", "WLAN connect attempt ended without a verdict, last status:", state) in lines, (state, lines)


def test_a_poll_ending_in_a_verdict_persists_no_no_verdict_warning() -> None:
    for state in (network.STAT_GOT_IP, network.STAT_WRONG_PASSWORD, network.STAT_NO_AP_FOUND, network.STAT_CONNECT_FAIL, 12345):
        client = _make_client()
        run(client.pr.setup())
        _script_status(client, [network.STAT_CONNECTING, state])
        _poll_printing(client)
        assert code("W", "WLAN_NO_VERDICT") not in _used_slots(run(client.get_error_counter())), state


def test_poll_sta_connect_status_returns_after_one_status_call_on_got_ip() -> None:
    # A successful connect costs one poll step, not the whole window.
    client = _make_client()
    calls = _script_status(client, [network.STAT_GOT_IP])
    fast = FastAsyncSleep()

    async def scenario() -> "list[float]":
        await client._poll_sta_connect_status()
        return fast.of(asyncio.current_task())

    with fast:
        assert run(scenario()) == []
    assert calls == [()]


def test_a_poll_without_a_verdict_steps_in_milliseconds_for_its_whole_bound() -> None:
    client = _make_client()
    run(client.pr.setup())
    calls = _script_status(client, [network.STAT_CONNECTING])
    fast = FastAsyncSleep()

    async def scenario() -> "list[int]":
        await client._poll_sta_connect_status()
        return fast.ms_of(asyncio.current_task())

    with fast:
        assert run(scenario()) == [_STA_CONNECT_POLL_MS] * _STA_CONNECT_POLL_ITERS
    assert len(calls) == _STA_CONNECT_POLL_ITERS


# ---------------------------------------------------------------------------
# _start_hotspot() success branch - only the missing-config (CFG_READ) branch was exercised above;
# a healthy config must actually reach set_wifi_led()/_activate_hotspot_ap().
# ---------------------------------------------------------------------------


def test_start_hotspot_valid_config_activates_the_ap() -> None:
    client = _make_client()

    async def fake_select(_mode: int) -> None:
        return None  # skips the real mode-switch dance (and its real asyncio.sleep()s) entirely

    client._select_wifi_mode = fake_select  # type: ignore[assignment, method-assign]  # mocked by reassignment

    async def scenario() -> None:
        await client._start_hotspot()
        assert client._dns_server_task is not None
        await cancel(client._dns_server_task)

    run(scenario())
    assert client._hotspot_started_once is True
    assert client._hw_op_failed is False
    assert {"essid": "SensorNode", "password": "12345678"} in _wlan(client).config_calls


def test_start_hotspot_uses_the_configured_hotspot_password_not_the_default() -> None:
    # HotspotPW is per-device configurable (SPECIFICATION.md Part C.14) - proves a genuinely
    # non-default value written through cfgmgr actually reaches wlan.config(), not just that the
    # schema default happens to match every other test's hardcoded "12345678" expectation.
    client = _make_client()
    ok, results = run(client.cfgmgr.write_config({"HotspotPW": "customhotspotpw1"}))
    assert ok is True
    assert results["HotspotPW"] == "Valid"

    async def fake_select(_mode: int) -> None:
        return None

    client._select_wifi_mode = fake_select  # type: ignore[assignment, method-assign]  # mocked by reassignment

    async def scenario() -> None:
        await client._start_hotspot()
        assert client._dns_server_task is not None
        await cancel(client._dns_server_task)

    run(scenario())
    assert client._hw_op_failed is False
    assert {"essid": "SensorNode", "password": "customhotspotpw1"} in _wlan(client).config_calls


# ---------------------------------------------------------------------------
# _run_hotspot_mode() brings the selected AP up again on a tick without a link; doing so never leaks a
# second DNS server task. An active AP reports STAT_GOT_IP (cyw43_lwip.c), as tests/network.py's fake does; a
# tick without that link is the repeated call these drive by calling _start_hotspot() twice directly.
# ---------------------------------------------------------------------------


def test_start_hotspot_does_not_leak_a_dns_server_task_when_called_again_while_already_running() -> None:
    client = _make_client()

    async def fake_select(_mode: int) -> None:
        return None

    client._select_wifi_mode = fake_select  # type: ignore[assignment, method-assign]  # mocked by reassignment

    async def scenario() -> None:
        # Mirrors _run_hotspot_mode() calling _start_hotspot() again on a later loop iteration
        # while wlan.status() still isn't STAT_GOT_IP - the real, reachable repeated-call shape.
        await client._start_hotspot()
        first_task = client._dns_server_task
        assert first_task is not None
        await client._start_hotspot()
        second_task = client._dns_server_task
        try:
            assert second_task is first_task  # no new task created while the first is still running
            assert not first_task.done()  # and the original task was never cancelled out from under it
        finally:
            await cancel(first_task)

    run(scenario())


def test_start_hotspot_starts_a_fresh_dns_server_task_if_the_previous_one_already_finished() -> None:
    # The other half of the guard: a *finished* task (real crash/cancellation) must not block a
    # legitimate restart, matching asy_system_service.py's own supervisor's (supervise_tasks()) `is None or
    # .done()` convention.
    client = _make_client()

    async def fake_select(_mode: int) -> None:
        return None

    client._select_wifi_mode = fake_select  # type: ignore[assignment, method-assign]  # mocked by reassignment

    async def scenario() -> None:
        await client._start_hotspot()
        first_task = client._dns_server_task
        assert first_task is not None
        await cancel(first_task)
        assert first_task.done()
        await client._start_hotspot()
        second_task = client._dns_server_task
        assert second_task is not None
        assert second_task is not first_task
        await cancel(second_task)

    run(scenario())


# ---------------------------------------------------------------------------
# Radio reconfiguration idempotency (real bench hardware investigation): a genuine re-entry while
# the AP interface is still active must not reapply essid/password/active(True), or the real CYW43
# firmware can interrupt its beacon - unlike the DNS-task guard above, a pure resource-leak concern.
# ---------------------------------------------------------------------------


def test_configure_hotspot_ap_does_not_reapply_essid_password_when_already_active() -> None:
    client = _make_client()
    run(client.pr.setup())

    async def scenario() -> None:
        essid_call: dict[str, object] = {"essid": "MyHost", "password": "12345678"}
        client._configure_hotspot_ap("US", "MyHost", "12345678")
        first_task = client._dns_server_task
        assert first_task is not None
        assert _wlan(client)._active is True
        assert _wlan(client).config_calls.count(essid_call) == 1
        client._configure_hotspot_ap("US", "MyHost", "12345678")  # a real re-entry while still active
        assert _wlan(client).config_calls.count(essid_call) == 1  # not reapplied a second time
        assert client._dns_server_task is first_task  # unaffected - the DNS-task guard is independent
        await cancel(first_task)

    run(scenario())


def test_configure_hotspot_ap_reconfigures_after_the_interface_was_externally_deactivated() -> None:
    client = _make_client()
    run(client.pr.setup())

    async def scenario() -> None:
        essid_call: dict[str, object] = {"essid": "MyHost", "password": "12345678"}
        client._configure_hotspot_ap("US", "MyHost", "12345678")
        first_task = client._dns_server_task
        assert first_task is not None
        assert _wlan(client).config_calls.count(essid_call) == 1
        _wlan(client).active(False)  # simulates a real external deactivation, not a normal steady-state tick
        client._configure_hotspot_ap("US", "MyHost", "12345678")
        assert _wlan(client).config_calls.count(essid_call) == 2  # self-healed: reconfigured, not silently skipped
        assert _wlan(client)._active is True
        second_task = client._dns_server_task
        assert second_task is not None
        await cancel(first_task)
        if second_task is not first_task:
            await cancel(second_task)

    run(scenario())



def test_an_over_long_hotspot_password_falls_back_instead_of_invalidating_the_config() -> None:
    # The upper bound is the rung that matters most: an unsatisfiable default makes ConfigManager
    # answer None to every read, costing the device its whole networking config. buildgen refuses
    # such a value at build time; this is the backstop that keeps a device that got one bootable.
    client = WifiService(WifiConfig("SensorNode", "p" * 64, 5, 5), cfg_path=_tmp_cfg_dir())
    run(client.cfgmgr.setup())
    assert run(client.cfgmgr.get_dict(["HotspotPW"])) == {"HotspotPW": "12345678"}


def test_a_persisted_rename_survives_a_later_build_injecting_a_different_default() -> None:
    # The reason these arrive as defaults rather than fixed values: a device renamed through the web
    # UI must keep that name across a reflash whose TOML says something else. Two constructions over
    # one config directory is exactly what that reflash looks like from the config file's side.
    cfg_path = _tmp_cfg_dir()
    first = WifiService(WifiConfig("SensorStationTest", "12345678", 5, 5), cfg_path=cfg_path)

    async def rename() -> "WriteValidity":
        await first.cfgmgr.setup()
        results = await first._set_dict_cfg({"Hostname": "KitchenPi"}, first.get_cfg_schema())
        await first.cfgmgr.flush_pending()  # the real file write is an independent task, never inline
        return results

    assert run(rename()) == {"Hostname": "Valid"}
    second = WifiService(WifiConfig("SensorStationOther", "12345678", 5, 5), cfg_path=cfg_path)
    run(second.cfgmgr.setup())
    assert run(second.cfgmgr.get_dict(["Hostname"])) == {"Hostname": "KitchenPi"}


def test_a_default_is_only_substituted_into_a_bounded_string_field() -> None:
    # The bounds check is what keeps an unusable default out of the config, and it can only read the
    # length of a str. Any other field shape therefore keeps its own default rather than taking an
    # unchecked one - the two fields buildgen injects are both bounded strings.
    schema: cm.ConfigSchema = (("LEDWifiOn", "bool", True, None, None, None),)
    assert asy_wifi_service._with_default(schema, "yes") is schema  # type: ignore[arg-type]  # the schema with no string field under test


# ---------------------------------------------------------------------------
# SPECIFICATION.md C.7.4: the radio bounds SSID/PW/Country/Hostname/HotspotPW in UTF-8 BYTES, where
# the schema counts characters, and Hostname/Country by shape - refused at write, and a stored one
# runs on its default, never reaching the radio as a "hardware" failure that feeds the give-up streak.
# ---------------------------------------------------------------------------

# (field, largest accepted, smallest refused) - each pair within the schema's character bound.
# No Hostname row: a host label is ASCII, so its byte bound equals its character bound.
_BYTE_BOUNDS = (
    ("SSID", "ä" * 16, "ä" * 16 + "x"),  # 32 bytes / 33 bytes, both <= 32 characters
    ("PW", "ä" * 31 + "x", "ä" * 32),  # 63 / 64 bytes
    ("Country", "AT", "ÄT"),  # 2 / 3 bytes, both 2 characters
    ("HotspotPW", "ä" * 31 + "x", "ä" * 32),
)


def test_each_radio_field_refuses_one_byte_over_its_bound_and_accepts_the_bound() -> None:
    for field, fits, too_long in _BYTE_BOUNDS:
        client = _make_client()
        run(client.pr.setup())
        before = run(client.cfgmgr.get_dict([field]))
        assert run(client._set_dict_cfg({field: too_long}, client.get_cfg_schema())) == {field: "Invalid"}, field
        run(client.cfgmgr.flush_pending())
        assert run(client.cfgmgr.get_dict([field])) == before, field  # nothing stored
        assert _last_err(run(client.get_error_counter()), "ErrNum") == code("E", "BAD_ARG"), field
        assert run(client._set_dict_cfg({field: fits}, client.get_cfg_schema())) == {field: "Valid"}, field
        run(client.cfgmgr.flush_pending())
        assert run(client.cfgmgr.get_dict([field])) == {field: fits}, field


def test_radio_bytes_ok_passes_through_everything_the_schema_check_owns() -> None:
    field = ("Hostname", "str", "SensorNode", 1, 32, None)
    ok = asy_wifi_service._radio_value_ok
    assert ok(field, 12) is True  # not a str: the schema's type check refuses it
    assert ok(field, "") is True  # under the character min: the schema's refusal, not a byte one
    assert ok(field, "x" * 40) is True  # over the character max: likewise
    assert ok(("PW", "str", "", 8, 63, ""), "") is True  # the special bypass value
    assert ok(("X", "str", None, None, None, None), "ä" * 99) is True  # no int bounds to apply
    ssid = ("SSID", "str", "", 0, 32, None)  # no shape of its own, so only the byte bound applies
    assert ok(ssid, "ä" * 16) is True  # exactly 32 bytes
    assert ok(ssid, "ä" * 17) is False  # 34 bytes inside 17 characters
    assert ok(field, "ä" * 17) is False


def test_an_unknown_key_beside_a_refused_radio_field_is_still_the_schemas_to_judge() -> None:
    client = _make_client()
    results = run(client._set_dict_cfg({"Hostname": "ä" * 17, "Nope": "x"}, client.get_cfg_schema()))
    assert results == {"Hostname": "Invalid", "Nope": "Invalid"}


def test_a_refused_radio_field_leaves_the_rest_of_the_request_applied() -> None:
    client = _make_client()
    results = run(client._set_dict_cfg({"Hostname": "ä" * 17, "SSID": "HomeNet", "LEDWifiOn": False}, client.get_cfg_schema()))
    assert results == {"Hostname": "Invalid", "SSID": "Valid", "LEDWifiOn": "Valid"}
    run(client.cfgmgr.flush_pending())
    assert run(client.cfgmgr.get_dict(["SSID", "LEDWifiOn"])) == {"SSID": "HomeNet", "LEDWifiOn": False}


def test_the_open_network_password_bypass_still_passes_the_byte_check() -> None:
    client = _make_client()
    run(client._set_dict_cfg({"PW": "x" * 8}, client.get_cfg_schema()))
    assert run(client._set_dict_cfg({"PW": ""}, client.get_cfg_schema())) == {"PW": "Valid"}


def test_a_character_bound_violation_is_still_the_schemas_refusal_not_a_byte_one() -> None:
    client = _make_client()
    run(client.pr.setup())
    assert run(client._set_dict_cfg({"Country": "D"}, client.get_cfg_schema())) == {"Country": "Invalid"}
    assert code("E", "BAD_ARG") not in run(client.get_error_counter())["WIFI"]["ErrNum"]


def _client_with_stored(values: "dict[str, str]", conn_fail_to_hotspot: int = 5) -> WifiService:
    # A value the radio refuses, already on flash - stored before C.7.4 or hand-edited.
    stored = {"SSID": "HomeNet", "PW": "secret123", "Country": "DE", "Hostname": "SensorNode", "LEDWifiOn": True, "HotspotPW": "12345678"}
    stored.update(values)
    return _make_client_with_json(json.dumps(stored), conn_fail_to_hotspot=conn_fail_to_hotspot)


def _no_poll(client: WifiService) -> None:
    async def skip() -> None:
        return None

    client._poll_sta_connect_status = skip  # type: ignore[method-assign]  # connect's outcome is not under test


def test_a_stored_over_long_country_connects_on_the_default_not_a_hardware_failure() -> None:
    client = _client_with_stored({"Country": "ÄT"})
    run(client.pr.setup())
    _no_poll(client)
    assert network.country() == "XX"  # the radio's power-on seed: only the product's own call can make it "DE"
    for _ in range(3):
        client._hw_op_failed = False
        run(client._attempt_sta_connect())
        assert client._hw_op_failed is False
    assert network.country() == "DE"
    assert len(_wlan(client).connect_calls) == 3
    log = run(client.get_error_counter())["WIFI"]
    assert log["ErrNum"][-1] == code("W", "STORED_DEFAULT") and log["ErrType"][-1] == "W"
    assert log["ErrCount"] == 3  # counted every attempt, one ring slot (the central rule)
    assert log["ErrNum"].count(code("W", "STORED_DEFAULT")) == 1
    assert run(client.get_dict_cfg())["WIFI"]["Country"] == "DE"  # GET shows the default in use


def test_two_over_bound_stored_fields_count_each_and_keep_one_slot() -> None:
    client = _client_with_stored({"Country": "ÄT", "Hostname": "ä" * 17})
    run(client.pr.setup())
    _no_poll(client)
    run(client._attempt_sta_connect())
    log = run(client.get_error_counter())
    assert _used_slots(log) == [code("W", "STORED_DEFAULT")]
    assert log["WIFI"]["ErrCount"] == 2
    shown = run(client.get_dict_cfg())["WIFI"]
    assert (shown["Country"], shown["Hostname"]) == ("DE", "SensorNode")  # GET shows the defaults in use


def test_two_refused_radio_puts_count_each_and_keep_one_slot() -> None:
    client = _make_client()
    run(client.pr.setup())
    for value in ("ä" * 17, "ä" * 18):
        assert run(client._set_dict_cfg({"Hostname": value}, client.get_cfg_schema())) == {"Hostname": "Invalid"}
    log = run(client.get_error_counter())
    assert _used_slots(log) == [code("E", "BAD_ARG")]
    assert log["WIFI"]["ErrCount"] == 2


def test_a_stored_over_long_ssid_and_password_never_reach_connect() -> None:
    client = _client_with_stored({"SSID": "ä" * 16 + "x", "PW": "ä" * 32})
    run(client.pr.setup())
    _no_poll(client)
    run(client._attempt_sta_connect())  # the fake raises if either reached connect() over its bound
    assert client._hw_op_failed is False
    assert _wlan(client).connect_calls == []  # the SSID fell back to its "" default: straight to hotspot
    assert (client._conn_phase, client._connection_failures) == (_PHASE_HOTSPOT, 0)
    shown = run(client.get_dict_cfg())["WIFI"]
    assert (shown["SSID"], shown["PW"]) == ("", "********")  # GET shows the SSID in use; the password stays masked


def test_a_stored_over_long_hostname_falls_back_to_the_devices_own_default() -> None:
    # The fallback is the LIVE schema's default, i.e. buildgen's per-device hostname, not "SensorNode".
    cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_WIFI.cfg", "w") as f:
        f.write('{"SSID": "HomeNet", "PW": "secret123", "Country": "DE", "Hostname": "' + "ä" * 17 + '", "LEDWifiOn": true, "HotspotPW": "12345678"}')
    client = WifiService(WifiConfig("SensorStationTest", "12345678", 5, 5), cfg_path=cfg_path)
    run(client.cfgmgr.setup())
    run(client.pr.setup())
    _no_poll(client)
    assert network.hostname() == "PicoW"  # the radio's power-on seed: only the product's own call can change it
    run(client._attempt_sta_connect())
    assert network.hostname() == "SensorStationTest"
    assert client._hw_op_failed is False
    assert run(client.get_dict_cfg())["WIFI"]["Hostname"] == "SensorStationTest"  # the live default, as in use


def test_a_stored_over_long_hotspot_value_starts_the_hotspot_on_the_default() -> None:
    client = _client_with_stored({"Country": "ÄT", "Hostname": "ä" * 17})
    run(client.pr.setup())

    async def fake_select(_mode: int) -> None:
        return None

    client._select_wifi_mode = fake_select  # type: ignore[assignment, method-assign]  # mocked by reassignment
    assert (network.country(), network.hostname()) == ("XX", "PicoW")  # the power-on seeds, so the check can fail
    run(client._start_hotspot())
    assert client._hw_op_failed is False
    assert (network.country(), network.hostname()) == ("DE", "SensorNode")
    shown = run(client.get_dict_cfg())["WIFI"]
    assert (shown["Country"], shown["Hostname"]) == ("DE", "SensorNode")


def _radio_shape_cases() -> "dict[str, dict[str, list[str]]]":
    # One corpus, three judges: this product check, buildgen's and the mock's (SPECIFICATION.md G.2).
    with open("tests/_radio_shape_cases.json") as f:
        cases: dict[str, dict[str, list[str]]] = json.load(f)
    return cases


def _judge_shape_case(field: str, value: str, *, accepted: bool) -> None:
    network.reset_test_state()  # type: ignore[attr-defined]  # the fake's own after-each reset: each corpus case meets a power-on radio
    client = _make_client()
    client.pr.set_level(2)  # errors and warnings reach print(), so the refusal's text is checked too
    run(client.pr.setup())
    before = run(client.cfgmgr.get_dict([field]))
    with record_prints() as recorder:
        result = run(client._set_dict_cfg({field: value}, client.get_cfg_schema()))
    run(client.cfgmgr.flush_pending())
    if accepted:
        assert result[field] in ("Valid", "Unchanged"), (field, value, result)  # "Unchanged": equals the default
        assert run(client.cfgmgr.get_dict([field])) == {field: value}, (field, value)
        return
    assert result == {field: "Invalid"}, (field, value)
    assert run(client.cfgmgr.get_dict([field])) == before, (field, value)  # nothing stored
    low, high = next((f[3], f[4]) for f in client.get_cfg_schema() if f[0] == field)
    assert isinstance(low, int) and isinstance(high, int), field
    if not low <= len(value) <= high:
        return  # the schema's own character-bound refusal, not the radio check's (tested above)
    assert recorder.lines == [("WIFI", "Refusing", field, "- outside the radio's accepted form")], (field, value)
    stored = _client_with_stored({field: value})
    run(stored.pr.setup())
    _no_poll(stored)
    assert (network.hostname(), network.country()) == ("PicoW", "XX")  # the power-on seeds, so the check can fail
    run(stored._attempt_sta_connect())
    default = next(f[2] for f in stored.get_cfg_schema() if f[0] == field)
    assert (network.hostname() if field == "Hostname" else network.country()) == default, (field, value)
    log = run(stored.get_error_counter())["WIFI"]
    assert _used_slots(run(stored.get_error_counter())) == [code("W", "STORED_DEFAULT")] and log["ErrCount"] == 1, (field, value)
    assert run(stored.get_dict_cfg())["WIFI"][field] == default, (field, value)  # GET shows the value in use


# The corpus keys this file judges and the field each goes through; with the other judge files' they name every key
# of tests/_radio_shape_cases.json (tests_scripts/test_radio_shape_corpus.py).
_JUDGED_SHAPES = (("hostLabel", "Hostname"), ("countryCode", "Country"))


def test_every_host_label_and_country_case_is_judged_as_the_corpus_says() -> None:
    cases = _radio_shape_cases()
    for shape, field in _JUDGED_SHAPES:
        assert cases[shape]["accept"] and cases[shape]["reject"], shape
        for value in cases[shape]["accept"]:
            _judge_shape_case(field, value, accepted=True)
        for value in cases[shape]["reject"]:
            _judge_shape_case(field, value, accepted=False)


def test_wlan_connect_never_gives_up_over_a_stored_radio_value() -> None:
    # Regression: an over-long Country used to raise on every attempt, set _hw_op_failed, and end the
    # task after max_module_error cycles (the give-up) - a supervisor restart per few cycles, then a reboot.
    client = _client_with_stored({"Country": "ÄT"}, conn_fail_to_hotspot=1000)  # stays on the STA path
    _no_poll(client)
    attempts = [0]
    real_attempt = client._attempt_sta_connect

    async def counted_attempt() -> None:
        attempts[0] += 1
        await real_attempt()

    async def no_mode_switch() -> None:
        client._reconn_wifi = False  # the real one's mode switch sleeps its three settle waits; not under test here

    client._attempt_sta_connect = counted_attempt  # type: ignore[method-assign]
    client._handle_reconnect_trigger = no_mode_switch  # type: ignore[method-assign]

    async def scenario() -> bool:
        task = asyncio.create_task(client._connect_loop())
        for _ in range(400):
            await asyncio.sleep(0)
        still_running = not task.done()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return still_running

    with FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario()) is True
    assert attempts[0] > 3 * client._max_module_error  # far past the old give-up streak
    kept = _used_slots(run(client.get_error_counter()))
    assert code("E", "GIVE_UP") not in kept and code("E", "WLAN_GIVE_UP") not in kept


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
