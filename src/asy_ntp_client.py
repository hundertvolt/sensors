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

from machine import RTC, Timer
from micropython import const

from asy_base_classes import SensorReaderConfig, TickSeconds, arm_tick_timer, set_utc_valid, utc_now
from asy_config_manager import INVALID, make_dict
from asy_dns_client import host_name_ok, ipv4_to_int, resolve_ipv4
from asy_print_log import DEFAULT_LOG, LogConfig
from asy_udp_socket import UDPSocket

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import NamedTuple

    from asy_base_classes import JsonMapping, TaskStarter, TimerStarter
    from asy_config_manager import ConfigSchema, WriteValidity
    from asy_print_log import ErrorLog

# Codes from the global catalog (buildgen/error_catalog.json): the shared ones and NTP's band.
_ERR_CALLBACK = const(14)
_ERR_TIMER = const(17)
_ERR_ALLOC = const(20)
_ERR_BAD_ARG = const(21)
_ERR_CFG_READ = const(26)
_ERR_NTP_DNS = const(67)
_ERR_NTP_IMPLAUSIBLE = const(68)
_ERR_NTP_MALFORMED = const(69)
_ERR_NTP_RETRIES = const(70)
_ERR_NTP_NO_REPLY = const(71)
_ERR_NTP_NOT_SENT = const(72)
_WRN_STORED_DEFAULT = const(10)
_WRN_SOCKET_TEARDOWN = const(12)
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

_NTP_UDP_PORT = const(123)  # RFC 5905 SS7.2
_NTP_PACKET_LEN = const(48)  # RFC 5905 SS7.3: the NTP header; the reply fields read end at byte 48
_NTP_REQUEST = b"\x1b" + bytes(_NTP_PACKET_LEN - 1)  # LI 0, VN 3, mode 3 (client); built once, so an attempt allocates none

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
# @web DNSFallback section=networking submitGroup=dns label="Fallback DNS Servers" shape=ipv4List description="Asked after the DHCP-provided server fails. Empty = none. The website cannot send an empty value (Part H.4); use the API."

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
        self._check_armed: bool | None = None  # each timer starter's outcome: None until attempted
        self._tick_armed: bool | None = None

    async def _get_ntp_config(self) -> tuple[str, str, int] | None:
        values = await self.cfgmgr.get_str_values(_VAL_NTP_HOST + _VAL_DNS_FALLBACK)
        offs = await self.cfgmgr.get_int_values(_VAL_NTP_OFFSET)
        if values is None or offs is None or len(values) != _NTP_STR_COUNT or len(offs) != 1:
            return None
        host, fallback = values
        if not host_name_ok(host):
            await self.pr.wrn_s("Stored NTPHost is not a host name, using its default", wrnno=_WRN_STORED_DEFAULT)
            host = _VAL_NTP_HOST[0][2]
        if not _dns_fallback_ok(fallback):  # a file written outside the PUT path; four servers would break the C.8 bound
            await self.pr.wrn_s("Stored DNSFallback is not a list of up to three IPv4 addresses, using its default", wrnno=_WRN_STORED_DEFAULT)
            fallback = _VAL_DNS_FALLBACK[0][2]
        return host, fallback, offs[0]

    async def _set_last_sync_age(self, *, value: int | None) -> None:
        data = await self.get_data()
        await self._set_meas_data(NTP(Synced=data.Synced, LastSyncAge=value, TS=data.TS))

    async def _set_mgr_cfg(self, data: "JsonMapping", cfg_vals: "ConfigSchema") -> "tuple[bool, WriteValidity]":
        # NTPHost and DNSFallback are shape-checked before they are stored; the rest of the request goes through
        # ConfigManager as usual (SPECIFICATION.md C.7.2).
        refused = {}
        if "NTPHost" in data and not host_name_ok(data["NTPHost"]):
            refused["NTPHost"] = "- not a host name or IPv4 address"
        if "DNSFallback" in data and not _dns_fallback_ok(data["DNSFallback"]):
            refused["DNSFallback"] = "- not a list of up to three IPv4 addresses"
        for key, why in refused.items():
            await self.pr.err_s("Refusing", key, why, errno=_ERR_BAD_ARG)
        ok, results = await super()._set_mgr_cfg({k: v for k, v in data.items() if k not in refused}, cfg_vals)
        for key in refused:
            results[key] = INVALID
        return ok, results

    async def _set_synced(self, *, value: bool) -> None:
        # Nothing runs between this get and the set below: an uncontended lock never yields (Part F.1).
        # get_data() keeps the NTP fields typed, not the base class's generic NamedTuple.
        data = await self.get_data()
        await self._set_meas_data(NTP(Synced=value, LastSyncAge=data.LastSyncAge, TS=data.TS))

    def _arm_check_timer(self) -> bool:
        try:
            self._ntp_timer.init(
                period=_NTP_CHECK_INTERV * 1000,
                mode=Timer.PERIODIC,
                callback=lambda _b: self._ntp_timer_trigger_event.set(),
            )
        except (MemoryError, OSError) as e:  # alarm-pool exhaustion (ENOMEM, Part F.1): retried at the next sync trigger;
            # a second failure ends the task for the supervisor (_rearm_failed_timers()).
            self.pr.err("Could not start NTP timer:", e)
            return False
        return True

    async def _fetch_ntp_reply(self, addr: tuple[str, int]) -> bytes | None:
        cli = UDPSocket(addr, mode="client")
        # Only the connected server's replies reach this socket (lwIP udp_input()); no origin check (SPECIFICATION.md C.7.2).
        # write()/recvfrom()/disconnect() never raise: each returns its None-shaped sentinel (asy_udp_socket.py).
        try:
            if await cli.write(_NTP_REQUEST, timeout_ms=self._ntp_fetch_timeout_ms) is None:
                await self.pr.err_s("NTP request not sent to", addr[0], errno=_ERR_NTP_NOT_SENT)
                return None
            msg, _ = await cli.recvfrom(_NTP_PACKET_LEN, timeout_ms=self._ntp_fetch_timeout_ms)
        finally:
            if not await cli.disconnect():
                await self.pr.wrn_s("NTP socket teardown did not complete cleanly.", wrnno=_WRN_SOCKET_TEARDOWN)
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
                    # ONE_SHOT: a dropped fire loses only this retry; _refresh_loop()'s due check starts the next sync once NTPInterval (default 12 h) has passed.
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
            if len(msg) < _NTP_PACKET_LEN:
                await self.pr.err_s("Short NTP reply, treating as no response:", len(msg), errno=_ERR_NTP_MALFORMED)
                return None
            leap_indicator = (msg[0] >> 6) & 0x3
            stratum = msg[1]
            if leap_indicator == _NTP_LI_UNSYNCHRONIZED or stratum == _NTP_STRATUM_INVALID:
                # Server says its own clock is unsynchronized, or this is a Kiss-o'-Death packet -
                # never a genuine time source, regardless of its Transmit Timestamp.
                await self.pr.wrn_s("NTP reply unsynchronized or Kiss-of-Death, rejecting:", leap_indicator, stratum, wrnno=_WRN_NTP_UNSYNC_REPLY)
                return None
            raw_s = struct.unpack("!I", msg[40:44])[0]
            if raw_s == 0:  # A zero timestamp is unset (RFC 5905 6); the era step below would read it as 2036.
                await self.pr.err_s("NTP reply has no transmit timestamp, rejecting", errno=_ERR_NTP_MALFORMED)
                return None
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
        except MemoryError as e:  # the shared allocation code (Part F.1), not the malformed-reply one
            await self.pr.err_s("NTP reply could not be parsed, treating as no response:", e, errno=_ERR_ALLOC)
            return None
        except OSError as e:
            # The RTC set refused - treat like no response. A short or unset reply is refused above, so no
            # IndexError or ValueError reaches here (every index and the unpack lie inside the 48-byte header).
            await self.pr.err_s("Malformed NTP reply, treating as no response:", e, errno=_ERR_NTP_MALFORMED)
            return None
        else:
            return tm

    async def _rearm_failed_timers(self) -> bool:
        # A starter that failed is retried from the task; a second failure is persisted and ends the task for the
        # supervisor, whose restart retries it again (Part C.9). False: the caller returns.
        if self._check_armed is False:
            self._check_armed = self._arm_check_timer()
            if not self._check_armed:
                await self.pr.err_s("NTP", "check", "timer not armed", errno=_ERR_TIMER)
                return False
        if self._tick_armed is False:
            self._tick_armed = arm_tick_timer(self._counter_timer, self._time_counter_trigger_event, self.pr, "NTP sync age")
            if not self._tick_armed:
                await self.pr.err_s("NTP", "sync-age", "timer not armed", errno=_ERR_TIMER)
                return False
        return True

    async def _refresh_loop(self) -> None:  # NTP refresh timer
        self._ntp_sec_count = 0
        while True:
            await self._ntp_timer_trigger_event.wait()
            ntp_interv = await self.cfgmgr.get_int_values(_VAL_NTP_INTERVAL)
            if ntp_interv is None or len(ntp_interv) != 1:
                ntp_interv = [12]
                await self.pr.err_s("Missing NTP configuration, defaulting interval to 12h!", errno=_ERR_CFG_READ)

            if await self.ntp_issynced():
                # Stale once the last success is _NTP_ASYNC_INTERV intervals old; a failed due resync resets only the due cadence, never this age
                # (agent, 2026-09-27; owner-reviewed, 2026-10-02; legacy's intent, legacy/firmware/python/CommonDrivers/async_connect.py:450-461).
                if self._sync_age.read() >= _NTP_ASYNC_INTERV * ntp_interv[0] * 3600:
                    await self._set_synced(value=False)
                else:
                    self._ntp_sec_count += _NTP_CHECK_INTERV

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

    async def _resolve_ntp_server(self, ntp_host: str, dns_server: str | None, fallback: str) -> tuple[str, int] | None:
        servers = (() if dns_server is None else (dns_server,)) + tuple(s for s in fallback.split(",") if s)
        ip = await resolve_ipv4(ntp_host, servers, timeout_ms=self._dns_timeout_ms, tries=self._dns_tries, pr=self.pr)
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
        if not await self._rearm_failed_timers():
            return
        while True:
            await self._ntp_sync_trigger_event.wait()
            if not await self._rearm_failed_timers():
                return
            self.pr.evt("NTP sync starting.")
            dns_server = await self._safe_get_dns_server()  # the snapshot's DHCP server, read outside wifi_mode_lock
            async with self.wifi_mode_lock:
                tm, network_ok = await self._run_ntp_sync_attempt(dns_server)
            # Never gives up (Part C.7.2): a failed unsynced attempt only lengthens the retry interval
            # (a synced one has _handle_ntp_sync_failure()'s retries). A skipped one leaves it alone.
            if tm is None and network_ok and not await self.ntp_issynced():
                self._retry_wait_s = min(self._retry_wait_s * _NTP_BACKOFF_MULT, self._retry_max_s)

    def get_task_starters(self) -> "list[TaskStarter]":
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
        self._check_armed = self._arm_check_timer()

    def start_sync_age_timer(self) -> None:
        self._tick_armed = arm_tick_timer(self._counter_timer, self._time_counter_trigger_event, self.pr, "NTP sync age")

    def stop_check_timer(self) -> None:
        self._ntp_timer.deinit()

    def stop_sync_age_timer(self) -> None:
        self._counter_timer.deinit()

    async def get_data(self) -> NTP:
        # Narrows to this Reader's concrete NTP - see SPECIFICATION.md C.4.2's get_data() convention.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(self.name, _VAL_NTP_HOST + _VAL_NTP_OFFSET + _VAL_NTP_INTERVAL + _VAL_GMT_OFFSET + _VAL_DST_OFFSET + _VAL_DNS_FALLBACK)

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data, _FIELDS, name=self.name)

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    async def get_last_ntp_sync(self) -> int | None:  # None = not synced now: never, gone stale, or cleared by a settings change
        age = (await self.get_data()).LastSyncAge
        return None if age is None else int(age)

    async def cettime(
        self,
    ) -> GMTimeStruct | None:  # local-time conversion
        # Gated on the clock having been set this boot, not on Synced: the RTC keeps good time after a sync goes
        # stale, so local-time consumers (the alert window) keep running through a network loss (agent, 2026-10-06).
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

    async def ntp_force_sync(self) -> None:
        # A settings change clears Synced, as legacy did: nothing runs on a sync taken under the old settings (owner, 2026-09-29).
        data = await self.get_data()
        await self._set_meas_data(NTP(Synced=False, LastSyncAge=None, TS=data.TS))
        self._ntp_retry_timer.deinit()
        self._ntp_retries = 0
        self._reset_backoff()  # an operator's resync must not wait out a long backoff step
        self._ntp_sync_trigger_event.set()
        self.pr.evt("Force resync triggered.")

    async def ntp_issynced(self) -> bool:
        return bool((await self.get_data()).Synced)
