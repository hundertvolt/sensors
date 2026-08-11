"""Async NTP client + CET/CEST local-time helper. Not a sensor, but config-managed the same way:
extends base_classes.py's SensorReaderConfig, owns its own config_NTP.cfg (see SPECIFICATION.md Part C).
Every field is persist-only - nothing here needs a live push, so base_classes.py's generic
_set_dict_cfg() already provides full setter support with zero changes to this file (no
self._push_callbacks entries registered). errno/wrnno numbering starts at 11 here (1-4/10 are
base_classes.py's own).
"""

import asyncio
import struct
import time
from collections import namedtuple

from machine import RTC, Timer
from micropython import const

from asy_dns_client import resolve_ipv4
from asy_udp_socket import AsyUDPSocket
from base_classes import SensorReaderConfig
from config_manager import make_dict

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from asy_fram_manager import AsyFramManager

_NTP_ASYNC_INTERV = const(3)  # 3 times interval considered as out of sync
_NTP_CHECK_INTERV = const(10)  # seconds to count for NTP status update
_NTP_CONN_TIMEOUT = const(5000)  # 5s  to send request / receive an answer from NTP server
_NTP_SYNC_RETRIES = const(3)  # try 3 times to connect to NTP server before stopping
_NTP_RETRY_INTERV = const(15)  # wait 15 secs before retrying to sync

_NTP_UDP_PORT = 123  # RFC 5905's standard port; not const()-wrapped so tests can redirect it to a
# fake server's ephemeral port (binding real port 123 needs root).

_NTP_EPOCH_DELTA = const(2208988800)  # 1900 -> 1970, RFC 5905's NTP-to-Unix epoch conversion
_NTP_ERA_SECONDS = const(4294967296)  # 2**32 - one full NTP era (32-bit seconds field wraps ~2036)
# Plausibility window for a parsed reply - floor+ceiling together reject implausible/corrupt data
# even after era-reinterpretation (a floor alone can't). Bump both forward occasionally to stay
# "recent enough"/"far enough out".
_NTP_MIN_PLAUSIBLE_UNIX_TIME = const(1735689600)  # 2025-01-01T00:00:00Z - predates this file itself
_NTP_MAX_PLAUSIBLE_UNIX_TIME = const(4102444800)  # 2100-01-01T00:00:00Z - past the ~2036 era wrap

_NTP_LI_UNSYNCHRONIZED = const(3)  # RFC 5905 Leap Indicator top-2-bits: 3 = server's own clock is
# unsynchronized - its Transmit Timestamp can still look plausible, so needs its own check.
_NTP_STRATUM_INVALID = const(0)  # RFC 5905/4330 stratum 0 = Kiss-o'-Death packet. Its Transmit
# Timestamp is typically all-zero, which lands inside the plausibility window above.

# Schema tuples for ConfigManager.get_*_values() - min/max mirror the already-validated bounds the
# deployed, pre-refactor REST handler uses; defaults are the only source of truth for a fresh config_NTP.cfg.
_VAL_NH = const((("NTP_Host", "str", "pool.ntp.org", 3, 1024, None),))
_VAL_NOS = const((("NTP_Offset_S", "int", 0, -43200, 43200, None),))
_VAL_NIH = const((("NTP_Interv_H", "int", 12, 1, 24, None),))
_VAL_GMT = const((("GMTOffset", "int", 3600, -43200, 43200, None),))
_VAL_DST = const((("DSTOffset", "int", 3600, -43200, 43200, None),))

_NAME = const("NTP")
NTP = namedtuple("NTP", ("Synced", "LastSyncAge", "TS"))
GMTimeStruct = namedtuple("GMTimeStruct", ("year", "month", "mday", "hour", "minute", "second", "weekday", "yearday"))


class AsyNtpClient(SensorReaderConfig):
    def __init__(
        self,
        wifi_mode_lock: asyncio.Lock,
        network_available: "Callable[[], bool]",
        get_dns_server: "Callable[[], str | None]",
        dns_timeout_ms: int = 500,  # forwarded to resolve_ipv4() - whichever module wires this up
        # decides the real deployment value at construction time.
        dns_tries: int = 1,  # forwarded to resolve_ipv4() - see dns_timeout_ms's own comment.
        ntp_fetch_timeout_ms: int = _NTP_CONN_TIMEOUT,  # forwarded to _fetch_ntp_reply()'s socket
        # call - same reasoning as dns_timeout_ms.
        max_i2c_err: int = 5,
        cfg_path: str = "",
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        super().__init__(
            NTP(False, None, None),
            max_i2c_err,  # consecutive failed-sync-attempt streak before asy_ntp_time() gives up and
            # lets the task supervisor restart this task - see that method's own _error_check() call.
            _NAME,
            _VAL_NH + _VAL_NOS + _VAL_NIH + _VAL_GMT + _VAL_DST,
            cfg_path=cfg_path,
            fram=fram,
            history_length=history_length,
            debug=debug,
        )
        self.wifi_mode_lock = wifi_mode_lock  # shared with AsyConnTime - protects the WLAN state this class only reads
        self.network_available = network_available  # AsyConnTime.network_available - caller must hold wifi_mode_lock
        self.get_dns_server = get_dns_server  # AsyConnTime.get_dns_server_ip - the network's own DHCP-assigned DNS server, or None
        self.dns_timeout_ms = dns_timeout_ms
        self.dns_tries = dns_tries
        self.ntp_fetch_timeout_ms = ntp_fetch_timeout_ms
        self.ntp_sec_count = 0
        self.ntp_retries = 0
        self.ntp_sync_trigger_event = asyncio.ThreadSafeFlag()
        self.ntp_timer_trigger_event = asyncio.ThreadSafeFlag()
        self.time_counter_trigger_event = asyncio.ThreadSafeFlag()
        self.ntp_timer = Timer()
        self.ntp_retry_timer = Timer()
        self.counter_timer = Timer()

    def _now(self) -> int | None:
        try:
            return time.mktime(time.gmtime())
        except (OverflowError, OSError):  # rp2's mktime()/gmtime() raise past its ~2037 32-bit epoch range
            return None

    async def _safe_get_dns_server(self) -> str | None:
        # Must be called before wifi_mode_lock.acquire(), never after: get_dns_server() gates on
        # wifi_mode_lock.locked() itself, which this file also holds during the sync attempt below -
        # calling it from inside that section always returned None.
        try:
            return self.get_dns_server()
        except Exception as e:  # caller-supplied callback - could legitimately misbehave
            await self.pr.wrn_s("get_dns_server() callback failed:", e, wrnno=3)
            return None

    async def _get_ntp_config(self) -> tuple[list[str], list[int]] | None:
        ntp_host = await self.cfgmgr.get_str_values(_VAL_NH)
        ntp_offs = await self.cfgmgr.get_int_values(_VAL_NOS)
        if ntp_host is None or ntp_offs is None or len(ntp_host) != 1 or len(ntp_offs) != 1:
            return None
        return ntp_host, ntp_offs

    async def _resolve_ntp_server(self, ntp_host: str, dns_server: str | None) -> tuple[str, int] | None:
        servers = () if dns_server is None else (dns_server,)
        ip = await resolve_ipv4(ntp_host, servers, timeout_ms=self.dns_timeout_ms, tries=self.dns_tries)
        if ip is None:
            await self.pr.err_s("No valid NTP server:", ntp_host, errno=12)
            return None
        return ip, _NTP_UDP_PORT

    async def _fetch_ntp_reply(self, addr: tuple[str, int]) -> bytes | None:
        try:
            cli = AsyUDPSocket(addr, mode="client")
        except (ValueError, TypeError) as e:  # malformed addr - see AsyUDPSocket's own contract
            await self.pr.err_s("Invalid NTP server address:", e, errno=13)
            return None
        # write_and_recvfrom()/disconnect() never raise - they return their None-shaped sentinel on
        # any failure instead (see asy_udp_socket.py's contract), so no try/except is needed here.
        msg, _addr_from = await cli.write_and_recvfrom(
            b"\x1b" + bytearray(47),
            1024,
            timeout_ms=self.ntp_fetch_timeout_ms,
        )
        await cli.disconnect()
        return msg

    async def _set_synced(self, value: bool) -> None:
        # Uncontended asyncio.Lock.acquire() never yields (extmod/asyncio/lock.py), so nothing can
        # run between this get and the following set. Uses get_data() so the NTP fields are typed,
        # not the base class's generic NamedTuple.
        data = await self.get_data()
        await self._set_meas_data(NTP(value, data.LastSyncAge, data.TS))

    async def _set_last_sync_age(self, value: int | None) -> None:
        data = await self.get_data()
        await self._set_meas_data(NTP(data.Synced, value, data.TS))

    async def _increment_last_sync_age(self) -> int | None:
        # None counts as 0 - the first increment after a fresh sync turns "just synced" into a
        # real age of 1, matching base_classes.py's LockedCounter.increment() this replaces.
        data = await self.get_data()
        current = 0 if data.LastSyncAge is None else data.LastSyncAge
        new_value = min(current + 1, 0xFFFFFFFF)
        await self._set_meas_data(NTP(data.Synced, new_value, data.TS))
        return new_value

    async def _run_ntp_sync_attempt(self, dns_server: str | None) -> "tuple[tuple[int, ...] | None, bool]":
        try:
            network_ok = self.network_available()
        except Exception as e:  # caller-supplied callback - could legitimately misbehave
            await self.pr.wrn_s("network_available() callback failed:", e, wrnno=1)
            network_ok = False
        if not network_ok:
            self.pr.all("Network not available, skipping sync attempt.")
            return None, False
        ntp_config = await self._get_ntp_config()
        if ntp_config is None:
            await self._set_synced(False)
            await self.pr.err_s("Missing NTP configuration!", errno=11)
            return None, True
        ntp_host, ntp_offs = ntp_config
        addr = await self._resolve_ntp_server(ntp_host[0], dns_server)
        if addr is None:
            await self._handle_ntp_sync_failure()
            return None, True
        msg = await self._fetch_ntp_reply(addr)
        if msg is None:
            await self._handle_ntp_sync_failure()
            return None, True
        tm = await self._parse_ntp_reply(msg, ntp_offs[0])
        if tm is None:
            await self._handle_ntp_sync_failure()
        else:
            await self._handle_ntp_sync_success(tm)
        return tm, True

    async def _parse_ntp_reply(self, msg: bytes, ntp_offset_s: int) -> tuple[int, ...] | None:
        try:
            leap_indicator = (msg[0] >> 6) & 0x3
            stratum = msg[1]
            if leap_indicator == _NTP_LI_UNSYNCHRONIZED or stratum == _NTP_STRATUM_INVALID:
                # Server says its own clock is unsynchronized, or this is a Kiss-o'-Death packet -
                # never a genuine time source, regardless of its Transmit Timestamp.
                await self.pr.wrn_s(
                    "NTP reply unsynchronized or Kiss-of-Death, rejecting:", leap_indicator, stratum, wrnno=2
                )
                return None
            raw_seconds = struct.unpack("!I", msg[40:44])[0]
            ntp_time = raw_seconds - _NTP_EPOCH_DELTA + ntp_offset_s  # assume the current NTP era first
            if ntp_time < _NTP_MIN_PLAUSIBLE_UNIX_TIME:
                # Either a still-wrapped reply from the next NTP era (RFC 5905 7.3) - reinterpret
                # and recheck - or implausible data, rejected below if still out of range.
                ntp_time += _NTP_ERA_SECONDS
            if not (_NTP_MIN_PLAUSIBLE_UNIX_TIME <= ntp_time <= _NTP_MAX_PLAUSIBLE_UNIX_TIME):
                await self.pr.err_s("Implausible NTP time, rejecting:", ntp_time, errno=14)
                return None
            self.pr.all("Received NTP time:", ntp_time)
            tm = time.gmtime(ntp_time)
            RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
            return tm
        except (IndexError, OverflowError, ValueError, OSError) as e:
            # malformed/truncated reply (MicroPython's struct raises plain ValueError, not
            # struct.error) or an out-of-range timestamp - treat like no response.
            await self.pr.err_s("Malformed NTP response, treating as no response:", e, errno=15)
            return None

    async def _handle_ntp_sync_failure(self) -> None:
        self.pr.all("Invalid NTP time received!")
        self.ntp_retry_timer.deinit()
        if await self.ntp_issynced():  # in case of already synced, retry if regular trigger fails
            if (
                self.ntp_retries < _NTP_SYNC_RETRIES
            ):  # if not synced at all, self.ntp_time_hours_counter() will permanently try to sync
                self.pr.evt("Waiting for NTP sync retry.")
                try:
                    self.ntp_retry_timer.init(
                        period=_NTP_RETRY_INTERV * 1000,
                        mode=Timer.ONE_SHOT,
                        callback=lambda b: self.ntp_sync_trigger_event.set(),
                    )
                    self.ntp_retries += 1
                except (OSError, MemoryError) as e:  # alarm-pool exhaustion (ENOMEM) - give up this retry cycle rather
                    # than crashing the task; ntp_time_hours_counter()'s regular check still recovers it.
                    await self.pr.err_s("Could not arm NTP retry timer:", e, errno=16)
                    self.ntp_retries = 0
            else:
                await self.pr.err_s("Maximum retries reached, cancelling sync!", errno=17)
                self.ntp_retries = 0

    async def _handle_ntp_sync_success(self, tm: tuple[int, ...]) -> None:
        self.ntp_retry_timer.deinit()
        self.ntp_retries = 0
        await self._set_meas_data(NTP(True, 0, self._now()))
        self.pr.one("RTC set to:", tm)

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
        try:
            self.ntp_timer.init(
                period=_NTP_CHECK_INTERV * 1000,
                mode=Timer.PERIODIC,
                callback=lambda b: self.ntp_timer_trigger_event.set(),
            )
        except (OSError, MemoryError) as e:  # alarm-pool exhaustion (ENOMEM, see CLAUDE.md) - degrades gracefully;
            # NTP refresh scheduling just never starts rather than crashing the caller.
            self.pr.err("Could not start NTP timer:", e)

    def start_counter_timer(self) -> None:
        try:
            self.counter_timer.init(
                period=1000,
                mode=Timer.PERIODIC,
                callback=lambda b: self.time_counter_trigger_event.set(),
            )
        except (OSError, MemoryError) as e:  # alarm-pool exhaustion (ENOMEM) - same graceful degradation as start_ntp_timer()
            self.pr.err("Could not start counter timer:", e)

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_ntp_client, self.start_asy_ntp_refresh, self.start_asy_sync_age_counter]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return [self.start_ntp_timer, self.start_counter_timer]

    def stop_ntp_timer(self) -> None:
        self.ntp_timer.deinit()

    def stop_counter_timer(self) -> None:
        self.counter_timer.deinit()

    async def get_data(self) -> NTP:
        # Narrows to this Reader's concrete NTP - see SPECIFICATION.md C.4.2's get_data() convention.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data)

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(_NAME, _VAL_NH + _VAL_NOS + _VAL_NIH + _VAL_GMT + _VAL_DST)

    async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:
        return await self.pr.get_log()

    async def get_last_ntp_sync(self) -> int | None:  # None = never synced yet
        age = (await self.get_data()).LastSyncAge
        return None if age is None else int(age)

    async def ntp_issynced(self) -> bool:
        return bool((await self.get_data()).Synced)

    async def cettime(
        self,
    ) -> GMTimeStruct | None:  # local-time conversion
        if not (await self.ntp_issynced()):
            return None
        time_offs = await self.cfgmgr.get_int_values(_VAL_GMT + _VAL_DST)
        if time_offs is None or len(time_offs) != 2:
            return None
        try:
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
        except (OverflowError, ValueError, OSError) as e:
            # rp2's mktime()/gmtime() raise OverflowError past its ~2037 32-bit epoch range - treat
            # exactly like "not ready" instead of crashing the caller.
            await self.pr.err_s("Time calculation failed:", e, errno=19)
            return None
        if len(cet) == 8:
            return GMTimeStruct(*cet)
        return None

    async def ntp_force_sync(self) -> None:
        await self._set_last_sync_age(None)
        self.ntp_retry_timer.deinit()
        self.ntp_retries = 0
        self.ntp_sync_trigger_event.set()
        self.pr.evt("Force resync triggered.")

    async def asy_ntp_time(self) -> None:
        await self.pr.setup()  # required for all logged warnings and errors (base_classes.py's own
        # __init__ never calls this - matches every _init_<sensor>() in the three promoted drivers)
        self._err_cnt_internal = 0  # fresh failure streak each task (re)start, same as _init_<sensor>()
        await self._set_meas_data(NTP(False, None, self._now()))
        while True:
            await self.ntp_sync_trigger_event.wait()
            self.pr.evt("NTP sync starting.")
            dns_server = await self._safe_get_dns_server()  # must be read before acquiring
            # wifi_mode_lock below - see _safe_get_dns_server()'s own comment.
            await self.wifi_mode_lock.acquire()
            try:
                tm, network_ok = await self._run_ntp_sync_attempt(dns_server)
            finally:
                try:
                    self.wifi_mode_lock.release()
                except RuntimeError:  # in case it's already released somehow
                    pass
            # Consecutive-failure streak over real sync attempts, independent from and coarser than
            # _handle_ntp_sync_failure()'s own short-term retry loop. condition=network_ok excludes
            # "network wasn't up yet" from counting; narrows tm to just its presence/absence.
            if not await self._error_check((None if tm is None else tm[0],), condition=network_ok):
                await self.pr.err_s("Giving up after repeated sync failures, restarting task.", errno=20)
                return

    async def ntp_time_hours_counter(self) -> None:  # NTP refresh timer
        self.ntp_sec_count = 0
        while True:
            await self.ntp_timer_trigger_event.wait()
            ntp_interv = await self.cfgmgr.get_int_values(_VAL_NIH)
            if ntp_interv is None or len(ntp_interv) != 1:
                ntp_interv = [12]
                await self.pr.err_s("Missing NTP configuration, defaulting interval to 12h!", errno=18)

            if await self.ntp_issynced():
                if self.ntp_sec_count < (_NTP_ASYNC_INTERV * ntp_interv[0] * 60 * 60):
                    self.ntp_sec_count += _NTP_CHECK_INTERV
                else:
                    await self._set_synced(False)

            self.pr.all("Sync-age tick counter at", self.ntp_sec_count)
            if (not (await self.ntp_issynced())) or (self.ntp_sec_count >= (ntp_interv[0] * 60 * 60)):
                self.ntp_retry_timer.deinit()
                self.ntp_retries = 0
                self.ntp_sync_trigger_event.set()
                self.ntp_sec_count = 0
                self.pr.evt("NTP resync triggered.")
            del ntp_interv

    async def time_counter(self) -> None:
        await self._set_last_sync_age(None)
        while True:
            await self.time_counter_trigger_event.wait()
            if await self.ntp_issynced():
                await self._increment_last_sync_age()
            else:
                await self._set_last_sync_age(None)
