import asyncio
import json
import os
import select
import socket
import sys

sys.path.insert(0, "digital_twin/unixport")  # the Unix-port UDP address shim (SPECIFICATION.md F.7 row 1)

import network
from _error_codes import code
from _tmp_scratch import TmpScratch
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from machine import Timer

import asy_base_classes
import asy_print_log as print_log_module
import asy_wifi_service
from asy_print_log import LogConfig
from asy_udp_socket import UDPSocket
from asy_wifi_service import WIFI, WifiConfig, WifiService

# UDPSocket takes plain (host, port) tuples; on this Unix build the shim resolves them (once, class-wide).
patch_asy_udp_socket_for_unix_port()

_WIFI = "src/asy_wifi_service.py"


def _src_const(name: str) -> str:
    # A shipped const()'s literal, read from the source: a const() is not a module attribute on MicroPython.
    with open(_WIFI) as f:
        for line in f:
            if line.startswith(name + " = const("):
                literal: str = line.split("const(", 1)[1].split(")", 1)[0]
                return literal
    raise AssertionError(name + " not found in " + _WIFI)


def _src_pattern(name: str) -> "tuple[float, float]":
    # One LED pattern's (on, off) seconds: _src_pattern("HOTSPOT") reads _LED_HOTSPOT_ON_S and _LED_HOTSPOT_OFF_S.
    return float(_src_const("_LED_" + name + "_ON_S")), float(_src_const("_LED_" + name + "_OFF_S"))


_PHASE_STA_SEEKING = int(_src_const("_PHASE_STA_SEEKING"))
_PHASE_STA_ESTABLISHED = int(_src_const("_PHASE_STA_ESTABLISHED"))
_PHASE_HOTSPOT = int(_src_const("_PHASE_HOTSPOT"))
_PHASE_DEACTIVATED = int(_src_const("_PHASE_DEACTIVATED"))

# asy_wifi_service.py's own _VAL_SSID/_VAL_PW/_VAL_COUNTRY/_VAL_HOSTNAME/_VAL_LED_WIFI_ON schema tuples - not
# importable once const()-folded, so mirrored here; test_cfg_schema_matches_what_cfgmgr_was_built_with keeps them in sync.
_VAL_SSID = (("SSID", "str", "", 0, 32, None),)
_VAL_PW = (("PW", "str", "", 8, 63, ""),)
_VAL_COUNTRY = (("Country", "str", "DE", 2, 2, None),)
_VAL_HOSTNAME = (("Hostname", "str", "SensorNode", 1, 32, None),)
_VAL_LED_WIFI_ON = (("LEDWifiOn", "bool", True, None, None, None),)
_VAL_HOTSPOT_PW = (("HotspotPW", "str", "12345678", 8, 63, None),)

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
    from collections.abc import Callable, Coroutine
    from typing import Any, Literal, TypeVar

    from typing_extensions import Self

    from asy_base_classes import PushFct
    from asy_config_manager import CfgValue, WriteValidity
    from asy_print_log import ErrorLog

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


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


def _wlan(client: WifiService) -> "Any":
    # _wlan(client) is typed against the real network.WLAN stub (pyproject.toml's tests/network.py
    # exclude is deliberate), but at runtime MICROPYPATH constructs tests/network.py's fake with its
    # test-only attributes. Narrows to Any once here, so no test below needs a `# type: ignore`.
    return client._wlan


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("wifi")


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


class FakeLED:
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

    def on(self) -> None:
        exc = self.raise_on.get("on")
        if exc is not None:
            raise exc
        self.on_calls += 1
        self.state = True

    def off(self) -> None:
        exc = self.raise_on.get("off")
        if exc is not None:
            raise exc
        self.off_calls += 1
        self.state = False

    def toggle(self) -> None:
        exc = self.raise_on.get("toggle")
        if exc is not None:
            raise exc
        self.toggle_calls += 1
        self.state = not self.state


class _RaiseOnArm:
    # Same technique as test_asy_ntp_client.py's _RaiseOnArm - toggles tests/machine.py's shared
    # Timer.raise_on_arm for the `with` block, simulating rp2 alarm-pool exhaustion. `exc` picks
    # which arm of `except (OSError, MemoryError)` runs; neither covers the other (Part F).
    def __init__(self, exc: "type[BaseException]" = OSError) -> None:
        self._exc = exc

    def __enter__(self) -> "Self":
        Timer.raise_on_arm_exc = self._exc
        Timer.raise_on_arm = True
        return self

    def __exit__(self, *exc_info: object) -> None:
        Timer.raise_on_arm = False
        Timer.raise_on_arm_exc = OSError


def make_client(
    conn_fail_to_hotspot: int = 5,
    ext_led: "FakeLED | None" = None,
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


def make_client_with_json(  # parameters/defaults mirror make_client() above, minus its cfg_path
    json_text: str,
    conn_fail_to_hotspot: int = 5,
    ext_led: "FakeLED | None" = None,
    hotspot_time_min: int = 5,
    max_module_error: int = 5,
    debug: "int | None" = None,
) -> WifiService:
    cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_WIFI.cfg", "w") as f:
        f.write(json_text)
    return make_client(
        conn_fail_to_hotspot=conn_fail_to_hotspot,
        ext_led=ext_led,
        hotspot_time_min=hotspot_time_min,
        max_module_error=max_module_error,
        cfg_path=cfg_path,
        debug=debug,
    )


def make_invalid_cfg_client() -> WifiService:
    # A directory where ConfigManager expects a plain file - same technique as
    # test_asy_ntp_client.py's own make_invalid_cfg_client().
    cfg_path = _tmp_cfg_dir()
    os.mkdir(cfg_path + "config_WIFI.cfg")
    return make_client(cfg_path=cfg_path)


_VALID_JSON = (
    '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", '
    '"Hostname": "TestNode", "LEDWifiOn": false}'
)


async def _tick(flag: "asyncio.ThreadSafeFlag", times: int = 1) -> None:
    for _ in range(times):
        flag.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)  # parks: the woken loop runs one iteration; each caller's asserts check it ran


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


_SLEPT_CAP = 512


class _FastAsyncSleep:
    # Every asyncio.sleep() becomes one yield, its first _SLEPT_CAP calls recorded with their task (a test reads
    # one task's sleeps, never an earlier test's parked task's). asyncio.sleep is process-wide: restored on exit.
    def __init__(self) -> None:
        self.slept: list[tuple[object, float]] = []

    def __enter__(self) -> "Self":
        self._real_sleep = asyncio.sleep

        async def _fast(seconds: float) -> None:
            if len(self.slept) < _SLEPT_CAP:  # bounded: a loop spinning on fast sleeps must not grow it
                self.slept.append((asyncio.current_task(), seconds))
            await self._real_sleep(0)

        asyncio.sleep = _fast  # type: ignore[assignment]  # deliberate monkeypatch, not a real caller mismatch
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.sleep = self._real_sleep

    def of(self, task: object) -> "list[float]":
        # The seconds `task` asked to sleep, in order.
        return [seconds for owner, seconds in self.slept if owner is task]


class _DrivenTime:
    # A ticks source the test advances, installed as asy_base_classes' `time` for the block: the uptime
    # counts measured ticks (SPECIFICATION.md G.2), so it follows advance(), never the number of wake-ups.
    def __init__(self) -> None:
        self.now_ms = 0

    def __enter__(self) -> "Self":
        self._real = asy_base_classes.time
        asy_base_classes.time = self  # type: ignore[assignment]  # a module attribute swap, restored on exit
        return self

    def __exit__(self, *exc_info: object) -> None:
        asy_base_classes.time = self._real

    def advance(self, ms: int) -> None:
        self.now_ms += ms

    def ticks_ms(self) -> int:
        return self.now_ms

    def ticks_diff(self, new: int, old: int) -> int:
        return new - old

    def gmtime(self) -> "tuple[int, ...]":
        return self._real.gmtime()

    def mktime(self, t: "tuple[int, ...]") -> int:
        return self._real.mktime(t)


# ---------------------------------------------------------------------------
# __init__ / get_task_starters / get_timer_starters (SPECIFICATION.md Part C.9)
# ---------------------------------------------------------------------------


def test_init_creates_an_sta_mode_wlan_by_default() -> None:
    client = make_client()
    assert _wlan(client).if_id == network.STA_IF


def test_init_creates_its_own_config_file_with_schema_defaults() -> None:
    client = make_client()
    values = run(client.cfgmgr.get_dict(["SSID", "PW", "Country", "Hostname", "LEDWifiOn"]))
    assert values is not None
    assert values == {"SSID": "", "PW": "", "Country": "DE", "Hostname": "SensorNode", "LEDWifiOn": True}


def test_a_per_device_hostname_and_hotspot_password_replace_the_shared_defaults() -> None:
    # buildgen passes devices/*.toml's own [device].hostname/hotspot_password here. Before this
    # existed the two TOML fields were validated and then reached nothing, so every device booted
    # as "SensorNode" whatever its own file said.
    client = WifiService(WifiConfig("SensorStationWozi", "hunter2hunter2", 5, 5), cfg_path=_tmp_cfg_dir())
    run(client.cfgmgr.setup())
    values = run(client.cfgmgr.get_dict(["Hostname", "HotspotPW"]))
    assert values == {"Hostname": "SensorStationWozi", "HotspotPW": "hunter2hunter2"}


def test_an_injected_value_still_goes_through_the_schema_bounds() -> None:
    # Only the default moves - the validation rungs are the same ones a REST PUT hits, so a build
    # that injected a 3-character hotspot password must not produce a device the CYW43 cannot bring
    # up. It falls back to the schema's own default rather than accepting it.
    client = WifiService(WifiConfig("", "short", 5, 5), cfg_path=_tmp_cfg_dir())  # too short, which is the point of the test
    run(client.cfgmgr.setup())
    values = run(client.cfgmgr.get_dict(["Hostname", "HotspotPW"]))
    assert values == {"Hostname": "SensorNode", "HotspotPW": "12345678"}


def test_get_task_starters_returns_wlan_connect_uptime_counter_and_hotspot_watcher() -> None:
    client = make_client()
    starters = client.get_task_starters()
    assert starters == [client.start_asy_connect, client.start_asy_uptime, client.start_asy_hotspot_timeout]


def test_get_timer_starters_returns_the_counter_timer() -> None:
    client = make_client()
    assert client.get_timer_starters() == [client.start_uptime_timer]


def test_start_counter_timer_arms_periodic_1s() -> None:
    client = make_client()
    assert client._tick_armed is None  # not attempted yet: a test or tool that starts only the tasks
    client.start_uptime_timer()
    assert client._counter_timer.mode == Timer.PERIODIC
    assert client._counter_timer.period == 1000
    assert client._tick_armed is True


def test_start_counter_timer_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    client = make_client()
    with _RaiseOnArm():
        client.start_uptime_timer()  # must not raise despite the timer failing to arm
    assert client._counter_timer.period == -1  # never actually armed
    assert client._tick_armed is False  # recorded, so _connect_loop() retries it


def test_start_counter_timer_degrades_gracefully_on_a_memory_error() -> None:
    # Sibling of the OSError test above, for the other arm of start_uptime_timer()'s own
    # `except (OSError, MemoryError)`: a real alarm allocation can fail with MemoryError instead,
    # which is not an OSError subclass - same graceful degradation must hold either way.
    client = make_client()
    with _RaiseOnArm(MemoryError):
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
    client = make_client()
    run(client.pr.setup())
    with _RaiseOnArm():
        client.start_uptime_timer()
    _no_sta(client)

    async def scenario() -> "tuple[bool | None, bool | None]":
        task = asyncio.create_task(client._connect_loop())
        with _RaiseOnArm():
            for _ in range(4):  # one iteration: the re-arm fails again
                await asyncio.sleep(0)
        still_failing = client._tick_armed
        for _ in range(4):  # the next iteration: the pool has room again
            await asyncio.sleep(0)
        rearmed = client._tick_armed
        await _cancel(task)
        return still_failing, rearmed

    with _FastAsyncSleep():
        still_failing, rearmed = run(scenario())
    assert (still_failing, rearmed) == (False, True)
    assert client._counter_timer.period == 1000
    log = run(client.get_error_counter())
    assert code("E", "TIMER") in _used_slots(log)


def test_max_failed_rearms_end_the_loop() -> None:
    # A re-arm that keeps failing escalates: the streak ends the task, and the supervisor takes the next step.
    client = make_client(max_module_error=2)
    run(client.pr.setup())
    _no_sta(client)
    client._tick_armed = False

    async def scenario() -> bool:
        task = asyncio.create_task(client._connect_loop())
        with _RaiseOnArm():
            await asyncio.wait_for(task, _CONNECT_BOUND_S)
        return task.done()

    with _FastAsyncSleep():
        assert run(scenario()) is True
    kept = _used_slots(run(client.get_error_counter()))
    assert code("E", "TIMER") in kept and code("E", "WLAN_GIVE_UP") in kept, kept


def test_an_unreadable_status_keeps_the_link_state_and_uptime() -> None:
    # Unreadable is unknown, not down: the link state, the uptime and the published snapshot stand, and
    # one warning slot counts how many ticks were unreadable.
    with _DrivenTime() as clock:
        client = make_client()
        run(client.pr.setup())
        _wlan(client)._status = network.STAT_GOT_IP
        _wlan(client)._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "10.0.0.53")

        async def scenario() -> "tuple[int, WIFI, bool, int, WIFI, int]":
            task = asyncio.create_task(client._uptime_loop())
            await asyncio.sleep(0)
            for _ in range(3):
                clock.advance(1000)
                await _tick(client._time_counter_trigger_event)
            before = await client.get_data()
            _wlan(client).raise_on["status"] = OSError("simulated status failure")
            for _ in range(2):
                clock.advance(1000)
                await _tick(client._time_counter_trigger_event)
            during = (client._wifi_connected, await client.get_wifi_uptime(), await client.get_data())
            del _wlan(client).raise_on["status"]
            clock.advance(1000)
            await _tick(client._time_counter_trigger_event)
            after = await client.get_wifi_uptime()
            await _cancel(task)
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
    client = make_client(debug=3)
    assert client.pr.level == 3


# ---------------------------------------------------------------------------
# get_dict_cfg / get_error_counter - the base-class getter quartet (SPECIFICATION.md Part C.4.2)
# ---------------------------------------------------------------------------


def test_get_dict_cfg_masks_the_password() -> None:
    # the /networking GET masks PW (SPEC A.8), and HotspotPW the same way
    client = make_client_with_json(_VALID_JSON)
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
    client = make_client_with_json(_VALID_JSON)
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
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["SSID"] == ""
    assert values["PW"] == "supersecret"  # untouched


def test_config_ssid_too_long_falls_back_to_default_ssid_only() -> None:
    json_text = (
        '{"SSID": "' + ("x" * 33) + '", "PW": "supersecret", "Country": "US", '
        '"Hostname": "TestNode", "LEDWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["SSID"] == ""  # defaulted (max 32)
    assert values["PW"] == "supersecret"  # untouched


def test_config_pw_too_long_falls_back_to_default_pw_only() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "' + ("x" * 64) + '", "Country": "US", '
        '"Hostname": "TestNode", "LEDWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["PW"] == ""  # defaulted (max 63)
    assert values["SSID"] == "MyNetwork"  # untouched


def test_config_country_too_long_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "USA", '
        '"Hostname": "TestNode", "LEDWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["Country"] == "DE"


def test_config_country_too_short_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "U", '
        '"Hostname": "TestNode", "LEDWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["Country"] == "DE"


def test_config_country_wrong_type_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": 12345, '
        '"Hostname": "TestNode", "LEDWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["Country"] == "DE"


def test_config_hostname_empty_falls_back_to_default() -> None:
    json_text = '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", "Hostname": "", "LEDWifiOn": false}'
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["Hostname"] == "SensorNode"  # min 1


def test_config_hostname_too_long_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", '
        '"Hostname": "' + ("h" * 64) + '", "LEDWifiOn": false}'
    )
    client = make_client_with_json(json_text)
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
    client = make_client_with_json(json_text)
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
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["Hostname"] == name


def test_config_led_wifi_on_wrong_type_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", '
        '"Hostname": "TestNode", "LEDWifiOn": "true"}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["LEDWifiOn"] is True  # a JSON string isn't a real bool - defaulted


def test_config_multiple_invalid_fields_each_fall_back_independently() -> None:
    json_text = (
        '{"SSID": "' + ("x" * 33) + '", "PW": "supersecret", "Country": 12345, '
        '"Hostname": "TestNode", "LEDWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values["SSID"] == ""  # defaulted
    assert values["PW"] == "supersecret"  # untouched
    assert values["Country"] == "DE"  # defaulted
    assert values["Hostname"] == "TestNode"  # untouched
    assert values["LEDWifiOn"] is False  # untouched


def test_config_all_fields_invalid_falls_back_to_every_default() -> None:
    json_text = '{"SSID": null, "PW": 12345, "Country": "", "Hostname": null, "LEDWifiOn": "nope"}'
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values == _WIFI_DEFAULTS


def test_config_missing_file_uses_every_default() -> None:
    client = make_client()  # fresh directory - no config_WIFI.cfg written, so every default applies
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values == _WIFI_DEFAULTS


def test_config_non_dict_json_uses_every_default() -> None:
    client = make_client_with_json("[1, 2, 3]")
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values == _WIFI_DEFAULTS


def test_config_malformed_json_syntax_uses_every_default() -> None:
    client = make_client_with_json("{not json at all")
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values is not None
    assert values == _WIFI_DEFAULTS


def test_config_returns_none_when_config_manager_itself_is_invalid() -> None:
    client = make_invalid_cfg_client()
    assert client.cfgmgr.valid is False
    assert run(client.cfgmgr.get_dict(_WIFI_KEYS)) is None


def test_get_dict_cfg_returns_schema_defaults_wrapped_in_wifi_key() -> None:
    # PW comes back "********" even though the real cached default is "" - _cfg_overlay()'s masks are
    # unconditional (see test_get_dict_cfg_masks_the_password above).
    client = make_client()
    result = run(client.get_dict_cfg())
    expected = dict(_WIFI_DEFAULTS)
    expected["PW"] = "********"
    expected["HotspotPW"] = "********"
    assert result == {"WIFI": expected}


def test_get_dict_cfg_returns_all_none_values_when_config_manager_is_invalid() -> None:
    # PW is still "********", not None - _cfg_overlay()'s masks hold whether or not the underlying
    # ConfigManager is valid; with no values to read, nothing else is overlaid.
    client = make_invalid_cfg_client()
    result = run(client.get_dict_cfg())
    expected: dict[str, str | None] = dict.fromkeys(_WIFI_KEYS)
    expected["PW"] = "********"
    expected["HotspotPW"] = "********"
    assert result == {"WIFI": expected}


def test_get_error_counter_starts_empty_and_records_a_real_error() -> None:
    client = make_client()
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
    recorder = _PrintRecorder()
    try:
        call()
    finally:
        recorder.restore()
    return recorder.lines


def test_led_helpers_are_no_ops_when_no_led_selected() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)  # selected only once LEDWifiOn turns it on
    for helper in (client._led_on, client._led_off, client._led_toggle):
        assert _led_lines(client, helper) == []  # must not raise or report despite self._led being None
    assert (led.on_calls, led.off_calls, led.toggle_calls, client._led) == (0, 0, 0, None)


def test_set_wifi_led_true_selects_the_ext_led() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    assert client._led is led


def test_led_on_calls_the_selected_leds_on() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    client._led_on()
    assert led.on_calls == 1


def test_led_off_calls_the_selected_leds_off_and_does_not_recurse() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    client._led_off()
    assert led.off_calls == 1
    assert led.on_calls == 0


def test_led_toggle_calls_the_selected_leds_toggle() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    client._led_toggle()
    assert led.toggle_calls == 1


def test_set_wifi_led_false_turns_the_led_off_and_clears_it() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    run(client.set_wifi_led(status=False))
    assert led.off_calls == 1
    assert client._led is None


def test_each_led_helper_degrades_to_one_console_line_when_a_misbehaving_ext_led_raises() -> None:
    # self._led can be a caller-injected ext_led, not necessarily a real, never-raising Pin - a broken
    # implementation must not crash whatever caller touched the LED; one line reports it, and the next
    # call still reaches the LED.
    for method, text in (("on", "LED on() failed:"), ("off", "LED off() failed:"), ("toggle", "LED toggle() failed:")):
        led = FakeLED()
        client = make_client(ext_led=led)
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
    client = make_client(ext_led=FakeLED())
    assert run(client.set_wifi_led(status=True)) is True
    assert run(client.set_wifi_led(status=False)) is True


def test_a_cancelled_flash_leaves_the_led_as_the_canceller_sets_it() -> None:
    # The flash task has no cancel handler: a cancel ends it at its sleep, touching no LED, so the LED
    # stays as the canceller left it - here _reset_wlan_connect_state()'s off, never overridden later.
    led = FakeLED()
    client = make_client(ext_led=led)
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

    with _FastAsyncSleep():
        lit, final, cancelled = run(scenario())
    assert lit is True
    assert final is False
    assert cancelled is True


def test_a_raising_led_helper_ends_the_flash_task_with_one_unexpected_entry() -> None:
    # The flash task is unsupervised, so its top persists an unexpected end. The real _led_on() absorbs
    # the LED's own raise, so the top is reached through a replaced helper.
    client = make_client(ext_led=FakeLED())
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

    with _FastAsyncSleep():
        assert run(scenario()) is True
    log = run(client.get_error_counter())
    assert _used_slots(log) == [code("E", "UNEXPECTED")]
    assert log["WIFI"]["ErrCount"] == 1


# ---------------------------------------------------------------------------
# LED patterns: one flash task, created only through _run_led_pattern(); every pattern obeys LEDWifiOn
# (silent while it is off). The phases are read from the recorded sleeps, in seconds.
# ---------------------------------------------------------------------------


async def _drive(steps: int = 8) -> None:
    for _ in range(steps):  # parks: each one lets a fast-slept flash task run one phase
        await asyncio.sleep(0)


async def _stop_flash(client: WifiService) -> None:
    flash = client._ledflash
    assert flash is not None, "no flash task ran"
    await _cancel(flash)
    client._ledflash = None


def _lit_client(*, led_on: bool = True) -> "tuple[WifiService, FakeLED]":
    led = FakeLED()
    client = make_client(ext_led=led, hotspot_time_min=1)
    run(client.set_wifi_led(status=led_on))
    return client, led


def test_the_hotspot_pattern_is_on_2900_off_100() -> None:
    # Guard on the behaviour (unchanged); it failed first only on the renamed constants.
    client, led = _lit_client()
    fast = _FastAsyncSleep()

    async def scenario() -> "list[float]":
        await client._hotspot_client_absent()
        await _drive()
        phases = fast.of(client._ledflash)
        await _stop_flash(client)
        return phases

    with fast:
        phases = run(scenario())
    assert phases[:4] == list(_src_pattern("HOTSPOT")) * 2
    assert led.on_calls >= 2 and led.off_calls >= 1


def test_a_station_on_the_hotspot_runs_its_own_pattern() -> None:
    # A phone holding the AP shows an even slow blink, never a steady light that looks like a working home link.
    client, led = _lit_client()
    fast = _FastAsyncSleep()

    async def scenario() -> "list[float]":
        client._hotspot_client_connected()
        await _drive()
        phases = fast.of(client._ledflash)
        await _stop_flash(client)
        return phases

    with fast:
        phases = run(scenario())
    assert phases[:4] == list(_src_pattern("HOTSPOT_CLIENT")) * 2
    assert led.on_calls >= 2 and led.off_calls >= 1


def test_the_client_leaving_restores_the_hotspot_pattern() -> None:
    client, _led = _lit_client()
    fast = _FastAsyncSleep()

    async def scenario() -> "tuple[list[float], bool]":
        client._hotspot_client_connected()
        await _drive()
        client_flash = client._ledflash
        await client._hotspot_client_absent()
        await _drive()
        phases = fast.of(client._ledflash)
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

    with _FastAsyncSleep():
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

    with _FastAsyncSleep():
        assert run(scenario()) == (True, True)
    assert _used_slots(run(client.get_error_counter())) == [code("E", "UNEXPECTED")]


def test_the_client_pattern_with_the_wifi_led_off_stays_dark() -> None:
    client, led = _lit_client(led_on=False)

    async def scenario() -> None:
        client._hotspot_client_connected()
        await _drive()
        await _stop_flash(client)

    with _FastAsyncSleep():
        run(scenario())
    assert (led.on_calls, led.off_calls, led.toggle_calls) == (0, 0, 0)


def _deactivated_client(*, led_on: bool) -> "tuple[WifiService, FakeLED]":
    # LEDWifiOn as stored, the phase already deactivated (it survives the loop's restart reset).
    led = FakeLED()
    client = make_client_with_json('{"LEDWifiOn": ' + ("true" if led_on else "false") + "}", ext_led=led)
    client._conn_phase = _PHASE_DEACTIVATED
    return client, led


def test_deactivated_with_the_led_enabled_blinks_100_on_2900_off() -> None:
    client, led = _deactivated_client(led_on=True)
    fast = _FastAsyncSleep()

    async def scenario() -> "list[float]":
        task = asyncio.create_task(client._connect_loop())
        await _drive(12)
        phases = fast.of(client._ledflash)
        await _cancel(task)
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
        await _cancel(task)
        await _stop_flash(client)

    with _FastAsyncSleep():
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
        await _cancel(task)
        await _stop_flash(client)
        return dark, results

    with _FastAsyncSleep():
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
        await _cancel(task)
        await _stop_flash(client)
        return results, after

    with _FastAsyncSleep():
        results, after = run(scenario())
    assert results == {"LEDWifiOn": "Valid"}
    assert led.state is False  # the setter's own off
    assert (led.on_calls, led.off_calls, led.toggle_calls) == after, "the pattern kept lighting a disabled LED"


# ---------------------------------------------------------------------------
# _push_wifi_led / self._push_callbacks - the generic setter dispatch's per-field live-push
# registration (asy_base_classes.py's _set_dict_cfg), registered once at construction (project
# decision), not passed per-call.
# ---------------------------------------------------------------------------


def test_push_wifi_led_reports_success_for_a_well_typed_no_op() -> None:
    # A push whose value type checks out reports success even when the setter changes nothing.
    client = make_client(ext_led=FakeLED())
    assert run(client._push_wifi_led(False)) is True  # the LED is already off
    assert run(client._push_wifi_led(False)) is True
    assert run(client._push_wifi_led(True)) is True
    assert run(client._push_wifi_led(True)) is True  # already on


def test_led_wifi_on_push_callback_is_registered_at_construction() -> None:
    client = make_client(ext_led=FakeLED())
    assert "LEDWifiOn" in client._push_callbacks


def test_push_callbacks_registered_for_led_wifi_on_only() -> None:
    # Exhaustive, not just "LEDWifiOn is present": SSID/PW/Country/Hostname are persist-only and
    # must have no push entry; the external LED arrives at construction, never through a setter.
    client = make_client(ext_led=FakeLED())
    assert set(client._push_callbacks) == {"LEDWifiOn"}


def test_led_wifi_on_push_callback_applies_the_value_through_set_wifi_led() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    callback = client._push_callbacks["LEDWifiOn"]
    assert run(_push(callback, True)) is True
    assert client._led is led


def test_led_wifi_on_push_narrowing_arm_returns_false_for_a_non_bool() -> None:
    # _set_dict_cfg only ever invokes a push callback with an already schema-validated value (real
    # bool, by construction) - this guards the type for the checker and as defense-in-depth, not
    # because a real caller can reach it with the wrong type.
    client = make_client(ext_led=FakeLED())
    callback = client._push_callbacks["LEDWifiOn"]
    assert run(_push(callback, "not a bool")) is False
    assert run(_push(callback, 1)) is False


def test_set_dict_cfg_led_wifi_on_end_to_end_persists_and_pushes() -> None:
    # Full integration: the generic dispatch persists LEDWifiOn to config_WIFI.cfg *and* pushes it
    # live through set_wifi_led, in one call - exactly the shape a future REST endpoint will use.
    led = FakeLED()
    client = make_client(ext_led=led)
    results = run(client._set_dict_cfg({"LEDWifiOn": False}, client.get_cfg_schema()))
    assert results == {"LEDWifiOn": "Valid"}
    assert client._led is None  # pushed: turned off and cleared
    assert run(client.cfgmgr.get_dict(["LEDWifiOn"])) == {"LEDWifiOn": False}  # persisted too


def test_set_dict_cfg_multiple_invalid_fields_reported_independently() -> None:
    # Mirrors asy_ntp_client.py's own multi-invalid _set_dict_cfg coverage - this driver had no
    # multi-field _set_dict_cfg test beyond the single-field LEDWifiOn one above, despite four
    # persist-only string fields each with their own min/max/special validation.
    led = FakeLED()
    client = make_client(ext_led=led)
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
    client = make_client_with_json(
        '{"SSID": "MyNetwork", "PW": "", "Country": "US", "Hostname": "TestNode", "LEDWifiOn": false}',
    )
    values = run(client.cfgmgr.get_dict(["PW"]))
    assert values == {"PW": ""}


def test_pw_below_wpa2_minimum_length_falls_back_to_default() -> None:
    # 7 characters - one short of WPA2-PSK's real 8-character minimum - is neither the empty-string
    # special case nor a valid in-range password, so it's rejected like any other out-of-range value.
    json_text = '{"SSID": "MyNetwork", "PW": "short12", "Country": "US", "Hostname": "TestNode", "LEDWifiOn": false}'
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(["PW"]))
    assert values == {"PW": ""}  # defaulted, not the too-short value


def test_pw_at_wpa2_minimum_length_is_accepted() -> None:
    json_text = '{"SSID": "MyNetwork", "PW": "exactly8", "Country": "US", "Hostname": "TestNode", "LEDWifiOn": false}'
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(["PW"]))
    assert values == {"PW": "exactly8"}


def test_write_config_pw_below_minimum_is_marked_invalid_not_silently_dropped() -> None:
    client = make_client()
    ok, results = run(client.cfgmgr.write_config({"PW": "short"}))
    assert ok is True
    assert results == {"PW": "Invalid"}
    assert run(client.cfgmgr.get_dict(["PW"])) == {"PW": ""}  # untouched default


def test_write_config_pw_empty_string_is_valid_and_resets_to_open_network() -> None:
    client = make_client_with_json(_VALID_JSON)  # starts with a real "supersecret" password
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
    client = make_client()

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
    client = make_client()

    async def scenario() -> None:
        task = asyncio.create_task(client._get_hotspot_stations())
        await asyncio.sleep(0)  # a park: the call takes the lock and reaches its settle sleep, checked below
        assert client.wifi_mode_lock.locked(), "the call did not take the lock, so this proves nothing"
        await _cancel(task)

    run(scenario())
    assert not client.wifi_mode_lock.locked(), "the wifi mode lock leaked on cancellation"


def test_handle_reconnect_trigger_cancels_a_running_ledflash_task() -> None:
    # The hotspot LED flasher is a real task; a reconnect that left it running would keep blinking
    # the hotspot pattern after the mode change, and leak the task for the rest of the uptime.
    client = make_client(hotspot_time_min=1)
    run(client._hotspot_client_absent())  # arms the shutoff timer and starts a real _ledflash task

    async def scenario() -> "asyncio.Task[Any]":
        await asyncio.sleep(0)  # a park: the flash task starts
        flash = client._ledflash
        assert flash is not None, "no _ledflash task to cancel, so this proves nothing"
        await client._handle_reconnect_trigger()
        await asyncio.sleep(0)  # a park: the cancelled task runs to its end; done() below checks it
        return flash

    with _FastAsyncSleep():  # the trigger's caller grace and settle waits
        flash = run(scenario())
    assert client._ledflash is None, "_handle_reconnect_trigger() left its _ledflash reference behind"
    # done(), not cancelled(): MicroPython's Task has no cancelled() at all (see typings/).
    assert flash.done(), "the _ledflash task was dropped rather than cancelled"


# ---------------------------------------------------------------------------
# get_data()/get_dict_data() - the cached-reading convention: backed by _uptime_loop()'s 1Hz push
# (_update_wifi_snapshot()), not a live lock-aware query - see get_data()'s own comment on why.
# ---------------------------------------------------------------------------


def test_get_data_reflects_the_initial_never_connected_state() -> None:
    client = make_client()
    assert run(client.get_data()) == WIFI(None, None, None, None, None, None, None, None)


def test_get_data_returns_the_cached_snapshot_not_a_live_query() -> None:
    client = make_client()
    snapshot = WIFI(Mode="STA", Connected=True, IP="10.0.0.5", Subnet="255.255.255.0", Gateway="10.0.0.1", DNS="10.0.0.53", RSSI=-61, TS=12345)
    run(client._set_meas_data(snapshot))
    assert run(client.get_data()) == snapshot


def test_get_dict_data_wraps_get_data_under_the_wifi_key() -> None:
    client = make_client()
    run(client._set_meas_data(WIFI(Mode="AP", Connected=False, IP=None, Subnet=None, Gateway=None, DNS=None, RSSI=None, TS=999)))
    dict_data = run(client.get_dict_data())
    assert dict_data == {"WIFI": {"Mode": "AP", "Connected": False, "IP": None, "Subnet": None, "Gateway": None, "DNS": None, "RSSI": None, "TS": 999}}


# ---------------------------------------------------------------------------
# _update_wifi_snapshot() - one 8-field WIFI tuple per _uptime_loop() tick, the radio read once; every
# networking getter answers from it, never from the radio (SPECIFICATION.md C.8)
# ---------------------------------------------------------------------------


def _record_calls(wlan: "Any", method: str) -> "list[tuple[object, ...]]":
    # Wraps one WLAN-fake method so a test sees every call the code made; tests/network.py records none.
    real = getattr(wlan, method)
    calls: list[tuple[object, ...]] = []

    def recorded(*args: object) -> object:
        calls.append(args)
        return real(*args)

    setattr(wlan, method, recorded)
    return calls


def test_update_wifi_snapshot_sta_mode_reports_the_four_addresses_and_the_rssi() -> None:
    client = make_client()
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
    client = make_client()
    with _FastAsyncSleep():
        run(client._switch_wlan_mode(network.AP_IF))
    client._conn_phase = _PHASE_HOTSPOT
    _wlan(client)._ifconfig = ("192.168.4.1", "255.255.255.0", "192.168.4.1", "0.0.0.0")
    status_calls = _record_calls(_wlan(client), "status")
    run(client._update_wifi_snapshot(connected=True))
    data = run(client.get_data())
    assert (data.Mode, data.Connected, data.IP, data.RSSI) == ("AP", True, "192.168.4.1", None)
    assert status_calls == []


def test_a_snapshot_without_a_link_has_no_rssi_and_no_dhcp_dns() -> None:
    client = make_client()
    _wlan(client)._ifconfig = ("0.0.0.0", "255.255.255.0", "0.0.0.0", "0.0.0.0")
    status_calls = _record_calls(_wlan(client), "status")
    run(client._update_wifi_snapshot(connected=False))
    data = run(client.get_data())
    assert (data.Mode, data.Connected, data.RSSI) == ("STA", False, None)
    assert status_calls == []
    assert client.get_dns_server_ip() is None


def test_deactivated_snapshot_makes_no_radio_call() -> None:
    client = make_client()
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
    client = make_client()
    _wlan(client).raise_on["ifconfig"] = OSError("simulated ifconfig failure")
    run(client._update_wifi_snapshot(connected=True))  # must not raise
    data = run(client.get_data())
    assert (data.IP, data.Subnet, data.Gateway, data.DNS) == (None, None, None, None)
    assert (data.Connected, data.RSSI) == (True, -50)  # the rest of the snapshot is unaffected
    assert client.get_dns_server_ip() is None


def test_a_failed_rssi_read_publishes_none_and_keeps_the_rest() -> None:
    client = make_client()
    _wlan(client)._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "10.0.0.53")
    _wlan(client).raise_on["status"] = OSError("simulated rssi failure")
    run(client._update_wifi_snapshot(connected=True))  # must not raise
    data = run(client.get_data())
    assert (data.IP, data.DNS, data.RSSI) == ("10.0.0.5", "10.0.0.53", None)


def test_get_dns_server_ip_returns_the_dhcp_dns_of_the_last_snapshot() -> None:
    client = make_client()
    _wlan(client)._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "192.168.1.1")
    assert client.get_dns_server_ip() is None  # no snapshot yet
    run(client._update_wifi_snapshot(connected=True))
    assert client.get_dns_server_ip() == "192.168.1.1"


def test_get_dns_server_ip_returns_the_last_snapshot_value_while_the_lock_is_held() -> None:
    # The DNS server NTP needs is never lost because WiFi holds the lock when NTP samples it.
    client = make_client()
    _wlan(client)._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "192.168.1.1")
    run(client._update_wifi_snapshot(connected=True))
    run(client.wifi_mode_lock.acquire())
    try:
        assert client.get_dns_server_ip() == "192.168.1.1"
    finally:
        client.wifi_mode_lock.release()


def test_get_dns_server_ip_reads_no_radio() -> None:
    client = make_client()
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
    with _DrivenTime() as clock:
        client = make_client()
        client._conn_phase = _PHASE_DEACTIVATED

        async def scenario() -> "tuple[int, Any]":
            task = asyncio.create_task(client._uptime_loop())
            for _ in range(2):
                clock.advance(1000)
                await _tick(client._time_counter_trigger_event)
            uptime = await client.get_wifi_uptime()
            data = await client.get_data()
            await _cancel(task)
            return uptime, data.Connected

        uptime, connected = run(scenario())
    assert uptime == 0
    assert connected is False


def test_uptime_loop_counts_measured_seconds_while_connected() -> None:
    with _DrivenTime() as clock:
        client = make_client()
        _wlan(client)._status = network.STAT_GOT_IP

        async def scenario() -> int:
            task = asyncio.create_task(client._uptime_loop())
            await asyncio.sleep(0)
            for _ in range(3):
                clock.advance(1000)
                await _tick(client._time_counter_trigger_event)
            uptime = await client.get_wifi_uptime()
            await _cancel(task)
            return uptime

        assert run(scenario()) == 3


def test_a_delayed_wake_advances_uptime_by_the_measured_time() -> None:
    # One wake-up 2.5 s after the last: the uptime grows by the 2 whole seconds that passed, not by 1
    # per wake-up, so a dropped or late soft-Timer callback costs latency only (SPECIFICATION.md C.9).
    with _DrivenTime() as clock:
        client = make_client()
        _wlan(client)._status = network.STAT_GOT_IP

        async def scenario() -> int:
            task = asyncio.create_task(client._uptime_loop())
            await asyncio.sleep(0)
            clock.advance(2500)
            await _tick(client._time_counter_trigger_event)
            uptime = await client.get_wifi_uptime()
            await _cancel(task)
            return uptime

        assert run(scenario()) == 2


def test_uptime_loop_resets_uptime_while_not_connected() -> None:
    with _DrivenTime() as clock:
        client = make_client()
        _wlan(client)._status = network.STAT_IDLE

        async def scenario() -> int:
            task = asyncio.create_task(client._uptime_loop())
            for _ in range(2):
                clock.advance(1000)
                await _tick(client._time_counter_trigger_event)
            uptime = await client.get_wifi_uptime()
            await _cancel(task)
            return uptime

        assert run(scenario()) == 0


# ---------------------------------------------------------------------------
# Observation-tier helpers: a status/isconnected/ifconfig *query* failing degrades silently
# (returns a safe sentinel) instead of raising or feeding get_error_counter()
# ---------------------------------------------------------------------------


def test_wlan_status_or_none_returns_the_real_status() -> None:
    client = make_client()
    _wlan(client)._status = network.STAT_CONNECTING
    assert client._wlan_status_or_none() == network.STAT_CONNECTING


def test_wlan_status_or_none_returns_none_on_exception() -> None:
    client = make_client()
    _wlan(client).raise_on["status"] = OSError("simulated")
    assert client._wlan_status_or_none() is None


def test_wlan_isconnected_or_false_returns_false_on_exception() -> None:
    client = make_client()
    _wlan(client).raise_on["isconnected"] = OSError("simulated")
    assert client._wlan_isconnected_or_false() is False


def _available_locked(client: WifiService) -> bool:
    # network_available_locked() under the lock its caller must hold, as NTPClient calls it.
    async def held() -> bool:
        async with client.wifi_mode_lock:
            return client.network_available_locked()

    return run(held())


def test_network_available_true_only_in_sta_mode_with_an_ip() -> None:
    client = make_client()
    client._conn_phase = _PHASE_STA_SEEKING
    _wlan(client)._status = network.STAT_GOT_IP
    assert _available_locked(client) is True


def test_network_available_false_in_hotspot_mode_even_with_an_ip() -> None:
    client = make_client()
    client._conn_phase = _PHASE_HOTSPOT
    _wlan(client)._status = network.STAT_GOT_IP
    assert _available_locked(client) is False


def test_network_available_false_on_a_status_exception() -> None:
    client = make_client()
    client._conn_phase = _PHASE_STA_SEEKING
    _wlan(client).raise_on["status"] = OSError("simulated")
    assert _available_locked(client) is False  # degrades via _wlan_status_or_none(), not a raise


# ---------------------------------------------------------------------------
# is_hotspot_active() - lock-free getter for asy_webserver_service.py's captive-portal redirect
# fallback (SPECIFICATION.md Part A.5). All four _conn_phase values are exercised deliberately:
# a regression narrowed to, say, _PHASE_DEACTIVATED alone would slip past a two-case test.
# ---------------------------------------------------------------------------


def test_is_hotspot_active_true_in_hotspot_phase() -> None:
    client = make_client()
    client._conn_phase = _PHASE_HOTSPOT
    assert client.is_hotspot_active() is True


def test_is_hotspot_active_false_in_sta_seeking_phase() -> None:
    client = make_client()
    client._conn_phase = _PHASE_STA_SEEKING
    assert client.is_hotspot_active() is False


def test_is_hotspot_active_false_in_sta_established_phase() -> None:
    client = make_client()
    client._conn_phase = _PHASE_STA_ESTABLISHED
    assert client.is_hotspot_active() is False


def test_is_hotspot_active_false_in_deactivated_phase() -> None:
    client = make_client()
    client._conn_phase = _PHASE_DEACTIVATED
    assert client.is_hotspot_active() is False


def test_is_hotspot_active_dynamic_mode_switch_reflects_live_state_not_cached() -> None:
    # Dynamic-mode-switch coverage: a plain int-compare getter with no caching must track
    # _conn_phase live on the SAME client instance across repeated calls. Every other test above
    # uses a fresh make_client() per phase, which alone wouldn't catch a memoization bug.
    client = make_client()
    for phase, expected in (
        (_PHASE_STA_SEEKING, False),
        (_PHASE_HOTSPOT, True),
        (_PHASE_STA_ESTABLISHED, False),
        (_PHASE_HOTSPOT, True),
        (_PHASE_DEACTIVATED, False),
    ):
        client._conn_phase = phase
        assert client.is_hotspot_active() is expected, f"phase {phase} -> expected {expected}"


# ---------------------------------------------------------------------------
# Compound scenario: an established connection's outage retry (_on_sta_disconnected()'s
# _STA_RETRY_AFTER_LOSS_S wait) is in flight while a REST-facing getter runs in a second task - the
# shape GET /status or GET /networking sees during a live 60 s retry window.
# ---------------------------------------------------------------------------


def test_status_getters_return_the_last_snapshot_during_an_outage_retry() -> None:
    client = make_client(conn_fail_to_hotspot=2)
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
        await _cancel(task)
        return answers, still_waiting, taken

    answers, still_waiting, taken = run(scenario())
    assert still_waiting is True, "the 60 s retry wait finished early - the getters were not read during it"
    assert answers == (snapshot, "10.0.0.53", False)
    assert taken is True, "the retry wait held wifi_mode_lock"
    # The ESTABLISHED branch is a patient retry, never an escalation toward the hotspot.
    assert client._connection_failures == 0


def test_reconnect_wifi_sets_the_trigger_and_tears_down_hotspot_bookkeeping() -> None:
    client = make_client(hotspot_time_min=1)
    run(client._hotspot_client_absent())  # arms _hotspot_timer + starts a real _ledflash task

    async def scenario() -> "tuple[bool, bool, bool]":
        await asyncio.sleep(0)
        ledflash_before = client._ledflash
        client.reconnect_wifi()
        ledflash_cleared = (ledflash_before is not None) and (client._ledflash is None)
        assert ledflash_before is not None
        await _cancel(ledflash_before)  # let the cancellation actually settle
        return client._reconn_wifi, client._hotspot_timer_running, ledflash_cleared

    reconn, timer_running, ledflash_cleared = run(scenario())
    assert reconn is True
    assert timer_running is False
    assert ledflash_cleared is True


# ---------------------------------------------------------------------------
# _hotspot_client_connected() / _hotspot_client_absent() - the hotspot auto-shutoff timer
# ---------------------------------------------------------------------------


def test_hotspot_client_connected_stops_the_shutoff_timer_and_starts_the_client_pattern() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
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
    client = make_client(hotspot_time_min=1)
    run(client._hotspot_client_absent())
    assert client._hotspot_timer_running is True
    assert client._hotspot_timer.mode == Timer.PERIODIC  # C.9: a dropped fire is re-fired next period
    assert client._hotspot_timer.period == 60000  # hotspot_time_min=1 -> 60000ms


def test_hotspot_client_absent_shutoff_timer_fires_reconnect() -> None:
    # The Timer callback itself only sets _hotspot_timeout_trigger_event (no business logic inside
    # the IRQ callback, see C.9) - _hotspot_timeout_loop() is the coroutine that actually calls
    # reconnect_wifi() once woken by that flag.
    client = make_client(hotspot_time_min=1)
    run(client._hotspot_client_absent())

    async def scenario() -> bool:
        watcher = client.start_asy_hotspot_timeout()
        client._hotspot_timer.trigger()
        await asyncio.sleep(0)
        result = client._reconn_wifi
        await _cancel(watcher)
        return result

    assert run(scenario()) is True


def test_hotspot_timeout_watcher_calls_reconnect_wifi_directly_when_woken() -> None:
    client = make_client(hotspot_time_min=1)
    run(client._hotspot_client_absent())  # arms _hotspot_timer + starts a real _ledflash task
    ledflash_before = client._ledflash

    async def scenario() -> bool:
        watcher = client.start_asy_hotspot_timeout()
        client._hotspot_timeout_trigger_event.set()
        await asyncio.sleep(0)
        result = client._reconn_wifi
        await _cancel(watcher)
        assert ledflash_before is not None
        await _cancel(ledflash_before)  # reconnect_wifi() already cancelled it - let it settle
        return result

    assert run(scenario()) is True


def test_a_dropped_hotspot_timer_fire_is_recovered_by_the_next_period() -> None:
    # The soft-callback drop (Part F.1): the first period's fire never reaches the flag. PERIODIC
    # keeps the timer armed, so the next period's fire still reconnects - no backstop needed.
    client = make_client(hotspot_time_min=1)
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
        await _cancel(watcher)
        return after_drop, result

    assert run(scenario()) == (False, True)


def test_the_first_delivered_hotspot_fire_stops_the_periodic_timer() -> None:
    # reconnect_wifi() deinits the timer, so PERIODIC never turns into a reconnect every period.
    client = make_client(hotspot_time_min=1)
    run(client._hotspot_client_absent())
    timer = client._hotspot_timer

    async def scenario() -> None:
        watcher = client.start_asy_hotspot_timeout()
        timer.trigger()
        await asyncio.sleep(0)
        await _cancel(watcher)

    run(scenario())
    assert timer.deinit_called is True
    assert client._hotspot_timer_running is False
    assert timer.callback is None  # nothing left to fire


def test_repeated_absent_ticks_neither_rearm_the_timer_nor_log_anything() -> None:
    # The old ONE_SHOT backstop counted these ticks and persisted errno 19 past 2x hotspot_time;
    # with PERIODIC there is nothing to count and nothing to log (errno 19 is retired, C.7.1).
    client = make_client(hotspot_time_min=1)
    run(client.pr.setup())
    run(client._hotspot_client_absent())
    armed = client._hotspot_timer.callback
    for _ in range(50):  # ~4 minutes of 5s ticks, past the old 24-tick threshold
        run(client._hotspot_client_absent())
    assert client._hotspot_timer.callback is armed
    assert client._reconn_wifi is False  # only the timer ends hotspot mode, never the tick count
    assert run(client.get_error_counter())["WIFI"]["ErrCount"] == 0


def test_hotspot_client_absent_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    client = make_client(hotspot_time_min=1)
    run(client.pr.setup())
    with _RaiseOnArm():
        run(client._hotspot_client_absent())  # must not raise despite the timer failing to arm
    assert client._hotspot_timer_running is False  # left False so the next cycle retries arming it
    assert _used_slots(run(client.get_error_counter())) == [code("E", "TIMER")]  # a hotspot that never times out is evidence


def test_hotspot_client_absent_degrades_gracefully_on_a_memory_error() -> None:
    # Sibling of the OSError test above, for the other arm of _hotspot_client_absent()'s own
    # `except (OSError, MemoryError)` - _hotspot_timer_running stays False either way, so the next
    # refresh cycle retries arming it rather than getting stuck.
    client = make_client(hotspot_time_min=1)
    run(client.pr.setup())
    with _RaiseOnArm(MemoryError):
        run(client._hotspot_client_absent())  # must not raise despite the timer failing to arm
    assert client._hotspot_timer_running is False  # left False so the next cycle retries arming it
    assert _used_slots(run(client.get_error_counter())) == [code("E", "TIMER")]


def test_hotspot_client_absent_starts_the_led_flash_task() -> None:
    client = make_client()

    async def scenario() -> None:
        await client._hotspot_client_absent()
        assert client._ledflash is not None
        await _cancel(client._ledflash)

    run(scenario())


# ---------------------------------------------------------------------------
# "Attempt" operations - a mode switch, hotspot activation, a connect trigger, polling connect
# status, the disconnect-wait, permanent deactivation: each persists a real errno via pr.err_s() and
# sets self._hw_op_failed on a genuine exception, independent of the AP-reachability-driven fallback.
# ---------------------------------------------------------------------------


def test_switch_wlan_mode_exception_sets_hw_op_failed_and_persists_wlan_mode_switch() -> None:
    client = make_client()
    run(client.pr.setup())
    _wlan(client).raise_on["disconnect"] = RuntimeError("simulated hardware fault")
    assert run(client._select_wifi_mode(network.AP_IF)) is False  # the failed switch reported to its caller
    assert client._hw_op_failed is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "WLAN_MODE_SWITCH")
    assert _last_err(counter, "ErrType") == "E"


def test_activate_hotspot_ap_exception_sets_hw_op_failed_and_persists_wlan_ap_start() -> None:
    client = make_client()
    run(client.pr.setup())
    _wlan(client).raise_on["config"] = RuntimeError("simulated hardware fault")
    run(client._activate_hotspot_ap("DE", "TestHost", "12345678"))
    assert client._hw_op_failed is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "WLAN_AP_START")
    assert _last_err(counter, "ErrType") == "E"


def test_activate_hotspot_ap_success_configures_and_activates_the_ap() -> None:
    client = make_client()

    async def scenario() -> None:
        await client._activate_hotspot_ap("US", "MyHost", "12345678")
        assert client._hw_op_failed is False
        assert _wlan(client)._active is True
        assert {"essid": "MyHost", "password": "12345678"} in _wlan(client).config_calls
        assert client._dns_server_task is not None
        await _cancel(client._dns_server_task)

    run(scenario())


def test_trigger_sta_connect_exception_sets_hw_op_failed_and_persists_wlan_sta_start() -> None:
    client = make_client()
    run(client.pr.setup())
    _wlan(client).raise_on["connect"] = RuntimeError("simulated hardware fault")
    result = run(client._trigger_sta_connect("ssid", "pw", "DE", "host"))
    assert result is False
    assert client._hw_op_failed is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "WLAN_STA_START")
    assert _last_err(counter, "ErrType") == "E"


def test_trigger_sta_connect_success_returns_true_and_records_the_attempt() -> None:
    client = make_client()
    result = run(client._trigger_sta_connect("MySSID", "MyPW", "DE", "host"))
    assert result is True
    assert client._hw_op_failed is False
    assert _wlan(client).connect_calls == [("MySSID", "MyPW")]
    assert _wlan(client)._active is True


def test_poll_sta_connect_status_exception_sets_hw_op_failed_and_persists_wlan_sta_poll() -> None:
    client = make_client()
    run(client.pr.setup())
    _wlan(client).raise_on["status"] = RuntimeError("simulated hardware fault")
    run(client._poll_sta_connect_status())
    assert client._hw_op_failed is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "WLAN_STA_POLL")
    assert _last_err(counter, "ErrType") == "E"


def test_poll_sta_connect_status_wrong_password_persists_wlan_auth_failed() -> None:
    # cyw43 reports any failed AUTH event or key exchange as BADAUTH: the text claims no more than that.
    client = make_client()
    run(client.pr.setup())
    _wlan(client)._status = network.STAT_WRONG_PASSWORD
    lines = _poll_printing(client)
    assert ("WIFI", "WLAN authentication or handshake failed") in lines, lines
    assert client._hw_op_failed is False  # a real connect outcome, not a hardware/driver failure
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("W", "WLAN_AUTH_FAILED")
    assert _last_err(counter, "ErrType") == "W"


def test_poll_sta_connect_status_no_ap_found_persists_wlan_no_ap() -> None:
    client = make_client()
    run(client.pr.setup())
    _wlan(client)._status = network.STAT_NO_AP_FOUND
    run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("W", "WLAN_NO_AP")
    assert _last_err(counter, "ErrType") == "W"


def test_poll_sta_connect_status_connect_fail_persists_wlan_connect_failed() -> None:
    client = make_client()
    run(client.pr.setup())
    _wlan(client)._status = network.STAT_CONNECT_FAIL
    run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("W", "WLAN_CONNECT_FAILED")
    assert _last_err(counter, "ErrType") == "W"


def test_poll_sta_connect_status_undefined_state_persists_wlan_status_unknown() -> None:
    client = make_client()
    run(client.pr.setup())
    _wlan(client)._status = 12345  # not any real/defined network.STAT_* value
    run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("W", "WLAN_STATUS_UNKNOWN")
    assert _last_err(counter, "ErrType") == "W"


# A repeated connect verdict is one code: one slot, every attempt counted (C.7.1's central rule).


def test_a_repeated_connect_verdict_spends_one_slot_however_often_the_outage_retries() -> None:
    client = make_client()
    run(client.pr.setup())
    _wlan(client)._status = network.STAT_NO_AP_FOUND
    for _attempt in range(10):
        run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    assert _used_slots(counter) == [code("W", "WLAN_NO_AP")], "ten retries must not spend ten slots"
    assert counter["WIFI"]["ErrCount"] == 10, "...and must still be counted: ten failed attempts are ten events"


def test_a_different_verdict_in_the_same_outage_still_persists() -> None:
    client = make_client()
    run(client.pr.setup())
    for status in (network.STAT_NO_AP_FOUND, network.STAT_NO_AP_FOUND, network.STAT_WRONG_PASSWORD):
        _wlan(client)._status = status
        run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    # Two distinct verdicts on one outage, each evidence of what the link did: both keep a slot.
    assert _used_slots(counter) == [code("W", "WLAN_NO_AP"), code("W", "WLAN_AUTH_FAILED")]


def test_a_recurrence_after_recovery_stays_one_slot() -> None:
    client = make_client()
    run(client.pr.setup())
    _wlan(client)._status = network.STAT_NO_AP_FOUND
    run(client._poll_sta_connect_status())
    client._on_sta_connected()
    run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    assert _used_slots(counter) == [code("W", "WLAN_NO_AP")]
    assert counter["WIFI"]["ErrCount"] == 2


def test_disconnect_sta_and_wait_exception_sets_hw_op_failed_and_persists_wlan_sta_disconnect() -> None:
    client = make_client()
    run(client.pr.setup())
    _wlan(client).raise_on["disconnect"] = RuntimeError("simulated hardware fault")
    run(client._disconnect_sta_and_wait())
    assert client._hw_op_failed is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "WLAN_STA_DISCONNECT")
    assert _last_err(counter, "ErrType") == "E"


def test_disconnect_sta_and_wait_returns_immediately_when_already_disconnected() -> None:
    client = make_client()
    _wlan(client)._connected = False
    run(client._disconnect_sta_and_wait())
    assert client._hw_op_failed is False
    assert _wlan(client).disconnect_called is True


def test_disconnect_sta_and_wait_times_out_instead_of_hanging_forever() -> None:
    # A driver that never confirms disconnection (isconnected() always True) must not hang _connect_loop()
    # forever: the wait is bounded by _STA_DISCONNECT_WAIT_ITERS x _STA_DISCONNECT_POLL_S, each step a yield here.

    # The fake WLAN's disconnect() normally clears _connected as a side effect; overridden here to
    # a no-op so isconnected() keeps reporting True throughout.
    client = make_client()
    run(client.pr.setup())
    _wlan(client)._connected = True
    _wlan(client).disconnect = lambda: setattr(_wlan(client), "disconnect_called", True)
    fast = _FastAsyncSleep()

    async def scenario() -> "list[float]":
        await client._disconnect_sta_and_wait()
        return fast.of(asyncio.current_task())

    with fast:
        steps = run(scenario())
    assert steps == [float(_src_const("_STA_DISCONNECT_POLL_S"))] * int(_src_const("_STA_DISCONNECT_WAIT_ITERS"))
    assert client._hw_op_failed is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "TIMEOUT")
    assert _last_err(counter, "ErrType") == "E"


def test_deactivate_wlan_permanently_sets_state_even_when_the_hardware_call_raises() -> None:
    client = make_client()
    run(client.pr.setup())
    client._conn_phase = _PHASE_HOTSPOT
    _wlan(client).raise_on["disconnect"] = RuntimeError("simulated hardware fault")
    run(client._deactivate_wlan_permanently())
    assert client._conn_phase == _PHASE_DEACTIVATED
    assert client._hw_op_failed is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("E", "WLAN_OFF")
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
    client = make_client(debug=5)  # DebugLevel 5 (SPEC A.8) - pr.all() actually prints, not gated off
    _wlan(client)._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "8.8.8.8")
    client._print_wlan_diagnostics()  # must not raise


def test_print_wlan_diagnostics_degrades_gracefully_when_ifconfig_raises() -> None:
    print("(expected) debug=5 makes the fresh ConfigManager below log its normal first-use config-file creation")
    client = make_client(debug=5)
    _wlan(client).raise_on["ifconfig"] = RuntimeError("simulated hardware fault")
    print("(expected) simulating a hardware fault - the following 'WLAN diagnostic read failed' is intentional")
    client._print_wlan_diagnostics()  # must not raise


def test_on_sta_connected_updates_state_and_turns_led_on() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    client._connection_failures = 3
    client._on_sta_connected()
    assert client._conn_phase == _PHASE_STA_ESTABLISHED
    assert client._connection_failures == 0
    assert led.on_calls == 1


def test_register_sta_connection_failure_increments_below_threshold() -> None:
    client = make_client(conn_fail_to_hotspot=3)
    run(client._register_sta_connection_failure())
    assert client._connection_failures == 1
    assert client._conn_phase == _PHASE_STA_SEEKING


def test_register_sta_connection_failure_switches_to_hotspot_at_threshold() -> None:
    client = make_client(conn_fail_to_hotspot=2)
    client._connection_failures = 1  # one below threshold already
    client._hotspot_started_once = False
    run(client._register_sta_connection_failure())
    assert client._connection_failures == 0
    assert client._conn_phase == _PHASE_HOTSPOT


def test_register_sta_connection_failure_deactivates_when_hotspot_already_tried() -> None:
    client = make_client(conn_fail_to_hotspot=2)
    run(client.pr.setup())
    client._connection_failures = 1
    client._hotspot_started_once = True
    run(client._register_sta_connection_failure())
    assert client._conn_phase == _PHASE_DEACTIVATED


def test_on_sta_disconnected_registers_failure_when_never_connected() -> None:
    client = make_client(conn_fail_to_hotspot=3)
    client._conn_phase = _PHASE_STA_SEEKING
    run(client._on_sta_disconnected())
    assert client._connection_failures == 1


def test_on_sta_disconnected_retries_after_a_minute_when_previously_connected() -> None:
    # _PHASE_STA_ESTABLISHED reports the retry as due; _run_sta_mode() then sleeps _STA_RETRY_AFTER_LOSS_S
    # after releasing wifi_mode_lock, so NTP, the uptime tick and a reconnect are never held up by the wait.
    client = make_client(conn_fail_to_hotspot=2)
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
    assert waited == [(float(int(_src_const("_STA_RETRY_AFTER_LOSS_S"))), False)]
    assert client._connection_failures == 0  # never reached _register_sta_connection_failure()


def test_handle_sta_connection_result_connected_calls_on_sta_connected() -> None:
    client = make_client()
    _wlan(client)._connected = True
    assert run(client._handle_sta_connection_result()) is False  # connected: no retry wait due
    assert client._conn_phase == _PHASE_STA_ESTABLISHED


def test_handle_sta_connection_result_disconnected_calls_on_sta_disconnected() -> None:
    client = make_client(conn_fail_to_hotspot=3)
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
    client = make_client(cfg_path=cfg_path, ext_led=FakeLED())
    run(client.pr.setup())
    run(client._apply_initial_led_config())
    assert client._conn_phase == _PHASE_DEACTIVATED
    assert client._led is not None
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("W", "CFG_READ")
    assert _last_err(counter, "ErrType") == "W"
    assert _used_slots(run(client.cfgmgr.get_error_counter()), "CFGMGR_WIFI")[-1] == code("E", "CFG_NOT_VALID")


def test_apply_initial_led_config_valid_config_does_not_deactivate() -> None:
    client = make_client()
    run(client._apply_initial_led_config())
    assert client._conn_phase != _PHASE_DEACTIVATED


def test_start_hotspot_missing_config_logs_in_both_layers() -> None:
    client = make_invalid_cfg_client()
    run(client.pr.setup())

    async def fake_select(_mode: int) -> None:
        return None  # skips the real mode-switch dance (and its real asyncio.sleep()s) entirely

    client._select_wifi_mode = fake_select  # type: ignore[method-assign, assignment]  # deliberate monkeypatch
    run(client._start_hotspot())
    assert client._hotspot_started_once is True
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("W", "CFG_READ")
    assert _last_err(counter, "ErrType") == "W"
    assert _used_slots(run(client.cfgmgr.get_error_counter()), "CFGMGR_WIFI")[-1] == code("E", "CFG_NOT_VALID")


def test_attempt_sta_connect_missing_config_logs_in_both_layers() -> None:
    client = make_invalid_cfg_client()
    run(client.pr.setup())
    run(client._attempt_sta_connect())
    assert _wlan(client).connect_calls == []  # never reached the real connect attempt
    counter = run(client.get_error_counter())
    assert _last_err(counter, "ErrNum") == code("W", "CFG_READ")
    assert _last_err(counter, "ErrType") == "W"
    assert _used_slots(run(client.cfgmgr.get_error_counter()), "CFGMGR_WIFI")[-1] == code("E", "CFG_NOT_VALID")


def test_an_empty_ssid_returns_to_the_hotspot_without_a_failure_streak() -> None:
    # No SSID (factory state, or after "Reset to defaults"): nothing to attempt, so no streak - even after
    # the hotspot ran once, an unconfigured unit goes back to its hotspot instead of deactivating.
    client = make_client(conn_fail_to_hotspot=2)  # the default SSID is "" until configured
    run(client.pr.setup())
    client._hotspot_started_once = True
    client.pr.set_level(4)
    recorder = _PrintRecorder()
    try:
        run(client._attempt_sta_connect())
    finally:
        recorder.restore()
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
    with _FastAsyncSleep():
        run(client._leave_hotspot_mode())
        run(client._run_sta_mode())


def test_an_unconfigured_unit_never_deactivates_over_two_hotspot_windows() -> None:
    client = make_client(conn_fail_to_hotspot=1)
    run(client.pr.setup())
    for window in range(2):
        client._conn_phase = _PHASE_HOTSPOT
        _end_hotspot_window(client)
        assert client._conn_phase == _PHASE_HOTSPOT, window
        assert client._connection_failures == 0, window
    assert run(client.get_error_counter())["WIFI"]["ErrCount"] == 0


def test_a_configured_ssid_whose_second_streak_fails_still_deactivates() -> None:
    # Control, the owner rule (SPECIFICATION.md A.4): a second streak of real STA attempts ends DEACTIVATED.
    client = make_client_with_json(_VALID_JSON, conn_fail_to_hotspot=1)
    run(client.pr.setup())
    _wlan(client)._status = network.STAT_NO_AP_FOUND
    client._conn_phase = _PHASE_HOTSPOT
    _end_hotspot_window(client)
    assert len(_wlan(client).connect_calls) == 1
    assert client._conn_phase == _PHASE_DEACTIVATED


def test_the_first_streak_persists_its_fallback_and_the_second_its_deactivation_once() -> None:
    # The two owner-designed transitions leave a trace in the WIFI history, so it says why a unit was offline.
    client = make_client(conn_fail_to_hotspot=2)
    run(client.pr.setup())
    for _ in range(2):
        run(client._register_sta_connection_failure())
    assert client._conn_phase == _PHASE_HOTSPOT
    assert _used_slots(run(client.get_error_counter())) == [code("W", "WLAN_TO_HOTSPOT")]
    client._conn_phase = _PHASE_STA_SEEKING
    client._hotspot_started_once = True
    with _FastAsyncSleep():
        for _ in range(2):
            run(client._register_sta_connection_failure())
    assert client._conn_phase == _PHASE_DEACTIVATED
    log = run(client.get_error_counter())
    assert _used_slots(log) == [code("W", "WLAN_TO_HOTSPOT"), code("W", "WLAN_DEACTIVATED")]
    _no_sta(client)

    async def deactivated_iterations() -> None:
        task = asyncio.create_task(client._connect_loop())
        await _drive(12)
        await _cancel(task)
        if client._ledflash is not None:
            await _stop_flash(client)

    with _FastAsyncSleep():
        run(deactivated_iterations())
    assert run(client.get_error_counter()) == log  # further deactivated iterations persist nothing


# ---------------------------------------------------------------------------
# The orchestration layer around _connect_loop()'s main loop, previously only exercised indirectly:
# _run_sta_mode, _get_hotspot_stations, _manage_hotspot_stations, _run_hotspot_mode,
# _leave_hotspot_mode, _wait_for_sta_disconnect and _handle_reconnect_trigger.
# ---------------------------------------------------------------------------


def test_run_sta_mode_attempts_connect_when_not_connected() -> None:
    client = make_client()
    _wlan(client)._connected = False
    attempt_calls = [0]

    async def fake_attempt() -> None:
        attempt_calls[0] += 1

    client._attempt_sta_connect = fake_attempt  # type: ignore[method-assign]  # deliberate monkeypatch
    run(client._run_sta_mode())
    assert attempt_calls[0] == 1
    assert client.wifi_mode_lock.locked() is False  # released despite the attempt being faked out


def test_run_sta_mode_skips_attempt_when_already_connected() -> None:
    client = make_client()
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
    client = make_client(conn_fail_to_hotspot=2)
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
    client = make_client_with_json(_VALID_JSON, conn_fail_to_hotspot=2)
    client._conn_phase = _PHASE_STA_ESTABLISHED
    _wlan(client)._connected = True

    async def scenario() -> None:
        for _ in range(10):  # stuck true for a while first, same shape as the steady-state test above
            await client._run_sta_mode()
        assert _wlan(client).connect_calls == []  # confirms nothing attempted yet
        _wlan(client)._connected = False  # the real firmware-level flip, finally happening
        await client._run_sta_mode()  # its connect poll runs its full window: the fake reports IDLE throughout

    with _FastAsyncSleep():
        run(scenario())
    assert len(_wlan(client).connect_calls) == 1  # a real reconnect attempt was made on this very
    # first post-flip cycle


def test_get_hotspot_stations_returns_the_real_list_on_success() -> None:
    client = make_client()
    _wlan(client)._stations = [(b"\xaa\xbb\xcc\xdd\xee\xff",)]
    stations = run(client._get_hotspot_stations())
    assert stations == [(b"\xaa\xbb\xcc\xdd\xee\xff",)]
    assert client.wifi_mode_lock.locked() is False


def test_get_hotspot_stations_answers_none_for_a_failed_query_and_an_empty_list_for_no_client() -> None:
    client = make_client()
    assert run(client._get_hotspot_stations()) == []  # a real empty list: no client
    _wlan(client).raise_on["status"] = RuntimeError("simulated hardware fault")
    assert run(client._get_hotspot_stations()) is None  # unknown, never "no client"
    assert client.wifi_mode_lock.locked() is False


def _failed_stations_case(*, timer_running: bool) -> None:
    client = make_client(hotspot_time_min=1)
    run(client.pr.setup())
    if timer_running:
        run(client._hotspot_client_absent())
    transitions: list[str] = []

    def connected() -> None:
        transitions.append("connected")

    async def absent() -> None:
        transitions.append("absent")

    client._hotspot_client_connected = connected  # type: ignore[method-assign]  # observed, not run
    client._hotspot_client_absent = absent  # type: ignore[method-assign]  # observed, not run
    _wlan(client).raise_on["status"] = RuntimeError("simulated stations failure")
    for _ in range(3):
        run(client._manage_hotspot_stations())
    assert transitions == [], timer_running
    assert client._hotspot_timer_running is timer_running
    log = run(client.get_error_counter())
    assert _used_slots(log) == [code("W", "WLAN_STATIONS_UNKNOWN")] and log["WIFI"]["ErrCount"] == 3, (timer_running, log)
    if client._ledflash is not None:
        run(_stop_flash(client))


def test_a_failed_stations_query_leaves_the_hotspot_timer_as_it_was() -> None:
    # A failed query is unknown: a running shutoff timer keeps running (no client seen) and a stopped one
    # stays stopped (a client was seen); neither transition runs, and one slot counts the failed queries.
    _failed_stations_case(timer_running=True)
    _failed_stations_case(timer_running=False)


def test_manage_hotspot_stations_with_a_client_connected_stops_the_shutoff_timer() -> None:
    client = make_client()
    _wlan(client)._stations = [(b"\xaa\xbb\xcc\xdd\xee\xff",)]
    client._hotspot_timer.init(period=5000, mode=Timer.ONE_SHOT, callback=lambda _b: None)
    run(client._manage_hotspot_stations())
    assert client._hotspot_timer.deinit_called is True


def test_manage_hotspot_stations_with_no_client_arms_the_shutoff_timer() -> None:
    client = make_client(hotspot_time_min=1)
    _wlan(client)._stations = []
    run(client._manage_hotspot_stations())
    assert client._hotspot_timer_running is True


def test_run_hotspot_mode_starts_hotspot_when_no_ip_yet() -> None:
    client = make_client()
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
    client = make_client()
    client._ap_selected = True
    _wlan(client)._status = network.STAT_IDLE
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
    client = make_client()
    _wlan(client)._status = network.STAT_GOT_IP
    manage_calls = [0]

    async def fake_manage() -> None:
        manage_calls[0] += 1

    client._manage_hotspot_stations = fake_manage  # type: ignore[method-assign]  # deliberate monkeypatch
    run(client._run_hotspot_mode())
    assert manage_calls[0] == 1


def test_leave_hotspot_mode_switches_back_to_sta_and_cancels_dns_task() -> None:
    client = make_client()
    client._conn_phase = _PHASE_HOTSPOT
    select_calls: list[Any] = []

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
    client = make_client()
    _wlan(client)._connected = False
    run(client._wait_for_sta_disconnect())
    assert client.wifi_mode_lock.locked() is False
    assert _wlan(client).disconnect_called is True


def test_handle_reconnect_trigger_hotspot_mode_leaves_hotspot() -> None:
    client = make_client()
    client._conn_phase = _PHASE_HOTSPOT
    leave_calls = [0]

    async def fake_leave() -> None:
        leave_calls[0] += 1

    client._leave_hotspot_mode = fake_leave  # type: ignore[method-assign]  # deliberate monkeypatch
    run(client._handle_reconnect_trigger())
    assert leave_calls[0] == 1
    assert client._reconn_wifi is False


def test_handle_reconnect_trigger_sta_mode_waits_for_disconnect() -> None:
    client = make_client()
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
    client = make_client()
    client._conn_phase = _PHASE_HOTSPOT
    client._reset_wlan_connect_state()
    assert client._conn_phase == _PHASE_HOTSPOT


def test_reset_wlan_connect_state_resets_sta_established_to_seeking() -> None:
    client = make_client()
    client._conn_phase = _PHASE_STA_ESTABLISHED
    client._reset_wlan_connect_state()
    assert client._conn_phase == _PHASE_STA_SEEKING


def test_reset_wlan_connect_state_preserves_deactivated_phase_across_a_restart() -> None:
    # A task restart (e.g. after the _hw_op_failed streak gives up) must NOT pull the state machine
    # out of the terminal deactivated phase - _PHASE_DEACTIVATED is a deliberate, permanent WLAN-off
    # state (Part A.4: a physical power-cycle is the recovery), same casing as _PHASE_HOTSPOT above.
    client = make_client()
    client._conn_phase = _PHASE_DEACTIVATED
    client._reset_wlan_connect_state()
    assert client._conn_phase == _PHASE_DEACTIVATED


def test_reset_wlan_connect_state_clears_failure_counters_and_hotspot_started_once() -> None:
    client = make_client()
    client._connection_failures = 3
    client._hotspot_started_once = True
    client._reset_wlan_connect_state()
    assert client._connection_failures == 0
    assert client._hotspot_started_once is False


def test_reset_wlan_connect_state_cancels_ledflash_and_dns_server_task() -> None:
    client = make_client()

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
    client = make_client()
    client._conn_phase = _PHASE_HOTSPOT
    client._reset_wlan_connect_state()
    assert client._reconn_wifi is True


def test_reset_wlan_connect_state_sets_reconn_wifi_true_when_already_connected() -> None:
    client = make_client()
    _wlan(client)._connected = True
    client._reset_wlan_connect_state()
    assert client._reconn_wifi is True


def test_reset_wlan_connect_state_sets_reconn_wifi_true_when_wlan_active_but_not_connected() -> None:
    client = make_client()
    _wlan(client)._active = True
    client._reset_wlan_connect_state()
    assert client._reconn_wifi is True


def test_reset_wlan_connect_state_sets_reconn_wifi_false_when_seeking_and_wlan_is_idle() -> None:
    client = make_client()
    client._reset_wlan_connect_state()
    assert client._reconn_wifi is False


def test_reset_wlan_connect_state_degrades_to_reconn_wifi_true_on_exception() -> None:
    # A real exception checking wlan.isconnected()/active() at task-start time is rare (once per
    # task (re)start) but must still force a safe reconnect-on-next-iteration default rather than
    # silently under-reacting.
    client = make_client()
    run(client.pr.setup())
    _wlan(client).raise_on["isconnected"] = RuntimeError("simulated hardware fault")
    client._reset_wlan_connect_state()
    assert client._reconn_wifi is True


def test_reset_wlan_connect_state_turns_the_led_off() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(status=True))
    client._led_on()
    client._reset_wlan_connect_state()
    assert led.off_calls == 1


def test_a_restart_in_hotspot_ends_in_sta_with_a_fresh_streak() -> None:
    # Guard (the behaviour is unchanged; holds at once): the restart keeps HOTSPOT only so the forced
    # reconnect leaves it through _leave_hotspot_mode(), as legacy's own restart did.
    client = make_client()
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
        await _cancel(loop)
        return dns_task, loop

    with _FastAsyncSleep():
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
    client = make_client()
    before = (client.pr.initialized, client._dns_server.pr.initialized)
    assert run(client.setup()) is True
    assert before == (False, False)
    assert (client.pr.initialized, client._dns_server.pr.initialized) == (True, True)

    unset = make_client()

    async def scenario() -> "tuple[bool, bool]":
        task = asyncio.create_task(unset._connect_loop())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        states = (unset.pr.initialized, unset._dns_server.pr.initialized)
        await _cancel(task)
        return states

    with _FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario()) == (False, False)


def test_wlan_connect_resets_err_cnt_internal_at_the_start_of_every_run() -> None:
    client = make_client()
    client._err_cnt_internal = 99

    async def scenario() -> int:
        task = asyncio.create_task(client._connect_loop())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        streak = client._err_cnt_internal
        await _cancel(task)
        return streak

    with _FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario()) == 0


def test_wlan_connect_skips_the_state_machine_entirely_while_deactivated() -> None:
    client = make_client()
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
        await _cancel(task)
        return calls

    with _FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario()) == 0


def test_wlan_connect_dispatches_to_hotspot_mode_when_conn_phase_is_hotspot() -> None:
    client = make_client()
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
        await _cancel(task)
        return calls

    with _FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        hotspot_called, sta_called = run(scenario())
    assert hotspot_called >= 1
    assert sta_called == 0


def test_wlan_connect_dispatches_to_sta_mode_when_conn_phase_is_not_hotspot() -> None:
    client = make_client()
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
        await _cancel(task)
        return calls

    with _FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        hotspot_called, sta_called = run(scenario())
    assert sta_called >= 1
    assert hotspot_called == 0


def test_wlan_connect_calls_handle_reconnect_trigger_when_reconn_wifi_is_set() -> None:
    # A task (re)start while the driver still reports connected forces _reconn_wifi=True via
    # _reset_wlan_connect_state() - _connect_loop()'s loop must act on that the very first iteration,
    # not only on one following an explicit reconnect_wifi()/hotspot-timer trigger.
    client = make_client()
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
        await _cancel(task)
        return calls

    with _FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario()) == 1


def test_connect_loop_gives_up_after_repeated_hardware_failures_and_persists_both_entries() -> None:
    client = make_client(max_module_error=2)

    async def failing_run_sta_mode() -> None:
        client._hw_op_failed = True  # simulates a real WLAN-hardware exception every cycle

    client._run_sta_mode = failing_run_sta_mode  # type: ignore[method-assign]  # deliberate monkeypatch

    async def scenario() -> "ErrorLog":
        task = asyncio.create_task(client._connect_loop())
        await asyncio.wait_for(task, _CONNECT_BOUND_S)  # must actually complete, not loop forever
        return await client.get_error_counter()

    with _FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        counter = run(scenario())
    kept = _used_slots(counter)
    # The base streak's GIVE_UP, then WIFI's own give-up entry: each layer keeps its own, once.
    assert kept.count(code("E", "GIVE_UP")) == 1 and kept.count(code("E", "WLAN_GIVE_UP")) == 1, kept
    assert _last_err(counter, "ErrNum") == code("E", "WLAN_GIVE_UP")


def test_wlan_connect_never_gives_up_while_repeatedly_succeeding() -> None:
    client = make_client(max_module_error=2)

    async def succeeding_run_sta_mode() -> None:
        return None  # _hw_op_failed stays False (reset every iteration by _connect_loop() itself)

    client._run_sta_mode = succeeding_run_sta_mode  # type: ignore[method-assign]  # deliberate monkeypatch

    async def scenario() -> bool:
        task = asyncio.create_task(client._connect_loop())
        for _ in range(10):
            await asyncio.sleep(0)
        still_running = not task.done()
        await _cancel(task)
        return still_running

    with _FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario()) is True


def test_wlan_connect_recovers_the_streak_on_alternating_failure_and_success() -> None:
    # Proves the give-up decision is a genuine streak, not a monotonic lifetime counter: a success
    # decrements _err_cnt_internal (asy_base_classes.py's own _error_check() contract), so failures that
    # never land two-in-a-row must never trip max_module_error=2, however many cycles run in total.
    client = make_client(max_module_error=2)
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
        await _cancel(task)
        return still_running

    with _FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
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

        def counted(if_id: int) -> "Any":
            built.append(if_id)
            return real(if_id)

        network.WLAN = counted  # type: ignore[misc, assignment]  # a module attribute swap, restored on exit
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
    await _cancel(task)


def test_two_failed_iterations_re_select_the_radio_once() -> None:
    client = make_client()
    run(client.pr.setup())
    first = _wlan(client)
    with _FastAsyncSleep(), _CountedWLAN() as wlan:
        run(_failing_iterations(client, 4))
    assert wlan.built == [network.STA_IF]  # once per episode, though four iterations failed
    assert first.deinit_called is True
    kept = _used_slots(run(client.get_error_counter()))
    assert kept.count(code("W", "DEVICE_RECOVERY")) == 1, kept


def test_in_hotspot_the_ap_is_re_selected() -> None:
    client = make_client()
    client._conn_phase = _PHASE_HOTSPOT
    with _FastAsyncSleep(), _CountedWLAN() as wlan:
        assert run(client._recover_device()) is True
    assert wlan.built == [network.AP_IF]
    assert client._ap_selected is True


def test_deactivated_makes_no_radio_call() -> None:
    client = make_client()
    client._conn_phase = _PHASE_DEACTIVATED
    first = _wlan(client)
    with _FastAsyncSleep(), _CountedWLAN() as wlan:
        assert run(client._recover_device()) is None  # no participant rung: no radio in use
    assert wlan.built == []
    assert first.deinit_called is False and first.disconnect_called is False


def test_a_raising_deinit_logs_one_mode_switch_entry_and_no_recovery_warning() -> None:
    client = make_client()
    run(client.pr.setup())
    _wlan(client).raise_on["deinit"] = RuntimeError("simulated hardware fault")
    with _FastAsyncSleep(), _CountedWLAN() as wlan:
        run(_failing_iterations(client, 3))
    assert wlan.built == []
    kept = _used_slots(run(client.get_error_counter()))
    assert kept.count(code("E", "WLAN_MODE_SWITCH")) == 1, kept
    assert code("W", "DEVICE_RECOVERY") not in kept, kept


def test_the_radio_rung_fires_again_after_a_restart_and_a_good_iteration() -> None:
    client = make_client()
    run(client.pr.setup())

    async def one_good_iteration() -> None:
        _no_sta(client)
        task = asyncio.create_task(client._connect_loop())
        await _drive(4)
        await _cancel(task)

    with _FastAsyncSleep(), _CountedWLAN() as wlan:
        run(_failing_iterations(client, 2))
        run(one_good_iteration())  # a restart, then an iteration without a failure: the episode ends
        run(_failing_iterations(client, 2))
    assert wlan.built == [network.STA_IF, network.STA_IF]


# ===========================================================================
# Integration tests: real (not mocked) captive DNS server - downstream. _configure_hotspot_ap()
# starts a real CaptiveDNS.run() task over a real UDPSocket, so a genuinely malformed/off-subnet
# datagram is handled end to end rather than in isolation.

# CaptiveDNS.__init__ hardcodes privileged port 53 (no root in CI), redirected here by swapping
# client._dns_server._udps for a fresh UDPSocket on a free ephemeral port before starting the
# hotspot, since CaptiveDNS.run() only ever touches self._udps and never rebuilds it.
# ===========================================================================

# 27000+, not a base shared with another test file: scripts/test.sh runs files concurrently, so a
# base must be disjoint from every other file's and must sit below the OS ephemeral range
# (32768-60999). See scripts/test.sh's own TEST_PARALLELISM comment for the full allocation.

# A duplicate unicast UDP bind does not fail with EADDRINUSE here (both sockets set SO_REUSEADDR,
# confirmed directly) - it silently delivers each datagram to one socket only, so a collision
# surfaces as an inexplicable timeout rather than an error.
_next_port = 27000


def _make_addr() -> "tuple[str, int]":
    global _next_port
    _next_port += 1
    return ("127.0.0.1", _next_port)


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
    client = make_client()
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
            await _cancel(client._dns_server_task)

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

    async def recvfrom(self, _bufsize: int) -> "tuple[bytes, tuple[str, int]] | tuple[None, None]":
        if not self._script:
            await asyncio.sleep(3600)  # nothing more to deliver - park forever, caller cancels us
        return self._script.pop(0)

    async def sendto(self, data: bytes, addr: "tuple[str, int]") -> int:
        self.sent.append((data, addr))
        return len(data)

    async def disconnect(self) -> None:
        return None


def test_integration_hotspot_captive_dns_answers_an_on_subnet_query() -> None:
    client = make_client()
    fake_udps = _ScriptedUDPSocket([(_dns_query_packet("test.example.com"), ("192.168.4.55", 5353))])
    client._dns_server._udps = fake_udps  # type: ignore[assignment]  # duck-typed fake, same pattern as asy_captive_dns.py's own tests

    async def scenario() -> None:
        task = asyncio.create_task(client._dns_server.run("192.168.4.1", "255.255.255.0"))
        for _ in range(_SENT_POLL_TRIES):
            if fake_udps.sent:
                break
            await asyncio.sleep_ms(_SENT_POLL_MS)
        await _cancel(task)

    run(scenario())
    assert len(fake_udps.sent) == 1
    reply, addr = fake_udps.sent[0]
    assert addr == ("192.168.4.55", 5353)
    assert reply[:2] == b"\x12\x34"  # echoes the query's own transaction ID
    assert reply[-4:] == bytes([192, 168, 4, 1])  # resolves to own_ip


def test_integration_hotspot_captive_dns_ignores_an_off_subnet_query() -> None:
    # A well-formed query from an address outside the AP's own subnet must be silently ignored (see
    # CaptiveDNS.run()'s on_subnet check) - proves the filter, not just "any query gets answered".
    client = make_client()
    fake_udps = _ScriptedUDPSocket([(_dns_query_packet("test.example.com"), ("10.0.0.55", 5353))])
    client._dns_server._udps = fake_udps  # type: ignore[assignment]  # duck-typed fake, same pattern as asy_captive_dns.py's own tests

    async def scenario() -> None:
        task = asyncio.create_task(client._dns_server.run("192.168.4.1", "255.255.255.0"))
        await asyncio.sleep(_OFF_SUBNET_WAIT_S)
        await _cancel(task)

    run(scenario())
    assert fake_udps.sent == []


# ===========================================================================
# Integration tests: the full _connect_loop() task end to end through the fake network.WLAN, proving
# how a real connect success/failure sequence propagates up through get_data()/get_error_counter()
# and _connection_failures/hotspot fallback. Mirrors test_asy_ntp_client.py's own section.
# ===========================================================================


def test_integration_sta_connect_succeeds_and_propagates_to_get_data() -> None:
    # Simulates a driver reporting a connection established the instant connect() is called;
    # _poll_sta_connect_status() then returns after its first status read.

    # get_data()'s cached snapshot is only ever pushed by _uptime_loop()'s own task, so that is
    # driven here alongside _connect_loop(), exactly like a real task-starter set would.
    client = make_client_with_json(_VALID_JSON)
    original_connect = _wlan(client).connect

    def fake_connect(ssid: str, pw: str) -> None:
        original_connect(ssid, pw)
        _wlan(client)._status = network.STAT_GOT_IP
        _wlan(client)._connected = True

    _wlan(client).connect = fake_connect

    async def scenario() -> "tuple[bool, Any]":
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
        await _cancel(connect_task)
        await _cancel(counter_task)
        return connected_once, (await client.get_data()).Connected

    with _FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        connected_once, data_connected = run(scenario())
    assert connected_once is True
    assert data_connected is True


def test_integration_repeated_wrong_password_falls_back_to_hotspot_mode() -> None:
    client = make_client_with_json(_VALID_JSON, conn_fail_to_hotspot=3)
    _wlan(client)._status = network.STAT_WRONG_PASSWORD  # every _poll_sta_connect_status() call sees this

    async def scenario() -> bool:
        task = asyncio.create_task(client._connect_loop())
        for _ in range(_PHASE_POLL_TRIES):
            if client._conn_phase == _PHASE_HOTSPOT:
                break
            await asyncio.sleep_ms(_PHASE_POLL_MS)
        hotspot_reached = client._conn_phase == _PHASE_HOTSPOT
        await _cancel(task)
        return hotspot_reached

    with _FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario())


def test_cfg_schema_matches_what_cfgmgr_was_built_with() -> None:
    # Regression check for the integration bug where a shared REST helper needed each module's own
    # schema to validate a write correctly - get_cfg_schema() gives an outside caller that schema,
    # without reaching into a private const.
    client = make_client()
    assert client.get_cfg_schema() == (_VAL_SSID + _VAL_PW + _VAL_COUNTRY + _VAL_HOSTNAME + _VAL_LED_WIFI_ON + _VAL_HOTSPOT_PW)


def test_get_cfg_schema_matches_the_public_attribute() -> None:
    # get_cfg_schema() is the base-class-owned access path (see asy_base_classes.py) to the private schema.
    client = make_client()
    assert client.get_cfg_schema() == client._cfg_schema
    assert client.get_cfg_schema() == (_VAL_SSID + _VAL_PW + _VAL_COUNTRY + _VAL_HOSTNAME + _VAL_LED_WIFI_ON + _VAL_HOTSPOT_PW)


def test_write_config_via_public_cfg_schema_round_trips_a_real_value() -> None:
    # Proves get_cfg_schema()'s schema is actually usable for a real write, not just structurally equal - the exact
    # call shape api_helpers.py's cmd_post_check() now makes.
    client = make_client()

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
    client = make_client()

    async def scenario() -> bool:
        task = client.start_asy_connect()
        await asyncio.sleep(0)
        is_task = isinstance(task, asyncio.Task)
        await _cancel(task)
        return is_task

    assert run(scenario()) is True


def test_start_asy_uptime_counter_returns_a_real_task() -> None:
    client = make_client()

    async def scenario() -> bool:
        task = client.start_asy_uptime()
        await asyncio.sleep(0)
        is_task = isinstance(task, asyncio.Task)
        await _cancel(task)
        return is_task

    assert run(scenario()) is True


def test_stop_counter_timer_deinits_the_counter_timer() -> None:
    client = make_client()
    client.start_uptime_timer()
    client.stop_uptime_timer()
    assert client._counter_timer.deinit_called is True


# The snapshot's timestamp is asy_base_classes.utc_now(): None until NTP has set the clock this boot
# ---------------------------------------------------------------------------


def test_the_snapshot_timestamp_is_none_until_the_clock_is_set() -> None:
    client = make_client()
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
    client = make_client()
    original_wlan = _wlan(client)

    async def scenario() -> bool:
        return await client._select_wifi_mode(network.AP_IF)

    with _FastAsyncSleep():
        assert run(scenario()) is True
    assert client._hw_op_failed is False
    assert original_wlan.deinit_called is True
    assert _wlan(client) is not original_wlan  # a fresh WLAN instance replaced it
    assert _wlan(client).if_id == network.AP_IF
    assert run(client.get_wifi_uptime()) == 0


def test_switch_wlan_mode_records_the_selected_interface() -> None:
    # The record the snapshot reads instead of the radio: True only once an AP interface really exists.
    client = make_client()
    run(client.pr.setup())
    seen = [client._ap_selected]
    with _FastAsyncSleep():
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
    client = make_client()
    _wlan(client)._stations = [(b"\xaa\xbb\xcc\xdd\xee\xff",), (b"\x01\x02\x03\x04\x05\x06",)]
    stations = run(client._get_hotspot_stations())
    assert stations == [(b"\xaa\xbb\xcc\xdd\xee\xff",), (b"\x01\x02\x03\x04\x05\x06",)]
    assert not client.wifi_mode_lock.locked()  # released via the finally block


def test_hotspot_client_connected_cancels_an_already_running_ledflash_task() -> None:
    client = make_client()

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

    _wlan(client).status = status
    return calls


def _poll_printing(client: WifiService) -> "list[tuple[object, ...]]":
    # Runs one poll at full console detail (level 5) and returns the lines it printed.
    client.pr.set_level(5)
    recorder = _PrintRecorder()
    try:
        with _FastAsyncSleep():
            run(client._poll_sta_connect_status())
    finally:
        recorder.restore()
    return recorder.lines


def test_poll_sta_connect_status_prints_each_in_progress_state_and_persists_nothing_once_a_verdict_comes() -> None:
    for state, text in ((network.STAT_IDLE, "WLAN idle"), (network.STAT_CONNECTING, "WLAN connecting"), (int(_src_const("_STAT_JOINED_NO_IP")), "WLAN obtaining IP")):
        client = make_client()
        run(client.pr.setup())
        _script_status(client, [state, network.STAT_GOT_IP])
        lines = _poll_printing(client)
        assert ("WIFI", text) in lines, (state, lines)
        assert ("WIFI", "WLAN connection successful") in lines, state
        assert client._hw_op_failed is False
        assert run(client.get_error_counter())["WIFI"]["ErrCount"] == 0, state


def test_a_poll_without_a_verdict_persists_one_warning_naming_the_last_status() -> None:
    # E.g. a DHCP server that never answers: joined, no IP, for the whole poll window.
    for state in (network.STAT_CONNECTING, int(_src_const("_STAT_JOINED_NO_IP"))):
        client = make_client()
        run(client.pr.setup())
        _script_status(client, [state])
        lines = _poll_printing(client)
        log = run(client.get_error_counter())
        assert _used_slots(log) == [code("W", "WLAN_NO_VERDICT")] and log["WIFI"]["ErrCount"] == 1, (state, log)
        assert ("WIFI", "WLAN connect attempt ended without a verdict, last status:", state) in lines, (state, lines)


def test_a_poll_ending_in_a_verdict_persists_no_no_verdict_warning() -> None:
    for state in (network.STAT_GOT_IP, network.STAT_WRONG_PASSWORD, network.STAT_NO_AP_FOUND, network.STAT_CONNECT_FAIL, 12345):
        client = make_client()
        run(client.pr.setup())
        _script_status(client, [network.STAT_CONNECTING, state])
        _poll_printing(client)
        assert code("W", "WLAN_NO_VERDICT") not in _used_slots(run(client.get_error_counter())), state


def test_poll_sta_connect_status_returns_after_one_status_call_on_got_ip() -> None:
    # A successful connect costs one poll step, not the whole window.
    client = make_client()
    calls = _script_status(client, [network.STAT_GOT_IP])
    fast = _FastAsyncSleep()

    async def scenario() -> "list[float]":
        await client._poll_sta_connect_status()
        return fast.of(asyncio.current_task())

    with fast:
        assert run(scenario()) == []
    assert calls == [()]


# ---------------------------------------------------------------------------
# _start_hotspot() success branch - only the missing-config (CFG_READ) branch was exercised above;
# a healthy config must actually reach set_wifi_led()/_activate_hotspot_ap().
# ---------------------------------------------------------------------------


def test_start_hotspot_valid_config_activates_the_ap() -> None:
    client = make_client()

    async def fake_select(_mode: int) -> None:
        return None  # skips the real mode-switch dance (and its real asyncio.sleep()s) entirely

    client._select_wifi_mode = fake_select  # type: ignore[method-assign, assignment]  # deliberate monkeypatch

    async def scenario() -> None:
        await client._start_hotspot()
        assert client._dns_server_task is not None
        await _cancel(client._dns_server_task)

    run(scenario())
    assert client._hotspot_started_once is True
    assert client._hw_op_failed is False
    assert {"essid": "SensorNode", "password": "12345678"} in _wlan(client).config_calls


def test_start_hotspot_uses_the_configured_hotspot_password_not_the_default() -> None:
    # HotspotPW is per-device configurable (SPECIFICATION.md Part C.14) - proves a genuinely
    # non-default value written through cfgmgr actually reaches wlan.config(), not just that the
    # schema default happens to match every other test's hardcoded "12345678" expectation.
    client = make_client()
    ok, results = run(client.cfgmgr.write_config({"HotspotPW": "customhotspotpw1"}))
    assert ok is True
    assert results["HotspotPW"] == "Valid"

    async def fake_select(_mode: "Any") -> None:
        return None

    client._select_wifi_mode = fake_select  # type: ignore[method-assign, assignment]  # deliberate monkeypatch

    async def scenario() -> None:
        await client._start_hotspot()
        assert client._dns_server_task is not None
        await _cancel(client._dns_server_task)

    run(scenario())
    assert client._hw_op_failed is False
    assert {"essid": "SensorNode", "password": "customhotspotpw1"} in _wlan(client).config_calls


# ---------------------------------------------------------------------------
# _run_hotspot_mode() brings the selected AP up again on a tick without a link; doing so never leaks a
# second DNS server task. A real active AP reports STAT_GOT_IP (cyw43_lwip.c); tests/network.py's fake
# does not on its own, so these call _start_hotspot() twice directly.
# ---------------------------------------------------------------------------


def test_start_hotspot_does_not_leak_a_dns_server_task_when_called_again_while_already_running() -> None:
    client = make_client()

    async def fake_select(_mode: int) -> None:
        return None

    client._select_wifi_mode = fake_select  # type: ignore[method-assign, assignment]  # deliberate monkeypatch

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
            await _cancel(first_task)

    run(scenario())


def test_start_hotspot_starts_a_fresh_dns_server_task_if_the_previous_one_already_finished() -> None:
    # The other half of the guard: a *finished* task (real crash/cancellation) must not block a
    # legitimate restart, matching asy_system_service.py's own start_and_check_tasks() `is None or
    # .done()` convention.
    client = make_client()

    async def fake_select(_mode: int) -> None:
        return None

    client._select_wifi_mode = fake_select  # type: ignore[method-assign, assignment]  # deliberate monkeypatch

    async def scenario() -> None:
        await client._start_hotspot()
        first_task = client._dns_server_task
        assert first_task is not None
        await _cancel(first_task)
        assert first_task.done()
        await client._start_hotspot()
        second_task = client._dns_server_task
        assert second_task is not None
        assert second_task is not first_task
        await _cancel(second_task)

    run(scenario())


# ---------------------------------------------------------------------------
# Radio reconfiguration idempotency (real bench hardware investigation): a genuine re-entry while
# the AP interface is still active must not reapply essid/password/active(True), or the real CYW43
# firmware can interrupt its beacon - unlike the DNS-task guard above, a pure resource-leak concern.
# ---------------------------------------------------------------------------


def test_configure_hotspot_ap_does_not_reapply_essid_password_when_already_active() -> None:
    client = make_client()
    run(client.pr.setup())

    async def scenario() -> None:
        essid_call = {"essid": "MyHost", "password": "12345678"}
        client._configure_hotspot_ap("US", "MyHost", "12345678")
        first_task = client._dns_server_task
        assert first_task is not None
        assert _wlan(client)._active is True
        assert _wlan(client).config_calls.count(essid_call) == 1
        client._configure_hotspot_ap("US", "MyHost", "12345678")  # a real re-entry while still active
        assert _wlan(client).config_calls.count(essid_call) == 1  # not reapplied a second time
        assert client._dns_server_task is first_task  # unaffected - the DNS-task guard is independent
        await _cancel(first_task)

    run(scenario())


def test_configure_hotspot_ap_reconfigures_after_the_interface_was_externally_deactivated() -> None:
    client = make_client()
    run(client.pr.setup())

    async def scenario() -> None:
        essid_call = {"essid": "MyHost", "password": "12345678"}
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
        await _cancel(first_task)
        if second_task is not first_task:
            await _cancel(second_task)

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
    first = WifiService(WifiConfig("SensorStationWozi", "12345678", 5, 5), cfg_path=cfg_path)

    async def rename() -> "Any":
        await first.cfgmgr.setup()
        results = await first._set_dict_cfg({"Hostname": "KitchenPi"}, first.get_cfg_schema())
        await first.cfgmgr.flush_pending()  # the real file write is an independent task, never inline
        return results

    assert run(rename()) == {"Hostname": "Valid"}
    second = WifiService(WifiConfig("SensorStationSomethingElse", "12345678", 5, 5), cfg_path=cfg_path)
    run(second.cfgmgr.setup())
    assert run(second.cfgmgr.get_dict(["Hostname"])) == {"Hostname": "KitchenPi"}


def test_a_default_is_only_substituted_into_a_bounded_string_field() -> None:
    # The bounds check is what keeps an unusable default out of the config, and it can only read the
    # length of a str. Any other field shape therefore keeps its own default rather than taking an
    # unchecked one - the two fields buildgen injects are both bounded strings.
    schema: Any = (("LEDWifiOn", "bool", True, None, None, None),)
    assert asy_wifi_service._with_default(schema, "yes") is schema


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
        client = make_client()
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
    import asy_wifi_service

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
    client = make_client()
    results = run(client._set_dict_cfg({"Hostname": "ä" * 17, "Nope": "x"}, client.get_cfg_schema()))
    assert results == {"Hostname": "Invalid", "Nope": "Invalid"}


def test_a_refused_radio_field_leaves_the_rest_of_the_request_applied() -> None:
    client = make_client()
    results = run(client._set_dict_cfg({"Hostname": "ä" * 17, "SSID": "HomeNet", "LEDWifiOn": False}, client.get_cfg_schema()))
    assert results == {"Hostname": "Invalid", "SSID": "Valid", "LEDWifiOn": "Valid"}
    run(client.cfgmgr.flush_pending())
    assert run(client.cfgmgr.get_dict(["SSID", "LEDWifiOn"])) == {"SSID": "HomeNet", "LEDWifiOn": False}


def test_the_open_network_password_bypass_still_passes_the_byte_check() -> None:
    client = make_client()
    run(client._set_dict_cfg({"PW": "x" * 8}, client.get_cfg_schema()))
    assert run(client._set_dict_cfg({"PW": ""}, client.get_cfg_schema())) == {"PW": "Valid"}


def test_a_character_bound_violation_is_still_the_schemas_refusal_not_a_byte_one() -> None:
    client = make_client()
    run(client.pr.setup())
    assert run(client._set_dict_cfg({"Country": "D"}, client.get_cfg_schema())) == {"Country": "Invalid"}
    assert code("E", "BAD_ARG") not in run(client.get_error_counter())["WIFI"]["ErrNum"]


def _client_with_stored(values: "dict[str, str]", conn_fail_to_hotspot: int = 5) -> WifiService:
    # A value the radio refuses, already on flash - stored before C.7.4 or hand-edited.
    import json as _json

    stored = {"SSID": "HomeNet", "PW": "secret123", "Country": "DE", "Hostname": "SensorNode", "LEDWifiOn": True, "HotspotPW": "12345678"}
    stored.update(values)
    return make_client_with_json(_json.dumps(stored), conn_fail_to_hotspot=conn_fail_to_hotspot)


def _no_poll(client: WifiService) -> None:
    async def skip() -> None:
        return None

    client._poll_sta_connect_status = skip  # type: ignore[method-assign]  # connect's outcome is not under test


def test_a_stored_over_long_country_connects_on_the_default_not_a_hardware_failure() -> None:
    client = _client_with_stored({"Country": "ÄT"})
    run(client.pr.setup())
    _no_poll(client)
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
    client = make_client()
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
    client = WifiService(WifiConfig("SensorStationDev", "12345678", 5, 5), cfg_path=cfg_path)
    run(client.cfgmgr.setup())
    run(client.pr.setup())
    _no_poll(client)
    run(client._attempt_sta_connect())
    assert network.hostname() == "SensorStationDev"
    assert client._hw_op_failed is False
    assert run(client.get_dict_cfg())["WIFI"]["Hostname"] == "SensorStationDev"  # the live default, as in use


def test_a_stored_over_long_hotspot_value_starts_the_hotspot_on_the_default() -> None:
    client = _client_with_stored({"Country": "ÄT", "Hostname": "ä" * 17})
    run(client.pr.setup())

    async def fake_select(_mode: int) -> None:
        return None

    client._select_wifi_mode = fake_select  # type: ignore[method-assign, assignment]  # deliberate monkeypatch
    run(client._start_hotspot())
    assert client._hw_op_failed is False
    assert (network.country(), network.hostname()) == ("DE", "SensorNode")
    shown = run(client.get_dict_cfg())["WIFI"]
    assert (shown["Country"], shown["Hostname"]) == ("DE", "SensorNode")


class _PrintRecorder:
    # Local stand-in for a shared print recorder: shadows print() inside asy_print_log only, so every
    # console line a logger emits is captured with its arguments; restore() removes the shadow.
    def __init__(self) -> None:
        self.lines: list[tuple[object, ...]] = []
        print_log_module.print = self  # type: ignore[attr-defined]

    def __call__(self, *args: object, **_kwargs: object) -> None:
        self.lines.append(args)

    def restore(self) -> None:
        del print_log_module.print  # type: ignore[attr-defined]


def _radio_shape_cases() -> "dict[str, dict[str, list[str]]]":
    # One corpus, three judges: this product check, buildgen's and the mock's (SPECIFICATION.md G.2).
    with open("tests/_radio_shape_cases.json") as f:
        cases: dict[str, dict[str, list[str]]] = json.load(f)
    return cases


def _judge_shape_case(field: str, value: str, *, accepted: bool) -> None:
    client = make_client()
    client.pr.set_level(2)  # errors and warnings reach print(), so the refusal's text is checked too
    run(client.pr.setup())
    before = run(client.cfgmgr.get_dict([field]))
    recorder = _PrintRecorder()
    try:
        result = run(client._set_dict_cfg({field: value}, client.get_cfg_schema()))
    finally:
        recorder.restore()
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
    run(stored._attempt_sta_connect())
    default = next(f[2] for f in stored.get_cfg_schema() if f[0] == field)
    assert (network.hostname() if field == "Hostname" else network.country()) == default, (field, value)
    log = run(stored.get_error_counter())["WIFI"]
    assert _used_slots(run(stored.get_error_counter())) == [code("W", "STORED_DEFAULT")] and log["ErrCount"] == 1, (field, value)
    assert run(stored.get_dict_cfg())["WIFI"][field] == default, (field, value)  # GET shows the value in use


def test_every_host_label_and_country_case_is_judged_as_the_corpus_says() -> None:
    cases = _radio_shape_cases()
    for shape, field in (("hostLabel", "Hostname"), ("countryCode", "Country")):
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

    with _FastAsyncSleep():  # _connect_loop() sleeps its 5 s refresh between cycles
        assert run(scenario()) is True
    assert attempts[0] > 3 * client._max_module_error  # far past the old give-up streak
    kept = _used_slots(run(client.get_error_counter()))
    assert code("E", "GIVE_UP") not in kept and code("E", "WLAN_GIVE_UP") not in kept


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
