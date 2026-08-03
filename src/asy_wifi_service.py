"""Async WiFi connection/hotspot/LED service. Not a sensor, but config-managed the same way: extends
base_classes.py's SensorReaderConfig, owns its own config_WIFI.cfg (see DRIVER_SPEC.md). "Attempt"
operations persist a real errno via self.pr.err_s() and set self.hw_op_failed, feeding
wlan_connect()'s _error_check() streak; routine state observations degrade silently via
self.pr.err() instead. errno numbering starts at 11, same convention as asy_ntp_client.py.
"""

import asyncio
import time
from collections import namedtuple

import network
from machine import Pin, Timer
from micropython import const

from base_classes import LockedCounter, SensorReaderConfig
from captive_dns import DNSServer
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


# Schema tuples for ConfigManager.get_*_values() - min/max mirror sensortask-wozi.py's REST bounds,
# except SSID/PW's min is relaxed to 0 (fresh "" default) and Hostname's max is 32, network.hostname()'s
# real hard cap, not the REST route's still-open 1-63.
_VAL_SSID = const((("SSID", "str", "", 0, 32, None),))
_VAL_PW = const((("PW", "str", "", 0, 63, None),))
_VAL_CTRY = const((("Country", "str", "DE", 2, 2, None),))
_VAL_HOST = const((("Hostname", "str", "SensorNode", 1, 32, None),))
_VAL_LED = const((("LedWifiOn", "bool", True, None, None, None),))

_NAME = const("WIFI")
WIFI = namedtuple("WIFI", ("Mode", "Connected", "IP", "TS"))

_STA_DISCONNECT_WAIT_ITERS = const(20)  # 20 * 0.5s = 10s max wait for isconnected() to clear -
# bounds _disconnect_sta_and_wait()'s loop; a real disconnect() completes far faster than this.

# self._conn_phase - the connection state machine. Not importable as a module attribute once
# const()-folded (see tests/test_asy_wifi_service.py's own mirrored copy), same tradeoff as every
# constant here.
_PHASE_STA_SEEKING = const(0)  # STA mode, has not connected successfully since the last reset
_PHASE_STA_ESTABLISHED = const(1)  # STA mode, connected at least once since the last reset - live
# wlan.isconnected() still distinguishes "connected" from "disconnected, retrying every 60s".
_PHASE_HOTSPOT = const(2)  # AP/hotspot fallback mode active
_PHASE_DEACTIVATED = const(3)  # terminal - WLAN fully deactivated, needs a task/device restart


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
        max_i2c_err: int = 5,  # consecutive hw_op_failed cycles before giving up and letting the
        # task supervisor restart this task - same _error_check() contract every Reader uses,
        # despite the misleading "i2c" name inherited from SensorReaderConfig (no I2C bus here).
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
        self.dns_server = DNSServer(debug=bool(debug))
        self.dns_server_task: asyncio.Task[None] | None = None
        self.reconn_wifi = False
        self.time_counter_trigger_event = asyncio.ThreadSafeFlag()
        self.wifi_mode_lock = asyncio.Lock()
        self.counter_timer = Timer()
        self.hotspot_timer = Timer()
        self.hotspot_timer_running = False
        self.ledflash: asyncio.Task[None] | None = None
        # wlan_connect()'s own state machine - reset at the top of every wlan_connect() call
        # (i.e. every task (re)start), not meant to be read from outside this class.
        self._conn_phase = _PHASE_STA_SEEKING
        self.connection_failures = 0
        self.hotspot_started_once = False
        self.hw_op_failed = False  # this loop iteration's flag feeding _error_check(), see wlan_connect()

    def _now(self) -> int | None:
        try:
            return time.mktime(time.gmtime())
        except (OverflowError, OSError):  # rp2's mktime()/gmtime() raise past its ~2037 32-bit epoch range
            return None

    async def _mask_pw(self) -> dict[str, int | float | str | bool | None]:
        # PW is a real credential. sensortask-wozi.py's /net/config route already masks it before
        # returning it ("********") - reusing _get_dict_cfg()'s callback overlay keeps that masking
        # in the generic getter-quartet path too, so it can't leak the plaintext value elsewhere.
        return {"PW": "********"}

    def _wlan_status_or_none(self) -> int | None:
        # Observation-tier: a status query failing (WLAN mid-transition/deinitialized) is routine
        # enough to degrade silently - the state machine's own "attempt" methods persist a real errno.
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

    def _release_wifi_lock(self) -> None:
        try:
            self.wifi_mode_lock.release()
        except RuntimeError:  # in case it's already released somehow
            pass

    def _led_on(self) -> None:
        if self.led is not None:
            try:  # self.led may be a caller-supplied ext_led (LEDControl Protocol, not necessarily
                # a real Pin) - could legitimately misbehave. Purely decorative status, so degrades
                # silently rather than feeding hw_op_failed/_error_check() (that's about the WLAN
                # hardware, not the LED).
                self.led.on()
            except Exception as e:
                self.pr.err(_NAME, "LED on() failed:", e)

    def _led_off(self) -> None:
        if self.led is not None:
            try:  # see _led_on()'s comment
                self.led.off()
            except Exception as e:
                self.pr.err(_NAME, "LED off() failed:", e)

    def _led_toggle(self) -> None:
        if self.led is not None:
            try:  # see _led_on()'s comment
                self.led.toggle()
            except Exception as e:
                self.pr.err(_NAME, "LED toggle() failed:", e)

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
            self.pr.all(_NAME, "Wifi inactive")
            await asyncio.sleep(2)
            self.wlan.deinit()
            self.pr.all(_NAME, "Wifi off")
            await asyncio.sleep(1)
            await self.wifi_uptime.set_value(0)
            self.wlan = network.WLAN(mode)
            self.pr.all(_NAME, "Wifi mode set")
            await asyncio.sleep(1)
        except Exception as e:
            self.hw_op_failed = True
            await self.pr.err_s(_NAME, "Error switching WLAN mode:", e, errno=11)

    def _reset_wlan_connect_state(self) -> None:
        if self.ledflash is not None:
            self.ledflash.cancel()
            self.ledflash = None
        if self.dns_server_task is not None:
            self.dns_server_task.cancel()
            self.dns_server_task = None
        self.connection_failures = 0
        self.hotspot_started_once = False
        if self._conn_phase != _PHASE_HOTSPOT:
            # Deliberately left at _PHASE_HOTSPOT on a task restart mid-hotspot (matches the old
            # code's behavior) - reconn_wifi below and wlan_connect()'s first iteration both still
            # see it and route through the same forced leave-hotspot-and-reconnect path.
            self._conn_phase = _PHASE_STA_SEEKING
        self.hotspot_timer.deinit()
        self.hotspot_timer_running = False
        try:
            self.reconn_wifi = (self._conn_phase == _PHASE_HOTSPOT) or self.wlan.isconnected() or bool(self.wlan.active())
        except Exception as e:  # rare (once per task (re)start) - safe default forces a clean reconnect
            self.pr.err(_NAME, "Error checking WLAN state at start:", e)
            self.reconn_wifi = True
        # clear possible previous connections
        self._led_off()

    async def _apply_initial_led_config(self) -> None:
        led_cfg = await self._read_wifi_led_cfg()
        if led_cfg is None:
            await self.set_wifi_led(False)
            self._conn_phase = _PHASE_DEACTIVATED
            await self.pr.wrn_s(_NAME, "Fehlende WLAN Konfiguration!", wrnno=1)
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
        leaving_hotspot = self._conn_phase == _PHASE_HOTSPOT
        if not leaving_hotspot:
            # _leave_hotspot_mode() below already lands on this same value via its own transition -
            # only the plain-STA-reconnect path needs it set here.
            self._conn_phase = _PHASE_STA_SEEKING
        self.pr.evt(_NAME, "WLAN Reconnect ausgelöst!")
        await asyncio.sleep(5)  # allow final tasks of calling function
        if leaving_hotspot:  # mode switch
            await self._leave_hotspot_mode()
        else:  # plain reconnect
            await self._wait_for_sta_disconnect()
        await asyncio.sleep(3)  # wait once for whatever else to settle

    async def _leave_hotspot_mode(self) -> None:
        self._conn_phase = _PHASE_STA_SEEKING
        if self.dns_server_task is not None:
            self.dns_server_task.cancel()
            self.dns_server_task = None
        await self._select_wifi_mode(network.STA_IF)
        self._led_off()
        self.pr.one(_NAME, "WLAN Hotspot wurde ausgeschaltet")

    async def _wait_for_sta_disconnect(self) -> None:
        self.pr.evt(_NAME, "WLAN neu verbinden...")
        await self.wifi_mode_lock.acquire()
        try:
            await self._disconnect_sta_and_wait()
        finally:
            self._release_wifi_lock()
        self._led_off()
        self.pr.evt(_NAME, "WLAN ist getrennt")

    async def _disconnect_sta_and_wait(self) -> None:
        try:
            self.wlan.disconnect()
            for _i in range(_STA_DISCONNECT_WAIT_ITERS):  # bounded - a driver that never actually
                # disconnects (isconnected() staying True forever) must not hang this task forever;
                # matches _poll_sta_connect_status()'s own bounded for-loop convention.
                if not self.wlan.isconnected():
                    break
                self._led_toggle()
                await asyncio.sleep(0.5)
            else:
                self.hw_op_failed = True
                await self.pr.err_s(_NAME, "Timed out waiting for STA disconnect", errno=18)
        except Exception as e:
            self.hw_op_failed = True
            await self.pr.err_s(_NAME, "Error waiting for STA disconnect:", e, errno=15)

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
                await self.pr.wrn_s(_NAME, "Fehlende WLAN Konfiguration!", wrnno=2)
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
            self.hw_op_failed = True
            await self.pr.err_s(_NAME, "Error activating hotspot AP:", e, errno=12)

    def _configure_hotspot_ap(self, country: str, hostname: str) -> None:
        network.country(country)  # Country
        network.hostname(hostname)  # Hostname
        self.wlan.config(essid=hostname, password="12345678")
        self.wlan.active(True)
        self.wlan.config(pm=0xA11140)  # Stromsparmodus ausschalten
        own_ip, own_netmask = self.wlan.ifconfig()[:2]
        evtloop = asyncio.get_event_loop()
        self.dns_server_task = evtloop.create_task(self.dns_server.run(own_ip, own_netmask))
        self.pr.one(_NAME, "WLAN Hotspot wurde gestartet")

    async def _manage_hotspot_stations(self) -> None:
        self.pr.all(_NAME, "Hotspot Mode ist aktiv")
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
            self.pr.all(_NAME, "Connected stations:", stations)
            return stations  # type: ignore[return-value]  # stub types status(str) as int; real AP-mode "stations" returns a list per MicroPython docs
        except Exception as e:  # observation-tier (polled every wifi_refresh_sec while hotspot is
            # active) - see _wlan_status_or_none()'s comment on why this stays silent, not err_s()
            self.pr.err(_NAME, "Verbundene Clients können nicht abgerufen werden:", e)
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
        self.pr.evt(_NAME, "Client mit Hotspot verbunden, Timer gestoppt")

    def _hotspot_client_absent(self) -> None:
        if not self.hotspot_timer_running:
            self.pr.evt(_NAME, "Kein Client verbunden - Hotspot Timer gestartet")
            try:
                self.hotspot_timer.init(
                    period=self.hotspot_time,
                    mode=Timer.ONE_SHOT,
                    callback=lambda b: self.reconnect_wifi(),
                )
                self.hotspot_timer_running = True  # try to reconnect once after hotspot time if no client connected (maybe router reboot after power loss)
            except OSError as e:  # alarm-pool exhaustion (ENOMEM) - matches asy_ntp_client.py's own
                # Timer.init() guards; hotspot_timer_running stays False so the next
                # wifi_refresh_sec cycle retries arming it instead of getting stuck unset.
                self.pr.err(_NAME, "Could not start hotspot timer:", e)
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
        self.pr.evt(_NAME, "WLAN-Verbindung herstellen")
        led_cfg = await self._read_wifi_led_cfg()
        await self.set_wifi_led(False if led_cfg is None else led_cfg)
        wifi_cfg = await self.cfgmgr.get_str_values(_VAL_SSID + _VAL_PW + _VAL_CTRY + _VAL_HOST)
        if wifi_cfg is None or len(wifi_cfg) != 4:
            await self.pr.wrn_s(_NAME, "Fehlende WLAN Konfiguration!", wrnno=3)
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
            self.hw_op_failed = True
            await self.pr.err_s(_NAME, "Error attempting STA connect:", e, errno=13)
            return False

    async def _poll_sta_connect_status(self) -> None:
        for _i in range(10):
            self._led_toggle()
            try:
                status = self.wlan.status()
            except Exception as e:
                self.hw_op_failed = True
                await self.pr.err_s(_NAME, "Error polling STA connect status:", e, errno=14)
                return
            if status == network.STAT_IDLE:
                self.pr.all(_NAME, "WLAN idle")
            elif status == network.STAT_CONNECTING:
                self.pr.all(_NAME, "WLAN connecting")
            elif status == 2:  #  not defined by constant in class yet!
                self.pr.all(_NAME, "WLAN obtaining IP")
            elif status == network.STAT_WRONG_PASSWORD:
                await self.pr.wrn_s(_NAME, "WLAN wrong password", wrnno=4)
                return
            elif status == network.STAT_NO_AP_FOUND:
                await self.pr.wrn_s(_NAME, "WLAN access point not found", wrnno=5)
                return
            elif status == network.STAT_CONNECT_FAIL:
                await self.pr.wrn_s(_NAME, "WLAN connection failed", wrnno=6)
                return
            elif status == network.STAT_GOT_IP:
                self.pr.all(_NAME, "WLAN connection successful")
            else:
                await self.pr.wrn_s(_NAME, "WLAN undefined state:", status, wrnno=7)
                return
            await asyncio.sleep(0.5)

    async def _handle_sta_connection_result(self) -> None:
        if self._wlan_isconnected_or_false():
            self._on_sta_connected()
        else:
            await self._on_sta_disconnected()

    def _on_sta_connected(self) -> None:
        self.pr.one(_NAME, "WLAN-Verbindung hergestellt")
        self._conn_phase = _PHASE_STA_ESTABLISHED
        self.connection_failures = 0
        self._led_on()
        self._print_wlan_diagnostics()

    def _print_wlan_diagnostics(self) -> None:  # self.pr.all() self-gates on the configured level
        try:
            self.pr.all(_NAME, "WLAN-Status:", self.wlan.status())
            net_config = self.wlan.ifconfig()
            self.pr.all(_NAME, "IPv4-Adresse:", net_config[0], "/", net_config[1])
            self.pr.all(_NAME, "Standard-Gateway:", net_config[2])
            self.pr.all(_NAME, "DNS-Server:", net_config[3])
        except Exception as e:  # observation-tier - see _wlan_status_or_none()'s comment
            self.pr.err(_NAME, "WLAN diagnostic read failed:", e)

    async def _on_sta_disconnected(self) -> None:
        self.pr.evt(_NAME, "Keine WLAN-Verbindung")
        if self._conn_phase == _PHASE_STA_ESTABLISHED:
            self.pr.evt(_NAME, "WLAN-Verbindung war zuvor erfolgreich, neuer Versuch in 1 Minute...")
            await asyncio.sleep(60)  # retry previously successful connecion in one minute
        else:
            await self._register_sta_connection_failure()
        self._led_off()
        self.pr.all(_NAME, "WLAN-Status:", self._wlan_status_or_none())

    async def _register_sta_connection_failure(self) -> None:
        if self.connection_failures < (self.conn_fail_to_hotspot - 1):
            self.connection_failures += 1
            self.pr.evt(_NAME, "Zähler für fehlgeschlagene Verbindungen:", self.connection_failures)
            return
        self.connection_failures = 0
        if self.hotspot_started_once:
            await self._deactivate_wlan_permanently()
        else:
            self._conn_phase = _PHASE_HOTSPOT
            self.pr.one(_NAME, "Dauerhaft keine WLAN-Verbindung - aktiviere Hotspot!")

    async def _deactivate_wlan_permanently(self) -> None:
        self.pr.one(_NAME, "Dauerhaft keine WLAN-Verbindung, keine Verbindung zu Hotspot. Deaktiviere WLAN!")
        self._conn_phase = _PHASE_DEACTIVATED
        try:
            self.wlan.disconnect()
            self.wlan.active(False)
            await asyncio.sleep(2)
            self.wlan.deinit()
        except Exception as e:
            self.hw_op_failed = True
            await self.pr.err_s(_NAME, "Error deactivating WLAN:", e, errno=16)

    async def _update_wifi_snapshot(self, connected: bool) -> None:
        mode = "AP" if self._conn_phase == _PHASE_HOTSPOT else "STA"
        ip = None
        try:
            ifcfg = self.wlan.ifconfig()
            if len(ifcfg) == 4:
                ip = ifcfg[0]
        except Exception as e:  # observation-tier - see _wlan_status_or_none()'s comment
            self.pr.err(_NAME, "wlan.ifconfig() failed:", e)
        await self._set_meas_data(WIFI(mode, connected, ip, self._now()))

    def start_asy_wlan_connect(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.wlan_connect())

    def start_asy_uptime_counter(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.time_counter())

    def start_counter_timer(self) -> None:
        try:
            self.counter_timer.init(
                period=1000,
                mode=Timer.PERIODIC,
                callback=lambda b: self.time_counter_trigger_event.set(),
            )
        except OSError as e:  # alarm-pool exhaustion (ENOMEM) - degrades gracefully instead of
            # crashing the caller (uptime counting just never starts this cycle).
            self.pr.err(_NAME, "Could not start counter timer:", e)

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_wlan_connect, self.start_asy_uptime_counter]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return [self.start_counter_timer]

    async def get_data(self) -> WIFI:
        # Narrows _get_meas_data()'s generic NamedTuple to this Reader's concrete WIFI, matching
        # asy_ntp_client.py's own convention. Backed by time_counter()'s 1Hz cache push rather than
        # a live lock-aware query - avoids a transient "unknown" reading mid-mode-switch.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data)

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(
            _NAME, _VAL_SSID + _VAL_PW + _VAL_CTRY + _VAL_HOST + _VAL_LED, callback=self._mask_pw
        )

    async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:
        return await self.pr.get_log(_NAME)

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
        return None  # type: ignore[unreachable]  # defensive: real WLAN.ifconfig() is a fixed 4-tuple per the stub

    def get_dns_server_ip(self) -> str | None:
        # asy_ntp_client.py's get_dns_server callback - the DHCP-assigned DNS server for
        # resolve_ipv4() to try first. Reuses get_wlan_ifconfig()'s own None-on-failure convention.
        ifcfg = self.get_wlan_ifconfig()
        return None if ifcfg is None else ifcfg[3]

    def get_wlan_rssi(self) -> int | None:
        if self.wifi_mode_lock.locked():
            return None
        try:
            rssi = int(self.wlan.status("rssi"))  # not valid in AP mode!
        except Exception as e:  # observation-tier - see _wlan_status_or_none()'s comment. Confirmed
            # via extmod/network_cyw43.c: querying "rssi" outside STA mode raises
            # ValueError("STA required"), a routine failure while hotspot_mode is active - still
            # logs, unlike a silent swallow.
            self.pr.err(_NAME, "wlan.status('rssi') failed:", e)
            rssi = None
        return rssi

    def get_wifi_mode_lock(self) -> asyncio.Lock:
        return self.wifi_mode_lock

    async def get_wifi_uptime(self) -> int:
        value = await self.wifi_uptime.get_value()  # never None: never constructed/set with a None sentinel
        return 0 if value is None else value

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

    def stop_counter_timer(self) -> None:
        self.counter_timer.deinit()

    def reconnect_wifi(self) -> None:
        self.hotspot_timer.deinit()
        self.hotspot_timer_running = False
        if self.ledflash is not None:
            self.ledflash.cancel()
            self.ledflash = None
        self.reconn_wifi = True

    def wlan_isconnected(self) -> bool:
        if self.wifi_mode_lock.locked():
            return False
        return self._wlan_isconnected_or_false()

    def network_available(self) -> bool:  # caller must already hold wifi_mode_lock
        return (self._conn_phase != _PHASE_HOTSPOT) and (self._wlan_status_or_none() == network.STAT_GOT_IP)

    async def wlan_connect(self) -> None:  # Funktion: WLAN-Verbindung
        await self.pr.setup()  # required for all logged warnings and errors (base_classes.py's own
        # __init__ never calls this - matches every _init_<sensor>() in the three promoted drivers)
        self._err_cnt_internal = 0  # fresh failure streak each task (re)start, same as _init_<sensor>()
        self._reset_wlan_connect_state()
        await self._apply_initial_led_config()
        while True:
            if self._conn_phase == _PHASE_DEACTIVATED:
                self.pr.all(_NAME, "WLAN ist deaktiviert.")
            else:
                self.hw_op_failed = False
                if self.reconn_wifi:
                    await self._handle_reconnect_trigger()
                if self._conn_phase == _PHASE_HOTSPOT:
                    await self._run_hotspot_mode()
                else:
                    await self._run_sta_mode()
                # Consecutive-failure streak over real WLAN-hardware exceptions (separate from
                # connection_failures' AP-reachability fallback): gives up on the whole task,
                # matching a Reader's read_loop() returning False.
                if not await self._error_check((None,) if self.hw_op_failed else (1,), _NAME):
                    await self.pr.err_s(
                        _NAME, "Giving up after repeated WLAN hardware failures, restarting task.", errno=17
                    )
                    return
            await asyncio.sleep(self.wifi_refresh_sec)

    async def time_counter(self) -> None:
        await self.wifi_uptime.set_value(0)
        while True:
            await self.time_counter_trigger_event.wait()
            if self._conn_phase == _PHASE_DEACTIVATED:
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
