import time
import socket
import struct
import asyncio
from uasyncio import Lock, ThreadSafeFlag
from asy_udp_socket import AsyUDPSocket
from machine import Timer, RTC
from micropython import const
from async_manager import ConfigManager
from base_classes import LockedCounter, LockedFlag
from typing import Callable
from collections import namedtuple

_NTP_ASYNC_INTERV = const(3)  # 3 times interval considered as out of sync
_NTP_CHECK_INTERV = const(10)  # seconds to count for NTP status update
_NTP_CONN_TIMEOUT = const(5000)  # 5s  to send request / receive an answer from NTP server
_NTP_SYNC_RETRIES = const(3)  # try 3 times to connect to NTP server before stopping
_NTP_RETRY_INTERV = const(15)  # wait 15 secs before retrying to sync

_DEFAULT_CONFIG = const(
    '{"NTP_Host": "pool.ntp.org", "NTP_Offset_S": 0, "NTP_Interv_H": 12, "GMTOffset": 3600, "DSTOffset": 3600}'
)

GMTimeStruct = namedtuple("GMTimeStruct", ("year", "month", "mday", "hour", "minute", "second", "weekday", "yearday"))


class asy_ntp_client:
    def __init__(
        self,
        cfgmgr: ConfigManager,
        wifi_mode_lock: Lock,
        network_available: Callable[[], bool],
        asy_long_block_lock: Lock | None = None,
        debug: bool = False,
    ) -> None:
        self.cfgmgr = cfgmgr
        self.wifi_mode_lock = wifi_mode_lock  # shared with asy_conn_time - protects the WLAN state this class only reads
        self.network_available = network_available  # asy_conn_time.network_available - caller must hold wifi_mode_lock
        self.last_ntp_sync = LockedCounter(init_value=None, max_val=0xFFFFFFFF)  # None = never synced yet
        self.ntp_sec_count = 0
        self.ntp_retries = 0
        self.ntp_synced = LockedFlag(init_value=False)
        self.debug = debug
        self.ntp_sync_trigger_event = ThreadSafeFlag()
        self.ntp_timer_trigger_event = ThreadSafeFlag()
        self.time_counter_trigger_event = ThreadSafeFlag()
        self.asy_long_block_lock = Lock() if asy_long_block_lock is None else asy_long_block_lock
        self.ntp_timer = Timer()
        self.ntp_retry_timer = Timer()
        self.counter_timer = Timer()

    @staticmethod
    def get_default_cfg() -> Dict[str, int | float | str | bool]:
        try:
            res = json.load(_DEFAULT_CONFIG)
            if isinstance(res, dict):
                return res
        except Exception:
            pass
        return {}

    def start_asy_ntp_client(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.asy_ntp_time())

    def start_asy_ntp_refresh(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.ntp_time_hours_counter())

    def start_asy_sync_age_counter(self) -> asyncio.Task[None]:
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

    def get_long_block_lock(self) -> Lock:
        return self.asy_long_block_lock

    async def ntp_issynced(self) -> bool:
        return await self.ntp_synced.get_value()

    async def ntp_force_sync(self) -> None:
        await self.ntp_synced.set_false()
        await self.last_ntp_sync.set_value(None)
        self.ntp_retry_timer.deinit()
        self.ntp_retries = 0
        self.ntp_sync_trigger_event.set()
        if self.debug:
            print("NTP Force Resync triggered!")

    async def get_last_ntp_sync(self) -> int | None:  # None = never synced yet
        return await self.last_ntp_sync.get_value()

    async def asy_ntp_time(self) -> None:  # Funktion: Zeit per NTP holen
        await self.ntp_synced.set_false()
        await self.last_ntp_sync.set_value(None)
        while True:
            await self.ntp_sync_trigger_event.wait()
            if self.debug:
                print("NTP Start Sync.")
            await self.wifi_mode_lock.acquire()
            try:
                if self.network_available():
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
                            await self.last_ntp_sync.set_value(0)
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
        await self.last_ntp_sync.set_value(None)
        while True:
            await self.time_counter_trigger_event.wait()
            if await self.ntp_synced.get_value():
                await self.last_ntp_sync.increment()
            else:
                await self.last_ntp_sync.set_value(None)
