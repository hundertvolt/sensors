"""Async NTP client + CET/CEST local-time helper (asy_ntp_client). Not a sensor (no I2C/SPI bus),
but config-managed the same way as every promoted sensor driver: extends base_classes.py's
SensorReaderConfig, owns its own config_NTP.cfg file/schema internally - no externally-injected
ConfigManager, no separate get_default_cfg()/_DEFAULT_CONFIG merge step. See DRIVER_SPEC.md for the
shared contract this follows and BACKLOG.md for why a service (not just a sensor) fits it too.

Verified against RFC 5905 (NTPv4) - see BACKLOG.md for the full packet-format/era-rollover/Kiss-of-
Death verification history. Config setters are explicitly out of scope (DRIVER_SPEC.md section 5,
project owner's stated decision) - only the getter quartet (get_data()/get_dict_data()/
get_dict_cfg()/get_error_counter()) is implemented here.

get_task_starters()/get_timer_starters() (DRIVER_SPEC.md section 9 requires both on every driver/
service) and max_i2c_err/_error_check() (was previously inert, like asy_wifi_service.py's own
max_i2c_err before it was wired up) were added later, alongside asy_ntp_time()'s own
self.pr.setup() call (base_classes.py's SensorReaderConfig.__init__ never calls this itself - every
promoted sensor driver's _init_<sensor>() does, this file had no equivalent entry point before).
_error_check()'s streak is a coarser, independent safety net layered on top of
_handle_ntp_sync_failure()'s own short-term ntp_retries/_NTP_SYNC_RETRIES retry loop - see
asy_ntp_time()'s own comment. Every errno/wrnno this file assigns starts at 11, not 1: base_classes
.py's own _error_check()/_get_dict_cfg() already claim errno 1-4 internally for any driver that
calls them (both now called here), and 10 is the shared "initial setup failed" convention (DRIVER_
SPEC.md section 7) which doesn't apply to this file (no protocol-layer setup() to fail) - skipped
rather than reused for something else, to keep that convention meaningful project-wide.

_resolve_ntp_server() no longer calls socket.getaddrinfo() - a real, synchronously-blocking call
(see BACKLOG.md's original finding) - and consequently no longer needs async_connect.py's
get_long_block_lock() coordination either. It now delegates to asy_dns_client.py's resolve_ipv4(),
a from-scratch async DNS client (inspired by, not a port of, github.com/vshymanskyy/aiodns - see
that file's own module docstring for the full comparison and licensing note) built on this
project's own AsyUDPSocket, which already yields to the event loop throughout instead of blocking
it. A new get_dns_server callback (asy_conn_time.get_dns_server_ip, mirroring the existing
network_available callback's shape) supplies the network's own DHCP-assigned DNS server as the
first server tried, falling back to public resolvers if it's unavailable. The asy_long_block_lock
constructor parameter, field, and get_long_block_lock() method are removed entirely - this file was
the shared lock's only real user (see BACKLOG.md); neopixel_signal.py's own use of the same lock
(coordinating its LED animation against this file's block) is removed alongside it for the same
reason, not left as now-pointless dead wiring. See BACKLOG.md for the full before/after design
writeup, including why this doesn't resolve (or foreclose) the still-open question of whether
config_manager.py's write_config() separately needs long-block coordination of its own.

_resolve_ntp_server()'s returned port is now the module-level _NTP_UDP_PORT (still 123, unchanged
behavior) rather than a bare literal - see that constant's own comment for why it's deliberately not
const()-wrapped like every sibling constant here.
"""

import asyncio
import struct
import time
from collections import namedtuple

from machine import RTC, Timer
from micropython import const
from uasyncio import Lock, ThreadSafeFlag

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

_NTP_UDP_PORT = 123  # RFC 5905's standard NTP port. Deliberately NOT const()-wrapped, unlike every
# other module-level constant here: MicroPython's const() inlines the literal at compile time
# (confirmed directly - see asy_dns_client.py's own _FALLBACK_DNS_SERVERS for the same reasoning),
# so tests/test_asy_ntp_client.py's real-network integration tests can redirect this to a fake NTP
# server's own ephemeral port (binding a real listener on the actual port 123 needs root/
# CAP_NET_BIND_SERVICE, which CI runners don't have). _resolve_ntp_server() reads this once per
# sync attempt (hours apart), so skipping the const-fold costs nothing performance-wise here.

_NTP_EPOCH_DELTA = const(2208988800)  # 1900 -> 1970, RFC 5905's NTP-to-Unix epoch conversion
_NTP_ERA_SECONDS = const(4294967296)  # 2**32 - one full NTP era (the 32-bit seconds field wraps ~2036)
# Plausibility window for a parsed NTP reply, see BACKLOG.md. A floor alone can't actually reject
# anything once era-reinterpretation is in play: for any 32-bit raw value, either the current-era
# reading already clears the floor, or adding one era pushes it decades past the floor - some
# interpretation always "looks" post-floor. Pairing the floor with a ceiling is what gives this an
# actual ability to reject implausible/corrupt data instead of just always picking a plausible-
# looking era: a raw value only gets rejected if BOTH the current-era and the next-era reading fall
# outside [floor, ceiling] - which does happen for a wide swath of the raw range (see BACKLOG.md's
# worked example). Both bounds need bumping forward occasionally to stay "recent enough"/"far
# enough out" without ever needing to track wall-clock time itself.
_NTP_MIN_PLAUSIBLE_UNIX_TIME = const(1735689600)  # 2025-01-01T00:00:00Z - no genuine reply can
# predate this file's own writing.
_NTP_MAX_PLAUSIBLE_UNIX_TIME = const(4102444800)  # 2100-01-01T00:00:00Z - comfortably past the
# ~2036 era wrap (so a real post-2036 reply still passes) but not so far out that it stops meaning
# anything as a sanity check; this file isn't expected to still be running unmodified by then.

_NTP_LI_UNSYNCHRONIZED = const(3)  # RFC 5905's Leap Indicator field (top 2 bits of byte 0): 3 means
# "unknown (clock unsynchronized)" - an alarm condition. The server is explicitly saying its own
# time isn't trustworthy yet (e.g. just rebooted, hasn't synced upstream itself); its Transmit
# Timestamp can still look like a perfectly plausible date and pass the floor/ceiling window above,
# so this needs its own check rather than being caught by the plausibility bounds.
_NTP_STRATUM_INVALID = const(0)  # RFC 5905/4330: stratum 0 means "unspecified or invalid" - used for
# Kiss-o'-Death (KoD) packets (mode 4, LI 3, stratum 0, an ASCII "kiss code" in the Reference
# Identifier field, e.g. rate-limiting a client that's polling too fast). A KoD reply's Transmit
# Timestamp is typically all-zero, which - concretely, not just in theory - lands exactly on
# 2036-02-07T06:28:16Z after this file's own era-reinterpretation step (era 0's max representable
# value plus one second), squarely inside the plausibility window above; without this check it would
# be silently accepted as a genuine successful sync.

# Schema tuples for ConfigManager.get_*_values() - min/max mirror the REST-API bounds
# sensortask-wozi.py's update_valid_json() already enforces for these same fields, so both
# validation paths agree; defaults are the only source of truth for a fresh config_NTP.cfg now -
# there is no separate _DEFAULT_CONFIG JSON blob to keep in sync with these anymore.
_VAL_NH = const((("NTP_Host", "str", "pool.ntp.org", 3, 1024, None),))
_VAL_NOS = const((("NTP_Offset_S", "int", 0, -43200, 43200, None),))
_VAL_NIH = const((("NTP_Interv_H", "int", 12, 1, 24, None),))
_VAL_GMT = const((("GMTOffset", "int", 3600, -43200, 43200, None),))
_VAL_DST = const((("DSTOffset", "int", 3600, -43200, 43200, None),))

_NAME = const("NTP")
NTP = namedtuple("NTP", ("Synced", "LastSyncAge", "TS"))
GMTimeStruct = namedtuple("GMTimeStruct", ("year", "month", "mday", "hour", "minute", "second", "weekday", "yearday"))


class asy_ntp_client(SensorReaderConfig):
    def __init__(
        self,
        wifi_mode_lock: Lock,
        network_available: "Callable[[], bool]",
        get_dns_server: "Callable[[], str | None]",
        max_i2c_err: int = 5,
        cfg_path: str = "",
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        super().__init__(
            NTP(False, None, None),
            max_i2c_err,  # inert here - this driver never calls _error_check(); kept only because
            # SensorReaderConfig's own constructor contract requires it.
            _NAME,
            _VAL_NH + _VAL_NOS + _VAL_NIH + _VAL_GMT + _VAL_DST,
            cfg_path=cfg_path,
            fram=fram,
            history_length=history_length,
            debug=debug,
        )
        self.wifi_mode_lock = wifi_mode_lock  # shared with asy_conn_time - protects the WLAN state this class only reads
        self.network_available = network_available  # asy_conn_time.network_available - caller must hold wifi_mode_lock
        self.get_dns_server = get_dns_server  # asy_conn_time.get_dns_server_ip - the network's own DHCP-assigned DNS server, or None
        self.ntp_sec_count = 0
        self.ntp_retries = 0
        self.ntp_sync_trigger_event = ThreadSafeFlag()
        self.ntp_timer_trigger_event = ThreadSafeFlag()
        self.time_counter_trigger_event = ThreadSafeFlag()
        self.ntp_timer = Timer()
        self.ntp_retry_timer = Timer()
        self.counter_timer = Timer()

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
        except OSError as e:  # alarm-pool exhaustion (ENOMEM, see BACKLOG.md) - degrades gracefully;
            # NTP refresh scheduling just never starts rather than crashing the caller.
            self.pr.err(_NAME, "Could not start NTP timer:", e)

    def start_counter_timer(self) -> None:
        try:
            self.counter_timer.init(
                period=1000,
                mode=Timer.PERIODIC,
                callback=lambda b: self.time_counter_trigger_event.set(),
            )
        except OSError as e:  # alarm-pool exhaustion (ENOMEM) - same graceful degradation as start_ntp_timer()
            self.pr.err(_NAME, "Could not start counter timer:", e)

    def stop_ntp_timer(self) -> None:
        self.ntp_timer.deinit()

    def stop_counter_timer(self) -> None:
        self.counter_timer.deinit()

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_ntp_client, self.start_asy_ntp_refresh, self.start_asy_sync_age_counter]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return [self.start_ntp_timer, self.start_counter_timer]

    def _now(self) -> int | None:
        try:
            return time.mktime(time.gmtime())
        except (OverflowError, OSError):  # rp2's mktime()/gmtime() raise past its ~2037 32-bit epoch range
            return None

    async def _set_synced(self, value: bool) -> None:
        # Safe without holding one lock across both calls: MicroPython's asyncio.Lock.acquire()
        # never yields when uncontended (extmod/asyncio/lock.py) - nothing else can run between this
        # get and the following set unless something in between itself awaits, and nothing here does.
        # Reads via get_data() (not _get_meas_data() directly) so the concrete NTP fields below are
        # typed, not the base class's generic "NamedTuple" - see get_data()'s own comment.
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

    async def get_data(self) -> NTP:
        # Narrows _get_meas_data()'s generic "NamedTuple" to this Reader's concrete NTP;
        # typing.cast() isn't usable (no runtime presence on MicroPython) so this identity return
        # does the same job - see DRIVER_SPEC.md's get_data() narrowing convention.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data)

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(_NAME, _VAL_NH + _VAL_NOS + _VAL_NIH + _VAL_GMT + _VAL_DST)

    async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:
        return await self.pr.get_log(_NAME)

    async def ntp_issynced(self) -> bool:
        return bool((await self.get_data()).Synced)

    async def ntp_force_sync(self) -> None:
        await self._set_last_sync_age(None)
        self.ntp_retry_timer.deinit()
        self.ntp_retries = 0
        self.ntp_sync_trigger_event.set()
        self.pr.evt(_NAME, "Force resync triggered.")

    async def get_last_ntp_sync(self) -> int | None:  # None = never synced yet
        age = (await self.get_data()).LastSyncAge
        return None if age is None else int(age)

    async def asy_ntp_time(self) -> None:  # Funktion: Zeit per NTP holen
        await self.pr.setup()  # required for all logged warnings and errors (base_classes.py's own
        # __init__ never calls this - matches every _init_<sensor>() in the three promoted drivers)
        self._err_cnt_internal = 0  # fresh failure streak each task (re)start, same as _init_<sensor>()
        await self._set_meas_data(NTP(False, None, self._now()))
        while True:
            await self.ntp_sync_trigger_event.wait()
            self.pr.evt(_NAME, "NTP sync starting.")
            await self.wifi_mode_lock.acquire()
            try:
                tm, network_ok = await self._run_ntp_sync_attempt()
            finally:
                try:
                    self.wifi_mode_lock.release()
                except RuntimeError:  # in case it's already released somehow
                    pass
            # Consecutive-failure streak over real sync attempts (network was available but the
            # attempt still failed) - independent from, and a coarser safety net than,
            # _handle_ntp_sync_failure()'s own ntp_retries/_NTP_SYNC_RETRIES short-term retry
            # loop: this one is about repeated failure across many *trigger cycles* (hours apart,
            # or explicit force-syncs), not about one trigger's own quick retries. condition=
            # network_ok excludes "network wasn't up yet" from counting, the same way SGP40
            # excludes a missing-compensation read via condition=compensated. _error_check()'s
            # results tuple wants int|float|None elements, not tm's own gmtime()-shaped tuple, so
            # this narrows to just tm's presence/absence (its year field, arbitrarily) - the
            # generic check only ever asks "is this None", never the value itself.
            if not await self._error_check((None if tm is None else tm[0],), _NAME, condition=network_ok):
                await self.pr.err_s(_NAME, "Giving up after repeated sync failures, restarting task.", errno=20)
                return

    async def _run_ntp_sync_attempt(self) -> "tuple[tuple[int, ...] | None, bool]":
        try:
            network_ok = self.network_available()
        except Exception as e:  # caller-supplied callback (async_connect.py) - could legitimately misbehave
            await self.pr.wrn_s(_NAME, "network_available() callback failed:", e, wrnno=1)
            network_ok = False
        if not network_ok:
            self.pr.all(_NAME, "Network not available, skipping sync attempt.")
            return None, False
        ntp_config = await self._get_ntp_config()
        if ntp_config is None:
            await self._set_synced(False)
            await self.pr.err_s(_NAME, "Missing NTP configuration!", errno=11)
            return None, True
        ntp_host, ntp_offs = ntp_config
        addr = await self._resolve_ntp_server(ntp_host[0])
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

    async def _get_ntp_config(self) -> tuple[list[str], list[int]] | None:
        ntp_host = await self.cfgmgr.get_str_values(_VAL_NH)
        ntp_offs = await self.cfgmgr.get_int_values(_VAL_NOS)
        if ntp_host is None or ntp_offs is None or len(ntp_host) != 1 or len(ntp_offs) != 1:
            return None
        return ntp_host, ntp_offs

    async def _resolve_ntp_server(self, ntp_host: str) -> tuple[str, int] | None:
        try:
            dns_server = self.get_dns_server()
        except Exception as e:  # caller-supplied callback (asy_conn_time) - could legitimately misbehave, same as network_available()
            await self.pr.wrn_s(_NAME, "get_dns_server() callback failed:", e, wrnno=3)
            dns_server = None
        servers = () if dns_server is None else (dns_server,)
        ip = await resolve_ipv4(ntp_host, servers)
        if ip is None:
            await self.pr.err_s(_NAME, "No valid NTP server:", ntp_host, errno=12)
            return None
        return ip, _NTP_UDP_PORT

    async def _fetch_ntp_reply(self, addr: tuple[str, int]) -> bytes | None:
        try:
            cli = AsyUDPSocket(addr, mode="client")
        except (ValueError, TypeError) as e:  # malformed addr - see AsyUDPSocket's own contract
            await self.pr.err_s(_NAME, "Invalid NTP server address:", e, errno=13)
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

    async def _parse_ntp_reply(self, msg: bytes, ntp_offset_s: int) -> tuple[int, ...] | None:
        try:
            leap_indicator = (msg[0] >> 6) & 0x3
            stratum = msg[1]
            if leap_indicator == _NTP_LI_UNSYNCHRONIZED or stratum == _NTP_STRATUM_INVALID:
                # Server says its own clock is unsynchronized, or this is a Kiss-o'-Death packet
                # (see the constants' own comments) - never a genuine time source, regardless of
                # what its Transmit Timestamp happens to contain.
                await self.pr.wrn_s(
                    _NAME, "NTP reply unsynchronized or Kiss-of-Death, rejecting:", leap_indicator, stratum, wrnno=2
                )
                return None
            raw_seconds = struct.unpack("!I", msg[40:44])[0]
            ntp_time = raw_seconds - _NTP_EPOCH_DELTA + ntp_offset_s  # assume the current NTP era first
            if ntp_time < _NTP_MIN_PLAUSIBLE_UNIX_TIME:
                # Either a still-wrapped reply from the next NTP era (RFC 5905 7.3: the 32-bit
                # seconds field wraps ~2036) - reinterpret once and recheck - or outright implausible
                # data, rejected below if still out of range after the reinterpretation.
                ntp_time += _NTP_ERA_SECONDS
            if not (_NTP_MIN_PLAUSIBLE_UNIX_TIME <= ntp_time <= _NTP_MAX_PLAUSIBLE_UNIX_TIME):
                await self.pr.err_s(_NAME, "Implausible NTP time, rejecting:", ntp_time, errno=14)
                return None
            self.pr.all(_NAME, "Received NTP time:", ntp_time)
            tm = time.gmtime(ntp_time)
            RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
            return tm
        except (IndexError, OverflowError, ValueError, OSError) as e:
            # malformed/truncated reply (MicroPython's struct module raises plain ValueError, not
            # CPython's struct.error - confirmed directly against the pinned interpreter, no
            # struct.error attribute exists here at all; IndexError covers a reply too short to even
            # contain the LI/Stratum bytes read above), or an out-of-range timestamp (rp2's ~2037
            # 32-bit epoch limit - see BACKLOG.md) - treat exactly like no response at
            # all rather than letting it crash the whole task.
            await self.pr.err_s(_NAME, "Malformed NTP response, treating as no response:", e, errno=15)
            return None

    async def _handle_ntp_sync_failure(self) -> None:
        self.pr.all(_NAME, "Invalid NTP time received!")
        self.ntp_retry_timer.deinit()
        if await self.ntp_issynced():  # in case of already synced, retry if regular trigger fails
            if (
                self.ntp_retries < _NTP_SYNC_RETRIES
            ):  # if not synced at all, self.ntp_time_hours_counter() will permanently try to sync
                self.pr.evt(_NAME, "Waiting for NTP sync retry.")
                try:
                    self.ntp_retry_timer.init(
                        period=_NTP_RETRY_INTERV * 1000,
                        mode=Timer.ONE_SHOT,
                        callback=lambda b: self.ntp_sync_trigger_event.set(),
                    )
                    self.ntp_retries += 1
                except OSError as e:  # alarm-pool exhaustion (ENOMEM) - give up this retry cycle rather
                    # than crashing the task; ntp_time_hours_counter()'s regular check still recovers it.
                    await self.pr.err_s(_NAME, "Could not arm NTP retry timer:", e, errno=16)
                    self.ntp_retries = 0
            else:
                await self.pr.err_s(_NAME, "Maximum retries reached, cancelling sync!", errno=17)
                self.ntp_retries = 0

    async def _handle_ntp_sync_success(self, tm: tuple[int, ...]) -> None:
        self.ntp_retry_timer.deinit()
        self.ntp_retries = 0
        await self._set_meas_data(NTP(True, 0, self._now()))
        self.pr.one(_NAME, "RTC set to:", tm)

    async def ntp_time_hours_counter(self) -> None:  # Timer für NTP Refresh
        self.ntp_sec_count = 0
        while True:
            await self.ntp_timer_trigger_event.wait()
            ntp_interv = await self.cfgmgr.get_int_values(_VAL_NIH)
            if ntp_interv is None or len(ntp_interv) != 1:
                ntp_interv = [12]
                await self.pr.err_s(_NAME, "Missing NTP configuration, defaulting interval to 12h!", errno=18)

            if await self.ntp_issynced():
                if self.ntp_sec_count < (_NTP_ASYNC_INTERV * ntp_interv[0] * 60 * 60):
                    self.ntp_sec_count += _NTP_CHECK_INTERV
                else:
                    await self._set_synced(False)

            self.pr.all(_NAME, "Sync-age tick counter at", self.ntp_sec_count)
            if (not (await self.ntp_issynced())) or (self.ntp_sec_count >= (ntp_interv[0] * 60 * 60)):
                self.ntp_retry_timer.deinit()
                self.ntp_retries = 0
                self.ntp_sync_trigger_event.set()
                self.ntp_sec_count = 0
                self.pr.evt(_NAME, "NTP resync triggered.")
            del ntp_interv

    async def cettime(
        self,
    ) -> GMTimeStruct | None:  # Umrechnung Lokalzeit
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
            # rp2's mktime()/gmtime() raise OverflowError past its ~2037 32-bit epoch range (see
            # BACKLOG.md) - treat exactly like "not ready" instead of crashing the caller.
            await self.pr.err_s(_NAME, "Time calculation failed:", e, errno=19)
            return None
        if len(cet) == 8:
            return GMTimeStruct(*cet)
        return None

    async def time_counter(self) -> None:
        await self._set_last_sync_age(None)
        while True:
            await self.time_counter_trigger_event.wait()
            if await self.ntp_issynced():
                await self._increment_last_sync_age()
            else:
                await self._set_last_sync_age(None)
