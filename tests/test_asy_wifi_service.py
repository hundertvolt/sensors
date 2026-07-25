import sys

sys.path.insert(0, "improved-quality")  # not yet promoted to src/ - see CLAUDE.md

import asyncio
import os

# improved-quality/ isn't on mypy_path (only src/typings are - see pyproject.toml) since it's
# still WIP, not yet promoted; every asy_wifi_service-typed value below is consequently Any, not a
# real gap being masked.
import network
from asy_wifi_service import WIFI, asy_conn_time  # type: ignore[import-not-found]

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
    def __init__(self) -> None:
        self.on_calls = 0
        self.off_calls = 0
        self.toggle_calls = 0

    def on(self) -> None:
        self.on_calls += 1

    def off(self) -> None:
        self.off_calls += 1

    def toggle(self) -> None:
        self.toggle_calls += 1


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


def make_client_with_json(json_text: str) -> asy_conn_time:
    cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_WIFI.cfg", "w") as f:
        f.write(json_text)
    return make_client(cfg_path=cfg_path)


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
    client.hotspot_mode = True
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
    client.wlan_deactivated = True

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
    client.hotspot_mode = False
    client.wlan._status = network.STAT_GOT_IP
    assert client.network_available() is True


def test_network_available_false_in_hotspot_mode_even_with_an_ip() -> None:
    client = make_client()
    client.hotspot_mode = True
    client.wlan._status = network.STAT_GOT_IP
    assert client.network_available() is False


def test_network_available_false_on_a_status_exception() -> None:
    client = make_client()
    client.hotspot_mode = False
    client.wlan.raise_on["status"] = OSError("simulated")
    assert client.network_available() is False  # degrades via _wlan_status_or_none(), not a raise


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


def test_deactivate_wlan_permanently_sets_state_even_when_the_hardware_call_raises() -> None:
    client = make_client()
    run(client.pr.setup())
    client.hotspot_mode = True
    client.wlan.raise_on["disconnect"] = RuntimeError("simulated hardware fault")
    run(client._deactivate_wlan_permanently())
    assert client.wlan_deactivated is True
    assert client.hotspot_mode is False
    assert client.hw_op_failed is True
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 16
    assert counter["WIFI"]["ErrType"][-1] == "E"


# ---------------------------------------------------------------------------
# Missing-configuration warnings - a real, actionable reason now persists via pr.wrn_s() instead of
# vanishing into a debug-only print
# ---------------------------------------------------------------------------


def test_apply_initial_led_config_missing_config_persists_wrnno_1_and_deactivates() -> None:
    client = make_invalid_cfg_client()
    run(client.pr.setup())
    run(client._apply_initial_led_config())
    assert client.wlan_deactivated is True
    counter = run(client.get_error_counter())
    assert counter["WIFI"]["ErrNum"][-1] == 1
    assert counter["WIFI"]["ErrType"][-1] == "W"


def test_apply_initial_led_config_valid_config_does_not_deactivate() -> None:
    client = make_client()
    run(client._apply_initial_led_config())
    assert client.wlan_deactivated is False


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
        client.wlan_deactivated = True  # simulates the missing-config path without a real cfg fault

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


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
