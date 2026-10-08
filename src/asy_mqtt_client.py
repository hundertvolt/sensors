"""MQTT 3.1.1 client service (QoS 0/1, clean session, plain TCP): a supervised keeper owns the connection's writes,
deadlines and reconnects, one reader per connection owns its reads, and a publisher sends each module's measurements.
The radio stays WifiService's alone; the contract is SPECIFICATION.md Part A.11."""

import asyncio
import errno
import json
import math
import socket
import time
from collections import namedtuple

from micropython import const

from asy_base_classes import COUNTER_CAP, SensorReaderConfig, TickSeconds, utc_now
from asy_config_manager import INVALID, make_dict, name_cfg, schema_dict
from asy_dns_client import host_name_ok, resolve_ipv4
from asy_print_log import DEFAULT_LOG, LogConfig
from mqtt_codec import (
    CONNACK,
    LENGTH_INCOMPLETE,
    LENGTH_MALFORMED,
    PINGRESP,
    PUBACK,
    PUBLISH,
    SUBACK,
    SUBACK_FAILURE,
    client_id_ok,
    decode_remaining_length,
    encode_connect,
    encode_puback,
    encode_publish,
    encode_subscribe,
    prefix_ok,
    remaining_length_bytes,
    text_ok,
    topic_matches,
    topic_name_ok,
)

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import NamedTuple, Protocol

    # A ticks_ms() value: the stubs type it opaque, so it only ever reaches time.ticks_diff()/ticks_add().
    from _mpy_shed.time_mp import _TicksMs

    from asy_base_classes import JsonMapping, TaskStarter, TimerStarter
    from asy_config_manager import ConfigSchema, WriteValidity
    from asy_print_log import ErrorLog

    class _Stream(Protocol):
        # MicroPython's one asyncio Stream class, which the stubs split into StreamReader and StreamWriter.
        out_buf: bytes

        async def drain(self) -> None: ...

        async def readinto(self, buf: memoryview) -> int | None: ...

        async def wait_closed(self) -> None: ...

        def write(self, buf: bytes | bytearray | memoryview) -> None: ...

    class _Source(Protocol):
        # A module whose /measurements object the publisher sends (C.4.2's get_dict_data()).
        async def get_dict_data(self) -> Mapping[str, Mapping[str, object]]: ...

    # Build-time values the generated module passes whole: the client id default and every timing (Part N's mqtt.*).
    class MqttConfig(NamedTuple):
        client_id: str
        keepalive_s: int
        ping_interval_ms: int
        response_timeout_ms: int
        connect_timeout_ms: int
        backoff_min_ms: int
        backoff_max_ms: int
        stable_after_ms: int
        qos1_retry_ms: int
        drain_timeout_ms: int
        tick_ms: int
        link_poll_ms: int
        idle_recheck_ms: int
        dns_timeout_ms: int
        dns_tries: int

    # A wired receiver of inbound messages (owner, 2026-10-07: they may trigger behaviours or carry values; no flash
    # writes). The callback runs on the reader, synchronously, and must copy what it keeps from the two views.
    class MqttConsumer(NamedTuple):
        topic_filter: str
        callback: "Callable[[memoryview, memoryview, bool], None]"

else:
    MqttConfig = namedtuple(
        "MqttConfig",
        (
            "client_id", "keepalive_s", "ping_interval_ms", "response_timeout_ms", "connect_timeout_ms", "backoff_min_ms", "backoff_max_ms",
            "stable_after_ms", "qos1_retry_ms", "drain_timeout_ms", "tick_ms", "link_poll_ms", "idle_recheck_ms", "dns_timeout_ms", "dns_tries",
        ),
    )
    MqttConsumer = namedtuple("MqttConsumer", ("topic_filter", "callback"))

# Codes from the global catalog (buildgen/error_catalog.json): the shared ones and MQTT's band.
_ERR_CALLBACK = const(14)
_ERR_SOURCE = const(15)
_ERR_ALLOC = const(20)
_ERR_BAD_ARG = const(21)
_ERR_UNEXPECTED = const(23)
_ERR_MQTT_DNS = const(115)
_ERR_MQTT_CONNECT = const(116)
_ERR_MQTT_REFUSED = const(117)
_ERR_MQTT_PROTOCOL = const(118)
_ERR_MQTT_NO_PINGRESP = const(119)
_ERR_MQTT_LOST = const(120)
_ERR_MQTT_STALLED = const(121)
_ERR_MQTT_SUB_REFUSED = const(122)
_WRN_STORED_DEFAULT = const(10)
_WRN_CFG_READ = const(13)
_WRN_MQTT_SHORT_SESSIONS = const(82)

# Buffers, allocated once at construction (Part A.11's memory budget).
# @tunable mqtt.rx_buf_bytes = 1024
_RX_BYTES = const(1024)  # the largest inbound packet parsed; a larger one is read and discarded
# @tunable mqtt.tx_buf_bytes = 640
_TX_BYTES = const(640)  # one outbound packet: the largest CONNECT, or a PUBLISH of a full slot
# @tunable mqtt.out_slots = 8
_OUT_SLOTS = const(8)
# @tunable mqtt.out_payload_max = 384
_OUT_PAYLOAD = const(384)
# @tunable mqtt.ack_slots = 32
_ACK_SLOTS = const(32)  # inbound QoS 1 ids awaiting their PUBACK; above the broker's in-flight window (20)
# @tunable mqtt.last_topic_bytes = 64
_LAST_TOPIC_BYTES = const(64)
# @tunable mqtt.max_out_backlog = 2048
_MAX_OUT_BACKLOG = const(2048)  # bytes the socket has not taken yet; past it the broker counts as stalled
# @tunable mqtt.qos1_max_tries = 3
_QOS1_MAX_TRIES = const(3)
# @tunable mqtt.short_session_warn = 3
_SHORT_SESSION_WARN = const(3)
# @tunable mqtt.pub_step_ms = 1000
_PUB_STEP_MS = const(1000)  # the publisher's check for a due round: how late the first one follows a CONNACK
# @tunable mqtt.unconfirmed_max_bytes = 2000
_UNCONFIRMED_MAX = const(2000)  # bytes written but not yet proven received: the connection's lwIP MEM_SIZE share
_MAX_TEXT_BYTES = const(64)  # MQTTUser/MQTTPW
_ID_BYTES = const(2)  # a packet id, and a string's length prefix (MQTT 3.1.1 section 1.5.3)
_SUBACK_MIN = const(3)  # a packet id and at least one return code
_CONNACK_LEN = const(4)
_TEXT_FIELDS = const(5)  # host, user, password, client id, prefix
_INT_FIELDS = const(2)  # port, publish interval
_PW_MASK = "********"

_PINGREQ_PKT = b"\xc0\x00"
_DISCONNECT_PKT = b"\xe0\x00"
_ONLINE = b"online"  # <base>/status, retained: published after each CONNACK
_OFFLINE = b"offline"  # the will, and published before a reconfiguring DISCONNECT

# Slot states of the outbound ring.
_SLOT_FREE = const(0)
_SLOT_QUEUED = const(1)
_SLOT_INFLIGHT = const(2)

# The keeper's state, shown as MQTTState.
_ST_DISABLED = const(0)
_ST_WAITING = const(1)
_ST_CONNECTING = const(2)
_ST_CONNECTED = const(3)
_ST_BACKOFF = const(4)
_ST_NO_MEMORY = const(5)
_STATES = ("disabled", "waiting", "connecting", "connected", "backoff", "no memory")

# Why a connection ended (or never started), shown as MQTTLastReason; ints, so a reason allocates nothing.
_R_NONE = const(0)
_R_LINK = const(1)
_R_RECONFIGURE = const(2)
_R_PING = const(3)
_R_EOF = const(4)
_R_IO = const(5)
_R_PROTOCOL = const(6)
_R_STALLED = const(7)
_R_CONNECT = const(8)
_R_UNEXPECTED = const(9)
_REASONS = ("none", "link down", "reconfigured", "no pingresp", "closed by broker", "socket error", "protocol error", "stalled", "connect failed", "unexpected")

# Counters, saturating at COUNTER_CAP; the first eight are published in MQTTState's group.
_C_CONNECTS = const(0)
_C_TEARDOWNS = const(1)
_C_TX = const(2)
_C_TX_DROP = const(3)
_C_RX = const(4)
_C_RX_DROP = const(5)
_C_PING_TIMEOUTS = const(6)
_C_SHORT = const(7)
_C_CONSUMER_ERR = const(8)
_COUNTERS = const(9)

_NAME = const("MQTT")
MQTT = namedtuple("MQTT", ("Connected", "TS"))
_FIELDS = const(("Connected", "TS"))  # kept in sync with MQTT's own fields above

# Schema (persist-only; read at each connect). Every string is checked for its MQTT shape at PUT and at use.
_VAL_MQTT_ENABLE = const((("MQTTEnable", "bool", False, None, None, None),))
_VAL_MQTT_HOST = const((("MQTTHost", "str", "", 1, 253, ""),))  # special "": no broker, the client off
_VAL_MQTT_PORT = const((("MQTTPort", "int", 1883, 1, 65535, None),))
_VAL_MQTT_USER = const((("MQTTUser", "str", "", 0, 64, None),))
_VAL_MQTT_PW = const((("MQTTPW", "str", "", 0, 64, None),))
_VAL_MQTT_CLIENT_ID = const((("MQTTClientId", "str", "SensorNode", 1, 23, None),))
_VAL_MQTT_PREFIX = const((("MQTTPrefix", "str", "sensors", 1, 64, None),))
_VAL_MQTT_PUB_INTERVAL = const((("MQTTPubInterval", "int", 60, 10, 3600, None),))

# @web-group section=networking submitGroup=mqtt label="MQTT Broker" submit=true submitLabel="Apply & Reconnect"
# @web MQTTEnable section=networking submitGroup=mqtt label="MQTT Client" onLabel="On" offLabel="Off"
# @web MQTTHost section=networking submitGroup=mqtt label="Broker Address" description="IPv4 address, host name or .local name; plain TCP, no TLS." bytes=true shape=hostName special:""="No broker (client off)"
# @web MQTTPort section=networking submitGroup=mqtt label="Broker Port"
# @web MQTTUser section=networking submitGroup=mqtt label="User Name" description="Leave empty for an anonymous broker." bytes=true
# @web MQTTPW section=networking submitGroup=mqtt label="Password" mask=true bytes=true
# @web MQTTClientId section=networking submitGroup=mqtt label="Client ID" description="Also the device's topic level." bytes=true shape=hostLabel
# @web MQTTPrefix section=networking submitGroup=mqtt label="Topic Prefix" description="Topics are <prefix>/<client id>/status, /measurements/<module> and /cmd/#." bytes=true
# @web MQTTPubInterval section=networking submitGroup=mqtt label="Publish Interval" unit="s"

# This service's one optional live cross-instance dependency (Part C.14): its FRAM error-log target.
# @wiring fram_target FRAMManager log optional kwarg


def _json_ready(value: object) -> object:
    # A /measurements value as JSON can carry it: non-finite floats become None, as the REST stream writes them.
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    return value


class MQTTClient(SensorReaderConfig):
    # Per-connection state, set by _reset_connection_state() before every connect.
    _rx_len: int
    _discard: int
    _reader_end: int
    _detail: int
    _ping_out: bool
    _ping_sent: "_TicksMs"
    _last_ping: "_TicksMs"
    _last_link: "_TicksMs"
    _connected_at: "_TicksMs"
    _stable: bool
    _sub_refused: bool
    _ack_head: int
    _ack_count: int
    _unconfirmed: int
    _ping_mark: int
    _ping_early: bool

    def __init__(
        self,
        wifi_mode_lock: asyncio.Lock,
        network_available_locked: "Callable[[], bool]",
        get_dns_server: "Callable[[], str | None]",
        config: MqttConfig,
        sources: "tuple[_Source, ...]" = (),
        consumers: "tuple[MqttConsumer, ...]" = (),
        cfg_path: str = "",
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        name, kind, _default, low, high, special = _VAL_MQTT_CLIENT_ID[0]
        default_id = config.client_id if client_id_ok(config.client_id) else _default
        self._val_client_id = ((name, kind, default_id, low, high, special),)  # the device's hostname as the default
        super().__init__(
            MQTT(Connected=False, TS=None),
            _NAME,
            _VAL_MQTT_ENABLE + _VAL_MQTT_HOST + _VAL_MQTT_PORT + _VAL_MQTT_USER + _VAL_MQTT_PW + self._val_client_id + _VAL_MQTT_PREFIX + _VAL_MQTT_PUB_INTERVAL,
            max_module_error=0,  # no failure streak: a broker outage is routine, never a restart (Part C.7.2)
            cfg_path=cfg_path,
            log=log,
        )
        self.wifi_mode_lock = wifi_mode_lock  # shared with WifiService; held only around the availability check
        self._network_available_locked = network_available_locked
        self._get_dns_server = get_dns_server
        self._cfg = config
        self._sources = sources
        self._consumers = consumers
        self._alloc_error: Exception | None = None
        try:
            self._rx = bytearray(_RX_BYTES)
            self._tx = bytearray(_TX_BYTES)
            self._ring = bytearray(_OUT_SLOTS * _OUT_PAYLOAD)
            self._acks = bytearray(2 * _ACK_SLOTS)
            self._last_topic = bytearray(_LAST_TOPIC_BYTES)
            self._rxmv = memoryview(self._rx)
            self._txmv = memoryview(self._tx)
            self._ringmv = memoryview(self._ring)
            self._slot_len = [0] * _OUT_SLOTS
            self._slot_topic: list[bytes | None] = [None] * _OUT_SLOTS
            self._slot_qos = bytearray(_OUT_SLOTS)
            self._slot_retain = bytearray(_OUT_SLOTS)
            self._slot_state = bytearray(_OUT_SLOTS)
            self._slot_tries = bytearray(_OUT_SLOTS)
            self._slot_seq = [0] * _OUT_SLOTS
            self._slot_pid = [0] * _OUT_SLOTS
            self._slot_sent = [time.ticks_ms()] * _OUT_SLOTS
            self._counts = [0] * _COUNTERS
        except MemoryError as e:  # boot-time only; the client stays off and setup() persists why
            self._alloc_error = e
        self._wake = asyncio.Event()  # set by reconnect(): ends an idle or backoff wait at once
        self._pub_interval_ms = _VAL_MQTT_PUB_INTERVAL[0][2] * 1000  # read with the other settings at each connect
        self._pub_due = False  # set at each CONNACK: the first round follows it instead of a whole interval
        self._uptime = TickSeconds()
        self._meas_topics: dict[str, bytes] = {}
        self._consumer_filters = tuple(c.topic_filter.encode() for c in consumers)
        self._consumer_pairs = tuple((c.topic_filter.encode(), c.callback) for c in consumers)  # zip() has no strict= on MicroPython
        self._consumer_errors_logged = 0
        self._last_topic_len = 0
        self._seq = 0
        self._pid = 0
        self._reset_connection_state()
        self._state = _ST_NO_MEMORY if self._alloc_error is not None else _ST_DISABLED
        self._last_reason = _R_NONE
        self._broker_ip: str | None = None
        self._backoff_ms = config.backoff_min_ms
        self._short_streak = 0
        self._reconfigure = False
        self._cfg_warned = False
        self._reader: asyncio.Task[None] | None = None
        self._stream: _Stream | None = None
        self._host = ""
        self._port = 0
        self._user = b""
        self._password = b""
        self._client_id = b""
        self._base = b""
        self._push_callbacks.clear()  # every field is persist-only: the next connect reads it

    async def _set_mgr_cfg(self, data: "JsonMapping", cfg_vals: "ConfigSchema") -> "tuple[bool, WriteValidity]":
        # Refuses a string outside its MQTT shape before it is stored (C.7.4's precedent); the rest goes through as usual.
        fields = schema_dict(cfg_vals)
        refused = [k for k, v in data.items() if k in fields and isinstance(v, str) and not self._shape_ok(k, v)]
        for key in refused:
            await self.pr.err_s("Refusing", key, "- outside the MQTT client's accepted form", errno=_ERR_BAD_ARG)
        ok, results = await super()._set_mgr_cfg({k: v for k, v in data.items() if k not in refused}, cfg_vals)
        for key in refused:
            results[key] = INVALID
        return ok, results

    def _set_state(self, state: int) -> None:
        self._state = state

    async def _backoff_wait(self) -> None:
        # The backoff step, ended early by reconnect(); the step doubles to its cap, and only a stable session resets it.
        self._set_state(_ST_BACKOFF)
        try:
            await asyncio.wait_for_ms(self._wake.wait(), self._backoff_ms)
        except asyncio.TimeoutError:
            pass
        self._backoff_ms = min(self._backoff_ms * 2, self._cfg.backoff_max_ms)

    def _bump(self, i: int) -> None:
        count = self._counts[i]
        if count < COUNTER_CAP:
            self._counts[i] = count + 1

    async def _close(self) -> None:
        # The teardown every connection ends with: the reader cancelled, then the socket closed. Never awaited: an
        # except CancelledError there would also swallow the keeper's own cancellation (Part A.11).
        reader, self._reader = self._reader, None
        if reader is not None:
            reader.cancel()  # out of the poll set at once; its end raises nothing anyone must retrieve
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                await stream.wait_closed()  # Stream.close() is a no-op; wait_closed() closes the socket
            except OSError:
                pass

    def _compact(self, used: int) -> None:
        left = self._rx_len - used
        if left > 0:
            self._rx[0:left] = self._rxmv[used : self._rx_len]
        self._rx_len = left

    async def _connect(self) -> int:
        # Resolve, connect and CONNECT/CONNACK under their own timeouts; _R_NONE once the session is up.
        dns_server = await self._safe_dns_server()  # read before any lock, as NTP does
        ip = await resolve_ipv4(self._host, () if dns_server is None else (dns_server,), timeout_ms=self._cfg.dns_timeout_ms, tries=self._cfg.dns_tries, pr=self.pr)
        if ip is None:
            await self.pr.err_s("Broker name did not resolve:", self._host, errno=_ERR_MQTT_DNS)
            return _R_CONNECT
        self._broker_ip = ip
        try:
            addr = socket.getaddrinfo(ip, self._port)[0][-1]  # an IPv4 literal: no DNS query (Part F.2)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except (MemoryError, OSError) as e:
            await self.pr.err_s("Could not open a socket:", e, errno=_ERR_MQTT_CONNECT)
            return _R_CONNECT
        stream: _Stream = asyncio.StreamReader(sock)  # type: ignore[assignment]  # MicroPython's one Stream class
        self._stream = stream  # owned from here: _close() ends it on every path
        sock.setblocking(False)
        n = encode_connect(self._txmv, self._client_id, self._cfg.keepalive_s, self._base + b"/status", _OFFLINE, self._user, self._password)
        if n < 0:  # unreachable within the schema's bounds, which _TX_BYTES is sized for
            await self.pr.err_s("CONNECT does not fit the transmit buffer", errno=_ERR_MQTT_CONNECT)
            return _R_CONNECT
        try:
            try:
                sock.connect(addr)
            except OSError as e:
                if e.errno != errno.EINPROGRESS:
                    raise
            stream.write(self._txmv[:n])  # held in out_buf until the handshake completes
            await asyncio.wait_for_ms(stream.drain(), self._cfg.connect_timeout_ms)
            reason = await self._read_connack(stream)
        except (OSError, asyncio.TimeoutError) as e:
            await self.pr.err_s("Broker connect failed:", ip, e, errno=_ERR_MQTT_CONNECT)
            return _R_CONNECT
        return reason

    async def _connection_loop(self) -> None:
        # The keeper (Part A.11): never ends on a remote fault; a restarted task first closes what the last one left.
        await self._close()
        while True:
            self._wake.clear()
            self._reconfigure = False
            if self._alloc_error is not None or not await self._read_params():
                self._set_state(_ST_NO_MEMORY if self._alloc_error is not None else _ST_DISABLED)
                try:
                    await asyncio.wait_for_ms(self._wake.wait(), self._cfg.idle_recheck_ms)
                except asyncio.TimeoutError:
                    pass
                continue
            if not await self._safe_link_up():
                self._set_state(_ST_WAITING)
                await asyncio.sleep_ms(self._cfg.link_poll_ms)
                continue
            started = time.ticks_ms()
            reason = await self._session()
            await self._log_end(reason, time.ticks_diff(time.ticks_ms(), started))
            if reason == _R_RECONFIGURE:
                self._backoff_ms = self._cfg.backoff_min_ms
                self._cfg_warned = False
                continue
            if reason != _R_LINK:
                await self._backoff_wait()

    def _flush_acks(self, stream: "_Stream") -> None:
        # The PUBACKs the reader queued, sent by the keeper alone: one writer, so no write lands in a running drain.
        while self._ack_count > 0:
            i = self._ack_head * 2
            n = encode_puback(self._txmv, (self._acks[i] << 8) | self._acks[i + 1])
            self._write(stream, self._txmv[:n])  # tiny and never held: the broker's inbound flow depends on them
            self._ack_head = (self._ack_head + 1) % _ACK_SLOTS
            self._ack_count -= 1

    def _flush_outbound(self, stream: "_Stream", now: "_TicksMs") -> None:
        # Queued messages oldest first, then QoS 1 retransmissions; a give-up is counted, never a teardown.
        for _ in range(_OUT_SLOTS):
            i = self._oldest_queued()
            if i < 0 or not self._send_slot(stream, i, dup=False):
                break  # nothing queued, or no room: order is kept, the rest waits for the ping's answer
            self._bump(_C_TX)
            if self._slot_qos[i]:
                self._slot_state[i] = _SLOT_INFLIGHT
                self._slot_sent[i] = now
            else:
                self._free(i)
        for i in range(_OUT_SLOTS):
            if self._slot_state[i] == _SLOT_INFLIGHT and time.ticks_diff(now, self._slot_sent[i]) >= self._cfg.qos1_retry_ms:
                if self._slot_tries[i] >= _QOS1_MAX_TRIES:
                    self._free(i)
                    self._bump(_C_TX_DROP)
                elif self._send_slot(stream, i, dup=True):
                    self._slot_sent[i] = now

    def _free(self, i: int) -> None:
        self._slot_state[i] = _SLOT_FREE
        self._slot_topic[i] = None

    def _free_slot(self) -> int:
        # A free slot, else the oldest queued QoS 0 one (best effort gives way), else -1.
        oldest = -1
        for i in range(_OUT_SLOTS):
            state = self._slot_state[i]
            if state == _SLOT_FREE:
                return i
            if state == _SLOT_QUEUED and not self._slot_qos[i] and (oldest < 0 or self._slot_seq[i] < self._slot_seq[oldest]):
                oldest = i
        if oldest >= 0:
            self._bump(_C_TX_DROP)
        return oldest

    def _handle(self, hdr: int, total: int) -> int:
        # One complete packet at rx[0:total]; a reason other than _R_NONE ends the connection.
        rx = self._rx
        kind = rx[0] & 0xF0
        if kind == PUBLISH:
            return self._on_publish(hdr, total)
        if kind == PUBACK and total - hdr == _ID_BYTES:
            pid = (rx[hdr] << 8) | rx[hdr + 1]
            for i in range(_OUT_SLOTS):
                if self._slot_state[i] == _SLOT_INFLIGHT and self._slot_pid[i] == pid:
                    self._free(i)
                    break
            return _R_NONE
        if kind == PINGRESP and total == hdr:
            # TCP delivers in order, so everything written up to the PINGREQ has arrived and lwIP has freed it.
            self._ping_out = False
            self._unconfirmed = max(0, self._unconfirmed - self._ping_mark)
            self._ping_mark = 0
            return _R_NONE
        if kind == SUBACK and total - hdr >= _SUBACK_MIN:
            for j in range(hdr + _ID_BYTES, total):
                if rx[j] == SUBACK_FAILURE:
                    self._sub_refused = True
            return _R_NONE
        self._detail = rx[0]
        return _R_PROTOCOL

    async def _log_end(self, reason: int, lasted_ms: int) -> None:
        # One persisted entry per failed attempt or lost connection; a link loss and a reconfigure log nothing.
        if reason in (_R_EOF, _R_IO) and lasted_ms < self._cfg.stable_after_ms:
            self._bump(_C_SHORT)
            if self._short_streak < _SHORT_SESSION_WARN:
                self._short_streak += 1
                if self._short_streak == _SHORT_SESSION_WARN:
                    # This end is the warning, not also an error: one occurrence is one kind (C.7.1).
                    await self.pr.wrn_s("Sessions keep ending right after they start - another client with this client id?", wrnno=_WRN_MQTT_SHORT_SESSIONS)
                    return
        if reason == _R_PING:
            await self.pr.err_s("No PINGRESP from", self._broker_ip, errno=_ERR_MQTT_NO_PINGRESP)
        elif reason == _R_EOF:
            await self.pr.err_s("Broker closed the connection", errno=_ERR_MQTT_LOST)
        elif reason == _R_IO:
            await self.pr.err_s("Connection lost, errno", self._detail, errno=_ERR_MQTT_LOST)
        elif reason == _R_PROTOCOL:
            await self.pr.err_s("Protocol error, packet", self._detail, errno=_ERR_MQTT_PROTOCOL)
        elif reason == _R_STALLED:
            await self.pr.err_s("Broker stopped reading", errno=_ERR_MQTT_STALLED)
        elif reason == _R_UNEXPECTED:
            await self.pr.err_s("Reader ended unexpectedly", errno=_ERR_UNEXPECTED)
        elif reason == _R_RECONFIGURE:
            self.pr.evt("Reconnecting with new settings.")

    async def _mask_pw(self) -> dict[str, int | float | str | bool | None]:
        return {name_cfg(_VAL_MQTT_PW): _PW_MASK}

    def _new_connection(self) -> None:
        # Per-connection state, reset before each connect; the outbound ring survives (a clean session re-sends).
        self._reset_connection_state()
        for i in range(_OUT_SLOTS):
            if self._slot_state[i] == _SLOT_INFLIGHT:
                self._slot_state[i] = _SLOT_QUEUED  # the broker forgot its id: sent again as new
                self._slot_tries[i] = 0
            elif self._slot_state[i] == _SLOT_QUEUED and not self._slot_qos[i]:
                self._free(i)  # QoS 0 is never carried across an outage

    def _next_pid(self) -> int:
        self._pid = self._pid % 65535 + 1
        return self._pid

    def _oldest_queued(self) -> int:
        found = -1
        for i in range(_OUT_SLOTS):
            if self._slot_state[i] == _SLOT_QUEUED and (found < 0 or self._slot_seq[i] < self._slot_seq[found]):
                found = i
        return found

    def _on_publish(self, hdr: int, total: int) -> int:
        rx = self._rx
        qos = (rx[0] >> 1) & 3
        if total - hdr < _ID_BYTES:
            return self._protocol(rx[0])
        tlen = (rx[hdr] << 8) | rx[hdr + 1]
        t0 = hdr + _ID_BYTES
        p0 = t0 + tlen + (_ID_BYTES if qos else 0)
        if qos > 1 or p0 > total:
            return self._protocol(rx[0])
        if qos:
            if self._ack_count < _ACK_SLOTS:
                j = ((self._ack_head + self._ack_count) % _ACK_SLOTS) * 2
                self._acks[j] = rx[p0 - 2]
                self._acks[j + 1] = rx[p0 - 1]
                self._ack_count += 1
            else:
                self._bump(_C_RX_DROP)  # unacknowledged: the broker keeps it in flight
        self._bump(_C_RX)
        topic = self._rxmv[t0 : t0 + tlen]
        n = min(tlen, _LAST_TOPIC_BYTES)
        self._last_topic[0:n] = topic[0:n]
        self._last_topic_len = n
        payload = self._rxmv[p0:total]
        retained = bool(rx[0] & 1)
        for flt, callback in self._consumer_pairs:
            if topic_matches(flt, topic):
                try:
                    callback(topic, payload, retained)
                except Exception:  # a consumer's fault never ends the reader; the keeper logs it
                    self._bump(_C_CONSUMER_ERR)
        return _R_NONE

    def _protocol(self, first: int) -> int:
        self._detail = first
        return _R_PROTOCOL

    async def _publish_loop(self) -> None:
        # A round right after each CONNACK, then every MQTTPubInterval; the interval is read at connect, so a changed
        # setting, which reconnects, applies at once.
        last = time.ticks_ms()
        while True:
            await asyncio.sleep_ms(_PUB_STEP_MS)
            if self._state != _ST_CONNECTED:
                continue
            if self._pub_due or time.ticks_diff(time.ticks_ms(), last) >= self._pub_interval_ms:
                self._pub_due = False
                last = time.ticks_ms()
                await self._publish_measurements()

    async def _publish_measurements(self) -> None:
        # One QoS 0 message per module, its /measurements object as JSON (owner, 2026-10-07: 'Also measurements JSON').
        for source in self._sources:
            try:
                data = await source.get_dict_data()
            except Exception as e:  # a producer's get_dict_data() never raises by contract; guarded all the same
                await self.pr.err_s("Measurement source failed:", e, errno=_ERR_SOURCE)
                continue
            for name, fields in data.items():
                topic = self._meas_topics.get(name)
                if topic is None:
                    topic = self._base + b"/measurements/" + name.encode()
                    self._meas_topics[name] = topic
                self.publish(topic, json.dumps(_json_ready(fields)))

    def _queue(self, topic: bytes, payload: bytes | bytearray | memoryview, qos: int, *, retain: bool) -> bool:
        i = self._free_slot()
        if i < 0:
            self._bump(_C_TX_DROP)
            return False
        n = len(payload)
        start = i * _OUT_PAYLOAD
        self._ringmv[start : start + n] = payload
        self._slot_len[i] = n
        self._slot_topic[i] = topic
        self._slot_qos[i] = qos
        self._slot_retain[i] = 1 if retain else 0
        self._slot_tries[i] = 0
        self._seq = self._seq + 1 if self._seq < COUNTER_CAP else 0
        self._slot_seq[i] = self._seq
        self._slot_state[i] = _SLOT_QUEUED
        return True

    async def _read_connack(self, stream: "_Stream") -> int:
        # CONNACK (section 3.2) within the response timeout; anything after its four bytes stays for the reader.
        deadline = time.ticks_add(time.ticks_ms(), self._cfg.response_timeout_ms)
        while self._rx_len < _CONNACK_LEN:
            left = time.ticks_diff(deadline, time.ticks_ms())
            if left <= 0:
                raise asyncio.TimeoutError
            n = await asyncio.wait_for_ms(stream.readinto(self._rxmv[self._rx_len :]), left)
            if not n:
                raise OSError(errno.ECONNRESET)
            self._rx_len += n
        rx = self._rx
        if rx[0] != CONNACK or rx[1] != _ID_BYTES or rx[2] & 0xFE:  # bit 0 is Session Present, never an error (mqtt_as A4)
            await self.pr.err_s("Malformed CONNACK:", rx[0], rx[1], rx[2], errno=_ERR_MQTT_PROTOCOL)
            return _R_CONNECT
        if rx[3]:
            await self.pr.err_s("Broker refused the connection, return code", rx[3], errno=_ERR_MQTT_REFUSED)
            return _R_CONNECT
        self._compact(_CONNACK_LEN)
        return _R_NONE

    async def _read_params(self) -> bool:
        # The configuration for the next connect; False when off, or when a read or a stored shape fails.
        enable = await self.cfgmgr.get_bool_values(_VAL_MQTT_ENABLE)
        texts = await self.cfgmgr.get_str_values(_VAL_MQTT_HOST + _VAL_MQTT_USER + _VAL_MQTT_PW + self._val_client_id + _VAL_MQTT_PREFIX)
        ints = await self.cfgmgr.get_int_values(_VAL_MQTT_PORT + _VAL_MQTT_PUB_INTERVAL)
        if enable is None or texts is None or ints is None or len(texts) != _TEXT_FIELDS or len(ints) != _INT_FIELDS:
            if not self._cfg_warned:
                self._cfg_warned = True
                await self.pr.wrn_s("Error reading own configuration!", wrnno=_WRN_CFG_READ)
            return False
        host, user, password, client_id, prefix = texts
        if not enable[0] or not host:
            return False
        if not (host_name_ok(host) and client_id_ok(client_id) and prefix_ok(prefix) and text_ok(user.encode(), _MAX_TEXT_BYTES) and text_ok(password.encode(), _MAX_TEXT_BYTES)):
            if not self._cfg_warned:
                self._cfg_warned = True
                await self.pr.wrn_s("Stored MQTT settings out of shape, client off:", host, client_id, prefix, wrnno=_WRN_STORED_DEFAULT)
            return False
        base = (prefix + "/" + client_id).encode()
        if base != self._base:
            self._meas_topics.clear()
        self._host, self._port, self._base = host, ints[0], base
        self._pub_interval_ms = ints[1] * 1000
        self._user, self._password, self._client_id = user.encode(), password.encode(), client_id.encode()
        return True

    async def _reader_loop(self, stream: "_Stream") -> None:
        # The connection's only reader; it never logs and never raises, and records why it ended for the keeper.
        try:
            while True:
                n = await stream.readinto(self._rxmv[self._rx_len :])
                if n is None:
                    continue
                if n == 0:
                    self._reader_end = _R_EOF
                    return
                if self._discard:
                    if n <= self._discard:
                        self._discard -= n
                        continue
                    n -= self._discard
                    self._rx[0:n] = self._rxmv[self._discard : self._discard + n]
                    self._discard = 0
                self._rx_len += n
                reason = self._take_packets()
                if reason != _R_NONE:
                    self._reader_end = reason
                    return
        except OSError as e:
            self._detail = e.errno if isinstance(e.errno, int) else 0
            self._reader_end = _R_IO
        except Exception:  # never-raise boundary: the keeper persists UNEXPECTED
            self._reader_end = _R_UNEXPECTED

    def _reset_connection_state(self) -> None:
        self._rx_len = 0
        self._discard = 0
        self._reader_end = _R_NONE
        self._detail = 0
        self._ping_out = False
        now = time.ticks_ms()
        self._ping_sent = now
        self._last_ping = now
        self._last_link = now
        self._connected_at = now
        self._stable = False
        self._sub_refused = False
        self._ack_head = 0
        self._ack_count = 0
        self._unconfirmed = 0  # bytes written since the CONNACK that no PINGRESP has confirmed yet
        self._ping_mark = 0  # _unconfirmed right after the outstanding PINGREQ: what its PINGRESP confirms
        self._ping_early = False  # a write is waiting for room: the next tick pings without waiting its interval

    async def _safe_dns_server(self) -> str | None:
        try:
            return self._get_dns_server()
        except Exception as e:  # caller-supplied callback - could legitimately misbehave
            await self.pr.err_s("get_dns_server() callback failed:", e, errno=_ERR_CALLBACK)
            return None

    async def _safe_link_up(self) -> bool:
        # network_available_locked() under wifi_mode_lock, released before any broker I/O (Part A.11).
        failed: Exception | None = None
        async with self.wifi_mode_lock:
            try:
                available = self._network_available_locked()
            except Exception as e:  # caller-supplied callback - could legitimately misbehave
                failed = e
                available = False
        if failed is not None:
            await self.pr.err_s("network_available_locked() callback failed:", failed, errno=_ERR_CALLBACK)
        return available

    def _send_slot(self, stream: "_Stream", i: int, *, dup: bool) -> bool:
        # False when the PUBLISH would take the unconfirmed bytes past their cap; it waits for the next ping's answer.
        if not dup and self._slot_qos[i]:
            self._pid = self._pid % 65535 + 1
            self._slot_pid[i] = self._pid
        start = i * _OUT_PAYLOAD
        topic = self._slot_topic[i] or b""
        payload = self._ringmv[start : start + self._slot_len[i]]
        n = encode_publish(self._txmv, topic, payload, self._slot_qos[i], self._slot_pid[i], retain=bool(self._slot_retain[i]), dup=dup)
        if n > 0:
            if self._unconfirmed and self._unconfirmed + n > _UNCONFIRMED_MAX:
                self._ping_early = not self._ping_out
                return False
            self._write(stream, self._txmv[:n])
        self._slot_tries[i] += 1
        return True

    async def _serve(self, stream: "_Stream") -> int:
        # The keeper's tick while connected: every write, the ping and link deadlines, and stability.
        cfg = self._cfg
        subscribe = encode_subscribe(self._txmv, self._next_pid(), self._subscriptions())
        if subscribe > 0:
            self._write(stream, self._txmv[:subscribe])
        self._queue(self._base + b"/status", _ONLINE, 1, retain=True)
        while True:
            await asyncio.sleep_ms(cfg.tick_ms)  # sleep_ms() allocates nothing
            if self._reconfigure:
                return _R_RECONFIGURE
            if self._reader_end != _R_NONE:
                return self._reader_end
            now = time.ticks_ms()
            if time.ticks_diff(now, self._last_link) >= cfg.link_poll_ms:
                self._last_link = now
                if not self.wifi_mode_lock.locked() and not await self._safe_link_up():
                    return _R_LINK  # WIFI logs its own loss; a busy lock is no news, the ping covers it
            if self._ping_out:
                if time.ticks_diff(now, self._ping_sent) >= cfg.response_timeout_ms:
                    self._bump(_C_PING_TIMEOUTS)
                    return _R_PING
            elif self._ping_early or time.ticks_diff(now, self._last_ping) >= cfg.ping_interval_ms:
                self._write(stream, _PINGREQ_PKT)
                self._ping_mark = self._unconfirmed
                self._ping_early = False
                self._ping_out = True
                self._ping_sent = now
                self._last_ping = now
            self._flush_acks(stream)
            self._flush_outbound(stream, now)
            if self._sub_refused:
                self._sub_refused = False
                await self.pr.err_s("Broker refused a subscription", errno=_ERR_MQTT_SUB_REFUSED)
            if self._counts[_C_CONSUMER_ERR] != self._consumer_errors_logged:
                self._consumer_errors_logged = self._counts[_C_CONSUMER_ERR]
                await self.pr.err_s("An MQTT consumer raised", errno=_ERR_CALLBACK)
            backlog = len(stream.out_buf)
            if backlog > _MAX_OUT_BACKLOG:
                return _R_STALLED
            if backlog:
                try:
                    await asyncio.wait_for_ms(stream.drain(), cfg.drain_timeout_ms)
                except asyncio.TimeoutError:
                    return _R_STALLED  # the timeout cancelled a socket waiter: this connection ends now (Part A.11)
            if not self._stable and time.ticks_diff(time.ticks_ms(), self._connected_at) >= cfg.stable_after_ms:
                self._stable = True
                self._backoff_ms = cfg.backoff_min_ms
                self._short_streak = 0

    async def _session(self) -> int:
        # One connection from connect to teardown; the reason it ended.
        self._new_connection()
        self._set_state(_ST_CONNECTING)
        reason = _R_UNEXPECTED
        try:
            reason = await self._connect()
            stream = self._stream
            if reason != _R_NONE or stream is None:
                self._last_reason = reason
                return reason
            self._connected_at = time.ticks_ms()
            self._last_ping = self._connected_at
            self._last_link = self._connected_at
            self._uptime.restart(0)
            self._bump(_C_CONNECTS)
            self._set_state(_ST_CONNECTED)
            self._pub_due = True
            await self._set_meas_data(MQTT(Connected=True, TS=utc_now()))
            self.pr.evt("Connected to", self._broker_ip, "port", self._port)
            self._reader = asyncio.get_event_loop().create_task(self._reader_loop(stream))
            try:
                reason = await self._serve(stream)
            except OSError as e:
                self._detail = e.errno if isinstance(e.errno, int) else 0
                reason = _R_IO
            if reason == _R_RECONFIGURE:
                # A DISCONNECT makes the broker drop the will, so the retained status is set to offline first.
                n = encode_publish(self._txmv, self._base + b"/status", _OFFLINE, 0, 0, retain=True, dup=False)
                try:
                    stream.write(self._txmv[:n])
                    stream.write(_DISCONNECT_PKT)
                except OSError:
                    pass
            self._last_reason = reason
            return reason
        finally:
            if self._state == _ST_CONNECTED:
                self._bump(_C_TEARDOWNS)
                self._set_state(_ST_WAITING)
                await self._set_meas_data(MQTT(Connected=False, TS=utc_now()))
            await self._close()

    def _shape_ok(self, key: str, value: str) -> bool:
        # MQTTHost takes NTPHost's hostName shape, its special "" (the client off) aside (Part A.11).
        if key == name_cfg(_VAL_MQTT_HOST):
            return value == "" or host_name_ok(value)
        if key == name_cfg(self._val_client_id):
            return client_id_ok(value)
        if key == name_cfg(_VAL_MQTT_PREFIX):
            return prefix_ok(value)
        if key in (name_cfg(_VAL_MQTT_USER), name_cfg(_VAL_MQTT_PW)):
            return text_ok(value.encode(), _MAX_TEXT_BYTES)
        return True

    def _subscriptions(self) -> tuple[bytes, ...]:
        return (self._base + b"/cmd/#",) + self._consumer_filters

    def _take_packets(self) -> int:
        # Every complete packet in the receive buffer, in order; an oversize one switches to discarding its bytes.
        while self._rx_len >= _ID_BYTES:  # a first byte and at least one length byte
            rem = decode_remaining_length(self._rx, 1, self._rx_len)
            if rem == LENGTH_INCOMPLETE:
                return _R_NONE
            if rem == LENGTH_MALFORMED:
                return self._protocol(self._rx[0])
            total = 1 + remaining_length_bytes(self._rx, 1, self._rx_len) + rem
            if total > _RX_BYTES:
                self._bump(_C_RX_DROP)
                self._discard = total - self._rx_len
                self._rx_len = 0
                return _R_NONE
            if self._rx_len < total:
                return _R_NONE
            reason = self._handle(total - rem, total)
            if reason != _R_NONE:
                return reason
            self._compact(total)
        return _R_NONE

    def _write(self, stream: "_Stream", data: bytes | memoryview) -> None:
        # Every keeper write but the CONNECT and the teardown's, counted until a PINGRESP confirms it (_UNCONFIRMED_MAX).
        stream.write(data)
        self._unconfirmed += len(data)

    def get_task_starters(self) -> "list[TaskStarter]":
        return [self.start_asy_connection, self.start_asy_publish]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return []  # no machine.Timer anywhere in this file (SPECIFICATION.md C.9 shape)

    def start_asy_connection(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._connection_loop())

    def start_asy_publish(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._publish_loop())

    async def get_data(self) -> MQTT:
        # Narrows to this Reader's concrete MQTT - see SPECIFICATION.md C.4.2's get_data() convention.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(self.name, self._cfg_schema, callback=self._mask_pw)

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data, _FIELDS, name=self.name)

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    def get_link_status(self) -> dict[str, int | str | bool | None]:
        # GET /status's MQTT fields; built with no await, so one snapshot (Part A.8's copy safety).
        connected = self._state == _ST_CONNECTED
        try:
            last_topic: str | None = bytes(self._last_topic[0 : self._last_topic_len]).decode() if self._last_topic_len else None
        except UnicodeError:  # a multi-byte character cut at the buffer's end
            last_topic = None
        counts = self._counts if self._alloc_error is None else [0] * _COUNTERS
        return {
            "MQTTState": _STATES[self._state],
            "MQTTConnected": connected,
            "MQTTBroker": self._broker_ip if connected else None,
            "MQTTUptime": self._uptime.read() if connected else 0,
            "MQTTConnects": counts[_C_CONNECTS],
            "MQTTTeardowns": counts[_C_TEARDOWNS],
            "MQTTLastReason": _REASONS[self._last_reason],
            "MQTTTxMsgs": counts[_C_TX],
            "MQTTTxDropped": counts[_C_TX_DROP],
            "MQTTRxMsgs": counts[_C_RX],
            "MQTTRxDropped": counts[_C_RX_DROP],
            "MQTTPingTimeouts": counts[_C_PING_TIMEOUTS],
            "MQTTShortSessions": counts[_C_SHORT],
            "MQTTLastRxTopic": last_topic,
        }

    def is_connected(self) -> bool:
        return self._state == _ST_CONNECTED

    def publish(self, topic: str | bytes, payload: str | bytes | bytearray | memoryview, *, qos: int = 0, retain: bool = False) -> bool:
        # Never blocks, never raises on load: a copy into a free ring slot, or False (counted) - Part A.11.
        if self._alloc_error is not None:
            return False
        name = topic.encode() if isinstance(topic, str) else topic
        data = payload.encode() if isinstance(payload, str) else payload
        if qos not in (0, 1) or (qos == 0 and self._state != _ST_CONNECTED) or self._state == _ST_DISABLED or len(data) > _OUT_PAYLOAD or not topic_name_ok(name):
            self._bump(_C_TX_DROP)
            return False
        return self._queue(name, data, qos, retain=retain)

    def reconnect(self) -> None:
        # The settings group's post_fct: the keeper ends the connection on its next tick and reads the new settings.
        self._reconfigure = True
        self._wake.set()

    async def setup(self) -> bool:  # call once, before any task starter runs
        ok = await super().setup()  # the logger first, so the failure below persists
        if self._alloc_error is not None:
            await self.pr.err_s("MQTT buffers could not be allocated, client off:", self._alloc_error, errno=_ERR_ALLOC)
        return ok
