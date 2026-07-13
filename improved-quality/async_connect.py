import time
import network
import socket
import struct
import asyncio
from uasyncio import Lock, ThreadSafeFlag
from asy_udp_socket import AsyUDPSocket
from captive_dns import DNSServer
from machine import Pin, Timer, RTC
from micropython import const
from async_manager import TimeCounterManager, LockedFlag, ConfigManager
from typing import Tuple
from collections import namedtuple

try:
    from typing import Protocol
except Exception:

    class Protocol:  # type: ignore[no-redef]
        pass  # micropython does not support typing Protocol


_NTP_ASYNC_INTERV = const(3)  # 3 times interval considered as out of sync
_NTP_CHECK_INTERV = const(10)  # seconds to count for NTP status update
_NTP_CONN_TIMEOUT = const(5000)  # 5s  to send request / receive an answer from NTP server
_NTP_SYNC_RETRIES = const(3)  # try 3 times to connect to NTP server before stopping
_NTP_RETRY_INTERV = const(15)  # wait 15 secs before retrying to sync

_DEFAULT_CONFIG = const(
    '{"SSID": "", "PW": "", "Country": "DE", "Hostname": "SensorNode", "LedWifiOn": true, "NTP_Host": "pool.ntp.org", "NTP_Offset_S": 0, "NTP_Interv_H": 12, "GMTOffset": 3600, "DSTOffset": 3600}'
)

GMTimeStruct = namedtuple("GMTimeStruct", ("year", "month", "mday", "hour", "minute", "second", "weekday", "yearday"))


class LEDControl(Protocol):
    def on(self) -> None: ...
    def off(self) -> None: ...
    def toggle(self) -> None: ...


class asy_conn_time:
    def __init__(
        self,
        cfgmgr: ConfigManager,
        asy_long_block_lock: Lock | None = None,
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
        self.wifi_uptime = TimeCounterManager()
        self.last_ntp_sync = TimeCounterManager(init_value=-1)
        self.ntp_sec_count = 0
        self.ntp_retries = 0
        self.ntp_synced = LockedFlag(init_value=False)
        self.hotspot_mode = False
        self.debug = debug
        self.dns_server = DNSServer(debug=self.debug)
        self.dns_server_task: asyncio.Task[None] | None = None
        self.cfgmgr = cfgmgr
        self.reconn_wifi = False
        self.ntp_sync_trigger_event = ThreadSafeFlag()
        self.ntp_timer_trigger_event = ThreadSafeFlag()
        self.time_counter_trigger_event = ThreadSafeFlag()
        self.asy_long_block_lock = Lock() if asy_long_block_lock is None else asy_long_block_lock
        self.wifi_mode_lock = Lock()
        self.ntp_timer = Timer()
        self.ntp_retry_timer = Timer()
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

    def start_asy_ntp_client(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.asy_ntp_time())

    def start_asy_ntp_refresh(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.ntp_time_hours_counter())

    def start_asy_uptime_counter(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.time_counter())

    def start_ntp_timer(self) -> None:
        self.ntp_timer.init(
            period=_NTP_CHECK_INTERV * 1000,
            mode=Timer.PERIODIC,
            callback=lambda b: self.ntp_timer_trigger_event.set(),
        )

    def start_counter_timer(self) -> None:
        self.counter_timer.init(
            period=1000,
            mode=Timer.PERIODIC,
            callback=lambda b: self.time_counter_trigger_event.set(),
        )

    def stop_ntp_timer(self) -> None:
        self.ntp_timer.deinit()

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

    def get_long_block_lock(self) -> Lock:
        return self.asy_long_block_lock

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

    async def ntp_issynced(self) -> bool:
        return await self.ntp_synced.get_value()

    async def get_wifi_uptime(self) -> int:
        return await self.wifi_uptime.get_counter()

    async def ntp_force_sync(self) -> None:
        await self.ntp_synced.set_false()
        await self.last_ntp_sync.set_counter(-1)
        self.ntp_retry_timer.deinit()
        self.ntp_retries = 0
        self.ntp_sync_trigger_event.set()
        if self.debug:
            print("NTP Force Resync triggered!")

    async def get_last_ntp_sync(self) -> int:
        return await self.last_ntp_sync.get_counter()

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
            await self.wifi_uptime.set_counter(0)
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
                                own_ip = self.wlan.ifconfig()[0]
                                evtloop = asyncio.get_event_loop()
                                self.dns_server_task = evtloop.create_task(self.dns_server.run(own_ip))
                                del evtloop, own_ip
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

    async def asy_ntp_time(self) -> None:  # Funktion: Zeit per NTP holen
        await self.ntp_synced.set_false()
        await self.last_ntp_sync.set_counter(-1)
        while True:
            await self.ntp_sync_trigger_event.wait()
            if self.debug:
                print("NTP Start Sync.")
            await self.wifi_mode_lock.acquire()
            try:
                if (not self.hotspot_mode) and (self.wlan.status() == network.STAT_GOT_IP):
                    ntp_host = await self.cfgmgr.get_str_values(["NTP_Host"])
                    ntp_offs = await self.cfgmgr.get_int_values(["NTP_Offset_S"])
                    if ntp_host is None or ntp_offs is None or len(ntp_host) != 1 or len(ntp_offs) != 1:
                        await self.ntp_synced.set_false()
                        if self.debug:
                            print("Fehlende NTP Konfiguration!")
                    else:
                        await self.asy_long_block_lock.acquire()  # getaddrinfo may block for some time
                        if self.debug:
                            print("NTP Long Block Lock acquired.")
                        addr = None
                        try:
                            addr = socket.getaddrinfo(ntp_host[0], 123)[0][-1]
                        except Exception as e:
                            if self.debug:
                                print("No valid NTP server:", e)
                            addr = None
                        finally:
                            await asyncio.sleep(0)
                            try:
                                self.asy_long_block_lock.release()
                            except RuntimeError:  # in case it's already released somehow
                                pass
                            if self.debug:
                                print("NTP Long Block Lock released.")

                        if addr is None:
                            msg = None
                        else:
                            cli = None
                            try:
                                cli = AsyUDPSocket(addr, mode="client")
                                msg, add = await cli.write_and_recvfrom(
                                    b"\x1b" + bytearray(47),
                                    1024,
                                    timeout_ms=_NTP_CONN_TIMEOUT,
                                )
                                del add
                                await cli.disconnect()
                            except Exception:
                                cli = msg = None
                            finally:
                                if cli is not None:
                                    await cli.disconnect()
                            del cli, add, addr

                        if msg is None:
                            if self.debug:
                                print("Invalid NTP Time received!")
                            self.ntp_retry_timer.deinit()
                            if (
                                await self.ntp_synced.get_value()
                            ):  # in case of already synced, retry if regular trigger fails
                                if (
                                    self.ntp_retries < _NTP_SYNC_RETRIES
                                ):  # if not synced at all, self.ntp_time_hours_counter() will permanently try to sync
                                    if self.debug:
                                        print("Waiting for NTP sync retry.")
                                    self.ntp_retry_timer.init(
                                        period=_NTP_RETRY_INTERV * 1000,
                                        mode=Timer.ONE_SHOT,
                                        callback=lambda b: self.ntp_sync_trigger_event.set(),
                                    )
                                    self.ntp_retries += 1
                                else:
                                    if self.debug:
                                        print("Maximum retries reached, cancelling sync!")
                                    self.ntp_retries = 0
                        else:
                            self.ntp_retry_timer.deinit()
                            self.ntp_retries = 0
                            ntp_time = (
                                (struct.unpack("!I", msg[40:44])[0]) - 2208988800 + ntp_offs[0]
                            )  # offset since 1970
                            if self.debug:
                                print("Received NTP time:", ntp_time)
                            tm = time.gmtime(ntp_time)
                            RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
                            await self.last_ntp_sync.set_counter(0)
                            await self.ntp_synced.set_true()
                            if self.debug:
                                print("RTC set to:", tm)
                    del ntp_host, ntp_offs, msg, ntp_time, tm
            finally:
                try:
                    self.wifi_mode_lock.release()
                except RuntimeError:  # in case it's already released somehow
                    pass

    async def ntp_time_hours_counter(self) -> None:  # Timer für NTP Refresh
        self.ntp_sec_count = 0
        while True:
            await self.ntp_timer_trigger_event.wait()
            ntp_interv = await self.cfgmgr.get_int_values(["NTP_Interv_H"])
            if ntp_interv is None or len(ntp_interv) != 1:
                ntp_interv = [12]
                if self.debug:
                    print("Fehlende NTP Konfiguration!")

            if await self.ntp_synced.get_value():
                if self.ntp_sec_count < (_NTP_ASYNC_INTERV * ntp_interv[0] * 60 * 60):
                    self.ntp_sec_count += _NTP_CHECK_INTERV
                else:
                    await self.ntp_synced.set_false()

            if self.debug:
                print("NTP Sekundenzähler auf", self.ntp_sec_count)
            if (not (await self.ntp_synced.get_value())) or (self.ntp_sec_count >= (ntp_interv[0] * 60 * 60)):
                self.ntp_retry_timer.deinit()
                self.ntp_retries = 0
                self.ntp_sync_trigger_event.set()
                self.ntp_sec_count = 0
                if self.debug:
                    print("NTP Synchronisation ausgelöst.")
            del ntp_interv

    async def cettime(
        self,
    ) -> GMTimeStruct | None:  # Umrechnung Lokalzeit
        if not (await self.ntp_synced.get_value()):
            return None
        time_offs = await self.cfgmgr.get_int_values(["GMTOffset", "DSTOffset"])
        if time_offs is None or len(time_offs) != 2:
            return None
        year = time.gmtime()[0]  # get current year
        HHMarch = time.mktime(
            (year, 3, (31 - (int(5 * year / 4 + 4)) % 7), 1, 0, 0, 0, 0, 0)  # type: ignore[call-arg]
        )  # Time of March change to CEST
        HHOctober = time.mktime(
            (year, 10, (31 - (int(5 * year / 4 + 1)) % 7), 1, 0, 0, 0, 0, 0)  # type: ignore[call-arg]
        )  # Time of October change to CET
        now = time.time()
        if now < HHMarch:  # we are before last sunday of march
            cet = time.gmtime(now + time_offs[0])  # GMTOffset -> CET:  UTC+1H
        elif now < HHOctober:  # we are before last sunday of october
            cet = time.gmtime(now + time_offs[0] + time_offs[1])  # GMTOffset + DSTOffset-> CEST: UTC+2H
        else:  # we are after last sunday of october
            cet = time.gmtime(now + time_offs[0])  # GMTOffset -> CET:  UTC+1H
        if len(cet) == 8:
            return GMTimeStruct(*cet)
        return None

    async def time_counter(self) -> None:
        await self.wifi_uptime.set_counter(0)
        await self.last_ntp_sync.set_counter(-1)
        while True:
            await self.time_counter_trigger_event.wait()
            await self.wifi_mode_lock.acquire()
            try:
                if self.wlan.status() == network.STAT_GOT_IP:
                    await self.wifi_uptime.increment()
                else:
                    await self.wifi_uptime.set_counter(0)
            finally:
                try:
                    self.wifi_mode_lock.release()
                except RuntimeError:  # in case it's already released somehow
                    pass

            if await self.ntp_synced.get_value():
                await self.last_ntp_sync.increment()
            else:
                await self.last_ntp_sync.set_counter(-1)
