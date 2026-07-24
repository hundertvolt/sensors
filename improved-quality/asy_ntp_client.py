import json
import time
import socket
import struct
import asyncio
from uasyncio import Lock, ThreadSafeFlag
from asy_udp_socket import AsyUDPSocket
from machine import Timer, RTC
from micropython import const
from config_manager import ConfigManager
from base_classes import LockedCounter, LockedFlag
from typing import Callable, Dict
from collections import namedtuple

_NTP_ASYNC_INTERV = const(3)  # 3 times interval considered as out of sync
_NTP_CHECK_INTERV = const(10)  # seconds to count for NTP status update
_NTP_CONN_TIMEOUT = const(5000)  # 5s  to send request / receive an answer from NTP server
_NTP_SYNC_RETRIES = const(3)  # try 3 times to connect to NTP server before stopping
_NTP_RETRY_INTERV = const(15)  # wait 15 secs before retrying to sync

_DEFAULT_CONFIG = const(
    '{"NTP_Host": "pool.ntp.org", "NTP_Offset_S": 0, "NTP_Interv_H": 12, "GMTOffset": 3600, "DSTOffset": 3600}'
)

# Schema tuples for config_manager.ConfigManager.get_*_values() - min/max mirror the REST-API
# bounds sensortask-wozi.py's update_valid_json() already enforces for these same fields, so both
# validation paths agree; defaults mirror _DEFAULT_CONFIG above.
_VAL_NH = const((("NTP_Host", "str", "pool.ntp.org", 3, 1024, None),))
_VAL_NOS = const((("NTP_Offset_S", "int", 0, -43200, 43200, None),))
_VAL_NIH = const((("NTP_Interv_H", "int", 12, 1, 24, None),))
_VAL_GMT = const((("GMTOffset", "int", 3600, -43200, 43200, None),))
_VAL_DST = const((("DSTOffset", "int", 3600, -43200, 43200, None),))

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
            res = json.loads(_DEFAULT_CONFIG)
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
                await self._run_ntp_sync_attempt()
            finally:
                try:
                    self.wifi_mode_lock.release()
                except RuntimeError:  # in case it's already released somehow
                    pass

    async def _run_ntp_sync_attempt(self) -> None:
        if not self.network_available():
            return
        ntp_config = await self._get_ntp_config()
        if ntp_config is None:
            await self.ntp_synced.set_false()
            if self.debug:
                print("Fehlende NTP Konfiguration!")
            return
        ntp_host, ntp_offs = ntp_config
        addr = await self._resolve_ntp_server(ntp_host[0])
        if addr is None:
            await self._handle_ntp_sync_failure()
            return
        msg = await self._fetch_ntp_reply(addr)
        if msg is None:
            await self._handle_ntp_sync_failure()
            return
        tm = self._parse_ntp_reply(msg, ntp_offs[0])
        if tm is None:
            await self._handle_ntp_sync_failure()
        else:
            await self._handle_ntp_sync_success(tm)

    async def _get_ntp_config(self) -> tuple[list[str], list[int]] | None:
        ntp_host = await self.cfgmgr.get_str_values(_VAL_NH)
        ntp_offs = await self.cfgmgr.get_int_values(_VAL_NOS)
        if ntp_host is None or ntp_offs is None or len(ntp_host) != 1 or len(ntp_offs) != 1:
            return None
        return ntp_host, ntp_offs

    async def _resolve_ntp_server(self, ntp_host: str) -> tuple[str, int] | None:
        await self.asy_long_block_lock.acquire()  # getaddrinfo may block for some time - see BACKLOG.md
        if self.debug:
            print("NTP Long Block Lock acquired.")
        try:
            return socket.getaddrinfo(ntp_host, 123)[0][-1]
        except Exception as e:
            if self.debug:
                print("No valid NTP server:", e)
            return None
        finally:
            await asyncio.sleep(0)
            try:
                self.asy_long_block_lock.release()
            except RuntimeError:  # in case it's already released somehow
                pass
            if self.debug:
                print("NTP Long Block Lock released.")

    async def _fetch_ntp_reply(self, addr: tuple[str, int]) -> bytes | None:
        try:
            cli = AsyUDPSocket(addr, mode="client")
        except (ValueError, TypeError) as e:  # malformed addr - see AsyUDPSocket's own contract
            if self.debug:
                print("Invalid NTP server address:", e)
            return None
        # write_and_recvfrom()/disconnect() never raise - they return their documented
        # None-shaped sentinel on any OSError/MemoryError/timeout instead (see
        # src/asy_udp_socket.py's module contract), so no try/except is needed - or
        # correct - around this call.
        msg, _addr_from = await cli.write_and_recvfrom(
            b"\x1b" + bytearray(47),
            1024,
            timeout_ms=_NTP_CONN_TIMEOUT,
        )
        await cli.disconnect()
        return msg

    def _parse_ntp_reply(self, msg: bytes, ntp_offset_s: int) -> tuple[int, ...] | None:
        try:
            ntp_time = (struct.unpack("!I", msg[40:44])[0]) - 2208988800 + ntp_offset_s  # offset since 1970
            if self.debug:
                print("Received NTP time:", ntp_time)
            tm = time.gmtime(ntp_time)
            RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
            return tm
        except (struct.error, OverflowError, ValueError, OSError) as e:
            # malformed/truncated reply, or an out-of-range timestamp (rp2's ~2037
            # 32-bit epoch limit - see BACKLOG.md) - treat exactly like no response at
            # all rather than letting it crash the whole task.
            if self.debug:
                print("Malformed NTP response, treating as no response:", e)
            return None

    async def _handle_ntp_sync_failure(self) -> None:
        if self.debug:
            print("Invalid NTP Time received!")
        self.ntp_retry_timer.deinit()
        if await self.ntp_synced.get_value():  # in case of already synced, retry if regular trigger fails
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

    async def _handle_ntp_sync_success(self, tm: tuple[int, ...]) -> None:
        self.ntp_retry_timer.deinit()
        self.ntp_retries = 0
        await self.last_ntp_sync.set_value(0)
        await self.ntp_synced.set_true()
        if self.debug:
            print("RTC set to:", tm)

    async def ntp_time_hours_counter(self) -> None:  # Timer für NTP Refresh
        self.ntp_sec_count = 0
        while True:
            await self.ntp_timer_trigger_event.wait()
            ntp_interv = await self.cfgmgr.get_int_values(_VAL_NIH)
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
        time_offs = await self.cfgmgr.get_int_values(_VAL_GMT + _VAL_DST)
        if time_offs is None or len(time_offs) != 2:
            return None
        year = time.gmtime()[0]  # get current year
        HHMarch = time.mktime(
            (year, 3, (31 - (int(5 * year / 4 + 4)) % 7), 1, 0, 0, 0, 0, 0)
        )  # Time of March change to CEST
        HHOctober = time.mktime(
            (year, 10, (31 - (int(5 * year / 4 + 1)) % 7), 1, 0, 0, 0, 0, 0)
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
