"""Async WiFi connection/hotspot/LED service (asy_conn_time) - not a sensor (no I2C/SPI bus), but
config-managed the same way as every promoted sensor driver and asy_ntp_client.py: extends
base_classes.py's SensorReaderConfig, owns its own config_WIFI.cfg file/schema internally - no
externally-injected ConfigManager, no separate get_default_cfg()/_DEFAULT_CONFIG merge step. See
DRIVER_SPEC.md for the shared contract this follows.

First step of the async_connect.py -> asy_wifi_service.py promotion: the config-manager migration,
the getter quartet (get_data()/get_dict_data()/get_dict_cfg()/get_error_counter()),
get_task_starters()/get_timer_starters(), wlan_connect()'s factoring into shallow private methods,
get_data()'s switch to the cached-reading convention (_set_meas_data() pushed once per second from
time_counter(), see get_data()'s own comment), and tightened exception handling around every direct
network/wlan call (each caught close to its call site - "attempt" operations like a mode switch or
a connect attempt persist a real errno via self.pr.err_s(); routine state *observations* like a
status()/isconnected() query degrade silently to a sentinel instead, matching the pre-existing
wifi_mode_lock.locked() sentinel precedent, to avoid flooding get_error_counter() with a query that
legitimately fails on every tick while wlan_deactivated) are all done. What's still an otherwise
unmodified copy of improved-quality/async_connect.py's asy_conn_time: the STA/AP/LED state
machine's overall control flow and timer/locking structure, its naming staleness, the unbounded
isconnected()-wait loop inside _disconnect_sta_and_wait(), and the ONE_SHOT hotspot timer - these
are deliberately deferred to a later pass, not silently fixed here.
"""

import asyncio
import time
from collections import namedtuple

import network
from captive_dns import DNSServer
from machine import Pin, Timer
from micropython import const
from uasyncio import Lock, ThreadSafeFlag

from base_classes import LockedCounter, SensorReaderConfig
from config_manager import make_dict

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from asy_fram_manager import AsyFramManager

try:
    from typing import Protocol
except Exception:

    class Protocol:  # type: ignore[no-redef]
        pass  # micropython does not support typing Protocol


# Schema tuples for ConfigManager.get_*_values() - min/max mirror the REST-API bounds
# sensortask-wozi.py's update_valid_json() already enforces for SSID/Country/PW ("Country"(2-2),
# "SSID"(2-32), "PW"(8-63)), except SSID/PW's own min is relaxed to 0 here so the fresh, unconfigured
# default ("") self-validates against ConfigManager.__init__'s own type_or_range_error() check -
# actual REST-write bounds are still the tighter 2-32/8-63 (config setters are out of scope for
# this pass regardless, see DRIVER_SPEC.md section 5).
_VAL_SSID = const((("SSID", "str", "", 0, 32, None),))
_VAL_PW = const((("PW", "str", "", 0, 63, None),))
_VAL_CTRY = const((("Country", "str", "DE", 2, 2, None),))
_VAL_HOST = const((("Hostname", "str", "SensorNode", 1, 63, None),))
_VAL_LED = const((("LedWifiOn", "bool", True, None, None, None),))

_NAME = const("WIFI")
WIFI = namedtuple("WIFI", ("Mode", "Connected", "IP", "TS"))


class LEDControl(Protocol):
    def on(self) -> None: ...
    def off(self) -> None: ...
    def toggle(self) -> None: ...


class asy_conn_time(SensorReaderConfig):
    def __init__(
        self,
        conn_fail_to_hotspot: int = 5,
        led_pin: int | None = None,
        ext_led: LEDControl | None = None,
        wifi_refresh_sec: int = 5,
        hotspot_time_min: int = 5,
        max_i2c_err: int = 5,  # inert here - this service never calls _error_check(); kept only
        # because SensorReaderConfig's own constructor contract requires it (same as
        # asy_ntp_client.py's own comment for this parameter).
        cfg_path: str = "",
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        super().__init__(
            WIFI(None, None, None, None),
            max_i2c_err,
            _NAME,
            _VAL_SSID + _VAL_PW + _VAL_CTRY + _VAL_HOST + _VAL_LED,
            cfg_path=cfg_path,
            fram=fram,
            history_length=history_length,
            debug=debug,
        )
        self.wlan = network.WLAN(network.STA_IF)
        self.led_pin = None if led_pin is None else Pin(led_pin, mode=Pin.OUT, value=0)
        self.ext_led = ext_led
        self.led: LEDControl | None = None
        self.wifi_refresh_sec = wifi_refresh_sec
        self.hotspot_time = 60000 * hotspot_time_min  # convert to ms
        self.conn_fail_to_hotspot = conn_fail_to_hotspot
        self.wifi_uptime = LockedCounter(max_val=0xFFFFFFFF)
        self.hotspot_mode = False
        self.debug = debug  # still gates every literal `if self.debug: print(...)` call below,
        # unchanged this pass - see module docstring.
        self.dns_server = DNSServer(debug=bool(self.debug))
        self.dns_server_task: asyncio.Task[None] | None = None
        self.reconn_wifi = False
        self.time_counter_trigger_event = ThreadSafeFlag()
        self.wifi_mode_lock = Lock()
        self.counter_timer = Timer()
        self.hotspot_timer = Timer()
        self.hotspot_timer_running = False
        self.ledflash: asyncio.Task[None] | None = None
        # wlan_connect()'s own state machine - reset at the top of every wlan_connect() call
        # (i.e. every task (re)start), not meant to be read from outside this class.
        self.connection_failures = 0
        self.hotspot_started_once = False
        self.wlan_connected_once = False
        self.wlan_deactivated = False

    def start_asy_wlan_connect(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.wlan_connect())

    def start_asy_uptime_counter(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.time_counter())

    def start_counter_timer(self) -> None:
        self.counter_timer.init(
            period=1000,
            mode=Timer.PERIODIC,
            callback=lambda b: self.time_counter_trigger_event.set(),
        )

    def stop_counter_timer(self) -> None:
        self.counter_timer.deinit()

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_wlan_connect, self.start_asy_uptime_counter]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return [self.start_counter_timer]

    def _now(self) -> int | None:
        try:
            return time.mktime(time.gmtime())
        except (OverflowError, OSError):  # rp2's mktime()/gmtime() raise past its ~2037 32-bit epoch range
            return None

    async def get_data(self) -> WIFI:
        # Narrows _get_meas_data()'s generic "NamedTuple" to this Reader's concrete WIFI - matches
        # asy_ntp_client.py's own get_data() narrowing convention (DRIVER_SPEC.md section 4.2).
        # Backed by time_counter()'s 1Hz cache push (_update_wifi_snapshot()) rather than a live
        # lock-aware query: the earlier version called wlan_isconnected()/get_wlan_ifconfig(), which
        # return a safe-but-uninformative sentinel while wifi_mode_lock is held - meaning a caller
        # reading get_data() mid-mode-switch saw a transient "unknown" reading instead of the actual
        # last-known state, exactly the failure mode the cached-reading convention exists to avoid.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data)

    async def _mask_pw(self) -> dict[str, int | float | str | bool | None]:
        # PW is a real credential (the configured WiFi password). sensortask-wozi.py's existing
        # /net/config route already masks it before returning it ("********", never the real
        # cached value) - reusing _get_dict_cfg()'s callback-overlay mechanism here keeps that same
        # masking in the generic getter-quartet path too, so a future REST route wired straight to
        # get_dict_cfg() can't accidentally leak the plaintext password where today's route doesn't.
        return {"PW": "********"}

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(
            _NAME, _VAL_SSID + _VAL_PW + _VAL_CTRY + _VAL_HOST + _VAL_LED, callback=self._mask_pw
        )

    async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:
        return await self.pr.get_log(_NAME)

    def reconnect_wifi(self) -> None:
        self.hotspot_timer.deinit()
        self.hotspot_timer_running = False
        if self.ledflash is not None:
            self.ledflash.cancel()
            self.ledflash = None
        self.reconn_wifi = True

    def _wlan_status_or_none(self) -> int | None:
        # Observation-tier helper: a status *query* failing (WLAN mid-transition/deinitialized) is
        # routine enough here to degrade silently rather than feed get_error_counter() - the state
        # machine's own "attempt" methods (_switch_wlan_mode(), _trigger_sta_connect(), ...) are the
        # ones that persist a real errno when an actual operation fails.
        try:
            return self.wlan.status()
        except Exception as e:
            self.pr.err(_NAME, "wlan.status() failed:", e)
            return None

    def _wlan_isconnected_or_false(self) -> bool:
        try:
            return self.wlan.isconnected()
        except Exception as e:  # observation-tier - see _wlan_status_or_none()'s comment
            self.pr.err(_NAME, "wlan.isconnected() failed:", e)
            return False

    def wlan_isconnected(self) -> bool:
        if self.wifi_mode_lock.locked():
            return False
        return self._wlan_isconnected_or_false()

    def get_wlan_ifconfig(self) -> tuple[str, str, str, str] | None:
        if self.wifi_mode_lock.locked():
            return None
        try:
            ifcfg = self.wlan.ifconfig()
        except Exception as e:  # observation-tier - see _wlan_status_or_none()'s comment
            self.pr.err(_NAME, "wlan.ifconfig() failed:", e)
            return None
        if len(ifcfg) == 4:
            return ifcfg[0:4]
        return None

    def get_wlan_rssi(self) -> int | None:
        if self.wifi_mode_lock.locked():
            return None
        try:
            rssi = int(self.wlan.status("rssi"))  # not valid in AP mode!
        except Exception:
            rssi = None
        return rssi

    def get_wifi_mode_lock(self) -> Lock:
        return self.wifi_mode_lock

    def _release_wifi_lock(self) -> None:
        try:
            self.wifi_mode_lock.release()
        except RuntimeError:  # in case it's already released somehow
            pass

    def network_available(self) -> bool:  # caller must already hold wifi_mode_lock
        return (not self.hotspot_mode) and (self._wlan_status_or_none() == network.STAT_GOT_IP)

    def set_ext_led(self, ext_led: LEDControl) -> None:  # for post-setting ext_led at any time
        self.ext_led = ext_led  # if called even after init, call set_wifi_led(True) to init LED

    async def set_wifi_led(self, status: bool) -> None:
        if status:  # try to turn on
            if self.led is None:  # LED is actually off
                if self.led_pin is None:  # no gpio led defined
                    self.led = self.ext_led  # if also None, LED stays off anyway
                else:
                    self.led = self.led_pin  # gpio has priority if not None
        else:  # turn off
            self._led_off()
            self.led = None

    def _led_on(self) -> None:
        if self.led is not None:
            self.led.on()

    def _led_off(self) -> None:
        if self.led is not None:
            self.led.off()

    def _led_toggle(self) -> None:
        if self.led is not None:
            self.led.toggle()

    async def get_wifi_uptime(self) -> int:
        value = await self.wifi_uptime.get_value()  # never None: never constructed/set with a None sentinel
        return 0 if value is None else value

    async def _flash_led_off(self) -> None:
        while True:
            try:
                self._led_on()
                await asyncio.sleep(2.9)
                self._led_off()
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                self._led_on()
                break

    async def _select_wifi_mode(self, mode: int) -> None:
        await self.wifi_mode_lock.acquire()
        try:
            await self._switch_wlan_mode(mode)
        finally:
            self._release_wifi_lock()

    async def _switch_wlan_mode(self, mode: int) -> None:
        try:
            self.wlan.disconnect()
            self.wlan.active(False)
            if self.debug:
                print("Wifi inactive")
            await asyncio.sleep(2)
            self.wlan.deinit()
            if self.debug:
                print("Wifi off")
            await asyncio.sleep(1)
            await self.wifi_uptime.set_value(0)
            self.wlan = network.WLAN(mode)
            if self.debug:
                print("Wifi mode set")
            await asyncio.sleep(1)
        except Exception as e:
            await self.pr.err_s(_NAME, "Error switching WLAN mode:", e, errno=1)

    async def wlan_connect(self) -> None:  # Funktion: WLAN-Verbindung
        await self.pr.setup()  # required for all logged warnings and errors (base_classes.py's own
        # __init__ never calls this - matches every _init_<sensor>() in the three promoted drivers)
        self._reset_wlan_connect_state()
        await self._apply_initial_led_config()
        while True:
            if self.wlan_deactivated:
                if self.debug:
                    print("WLAN ist deaktiviert.")
            else:
                if self.reconn_wifi:
                    await self._handle_reconnect_trigger()
                if self.hotspot_mode:
                    await self._run_hotspot_mode()
                else:
                    await self._run_sta_mode()
            await asyncio.sleep(self.wifi_refresh_sec)

    def _reset_wlan_connect_state(self) -> None:
        if self.ledflash is not None:
            self.ledflash.cancel()
            self.ledflash = None
        if self.dns_server_task is not None:
            self.dns_server_task.cancel()
            self.dns_server_task = None
        self.connection_failures = 0
        self.hotspot_started_once = False
        self.wlan_connected_once = False
        self.wlan_deactivated = False
        self.hotspot_timer.deinit()
        self.hotspot_timer_running = False
        try:
            self.reconn_wifi = self.hotspot_mode or self.wlan.isconnected() or bool(self.wlan.active())
        except Exception as e:  # rare (once per task (re)start) - safe default forces a clean reconnect
            self.pr.err(_NAME, "Error checking WLAN state at start:", e)
            self.reconn_wifi = True
        # clear possible previous connections
        self._led_off()

    async def _apply_initial_led_config(self) -> None:
        led_cfg = await self._read_wifi_led_cfg()
        if led_cfg is None:
            await self.set_wifi_led(False)
            self.wlan_deactivated = True
            if self.debug:
                print("Fehlende WLAN Konfiguration!")
        else:
            await self.set_wifi_led(led_cfg)

    async def _read_wifi_led_cfg(self) -> bool | None:  # None = config missing/malformed
        wifi_led = await self.cfgmgr.get_bool_values(_VAL_LED)
        if wifi_led is None or len(wifi_led) != 1:
            return None
        return wifi_led[0]

    async def _handle_reconnect_trigger(self) -> None:
        self.hotspot_timer.deinit()
        self.hotspot_timer_running = False
        if self.ledflash is not None:
            self.ledflash.cancel()
            self.ledflash = None
        self.reconn_wifi = False
        self.wlan_connected_once = False
        if self.debug:
            print("WLAN Reconnect ausgelöst!")
        await asyncio.sleep(5)  # allow final tasks of calling function
        if self.hotspot_mode:  # mode switch
            await self._leave_hotspot_mode()
        else:  # plain reconnect
            await self._wait_for_sta_disconnect()
        await asyncio.sleep(3)  # wait once for whatever else to settle

    async def _leave_hotspot_mode(self) -> None:
        self.hotspot_mode = False
        if self.dns_server_task is not None:
            self.dns_server_task.cancel()
            self.dns_server_task = None
        await self._select_wifi_mode(network.STA_IF)
        self._led_off()
        if self.debug:
            print("WLAN Hotspot wurde ausgeschaltet")

    async def _wait_for_sta_disconnect(self) -> None:
        if self.debug:
            print("WLAN neu verbinden...")
        await self.wifi_mode_lock.acquire()
        try:
            await self._disconnect_sta_and_wait()
        finally:
            self._release_wifi_lock()
        self._led_off()
        if self.debug:
            print("WLAN ist getrennt")

    async def _disconnect_sta_and_wait(self) -> None:
        try:
            self.wlan.disconnect()
            while self.wlan.isconnected():  # wait until disconnected
                self._led_toggle()
                await asyncio.sleep(0.5)
        except Exception as e:
            await self.pr.err_s(_NAME, "Error waiting for STA disconnect:", e, errno=5)

    async def _run_hotspot_mode(self) -> None:
        status = await self._locked_wlan_status()
        if status != network.STAT_GOT_IP:
            await self._start_hotspot()
        else:
            await self._manage_hotspot_stations()

    async def _locked_wlan_status(self) -> int | None:
        await self.wifi_mode_lock.acquire()
        try:
            return self._wlan_status_or_none()
        finally:
            self._release_wifi_lock()

    async def _start_hotspot(self) -> None:
        await self._select_wifi_mode(network.AP_IF)
        await self.wifi_mode_lock.acquire()
        try:
            led_cfg = await self._read_wifi_led_cfg()
            wifi_cfg = await self.cfgmgr.get_str_values(_VAL_CTRY + _VAL_HOST)
            if wifi_cfg is None or led_cfg is None or len(wifi_cfg) != 2:
                if self.debug:
                    print("Fehlende WLAN Konfiguration!")
                await self.set_wifi_led(False)
            else:
                await self.set_wifi_led(led_cfg)
                await self._activate_hotspot_ap(wifi_cfg[0], wifi_cfg[1])
            self.hotspot_started_once = True
        finally:
            self._release_wifi_lock()

    async def _activate_hotspot_ap(self, country: str, hostname: str) -> None:
        try:
            self._configure_hotspot_ap(country, hostname)
        except Exception as e:
            await self.pr.err_s(_NAME, "Error activating hotspot AP:", e, errno=2)

    def _configure_hotspot_ap(self, country: str, hostname: str) -> None:
        network.country(country)  # Country
        network.hostname(hostname)  # Hostname
        self.wlan.config(essid=hostname, password="12345678")
        self.wlan.active(True)
        self.wlan.config(pm=0xA11140)  # Stromsparmodus ausschalten
        own_ip, own_netmask = self.wlan.ifconfig()[:2]
        evtloop = asyncio.get_event_loop()
        self.dns_server_task = evtloop.create_task(self.dns_server.run(own_ip, own_netmask))
        if self.debug:
            print("WLAN Hotspot wurde gestartet")

    async def _manage_hotspot_stations(self) -> None:
        if self.debug:
            print("Hotspot Mode ist aktiv")
        stations = await self._get_hotspot_stations()
        if len(stations) > 0:  # at least one client connected
            self._hotspot_client_connected()
        else:  # no client connected
            self._hotspot_client_absent()

    async def _get_hotspot_stations(self) -> "list[Any]":
        await self.wifi_mode_lock.acquire()
        try:
            await asyncio.sleep(0.1)
            # stations command needs no other status commands close before (and does not support "async with"!)
            stations = self.wlan.status("stations")
            if self.debug:
                print("Connected stations:", stations)
            return stations
        except Exception as e:
            if self.debug:
                print("Verbundene Clients können nicht abgerufen werden:", e)
            return []
        finally:
            self._release_wifi_lock()

    def _hotspot_client_connected(self) -> None:
        self.hotspot_timer.deinit()  # if client connected, do not stop hotspot
        self.hotspot_timer_running = False
        if self.ledflash is None:
            self._led_on()
        else:
            self.ledflash.cancel()
            self.ledflash = None
        if self.debug:
            print("Client mit Hotspot verbunden, Timer gestoppt")

    def _hotspot_client_absent(self) -> None:
        if not self.hotspot_timer_running:
            if self.debug:
                print("Kein Client verbunden - Hotspot Timer gestartet")
            self.hotspot_timer.init(
                period=self.hotspot_time,
                mode=Timer.ONE_SHOT,
                callback=lambda b: self.reconnect_wifi(),
            )
            self.hotspot_timer_running = True  # try to reconnect once after hotspot time if no client connected (maybe router reboot after power loss)
        if self.ledflash is None:
            evtloop = asyncio.get_event_loop()
            self.ledflash = evtloop.create_task(self._flash_led_off())

    async def _run_sta_mode(self) -> None:
        await self.wifi_mode_lock.acquire()
        try:
            if not self._wlan_isconnected_or_false():
                await self._attempt_sta_connect()
            await self._handle_sta_connection_result()
        finally:
            self._release_wifi_lock()

    async def _attempt_sta_connect(self) -> None:
        if self.debug:
            print("WLAN-Verbindung herstellen")
        led_cfg = await self._read_wifi_led_cfg()
        await self.set_wifi_led(False if led_cfg is None else led_cfg)
        wifi_cfg = await self.cfgmgr.get_str_values(_VAL_SSID + _VAL_PW + _VAL_CTRY + _VAL_HOST)
        if wifi_cfg is None or len(wifi_cfg) != 4:
            if self.debug:
                print("Fehlende WLAN Konfiguration!")
            return
        ssid, pw, country, hostname = wifi_cfg
        if ssid == "":  # SSID - invalid or empty config
            self.connection_failures = self.conn_fail_to_hotspot  # immediate hotspot mode
            return
        if await self._trigger_sta_connect(ssid, pw, country, hostname):
            await self._poll_sta_connect_status()

    async def _trigger_sta_connect(self, ssid: str, pw: str, country: str, hostname: str) -> bool:
        try:
            network.country(country)
            network.hostname(hostname)
            self.wlan.active(True)
            self.wlan.config(pm=0xA11140)  # Stromsparmodus ausschalten
            self.wlan.connect(ssid, pw)
            return True
        except Exception as e:
            await self.pr.err_s(_NAME, "Error attempting STA connect:", e, errno=3)
            return False

    async def _poll_sta_connect_status(self) -> None:
        for _i in range(10):
            self._led_toggle()
            try:
                status = self.wlan.status()
            except Exception as e:
                await self.pr.err_s(_NAME, "Error polling STA connect status:", e, errno=4)
                return
            if status == network.STAT_IDLE:
                if self.debug:
                    print("WLAN idle")
            elif status == network.STAT_CONNECTING:
                if self.debug:
                    print("WLAN connecting")
            elif status == 2:  #  not defined by constant in class yet!
                if self.debug:
                    print("WLAN obtaining IP")
            elif status == network.STAT_WRONG_PASSWORD:
                if self.debug:
                    print("WLAN wrong password")
                return
            elif status == network.STAT_NO_AP_FOUND:
                if self.debug:
                    print("WLAN access point not found")
                return
            elif status == network.STAT_CONNECT_FAIL:
                if self.debug:
                    print("WLAN connection failed")
                return
            elif status == network.STAT_GOT_IP:
                if self.debug:
                    print("WLAN connection successful")
            else:
                if self.debug:
                    print("WLAN undefined state")
                return
            await asyncio.sleep(0.5)

    async def _handle_sta_connection_result(self) -> None:
        if self._wlan_isconnected_or_false():
            self._on_sta_connected()
        else:
            await self._on_sta_disconnected()

    def _on_sta_connected(self) -> None:
        if self.debug:
            print("WLAN-Verbindung hergestellt")
        self.wlan_connected_once = True
        self.connection_failures = 0
        self._led_on()
        if self.debug:
            self._print_wlan_diagnostics()

    def _print_wlan_diagnostics(self) -> None:  # debug-only - self.debug already gates every caller
        try:
            print("WLAN-Status:", self.wlan.status())
            net_config = self.wlan.ifconfig()
            print("IPv4-Adresse:", net_config[0], "/", net_config[1])
            print("Standard-Gateway:", net_config[2])
            print("DNS-Server:", net_config[3])
        except Exception as e:
            print("WLAN diagnostic read failed:", e)

    async def _on_sta_disconnected(self) -> None:
        if self.debug:
            print("Keine WLAN-Verbindung")
        if self.wlan_connected_once:
            if self.debug:
                print("WLAN-Verbindung war zuvor erfolgreich, neuer Versuch in 1 Minute...")
            await asyncio.sleep(60)  # retry previously successful connecion in one minute
        else:
            await self._register_sta_connection_failure()
        self._led_off()
        if self.debug:
            print("WLAN-Status:", self._wlan_status_or_none())

    async def _register_sta_connection_failure(self) -> None:
        if self.connection_failures < (self.conn_fail_to_hotspot - 1):
            self.connection_failures += 1
            if self.debug:
                print("Zähler für fehlgeschlagene Verbindungen:", self.connection_failures)
            return
        self.connection_failures = 0
        if self.hotspot_started_once:
            await self._deactivate_wlan_permanently()
        else:
            self.hotspot_mode = True
            if self.debug:
                print("Dauerhaft keine WLAN-Verbindung - aktiviere Hotspot!")

    async def _deactivate_wlan_permanently(self) -> None:
        if self.debug:
            print("Dauerhaft keine WLAN-Verbindung, keine Verbindung zu Hotspot. Deaktiviere WLAN!")
        self.wlan_deactivated = True
        self.hotspot_mode = False
        try:
            self.wlan.disconnect()
            self.wlan.active(False)
            await asyncio.sleep(2)
            self.wlan.deinit()
        except Exception as e:
            await self.pr.err_s(_NAME, "Error deactivating WLAN:", e, errno=6)

    async def time_counter(self) -> None:
        await self.wifi_uptime.set_value(0)
        while True:
            await self.time_counter_trigger_event.wait()
            if self.wlan_deactivated:
                await self.wifi_uptime.set_value(0)
                await self._update_wifi_snapshot(False)
                continue
            await self.wifi_mode_lock.acquire()
            try:
                connected = self._wlan_status_or_none() == network.STAT_GOT_IP
                if connected:
                    await self.wifi_uptime.increment()
                else:
                    await self.wifi_uptime.set_value(0)
                await self._update_wifi_snapshot(connected)
            finally:
                self._release_wifi_lock()

    async def _update_wifi_snapshot(self, connected: bool) -> None:
        mode = "AP" if self.hotspot_mode else "STA"
        ip = None
        try:
            ifcfg = self.wlan.ifconfig()
            if len(ifcfg) == 4:
                ip = ifcfg[0]
        except Exception as e:  # observation-tier - see _wlan_status_or_none()'s comment
            self.pr.err(_NAME, "wlan.ifconfig() failed:", e)
        await self._set_meas_data(WIFI(mode, connected, ip, self._now()))
