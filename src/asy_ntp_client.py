# SPDX-FileCopyrightText: Copyright (c) 2013, 2014 micropython-lib contributors
# SPDX-License-Identifier: MIT
# Overlaps ntptime.py in the query byte, timestamp read and epoch delta - THIRD_PARTY_LICENSES.md.

"""Async NTP client + CET/CEST local-time helper. Not a sensor, but config-managed the same way:
extends asy_base_classes.py's SensorReaderConfig, owns its own config_NTP.cfg (see SPECIFICATION.md Part C).
"""
# Every field is persist-only, so asy_base_classes.py's generic _set_dict_cfg() gives full setter
# support with no _push_callbacks entries here at all.

import asyncio
import struct
import time
from collections import namedtuple

from machine import RTC, Timer
from micropython import const

from asy_base_classes import SensorReaderConfig, TickSeconds, arm_tick_timer, set_utc_valid, utc_now
from asy_config_manager import make_dict
from asy_dns_client import resolve_ipv4
from asy_print_log import DEFAULT_LOG, LogConfig
from asy_udp_socket import UDPSocket

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, NamedTuple

    from asy_base_classes import TimerStarter
    from asy_print_log import ErrorLog

# Codes from the global catalog (buildgen/error_catalog.json): the shared ones and NTP's band.
_ERR_CALLBACK = const(14)
_ERR_CLOCK = const(16)
_ERR_TIMER = const(17)
_ERR_BAD_ARG = const(21)
_ERR_CFG_READ = const(26)
_ERR_NTP_DNS = const(67)
_ERR_NTP_IMPLAUSIBLE = const(68)
_ERR_NTP_MALFORMED = const(69)
_ERR_NTP_RETRIES = const(70)
_ERR_NTP_NO_REPLY = const(71)
_WRN_NTP_UNSYNC_REPLY = const(40)

# @tunable ntp.async_intervals = 3
_NTP_ASYNC_INTERV = const(3)  # 3 times interval considered as out of sync
# @tunable ntp.check_interval_s = 10
_NTP_CHECK_INTERV = const(10)  # seconds to count for NTP status update
# @tunable ntp.sync_retries = 3
_NTP_SYNC_RETRIES = const(3)  # try 3 times to connect to NTP server before stopping
# @tunable ntp.retry_interval_s = 15
_NTP_RETRY_INTERV = const(15)  # wait 15 secs before retrying to sync
# @tunable ntp.backoff_mult = 2
_NTP_BACKOFF_MULT = const(2)  # unsynced retry interval doubles per failed attempt, up to its cap
# unsynced retry: first interval and its cap; both round up to the 10 s check tick (Part C.7.2)
# @tunable ntp.retry_s_default = 10
_DEFAULT_RETRY_S = const(10)
# @tunable ntp.retry_max_s_default = 600
_DEFAULT_RETRY_MAX_S = const(600)

# The client's timing, passed whole by the generated module: the resolver's DNS bounds, the fetch
# timeout and the unsynced backoff (first interval, cap).
if TYPE_CHECKING:
    class NtpTiming(NamedTuple):
        dns_timeout_ms: int
        dns_tries: int
        fetch_timeout_ms: int
        retry_s: int
        retry_max_s: int

else:
    NtpTiming = namedtuple("NtpTiming", ("dns_timeout_ms", "dns_tries", "fetch_timeout_ms", "retry_s", "retry_max_s"))

_NTP_UDP_PORT = 123  # RFC 5905's standard port; not const()-wrapped so tests can redirect it to a
# fake server's ephemeral port (binding real port 123 needs root).

_NTP_EPOCH_DELTA = const(2208988800)  # 1900 -> 1970, RFC 5905's NTP-to-Unix epoch conversion
_NTP_ERA_SECONDS = const(4294967296)  # 2**32 - one full NTP era (32-bit seconds field wraps ~2036)
# Plausibility window for a parsed reply - floor+ceiling together reject implausible/corrupt data
# even after era-reinterpretation (a floor alone can't). Bump both forward occasionally to stay
# "recent enough"/"far enough out".
# @tunable ntp.plausible_min_unix = 1735689600
_NTP_MIN_PLAUSIBLE_UNIX_TIME = const(1735689600)  # 2025-01-01T00:00:00Z - predates this file itself
# @tunable ntp.plausible_max_unix = 4102444800
_NTP_MAX_PLAUSIBLE_UNIX_TIME = const(4102444800)  # 2100-01-01T00:00:00Z - past the ~2036 era wrap

_NTP_LI_UNSYNCHRONIZED = const(3)  # RFC 5905 Leap Indicator top-2-bits: 3 = server's own clock is
# unsynchronized - its Transmit Timestamp can still look plausible, so needs its own check.
_NTP_STRATUM_INVALID = const(0)  # RFC 5905/4330 stratum 0 = Kiss-o'-Death packet. Its Transmit
# Timestamp is typically all-zero, which lands inside the plausibility window above.

_TIME_OFFSET_COUNT = const(2)  # cettime() reads exactly GMTOffset + DSTOffset
_GMTIME_FIELDS = const(8)  # time.gmtime()'s tuple width, matching GMTimeStruct's own field count

# Schema tuples for ConfigManager.get_*_values(). NTPHost is bounded by RFC 1035 (253 characters); the other
# bounds mirror the pre-refactor handler; defaults are the only source of truth for a fresh config_NTP.cfg.
_VAL_NTP_HOST = const((("NTPHost", "str", "pool.ntp.org", 3, 253, None),))
_VAL_NTP_OFFSET = const((("NTPOffset", "int", 0, -43200, 43200, None),))
_VAL_NTP_INTERVAL = const((("NTPInterval", "int", 12, 1, 24, None),))
_VAL_GMT_OFFSET = const((("GMTOffset", "int", 3600, -43200, 43200, None),))
_VAL_DST_OFFSET = const((("DSTOffset", "int", 3600, -43200, 43200, None),))

# @web-group section=networking submitGroup=ntp label="NTP Time Sync" submit=true submitLabel="Apply & Resync"
# @web NTPHost section=networking submitGroup=ntp label="NTP Server Address"
# @web NTPOffset section=networking submitGroup=ntp label="NTP Offset" unit="s" description="Added to Unix time; affects system time and all timestamps."
# @web NTPInterval section=networking submitGroup=ntp label="NTP Sync Interval" unit="h"

# Contributed into asy_system_service.py's "settings" group: GMTOffset/DSTOffset are real cettime()
# inputs owned by this module even though they render on the System page. That group is declared
# once, by asy_system_service.py's own @web-group tag; this file only adds fields to it.
# @web GMTOffset section=system submitGroup=settings label="GMT Offset" unit="s" description="Timezone offset to GMT; affects local time only."
# @web DSTOffset section=system submitGroup=settings label="DST Offset" unit="s" description="Daylight Savings offset; affects local time only."

# This service's one optional live cross-instance dependency (Part C.14): its FRAM error-log target,
# resolved from [device.wiring].fram_target implicitly because NTPClient is mandatory infra,
# never an [[instance]] entry - the same tag asy_system_service and asy_wifi_service carry.
# @wiring fram_target FRAMManager log optional kwarg

_NAME = const("NTP")
# Kept as a literal tuple inline (not `_FIELDS` below) because mypy's namedtuple plugin can only
# infer field names from a literal at the call site, not through a variable indirection.
NTP = namedtuple("NTP", ("Synced", "LastSyncAge", "TS"))
_FIELDS = const(("Synced", "LastSyncAge", "TS"))  # kept in sync with NTP's own fields above
GMTimeStruct = namedtuple("GMTimeStruct", ("year", "month", "mday", "hour", "minute", "second", "weekday", "yearday"))


class NTPClient(SensorReaderConfig):
    def __init__(
        self,
        wifi_mode_lock: asyncio.Lock,
        network_available_locked: "Callable[[], bool]",
        get_dns_server: "Callable[[], str | None]",
        timing: NtpTiming,
        cfg_path: str = "",
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        super().__init__(
            NTP(Synced=False, LastSyncAge=None, TS=None),
            _NAME,
            _VAL_NTP_HOST + _VAL_NTP_OFFSET + _VAL_NTP_INTERVAL + _VAL_GMT_OFFSET + _VAL_DST_OFFSET,
            max_module_error=0,  # no failure streak: an unreachable server is routine here, never a restart (owner, 2026-09-24; Part C.7.2)
            cfg_path=cfg_path,
            log=log,
        )
        self.wifi_mode_lock = wifi_mode_lock  # shared with WifiService - protects the WLAN state this class only reads
        self._network_available_locked = network_available_locked  # WifiService.network_available_locked - caller must hold wifi_mode_lock
        self._get_dns_server = get_dns_server  # WifiService.get_dns_server_ip - the network's own DHCP-assigned DNS server, or None
        self._dns_timeout_ms = timing.dns_timeout_ms
        self._dns_tries = timing.dns_tries
        self._ntp_fetch_timeout_ms = timing.fetch_timeout_ms
        self._retry_s = max(timing.retry_s, _NTP_CHECK_INTERV)
        self._retry_max_s = max(timing.retry_max_s, self._retry_s)
        self._retry_wait_s = self._retry_s  # current backoff step; reset by a sync or a forced resync
        self._unsynced_wait_s = 0  # seconds since the last unsynced attempt was triggered
        self._ntp_sec_count = 0
        self._ntp_retries = 0
        self._sync_age = TickSeconds()
        self._ntp_sync_trigger_event = asyncio.ThreadSafeFlag()
        self._ntp_timer_trigger_event = asyncio.ThreadSafeFlag()
        self._time_counter_trigger_event = asyncio.ThreadSafeFlag()
        self._ntp_timer = Timer()
        self._ntp_retry_timer = Timer()
        self._counter_timer = Timer()

    async def _get_ntp_config(self) -> tuple[list[str], list[int]] | None:
        ntp_host = await self.cfgmgr.get_str_values(_VAL_NTP_HOST)
        ntp_offs = await self.cfgmgr.get_int_values(_VAL_NTP_OFFSET)
        if ntp_host is None or ntp_offs is None or len(ntp_host) != 1 or len(ntp_offs) != 1:
            return None
        return ntp_host, ntp_offs

    async def _set_last_sync_age(self, *, value: int | None) -> None:
        data = await self.get_data()
        await self._set_meas_data(NTP(Synced=data.Synced, LastSyncAge=value, TS=data.TS))

    async def _set_synced(self, *, value: bool) -> None:
        # Uncontended asyncio.Lock.acquire() never yields (extmod/asyncio/lock.py), so nothing can
        # run between this get and the following set. Uses get_data() so the NTP fields are typed,
        # not the base class's generic NamedTuple.
        data = await self.get_data()
        await self._set_meas_data(NTP(Synced=value, LastSyncAge=data.LastSyncAge, TS=data.TS))

    async def _fetch_ntp_reply(self, addr: tuple[str, int]) -> bytes | None:
        try:
            cli = UDPSocket(addr, mode="client")
        except (TypeError, ValueError) as e:  # malformed addr - see UDPSocket's own contract
            await self.pr.err_s("Invalid NTP server address:", e, errno=_ERR_BAD_ARG)
            return None
        # write_and_recvfrom()/disconnect() never raise - they return their None-shaped sentinel on
        # any failure instead (see asy_udp_socket.py's contract), so no try/except is needed here.
        msg, _addr_from = await cli.write_and_recvfrom(
            b"\x1b" + bytearray(47),
            1024,
            timeout_ms=self._ntp_fetch_timeout_ms,
        )
        await cli.disconnect()
        if msg is None:
            await self.pr.err_s("No reply from NTP server:", addr[0], errno=_ERR_NTP_NO_REPLY)
        return msg

    async def _handle_ntp_sync_failure(self) -> None:
        self.pr.all("Invalid NTP time received!")
        self._ntp_retry_timer.deinit()
        if await self.ntp_issynced():  # in case of already synced, retry if regular trigger fails
            if (
                self._ntp_retries < _NTP_SYNC_RETRIES
            ):  # if not synced at all, self._refresh_loop() will permanently try to sync
                self.pr.evt("Waiting for NTP sync retry.")
                try:
                    self._ntp_retry_timer.init(
                        period=_NTP_RETRY_INTERV * 1000,
                        mode=Timer.ONE_SHOT,
                        callback=lambda _b: self._ntp_sync_trigger_event.set(),
                    )
                    self._ntp_retries += 1
                except (MemoryError, OSError) as e:  # alarm-pool exhaustion (ENOMEM) - give up this retry cycle rather
                    # than crashing the task; _refresh_loop()'s regular check still recovers it.
                    await self.pr.err_s("Could not arm NTP retry timer:", e, errno=_ERR_TIMER)
                    self._ntp_retries = 0
            else:
                await self.pr.err_s("Maximum retries reached, cancelling sync!", errno=_ERR_NTP_RETRIES)
                self._ntp_retries = 0

    async def _handle_ntp_sync_success(self, tm: tuple[int, ...]) -> None:
        set_utc_valid()  # the RTC was just set (_parse_ntp_reply()): every later utc_now() is a real time
        self._ntp_retry_timer.deinit()
        self._ntp_retries = 0
        self._reset_backoff()
        self._sync_age.restart(0)
        await self._set_meas_data(NTP(Synced=True, LastSyncAge=0, TS=utc_now()))
        self.pr.one("RTC set to:", tm)

    async def _parse_ntp_reply(self, msg: bytes, ntp_offset_s: int) -> tuple[int, ...] | None:
        try:
            leap_indicator = (msg[0] >> 6) & 0x3
            stratum = msg[1]
            if leap_indicator == _NTP_LI_UNSYNCHRONIZED or stratum == _NTP_STRATUM_INVALID:
                # Server says its own clock is unsynchronized, or this is a Kiss-o'-Death packet -
                # never a genuine time source, regardless of its Transmit Timestamp.
                await self.pr.wrn_s("NTP reply unsynchronized or Kiss-of-Death, rejecting:", leap_indicator, stratum, wrnno=_WRN_NTP_UNSYNC_REPLY)
                return None
            raw_s = struct.unpack("!I", msg[40:44])[0]
            ntp_time = raw_s - _NTP_EPOCH_DELTA + ntp_offset_s  # assume the current NTP era first
            if ntp_time < _NTP_MIN_PLAUSIBLE_UNIX_TIME:
                # Either a still-wrapped reply from the next NTP era (RFC 5905 7.3) - reinterpret
                # and recheck - or implausible data, rejected below if still out of range.
                ntp_time += _NTP_ERA_SECONDS
            if not (_NTP_MIN_PLAUSIBLE_UNIX_TIME <= ntp_time <= _NTP_MAX_PLAUSIBLE_UNIX_TIME):
                await self.pr.err_s("Implausible NTP time, rejecting:", ntp_time, errno=_ERR_NTP_IMPLAUSIBLE)
                return None
            self.pr.all("Received NTP time:", ntp_time)
            tm = time.gmtime(ntp_time)
            RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
        except (IndexError, OSError, OverflowError, ValueError) as e:
            # malformed/truncated reply (MicroPython's struct raises plain ValueError, not
            # struct.error) or an out-of-range timestamp - treat like no response.
            await self.pr.err_s("Malformed NTP response, treating as no response:", e, errno=_ERR_NTP_MALFORMED)
            return None
        else:
            return tm

    async def _refresh_loop(self) -> None:  # NTP refresh timer
        self._ntp_sec_count = 0
        while True:
            await self._ntp_timer_trigger_event.wait()
            ntp_interv = await self.cfgmgr.get_int_values(_VAL_NTP_INTERVAL)
            if ntp_interv is None or len(ntp_interv) != 1:
                ntp_interv = [12]
                await self.pr.err_s("Missing NTP configuration, defaulting interval to 12h!", errno=_ERR_CFG_READ)

            if await self.ntp_issynced():
                if self._ntp_sec_count < (_NTP_ASYNC_INTERV * ntp_interv[0] * 60 * 60):
                    self._ntp_sec_count += _NTP_CHECK_INTERV
                else:
                    await self._set_synced(value=False)

            self.pr.all("Sync-age tick counter at", self._ntp_sec_count)
            if await self.ntp_issynced():
                due = self._ntp_sec_count >= (ntp_interv[0] * 60 * 60)
            else:
                self._unsynced_wait_s += _NTP_CHECK_INTERV
                due = self._unsynced_wait_s >= self._retry_wait_s
            if due:
                self._ntp_retry_timer.deinit()
                self._ntp_retries = 0
                self._ntp_sync_trigger_event.set()
                self._ntp_sec_count = 0
                self._unsynced_wait_s = 0
                self.pr.evt("NTP resync triggered.")
            del ntp_interv

    def _reset_backoff(self) -> None:
        self._retry_wait_s = self._retry_s
        self._unsynced_wait_s = 0

    async def _resolve_ntp_server(self, ntp_host: str, dns_server: str | None) -> tuple[str, int] | None:
        servers = () if dns_server is None else (dns_server,)
        ip = await resolve_ipv4(ntp_host, servers, timeout_ms=self._dns_timeout_ms, tries=self._dns_tries)
        if ip is None:
            await self.pr.err_s("No valid NTP server:", ntp_host, errno=_ERR_NTP_DNS)
            return None
        return ip, _NTP_UDP_PORT

    async def _run_ntp_sync_attempt(self, dns_server: str | None) -> tuple[tuple[int, ...] | None, bool]:
        try:
            network_ok = self._network_available_locked()
        except Exception as e:  # caller-supplied callback - could legitimately misbehave
            await self.pr.err_s("network_available_locked() callback failed:", e, errno=_ERR_CALLBACK)
            network_ok = False
        if not network_ok:
            self.pr.all("Network not available, skipping sync attempt.")
            return None, False
        ntp_config = await self._get_ntp_config()
        if ntp_config is None:
            await self._set_synced(value=False)
            await self.pr.err_s("Missing NTP configuration!", errno=_ERR_CFG_READ)
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

    async def _safe_get_dns_server(self) -> str | None:
        # Must run before taking wifi_mode_lock, never inside it: get_dns_server() gates on wifi_mode_lock.locked()
        # itself, which this client holds during the sync attempt, so from inside it always returned None.
        try:
            return self._get_dns_server()
        except Exception as e:  # caller-supplied callback - could legitimately misbehave
            await self.pr.err_s("get_dns_server() callback failed:", e, errno=_ERR_CALLBACK)
            return None

    async def _sync_age_loop(self) -> None:
        await self._set_last_sync_age(value=None)
        while True:
            await self._time_counter_trigger_event.wait()
            if await self.ntp_issynced():
                await self._set_last_sync_age(value=self._sync_age.read())
            else:
                await self._set_last_sync_age(value=None)

    async def _sync_loop(self) -> None:
        await self._set_meas_data(NTP(Synced=False, LastSyncAge=None, TS=utc_now()))
        while True:
            await self._ntp_sync_trigger_event.wait()
            self.pr.evt("NTP sync starting.")
            dns_server = await self._safe_get_dns_server()  # read before taking wifi_mode_lock - see _safe_get_dns_server()
            async with self.wifi_mode_lock:
                tm, network_ok = await self._run_ntp_sync_attempt(dns_server)
            # Never gives up (Part C.7.2): a failed unsynced attempt only lengthens the retry interval
            # (a synced one has _handle_ntp_sync_failure()'s retries). A skipped one leaves it alone.
            if tm is None and network_ok and not await self.ntp_issynced():
                self._retry_wait_s = min(self._retry_wait_s * _NTP_BACKOFF_MULT, self._retry_max_s)

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_sync, self.start_asy_refresh, self.start_asy_sync_age]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return [self.start_check_timer, self.start_sync_age_timer]

    def start_asy_refresh(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._refresh_loop())

    def start_asy_sync(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._sync_loop())

    def start_asy_sync_age(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._sync_age_loop())

    def start_check_timer(self) -> None:
        try:
            self._ntp_timer.init(
                period=_NTP_CHECK_INTERV * 1000,
                mode=Timer.PERIODIC,
                callback=lambda _b: self._ntp_timer_trigger_event.set(),
            )
        except (MemoryError, OSError) as e:  # alarm-pool exhaustion (ENOMEM, see CLAUDE.md) - degrades gracefully;
            # NTP refresh scheduling just never starts rather than crashing the caller.
            self.pr.err("Could not start NTP timer:", e)

    def start_sync_age_timer(self) -> None:
        arm_tick_timer(self._counter_timer, self._time_counter_trigger_event, self.pr, "NTP sync age")

    def stop_check_timer(self) -> None:
        self._ntp_timer.deinit()

    def stop_sync_age_timer(self) -> None:
        self._counter_timer.deinit()

    async def get_data(self) -> NTP:
        # Narrows to this Reader's concrete NTP - see SPECIFICATION.md C.4.2's get_data() convention.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(self.name, _VAL_NTP_HOST + _VAL_NTP_OFFSET + _VAL_NTP_INTERVAL + _VAL_GMT_OFFSET + _VAL_DST_OFFSET)

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data, _FIELDS, name=self.name)

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    async def get_last_ntp_sync(self) -> int | None:  # None = never synced yet
        age = (await self.get_data()).LastSyncAge
        return None if age is None else int(age)

    async def cettime(
        self,
    ) -> GMTimeStruct | None:  # local-time conversion
        if not (await self.ntp_issynced()):
            return None
        time_offs = await self.cfgmgr.get_int_values(_VAL_GMT_OFFSET + _VAL_DST_OFFSET)
        if time_offs is None or len(time_offs) != _TIME_OFFSET_COUNT:
            return None
        try:
            year = time.gmtime()[0]  # get current year
            HHMarch = time.mktime(
                (year, 3, (31 - (int(5 * year / 4 + 4)) % 7), 1, 0, 0, 0, 0, 0),
            )  # Time of March change to CEST
            HHOctober = time.mktime(
                (year, 10, (31 - (int(5 * year / 4 + 1)) % 7), 1, 0, 0, 0, 0, 0),
            )  # Time of October change to CET
            now = time.time()
            if now < HHMarch:  # we are before last sunday of march
                cet = time.gmtime(now + time_offs[0])  # GMTOffset -> CET:  UTC+1H
            elif now < HHOctober:  # we are before last sunday of october
                cet = time.gmtime(now + time_offs[0] + time_offs[1])  # GMTOffset + DSTOffset-> CEST: UTC+2H
            else:  # we are after last sunday of october
                cet = time.gmtime(now + time_offs[0])  # GMTOffset -> CET:  UTC+1H
        except (OSError, OverflowError, ValueError) as e:
            # rp2's mktime()/gmtime() raise OverflowError past its ~2037 32-bit epoch range - treat
            # exactly like "not ready" instead of crashing the caller.
            await self.pr.err_s("Time calculation failed:", e, errno=_ERR_CLOCK)
            return None
        if len(cet) == _GMTIME_FIELDS:
            return GMTimeStruct(*cet)
        return None

    async def ntp_force_sync(self) -> None:
        await self._set_last_sync_age(value=None)
        self._ntp_retry_timer.deinit()
        self._ntp_retries = 0
        self._reset_backoff()  # an operator's resync must not wait out a long backoff step
        self._ntp_sync_trigger_event.set()
        self.pr.evt("Force resync triggered.")

    async def ntp_issynced(self) -> bool:
        return bool((await self.get_data()).Synced)
