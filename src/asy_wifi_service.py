"""Async WiFi connection/hotspot/LED service. Not a sensor, but config-managed the same way: extends
asy_base_classes.py's SensorReaderConfig, owns its own config_WIFI.cfg (see SPECIFICATION.md Part C).
"""
# "Attempt" operations persist a real errno via self.pr.err_s() and set self._hw_op_failed, feeding
# _connect_loop()'s _error_check() streak; routine state observations degrade silently via
# self.pr.err() instead.

import asyncio
from collections import namedtuple

import network
from machine import Timer
from micropython import const

from asy_base_classes import SensorReaderConfig, TickSeconds, arm_tick_timer, utc_now
from asy_captive_dns import CaptiveDNS
from asy_config_manager import make_dict, name_cfg, schema_dict, schema_names
from asy_print_log import DEFAULT_LOG, LogConfig

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, NamedTuple, Protocol

    from asy_base_classes import ErrorSource, TimerStarter
    from asy_config_manager import ConfigSchema, FieldSchema, WriteValidity
    from asy_print_log import ErrorLog, PrintLogHistory

    # Structural Protocol for a caller-supplied LED (SPECIFICATION.md Part C.10's typing convention).
    class LEDControl(Protocol):
        def off(self) -> None: ...
        def on(self) -> None: ...
        def toggle(self) -> None: ...


# Codes from the global catalog (buildgen/error_catalog.json): the shared ones and WIFI's band.
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
# @web PW section=networking submitGroup=identity label="Wi-Fi Password" mask=true bytes=true
# @web Country section=networking submitGroup=identity label="Country" bytes=true shape=countryCode description="Two uppercase letters (ISO 3166-1 alpha-2), e.g. DE."
# @web Hostname section=networking submitGroup=identity label="Hostname" bytes=true shape=hostLabel

# @web-group section=networking submitGroup=wifiLed label="Wi-Fi Status LED" submit=true
# @web LEDWifiOn section=networking submitGroup=wifiLed label="Wi-Fi Status LED"

_NAME = const("WIFI")
# Kept as a literal tuple inline (not `_FIELDS` below) because mypy's namedtuple plugin can only
# infer field names from a literal at the call site, not through a variable indirection.
WIFI = namedtuple("WIFI", ("Mode", "Connected", "IP", "TS"))
_FIELDS = const(("Mode", "Connected", "IP", "TS"))  # kept in sync with WIFI's own fields above


# The radio's own bounds are UTF-8 bytes, where the schema counts characters: country()/hostname()
# raise outside 2 / 32 bytes and connect() overflows past a 32-byte SSID (SPECIFICATION.md C.7.4).
_RADIO_FIELDS = schema_names(_VAL_SSID + _VAL_PW + _VAL_COUNTRY + _VAL_HOSTNAME + _VAL_HOTSPOT_PW)


def _country_ok(value: str) -> bool:
    # ISO 3166-1 alpha-2 in the cyw43 table's uppercase (cyw43_country.h:49)
    return len(value) == _COUNTRY_CODE_LEN and all("A" <= ch <= "Z" for ch in value)


def _host_label_ok(label: str) -> bool:
    # RFC 1123 SS2.1 host label (letters, digits, '-'; not at either end); the caller bounds the length.
    if not label or label[0] == "-" or label[-1] == "-":
        return False
    return all("0" <= ch <= "9" or "A" <= ch <= "Z" or "a" <= ch <= "z" or ch == "-" for ch in label)


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
        return _host_label_ok(value)
    if field[0] == name_cfg(_VAL_COUNTRY):
        return _country_ok(value)
    return True


def _with_default(schema: tuple[tuple[str, str, str, int, int, str | None], ...], value: str | None) -> tuple[tuple[str, str, str, int, int, str | None], ...]:
    # Substitutes a build-time per-device default into a one-field schema. Only the DEFAULT moves,
    # never the bounds, so a value a user already persisted still wins at boot.

    # A value outside the field's bounds is dropped rather than installed: ConfigManager treats an
    # unsatisfiable default as an invalid config and answers None to every read, costing the device
    # its networking config. buildgen.validate refuses it at build time; this keeps it bootable.
    if value is None:
        return schema
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
# @tunable wifi.led_flash_on_s = 2.9
_LED_FLASH_ON_S = const(2.9)  # _flash_led_off()'s on phase
# @tunable wifi.led_flash_off_s = 0.1
_LED_FLASH_OFF_S = const(0.1)  # and its off phase
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
_PHASE_DEACTIVATED = const(3)  # terminal - WLAN fully deactivated, needs a task/device restart

# @tunable wifi.refresh_s = 5
_WIFI_REFRESH_S = const(5)  # _connect_loop()'s loop period between connection checks

_STAT_OBTAINING_IP = const(2)  # network.STAT_* value seen mid-connect, between STAT_CONNECTING and
# STAT_GOT_IP - not yet exposed as a named constant by MicroPython's network module itself.


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
            WIFI(None, None, None, None),
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
        # _connect_loop()'s own state machine - reset at the top of every _connect_loop() call
        # (i.e. every task (re)start), not meant to be read from outside this class.
        self._conn_phase = _PHASE_STA_SEEKING
        self._connection_failures = 0
        self._hotspot_started_once = False
        self._hw_op_failed = False  # this loop iteration's flag feeding _error_check(), see _connect_loop()
        # SSID/PW/Country/Hostname are persist-only (read fresh from cfgmgr each connection attempt);
        # LEDWifiOn is the one field with a real live push.
        self._push_callbacks[name_cfg(_VAL_LED_WIFI_ON)] = self._push_wifi_led

    async def _get_hotspot_stations(self) -> "list[Any]":
        async with self.wifi_mode_lock:
            await asyncio.sleep(_HOTSPOT_STATIONS_SETTLE_S)
            try:
                # the stations command needs no other status command close before it
                stations = self._wlan.status("stations")
                self.pr.all("Connected stations:", stations)
            except Exception as e:  # observation-tier (polled every _WIFI_REFRESH_S while hotspot is
                # active) - see _wlan_status_or_none()'s comment on why this stays silent, not err_s()
                self.pr.err("Could not fetch connected clients:", e)
                return []
            else:
                return stations  # type: ignore[return-value]  # stub types status(str) as int; real AP-mode "stations" returns a list per MicroPython docs

    async def _set_mgr_cfg(
        self, data: dict[str, int | float | str | bool | None], cfg_vals: "ConfigSchema",
    ) -> "tuple[bool, WriteValidity]":
        # Refuses a radio value outside its byte bound or shape before it is stored (C.7.4); the rest of the
        # request goes through ConfigManager as usual.
        fields = schema_dict(cfg_vals)
        refused = [k for k, v in data.items() if k in _RADIO_FIELDS and k in fields and not _radio_value_ok(fields[k], v)]
        for key in refused:
            await self.pr.err_s("Refusing", key, "- outside the radio's accepted form", errno=_ERR_BAD_ARG)
        ok, results = await super()._set_mgr_cfg({k: v for k, v in data.items() if k not in refused}, cfg_vals)
        for key in refused:
            results[key] = "Invalid"
        return ok, results

    async def _activate_hotspot_ap(self, country: str, hostname: str, password: str) -> None:
        try:
            self._configure_hotspot_ap(country, hostname, password)
        except Exception as e:
            self._hw_op_failed = True
            await self.pr.err_s("Error activating hotspot AP:", e, errno=_ERR_WLAN_AP_START)

    async def _apply_initial_led_config(self) -> None:
        led_cfg = await self._read_wifi_led_cfg()
        if led_cfg is None:
            await self.set_wifi_led(status=False)
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
        if ssid == "":  # SSID - invalid or empty config
            self._connection_failures = self._conn_fail_to_hotspot  # immediate hotspot mode
            return
        if await self._trigger_sta_connect(ssid, pw, country, hostname):
            await self._poll_sta_connect_status()

    def _configure_hotspot_ap(self, country: str, hostname: str, password: str) -> None:
        # Only reached on the first tick after entering hotspot mode in normal operation - see
        # SPECIFICATION.md Part F.2 for why STAT_GOT_IP isn't STA-only. The active() guard below is
        # kept regardless, as low-risk defense against redundant reconfiguration on genuine re-entry.
        if not self._wlan.active():
            network.country(country)  # Country
            network.hostname(hostname)  # Hostname
            self._wlan.config(essid=hostname, password=password)  # HotspotPW, per-device configurable
            self._wlan.active(True)
            self._wlan.config(pm=0xA11140)  # disable power-save mode
            self.pr.one("WLAN hotspot was started")
        own_ip, own_netmask = self._wlan.ifconfig()[:2]
        # Guard against leaking a duplicate concurrent CaptiveDNS.run() task on top of one already
        # running - same "is None or .done()" convention asy_system_service.py's own
        # start_and_check_tasks() already uses for its supervised tasks.
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
            else:
                self._hw_op_failed = False
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
        self.pr.one("Permanently no WLAN connection, no connection to hotspot. Deactivating WLAN!")
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

    async def _flash_led_off(self) -> None:
        while True:
            try:
                self._led_on()
                await asyncio.sleep(_LED_FLASH_ON_S)
                self._led_off()
                await asyncio.sleep(_LED_FLASH_OFF_S)
            except asyncio.CancelledError:
                self._led_on()
                break
            except Exception as e:  # unsupervised task's top: its end is persisted, the LED left as it is
                await self.pr.err_s("LED flash task failed:", e, errno=_ERR_UNEXPECTED)
                break

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

    async def _handle_sta_connection_result(self) -> None:
        if self._wlan_isconnected_or_false():
            self._on_sta_connected()
        else:
            await self._on_sta_disconnected()

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
            except (MemoryError, OSError) as e:  # alarm-pool exhaustion (ENOMEM) - matches
                # asy_ntp_client.py's own Timer.init() guards; _hotspot_timer_running stays False so
                # the next _WIFI_REFRESH_S cycle retries arming it instead of getting stuck unset.
                self.pr.err("Could not start hotspot timer:", e)
        if self._ledflash is None:
            evtloop = asyncio.get_event_loop()
            self._ledflash = evtloop.create_task(self._flash_led_off())

    def _hotspot_client_connected(self) -> None:
        self._hotspot_timer.deinit()  # if client connected, do not stop hotspot
        self._hotspot_timer_running = False
        if self._ledflash is None:
            self._led_on()
        else:
            self._ledflash.cancel()
            self._ledflash = None
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
        if len(stations) > 0:  # at least one client connected
            self._hotspot_client_connected()
        else:  # no client connected
            await self._hotspot_client_absent()

    async def _mask_pw(self) -> dict[str, int | float | str | bool | None]:
        # PW/HotspotPW are real credentials, masked here ("********") via _get_dict_cfg()'s callback
        # overlay so neither can leak its plaintext value through any REST route built on the
        # generic getter-quartet path.
        return {name_cfg(_VAL_PW): "********", name_cfg(_VAL_HOTSPOT_PW): "********"}

    def _on_sta_connected(self) -> None:
        self.pr.one("WLAN connection established")
        self._conn_phase = _PHASE_STA_ESTABLISHED
        self._connection_failures = 0
        self._led_on()
        self._print_wlan_diagnostics()

    async def _on_sta_disconnected(self) -> None:
        self.pr.evt("No WLAN connection")
        if self._conn_phase == _PHASE_STA_ESTABLISHED:
            self.pr.evt("WLAN connection was previously successful, retrying in 1 minute...")
            await asyncio.sleep(_STA_RETRY_AFTER_LOSS_S)
        else:
            await self._register_sta_connection_failure()
        self._led_off()
        self.pr.all("WLAN status:", self._wlan_status_or_none())

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
            elif status == _STAT_OBTAINING_IP:
                self.pr.all("WLAN obtaining IP")
            elif status == network.STAT_WRONG_PASSWORD:
                await self.pr.wrn_s("WLAN authentication failed - wrong password, or the AP dropped mid-handshake", wrnno=_WRN_WLAN_AUTH_FAILED)
                return
            elif status == network.STAT_NO_AP_FOUND:
                await self.pr.wrn_s("WLAN access point not found", wrnno=_WRN_WLAN_NO_AP)
                return
            elif status == network.STAT_CONNECT_FAIL:
                await self.pr.wrn_s("WLAN connection failed", wrnno=_WRN_WLAN_CONNECT_FAILED)
                return
            elif status == network.STAT_GOT_IP:
                self.pr.all("WLAN connection successful")
            else:
                await self.pr.wrn_s("WLAN undefined state:", status, wrnno=_WRN_WLAN_STATUS_UNKNOWN)
                return
            await asyncio.sleep(_STA_CONNECT_POLL_S)

    def _print_wlan_diagnostics(self) -> None:  # self.pr.all() self-gates on the configured level
        try:
            self.pr.all("WLAN status:", self._wlan.status())
            net_config = self._wlan.ifconfig()
            self.pr.all("IPv4 address:", net_config[0], "/", net_config[1])
            self.pr.all("Default gateway:", net_config[2])
            self.pr.all("DNS server:", net_config[3])
        except Exception as e:  # observation-tier - see _wlan_status_or_none()'s comment
            self.pr.err("WLAN diagnostic read failed:", e)

    async def _push_wifi_led(self, value: int | float | str | bool | None) -> bool:
        # Narrows _push_callbacks' wide value type to set_wifi_led's real bool parameter - the
        # isinstance check is defense-in-depth, not a scenario a real (schema-validated) caller hits.
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
            if _radio_value_ok(live, value):
                safe.append(value)
            else:
                await self.pr.wrn_s("Stored", field[0], "is outside the radio's accepted form, using its default", wrnno=_WRN_STORED_DEFAULT)
                safe.append(str(live[2]))  # every radio field's default is a str
        return safe

    async def _read_wifi_led_cfg(self) -> bool | None:  # None = config missing/malformed
        wifi_led = await self.cfgmgr.get_bool_values(_VAL_LED_WIFI_ON)
        if wifi_led is None or len(wifi_led) != 1:
            return None
        return wifi_led[0]

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
            self.pr.one("Permanently no WLAN connection - activating hotspot!")

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
            # Both left as-is on a task restart, not reset to _PHASE_STA_SEEKING - see
            # SPECIFICATION.md Part A.4's "Permanent WiFi deactivation" bullet.
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
        if status != network.STAT_GOT_IP:
            await self._start_hotspot()
        else:
            await self._manage_hotspot_stations()

    async def _run_sta_mode(self) -> None:
        async with self.wifi_mode_lock:
            if not self._wlan_isconnected_or_false():
                await self._attempt_sta_connect()
            await self._handle_sta_connection_result()

    async def _select_wifi_mode(self, mode: int) -> None:
        async with self.wifi_mode_lock:
            await self._switch_wlan_mode(mode)

    async def _start_hotspot(self) -> None:
        await self._select_wifi_mode(network.AP_IF)
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
            self._hotspot_started_once = True

    async def _switch_wlan_mode(self, mode: int) -> None:
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
            self.pr.all("Wifi mode set")
            await asyncio.sleep(_WLAN_MODE_SETTLE_S)
        except Exception as e:
            self._hw_op_failed = True
            await self.pr.err_s("Error switching WLAN mode:", e, errno=_ERR_WLAN_MODE_SWITCH)

    async def _trigger_sta_connect(self, ssid: str, pw: str, country: str, hostname: str) -> bool:
        try:
            network.country(country)
            network.hostname(hostname)
            self._wlan.active(True)
            self._wlan.config(pm=0xA11140)  # disable power-save mode
            self._wlan.connect(ssid, pw)
        except Exception as e:
            self._hw_op_failed = True
            await self.pr.err_s("Error attempting STA connect:", e, errno=_ERR_WLAN_STA_START)
            return False
        else:
            return True

    async def _update_wifi_snapshot(self, *, connected: bool) -> None:
        mode = "AP" if self._conn_phase == _PHASE_HOTSPOT else "STA"
        ip = None
        try:
            ifcfg = self._wlan.ifconfig()
            if len(ifcfg) == _IFCONFIG_FIELDS:
                ip = ifcfg[0]
        except Exception as e:  # observation-tier - see _wlan_status_or_none()'s comment
            self.pr.err("wlan.ifconfig() failed:", e)
        await self._set_meas_data(WIFI(mode, connected, ip, utc_now()))

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
                connected = self._wlan_status_or_none() == network.STAT_GOT_IP
                self._wifi_connected = connected
                if connected:
                    self._wifi_uptime.read()  # one read per tick keeps it inside ticks_diff()'s horizon (G.2)
                else:
                    self._wifi_uptime.restart(0)
                await self._update_wifi_snapshot(connected=connected)

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

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
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
        arm_tick_timer(self._counter_timer, self._time_counter_trigger_event, self.pr, "WiFi uptime")

    def stop_uptime_timer(self) -> None:
        self._counter_timer.deinit()

    async def get_data(self) -> WIFI:
        # Narrows to this Reader's concrete WIFI - see SPECIFICATION.md C.4.2's get_data() convention.
        # Backed by _uptime_loop()'s 1Hz cache push rather than a live lock-aware query - avoids a
        # transient "unknown" reading mid-mode-switch.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(
            self.name, _VAL_SSID + _VAL_PW + _VAL_COUNTRY + _VAL_HOSTNAME + _VAL_LED_WIFI_ON + _VAL_HOTSPOT_PW, callback=self._mask_pw,
        )

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data, _FIELDS, name=self.name)

    def get_dns_server_ip(self) -> str | None:
        # The DHCP-assigned DNS server to try first, before any fallback list. Reuses
        # get_wlan_ifconfig()'s own None-on-failure convention.
        ifcfg = self.get_wlan_ifconfig()
        return None if ifcfg is None else ifcfg[3]

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

    # Locking convention (Part C.8's "Known inconsistency"): network_available_locked() assumes the caller
    # holds wifi_mode_lock; get_wlan_ifconfig(), get_wlan_rssi() and wlan_isconnected() check .locked()
    # themselves and degrade. A new getter picks one shape deliberately, never by copying its nearest neighbour.
    def get_wlan_ifconfig(self) -> tuple[str, str, str, str] | None:
        if self.wifi_mode_lock.locked():
            return None
        try:
            ifcfg = self._wlan.ifconfig()
        except Exception as e:  # observation-tier - see _wlan_status_or_none()'s comment
            self.pr.err("wlan.ifconfig() failed:", e)
            return None
        if len(ifcfg) == _IFCONFIG_FIELDS:
            return ifcfg[0:4]
        return None  # defensive: real WLAN.ifconfig() is a fixed 4-tuple per the stub

    def get_wlan_rssi(self) -> int | None:
        if self.wifi_mode_lock.locked():
            return None
        try:
            rssi = int(self._wlan.status("rssi"))  # not valid in AP mode!
        except Exception as e:  # observation-tier - see _wlan_status_or_none()'s comment. Per
            # extmod/network_cyw43.c, querying "rssi" outside STA mode raises ValueError("STA
            # required"), a routine failure while hotspot_mode is active - still logs.
            self.pr.err("wlan.status('rssi') failed:", e)
            rssi = None
        return rssi

    def is_hotspot_active(self) -> bool:
        # A plain self._conn_phase int-compare touches no hardware, unlike network_available_locked()'s
        # own _wlan_status_or_none() call - no lock needed, so this picks the callable-from-anywhere
        # getter shape (like get_dns_server_ip()/get_wlan_rssi() above), not network_available_locked()'s.
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

    def wlan_isconnected(self) -> bool:
        if self.wifi_mode_lock.locked():
            return False
        return self._wlan_isconnected_or_false()
