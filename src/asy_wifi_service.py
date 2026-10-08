"""Async WiFi connection/hotspot/LED service. Not a sensor, but config-managed the same way: extends
asy_base_classes.py's SensorReaderConfig, owns its own config_WIFI.cfg (see SPECIFICATION.md Part C).
"""
# "Attempt" operations persist a real errno via self.pr.err_s() and set self._hw_op_failed, feeding
# _connect_loop()'s _error_check() streak; routine state observations stay print-only via self.pr.err()
# (SPECIFICATION.md C.7 lists every site; error numbers come from the one catalog, C.7.1).

import asyncio
from collections import namedtuple

import network
from machine import Timer
from micropython import const

from asy_base_classes import SensorReaderConfig, TickSeconds, arm_tick_timer, utc_now
from asy_captive_dns import CaptiveDNS
from asy_config_manager import INVALID, make_dict, name_cfg, schema_dict, schema_names
from asy_dns_client import host_label_ok
from asy_print_log import DEFAULT_LOG, LogConfig

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import NamedTuple, Protocol

    from asy_base_classes import ErrorSource, JsonMapping, TaskStarter, TimerStarter
    from asy_config_manager import CfgValue, ConfigSchema, FieldSchema, WriteValidity
    from asy_print_log import ErrorLog, PrintLogHistory

    # Structural Protocol for a caller-supplied LED (SPECIFICATION.md Part C.10's typing convention).
    class LEDControl(Protocol):
        def off(self) -> None: ...
        def on(self) -> None: ...
        def toggle(self) -> None: ...


# Codes from the global catalog (buildgen/error_catalog.json): the shared ones and WIFI's band.
_ERR_TIMER = const(17)
_ERR_BAD_ARG = const(21)
_ERR_TIMEOUT = const(22)
_ERR_UNEXPECTED = const(23)
_ERR_WLAN_MODE_SWITCH = const(60)
_ERR_WLAN_AP_START = const(61)
_ERR_WLAN_STA_START = const(62)
_ERR_WLAN_STA_POLL = const(63)
_ERR_WLAN_STA_DISCONNECT = const(64)
_ERR_WLAN_OFF = const(65)
_ERR_WLAN_GIVE_UP = const(66)
_WRN_STORED_DEFAULT = const(10)
_WRN_CFG_READ = const(13)
_WRN_WLAN_AUTH_FAILED = const(36)
_WRN_WLAN_NO_AP = const(37)
_WRN_WLAN_CONNECT_FAILED = const(38)
_WRN_WLAN_STATUS_UNKNOWN = const(39)
_WRN_WLAN_STATIONS_UNKNOWN = const(77)
_WRN_WLAN_STATUS_UNREADABLE = const(78)
_WRN_WLAN_TO_HOTSPOT = const(79)
_WRN_WLAN_DEACTIVATED = const(80)
_WRN_WLAN_NO_VERDICT = const(81)

# Schema tuples for ConfigManager.get_*_values().
# SSID: 0-32 octets (802.11's real range); 0 also doubles as this driver's "not configured yet"
# sentinel (routes to hotspot fallback, see _attempt_sta_connect()).
_VAL_SSID = const((("SSID", "str", "", 0, 32, None),))
# PW: real passphrase length is WPA2-PSK's 8-63 *when used* - special="" bypasses that for an
# intentionally open/unsecured network.
_VAL_PW = const((("PW", "str", "", 8, 63, ""),))
_VAL_COUNTRY = const((("Country", "str", "DE", 2, 2, None),))  # ISO 3166-1 alpha-2, checked by _country_ok()
_COUNTRY_CODE_LEN = const(2)  # alpha-2: the shape _country_ok() checks, inside _VAL_COUNTRY's own 2..2
_VAL_HOSTNAME = const((("Hostname", "str", "SensorNode", 1, 32, None),))  # 32 = network.hostname()'s real cap
_VAL_LED_WIFI_ON = const((("LEDWifiOn", "bool", True, None, None, None),))
# Hotspot AP password - real WPA2-PSK length (8-63), defaulting to the hardcoded "12345678": accepted
# permanently as a known limitation (owner, 2026-09-26; CLAUDE.md), made per-device configurable.
# Masked like _VAL_PW.
_VAL_HOTSPOT_PW = const((("HotspotPW", "str", "12345678", 8, 63, None),))

# @web-group section=networking submitGroup=identity label="Wi-Fi & Identity" submit=true submitLabel="Apply & Reconnect"
# @web SSID section=networking submitGroup=identity label="Wi-Fi SSID" bytes=true
# @web PW section=networking submitGroup=identity label="Wi-Fi Password" mask=true bytes=true special:""="Open network"
# @web Country section=networking submitGroup=identity label="Country" bytes=true shape=countryCode description="Two uppercase letters (ISO 3166-1 alpha-2), e.g. DE."
# @web Hostname section=networking submitGroup=identity label="Hostname" bytes=true shape=hostLabel
# @web HotspotPW section=networking submitGroup=identity label="Hotspot Password" mask=true bytes=true description="Password of the fallback hotspot (8-63 characters)."

# @web-group section=networking submitGroup=wifiLed label="Wi-Fi Status LED" submit=true
# @web LEDWifiOn section=networking submitGroup=wifiLed label="Wi-Fi Status LED"

_NAME = const("WIFI")
# Kept as a literal tuple inline (not `_FIELDS` below) because mypy's namedtuple plugin can only
# infer field names from a literal at the call site, not through a variable indirection.
WIFI = namedtuple("WIFI", ("Mode", "Connected", "IP", "Subnet", "Gateway", "DNS", "RSSI", "TS"))
_FIELDS = const(("Mode", "Connected", "IP", "Subnet", "Gateway", "DNS", "RSSI", "TS"))  # kept in sync with WIFI's own fields above


# The radio's own bounds are UTF-8 bytes, where the schema counts characters: country()/hostname()
# raise outside 2 / 32 bytes and connect() overflows past a 32-byte SSID (SPECIFICATION.md C.7.4).
_RADIO_FIELDS = schema_names(_VAL_SSID + _VAL_PW + _VAL_COUNTRY + _VAL_HOSTNAME + _VAL_HOTSPOT_PW)


def _country_ok(value: str) -> bool:
    # ISO 3166-1 alpha-2 in the cyw43 table's uppercase (cyw43_country.h:49)
    return len(value) == _COUNTRY_CODE_LEN and all("A" <= ch <= "Z" for ch in value)


def _radio_value_ok(field: "FieldSchema", value: object) -> bool:
    # Three checks once the schema's own character bounds hold (anything else stays its refusal): the
    # UTF-8 byte count within the max (never fewer bytes than characters), Hostname a host label, and
    # Country an uppercase alpha-2 pair.
    low, high = field[3], field[4]
    if type(value) is not str or value == field[5] or type(low) is not int or type(high) is not int or not low <= len(value) <= high:
        return True
    if len(value.encode()) > high:
        return False
    if field[0] == name_cfg(_VAL_HOSTNAME):
        return host_label_ok(value)
    if field[0] == name_cfg(_VAL_COUNTRY):
        return _country_ok(value)
    return True


def _with_default(schema: tuple[tuple[str, str, str, int, int, str | None], ...], value: str) -> tuple[tuple[str, str, str, int, int, str | None], ...]:
    # Substitutes a build-time per-device default into a one-field schema. Only the DEFAULT moves,
    # never the bounds, so a value a user already persisted still wins at boot.

    # A value outside the field's bounds or shape is dropped rather than installed: ConfigManager treats
    # an unsatisfiable default as an invalid config and answers None to every read, costing the device
    # its networking config. buildgen.validate refuses it at build time; this keeps it bootable.
    name, kind, _default, low, high, special = schema[0]
    if kind != "str" or not (low <= len(value) <= high) or not _radio_value_ok(schema[0], value):
        return schema  # a non-str field would be substituted unchecked - keep the built-in default
    return ((name, kind, value, low, high, special),)


# This service's one optional live cross-instance dependency (Parts C.14 and L.4): the status LED it
# drives, resolved from [device.wiring].led_target to an already-constructed NeopixelDriver and passed
# as ext_led at construction (the NeoPixel is built first).
# @wiring led_target NeopixelDriver ext_led optional kwarg

# Its other optional dependency: the FRAM error-log target, resolved from [device.wiring].fram_target
# implicitly because WifiService is mandatory infra, exactly as asy_system_service.py's own tag is.
# __init__ passes the log config to super().__init__() and to this service's CaptiveDNS.
# @wiring fram_target FRAMManager log optional kwarg

# @tunable wifi.sta_disconnect_wait_iters = 20
_STA_DISCONNECT_WAIT_ITERS = const(20)  # 20 * 0.5s = 10s max wait for isconnected() to clear -
# bounds _disconnect_sta_and_wait()'s loop; a real disconnect() completes far faster than this.
# @tunable wifi.sta_disconnect_poll_s = 0.5
_STA_DISCONNECT_POLL_S = const(0.5)  # one step of that wait
# @tunable wifi.sta_connect_poll_s = 0.5
_STA_CONNECT_POLL_S = const(0.5)  # one step of _poll_sta_connect_status()'s wait for a verdict
# @tunable wifi.sta_connect_poll_iters = 10
_STA_CONNECT_POLL_ITERS = const(10)  # its bound: 10 * 0.5s = 5s
# @tunable wifi.hotspot_stations_settle_s = 0.1
_HOTSPOT_STATIONS_SETTLE_S = const(0.1)  # before the stations query
# @tunable wifi.wlan_down_settle_s = 2
_WLAN_DOWN_SETTLE_S = const(2)  # after disconnect() + active(False), before deinit()
# @tunable wifi.wlan_deinit_settle_s = 1
_WLAN_DEINIT_SETTLE_S = const(1)  # after deinit(), before the new interface
# @tunable wifi.wlan_mode_settle_s = 1
_WLAN_MODE_SETTLE_S = const(1)  # after the new interface is created
# @tunable wifi.sta_retry_after_loss_s = 60
_STA_RETRY_AFTER_LOSS_S = const(60)  # retry a previously successful connection after one minute
# The flash patterns' (on, off) phases, each run by the one flash task (_run_led_pattern()).
# @tunable wifi.led_hotspot_on_s = 2.9
_LED_HOTSPOT_ON_S = const(2.9)  # the hotspot without a client: mostly lit
# @tunable wifi.led_hotspot_off_s = 0.1
_LED_HOTSPOT_OFF_S = const(0.1)
# @tunable wifi.led_hotspot_client_on_s = 1.5
_LED_HOTSPOT_CLIENT_ON_S = const(1.5)  # a station on the hotspot: an even slow blink
# @tunable wifi.led_hotspot_client_off_s = 1.5
_LED_HOTSPOT_CLIENT_OFF_S = const(1.5)
# @tunable wifi.led_deactivated_on_s = 0.1
_LED_DEACTIVATED_ON_S = const(0.1)  # deactivated: the hotspot pattern inverted, a short blink every 3 s
# @tunable wifi.led_deactivated_off_s = 2.9
_LED_DEACTIVATED_OFF_S = const(2.9)
# @tunable wifi.reconnect_caller_grace_s = 5
_RECONNECT_CALLER_GRACE_S = const(5)  # lets the triggering caller's own final tasks finish
# @tunable wifi.reconnect_settle_s = 3
_RECONNECT_SETTLE_S = const(3)  # after the reconnect, once, for whatever else to settle

# Expected field counts of the config reads and of WLAN.ifconfig()'s fixed 4-tuple, checked before
# unpacking so a short/missing config degrades instead of raising.
_HOTSPOT_CFG_FIELDS = const(3)  # _VAL_COUNTRY + _VAL_HOSTNAME + _VAL_HOTSPOT_PW
_STA_CFG_FIELDS = const(4)  # _VAL_SSID + _VAL_PW + _VAL_COUNTRY + _VAL_HOSTNAME
_IFCONFIG_FIELDS = const(4)  # (ip, netmask, gateway, dns)

# self._conn_phase - the connection state machine. Not importable as a module attribute once
# const()-folded (see tests/test_asy_wifi_service.py's own mirrored copy), same tradeoff as every
# constant here.
_PHASE_STA_SEEKING = const(0)  # STA mode, has not connected successfully since the last reset
_PHASE_STA_ESTABLISHED = const(1)  # STA mode, connected at least once since the last reset - live
# wlan.isconnected() still distinguishes "connected" from "disconnected, retrying every 60s".
_PHASE_HOTSPOT = const(2)  # AP/hotspot fallback mode active
_PHASE_DEACTIVATED = const(3)  # terminal - WLAN fully deactivated until a power cycle or reset; survives a task restart

# @tunable wifi.refresh_s = 5
_WIFI_REFRESH_S = const(5)  # _connect_loop()'s loop period between connection checks

_STAT_JOINED_NO_IP = const(2)  # cyw43 CYW43_LINK_NOIP (cyw43.h:100): joined, no IP yet; network exports no name for it (extmod/modnetwork.c:197-202, v1.29.0)
# CYW43_PM_VALUE(NO_POWERSAVE, 200, 1, 1, 10): power save off, PM_PERFORMANCE's listen fields
# (network_cyw43.c:43-52, v1.29.0); legacy's word.
_PM_NO_POWERSAVE = const(0xA11140)


# The device's [device] settings, passed whole by the generated module: hostname and hotspot
# password are the two persisted fields' build-time defaults (_with_default).
if TYPE_CHECKING:
    class WifiConfig(NamedTuple):
        hostname: str
        hotspot_password: str
        conn_fail_to_hotspot: int
        hotspot_time_min: int

else:
    WifiConfig = namedtuple("WifiConfig", ("hostname", "hotspot_password", "conn_fail_to_hotspot", "hotspot_time_min"))


class WifiService(SensorReaderConfig):
    def __init__(
        self,
        wifi: WifiConfig,
        ext_led: "LEDControl | None" = None,
        # @tunable module.max_error = 5
        max_module_error: int = 5,  # consecutive _hw_op_failed cycles before giving up and letting the
        # task supervisor restart this task - same _error_check() contract every Reader uses,
        # inherited from SensorReaderConfig (no I2C bus here, just the shared generic mechanism).
        cfg_path: str = "",
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        super().__init__(
            WIFI(None, None, None, None, None, None, None, None),
            _NAME,
            _VAL_SSID + _VAL_PW + _VAL_COUNTRY + _with_default(_VAL_HOSTNAME, wifi.hostname) + _VAL_LED_WIFI_ON + _with_default(_VAL_HOTSPOT_PW, wifi.hotspot_password),
            max_module_error=max_module_error,
            cfg_path=cfg_path,
            log=log,
        )
        self._wlan = network.WLAN(network.STA_IF)
        self._ext_led = ext_led
        self._led: LEDControl | None = None
        self._hotspot_time = 60000 * wifi.hotspot_time_min  # convert to ms
        self._conn_fail_to_hotspot = wifi.conn_fail_to_hotspot
        self._wifi_uptime = TickSeconds()
        self._wifi_connected = False
        self._dhcp_dns: str | None = None
        self._ap_selected = False
        # CaptiveDNS gets its own independent "DNSSRV"-named logger, not this class's own self.pr (owner, 2026-08-07) -
        # its history is shown with the networking data (owner, 2026-09-26).
        self._dns_server = CaptiveDNS(log=log)
        self._dns_server_task: asyncio.Task[None] | None = None
        self._reconn_wifi = False
        self._time_counter_trigger_event = asyncio.ThreadSafeFlag()
        self.wifi_mode_lock = asyncio.Lock()  # serialises every use of the CYW43 radio
        self._counter_timer = Timer()
        self._hotspot_timer = Timer()
        self._hotspot_timer_running = False
        self._hotspot_timeout_trigger_event = asyncio.ThreadSafeFlag()
        self._ledflash: asyncio.Task[None] | None = None
        self._led_pattern: tuple[float, float] | None = None  # the (on, off) pattern _ledflash runs
        # _connect_loop()'s own state machine - reset at the top of every _connect_loop() call
        # (i.e. every task (re)start), not meant to be read from outside this class.
        self._conn_phase = _PHASE_STA_SEEKING
        self._connection_failures = 0
        self._hotspot_started_once = False
        self._hw_op_failed = False  # this loop iteration's flag feeding _error_check(), see _connect_loop()
        self._tick_armed: bool | None = None  # the uptime tick's last arm; None until start_uptime_timer() ran
        # SSID/PW/Country/Hostname are persist-only (read fresh from cfgmgr each connection attempt);
        # LEDWifiOn is the one field with a real live push.
        self._push_callbacks[name_cfg(_VAL_LED_WIFI_ON)] = self._push_wifi_led

    async def _get_hotspot_stations(self) -> list[tuple[bytes]] | None:
        async with self.wifi_mode_lock:
            # Legacy's settle before the stations query (legacy/firmware/python/CommonDrivers/async_connect.py:258); cyw43 055d642 states no such need.
            # It stays: two flashes are not spent testing a harmless 100 ms wait (owner, 2026-10-05, paraphrase).
            await asyncio.sleep(_HOTSPOT_STATIONS_SETTLE_S)
            try:
                stations = self._wlan.status("stations")
                self.pr.all("Connected stations:", stations)
            except Exception as e:  # A failed query is unknown, never 'no client': None leaves the hotspot timer as it is (the caller persists it).
                self.pr.err("Could not fetch connected clients:", e)
                return None
            else:
                # The 1.29 stub types status(str) as int; "stations" returns a list of 1-tuples (network_cyw43.c:371-388).
                # Remove the ignore when the stub types it (warn_unused_ignores then flags it).
                return stations  # type: ignore[return-value]

    async def _set_mgr_cfg(self, data: "JsonMapping", cfg_vals: "ConfigSchema") -> "tuple[bool, WriteValidity]":
        # Refuses a radio value outside its byte bound or shape before it is stored (C.7.4); the rest of the
        # request goes through ConfigManager as usual.
        fields = schema_dict(cfg_vals)
        refused = [k for k, v in data.items() if k in _RADIO_FIELDS and k in fields and not _radio_value_ok(fields[k], v)]
        for key in refused:
            await self.pr.err_s("Refusing", key, "- outside the radio's accepted form", errno=_ERR_BAD_ARG)
        ok, results = await super()._set_mgr_cfg({k: v for k, v in data.items() if k not in refused}, cfg_vals)
        for key in refused:
            results[key] = INVALID
        return ok, results

    async def _activate_hotspot_ap(self, country: str, hostname: str, password: str) -> None:
        try:
            self._configure_hotspot_ap(country, hostname, password)
        except Exception as e:
            self._hw_op_failed = True
            await self.pr.err_s("Error activating hotspot AP:", e, errno=_ERR_WLAN_AP_START)

    async def _apply_initial_led_config(self) -> None:
        led_cfg = await self._read_wifi_led_cfg()
        if led_cfg is None:  # LEDWifiOn on its schema default (on), so the deactivated pattern shows
            await self.set_wifi_led(status=_VAL_LED_WIFI_ON[0][2])
            self._conn_phase = _PHASE_DEACTIVATED
            await self.pr.wrn_s("Missing WLAN configuration!", wrnno=_WRN_CFG_READ)
        else:
            await self.set_wifi_led(status=led_cfg)

    async def _attempt_sta_connect(self) -> None:
        self.pr.evt("Establishing WLAN connection")
        led_cfg = await self._read_wifi_led_cfg()
        await self.set_wifi_led(status=False if led_cfg is None else led_cfg)
        wifi_cfg = await self.cfgmgr.get_str_values(_VAL_SSID + _VAL_PW + _VAL_COUNTRY + _VAL_HOSTNAME)
        if wifi_cfg is None or len(wifi_cfg) != _STA_CFG_FIELDS:
            await self.pr.wrn_s("Missing WLAN configuration!", wrnno=_WRN_CFG_READ)
            return
        ssid, pw, country, hostname = await self._radio_values(wifi_cfg, _VAL_SSID + _VAL_PW + _VAL_COUNTRY + _VAL_HOSTNAME)
        if ssid == "":  # No SSID: nothing to attempt, so no failure streak - straight back to the hotspot.
            self._connection_failures = 0
            self._conn_phase = _PHASE_HOTSPOT
            self.pr.evt("No SSID configured, hotspot mode")
            return
        if await self._trigger_sta_connect(ssid, pw, country, hostname):
            await self._poll_sta_connect_status()

    async def _bring_up_hotspot_ap(self) -> None:
        async with self.wifi_mode_lock:
            led_cfg = await self._read_wifi_led_cfg()
            wifi_cfg = await self.cfgmgr.get_str_values(_VAL_COUNTRY + _VAL_HOSTNAME + _VAL_HOTSPOT_PW)
            if wifi_cfg is None or led_cfg is None or len(wifi_cfg) != _HOTSPOT_CFG_FIELDS:
                await self.pr.wrn_s("Missing WLAN configuration!", wrnno=_WRN_CFG_READ)
                await self.set_wifi_led(status=False)
            else:
                await self.set_wifi_led(status=led_cfg)
                country, hostname, password = await self._radio_values(wifi_cfg, _VAL_COUNTRY + _VAL_HOSTNAME + _VAL_HOTSPOT_PW)
                await self._activate_hotspot_ap(country, hostname, password)

    async def _cfg_overlay(self) -> "dict[str, CfgValue]":
        # GET shows what the radio uses: passwords masked, and a stored value the radio would refuse as the default it runs
        # on (SPECIFICATION.md C.7.4).
        overlay: dict[str, CfgValue] = {name_cfg(_VAL_PW): "********", name_cfg(_VAL_HOTSPOT_PW): "********"}
        schema = _VAL_SSID + _VAL_COUNTRY + _VAL_HOSTNAME
        values = await self.cfgmgr.get_str_values(schema)
        if values is not None:
            fields = schema_dict(self._cfg_schema)
            for field, value in zip(schema, values):  # noqa: B905 - MicroPython zip() rejects strict=
                used = self._value_in_use(fields.get(field[0], field), value)
                if used != value:
                    overlay[field[0]] = used
        return overlay

    def _configure_hotspot_ap(self, country: str, hostname: str, password: str) -> None:
        # Configures only an inactive AP: re-applying essid/password to a running one can drop its beacon (cyw43).
        # Reached on a hotspot phase's first tick and when the selected AP reports no link (_run_hotspot_mode()).
        if not self._wlan.active():
            network.country(country)  # Country
            network.hostname(hostname)  # Hostname
            self._wlan.config(essid=hostname, password=password)  # HotspotPW, per-device configurable
            self._wlan.active(True)
            self._wlan.config(pm=_PM_NO_POWERSAVE)
            self.pr.one("WLAN hotspot was started")
        own_ip, own_netmask = self._wlan.ifconfig()[:2]
        # Guard against leaking a duplicate concurrent CaptiveDNS.run() task on top of one already
        # running - same "is None or .done()" convention asy_system_service.py's own supervisor
        # (supervise_tasks()) already uses for its supervised tasks.
        if self._dns_server_task is None or self._dns_server_task.done():
            evtloop = asyncio.get_event_loop()
            self._dns_server_task = evtloop.create_task(self._dns_server.run(own_ip, own_netmask))

    async def _connect_loop(self) -> None:
        self._err_cnt_internal = 0  # fresh failure streak each task (re)start, same as _init_<sensor>()
        self._reset_wlan_connect_state()
        await self._apply_initial_led_config()
        while True:
            if self._conn_phase == _PHASE_DEACTIVATED:
                self.pr.all("WLAN is deactivated.")
                # Deactivated: a distinct pattern (owner, 2026-09-29), a short blink every 3 s that obeys the Wi-Fi LED setting
                # like every pattern: silent while it is off, shown once it is turned on (owner, 2026-10-02).
                self._run_led_pattern(_LED_DEACTIVATED_ON_S, _LED_DEACTIVATED_OFF_S)
            else:
                self._hw_op_failed = False
                if self._tick_armed is False:  # the uptime tick never armed: this iteration retries it
                    self._tick_armed = arm_tick_timer(self._counter_timer, self._time_counter_trigger_event, self.pr, "WiFi uptime")
                    if not self._tick_armed:
                        await self.pr.err_s("WiFi uptime timer not armed", errno=_ERR_TIMER)
                        self._hw_op_failed = True
                if self._reconn_wifi:
                    await self._handle_reconnect_trigger()
                if self._conn_phase == _PHASE_HOTSPOT:
                    await self._run_hotspot_mode()
                else:
                    await self._run_sta_mode()
                # Consecutive-failure streak over real WLAN-hardware exceptions (separate from
                # _connection_failures' AP-reachability fallback): gives up on the whole task,
                # matching a Reader's _read_loop() returning False.
                if not await self._error_check((None,), condition=self._hw_op_failed):
                    await self.pr.err_s(
                        "Giving up after repeated WLAN hardware failures, restarting task.", errno=_ERR_WLAN_GIVE_UP,
                    )
                    return
            await asyncio.sleep(_WIFI_REFRESH_S)

    async def _deactivate_wlan_permanently(self) -> None:
        await self.pr.wrn_s("Permanently no WLAN connection, no connection to hotspot. Deactivating WLAN!", wrnno=_WRN_WLAN_DEACTIVATED)
        self._conn_phase = _PHASE_DEACTIVATED
        try:
            self._wlan.disconnect()
            self._wlan.active(False)
            await asyncio.sleep(_WLAN_DOWN_SETTLE_S)
            self._wlan.deinit()
        except Exception as e:
            self._hw_op_failed = True
            await self.pr.err_s("Error deactivating WLAN:", e, errno=_ERR_WLAN_OFF)

    async def _disconnect_sta_and_wait(self) -> None:
        try:
            self._wlan.disconnect()
            for _i in range(_STA_DISCONNECT_WAIT_ITERS):  # bounded - a driver that never actually
                # disconnects (isconnected() staying True forever) must not hang this task forever;
                # matches _poll_sta_connect_status()'s own bounded for-loop convention.
                if not self._wlan.isconnected():
                    break
                self._led_toggle()
                await asyncio.sleep(_STA_DISCONNECT_POLL_S)
            else:
                self._hw_op_failed = True
                await self.pr.err_s("Timed out waiting for STA disconnect", errno=_ERR_TIMEOUT)
        except Exception as e:
            self._hw_op_failed = True
            await self.pr.err_s("Error waiting for STA disconnect:", e, errno=_ERR_WLAN_STA_DISCONNECT)

    async def _flash_led(self, on_s: float, off_s: float) -> None:
        # A cancel ends the task at its sleep and touches no LED: the canceller sets the LED it wants.
        try:
            while True:
                self._led_on()
                await asyncio.sleep(on_s)
                self._led_off()
                await asyncio.sleep(off_s)
        except Exception as e:  # unsupervised task's top: its end is persisted, the LED left as it is
            await self.pr.err_s("LED flash task failed:", e, errno=_ERR_UNEXPECTED)

    async def _handle_reconnect_trigger(self) -> None:
        self._hotspot_timer.deinit()
        self._hotspot_timer_running = False
        if self._ledflash is not None:
            self._ledflash.cancel()
            self._ledflash = None
        self._reconn_wifi = False
        leaving_hotspot = self._conn_phase == _PHASE_HOTSPOT
        if not leaving_hotspot:
            # _leave_hotspot_mode() below already lands on this same value via its own transition -
            # only the plain-STA-reconnect path needs it set here.
            self._conn_phase = _PHASE_STA_SEEKING
        self.pr.evt("WLAN reconnect triggered!")
        await asyncio.sleep(_RECONNECT_CALLER_GRACE_S)  # allow final tasks of calling function
        if leaving_hotspot:  # mode switch
            await self._leave_hotspot_mode()
        else:  # plain reconnect
            await self._wait_for_sta_disconnect()
        await asyncio.sleep(_RECONNECT_SETTLE_S)  # wait once for whatever else to settle

    async def _handle_sta_connection_result(self) -> bool:  # True: the retry wait after a lost link is due
        if self._wlan_isconnected_or_false():
            self._on_sta_connected()
            return False
        return await self._on_sta_disconnected()

    async def _hotspot_client_absent(self) -> None:
        if not self._hotspot_timer_running:
            self.pr.evt("No client connected - hotspot timer started")
            try:
                # PERIODIC, per C.9: a dropped soft callback is simply re-fired one period later, and
                # the first one delivered ends the repeats - reconnect_wifi() deinits this timer.
                # The callback only sets the flag; _hotspot_timeout_loop() does the reconnect.
                self._hotspot_timer.init(
                    period=self._hotspot_time,
                    mode=Timer.PERIODIC,
                    callback=lambda _b: self._hotspot_timeout_trigger_event.set(),
                )
                self._hotspot_timer_running = True  # try to reconnect once after hotspot time if no client connected (maybe router reboot after power loss)
            except (MemoryError, OSError) as e:  # alarm-pool exhaustion (ENOMEM) -
                # _hotspot_timer_running stays False so the next refresh cycle retries arming it.
                await self.pr.err_s("Could not start hotspot timer:", e, errno=_ERR_TIMER)
        self._run_led_pattern(_LED_HOTSPOT_ON_S, _LED_HOTSPOT_OFF_S)

    def _hotspot_client_connected(self) -> None:
        self._hotspot_timer.deinit()  # if client connected, do not stop hotspot
        self._hotspot_timer_running = False
        self._run_led_pattern(_LED_HOTSPOT_CLIENT_ON_S, _LED_HOTSPOT_CLIENT_OFF_S)
        self.pr.evt("Client connected to hotspot, timer stopped")

    async def _hotspot_timeout_loop(self) -> None:
        while True:
            await self._hotspot_timeout_trigger_event.wait()
            self.reconnect_wifi()

    async def _leave_hotspot_mode(self) -> None:
        self._conn_phase = _PHASE_STA_SEEKING
        if self._dns_server_task is not None:
            self._dns_server_task.cancel()
            self._dns_server_task = None
        await self._select_wifi_mode(network.STA_IF)
        self._led_off()
        self.pr.one("WLAN hotspot was switched off")

    def _led_off(self) -> None:
        if self._led is not None:
            try:  # see _led_on()'s comment
                self._led.off()
            except Exception as e:
                self.pr.err("LED off() failed:", e)

    def _led_on(self) -> None:
        if self._led is not None:
            try:  # self._led may be a caller-supplied ext_led (LEDControl Protocol, not necessarily a
                # real Pin) - could misbehave, so this degrades silently rather than feeding
                # _hw_op_failed/_error_check().
                self._led.on()
            except Exception as e:
                self.pr.err("LED on() failed:", e)

    def _led_toggle(self) -> None:
        if self._led is not None:
            try:  # see _led_on()'s comment
                self._led.toggle()
            except Exception as e:
                self.pr.err("LED toggle() failed:", e)

    async def _locked_wlan_status(self) -> int | None:
        async with self.wifi_mode_lock:
            return self._wlan_status_or_none()

    async def _manage_hotspot_stations(self) -> None:
        self.pr.all("Hotspot mode is active")
        stations = await self._get_hotspot_stations()
        if stations is None:  # unknown: neither transition runs, so the timer stays as it was
            await self.pr.wrn_s("Hotspot stations unknown, hotspot timer left as it was", wrnno=_WRN_WLAN_STATIONS_UNKNOWN)
            return
        if len(stations) > 0:  # at least one client connected
            self._hotspot_client_connected()
        else:  # no client connected
            await self._hotspot_client_absent()

    def _on_sta_connected(self) -> None:
        self.pr.one("WLAN connection established")
        self._conn_phase = _PHASE_STA_ESTABLISHED
        self._connection_failures = 0
        self._led_on()
        self._print_wlan_diagnostics()

    async def _on_sta_disconnected(self) -> bool:  # True: the retry wait is due, which the caller sleeps unlocked
        self.pr.evt("No WLAN connection")
        retry_due = self._conn_phase == _PHASE_STA_ESTABLISHED
        if retry_due:
            self.pr.evt("WLAN connection was previously successful, retrying in 1 minute...")
        else:
            await self._register_sta_connection_failure()
        self._led_off()
        self.pr.all("WLAN status:", self._wlan_status_or_none())
        return retry_due

    async def _poll_sta_connect_status(self) -> None:
        for _i in range(_STA_CONNECT_POLL_ITERS):
            self._led_toggle()
            try:
                status = self._wlan.status()
            except Exception as e:
                self._hw_op_failed = True
                await self.pr.err_s("Error polling STA connect status:", e, errno=_ERR_WLAN_STA_POLL)
                return
            if status == network.STAT_IDLE:
                self.pr.all("WLAN idle")
            elif status == network.STAT_CONNECTING:
                self.pr.all("WLAN connecting")
            elif status == _STAT_JOINED_NO_IP:
                self.pr.all("WLAN obtaining IP")
            elif status == network.STAT_WRONG_PASSWORD:
                # cyw43 reports any failed AUTH event or key exchange as BADAUTH (cyw43_ctrl.c:383-395, 415-427): not proof of a wrong password.
                await self.pr.wrn_s("WLAN authentication or handshake failed", wrnno=_WRN_WLAN_AUTH_FAILED)
                return
            elif status == network.STAT_NO_AP_FOUND:
                await self.pr.wrn_s("WLAN access point not found", wrnno=_WRN_WLAN_NO_AP)
                return
            elif status == network.STAT_CONNECT_FAIL:
                await self.pr.wrn_s("WLAN connection failed", wrnno=_WRN_WLAN_CONNECT_FAILED)
                return
            elif status == network.STAT_GOT_IP:
                self.pr.all("WLAN connection successful")
                return
            else:
                await self.pr.wrn_s("WLAN undefined state:", status, wrnno=_WRN_WLAN_STATUS_UNKNOWN)
                return
            await asyncio.sleep(_STA_CONNECT_POLL_S)
        # Every verdict returned above: each poll stayed IDLE, CONNECTING or joined without an IP (a DHCP server that never answers).
        await self.pr.wrn_s("WLAN connect attempt ended without a verdict, last status:", status, wrnno=_WRN_WLAN_NO_VERDICT)

    def _print_wlan_diagnostics(self) -> None:  # self.pr.all() self-gates on the configured level
        try:
            self.pr.all("WLAN status:", self._wlan.status())
            net_config = self._wlan.ifconfig()
            self.pr.all("IPv4 address:", net_config[0], "/", net_config[1])
            self.pr.all("Default gateway:", net_config[2])
            self.pr.all("DNS server:", net_config[3])
        except Exception as e:  # observation-tier - see _wlan_status_or_none()'s comment
            self.pr.err("WLAN diagnostic read failed:", e)

    async def _push_wifi_led(self, value: "CfgValue") -> bool:
        # Narrows the config-value union to bool for set_wifi_led(); the schema already guarantees a bool,
        # so the False arm is unreachable - kept for the type.
        if not isinstance(value, bool):
            return False
        return await self.set_wifi_led(status=value)

    async def _radio_values(self, values: list[str], schema: "ConfigSchema") -> list[str]:
        # A value stored before C.7.4 (or hand-edited) that the radio would refuse runs on its default
        # instead: a config value is never a hardware failure, so it must not feed _hw_op_failed.
        fields = schema_dict(self._cfg_schema)
        safe = []
        for field, value in zip(schema, values):  # noqa: B905 - MicroPython zip() rejects strict=
            live = fields.get(field[0], field)
            used = self._value_in_use(live, value)
            if used != value:
                await self.pr.wrn_s("Stored", field[0], "is outside the radio's accepted form, using its default", wrnno=_WRN_STORED_DEFAULT)
            safe.append(used)
        return safe

    async def _read_wifi_led_cfg(self) -> bool | None:  # None = config missing/malformed
        wifi_led = await self.cfgmgr.get_bool_values(_VAL_LED_WIFI_ON)
        if wifi_led is None or len(wifi_led) != 1:
            return None
        return wifi_led[0]

    async def _recover_device(self) -> bool | None:
        # Participant rung (SPECIFICATION.md C.7/F.2): re-select the current mode; deinit() powers the CYW43 off
        # and the next active(True) reloads its firmware (cyw43_ctrl.c:118-175, cyw43-driver 055d642). None while deactivated: no radio in use.
        if self._conn_phase == _PHASE_DEACTIVATED:
            return None
        return await self._select_wifi_mode(network.AP_IF if self._conn_phase == _PHASE_HOTSPOT else network.STA_IF)

    async def _register_sta_connection_failure(self) -> None:
        if self._connection_failures < (self._conn_fail_to_hotspot - 1):
            self._connection_failures += 1
            self.pr.evt("Failed connection counter:", self._connection_failures)
            return
        self._connection_failures = 0
        if self._hotspot_started_once:
            await self._deactivate_wlan_permanently()
        else:
            self._conn_phase = _PHASE_HOTSPOT
            await self.pr.wrn_s("Permanently no WLAN connection - activating hotspot!", wrnno=_WRN_WLAN_TO_HOTSPOT)

    def _reset_wlan_connect_state(self) -> None:
        if self._ledflash is not None:
            self._ledflash.cancel()
            self._ledflash = None
        if self._dns_server_task is not None:
            self._dns_server_task.cancel()
            self._dns_server_task = None
        self._connection_failures = 0
        self._hotspot_started_once = False
        if self._conn_phase not in (_PHASE_HOTSPOT, _PHASE_DEACTIVATED):
            # DEACTIVATED survives a restart (A.4); HOTSPOT is kept only so reconn_wifi below leaves it through _leave_hotspot_mode(),
            # after which STA starts a fresh streak with hotspot_started_once cleared, as legacy's restart did (legacy/firmware/python/CommonDrivers/async_connect.py:176-181).
            self._conn_phase = _PHASE_STA_SEEKING
        self._hotspot_timer.deinit()
        self._hotspot_timer_running = False
        try:
            self._reconn_wifi = (self._conn_phase == _PHASE_HOTSPOT) or self._wlan.isconnected() or bool(self._wlan.active())
        except Exception as e:  # rare (once per task (re)start) - safe default forces a clean reconnect
            self.pr.err("Error checking WLAN state at start:", e)
            self._reconn_wifi = True
        # clear possible previous connections
        self._led_off()

    async def _run_hotspot_mode(self) -> None:
        status = await self._locked_wlan_status()
        if status == network.STAT_GOT_IP:
            await self._manage_hotspot_stations()
        elif not self._ap_selected:  # the hotspot phase's first tick: STA is still selected
            await self._start_hotspot()
        else:  # the selected AP reports no link: up again in place, and no client, so the timer still runs
            await self._bring_up_hotspot_ap()
            await self._hotspot_client_absent()

    def _run_led_pattern(self, on_s: float, off_s: float) -> None:
        # One flash task; asking for the pattern already running keeps its phase (a task that ended on a fault
        # is not running: the next request starts it again).
        if self._ledflash is not None and not self._ledflash.done() and self._led_pattern == (on_s, off_s):
            return
        if self._ledflash is not None:
            self._ledflash.cancel()
        self._led_pattern = (on_s, off_s)
        self._ledflash = asyncio.get_event_loop().create_task(self._flash_led(on_s, off_s))

    async def _run_sta_mode(self) -> None:
        async with self.wifi_mode_lock:
            if not self._wlan_isconnected_or_false():
                await self._attempt_sta_connect()
            retry_due = False
            if self._conn_phase != _PHASE_HOTSPOT:  # an empty SSID went straight to the hotspot: no result to judge
                retry_due = await self._handle_sta_connection_result()
        if retry_due:  # outside the lock: NTP, the uptime tick and a reconnect go on during the wait
            await asyncio.sleep(_STA_RETRY_AFTER_LOSS_S)

    async def _select_wifi_mode(self, mode: int) -> bool:
        async with self.wifi_mode_lock:
            return await self._switch_wlan_mode(mode)

    async def _start_hotspot(self) -> None:
        await self._select_wifi_mode(network.AP_IF)
        await self._bring_up_hotspot_ap()
        self._hotspot_started_once = True

    async def _switch_wlan_mode(self, mode: int) -> bool:
        self._ap_selected = False
        try:
            self._wlan.disconnect()
            self._wlan.active(False)
            self.pr.all("Wifi inactive")
            await asyncio.sleep(_WLAN_DOWN_SETTLE_S)
            self._wlan.deinit()
            self.pr.all("Wifi off")
            await asyncio.sleep(_WLAN_DEINIT_SETTLE_S)
            self._wifi_uptime.restart(0)
            self._wlan = network.WLAN(mode)
            self._ap_selected = mode == network.AP_IF
            self.pr.all("Wifi mode set")
            await asyncio.sleep(_WLAN_MODE_SETTLE_S)
        except Exception as e:
            self._hw_op_failed = True
            await self.pr.err_s("Error switching WLAN mode:", e, errno=_ERR_WLAN_MODE_SWITCH)
            return False
        return True

    async def _trigger_sta_connect(self, ssid: str, pw: str, country: str, hostname: str) -> bool:
        try:
            network.country(country)
            network.hostname(hostname)
            self._wlan.active(True)
            self._wlan.config(pm=_PM_NO_POWERSAVE)
            self._wlan.connect(ssid, pw)
        except Exception as e:
            self._hw_op_failed = True
            await self.pr.err_s("Error attempting STA connect:", e, errno=_ERR_WLAN_STA_START)
            return False
        else:
            return True

    async def _update_wifi_snapshot(self, *, connected: bool) -> None:
        mode = "AP" if self._conn_phase == _PHASE_HOTSPOT else "STA"
        if self._conn_phase == _PHASE_DEACTIVATED:  # no radio in use: nothing to read
            self._dhcp_dns = None
            await self._set_meas_data(WIFI(mode, connected, None, None, None, None, None, utc_now()))
            return
        ip: str | None = None
        subnet: str | None = None
        gateway: str | None = None
        dns: str | None = None
        try:
            ifcfg = self._wlan.ifconfig()
            if len(ifcfg) == _IFCONFIG_FIELDS:
                ip, subnet, gateway, dns = ifcfg
        except Exception as e:  # observation-tier - see _wlan_status_or_none()'s comment
            self.pr.err("wlan.ifconfig() failed:", e)
        rssi = None
        # Read only with a link on STA: an AP raises ValueError, and an inactive STA returns the driver's
        # unset value, its -EPERM dropped (extmod/network_cyw43.c:363-369, v1.29.0).
        if not self._ap_selected and connected:
            try:
                rssi = int(self._wlan.status("rssi"))
            except Exception as e:  # observation-tier - see _wlan_status_or_none()'s comment
                self.pr.err("wlan.status('rssi') failed:", e)
        self._dhcp_dns = dns if connected else None
        await self._set_meas_data(WIFI(mode, connected, ip, subnet, gateway, dns, rssi, utc_now()))

    async def _uptime_loop(self) -> None:
        self._wifi_uptime.restart(0)
        self._wifi_connected = False
        while True:
            await self._time_counter_trigger_event.wait()
            if self._conn_phase == _PHASE_DEACTIVATED:
                self._wifi_uptime.restart(0)
                self._wifi_connected = False
                await self._update_wifi_snapshot(connected=False)
                continue
            async with self.wifi_mode_lock:
                status = self._wlan_status_or_none()
                if status is not None:
                    # Link up, hotspot included: an active AP reports STAT_GOT_IP too (owner, 2026-09-29).
                    connected = status == network.STAT_GOT_IP
                    self._wifi_connected = connected
                    if not connected:
                        self._wifi_uptime.restart(0)
                    await self._update_wifi_snapshot(connected=connected)
                if self._wifi_connected:
                    self._wifi_uptime.read()  # one read per tick keeps it inside ticks_diff()'s horizon (G.2)
            if status is None:  # Unreadable is not down: the last link state and uptime stand; the warning count shows how long.
                await self.pr.wrn_s("WLAN status unreadable, link state kept", wrnno=_WRN_WLAN_STATUS_UNREADABLE)

    def _value_in_use(self, field: "FieldSchema", value: str) -> str:
        return value if _radio_value_ok(field, value) else str(field[2])

    async def _wait_for_sta_disconnect(self) -> None:
        self.pr.evt("Reconnecting WLAN...")
        async with self.wifi_mode_lock:
            await self._disconnect_sta_and_wait()
        self._led_off()
        self.pr.evt("WLAN is disconnected")

    def _wlan_isconnected_or_false(self) -> bool:
        try:
            return self._wlan.isconnected()
        except Exception as e:  # observation-tier - see _wlan_status_or_none()'s comment
            self.pr.err("wlan.isconnected() failed:", e)
            return False

    def _wlan_status_or_none(self) -> int | None:
        # Observation-tier: a status query failing (WLAN mid-transition/deinitialized) is routine
        # enough to degrade silently - the state machine's own "attempt" methods persist a real errno.
        try:
            return self._wlan.status()
        except Exception as e:
            self.pr.err("wlan.status() failed:", e)
            return None

    def get_task_starters(self) -> "list[TaskStarter]":
        return [self.start_asy_connect, self.start_asy_uptime, self.start_asy_hotspot_timeout]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return [self.start_uptime_timer]

    def start_asy_connect(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._connect_loop())

    def start_asy_hotspot_timeout(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._hotspot_timeout_loop())

    def start_asy_uptime(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._uptime_loop())

    def start_uptime_timer(self) -> None:
        # a failed arm is retried by _connect_loop(), which persists a second failure
        self._tick_armed = arm_tick_timer(self._counter_timer, self._time_counter_trigger_event, self.pr, "WiFi uptime")

    def stop_uptime_timer(self) -> None:
        self._counter_timer.deinit()

    # Every public getter reads state this service holds (the 1 Hz snapshot, the phase); none touches the radio. The one
    # radio read callers may make, network_available_locked(), requires wifi_mode_lock (SPECIFICATION.md C.8).
    async def get_data(self) -> WIFI:
        # Narrows to this Reader's concrete WIFI - see SPECIFICATION.md C.4.2's get_data() convention.
        # Backed by _uptime_loop()'s 1Hz cache push rather than a live lock-aware query - avoids a
        # transient "unknown" reading mid-mode-switch.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(
            self.name, _VAL_SSID + _VAL_PW + _VAL_COUNTRY + _VAL_HOSTNAME + _VAL_LED_WIFI_ON + _VAL_HOTSPOT_PW, callback=self._cfg_overlay,
        )

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data, _FIELDS, name=self.name)

    def get_dns_server_ip(self) -> str | None:
        # The DHCP-assigned DNS server to try first, from the last snapshot.
        return self._dhcp_dns

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    def get_error_sources(self) -> "list[ErrorSource]":
        # Extends SensorReaderConfig.get_error_sources() with this class's own independently-logged
        # sub-object, self._dns_server ("DNSSRV"). List concatenation, never a `[*x, y]` display -
        # that raises SyntaxError at parse time on the pinned MicroPython build (Part F.1).
        return super().get_error_sources() + [self._dns_server]

    def get_loggers(self) -> "list[PrintLogHistory]":
        return super().get_loggers() + [self._dns_server.pr]

    def get_wifi_mode_lock(self) -> asyncio.Lock:
        return self.wifi_mode_lock

    async def get_wifi_uptime(self) -> int:
        return self._wifi_uptime.read() if self._wifi_connected else 0

    def is_hotspot_active(self) -> bool:
        # A plain self._conn_phase compare touches no hardware, unlike network_available_locked()'s radio read -
        # no lock needed, the callable-from-anywhere getter shape.
        return self._conn_phase == _PHASE_HOTSPOT

    async def set_wifi_led(self, *, status: bool) -> bool:
        # Uniform setter return contract (owner, 2026-09-26): always True here - pure attribute
        # assignment plus _led_off()'s own already-defensive degrade-on-raise, nothing to reject.
        if status:  # try to turn on
            if self._led is None:  # LED is actually off
                self._led = self._ext_led  # if None, the LED stays off
        else:  # turn off
            self._led_off()
            self._led = None
        return True

    def network_available_locked(self) -> bool:  # caller must already hold wifi_mode_lock
        return (self._conn_phase != _PHASE_HOTSPOT) and (self._wlan_status_or_none() == network.STAT_GOT_IP)

    def reconnect_wifi(self) -> None:
        self._hotspot_timer.deinit()
        self._hotspot_timer_running = False
        if self._ledflash is not None:
            self._ledflash.cancel()
            self._ledflash = None
        self._reconn_wifi = True

    async def setup(self) -> bool:
        ok = await super().setup()
        await self._dns_server.pr.setup()  # the DNS server's own logger is set up separately
        return ok
