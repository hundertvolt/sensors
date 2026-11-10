# SPDX-FileCopyrightText: Copyright (c) 2013, 2014 micropython-lib contributors
# SPDX-License-Identifier: MIT
# Overlaps ntptime.py in the query byte, timestamp read and epoch delta - THIRD_PARTY_LICENSES.md.

"""Async NTP client + CET/CEST local-time helper. Not a sensor, but config-managed the same way:
extends asy_base_classes.py's SensorReaderConfig, owns its own config_NTP.cfg (see SPECIFICATION.md Part C).
"""
# Two fields check their shape before storing (_set_mgr_cfg(): NTPHost, DNSFallback); the rest persist through
# asy_base_classes.py's generic _set_dict_cfg(), with no _push_callbacks entries. Error numbers come from the one
# catalog (SPECIFICATION.md Part C.7.1).

import asyncio
import struct
import time
from collections import namedtuple

from machine import RTC
from micropython import const

from asy_base_classes import SensorReaderConfig, TickGrid, TickSeconds, set_utc_valid, utc_now
from asy_config_manager import INVALID, make_dict
from asy_dns_client import DNS_LABEL_MAX, host_label_ok, ipv4_to_int, resolve_ipv4
from asy_print_log import DEFAULT_LOG, LogConfig
from asy_udp_socket import UDPSocket

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import NamedTuple

    from asy_base_classes import JsonMapping, TaskStarter
    from asy_config_manager import ConfigSchema, WriteValidity

# Codes from the global catalog (buildgen/error_catalog.json): the shared ones and NTP's band.
_ERR_CALLBACK = const(14)
_ERR_BAD_ARG = const(21)
_ERR_CFG_READ = const(26)
_ERR_NTP_DNS = const(67)
_ERR_NTP_IMPLAUSIBLE = const(68)
_ERR_NTP_MALFORMED = const(69)
_ERR_NTP_RETRIES = const(70)
_ERR_NTP_NO_REPLY = const(71)
_ERR_NTP_NOT_SENT = const(72)
_WRN_NTP_UNSYNC_REPLY = const(40)

# @tunable ntp.async_intervals = 3
_NTP_ASYNC_INTERV = const(3)  # 3 times interval considered as out of sync
# @tunable ntp.check_interval_s = 10
_NTP_CHECK_INTERV = const(10)  # seconds to count for NTP status update
# @tunable ntp.sync_retries = 3
_NTP_SYNC_RETRIES = const(3)  # try 3 times to connect to NTP server before stopping
# @tunable ntp.retry_interval_s = 15
_NTP_RETRY_INTERV = const(15)  # wait 15 secs before retrying to sync
# @tunable ntp.retry_unsynced_s = 60
_NTP_RETRY_UNSYNCED_S = const(60)  # unsynced: the wait after a failed attempt; until one fails, every check tries (owner, 2026-11-03)

# The client's timing, passed whole by the generated module: the resolver's DNS bounds and the fetch timeout.
if TYPE_CHECKING:
    class NtpTiming(NamedTuple):
        dns_timeout_ms: int
        dns_tries: int
        fetch_timeout_ms: int

else:
    NtpTiming = namedtuple("NtpTiming", ("dns_timeout_ms", "dns_tries", "fetch_timeout_ms"))

_NTP_UDP_PORT = const(123)  # RFC 5905 SS7.2

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

_NTP_STR_COUNT = const(2)  # _get_ntp_config() reads exactly NTPHost + DNSFallback
_TIME_OFFSET_COUNT = const(2)  # cettime() reads exactly GMTOffset + DSTOffset
_GMTIME_FIELDS = const(8)  # time.gmtime()'s tuple width, matching GMTimeStruct's own field count

# Schema tuples for ConfigManager.get_*_values(). NTPHost is bounded by RFC 1035 (253 characters); the other
# bounds mirror the pre-refactor handler; defaults are the only source of truth for a fresh config_NTP.cfg.
_VAL_NTP_HOST = const((("NTPHost", "str", "pool.ntp.org", 3, 253, None),))
_VAL_NTP_OFFSET = const((("NTPOffset", "int", 0, -43200, 43200, None),))
_VAL_NTP_INTERVAL = const((("NTPInterval", "int", 12, 1, 24, None),))
_VAL_GMT_OFFSET = const((("GMTOffset", "int", 3600, -43200, 43200, None),))
_VAL_DST_OFFSET = const((("DSTOffset", "int", 3600, -43200, 43200, None),))
# DNS servers tried after the DHCP-provided one, in order; empty = none. Default: today's public pair
# (owner, 2026-09-26). At most three (agent, 2026-09-30; owner-reviewed, 2026-10-02), which bounds the NTP attempt's lock hold (SPECIFICATION.md C.8).
_VAL_DNS_FALLBACK = const((("DNSFallback", "str", "8.8.8.8,1.1.1.1", 0, 47, None),))
_DNS_FALLBACK_MAX = const(3)  # ipv4List items; the 47-character bound fits three dotted quads and two commas

# @web-group section=networking submitGroup=ntp label="NTP Time Sync" submit=true submitLabel="Apply & Resync"
# @web NTPHost section=networking submitGroup=ntp label="NTP Server Address" shape=hostName
# @web NTPOffset section=networking submitGroup=ntp label="NTP Offset" unit="s" description="Added to Unix time; affects system time and all timestamps."
# @web NTPInterval section=networking submitGroup=ntp label="NTP Sync Interval" unit="h"
# @web-group section=networking submitGroup=dns label="DNS Fallback Servers" submit=true
# @web DNSFallback section=networking submitGroup=dns label="Fallback DNS Servers" shape=ipv4List clearable=true description="Asked after the DHCP-provided server fails, in order. Empty = none; the Clear button empties it."

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


def _dns_fallback_ok(value: object) -> bool:
    # ipv4List shape: empty, or up to three comma-separated IPv4 literals.
    if type(value) is not str:
        return False
    if not value:
        return True
    items = value.split(",")
    return len(items) <= _DNS_FALLBACK_MAX and all(ipv4_to_int(item) is not None for item in items)


def _ntp_host_ok(value: object) -> bool:
    # hostName shape: an IPv4 literal, or dot-separated RFC 1123 labels of at most 63 characters.
    if type(value) is not str:
        return False
    return ipv4_to_int(value) is not None or all(len(label) <= DNS_LABEL_MAX and host_label_ok(label) for label in value.split("."))


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
            _VAL_NTP_HOST + _VAL_NTP_OFFSET + _VAL_NTP_INTERVAL + _VAL_GMT_OFFSET + _VAL_DST_OFFSET + _VAL_DNS_FALLBACK,
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
        self._retry_wait_s = _NTP_CHECK_INTERV  # the unsynced wait: every check until an attempt fails; reset by a sync or a forced resync
        self._unsynced_wait_s = 0  # seconds since the last unsynced attempt was triggered
        self._attempting = False  # a sync attempt in flight (_sync_loop()): a check tick meanwhile triggers none
        self._ntp_sec_count = 0
        self._ntp_retries = 0
        self._sync_age = TickSeconds()
        self._clock_valid = False  # ntp_clock_valid(): set by each successful sync, unset by a settings change
        self._ntp_sync_trigger_event = asyncio.ThreadSafeFlag()
        self._check = TickGrid(_NTP_CHECK_INTERV * 1000)  # the refresh check's cadence
        self._retry_due = False  # a failed synced attempt's retry: _sync_loop() waits _NTP_RETRY_INTERV, then retries

    async def _get_ntp_config(self) -> tuple[str, str, int] | None:
        values = await self.cfgmgr.get_str_values(_VAL_NTP_HOST + _VAL_DNS_FALLBACK)
        offs = await self.cfgmgr.get_int_values(_VAL_NTP_OFFSET)
        if values is None or offs is None or len(values) != _NTP_STR_COUNT or len(offs) != 1:
            return None
        host, fallback = values
        return host, fallback, offs[0]

    async def _set_mgr_cfg(self, data: "JsonMapping", cfg_vals: "ConfigSchema") -> "tuple[bool, WriteValidity]":
        # NTPHost and DNSFallback are shape-checked before they are stored; the rest of the request goes through
        # ConfigManager as usual (SPECIFICATION.md C.7.2).
        refused = {}
        if "NTPHost" in data and not _ntp_host_ok(data["NTPHost"]):
            refused["NTPHost"] = "- not a host name or IPv4 address"
        if "DNSFallback" in data and not _dns_fallback_ok(data["DNSFallback"]):
            refused["DNSFallback"] = "- not a list of up to three IPv4 addresses"
        for key, why in refused.items():
            self.pr.err_q("Refusing", key, why, errno=_ERR_BAD_ARG)
        ok, results = await super()._set_mgr_cfg({k: v for k, v in data.items() if k not in refused}, cfg_vals)
        for key in refused:
            results[key] = INVALID
        return ok, results

    async def _set_synced(self, *, value: bool) -> None:
        # Nothing runs between this get and the set below: an uncontended lock never yields (Part F.1).
        # get_data() keeps the NTP fields typed, not the base class's generic NamedTuple.
        data = await self.get_data()
        await self._set_meas_data(NTP(Synced=value, LastSyncAge=data.LastSyncAge, TS=data.TS))

    async def _fetch_ntp_reply(self, addr: tuple[str, int]) -> bytes | None:
        cli = UDPSocket(addr, mode="client", logger=self.pr)
        # Only the connected server's replies reach this socket (lwIP udp_input()); no origin check (SPECIFICATION.md C.7.2).
        # write()/recvfrom()/disconnect() never raise: each returns its None-shaped sentinel (asy_udp_socket.py).
        try:
            if await cli.write(b"\x1b" + bytearray(47), timeout_ms=self._ntp_fetch_timeout_ms) is None:
                self.pr.err_q("NTP request not sent to", addr[0], errno=_ERR_NTP_NOT_SENT)
                return None
            msg, _ = await cli.recvfrom(1024, timeout_ms=self._ntp_fetch_timeout_ms)
        finally:
            await cli.disconnect()
        if msg is None:
            self.pr.err_q("No reply from NTP server:", addr[0], errno=_ERR_NTP_NO_REPLY)
        return msg

    async def _handle_ntp_sync_failure(self) -> None:
        self.pr.all("Invalid NTP time received!")
        if await self.ntp_issynced():  # in case of already synced, retry if regular trigger fails
            if (
                self._ntp_retries < _NTP_SYNC_RETRIES
            ):  # if not synced at all, self._refresh_loop() will permanently try to sync
                self.pr.evt("Waiting for NTP sync retry.")
                self._retry_due = True
                self._ntp_retries += 1
            else:
                self.pr.err_q("Maximum retries reached, cancelling sync!", errno=_ERR_NTP_RETRIES)
                self._ntp_retries = 0

    async def _handle_ntp_sync_success(self, tm: tuple[int, ...]) -> None:
        set_utc_valid()  # the RTC was just set (_parse_ntp_reply()): every later utc_now() is a real time
        self._clock_valid = True
        self._ntp_retries = 0
        self._reset_retry_wait()
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
                self.pr.wrn_q("NTP reply unsynchronized or Kiss-of-Death, rejecting:", leap_indicator, stratum, wrnno=_WRN_NTP_UNSYNC_REPLY)
                return None
            raw_s = struct.unpack("!I", msg[40:44])[0]
            if raw_s == 0:  # A zero timestamp is unset (RFC 5905 6); the era step below would read it as 2036.
                self.pr.err_q("NTP reply has no transmit timestamp, rejecting", errno=_ERR_NTP_MALFORMED)
                return None
            ntp_time = raw_s - _NTP_EPOCH_DELTA + ntp_offset_s  # assume the current NTP era first
            if ntp_time < _NTP_MIN_PLAUSIBLE_UNIX_TIME:
                # Either a still-wrapped reply from the next NTP era (RFC 5905 7.3) - reinterpret
                # and recheck - or implausible data, rejected below if still out of range.
                ntp_time += _NTP_ERA_SECONDS
            if not (_NTP_MIN_PLAUSIBLE_UNIX_TIME <= ntp_time <= _NTP_MAX_PLAUSIBLE_UNIX_TIME):
                self.pr.err_q("Implausible NTP time, rejecting:", ntp_time, errno=_ERR_NTP_IMPLAUSIBLE)
                return None
            self.pr.all("Received NTP time:", ntp_time)
            tm = time.gmtime(ntp_time)
            RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
        except (IndexError, OverflowError, ValueError, OSError) as e:
            # malformed/truncated reply (MicroPython's struct raises plain ValueError, not
            # struct.error) or an out-of-range timestamp - treat like no response.
            self.pr.err_q("Malformed NTP reply, treating as no response:", e, errno=_ERR_NTP_MALFORMED)
            return None
        else:
            return tm

    async def _refresh_loop(self) -> None:  # the NTP refresh check, every _NTP_CHECK_INTERV on its grid
        self._ntp_sec_count = 0
        while True:
            await self._check.wait()
            ntp_interv = await self.cfgmgr.get_int_values(_VAL_NTP_INTERVAL)
            if ntp_interv is None or len(ntp_interv) != 1:
                ntp_interv = [12]
                await self.pr.err_s("Missing NTP configuration, defaulting interval to 12h!", errno=_ERR_CFG_READ)

            if await self.ntp_issynced():
                # Stale once the last success is _NTP_ASYNC_INTERV intervals old; a failed due resync resets only the due count, never
                # this age (agent, 2026-09-27; owner-reviewed, 2026-10-02; legacy's intent,
                # legacy/firmware/python/CommonDrivers/async_connect.py:450-461).
                if self._sync_age.read() >= _NTP_ASYNC_INTERV * ntp_interv[0] * 3600:
                    await self._set_synced(value=False)
                else:
                    self._ntp_sec_count += _NTP_CHECK_INTERV

            self.pr.all("Sync-age tick counter at", self._ntp_sec_count)
            if await self.ntp_issynced():
                due = self._ntp_sec_count >= (ntp_interv[0] * 60 * 60)
            else:
                self._unsynced_wait_s += _NTP_CHECK_INTERV
                due = self._unsynced_wait_s >= self._retry_wait_s and not self._attempting
            if due:
                self._ntp_retries = 0
                self._ntp_sync_trigger_event.set()
                self._ntp_sec_count = 0
                self._unsynced_wait_s = 0
                self.pr.evt("NTP resync triggered.")
            del ntp_interv

    def _reset_retry_wait(self) -> None:
        self._retry_wait_s = _NTP_CHECK_INTERV
        self._unsynced_wait_s = 0

    async def _resolve_ntp_server(self, ntp_host: str, dns_server: str | None, fallback: str) -> tuple[str, int] | None:
        servers = (() if dns_server is None else (dns_server,)) + tuple(s for s in fallback.split(",") if s)
        ip = await resolve_ipv4(ntp_host, servers, timeout_ms=self._dns_timeout_ms, tries=self._dns_tries, logger=self.pr)
        if ip is None:
            self.pr.err_q("No valid NTP server:", ntp_host, errno=_ERR_NTP_DNS)
            return None
        return ip, _NTP_UDP_PORT

    async def _run_ntp_sync_attempt(self, dns_server: str | None) -> tuple[tuple[int, ...] | None, bool]:
        try:
            network_ok = self._network_available_locked()
        except Exception as e:  # caller-supplied callback - could legitimately misbehave
            self.pr.err_q("network_available_locked() callback failed:", e, errno=_ERR_CALLBACK)
            network_ok = False
        if not network_ok:
            self.pr.all("Network not available, skipping sync attempt.")
            return None, False
        ntp_config = await self._get_ntp_config()
        if ntp_config is None:
            await self._set_synced(value=False)
            self.pr.err_q("Missing NTP configuration!", errno=_ERR_CFG_READ)
            return None, True
        ntp_host, fallback, ntp_offs = ntp_config
        addr = await self._resolve_ntp_server(ntp_host, dns_server, fallback)
        if addr is None:
            await self._handle_ntp_sync_failure()
            return None, True
        msg = await self._fetch_ntp_reply(addr)
        if msg is None:
            await self._handle_ntp_sync_failure()
            return None, True
        tm = await self._parse_ntp_reply(msg, ntp_offs)
        if tm is None:
            await self._handle_ntp_sync_failure()
        else:
            await self._handle_ntp_sync_success(tm)
        return tm, True

    async def _safe_get_dns_server(self) -> str | None:
        # WifiService.get_dns_server_ip() returns its last snapshot's DHCP server without taking a lock (None without
        # a connected link or with the radio deactivated); read before the attempt takes wifi_mode_lock.
        try:
            return self._get_dns_server()
        except Exception as e:  # caller-supplied callback - could legitimately misbehave
            await self.pr.err_s("get_dns_server() callback failed:", e, errno=_ERR_CALLBACK)
            return None

    async def _sync_loop(self) -> None:
        self._attempting = False  # a restart after a raise mid-attempt starts clear
        await self._set_meas_data(NTP(Synced=False, LastSyncAge=None, TS=utc_now()))
        while True:
            if self._retry_due:  # the retry: a trigger meanwhile is this attempt, so it is consumed
                self._retry_due = False
                await asyncio.sleep_ms(_NTP_RETRY_INTERV * 1000)
                self._ntp_sync_trigger_event.clear()
            else:
                await self._ntp_sync_trigger_event.wait()
            self.pr.evt("NTP sync starting.")
            dns_server = await self._safe_get_dns_server()  # the snapshot's DHCP server, read outside wifi_mode_lock
            self._attempting = True
            async with self.wifi_mode_lock:
                tm, network_ok = await self._run_ntp_sync_attempt(dns_server)
            self._attempting = False
            # Never gives up (Part C.7.2): a failed unsynced attempt waits _NTP_RETRY_UNSYNCED_S for the next
            # (a synced one has _handle_ntp_sync_failure()'s retries). A skipped one leaves the wait alone.
            if tm is None and network_ok and not await self.ntp_issynced():
                self._retry_wait_s = _NTP_RETRY_UNSYNCED_S

    def get_task_starters(self) -> "list[TaskStarter]":
        return [self.start_asy_sync, self.start_asy_refresh]

    def start_asy_refresh(self) -> asyncio.Task[None]:
        return asyncio.create_task(self._refresh_loop())

    def start_asy_sync(self) -> asyncio.Task[None]:
        return asyncio.create_task(self._sync_loop())

    async def get_data(self) -> NTP:
        # Narrows to this Reader's concrete NTP (SPECIFICATION.md C.4.2); LastSyncAge is measured as it is read:
        # the seconds since the last success while synced, else None.
        data: NTP = await self._get_meas_data()  # type: ignore[assignment]
        return NTP(Synced=data.Synced, LastSyncAge=self._sync_age.read() if data.Synced else None, TS=data.TS)

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(self.name, _VAL_NTP_HOST + _VAL_NTP_OFFSET + _VAL_NTP_INTERVAL + _VAL_GMT_OFFSET + _VAL_DST_OFFSET + _VAL_DNS_FALLBACK)

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data, _FIELDS, name=self.name)

    async def cettime(
        self,
    ) -> GMTimeStruct | None:  # local-time conversion
        # Gated on the clock having been set this boot, not on Synced: the RTC keeps good time after a sync goes
        # stale, so local-time consumers (the alert window) keep running through a network loss (owner, 2026-10-21: "Clock time: Option b"; owner, 2026-10-27).
        if utc_now() is None:
            return None
        time_offs = await self.cfgmgr.get_int_values(_VAL_GMT_OFFSET + _VAL_DST_OFFSET)
        if time_offs is None or len(time_offs) != _TIME_OFFSET_COUNT:
            return None
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
        if len(cet) == _GMTIME_FIELDS:
            return GMTimeStruct(*cet)
        return None

    async def ntp_clock_valid(self) -> bool:
        # The clock UTCTime and the VOC backups read: set by each successful sync, unset only by a settings change
        # (ntp_force_sync()). Staleness clears Synced alone, so a clock set this boot stays in use through it.
        return self._clock_valid

    async def ntp_force_sync(self) -> None:
        # A settings change clears Synced, as legacy did: nothing runs on a sync taken under the old settings (owner, 2026-09-29).
        data = await self.get_data()
        await self._set_meas_data(NTP(Synced=False, LastSyncAge=None, TS=data.TS))
        self._clock_valid = False  # UTCTime and the VOC backups wait for the next sync too
        self._ntp_retries = 0
        self._reset_retry_wait()  # an operator's resync tries at the next check, never after a failed attempt's wait
        self._ntp_sync_trigger_event.set()
        self.pr.evt("Force resync triggered.")

    async def ntp_issynced(self) -> bool:
        return bool((await self.get_data()).Synced)
