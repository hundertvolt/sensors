import network
import asyncio
from uasyncio import Lock, ThreadSafeFlag
from captive_dns import DNSServer
from machine import Pin, Timer
from micropython import const
from async_manager import ConfigManager
from base_classes import LockedCounter
from typing import Tuple

try:
    from typing import Protocol
except Exception:

    class Protocol:  # type: ignore[no-redef]
        pass  # micropython does not support typing Protocol


_DEFAULT_CONFIG = const(
    '{"SSID": "", "PW": "", "Country": "DE", "Hostname": "SensorNode", "LedWifiOn": true}'
)


class LEDControl(Protocol):
    def on(self) -> None: ...
    def off(self) -> None: ...
    def toggle(self) -> None: ...


class asy_conn_time:
    def __init__(
        self,
        cfgmgr: ConfigManager,
        conn_fail_to_hotspot: int = 5,
        led_pin: int | None = None,
        ext_led: LEDControl | None = None,
        wifi_refresh_sec: int = 5,
        hotspot_time_min: int = 5,
        debug: bool = False,
    ) -> None:
        self.wlan = network.WLAN(network.STA_IF)
        self.led_pin = None if led_pin is None else Pin(led_pin, mode=Pin.OUT, value=0)
        self.ext_led = ext_led
        self.led: LEDControl | None = None
        self.wifi_refresh_sec = wifi_refresh_sec
        self.hotspot_time = 60000 * hotspot_time_min  # convert to ms
        self.conn_fail_to_hotspot = conn_fail_to_hotspot
        self.wifi_uptime = LockedCounter(max_val=0xFFFFFFFF)
        self.hotspot_mode = False
        self.debug = debug
        self.dns_server = DNSServer(debug=self.debug)
        self.dns_server_task: asyncio.Task[None] | None = None
        self.cfgmgr = cfgmgr
        self.reconn_wifi = False
        self.time_counter_trigger_event = ThreadSafeFlag()
        self.wifi_mode_lock = Lock()
        self.counter_timer = Timer()
        self.hotspot_timer = Timer()
        self.hotspot_timer_running = False
        self.ledflash: asyncio.Task[None] | None = None

    @staticmethod
    def get_default_cfg() -> Dict[str, int | float | str | bool]:
        try:
            res = json.load(_DEFAULT_CONFIG)
            if isinstance(res, dict):
                return res
        except Exception:
            pass
        return {}

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
        return self.wlan.isconnected()

    def get_wlan_ifconfig(self) -> Tuple[str, str, str, str] | None:
        if self.wifi_mode_lock.locked():
            return None
        ifcfg = self.wlan.ifconfig()
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

    def network_available(self) -> bool:  # caller must already hold wifi_mode_lock
        return (not self.hotspot_mode) and (self.wlan.status() == network.STAT_GOT_IP)

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
            if self.led is not None:
                self.led.off()
            self.led = None

    async def get_wifi_uptime(self) -> int:
        value = await self.wifi_uptime.get_value()  # never None: never constructed/set with a None sentinel
        return 0 if value is None else value

    async def _flash_led_off(self) -> None:
        while True:
            try:
                if self.led is not None:
                    self.led.on()
                await asyncio.sleep(2.9)
                if self.led is not None:
                    self.led.off()
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                if self.led is not None:
                    self.led.on()
                break

    async def _select_wifi_mode(self, mode: int) -> None:
        await self.wifi_mode_lock.acquire()
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
        finally:
            try:
                self.wifi_mode_lock.release()
            except RuntimeError:  # in case it's already released somehow
                pass

    async def wlan_connect(self) -> None:  # Funktion: WLAN-Verbindung
        if self.ledflash is not None:
            self.ledflash.cancel()
            self.ledflash = None
        if self.dns_server_task is not None:
            self.dns_server_task.cancel()
            self.dns_server_task = None
        connection_failures = 0
        hotspot_started_once = False
        wlan_connected_once = False
        wlan_deactivated = False
        self.hotspot_timer.deinit()
        self.hotspot_timer_running = False
        self.reconn_wifi = (
            self.hotspot_mode or self.wlan.isconnected() or self.wlan.active()  # type: ignore[func-returns-value]
        )  # clear possible previous connections
        if self.led is not None:
            self.led.off()
        wifi_led = await self.cfgmgr.get_bool_values(["LedWifiOn"])
        if wifi_led is None or len(wifi_led) != 1:
            await self.set_wifi_led(False)
            wlan_deactivated = True
            if self.debug:
                print("Fehlende WLAN Konfiguration!")
        else:
            await self.set_wifi_led(wifi_led[0])
        del wifi_led
        while True:
            if wlan_deactivated:
                if self.debug:
                    print("WLAN ist deaktiviert.")
            else:
                if self.reconn_wifi:
                    self.hotspot_timer.deinit()
                    self.hotspot_timer_running = False
                    if self.ledflash is not None:
                        self.ledflash.cancel()
                        self.ledflash = None
                    self.reconn_wifi = False
                    wlan_connected_once = False
                    if self.debug:
                        print("WLAN Reconnect ausgelöst!")
                    await asyncio.sleep(5)
                    # allow final tasks of calling function
                    if self.hotspot_mode:  # mode switch
                        self.hotspot_mode = False
                        if self.dns_server_task is not None:
                            self.dns_server_task.cancel()
                            self.dns_server_task = None
                        await self._select_wifi_mode(network.STA_IF)
                        if self.led is not None:
                            self.led.off()
                        if self.debug:
                            print("WLAN Hotspot wurde ausgeschaltet")
                    else:  # plain reconnect
                        if self.debug:
                            print("WLAN neu verbinden...")
                        await self.wifi_mode_lock.acquire()
                        try:
                            self.wlan.disconnect()
                            while self.wlan.isconnected():  # wait until disconnected
                                if self.led is not None:
                                    self.led.toggle()
                                await asyncio.sleep(0.5)
                        finally:
                            try:
                                self.wifi_mode_lock.release()
                            except RuntimeError:  # in case it's already released somehow
                                pass
                        if self.led is not None:
                            self.led.off()
                        if self.debug:
                            print("WLAN ist getrennt")
                    await asyncio.sleep(3)
                    # wait once for whatever else to settle
                if self.hotspot_mode:
                    await self.wifi_mode_lock.acquire()
                    status: int | None = None
                    try:
                        status = self.wlan.status()
                    finally:
                        try:
                            self.wifi_mode_lock.release()
                        except RuntimeError:  # in case it's already released somehow
                            pass
                    if status != network.STAT_GOT_IP:
                        await self._select_wifi_mode(network.AP_IF)
                        await self.wifi_mode_lock.acquire()
                        try:
                            wifi_cfg = await self.cfgmgr.get_str_values(["Country", "Hostname"])
                            wifi_led = await self.cfgmgr.get_bool_values(["LedWifiOn"])
                            if wifi_cfg is None or wifi_led is None or len(wifi_cfg) != 2 or len(wifi_led) != 1:
                                if self.debug:
                                    print("Fehlende WLAN Konfiguration!")
                                await self.set_wifi_led(False)
                            else:
                                await self.set_wifi_led(wifi_led[0])
                                network.country(wifi_cfg[0])  # Country
                                network.hostname(wifi_cfg[1])  # Hostname
                                self.wlan.config(essid=wifi_cfg[1], password="12345678")
                                self.wlan.active(True)
                                self.wlan.config(pm=0xA11140)  # Stromsparmodus ausschalten
                                own_ip, own_netmask = self.wlan.ifconfig()[:2]
                                evtloop = asyncio.get_event_loop()
                                self.dns_server_task = evtloop.create_task(self.dns_server.run(own_ip, own_netmask))
                                del evtloop, own_ip, own_netmask
                                if self.debug:
                                    print("WLAN Hotspot wurde gestartet")
                            del wifi_cfg, wifi_led
                            hotspot_started_once = True
                        finally:
                            try:
                                self.wifi_mode_lock.release()
                            except RuntimeError:  # in case it's already released somehow
                                pass
                    else:  # got hotspot IP
                        if self.debug:
                            print("Hotspot Mode ist aktiv")
                        await self.wifi_mode_lock.acquire()
                        stations = []
                        try:
                            await asyncio.sleep(0.1)
                            # stations command needs no other status commands close before (and does not support "async with"!)
                            stations = self.wlan.status("stations")
                            if self.debug:
                                print("Connected stations:", stations)
                        except Exception as e:
                            if self.debug:
                                print("Verbundene Clients können nicht abgerufen werden:", e)
                            stations = []
                        finally:
                            try:
                                self.wifi_mode_lock.release()
                            except RuntimeError:  # in case it's already released somehow
                                pass
                        if len(stations) > 0:  # at least one client connected
                            self.hotspot_timer.deinit()  # if client connected, do not stop hotspot
                            self.hotspot_timer_running = False
                            if self.ledflash is None:
                                if self.led is not None:
                                    self.led.on()
                            else:
                                self.ledflash.cancel()
                                self.ledflash = None
                            if self.debug:
                                print("Client mit Hotspot verbunden, Timer gestoppt")
                        else:  # no client connected
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
                                del evtloop
                        del stations
                else:  # hotspot_mode
                    await self.wifi_mode_lock.acquire()
                    try:
                        if not self.wlan.isconnected():
                            if self.debug:
                                print("WLAN-Verbindung herstellen")
                            wifi_led = await self.cfgmgr.get_bool_values(["LedWifiOn"])
                            if wifi_led is None or len(wifi_led) != 1:
                                await self.set_wifi_led(False)
                            else:
                                await self.set_wifi_led(wifi_led[0])
                            del wifi_led
                            wifi_cfg = await self.cfgmgr.get_str_values(["SSID", "PW", "Country", "Hostname"])
                            if wifi_cfg is None or len(wifi_cfg) != 4:
                                if self.debug:
                                    print("Fehlende WLAN Konfiguration!")
                            else:
                                if wifi_cfg[0] == "":  # SSID - invalid or empty config
                                    connection_failures = self.conn_fail_to_hotspot  # immediate hotspot mode
                                else:
                                    network.country(wifi_cfg[2])  # Country
                                    network.hostname(wifi_cfg[3])  # Hostname
                                    self.wlan.active(True)
                                    self.wlan.config(pm=0xA11140)  # Stromsparmodus ausschalten
                                    self.wlan.connect(wifi_cfg[0], wifi_cfg[1])  # SSID, PW
                                    for i in range(10):
                                        if self.led is not None:
                                            self.led.toggle()
                                        status = self.wlan.status()
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
                                            break
                                        elif status == network.STAT_NO_AP_FOUND:
                                            if self.debug:
                                                print("WLAN access point not found")
                                            break
                                        elif status == network.STAT_CONNECT_FAIL:
                                            if self.debug:
                                                print("WLAN connection failed")
                                            break
                                        elif status == network.STAT_GOT_IP:
                                            if self.debug:
                                                print("WLAN connection successful")
                                        else:
                                            if self.debug:
                                                print("WLAN undefined state")
                                            break
                                        await asyncio.sleep(0.5)
                                    del status
                            del wifi_cfg
                        if self.wlan.isconnected():
                            if self.debug:
                                print("WLAN-Verbindung hergestellt")
                            wlan_connected_once = True
                            connection_failures = 0
                            if self.led is not None:
                                self.led.on()
                            if self.debug:
                                print("WLAN-Status:", self.wlan.status())
                                net_config = self.wlan.ifconfig()
                                print("IPv4-Adresse:", net_config[0], "/", net_config[1])
                                print("Standard-Gateway:", net_config[2])
                                print("DNS-Server:", net_config[3])
                                del net_config
                        else:
                            if self.debug:
                                print("Keine WLAN-Verbindung")
                            if wlan_connected_once:
                                if self.debug:
                                    print("WLAN-Verbindung war zuvor erfolgreich, neuer Versuch in 1 Minute...")
                                await asyncio.sleep(60)
                                # retry previously successful connecion in one minute
                            else:  # wlan_connected_once
                                if connection_failures < (self.conn_fail_to_hotspot - 1):
                                    connection_failures += 1
                                    if self.debug:
                                        print(
                                            "Zähler für fehlgeschlagene Verbindungen:",
                                            connection_failures,
                                        )
                                else:
                                    connection_failures = 0
                                    if hotspot_started_once:
                                        if self.debug:
                                            print(
                                                "Dauerhaft keine WLAN-Verbindung, keine Verbindung zu Hotspot. Deaktiviere WLAN!"
                                            )
                                        wlan_deactivated = True
                                        self.wlan.disconnect()
                                        self.wlan.active(False)
                                        self.hotspot_mode = False
                                        await asyncio.sleep(2)
                                        self.wlan.deinit()
                                    else:
                                        self.hotspot_mode = True
                                        if self.debug:
                                            print("Dauerhaft keine WLAN-Verbindung - aktiviere Hotspot!")
                            if self.led is not None:
                                self.led.off()
                            if self.debug:
                                print("WLAN-Status:", self.wlan.status())
                    finally:
                        try:
                            self.wifi_mode_lock.release()
                        except RuntimeError:  # in case it's already released somehow
                            pass
            await asyncio.sleep(self.wifi_refresh_sec)

    async def time_counter(self) -> None:
        await self.wifi_uptime.set_value(0)
        while True:
            await self.time_counter_trigger_event.wait()
            await self.wifi_mode_lock.acquire()
            try:
                if self.wlan.status() == network.STAT_GOT_IP:
                    await self.wifi_uptime.increment()
                else:
                    await self.wifi_uptime.set_value(0)
            finally:
                try:
                    self.wifi_mode_lock.release()
                except RuntimeError:  # in case it's already released somehow
                    pass
