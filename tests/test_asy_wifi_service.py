import sys

sys.path.insert(0, "improved-quality")  # not yet promoted to src/ - see CLAUDE.md

import asyncio
import os
import select
import socket

# improved-quality/ isn't on mypy_path (only src/typings are - see pyproject.toml) since it's
# still WIP, not yet promoted; every asy_wifi_service-typed value below is consequently Any, not a
# real gap being masked.
import network
from asy_wifi_service import WIFI, asy_conn_time  # type: ignore[import-not-found]
from machine import Timer

from asy_udp_socket import AsyUDPSocket

# Mirrors asy_wifi_service.py's own _PHASE_STA_SEEKING/_PHASE_STA_ESTABLISHED/_PHASE_HOTSPOT/
# _PHASE_DEACTIVATED values, duplicated here rather than imported: those are micropython.const()-
# wrapped there (consistent with every other module-level constant in that file), and const()
# values are inlined at compile time and don't survive as real importable module attributes on this
# port (confirmed directly) - `from asy_wifi_service import _PHASE_HOTSPOT` raises ImportError. Keep
# these four literals in sync with asy_wifi_service.py's own definitions if those ever change.
_PHASE_STA_SEEKING = 0
_PHASE_STA_ESTABLISHED = 1
_PHASE_HOTSPOT = 2
_PHASE_DEACTIVATED = 3

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


_TMP_DIR = "tests/_tmp"
_next_dir = 0


def _remove_any(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        try:
            os.rmdir(path)
        except OSError:
            pass  # already gone, or genuinely not removable - not this helper's problem


def _tmp_cfg_dir() -> str:
    # Same one-fresh-directory-per-call approach as test_asy_ntp_client.py's own _tmp_cfg_dir() -
    # asy_wifi_service names its own config file unconditionally ("config_WIFI.cfg", from
    # base_classes.py's SensorReaderConfig), so a fresh directory is what isolates tests from each
    # other, not a distinct filename.
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass  # already exists
    _next_dir += 1
    path = _TMP_DIR + "/wifi_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass  # already exists from a stale previous run
    _remove_any(path + "/config_WIFI.cfg")  # clear any stale leftover (file or directory) from a previous run
    return path + "/"


class FakeLED:
    # Structurally satisfies asy_wifi_service.py's own LEDControl Protocol (on/off/toggle) without
    # needing a real GPIO pin - same spirit as the fake network.WLAN this file also depends on.
    # raise_on models a genuinely misbehaving caller-injected ext_led (_led_on()/_led_off()/
    # _led_toggle() must degrade gracefully against this, not just a well-behaved LED).
    def __init__(self) -> None:
        self.on_calls = 0
        self.off_calls = 0
        self.toggle_calls = 0
        self.raise_on: dict[str, Exception] = {}

    def on(self) -> None:
        exc = self.raise_on.get("on")
        if exc is not None:
            raise exc
        self.on_calls += 1

    def off(self) -> None:
        exc = self.raise_on.get("off")
        if exc is not None:
            raise exc
        self.off_calls += 1

    def toggle(self) -> None:
        exc = self.raise_on.get("toggle")
        if exc is not None:
            raise exc
        self.toggle_calls += 1


class _RaiseOnArm:
    # Same technique as test_asy_ntp_client.py's own _RaiseOnArm - toggles tests/machine.py's
    # Timer.raise_on_arm (a shared class attribute) for the duration of the `with` block,
    # simulating real rp2 alarm-pool exhaustion (OSError(ENOMEM) from Timer.init()).
    def __enter__(self) -> "_RaiseOnArm":
        Timer.raise_on_arm = True
        return self

    def __exit__(self, *exc_info: "Any") -> None:
        Timer.raise_on_arm = False


def make_client(
    conn_fail_to_hotspot: int = 5,
    ext_led: "FakeLED | None" = None,
    wifi_refresh_sec: int = 5,
    hotspot_time_min: int = 5,
    max_i2c_err: int = 5,
    cfg_path: "str | None" = None,
    debug: "int | None" = None,
) -> asy_conn_time:
    if cfg_path is None:
        cfg_path = _tmp_cfg_dir()
    return asy_conn_time(
        conn_fail_to_hotspot=conn_fail_to_hotspot,
        led_pin=None,  # tests/machine.py's fake Pin doesn't accept the real Pin(..., value=0) kwarg
        # asy_wifi_service.py passes - every LED test below goes through ext_led instead, which
        # never constructs a real Pin.
        ext_led=ext_led,
        wifi_refresh_sec=wifi_refresh_sec,
        hotspot_time_min=hotspot_time_min,
        max_i2c_err=max_i2c_err,
        cfg_path=cfg_path,
        debug=debug,
    )


def make_client_with_json(json_text: str, **kwargs: "Any") -> asy_conn_time:
    cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_WIFI.cfg", "w") as f:
        f.write(json_text)
    return make_client(cfg_path=cfg_path, **kwargs)


def make_invalid_cfg_client() -> asy_conn_time:
    # A directory where ConfigManager expects a plain file - same technique as
    # test_asy_ntp_client.py's own make_invalid_cfg_client().
    cfg_path = _tmp_cfg_dir()
    os.mkdir(cfg_path + "config_WIFI.cfg")
    return make_client(cfg_path=cfg_path)


_VALID_JSON = (
    '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", '
    '"Hostname": "TestNode", "LedWifiOn": false}'
)


async def _tick(flag: "asyncio.ThreadSafeFlag", times: int = 1) -> None:
    for _ in range(times):
        flag.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)  # let one full loop iteration's awaits settle


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# __init__ / get_task_starters / get_timer_starters (DRIVER_SPEC.md section 9)
# ---------------------------------------------------------------------------


def test_init_creates_an_sta_mode_wlan_by_default() -> None:
    client = make_client()
    assert client.wlan.if_id == network.STA_IF


def test_init_creates_its_own_config_file_with_schema_defaults() -> None:
    client = make_client()
    values = run(client.cfgmgr.get_dict(["SSID", "PW", "Country", "Hostname", "LedWifiOn"]))
    assert values == {"SSID": "", "PW": "", "Country": "DE", "Hostname": "SensorNode", "LedWifiOn": True}


def test_get_task_starters_returns_wlan_connect_and_uptime_counter() -> None:
    client = make_client()
    starters = client.get_task_starters()
    assert starters == [client.start_asy_wlan_connect, client.start_asy_uptime_counter]


def test_get_timer_starters_returns_the_counter_timer() -> None:
    client = make_client()
    assert client.get_timer_starters() == [client.start_counter_timer]


def test_start_counter_timer_arms_periodic_1s() -> None:
    client = make_client()
    client.start_counter_timer()
    assert client.counter_timer.mode == Timer.PERIODIC
    assert client.counter_timer.period == 1000


def test_start_counter_timer_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    client = make_client()
    with _RaiseOnArm():
        client.start_counter_timer()  # must not raise despite the timer failing to arm
    assert client.counter_timer.period == -1  # never actually armed


def test_debug_level_propagates_to_the_inherited_pr_logger() -> None:
    client = make_client(debug=3)
    assert client.pr.get_level() == 3


# ---------------------------------------------------------------------------
# get_dict_cfg / get_error_counter - the base-class getter quartet (DRIVER_SPEC.md section 4.2)
# ---------------------------------------------------------------------------


def test_get_dict_cfg_masks_the_password() -> None:
    # sensortask-wozi.py's existing /net/config route already masks PW before returning it - proves
    # _mask_pw()'s callback-overlay keeps that same masking in the generic getter-quartet path.
    client = make_client_with_json(_VALID_JSON)
    result = run(client.get_dict_cfg())
    assert result["WIFI"]["PW"] == "********"
    assert result["WIFI"]["SSID"] == "MyNetwork"


# ---------------------------------------------------------------------------
# Configuration: every valid field, and single/multiple invalid recombinations coming from a real
# on-disk config_WIFI.cfg file, exercised through the real ConfigManager asy_wifi_service now owns
# internally (not mocked) - proving asy_wifi_service.py's own handling of ConfigManager's per-field
# defaulting, not re-testing ConfigManager's own contract (already covered by test_config_manager.py).
# get_dict_cfg()'s own PW-masking (_mask_pw()) hides the real underlying value regardless of
# validity, so these read the raw cached value via client.cfgmgr.get_dict([...]) instead - the same
# level test_asy_ntp_client.py's own config-matrix tests exercise through _get_ntp_config().
# ---------------------------------------------------------------------------

_WIFI_KEYS = ["SSID", "PW", "Country", "Hostname", "LedWifiOn"]
_WIFI_DEFAULTS = {"SSID": "", "PW": "", "Country": "DE", "Hostname": "SensorNode", "LedWifiOn": True}


def test_config_all_fields_valid_reads_real_values() -> None:
    client = make_client_with_json(_VALID_JSON)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values == {
        "SSID": "MyNetwork",
        "PW": "supersecret",
        "Country": "US",
        "Hostname": "TestNode",
        "LedWifiOn": False,
    }


def test_config_ssid_empty_is_valid_not_defaulted() -> None:
    # SSID's own schema min is relaxed to 0 (see asy_wifi_service.py's own schema comment) so the
    # fresh, unconfigured default ("") self-validates - unlike every other str field here.
    json_text = '{"SSID": "", "PW": "supersecret", "Country": "US", "Hostname": "TestNode", "LedWifiOn": false}'
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values["SSID"] == ""
    assert values["PW"] == "supersecret"  # untouched


def test_config_ssid_too_long_falls_back_to_default_ssid_only() -> None:
    json_text = (
        '{"SSID": "' + ("x" * 33) + '", "PW": "supersecret", "Country": "US", '
        '"Hostname": "TestNode", "LedWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values["SSID"] == ""  # defaulted (max 32)
    assert values["PW"] == "supersecret"  # untouched


def test_config_pw_too_long_falls_back_to_default_pw_only() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "' + ("x" * 64) + '", "Country": "US", '
        '"Hostname": "TestNode", "LedWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values["PW"] == ""  # defaulted (max 63)
    assert values["SSID"] == "MyNetwork"  # untouched


def test_config_country_too_long_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "USA", '
        '"Hostname": "TestNode", "LedWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values["Country"] == "DE"


def test_config_country_too_short_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "U", '
        '"Hostname": "TestNode", "LedWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values["Country"] == "DE"


def test_config_country_wrong_type_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": 12345, '
        '"Hostname": "TestNode", "LedWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values["Country"] == "DE"


def test_config_hostname_empty_falls_back_to_default() -> None:
    json_text = '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", "Hostname": "", "LedWifiOn": false}'
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values["Hostname"] == "SensorNode"  # min 1


def test_config_hostname_too_long_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", '
        '"Hostname": "' + ("h" * 64) + '", "LedWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values["Hostname"] == "SensorNode"  # max 32


def test_config_hostname_one_over_the_real_max_falls_back_to_default() -> None:
    # 33 chars - just past network.hostname()'s real, documented 32-character hard cap
    # (MICROPY_PY_NETWORK_HOSTNAME_MAX_LEN, confirmed against extmod/modnetwork.c on both the
    # deployed v1.26.0 pin and the v1.28.0 refactor target). _VAL_HOST's schema max was narrowed to
    # match this real constraint - see BACKLOG.md - so this must now be rejected at config-validation
    # time instead of reaching network.hostname() and raising there.
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", '
        '"Hostname": "' + ("h" * 33) + '", "LedWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values["Hostname"] == "SensorNode"


def test_config_hostname_at_the_real_max_is_accepted() -> None:
    # The boundary value itself (32 chars) must be accepted, not rejected.
    name = "h" * 32
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", '
        '"Hostname": "' + name + '", "LedWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values["Hostname"] == name


def test_config_led_wifi_on_wrong_type_falls_back_to_default() -> None:
    json_text = (
        '{"SSID": "MyNetwork", "PW": "supersecret", "Country": "US", '
        '"Hostname": "TestNode", "LedWifiOn": "true"}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values["LedWifiOn"] is True  # a JSON string isn't a real bool - defaulted


def test_config_multiple_invalid_fields_each_fall_back_independently() -> None:
    json_text = (
        '{"SSID": "' + ("x" * 33) + '", "PW": "supersecret", "Country": 12345, '
        '"Hostname": "TestNode", "LedWifiOn": false}'
    )
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values["SSID"] == ""  # defaulted
    assert values["PW"] == "supersecret"  # untouched
    assert values["Country"] == "DE"  # defaulted
    assert values["Hostname"] == "TestNode"  # untouched
    assert values["LedWifiOn"] is False  # untouched


def test_config_all_fields_invalid_falls_back_to_every_default() -> None:
    json_text = '{"SSID": null, "PW": 12345, "Country": "", "Hostname": null, "LedWifiOn": "nope"}'
    client = make_client_with_json(json_text)
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values == _WIFI_DEFAULTS


def test_config_missing_file_uses_every_default() -> None:
    client = make_client()  # fresh directory - no config_WIFI.cfg written, so every default applies
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values == _WIFI_DEFAULTS


def test_config_non_dict_json_uses_every_default() -> None:
    client = make_client_with_json("[1, 2, 3]")
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values == _WIFI_DEFAULTS


def test_config_malformed_json_syntax_uses_every_default() -> None:
    client = make_client_with_json("{not json at all")
    values = run(client.cfgmgr.get_dict(_WIFI_KEYS))
    assert values == _WIFI_DEFAULTS


def test_config_returns_none_when_config_manager_itself_is_invalid() -> None:
    client = make_invalid_cfg_client()
    assert client.cfgmgr.valid is False
    assert run(client.cfgmgr.get_dict(_WIFI_KEYS)) is None


def test_get_dict_cfg_returns_schema_defaults_wrapped_in_wifi_key() -> None:
    # PW comes back "********" even though the real cached default is "" - _mask_pw()'s callback
    # overlay is unconditional, confirmed directly (see test_get_dict_cfg_masks_the_password above).
    client = make_client()
    result = run(client.get_dict_cfg())
    expected = dict(_WIFI_DEFAULTS)
    expected["PW"] = "********"
    assert result == {"WIFI": expected}


def test_get_dict_cfg_returns_all_none_values_when_config_manager_is_invalid() -> None:
    # PW is still "********", not None - _mask_pw()'s callback overlay runs unconditionally,
    # regardless of whether the underlying ConfigManager itself is valid (confirmed directly).
    client = make_invalid_cfg_client()
    result = run(client.get_dict_cfg())
    expected: dict[str, str | None] = {key: None for key in _WIFI_KEYS}
    expected["PW"] = "********"
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
# regression test: an earlier replace_all edit this session accidentally overwrote its body with a
# call to itself (infinite recursion) - a plain call+assert already catches that regression, since
# a recursive _led_off() would blow the interpreter's recursion limit instead of returning cleanly.
# ---------------------------------------------------------------------------


def test_led_on_is_a_noop_when_no_led_selected() -> None:
    client = make_client()
    client._led_on()  # must not raise despite self.led being None


def test_led_off_is_a_noop_when_no_led_selected() -> None:
    client = make_client()
    client._led_off()  # must not raise despite self.led being None


def test_led_toggle_is_a_noop_when_no_led_selected() -> None:
    client = make_client()
    client._led_toggle()  # must not raise despite self.led being None


def test_set_wifi_led_true_selects_the_ext_led_when_no_gpio_pin() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(True))
    assert client.led is led


def test_led_on_calls_the_selected_leds_on() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(True))
    client._led_on()
    assert led.on_calls == 1


def test_led_off_calls_the_selected_leds_off_and_does_not_recurse() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(True))
    client._led_off()
    assert led.off_calls == 1
    assert led.on_calls == 0


def test_led_toggle_calls_the_selected_leds_toggle() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(True))
    client._led_toggle()
    assert led.toggle_calls == 1


def test_set_wifi_led_false_turns_the_led_off_and_clears_it() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(True))
    run(client.set_wifi_led(False))
    assert led.off_calls == 1
    assert client.led is None


def test_led_on_degrades_gracefully_when_a_misbehaving_ext_led_raises() -> None:
    # self.led can be a caller-injected ext_led, not necessarily a real, never-raising Pin - a
    # broken implementation must not crash whatever caller happened to touch the LED (e.g.
    # wlan_connect()'s own startup path, see BACKLOG.md).
    led = FakeLED()
    led.raise_on["on"] = RuntimeError("simulated misbehaving ext_led")
    client = make_client(ext_led=led)
    run(client.set_wifi_led(True))
    client._led_on()  # must not raise


def test_led_off_degrades_gracefully_when_a_misbehaving_ext_led_raises() -> None:
    led = FakeLED()
    led.raise_on["off"] = RuntimeError("simulated misbehaving ext_led")
    client = make_client(ext_led=led)
    run(client.set_wifi_led(True))
    client._led_off()  # must not raise


def test_led_toggle_degrades_gracefully_when_a_misbehaving_ext_led_raises() -> None:
    led = FakeLED()
    led.raise_on["toggle"] = RuntimeError("simulated misbehaving ext_led")
    client = make_client(ext_led=led)
    run(client.set_wifi_led(True))
    client._led_toggle()  # must not raise


# ---------------------------------------------------------------------------
# _release_wifi_lock() - replaces 7 duplicated try/except RuntimeError blocks
# ---------------------------------------------------------------------------


def test_release_wifi_lock_releases_a_held_lock() -> None:
    client = make_client()
    run(client.wifi_mode_lock.acquire())
    client._release_wifi_lock()
    assert not client.wifi_mode_lock.locked()


def test_release_wifi_lock_is_a_noop_when_already_released() -> None:
    client = make_client()
    client._release_wifi_lock()  # must not raise
    assert not client.wifi_mode_lock.locked()


# ---------------------------------------------------------------------------
# get_data()/get_dict_data() - the cached-reading convention: backed by time_counter()'s 1Hz push
# (_update_wifi_snapshot()), not a live lock-aware query - see get_data()'s own comment on why.
# ---------------------------------------------------------------------------


def test_get_data_reflects_the_initial_never_connected_state() -> None:
    client = make_client()
    data = run(client.get_data())
    assert data.Mode is None
    assert data.Connected is None
    assert data.IP is None


def test_get_data_returns_the_cached_snapshot_not_a_live_query() -> None:
    client = make_client()
    run(client._set_meas_data(WIFI("STA", True, "10.0.0.5", 12345)))
    data = run(client.get_data())
    assert data == WIFI("STA", True, "10.0.0.5", 12345)


def test_get_dict_data_wraps_get_data_under_the_wifi_key() -> None:
    client = make_client()
    run(client._set_meas_data(WIFI("AP", False, None, 999)))
    dict_data = run(client.get_dict_data())
    assert dict_data == {"WIFI": {"Mode": "AP", "Connected": False, "IP": None, "TS": 999}}


# ---------------------------------------------------------------------------
# _update_wifi_snapshot() - builds the cached WIFI tuple time_counter() pushes once per tick
# ---------------------------------------------------------------------------


def test_update_wifi_snapshot_sta_mode_reports_ip_from_ifconfig() -> None:
    client = make_client()
    client.wlan._ifconfig = ("192.168.1.42", "255.255.255.0", "192.168.1.1", "8.8.8.8")
    run(client._update_wifi_snapshot(True))
    data = run(client.get_data())
    assert data.Mode == "STA"
    assert data.Connected is True
    assert data.IP == "192.168.1.42"


def test_update_wifi_snapshot_hotspot_mode_reports_ap() -> None:
    client = make_client()
    client._conn_phase = _PHASE_HOTSPOT
    run(client._update_wifi_snapshot(True))
    data = run(client.get_data())
    assert data.Mode == "AP"


def test_update_wifi_snapshot_degrades_to_none_ip_when_ifconfig_raises() -> None:
    client = make_client()
    client.wlan.raise_on["ifconfig"] = OSError("simulated ifconfig failure")
    run(client._update_wifi_snapshot(False))  # must not raise
    data = run(client.get_data())
    assert data.IP is None
    assert data.Connected is False


# ---------------------------------------------------------------------------
# time_counter() - short-circuits while wlan_deactivated, pushes a fresh snapshot every tick
# otherwise, and drives wifi_uptime off the real connection state
# ---------------------------------------------------------------------------


def test_time_counter_short_circuits_and_zeroes_uptime_while_deactivated() -> None:
    client = make_client()
    client._conn_phase = _PHASE_DEACTIVATED

    async def scenario() -> "tuple[int, Any]":
        task = asyncio.create_task(client.time_counter())
        await _tick(client.time_counter_trigger_event, 2)
        uptime = await client.get_wifi_uptime()
        data = await client.get_data()
        await _cancel(task)
        return uptime, data.Connected

    uptime, connected = run(scenario())
    assert uptime == 0
    assert connected is False


def test_time_counter_increments_uptime_while_connected() -> None:
    client = make_client()
    client.wlan._status = network.STAT_GOT_IP

    async def scenario() -> int:
        task = asyncio.create_task(client.time_counter())
        await _tick(client.time_counter_trigger_event, 3)
        uptime = await client.get_wifi_uptime()
        await _cancel(task)
        return uptime  # type: ignore[no-any-return]  # client: Any, see module note near line 8

    assert run(scenario()) == 3


def test_time_counter_resets_uptime_while_not_connected() -> None:
    client = make_client()
    client.wlan._status = network.STAT_IDLE

    async def scenario() -> int:
        task = asyncio.create_task(client.time_counter())
        await _tick(client.time_counter_trigger_event, 2)
        uptime = await client.get_wifi_uptime()
        await _cancel(task)
        return uptime  # type: ignore[no-any-return]  # client: Any, see module note near line 8

    assert run(scenario()) == 0


# ---------------------------------------------------------------------------
# Observation-tier helpers: a status/isconnected/ifconfig *query* failing degrades silently
# (returns a safe sentinel) instead of raising or feeding get_error_counter()
# ---------------------------------------------------------------------------


def test_wlan_status_or_none_returns_the_real_status() -> None:
    client = make_client()
    client.wlan._status = network.STAT_CONNECTING
    assert client._wlan_status_or_none() == network.STAT_CONNECTING


def test_wlan_status_or_none_returns_none_on_exception() -> None:
    client = make_client()
    client.wlan.raise_on["status"] = OSError("simulated")
    assert client._wlan_status_or_none() is None


def test_wlan_isconnected_or_false_returns_false_on_exception() -> None:
    client = make_client()
    client.wlan.raise_on["isconnected"] = OSError("simulated")
    assert client._wlan_isconnected_or_false() is False


def test_get_wlan_ifconfig_returns_none_while_mode_lock_held() -> None:
    client = make_client()
    run(client.wifi_mode_lock.acquire())
    assert client.get_wlan_ifconfig() is None
    client._release_wifi_lock()


def test_get_wlan_ifconfig_returns_none_on_exception() -> None:
    client = make_client()
    client.wlan.raise_on["ifconfig"] = OSError("simulated")
    assert client.get_wlan_ifconfig() is None


def test_get_wlan_ifconfig_returns_the_real_tuple_on_success() -> None:
    client = make_client()
    client.wlan._ifconfig = ("10.0.0.1", "255.255.255.0", "10.0.0.254", "8.8.8.8")
    assert client.get_wlan_ifconfig() == ("10.0.0.1", "255.255.255.0", "10.0.0.254", "8.8.8.8")


def test_network_available_true_only_in_sta_mode_with_an_ip() -> None:
    client = make_client()
    client._conn_phase = _PHASE_STA_SEEKING
    client.wlan._status = network.STAT_GOT_IP
    assert client.network_available() is True


def test_network_available_false_in_hotspot_mode_even_with_an_ip() -> None:
    client = make_client()
    client._conn_phase = _PHASE_HOTSPOT
    client.wlan._status = network.STAT_GOT_IP
    assert client.network_available() is False


def test_network_available_false_on_a_status_exception() -> None:
    client = make_client()
    client._conn_phase = _PHASE_STA_SEEKING
    client.wlan.raise_on["status"] = OSError("simulated")
    assert client.network_available() is False  # degrades via _wlan_status_or_none(), not a raise


# ---------------------------------------------------------------------------
# get_wlan_rssi() / wlan_isconnected() / reconnect_wifi() - previously untested public accessors
# ---------------------------------------------------------------------------


def test_get_wlan_rssi_returns_none_while_mode_lock_held() -> None:
    client = make_client()
    run(client.wifi_mode_lock.acquire())
    assert client.get_wlan_rssi() is None
    client._release_wifi_lock()


def test_get_wlan_rssi_returns_the_real_value_on_success() -> None:
    client = make_client()
    client.wlan._rssi = -42
    assert client.get_wlan_rssi() == -42


def test_get_wlan_rssi_degrades_gracefully_on_exception() -> None:
    # Real rp2/cyw43 raises ValueError("STA required") when queried outside STA mode (confirmed
    # against extmod/network_cyw43.c) - a routine, expected failure while hotspot_mode is active.
    client = make_client()
    client.wlan.raise_on["status"] = ValueError("STA required")
    assert client.get_wlan_rssi() is None


def test_wlan_isconnected_returns_false_while_mode_lock_held() -> None:
    client = make_client()
    client.wlan._connected = True
    run(client.wifi_mode_lock.acquire())
    assert client.wlan_isconnected() is False
    client._release_wifi_lock()


def test_wlan_isconnected_returns_the_real_value_when_unlocked() -> None:
    client = make_client()
    client.wlan._connected = True
    assert client.wlan_isconnected() is True


def test_reconnect_wifi_sets_the_trigger_and_tears_down_hotspot_bookkeeping() -> None:
    client = make_client(hotspot_time_min=1)
    client._hotspot_client_absent()  # arms hotspot_timer + starts a real ledflash task

    async def scenario() -> "tuple[bool, bool, bool]":
        await asyncio.sleep(0)
        ledflash_before = client.ledflash
        client.reconnect_wifi()
        ledflash_cleared = (ledflash_before is not None) and (client.ledflash is None)
        assert ledflash_before is not None
        await _cancel(ledflash_before)  # let the cancellation actually settle
        return client.reconn_wifi, client.hotspot_timer_running, ledflash_cleared

    reconn, timer_running, ledflash_cleared = run(scenario())
    assert reconn is True
    assert timer_running is False
    assert ledflash_cleared is True


# ---------------------------------------------------------------------------
# _hotspot_client_connected() / _hotspot_client_absent() - the hotspot auto-shutoff timer
# ---------------------------------------------------------------------------


def test_hotspot_client_connected_stops_the_shutoff_timer_and_turns_the_led_on() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(True))
    client.hotspot_timer.init(period=5000, mode=Timer.ONE_SHOT, callback=lambda b: None)
    client._hotspot_client_connected()
    assert client.hotspot_timer.deinit_called is True
    assert led.on_calls == 1


def test_hotspot_client_absent_arms_the_shutoff_timer_once() -> None:
    client = make_client(hotspot_time_min=1)
    client._hotspot_client_absent()
    assert client.hotspot_timer_running is True
    assert client.hotspot_timer.mode == Timer.ONE_SHOT
    assert client.hotspot_timer.period == 60000  # hotspot_time_min=1 -> 60000ms


def test_hotspot_client_absent_shutoff_timer_fires_reconnect() -> None:
    client = make_client(hotspot_time_min=1)
    client._hotspot_client_absent()

    async def scenario() -> bool:
        client.hotspot_timer.trigger()
        await asyncio.sleep(0)
        return client.reconn_wifi  # type: ignore[no-any-return]  # client: Any, see module note near line 10

    assert run(scenario()) is True


def test_hotspot_client_absent_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    client = make_client(hotspot_time_min=1)
    with _RaiseOnArm():
        client._hotspot_client_absent()  # must not raise despite the timer failing to arm
    assert client.hotspot_timer_running is False  # left False so the next cycle retries arming it


def test_hotspot_client_absent_starts_the_led_flash_task() -> None:
    client = make_client()

    async def scenario() -> None:
        client._hotspot_client_absent()
        assert client.ledflash is not None
        await _cancel(client.ledflash)

    run(scenario())


# ---------------------------------------------------------------------------
# "Attempt" operations - a mode switch, hotspot activation, a connect trigger, polling connect
# status, the disconnect-wait, permanent deactivation: each persists a real errno via pr.err_s()
# and sets self.hw_op_failed on a genuine exception, independent of connection_failures/
# conn_fail_to_hotspot's own AP-reachability-driven hotspot fallback.
# ---------------------------------------------------------------------------


def test_switch_wlan_mode_exception_sets_hw_op_failed_and_persists_errno_11() -> None:
    client = make_client()
    run(client.pr.setup())
    client.wlan.raise_on["disconnect"] = RuntimeError("simulated hardware fault")
    run(client._switch_wlan_mode(network.AP_IF))
    assert client.hw_op_failed is True
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 11
    assert counter["WIFI"]["ErrType"][-1] == "E"


def test_activate_hotspot_ap_exception_sets_hw_op_failed_and_persists_errno_12() -> None:
    client = make_client()
    run(client.pr.setup())
    client.wlan.raise_on["config"] = RuntimeError("simulated hardware fault")
    run(client._activate_hotspot_ap("DE", "TestHost"))
    assert client.hw_op_failed is True
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 12
    assert counter["WIFI"]["ErrType"][-1] == "E"


def test_activate_hotspot_ap_success_configures_and_activates_the_ap() -> None:
    client = make_client()

    async def scenario() -> None:
        await client._activate_hotspot_ap("US", "MyHost")
        assert client.hw_op_failed is False
        assert client.wlan._active is True
        assert {"essid": "MyHost", "password": "12345678"} in client.wlan.config_calls
        assert client.dns_server_task is not None
        await _cancel(client.dns_server_task)

    run(scenario())


def test_trigger_sta_connect_exception_sets_hw_op_failed_and_persists_errno_13() -> None:
    client = make_client()
    run(client.pr.setup())
    client.wlan.raise_on["connect"] = RuntimeError("simulated hardware fault")
    result = run(client._trigger_sta_connect("ssid", "pw", "DE", "host"))
    assert result is False
    assert client.hw_op_failed is True
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 13
    assert counter["WIFI"]["ErrType"][-1] == "E"


def test_trigger_sta_connect_success_returns_true_and_records_the_attempt() -> None:
    client = make_client()
    result = run(client._trigger_sta_connect("MySSID", "MyPW", "DE", "host"))
    assert result is True
    assert client.hw_op_failed is False
    assert client.wlan.connect_calls == [("MySSID", "MyPW")]
    assert client.wlan._active is True


def test_poll_sta_connect_status_exception_sets_hw_op_failed_and_persists_errno_14() -> None:
    client = make_client()
    run(client.pr.setup())
    client.wlan.raise_on["status"] = RuntimeError("simulated hardware fault")
    run(client._poll_sta_connect_status())
    assert client.hw_op_failed is True
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 14
    assert counter["WIFI"]["ErrType"][-1] == "E"


def test_poll_sta_connect_status_wrong_password_persists_wrnno_4() -> None:
    client = make_client()
    run(client.pr.setup())
    client.wlan._status = network.STAT_WRONG_PASSWORD
    run(client._poll_sta_connect_status())
    assert client.hw_op_failed is False  # a real connect outcome, not a hardware/driver failure
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 4
    assert counter["WIFI"]["ErrType"][-1] == "W"


def test_poll_sta_connect_status_no_ap_found_persists_wrnno_5() -> None:
    client = make_client()
    run(client.pr.setup())
    client.wlan._status = network.STAT_NO_AP_FOUND
    run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 5
    assert counter["WIFI"]["ErrType"][-1] == "W"


def test_poll_sta_connect_status_connect_fail_persists_wrnno_6() -> None:
    client = make_client()
    run(client.pr.setup())
    client.wlan._status = network.STAT_CONNECT_FAIL
    run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 6
    assert counter["WIFI"]["ErrType"][-1] == "W"


def test_poll_sta_connect_status_undefined_state_persists_wrnno_7() -> None:
    client = make_client()
    run(client.pr.setup())
    client.wlan._status = 12345  # not any real/defined network.STAT_* value
    run(client._poll_sta_connect_status())
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 7
    assert counter["WIFI"]["ErrType"][-1] == "W"


def test_disconnect_sta_and_wait_exception_sets_hw_op_failed_and_persists_errno_15() -> None:
    client = make_client()
    run(client.pr.setup())
    client.wlan.raise_on["disconnect"] = RuntimeError("simulated hardware fault")
    run(client._disconnect_sta_and_wait())
    assert client.hw_op_failed is True
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 15
    assert counter["WIFI"]["ErrType"][-1] == "E"


def test_disconnect_sta_and_wait_returns_immediately_when_already_disconnected() -> None:
    client = make_client()
    client.wlan._connected = False
    run(client._disconnect_sta_and_wait())
    assert client.hw_op_failed is False
    assert client.wlan.disconnect_called is True


def test_disconnect_sta_and_wait_times_out_instead_of_hanging_forever() -> None:
    # Real correctness proof for the bounded-loop fix: a driver that never confirms disconnection
    # (isconnected() always True) must not hang wlan_connect() forever - this genuinely runs the
    # full _STA_DISCONNECT_WAIT_ITERS(20) * 0.5s = 10s bound in real time (const() values are
    # compiled away, so there's no way to fast-forward this from the test side - see
    # tests/README.md's own note on this class of MicroPython behavior). The fake WLAN's own
    # disconnect() normally clears _connected as a side effect (modeling a real disconnect
    # completing immediately) - overridden here to a no-op so isconnected() keeps reporting True
    # throughout, genuinely simulating a driver that never confirms disconnection.
    client = make_client()
    run(client.pr.setup())
    client.wlan._connected = True
    client.wlan.disconnect = lambda: setattr(client.wlan, "disconnect_called", True)
    run(client._disconnect_sta_and_wait())
    assert client.hw_op_failed is True
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 18
    assert counter["WIFI"]["ErrType"][-1] == "E"


def test_deactivate_wlan_permanently_sets_state_even_when_the_hardware_call_raises() -> None:
    client = make_client()
    run(client.pr.setup())
    client._conn_phase = _PHASE_HOTSPOT
    client.wlan.raise_on["disconnect"] = RuntimeError("simulated hardware fault")
    run(client._deactivate_wlan_permanently())
    assert client._conn_phase == _PHASE_DEACTIVATED
    assert client.hw_op_failed is True
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 16
    assert counter["WIFI"]["ErrType"][-1] == "E"


# ---------------------------------------------------------------------------
# _print_wlan_diagnostics() / _on_sta_connected() / _on_sta_disconnected() /
# _register_sta_connection_failure() / _handle_sta_connection_result() - previously untested
# STA-mode connect/disconnect bookkeeping helpers
# ---------------------------------------------------------------------------


def test_print_wlan_diagnostics_does_not_raise_on_success() -> None:
    client = make_client(debug=5)  # PrintLog.level_info() - pr.all() actually prints, not gated off
    client.wlan._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "8.8.8.8")
    client._print_wlan_diagnostics()  # must not raise


def test_print_wlan_diagnostics_degrades_gracefully_when_ifconfig_raises() -> None:
    client = make_client(debug=5)
    client.wlan.raise_on["ifconfig"] = RuntimeError("simulated hardware fault")
    client._print_wlan_diagnostics()  # must not raise


def test_on_sta_connected_updates_state_and_turns_led_on() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(True))
    client.connection_failures = 3
    client._on_sta_connected()
    assert client._conn_phase == _PHASE_STA_ESTABLISHED
    assert client.connection_failures == 0
    assert led.on_calls == 1


def test_register_sta_connection_failure_increments_below_threshold() -> None:
    client = make_client(conn_fail_to_hotspot=3)
    run(client._register_sta_connection_failure())
    assert client.connection_failures == 1
    assert client._conn_phase == _PHASE_STA_SEEKING


def test_register_sta_connection_failure_switches_to_hotspot_at_threshold() -> None:
    client = make_client(conn_fail_to_hotspot=2)
    client.connection_failures = 1  # one below threshold already
    client.hotspot_started_once = False
    run(client._register_sta_connection_failure())
    assert client.connection_failures == 0
    assert client._conn_phase == _PHASE_HOTSPOT


def test_register_sta_connection_failure_deactivates_when_hotspot_already_tried() -> None:
    client = make_client(conn_fail_to_hotspot=2)
    run(client.pr.setup())
    client.connection_failures = 1
    client.hotspot_started_once = True
    run(client._register_sta_connection_failure())
    assert client._conn_phase == _PHASE_DEACTIVATED


def test_on_sta_disconnected_registers_failure_when_never_connected() -> None:
    client = make_client(conn_fail_to_hotspot=3)
    client._conn_phase = _PHASE_STA_SEEKING
    run(client._on_sta_disconnected())
    assert client.connection_failures == 1


def test_on_sta_disconnected_retries_after_a_minute_when_previously_connected() -> None:
    # _PHASE_STA_ESTABLISHED takes the "retry a previously-successful connection in one minute"
    # branch, which asyncio.sleep(60)s for real - proven by observing the task is still suspended
    # there (not finished, never reached _register_sta_connection_failure()) instead of paying the
    # full 60s wait, the same "prove the bound without waiting it out" approach
    # test_wlan_connect_never_gives_up_while_repeatedly_succeeding() already uses.
    client = make_client(conn_fail_to_hotspot=2)
    client._conn_phase = _PHASE_STA_ESTABLISHED

    async def scenario() -> bool:
        task = asyncio.create_task(client._on_sta_disconnected())
        for _ in range(10):
            await asyncio.sleep(0)
        still_running = not task.done()
        await _cancel(task)
        return still_running

    assert run(scenario()) is True
    assert client.connection_failures == 0  # never reached _register_sta_connection_failure()


def test_handle_sta_connection_result_connected_calls_on_sta_connected() -> None:
    client = make_client()
    client.wlan._connected = True
    run(client._handle_sta_connection_result())
    assert client._conn_phase == _PHASE_STA_ESTABLISHED


def test_handle_sta_connection_result_disconnected_calls_on_sta_disconnected() -> None:
    client = make_client(conn_fail_to_hotspot=3)
    client.wlan._connected = False
    client._conn_phase = _PHASE_STA_SEEKING
    run(client._handle_sta_connection_result())
    assert client.connection_failures == 1


# ---------------------------------------------------------------------------
# Missing-configuration warnings - a real, actionable reason now persists via pr.wrn_s() instead of
# vanishing into a debug-only print
# ---------------------------------------------------------------------------


def test_apply_initial_led_config_missing_config_persists_wrnno_1_and_deactivates() -> None:
    client = make_invalid_cfg_client()
    run(client.pr.setup())
    run(client._apply_initial_led_config())
    assert client._conn_phase == _PHASE_DEACTIVATED
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 1
    assert counter["WIFI"]["ErrType"][-1] == "W"


def test_apply_initial_led_config_valid_config_does_not_deactivate() -> None:
    client = make_client()
    run(client._apply_initial_led_config())
    assert client._conn_phase != _PHASE_DEACTIVATED


def test_start_hotspot_missing_config_persists_wrnno_2() -> None:
    client = make_invalid_cfg_client()
    run(client.pr.setup())

    async def fake_select(_mode: "Any") -> None:
        return None  # skips the real mode-switch dance (and its real asyncio.sleep()s) entirely

    client._select_wifi_mode = fake_select
    run(client._start_hotspot())
    assert client.hotspot_started_once is True
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 2
    assert counter["WIFI"]["ErrType"][-1] == "W"


def test_attempt_sta_connect_missing_config_persists_wrnno_3() -> None:
    client = make_invalid_cfg_client()
    run(client.pr.setup())
    run(client._attempt_sta_connect())
    assert client.wlan.connect_calls == []  # never reached the real connect attempt
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 3
    assert counter["WIFI"]["ErrType"][-1] == "W"


def test_attempt_sta_connect_empty_ssid_forces_immediate_hotspot_fallback() -> None:
    # Pre-existing behavior (not new this session), kept here because it's the one branch of
    # _attempt_sta_connect() the missing-config test above doesn't otherwise exercise.
    client = make_client(conn_fail_to_hotspot=5)  # default SSID is "" until configured
    run(client._attempt_sta_connect())
    assert client.connection_failures == 5


# ---------------------------------------------------------------------------
# _run_sta_mode() / _get_hotspot_stations() / _manage_hotspot_stations() / _run_hotspot_mode() /
# _leave_hotspot_mode() / _wait_for_sta_disconnect() / _handle_reconnect_trigger() - the
# orchestration layer around wlan_connect()'s main loop, previously only exercised indirectly
# through the full loop (with these helpers themselves faked out) or not at all.
# ---------------------------------------------------------------------------


def test_run_sta_mode_attempts_connect_when_not_connected() -> None:
    client = make_client()
    client.wlan._connected = False
    attempt_calls = [0]

    async def fake_attempt() -> None:
        attempt_calls[0] += 1

    client._attempt_sta_connect = fake_attempt
    run(client._run_sta_mode())
    assert attempt_calls[0] == 1
    assert client.wifi_mode_lock.locked() is False  # released despite the attempt being faked out


def test_run_sta_mode_skips_attempt_when_already_connected() -> None:
    client = make_client()
    client.wlan._connected = True
    attempt_calls = [0]

    async def fake_attempt() -> None:
        attempt_calls[0] += 1

    client._attempt_sta_connect = fake_attempt
    run(client._run_sta_mode())
    assert attempt_calls[0] == 0


def test_get_hotspot_stations_returns_the_real_list_on_success() -> None:
    client = make_client()
    client.wlan._stations = [(b"\xaa\xbb\xcc\xdd\xee\xff",)]
    stations = run(client._get_hotspot_stations())
    assert stations == [(b"\xaa\xbb\xcc\xdd\xee\xff",)]
    assert client.wifi_mode_lock.locked() is False


def test_get_hotspot_stations_degrades_to_empty_list_on_exception() -> None:
    client = make_client()
    client.wlan.raise_on["status"] = RuntimeError("simulated hardware fault")
    stations = run(client._get_hotspot_stations())
    assert stations == []
    assert client.wifi_mode_lock.locked() is False


def test_manage_hotspot_stations_with_a_client_connected_stops_the_shutoff_timer() -> None:
    client = make_client()
    client.wlan._stations = [(b"\xaa\xbb\xcc\xdd\xee\xff",)]
    client.hotspot_timer.init(period=5000, mode=Timer.ONE_SHOT, callback=lambda b: None)
    run(client._manage_hotspot_stations())
    assert client.hotspot_timer.deinit_called is True


def test_manage_hotspot_stations_with_no_client_arms_the_shutoff_timer() -> None:
    client = make_client(hotspot_time_min=1)
    client.wlan._stations = []
    run(client._manage_hotspot_stations())
    assert client.hotspot_timer_running is True


def test_run_hotspot_mode_starts_hotspot_when_no_ip_yet() -> None:
    client = make_client()
    client.wlan._status = network.STAT_IDLE
    start_calls = [0]

    async def fake_start() -> None:
        start_calls[0] += 1

    client._start_hotspot = fake_start
    run(client._run_hotspot_mode())
    assert start_calls[0] == 1


def test_run_hotspot_mode_manages_stations_once_ip_obtained() -> None:
    client = make_client()
    client.wlan._status = network.STAT_GOT_IP
    manage_calls = [0]

    async def fake_manage() -> None:
        manage_calls[0] += 1

    client._manage_hotspot_stations = fake_manage
    run(client._run_hotspot_mode())
    assert manage_calls[0] == 1


def test_leave_hotspot_mode_switches_back_to_sta_and_cancels_dns_task() -> None:
    client = make_client()
    client._conn_phase = _PHASE_HOTSPOT
    select_calls: list[Any] = []

    async def fake_select(mode: "Any") -> None:
        select_calls.append(mode)

    client._select_wifi_mode = fake_select

    async def _sleep_forever() -> None:
        # asyncio.create_task() requires a real coroutine object, not the awaitable
        # asyncio.sleep(...) itself returns on this port - confirmed directly ("TypeError:
        # coroutine expected") - so this thin async def wrapper is the fix, not a style choice.
        await asyncio.sleep(100)

    async def scenario() -> bool:
        client.dns_server_task = asyncio.create_task(_sleep_forever())
        await client._leave_hotspot_mode()
        return (client._conn_phase != _PHASE_HOTSPOT) and (client.dns_server_task is None)

    assert run(scenario()) is True
    assert select_calls == [network.STA_IF]


def test_wait_for_sta_disconnect_acquires_and_releases_the_lock() -> None:
    client = make_client()
    client.wlan._connected = False
    run(client._wait_for_sta_disconnect())
    assert client.wifi_mode_lock.locked() is False
    assert client.wlan.disconnect_called is True


def test_handle_reconnect_trigger_hotspot_mode_leaves_hotspot() -> None:
    client = make_client()
    client._conn_phase = _PHASE_HOTSPOT
    leave_calls = [0]

    async def fake_leave() -> None:
        leave_calls[0] += 1

    client._leave_hotspot_mode = fake_leave
    run(client._handle_reconnect_trigger())
    assert leave_calls[0] == 1
    assert client.reconn_wifi is False


def test_handle_reconnect_trigger_sta_mode_waits_for_disconnect() -> None:
    client = make_client()
    client._conn_phase = _PHASE_STA_SEEKING
    wait_calls = [0]

    async def fake_wait() -> None:
        wait_calls[0] += 1

    client._wait_for_sta_disconnect = fake_wait
    run(client._handle_reconnect_trigger())
    assert wait_calls[0] == 1


# ---------------------------------------------------------------------------
# _reset_wlan_connect_state() - runs once at the top of every wlan_connect() task (re)start: clears
# the per-run failure bookkeeping, preserves (rather than resets) _conn_phase when a restart
# happens to land mid-hotspot, and computes reconn_wifi from the (possibly preserved) phase plus
# the real WLAN driver state. Previously only exercised indirectly through wlan_connect()'s own
# tests below - these isolate it directly, including the hotspot-preserving asymmetry the
# _conn_phase refactor had to keep (see asy_wifi_service.py's own comment on this method).
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


def test_reset_wlan_connect_state_resets_deactivated_to_seeking() -> None:
    # A task restart (e.g. after the hw_op_failed streak gives up) pulls the state machine back out
    # of the terminal deactivated phase - matches the old code's unconditional wlan_deactivated=False
    # reset here.
    client = make_client()
    client._conn_phase = _PHASE_DEACTIVATED
    client._reset_wlan_connect_state()
    assert client._conn_phase == _PHASE_STA_SEEKING


def test_reset_wlan_connect_state_clears_failure_counters_and_hotspot_started_once() -> None:
    client = make_client()
    client.connection_failures = 3
    client.hotspot_started_once = True
    client._reset_wlan_connect_state()
    assert client.connection_failures == 0
    assert client.hotspot_started_once is False


def test_reset_wlan_connect_state_cancels_ledflash_and_dns_server_task() -> None:
    client = make_client()

    async def _sleep_forever() -> None:
        await asyncio.sleep(100)

    async def scenario() -> "tuple[bool, bool]":
        client.ledflash = asyncio.create_task(_sleep_forever())
        client.dns_server_task = asyncio.create_task(_sleep_forever())
        client._reset_wlan_connect_state()
        return client.ledflash is None, client.dns_server_task is None

    ledflash_cleared, dns_task_cleared = run(scenario())
    assert ledflash_cleared is True
    assert dns_task_cleared is True


def test_reset_wlan_connect_state_sets_reconn_wifi_true_when_hotspot() -> None:
    client = make_client()
    client._conn_phase = _PHASE_HOTSPOT
    client._reset_wlan_connect_state()
    assert client.reconn_wifi is True


def test_reset_wlan_connect_state_sets_reconn_wifi_true_when_already_connected() -> None:
    client = make_client()
    client.wlan._connected = True
    client._reset_wlan_connect_state()
    assert client.reconn_wifi is True


def test_reset_wlan_connect_state_sets_reconn_wifi_true_when_wlan_active_but_not_connected() -> None:
    client = make_client()
    client.wlan._active = True
    client._reset_wlan_connect_state()
    assert client.reconn_wifi is True


def test_reset_wlan_connect_state_sets_reconn_wifi_false_when_seeking_and_wlan_is_idle() -> None:
    client = make_client()
    client._reset_wlan_connect_state()
    assert client.reconn_wifi is False


def test_reset_wlan_connect_state_degrades_to_reconn_wifi_true_on_exception() -> None:
    # A real exception checking wlan.isconnected()/active() at task-start time is rare (once per
    # task (re)start) but must still force a safe reconnect-on-next-iteration default rather than
    # silently under-reacting.
    client = make_client()
    run(client.pr.setup())
    client.wlan.raise_on["isconnected"] = RuntimeError("simulated hardware fault")
    client._reset_wlan_connect_state()
    assert client.reconn_wifi is True


def test_reset_wlan_connect_state_turns_the_led_off() -> None:
    led = FakeLED()
    client = make_client(ext_led=led)
    run(client.set_wifi_led(True))
    client._led_on()
    client._reset_wlan_connect_state()
    assert led.off_calls == 1


# ---------------------------------------------------------------------------
# wlan_connect() - the task-supervisor entry point: pr.setup(), the fresh _err_cnt_internal streak,
# and max_i2c_err/_error_check() giving up after repeated WLAN-hardware-exception cycles
# (independent from, and a coarser safety net than, connection_failures/conn_fail_to_hotspot's own
# AP-reachability-driven hotspot fallback).
# ---------------------------------------------------------------------------


def test_wlan_connect_calls_pr_setup_before_entering_its_loop() -> None:
    client = make_client(wifi_refresh_sec=0)
    assert client.pr.initialized is False

    async def scenario() -> bool:
        task = asyncio.create_task(client.wlan_connect())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        initialized = client.pr.initialized
        await _cancel(task)
        return initialized  # type: ignore[no-any-return]  # client: Any - see module note near line 8

    assert run(scenario()) is True


def test_wlan_connect_resets_err_cnt_internal_at_the_start_of_every_run() -> None:
    client = make_client(wifi_refresh_sec=0)
    client._err_cnt_internal = 99

    async def scenario() -> int:
        task = asyncio.create_task(client.wlan_connect())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        streak = client._err_cnt_internal
        await _cancel(task)
        return streak  # type: ignore[no-any-return]  # client: Any - see module note near line 8

    assert run(scenario()) == 0


def test_wlan_connect_skips_the_state_machine_entirely_while_deactivated() -> None:
    client = make_client(wifi_refresh_sec=0)
    sta_calls = [0]

    async def fake_apply_led_cfg() -> None:
        client._conn_phase = _PHASE_DEACTIVATED  # simulates the missing-config path without a real cfg fault

    async def fake_run_sta_mode() -> None:
        sta_calls[0] += 1

    client._apply_initial_led_config = fake_apply_led_cfg
    client._run_sta_mode = fake_run_sta_mode

    async def scenario() -> int:
        task = asyncio.create_task(client.wlan_connect())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        calls = sta_calls[0]
        await _cancel(task)
        return calls

    assert run(scenario()) == 0


def test_wlan_connect_dispatches_to_hotspot_mode_when_conn_phase_is_hotspot() -> None:
    client = make_client(wifi_refresh_sec=0)
    client._conn_phase = _PHASE_HOTSPOT
    hotspot_calls = [0]
    sta_calls = [0]

    async def fake_reconnect() -> None:
        return None  # isolates this test to the phase-dispatch branch, not the reconnect-trigger path

    async def fake_hotspot() -> None:
        hotspot_calls[0] += 1

    async def fake_sta() -> None:
        sta_calls[0] += 1

    client._handle_reconnect_trigger = fake_reconnect
    client._run_hotspot_mode = fake_hotspot
    client._run_sta_mode = fake_sta

    async def scenario() -> "tuple[int, int]":
        task = asyncio.create_task(client.wlan_connect())
        for _ in range(4):
            await asyncio.sleep(0)
        calls = hotspot_calls[0], sta_calls[0]
        await _cancel(task)
        return calls

    hotspot_called, sta_called = run(scenario())
    assert hotspot_called >= 1
    assert sta_called == 0


def test_wlan_connect_dispatches_to_sta_mode_when_conn_phase_is_not_hotspot() -> None:
    client = make_client(wifi_refresh_sec=0)
    hotspot_calls = [0]
    sta_calls = [0]

    async def fake_hotspot() -> None:
        hotspot_calls[0] += 1

    async def fake_sta() -> None:
        sta_calls[0] += 1

    client._run_hotspot_mode = fake_hotspot
    client._run_sta_mode = fake_sta

    async def scenario() -> "tuple[int, int]":
        task = asyncio.create_task(client.wlan_connect())
        for _ in range(4):
            await asyncio.sleep(0)
        calls = hotspot_calls[0], sta_calls[0]
        await _cancel(task)
        return calls

    hotspot_called, sta_called = run(scenario())
    assert sta_called >= 1
    assert hotspot_called == 0


def test_wlan_connect_calls_handle_reconnect_trigger_when_reconn_wifi_is_set() -> None:
    # A task (re)start while the driver still reports connected forces reconn_wifi=True via
    # _reset_wlan_connect_state()'s own computation - wlan_connect()'s loop must act on that the
    # very first iteration, not just on ones following an explicit reconnect_wifi()/hotspot-timer
    # trigger.
    client = make_client(wifi_refresh_sec=0)
    client.wlan._connected = True
    reconnect_calls = [0]

    async def fake_reconnect() -> None:
        reconnect_calls[0] += 1
        client.reconn_wifi = False  # avoid retriggering every loop iteration

    async def fake_sta() -> None:
        return None

    client._handle_reconnect_trigger = fake_reconnect
    client._run_sta_mode = fake_sta

    async def scenario() -> int:
        task = asyncio.create_task(client.wlan_connect())
        for _ in range(4):
            await asyncio.sleep(0)
        calls = reconnect_calls[0]
        await _cancel(task)
        return calls

    assert run(scenario()) == 1


def test_wlan_connect_gives_up_after_repeated_hardware_failures_and_persists_errno_17() -> None:
    client = make_client(wifi_refresh_sec=0, max_i2c_err=2)

    async def failing_run_sta_mode() -> None:
        client.hw_op_failed = True  # simulates a real WLAN-hardware exception every cycle

    client._run_sta_mode = failing_run_sta_mode

    async def scenario() -> "Any":
        task = asyncio.create_task(client.wlan_connect())
        await asyncio.wait_for(task, 2.0)  # must actually complete, not loop forever
        return await client.get_error_counter()

    counter = run(scenario())
    assert counter["WIFI"]["ErrNum"][-1] == 17
    assert counter["WIFI"]["ErrType"][-1] == "E"


def test_wlan_connect_never_gives_up_while_repeatedly_succeeding() -> None:
    client = make_client(wifi_refresh_sec=0, max_i2c_err=2)

    async def succeeding_run_sta_mode() -> None:
        return None  # hw_op_failed stays False (reset every iteration by wlan_connect() itself)

    client._run_sta_mode = succeeding_run_sta_mode

    async def scenario() -> bool:
        task = asyncio.create_task(client.wlan_connect())
        for _ in range(10):
            await asyncio.sleep(0)
        still_running = not task.done()
        await _cancel(task)
        return still_running

    assert run(scenario()) is True


def test_wlan_connect_recovers_the_streak_on_alternating_failure_and_success() -> None:
    # Proves the give-up decision is a genuine streak, not a monotonic lifetime counter: a success
    # decrements _err_cnt_internal (base_classes.py's own _error_check() contract), so failures that
    # never land two-in-a-row must never trip max_i2c_err=2, however many cycles run in total.
    client = make_client(wifi_refresh_sec=0, max_i2c_err=2)
    toggle = [True]

    async def alternating_run_sta_mode() -> None:
        client.hw_op_failed = toggle[0]
        toggle[0] = not toggle[0]

    client._run_sta_mode = alternating_run_sta_mode

    async def scenario() -> bool:
        task = asyncio.create_task(client.wlan_connect())
        for _ in range(20):
            await asyncio.sleep(0)
        still_running = not task.done()
        await _cancel(task)
        return still_running

    assert run(scenario()) is True


# ===========================================================================
# Integration tests: real (not mocked) captive DNS server - downstream. _configure_hotspot_ap()
# starts a real DNSServer.run() task backed by a real AsyUDPSocket; driving it end-to-end proves
# how a genuine malformed/off-subnet UDP datagram is handled, not just the unit under test in
# isolation. DNSServer.__init__ hardcodes port 53 (privileged, no root in CI - same problem
# test_asy_ntp_client.py's own _RedirectGetaddrinfo works around for real port 123) - redirected
# here by swapping client.dns_server.udps for a fresh AsyUDPSocket on a free ephemeral port before
# ever starting the hotspot, since DNSServer.run() only ever touches self.udps, never rebuilds it.
# ===========================================================================

_next_port = 54000


def make_addr() -> "tuple[str, int]":
    global _next_port
    _next_port += 1
    # Same Unix-port-only workaround as test_asy_ntp_client.py's own make_addr(): a plain
    # (host, port) tuple is rejected by bind()/connect()/sendto() on this port's "standard" build.
    return socket.getaddrinfo("127.0.0.1", _next_port)[0][-1]  # type: ignore[return-value]


def _dns_query_packet(domain: str) -> bytes:
    # Minimal standard-query DNS packet DNSQuery.__init__ can parse: a 12-byte header (opcode bits
    # of byte 2 all zero -> "standard query"), then the QNAME as length-prefixed labels terminated
    # by a zero-length label, then a harmless QTYPE=A/QCLASS=IN (never read by this file's own
    # parsing, which stops once the QNAME's terminator is reached).
    header = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    qname = b"".join(bytes([len(label)]) + label.encode("ascii") for label in domain.split(".")) + b"\x00"
    return header + qname + b"\x00\x01\x00\x01"


async def _start_real_hotspot(client: asy_conn_time, server_addr: "tuple[str, int]") -> None:
    # Same-subnet own_ip/netmask as the test client's own loopback source address, so
    # DNSServer.run()'s subnet filter doesn't reject the test query as off-subnet.
    client.wlan._ifconfig = ("127.0.0.1", "255.255.255.0", "127.0.0.1", "127.0.0.1")
    client.dns_server.udps = AsyUDPSocket(server_addr, mode="server")
    await client._activate_hotspot_ap("US", "TestHost")


def test_integration_hotspot_captive_dns_ignores_a_malformed_packet_without_crashing() -> None:
    # "Interrupted packet" simulation: a datagram far too short to even contain a DNS header, sent
    # from a genuine second socket over a real loopback UDP round trip (not mocked) - proves the
    # whole real transport-to-parsing pipeline survives, not just DNSQuery in isolation.
    # DNSQuery.__init__'s own (IndexError, UnicodeError) guard already handles this.
    client = make_client()
    server_addr = make_addr()

    async def scenario() -> bool:
        await _start_real_hotspot(client, server_addr)
        try:
            cli = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            cli.setblocking(False)
            cli.sendto(b"\x01\x02", server_addr)  # 2 bytes - nowhere near a real 12-byte header
            await asyncio.sleep(0.3)  # give the server a moment to (not) respond
            poller = select.poll()
            poller.register(cli, select.POLLIN)
            got_a_reply = any(event & select.POLLIN for _fd, event in poller.ipoll(0))
            still_alive = not client.dns_server_task.done()  # the malformed packet didn't kill the task
            return (not got_a_reply) and still_alive
        finally:
            await _cancel(client.dns_server_task)

    assert run(scenario())


class _ScriptedUDPSocket:
    # Feeds a scripted sequence of (data, addr) pairs to DNSServer.run()'s real recvfrom() calls,
    # with addr as a genuine (host, port) tuple. Needed because this Unix port's own AsyUDPSocket,
    # once bound via a pre-resolved sockaddr (required for a real bind() to work at all here - see
    # make_addr()'s own comment), returns an *opaque raw sockaddr* from its own real recvfrom() in
    # this specific build, not a parseable (host, port) tuple - exactly the quirk captive_dns.py's
    # own on_subnet except-clause already anticipates and degrades gracefully against (confirmed
    # directly: a real two-socket round trip here gets every packet dropped as "unparseable
    # address", regardless of actual subnet match). This drives DNSServer.run()'s real subnet-check
    # and response-building code against a controlled, always-clean address shape instead, so the
    # accept/reject distinction is actually being tested, not just "every real packet gets dropped
    # here regardless of subnet".
    def __init__(self, script: "list[tuple[bytes, tuple[str, int]]]") -> None:
        self._script = list(script)
        self.sent: list[tuple[bytes, tuple[str, int]]] = []

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
    client.dns_server.udps = fake_udps

    async def scenario() -> None:
        task = asyncio.create_task(client.dns_server.run("192.168.4.1", "255.255.255.0"))
        for _ in range(100):
            if fake_udps.sent:
                break
            await asyncio.sleep_ms(10)
        await _cancel(task)

    run(scenario())
    assert len(fake_udps.sent) == 1
    reply, addr = fake_udps.sent[0]
    assert addr == ("192.168.4.55", 5353)
    assert reply[:2] == b"\x12\x34"  # echoes the query's own transaction ID
    assert reply[-4:] == bytes([192, 168, 4, 1])  # resolves to own_ip


def test_integration_hotspot_captive_dns_ignores_an_off_subnet_query() -> None:
    # A well-formed query from an address outside the AP's own subnet must be silently ignored (see
    # DNSServer.run()'s on_subnet check) - proves the filter, not just "any query gets answered".
    client = make_client()
    fake_udps = _ScriptedUDPSocket([(_dns_query_packet("test.example.com"), ("10.0.0.55", 5353))])
    client.dns_server.udps = fake_udps

    async def scenario() -> None:
        task = asyncio.create_task(client.dns_server.run("192.168.4.1", "255.255.255.0"))
        await asyncio.sleep(0.2)
        await _cancel(task)

    run(scenario())
    assert fake_udps.sent == []


# ===========================================================================
# Integration tests: the full wlan_connect() task driven end-to-end through the fake network.WLAN,
# proving how a real connect success/failure sequence propagates all the way up through
# get_data()/get_error_counter() and connection_failures/hotspot fallback - not just the unit under
# test in isolation. Mirrors test_asy_ntp_client.py's own integration-tests section.
# ===========================================================================


def test_integration_sta_connect_succeeds_and_propagates_to_get_data() -> None:
    # _poll_sta_connect_status() never returns early on STAT_GOT_IP (existing, unmodified
    # behavior - it keeps polling for its full 10 iterations regardless), so this genuinely runs
    # ~5s in real time; simulates a WLAN driver that reports a connection as already established
    # the instant connect() is called (connect_calls still records the real attempt). get_data()'s
    # cached snapshot is only ever pushed by time_counter()'s own task (see get_data()'s own
    # comment) - driven here alongside wlan_connect(), exactly like a real task-starter set would.
    client = make_client_with_json(_VALID_JSON, wifi_refresh_sec=0)
    original_connect = client.wlan.connect

    def fake_connect(ssid: str, pw: str) -> None:
        original_connect(ssid, pw)
        client.wlan._status = network.STAT_GOT_IP
        client.wlan._connected = True

    client.wlan.connect = fake_connect

    async def scenario() -> "tuple[bool, Any]":
        connect_task = asyncio.create_task(client.wlan_connect())
        counter_task = asyncio.create_task(client.time_counter())
        connected_once = False
        for _ in range(200):
            client.time_counter_trigger_event.set()
            await asyncio.sleep_ms(50)
            data = await client.get_data()
            if data.Connected:
                connected_once = client._conn_phase == _PHASE_STA_ESTABLISHED
                break
        await _cancel(connect_task)
        await _cancel(counter_task)
        return connected_once, (await client.get_data()).Connected

    connected_once, data_connected = run(scenario())
    assert connected_once is True
    assert data_connected is True


def test_integration_repeated_wrong_password_falls_back_to_hotspot_mode() -> None:
    client = make_client_with_json(_VALID_JSON, wifi_refresh_sec=0, conn_fail_to_hotspot=3)
    client.wlan._status = network.STAT_WRONG_PASSWORD  # every _poll_sta_connect_status() call sees this

    async def scenario() -> bool:
        task = asyncio.create_task(client.wlan_connect())
        for _ in range(100):
            if client._conn_phase == _PHASE_HOTSPOT:
                break
            await asyncio.sleep_ms(20)
        hotspot_reached = client._conn_phase == _PHASE_HOTSPOT
        await _cancel(task)
        return hotspot_reached  # type: ignore[no-any-return]  # client: Any, see module note near line 10

    assert run(scenario())


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
