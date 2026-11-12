"""MQTT 3.1.1 client service with its packet codec (QoS 0/1, clean or persistent session, plain TCP): a supervised
keeper owns the connection's writes, deadlines and reconnects, one reader per connection its reads; wired partners
subscribe and publish under the device's base topic. WifiService owns the radio; the contract: SPECIFICATION.md A.12."""

import asyncio
import errno
import io
import socket
import time
from collections import namedtuple

from micropython import const

from asy_base_classes import COUNTER_CAP, SensorReaderConfig, TickSeconds, utc_now
from asy_config_manager import INVALID, make_dict, name_cfg, schema_dict
from asy_dns_client import host_name_ok, resolve_ipv4
from asy_print_log import DEFAULT_LOG, LogConfig, report_if_fatal

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import NamedTuple, Protocol, TypeVar

    # A ticks_ms() value: the stubs type it opaque, so it only ever reaches time.ticks_diff()/ticks_add().
    from _mpy_shed.time_mp import _TicksMs

    from asy_base_classes import JsonMapping, TaskStarter, TimerStarter
    from asy_config_manager import ConfigSchema, WriteValidity
    from asy_print_log import ErrorLog

    _T = TypeVar("_T")
    Buf = bytearray | memoryview
    Bytes = bytes | bytearray | memoryview
    Will = tuple[Bytes, Bytes, int, bool]  # topic, message, QoS, retain
    # A wired partner's receiver (owner, 2026-10-07, paraphrase: inbound messages may trigger behaviours or carry values,
    # no flash writes): run on the reader, synchronously, with views of the topic and payload and the PUBLISH's flag bits.
    MqttCallback = Callable[[memoryview, memoryview, int], None]

    class _Stream(Protocol):
        # MicroPython's one asyncio Stream class, which the stubs split into StreamReader and StreamWriter.
        out_buf: bytes

        async def drain(self) -> None: ...

        async def readinto(self, buf: memoryview) -> int | None: ...

        async def wait_closed(self) -> None: ...

        def write(self, buf: bytes | bytearray | memoryview) -> None: ...

    # Build-time values the generated module passes whole: the client id default and every timing (Part N's mqtt.*).
    class MqttConfig(NamedTuple):
        client_id: str
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

else:
    MqttConfig = namedtuple(
        "MqttConfig",
        (
            "client_id", "response_timeout_ms", "connect_timeout_ms", "backoff_min_ms", "backoff_max_ms",
            "stable_after_ms", "qos1_retry_ms", "drain_timeout_ms", "tick_ms", "link_poll_ms", "idle_recheck_ms", "dns_timeout_ms",
        ),
    )

# Fixed-header first bytes (MQTT 3.1.1 section 2.2), the low nibble already holding the flags each type requires.
_CONNECT = const(0x10)
_CONNACK = const(0x20)
_PUBLISH = const(0x30)
_PUBACK = const(0x40)
_SUBSCRIBE = const(0x82)
_SUBACK = const(0x90)
_PINGRESP = const(0xD0)
_SUBACK_FAILURE = const(0x80)
_MAX_REMAINING = const(268435455)  # four length bytes (section 2.2.3); below COUNTER_CAP, so never a heap int
_LENGTH_INCOMPLETE = const(-1)  # decode_remaining_length(): more bytes needed
_LENGTH_MALFORMED = const(-2)  # a fifth length byte (section 2.2.3)
_PROTOCOL_LEVEL = const(4)  # 3.1.1 (section 3.1.2.2)
_FLAG_USER = const(0x80)
_FLAG_PASSWORD = const(0x40)
_FLAG_WILL_RETAIN = const(0x20)
_FLAG_WILL_QOS1 = const(0x08)
_FLAG_WILL = const(0x04)
_FLAG_CLEAN = const(0x02)
_PUBLISH_DUP = const(0x08)
_PUBLISH_RETAIN = const(0x01)
_MAX_TOPIC = const(128)  # a PUBLISH topic name; with a full payload slot it still fits the client's transmit buffer
_MAX_CLIENT_ID = const(23)  # the length every 3.1.1 server must accept (section 3.1.3.1)
_MAX_LABEL = const(63)
_MAX_PREFIX = const(64)
_LEN_1_BYTE = const(0x80)  # remaining lengths below these take one, two and three bytes
_LEN_2_BYTES = const(0x4000)
_LEN_3_BYTES = const(0x200000)
_SLASH = const(0x2F)
_HASH = const(0x23)
_PLUS = const(0x2B)
_DOLLAR = const(0x24)
_NUL = const(0x00)

# Codes from the global catalog (buildgen/error_catalog.json): the shared ones and MQTT's band.
_ERR_CALLBACK = const(14)
_ERR_ALLOC = const(20)
_ERR_BAD_ARG = const(21)
_ERR_UNEXPECTED = const(23)
_ERR_MQTT_DNS = const(123)
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
_WRN_MQTT_RETIRE_FAILED = const(83)

# Buffers, allocated once at construction (Part A.12's memory budget).
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
# @tunable mqtt.unconfirmed_max_bytes = 2000
_UNCONFIRMED_MAX = const(2000)  # bytes written but not yet proven received: the connection's lwIP MEM_SIZE share
_MAX_TEXT_BYTES = const(64)  # MQTTUser/MQTTPW and the two status payloads
_ID_BYTES = const(2)  # a packet id, and a string's length prefix (MQTT 3.1.1 section 1.5.3)
_SUBACK_MIN = const(3)  # a packet id and at least one return code
_CONNACK_LEN = const(4)
_TEXT_FIELDS = const(8)  # host, user, password, client id, prefix, status topic, online and offline payloads
_INT_FIELDS = const(3)  # port, ping interval, status QoS
_BOOL_FIELDS = const(3)  # enable, persistent session, status retain
_PW_MASK = "********"

_PINGREQ_PKT = b"\xc0\x00"
_DISCONNECT_PKT = b"\xe0\x00"

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
_VAL_MQTT_PING_INTERVAL = const((("MQTTPingInterval", "int", 180, 10, 3600, 0),))  # special 0: no idle ping, keep-alive 0
_VAL_MQTT_PERSISTENT = const((("MQTTPersistent", "bool", False, None, None, None),))
_VAL_MQTT_WILL_TOPIC = const((("MQTTWillTopic", "str", "", 1, 128, ""),))  # special "": <base>/status
_VAL_MQTT_ONLINE_MSG = const((("MQTTOnlineMsg", "str", "online", 1, 64, None),))
_VAL_MQTT_WILL_MSG = const((("MQTTWillMsg", "str", "offline", 1, 64, None),))
_VAL_MQTT_WILL_QOS = const((("MQTTWillQoS", "int", 1, 0, 1, (0, 1)),))
_VAL_MQTT_WILL_RETAIN = const((("MQTTWillRetain", "bool", True, None, None, None),))

# @web-group section=networking submitGroup=mqtt label="MQTT Broker" submit=true submitLabel="Apply & Reconnect"
# @web MQTTEnable section=networking submitGroup=mqtt label="MQTT Client" onLabel="On" offLabel="Off"
# @web MQTTHost section=networking submitGroup=mqtt label="Broker Address" description="IPv4 address, host name or .local name; plain TCP, no TLS." bytes=true shape=hostName special:""="No broker (client off)"
# @web MQTTPort section=networking submitGroup=mqtt label="Broker Port"
# @web MQTTUser section=networking submitGroup=mqtt label="User Name" description="Leave empty for an anonymous broker." bytes=true
# @web MQTTPW section=networking submitGroup=mqtt label="Password" mask=true bytes=true
# @web MQTTClientId section=networking submitGroup=mqtt label="Client ID" description="Also the device's topic level." bytes=true shape=hostLabel
# @web MQTTPrefix section=networking submitGroup=mqtt label="Topic Prefix" description="The device's topics live under <prefix>/<client id>: its status and those of the modules wired to the client." bytes=true
# @web MQTTPingInterval section=networking submitGroup=mqtt label="Ping Interval" unit="s" description="Seconds between keep-alive pings on an idle link; each message gets one of its own. The broker fires the will about 1.5 x (interval + 10 s) after the device drops off; Off lets the broker wait for ever." special:0="Off"
# @web MQTTPersistent section=networking submitGroup=mqtt label="Persistent Session" description="The broker keeps the subscriptions and queues QoS 1 messages while the device is away." onLabel="On" offLabel="Off"
# @web MQTTWillTopic section=networking submitGroup=mqtt label="Status Topic" description="Carries the will and the online message." bytes=true special:""="<prefix>/<client id>/status"
# @web MQTTOnlineMsg section=networking submitGroup=mqtt label="Online Message" description="Published on the status topic after each connect." bytes=true
# @web MQTTWillMsg section=networking submitGroup=mqtt label="Offline Message" description="The will: the broker publishes it when the device drops off." bytes=true
# @web MQTTWillQoS section=networking submitGroup=mqtt label="Status QoS" special:0="0 - at most once" special:1="1 - at least once"
# @web MQTTWillRetain section=networking submitGroup=mqtt label="Retain Status" onLabel="On" offLabel="Off"

# This service's one optional live cross-instance dependency (Part C.14): its FRAM error-log target.
# @wiring fram_target FRAMManager log optional kwarg


def _byte_ok_for_topic(ch: int) -> bool:
    # A topic level byte: no NUL (section 1.5.3) and no wildcard ('+' 0x2B, '#' 0x23).
    return ch not in (_NUL, _HASH, _PLUS)


def _kept(old: "_T", new: "_T") -> "_T":
    # The object already held when equal: a setting read again at each connect re-births no long-lived copy.
    return old if old == new else new


def _label_ok(label: str) -> bool:
    # An RFC 1123 host label: letters, digits and '-', not at either end, 1-63 characters.
    if not 0 < len(label) <= _MAX_LABEL or label[0] == "-" or label[-1] == "-":
        return False
    return all("0" <= ch <= "9" or "A" <= ch <= "Z" or "a" <= ch <= "z" or ch == "-" for ch in label)


def _put_fixed(buf: "Buf", first: int, remaining: int) -> int:
    # Writes the fixed header and returns its length, or -1 when the header and body cannot fit.
    size = 2 if remaining < _LEN_1_BYTE else 3 if remaining < _LEN_2_BYTES else 4 if remaining < _LEN_3_BYTES else 5
    if remaining > _MAX_REMAINING or size + remaining > len(buf):
        return -1
    buf[0] = first
    i = 1
    value = remaining
    while True:
        byte = value & 0x7F
        value >>= 7
        buf[i] = byte | 0x80 if value else byte
        i += 1
        if not value:
            return i


def _put_str(buf: "Buf", i: int, data: "Bytes") -> int:
    # A two-byte length then the bytes; the caller has sized the buffer, so this only writes.
    n = len(data)
    buf[i] = n >> 8
    buf[i + 1] = n & 0xFF
    buf[i + 2 : i + 2 + n] = data
    return i + 2 + n


def client_id_ok(value: str) -> bool:
    # A host label of 1-23 bytes: the letters and digits every broker accepts, plus the hostname's inner hyphen.
    return len(value) <= _MAX_CLIENT_ID and len(value.encode()) == len(value) and _label_ok(value)


def decode_remaining_length(buf: "Bytes", start: int, end: int) -> int:
    # The remaining length whose bytes start at buf[start] (section 2.2.3), _LENGTH_INCOMPLETE when buf[start:end]
    # holds only part of it, _LENGTH_MALFORMED past four bytes. A non-minimal encoding is read as written.
    value = 0
    shift = 0
    for i in range(start, min(end, start + 4)):
        byte = buf[i]
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value
        shift += 7
    return _LENGTH_MALFORMED if end >= start + 4 else _LENGTH_INCOMPLETE


def encode_connect(buf: "Buf", client_id: "Bytes", keepalive_s: int, will: "Will | None", user: "Bytes", password: "Bytes", *, clean: bool) -> int:
    # Section 3.1: `will` is (topic, message, QoS, retain), None for none, whose QoS and retain flags are then 0
    # ([MQTT-3.1.2-11], -13); user and password only when non-empty, a password never without a user (3.1.2.9). The
    # length, or -1 if it does not fit.
    flags = _FLAG_CLEAN if clean else 0
    remaining = 10 + 2 + len(client_id)
    if will is not None:
        flags |= _FLAG_WILL | (_FLAG_WILL_QOS1 if will[2] else 0) | (_FLAG_WILL_RETAIN if will[3] else 0)
        remaining += 2 + len(will[0]) + 2 + len(will[1])
    if user:
        flags |= _FLAG_USER
        remaining += 2 + len(user)
        if password:
            flags |= _FLAG_PASSWORD
            remaining += 2 + len(password)
    i = _put_fixed(buf, _CONNECT, remaining)
    if i < 0:
        return -1
    i = _put_str(buf, i, b"MQTT")
    buf[i] = _PROTOCOL_LEVEL
    buf[i + 1] = flags
    buf[i + 2] = (keepalive_s >> 8) & 0xFF
    buf[i + 3] = keepalive_s & 0xFF
    i = _put_str(buf, i + 4, client_id)
    if will is not None:
        i = _put_str(buf, i, will[0])
        i = _put_str(buf, i, will[1])
    if flags & _FLAG_USER:
        i = _put_str(buf, i, user)
    if flags & _FLAG_PASSWORD:
        i = _put_str(buf, i, password)
    return i


def encode_puback(buf: "Buf", pid: int) -> int:
    # A PUBACK (section 3.4) into a buffer of at least four bytes.
    buf[0] = _PUBACK
    buf[1] = 2
    buf[2] = pid >> 8
    buf[3] = pid & 0xFF
    return 4


def encode_publish(buf: "Buf", topic: "Bytes", payload: "Bytes", qos: int, pid: int, *, retain: bool, dup: bool) -> int:
    # A PUBLISH (section 3.3) with its payload. Returns the length, or -1.
    i = encode_publish_head(buf, topic, len(payload), qos, pid, retain=retain, dup=dup)
    if i < 0:
        return -1
    buf[i : i + len(payload)] = payload
    return i + len(payload)


def encode_publish_head(buf: "Buf", topic: "Bytes", length: int, qos: int, pid: int, *, retain: bool, dup: bool) -> int:
    # A PUBLISH (section 3.3) up to its payload of `length` bytes, which the caller writes from the index returned;
    # -1 when the whole packet cannot fit. The packet id is written only at QoS 1.
    first = _PUBLISH | (qos << 1) | (_PUBLISH_RETAIN if retain else 0) | (_PUBLISH_DUP if dup and qos else 0)
    i = _put_fixed(buf, first, 2 + len(topic) + (2 if qos else 0) + length)
    if i < 0:
        return -1
    i = _put_str(buf, i, topic)
    if qos:
        buf[i] = pid >> 8
        buf[i + 1] = pid & 0xFF
        i += 2
    return i


def encode_subscribe(buf: "Buf", pid: int, filters: tuple[bytes, ...]) -> int:
    # One SUBSCRIBE (section 3.8) requesting QoS 1 for every filter. Returns the length, or -1.
    if not filters:
        return -1
    i = _put_fixed(buf, _SUBSCRIBE, 2 + sum(3 + len(f) for f in filters))
    if i < 0:
        return -1
    buf[i] = pid >> 8
    buf[i + 1] = pid & 0xFF
    i += 2
    for flt in filters:
        i = _put_str(buf, i, flt)
        buf[i] = 1
        i += 1
    return i


def prefix_ok(value: str) -> bool:
    # The topic prefix: 1-64 bytes, no wildcard or NUL, no empty level at either end (so <prefix>/<id> is one tree).
    data = value.encode()
    return 0 < len(data) <= _MAX_PREFIX and data[0] != _SLASH and data[-1] != _SLASH and all(_byte_ok_for_topic(ch) for ch in data)


def remaining_length_bytes(buf: "Bytes", start: int, end: int) -> int:
    # How many bytes the remaining length starting at buf[start] occupies; call only once
    # decode_remaining_length() returned a value.
    for i in range(start, min(end, start + 4)):
        if not buf[i] & 0x80:
            return i - start + 1
    return 4


def status_topic_ok(value: str) -> bool:
    # The will's topic: a topic name outside the '$' tree brokers reserve (mosquitto refuses a will under $CONTROL/).
    data = value.encode()
    return topic_name_ok(data) and data[0] != _DOLLAR


def text_ok(value: "Bytes", max_bytes: int) -> bool:
    # A UTF-8 user name or password: at most max_bytes and no NUL (section 1.5.3).
    return len(value) <= max_bytes and 0 not in value


def topic_matches(flt: "Bytes", topic: "Bytes") -> bool:
    # Section 4.7: '+' one level, '#' the rest (its parent level included); a '$' topic matches no leading wildcard.
    if topic and topic[0] == _DOLLAR and flt and flt[0] in (_HASH, _PLUS):
        return False
    fi = 0
    ti = 0
    nf = len(flt)
    nt = len(topic)
    while fi < nf:
        ch = flt[fi]
        if ch == _HASH:
            return True
        if ch == _PLUS:  # one level of the topic, possibly empty
            while ti < nt and topic[ti] != _SLASH:
                ti += 1
            fi += 1
            continue
        if ti >= nt:
            # "a/#" also matches "a": the topic ended exactly where "/#" begins.
            return ch == _SLASH and fi + 2 == nf and flt[fi + 1] == _HASH
        if topic[ti] != ch:
            return False
        fi += 1
        ti += 1
    return ti == nt


def topic_name_ok(value: "Bytes") -> bool:
    # A PUBLISH topic name: 1-128 bytes, no wildcard and no NUL (section 4.7.3); a wildcard would end the session.
    return 0 < len(value) <= _MAX_TOPIC and all(_byte_ok_for_topic(ch) for ch in value)


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
    # One MQTTPingInterval second in ms; a class attribute, so the device's instances hold no copy and a test shortens it.
    _ping_unit_ms = 1000

    def __init__(
        self,
        wifi_mode_lock: asyncio.Lock,
        network_available_locked: "Callable[[], bool]",
        get_dns_server: "Callable[[], str | None]",
        config: MqttConfig,
        cfg_path: str = "",
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        name, kind, _default, low, high, special = _VAL_MQTT_CLIENT_ID[0]
        default_id = config.client_id if client_id_ok(config.client_id) else _default
        self._val_client_id = ((name, kind, default_id, low, high, special),)  # the device's hostname as the default
        super().__init__(
            MQTT(Connected=False, TS=None),
            _NAME,
            _VAL_MQTT_ENABLE + _VAL_MQTT_HOST + _VAL_MQTT_PORT + _VAL_MQTT_USER + _VAL_MQTT_PW + self._val_client_id + _VAL_MQTT_PREFIX
            + _VAL_MQTT_PING_INTERVAL + _VAL_MQTT_PERSISTENT + _VAL_MQTT_WILL_TOPIC + _VAL_MQTT_ONLINE_MSG + _VAL_MQTT_WILL_MSG + _VAL_MQTT_WILL_QOS + _VAL_MQTT_WILL_RETAIN,
            max_module_error=0,  # no failure streak: a broker outage is routine, never a restart (Part C.7.2)
            cfg_path=cfg_path,
            log=log,
        )
        self.wifi_mode_lock = wifi_mode_lock  # shared with WifiService; held only around the availability check
        self._network_available_locked = network_available_locked
        self._get_dns_server = get_dns_server
        self._cfg = config
        self._alloc_error: Exception | None = None
        try:
            self._rx = bytearray(_RX_BYTES)
            self._tx = bytearray(_TX_BYTES)
            self._acks = bytearray(2 * _ACK_SLOTS)
            self._last_topic = bytearray(_LAST_TOPIC_BYTES)
            self._rxmv = memoryview(self._rx)
            self._txmv = memoryview(self._tx)
            # One preallocated stream per slot (io.BytesIO(alloc_size)), never one ring: no long-lived block here needs
            # more contiguous heap than _rx does.
            self._slots = [io.BytesIO(_OUT_PAYLOAD) for _ in range(_OUT_SLOTS)]
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
        except MemoryError as e:  # boot-time only: the client stays off, and setup() persists the ALLOC entry
            self._alloc_error = e
            self.pr.err("MQTT buffers could not be allocated:", e)
        self._wake = asyncio.Event()  # set by reconnect(): ends an idle or backoff wait at once
        self._ping_s = _VAL_MQTT_PING_INTERVAL[0][2]  # 0: no idle ping
        self._uptime = TickSeconds()
        # The wired partners' registrations, each "/" + its level below <base>, and the full topics and filters built from
        # them once per settings change (_build_topics()); a filter's index is its callback's.
        self._rel_filters: list[bytes] = []
        self._callbacks: list[MqttCallback] = []
        self._rel_topics: list[bytes] = []
        self._filters: tuple[bytes, ...] = ()
        self._topics: list[bytes] = []
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
        self._will_setting = ""  # MQTTWillTopic as last read; "" is <base>/status
        self._status_topic = b""  # the will's topic, also the online and offline messages'
        self._online = b""
        self._offline = b""
        self._status_qos = 1
        self._status_retain = True
        self._persistent = False
        self._session_present = False  # the last CONNACK's flag: the broker resumed a persistent session
        # The identity a broker may hold a persistent session for, and one left behind to end (Part A.12).
        self._owed: tuple[str, int, bytes, bytes, bytes, bytes] | None = None
        self._retire: tuple[str, int, bytes, bytes, bytes, bytes] | None = None
        self._push_callbacks.clear()  # every field is persist-only: the next connect reads it

    async def _set_mgr_cfg(self, data: "JsonMapping", cfg_vals: "ConfigSchema") -> "tuple[bool, WriteValidity]":
        # Refuses a string outside its MQTT shape before it is stored (C.7.4's precedent); the rest goes through as usual.
        fields = schema_dict(cfg_vals)
        refused = [k for k, v in data.items() if k in fields and isinstance(v, str) and not self._shape_ok(k, v)]
        for key in refused:
            self.pr.err_s("Refusing", key, "- outside the MQTT client's accepted form", errno=_ERR_BAD_ARG)
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

    def _build_topics(self) -> None:
        # Every partner's topic and filter under the current base: built once per settings change, kept until the next.
        base = self._base
        self._topics = [base + rel for rel in self._rel_topics]
        self._filters = tuple(base + rel for rel in self._rel_filters)

    def _bump(self, i: int) -> None:
        count = self._counts[i]
        if count < COUNTER_CAP:
            self._counts[i] = count + 1

    async def _close(self) -> None:
        # The teardown every connection ends with: the reader cancelled, then the socket closed. Never awaited: an
        # except CancelledError there would also swallow the keeper's own cancellation (Part A.12).
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

    async def _connect(self, host: str, port: int, client_id: bytes, user: bytes, password: bytes, will: bytes, *, clean: bool, quiet: bool = False) -> int:
        # Resolve, connect and CONNECT/CONNACK under their own timeouts; _R_NONE once the session is up. The will is the
        # status topic's when `will` is set; quiet (a retire) logs nothing, its caller logging the one warning.
        dns_server = await self._safe_dns_server()  # read before any lock, as NTP does
        ip = await resolve_ipv4(host, () if dns_server is None else (dns_server,), timeout_ms=self._cfg.dns_timeout_ms, logger=self.pr)
        if ip is None:
            if not quiet:
                self.pr.err_s("Broker name did not resolve:", host, errno=_ERR_MQTT_DNS)
            return _R_CONNECT
        if not quiet:
            self._broker_ip = ip
        try:
            addr = socket.getaddrinfo(ip, port)[0][-1]  # an IPv4 literal: no DNS query (Part F.2)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except (MemoryError, OSError) as e:
            if not quiet:
                self.pr.err_s("Could not open a socket:", e, errno=_ERR_MQTT_CONNECT)
            return _R_CONNECT
        stream: _Stream = asyncio.StreamReader(sock)  # type: ignore[assignment]  # MicroPython's one Stream class
        self._stream = stream  # owned from here: _close() ends it on every path
        sock.setblocking(False)
        # The keep-alive promises the next ping within the interval plus its own deadline; 0 promises none (section 3.1.2.10).
        keepalive = self._ping_s + (self._cfg.response_timeout_ms + 999) // 1000 if self._ping_s else 0
        n = encode_connect(self._txmv, client_id, keepalive, (self._status_topic, will, self._status_qos, self._status_retain) if will else None, user, password, clean=clean)
        if n < 0:  # unreachable within the schema's bounds, which _TX_BYTES is sized for
            if not quiet:
                self.pr.err_s("CONNECT does not fit the transmit buffer", errno=_ERR_MQTT_CONNECT)
            return _R_CONNECT
        try:
            try:
                sock.connect(addr)
            except OSError as e:
                if e.errno != errno.EINPROGRESS:
                    raise
            stream.write(self._txmv[:n])  # held in out_buf until the handshake completes
            await asyncio.wait_for_ms(stream.drain(), self._cfg.connect_timeout_ms)
            reason = await self._read_connack(stream, clean=clean, quiet=quiet)
        except (OSError, asyncio.TimeoutError) as e:
            if not quiet:
                self.pr.err_s("Broker connect failed:", ip, e, errno=_ERR_MQTT_CONNECT)
            return _R_CONNECT
        return reason

    async def _connection_loop(self) -> None:
        # The keeper (Part A.12): never ends on a remote fault; a restarted task first closes what the last one left.
        await self._close()
        while True:
            self._wake.clear()
            self._reconfigure = False
            enabled = self._alloc_error is None and await self._read_params()
            if self._retire is not None:
                if not await self._safe_link_up():
                    await asyncio.sleep_ms(self._cfg.link_poll_ms)  # a retire waits for the link as a connect does
                    continue
                await self._retire_session()
            if not enabled:
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
        if kind == _PUBLISH:
            return self._on_publish(hdr, total)
        if kind == _PUBACK and total - hdr == _ID_BYTES:
            pid = (rx[hdr] << 8) | rx[hdr + 1]
            for i in range(_OUT_SLOTS):
                if self._slot_state[i] == _SLOT_INFLIGHT and self._slot_pid[i] == pid:
                    self._free(i)
                    break
            return _R_NONE
        if kind == _PINGRESP and total == hdr:
            # TCP delivers in order, so everything written up to the PINGREQ has arrived and lwIP has freed it.
            self._ping_out = False
            self._unconfirmed = max(0, self._unconfirmed - self._ping_mark)
            self._ping_mark = 0
            return _R_NONE
        if kind == _SUBACK and total - hdr >= _SUBACK_MIN:
            for j in range(hdr + _ID_BYTES, total):
                if rx[j] == _SUBACK_FAILURE:
                    self._sub_refused = True
            return _R_NONE
        self._detail = rx[0]
        return _R_PROTOCOL

    async def _log_end(self, reason: int, lasted_ms: int) -> None:
        # One persisted entry per failed attempt or lost connection; a link loss and a reconfigure log nothing, and the
        # reader's top has logged an unexpected end.
        if reason in (_R_EOF, _R_IO) and lasted_ms < self._cfg.stable_after_ms:
            self._bump(_C_SHORT)
            if self._short_streak < _SHORT_SESSION_WARN:
                self._short_streak += 1
                if self._short_streak == _SHORT_SESSION_WARN:
                    # This end is the warning, not also an error: one occurrence is one kind (C.7.1).
                    self.pr.wrn_s("Sessions keep ending right after they start - another client with this client id?", wrnno=_WRN_MQTT_SHORT_SESSIONS)
                    return
        if reason == _R_PING:
            self.pr.err_s("No PINGRESP from", self._broker_ip, errno=_ERR_MQTT_NO_PINGRESP)
        elif reason == _R_EOF:
            self.pr.err_s("Broker closed the connection", errno=_ERR_MQTT_LOST)
        elif reason == _R_IO:
            self.pr.err_s("Connection lost, errno", self._detail, errno=_ERR_MQTT_LOST)
        elif reason == _R_PROTOCOL:
            self.pr.err_s("Protocol error, packet", self._detail, errno=_ERR_MQTT_PROTOCOL)
        elif reason == _R_STALLED:
            self.pr.err_s("Broker stopped reading", errno=_ERR_MQTT_STALLED)
        elif reason == _R_RECONFIGURE:
            self.pr.evt("Reconnecting with new settings.")

    async def _mask_pw(self) -> dict[str, int | float | str | bool | None]:
        return {name_cfg(_VAL_MQTT_PW): _PW_MASK}

    def _new_connection(self) -> None:
        # Per-connection state, reset before each connect; the outbound ring survives, its QoS 1 sorted at the CONNACK.
        self._reset_connection_state()
        for i in range(_OUT_SLOTS):
            if self._slot_state[i] == _SLOT_QUEUED and not self._slot_qos[i]:
                self._free(i)  # QoS 0 is never carried across an outage

    def _next_pid(self) -> int:
        # Never 0, and never an id still in flight, which a resumed session carries across connections (section 2.3.1).
        while True:
            pid = self._pid % 65535 + 1
            self._pid = pid
            for i in range(_OUT_SLOTS):
                if self._slot_state[i] == _SLOT_INFLIGHT and self._slot_pid[i] == pid:
                    break
            else:
                return pid

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
        flags = rx[0] & 0x0F  # DUP, QoS and RETAIN (section 3.3.1)
        filters = self._filters
        for i in range(len(filters)):
            if topic_matches(filters[i], topic):
                try:
                    self._callbacks[i](topic, payload, flags)
                except Exception as e:  # a consumer's fault never ends the reader; the keeper logs it
                    report_if_fatal(e)
                    self._bump(_C_CONSUMER_ERR)
        return _R_NONE

    def _protocol(self, first: int) -> int:
        self._detail = first
        return _R_PROTOCOL

    def _queue(self, topic: bytes, payload: bytes | bytearray | memoryview, qos: int, *, retain: bool) -> bool:
        i = self._free_slot()
        if i < 0:
            self._bump(_C_TX_DROP)
            return False
        slot = self._slots[i]
        slot.seek(0)
        slot.write(payload)  # within the slot: publish() refuses a payload above _OUT_PAYLOAD
        self._queued(i, len(payload), topic, qos, retain=retain)
        return True

    def _queued(self, i: int, n: int, topic: bytes, qos: int, *, retain: bool) -> None:
        # Slot i, its n payload bytes already in place, joins the queue as its newest message.
        self._slot_len[i] = n
        self._slot_topic[i] = topic
        self._slot_qos[i] = qos
        self._slot_retain[i] = 1 if retain else 0
        self._slot_tries[i] = 0
        self._seq = self._seq + 1 if self._seq < COUNTER_CAP else 0
        self._slot_seq[i] = self._seq
        self._slot_state[i] = _SLOT_QUEUED

    async def _read_connack(self, stream: "_Stream", *, clean: bool, quiet: bool) -> int:
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
        # Bit 0 is Session Present, never an error (mqtt_as A4), but always 0 on a clean session (section 3.2.2.2).
        if rx[0] != _CONNACK or rx[1] != _ID_BYTES or rx[2] & 0xFE or (clean and rx[2]):
            if not quiet:
                self.pr.err_s("Malformed CONNACK:", rx[0], rx[1], rx[2], errno=_ERR_MQTT_PROTOCOL)
            return _R_CONNECT
        if rx[3]:
            if not quiet:
                self.pr.err_s("Broker refused the connection, return code", rx[3], errno=_ERR_MQTT_REFUSED)
            return _R_CONNECT
        self._session_present = bool(rx[2])
        self._compact(_CONNACK_LEN)
        return _R_NONE

    async def _read_params(self) -> bool:
        # The configuration for the next connect; False when off, or when a read or a stored shape fails. A read that
        # succeeds also settles which persistent session is owed and which one is left behind (_settle_session()).
        bools = await self.cfgmgr.get_bool_values(_VAL_MQTT_ENABLE + _VAL_MQTT_PERSISTENT + _VAL_MQTT_WILL_RETAIN)
        texts = await self.cfgmgr.get_str_values(
            _VAL_MQTT_HOST + _VAL_MQTT_USER + _VAL_MQTT_PW + self._val_client_id + _VAL_MQTT_PREFIX + _VAL_MQTT_WILL_TOPIC + _VAL_MQTT_ONLINE_MSG + _VAL_MQTT_WILL_MSG,
        )
        ints = await self.cfgmgr.get_int_values(_VAL_MQTT_PORT + _VAL_MQTT_PING_INTERVAL + _VAL_MQTT_WILL_QOS)
        if bools is None or texts is None or ints is None or len(bools) != _BOOL_FIELDS or len(texts) != _TEXT_FIELDS or len(ints) != _INT_FIELDS:
            if not self._cfg_warned:
                self._cfg_warned = True
                self.pr.wrn_s("Error reading own configuration!", wrnno=_WRN_CFG_READ)
            return False
        enable, persistent, retain = bools
        host, user, password, client_id, prefix, will_topic, online, offline = texts
        if not enable or not host:
            self._settle_session(None, persistent=False)
            return False
        user_b, password_b, online_b, offline_b = user.encode(), password.encode(), online.encode(), offline.encode()
        texts_ok = text_ok(user_b, _MAX_TEXT_BYTES) and text_ok(password_b, _MAX_TEXT_BYTES) and text_ok(online_b, _MAX_TEXT_BYTES) and text_ok(offline_b, _MAX_TEXT_BYTES)
        if not (host_name_ok(host) and client_id_ok(client_id) and prefix_ok(prefix) and (not will_topic or status_topic_ok(will_topic)) and online_b and offline_b and texts_ok):
            if not self._cfg_warned:
                self._cfg_warned = True
                self.pr.wrn_s("Stored MQTT settings out of shape, client off:", host, client_id, prefix, will_topic, wrnno=_WRN_STORED_DEFAULT)
            return False
        base = (prefix + "/" + client_id).encode()
        if base != self._base or will_topic != self._will_setting:
            if base != self._base:
                self._base = base
                self._build_topics()
            self._will_setting = will_topic
            self._status_topic = will_topic.encode() if will_topic else base + b"/status"
        # Read anew at each connect, but an unchanged value keeps the object already held, born at setup().
        self._host, self._port, self._ping_s = _kept(self._host, host), ints[0], ints[1]
        self._user, self._password = _kept(self._user, user_b), _kept(self._password, password_b)
        self._client_id = _kept(self._client_id, client_id.encode())
        self._online, self._offline = _kept(self._online, online_b), _kept(self._offline, offline_b)
        self._status_qos, self._status_retain = ints[2], retain
        self._settle_session((self._host, self._port, self._client_id), persistent=persistent)
        self._persistent = persistent
        return True

    async def _reader_loop(self, stream: "_Stream") -> None:
        # The connection's only reader; it never raises, and records why it ended for the keeper. Its task top logs an
        # unexpected exception, the one entry it writes (C.9); every other end the keeper logs.
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
        except Exception as e:  # never-raise boundary: the task top
            self._reader_end = _R_UNEXPECTED
            self.pr.err_s("Reader ended unexpectedly:", e, errno=_ERR_UNEXPECTED)

    def _resend_inflight(self, stream: "_Stream", now: "_TicksMs") -> None:
        # Section 4.4: a resumed session's unacknowledged messages, oldest first, with their packet ids and DUP; one the
        # unconfirmed-bytes cap holds goes with the next retransmission round instead.
        while True:
            i = -1
            for j in range(_OUT_SLOTS):
                if self._slot_state[j] == _SLOT_INFLIGHT and not self._slot_tries[j] and (i < 0 or self._slot_seq[j] < self._slot_seq[i]):
                    i = j
            if i < 0 or not self._send_slot(stream, i, dup=True):
                return
            self._slot_sent[i] = now

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
        self._ping_early = False  # a PUBLISH awaits confirmation or room: the next free tick pings, interval or not

    async def _retire_session(self) -> None:
        # One clean connect with the identity left behind and no will, then DISCONNECT: the broker discards that session
        # ([MQTT-3.1.2-6]). Tried once; a failure is one warning, the session left to the broker's expiry (Part A.12).
        retire = self._retire
        self._retire = None
        if retire is None:
            return
        host, port, client_id, _base, user, password = retire
        self._reset_connection_state()
        self._set_state(_ST_CONNECTING)
        try:
            if await self._connect(host, port, client_id, user, password, b"", clean=True, quiet=True) == _R_NONE and self._stream is not None:
                self._stream.write(_DISCONNECT_PKT)
                await asyncio.wait_for_ms(self._stream.drain(), self._cfg.drain_timeout_ms)
                self.pr.evt("Ended the persistent session left on", host)
                return
        except (OSError, asyncio.TimeoutError):
            pass
        finally:
            await self._close()
        self.pr.wrn_s("Could not end the persistent session left on", host, "- the broker's expiry applies", wrnno=_WRN_MQTT_RETIRE_FAILED)

    async def _safe_dns_server(self) -> str | None:
        try:
            return self._get_dns_server()
        except Exception as e:  # caller-supplied callback - could legitimately misbehave
            self.pr.err_s("get_dns_server() callback failed:", e, errno=_ERR_CALLBACK)
            return None

    async def _safe_link_up(self) -> bool:
        # network_available_locked() under wifi_mode_lock, released before any broker I/O (Part A.12).
        async with self.wifi_mode_lock:
            try:
                return self._network_available_locked()
            except Exception as e:  # caller-supplied callback - could legitimately misbehave
                self.pr.err_s("network_available_locked() callback failed:", e, errno=_ERR_CALLBACK)
                return False

    def _send_slot(self, stream: "_Stream", i: int, *, dup: bool) -> bool:
        # False when the PUBLISH would take the unconfirmed bytes past their cap; it waits for the next ping's answer.
        if not dup and self._slot_qos[i]:
            self._slot_pid[i] = self._next_pid()
        topic = self._slot_topic[i] or b""
        length = self._slot_len[i]
        head = encode_publish_head(self._txmv, topic, length, self._slot_qos[i], self._slot_pid[i], retain=bool(self._slot_retain[i]), dup=dup)
        if head > 0:
            n = head + length
            if self._unconfirmed and self._unconfirmed + n > _UNCONFIRMED_MAX:
                if not self._ping_out:
                    self._ping_early = True
                return False
            slot = self._slots[i]
            slot.seek(0)
            slot.readinto(self._txmv[head:n])  # the payload after its head: one packet, one write
            self._write(stream, self._txmv[:n])
            self._ping_early = True  # a ping of its own confirms it, whatever the interval (owner, 2026-10-13)
        self._slot_tries[i] += 1
        return True

    async def _serve(self, stream: "_Stream") -> int:
        # The keeper's tick while connected: every write, the ping and link deadlines, and stability.
        cfg = self._cfg
        if self._session_present:
            self._resend_inflight(stream, time.ticks_ms())  # before anything new (section 4.6)
        subscribe = encode_subscribe(self._txmv, self._next_pid(), self._filters)  # every partner's filter; none: no SUBSCRIBE
        if subscribe > 0:
            self._write(stream, self._txmv[:subscribe])
        self._queue(self._status_topic, self._online, self._status_qos, retain=self._status_retain)
        self._flush_outbound(stream, time.ticks_ms())  # online in this step: a stalled loop cannot hold it past a tick
        while True:
            await asyncio.sleep_ms(cfg.tick_ms)  # sleep_ms() allocates nothing
            if self._reconfigure:
                return _R_RECONFIGURE
            if self._reader_end != _R_NONE:
                return self._reader_end
            now = time.ticks_ms()
            if time.ticks_diff(now, self._last_link) >= cfg.link_poll_ms and not self.wifi_mode_lock.locked():
                # A busy lock (a mode switch, a connect attempt) defers the check to the first tick after it, so a link lost
                # under it ends the connection then (owner, 2026-10-08: 'when the device is in hotspot mode, the MQTT client is off.').
                self._last_link = now
                if not await self._safe_link_up():
                    return _R_LINK  # WIFI logs its own loss
            if self._ping_out:
                if time.ticks_diff(now, self._ping_sent) >= cfg.response_timeout_ms:
                    self._bump(_C_PING_TIMEOUTS)
                    return _R_PING
            elif self._ping_early or (self._ping_s and time.ticks_diff(now, self._last_ping) >= self._ping_s * self._ping_unit_ms):
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
                self.pr.err_s("Broker refused a subscription", errno=_ERR_MQTT_SUB_REFUSED)
            if self._counts[_C_CONSUMER_ERR] != self._consumer_errors_logged:
                self._consumer_errors_logged = self._counts[_C_CONSUMER_ERR]
                self.pr.err_s("An MQTT consumer raised", errno=_ERR_CALLBACK)
            backlog = len(stream.out_buf)
            if backlog > _MAX_OUT_BACKLOG:
                return _R_STALLED
            if backlog:
                try:
                    await asyncio.wait_for_ms(stream.drain(), cfg.drain_timeout_ms)
                except asyncio.TimeoutError:
                    return _R_STALLED  # the timeout cancelled a socket waiter: this connection ends now (Part A.12)
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
            reason = await self._connect(self._host, self._port, self._client_id, self._user, self._password, self._offline, clean=not self._persistent)
            stream = self._stream
            if reason != _R_NONE or stream is None:
                self._last_reason = reason
                return reason
            self._settle_inflight()
            self._connected_at = time.ticks_ms()
            self._last_ping = self._connected_at
            self._last_link = self._connected_at
            self._uptime.restart(0)
            self._bump(_C_CONNECTS)
            self._set_state(_ST_CONNECTED)
            await self._set_meas_data(MQTT(Connected=True, TS=utc_now()))
            self.pr.evt("Connected to", self._broker_ip, "port", self._port)
            self._reader = asyncio.create_task(self._reader_loop(stream))
            try:
                reason = await self._serve(stream)
            except OSError as e:
                self._detail = e.errno if isinstance(e.errno, int) else 0
                reason = _R_IO
            if reason == _R_RECONFIGURE:
                # A DISCONNECT makes the broker drop the will, so the status is set to the offline message first.
                n = encode_publish(self._txmv, self._status_topic, self._offline, 0, 0, retain=self._status_retain, dup=False)
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

    def _settle_inflight(self) -> None:
        # After a CONNACK: a resumed session sends its unacknowledged QoS 1 again first, as they were (_resend_inflight());
        # without one, the session they belonged to is gone and they go out as new messages (section 3.2.2.2).
        due = time.ticks_add(time.ticks_ms(), -self._cfg.qos1_retry_ms)  # one the cap holds back goes at the next tick
        for i in range(_OUT_SLOTS):
            if self._slot_state[i] == _SLOT_INFLIGHT:
                self._slot_tries[i] = 0
                self._slot_sent[i] = due
                if not self._session_present:
                    self._slot_state[i] = _SLOT_QUEUED

    def _settle_session(self, nxt: tuple[str, int, bytes] | None, *, persistent: bool) -> None:
        # The persistent session a broker may hold is owed while the settings keep its identity, and left behind to be
        # retired once they move away from it, unless the next connect (same host, port and id, clean) discards it itself.
        left = self._retire if self._retire is not None else self._owed
        self._owed = (self._host, self._port, self._client_id, self._base, self._user, self._password) if nxt is not None and persistent else None
        kept = nxt is not None and left is not None and left[:3] == nxt and (not persistent or left[3] == self._base)
        self._retire = None if kept else left

    def _shape_ok(self, key: str, value: str) -> bool:
        # MQTTHost takes NTPHost's hostName shape, its special "" (the client off) aside (Part A.12).
        if key == name_cfg(_VAL_MQTT_HOST):
            return value == "" or host_name_ok(value)
        if key == name_cfg(self._val_client_id):
            return client_id_ok(value)
        if key == name_cfg(_VAL_MQTT_PREFIX):
            return prefix_ok(value)
        if key == name_cfg(_VAL_MQTT_WILL_TOPIC):
            return value == "" or status_topic_ok(value)
        if key in (name_cfg(_VAL_MQTT_USER), name_cfg(_VAL_MQTT_PW), name_cfg(_VAL_MQTT_ONLINE_MSG), name_cfg(_VAL_MQTT_WILL_MSG)):
            return text_ok(value.encode(), _MAX_TEXT_BYTES)
        return True

    def _take_packets(self) -> int:
        # Every complete packet in the receive buffer, in order; an oversize one switches to discarding its bytes.
        while self._rx_len >= _ID_BYTES:  # a first byte and at least one length byte
            rem = decode_remaining_length(self._rx, 1, self._rx_len)
            if rem == _LENGTH_INCOMPLETE:
                return _R_NONE
            if rem == _LENGTH_MALFORMED:
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
        return [self.start_asy_connection]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return []  # no machine.Timer anywhere in this file (SPECIFICATION.md C.9 shape)

    def start_asy_connection(self) -> asyncio.Task[None]:
        return asyncio.create_task(self._connection_loop())

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

    def add_consumer(self, topic_filter: str, callback: "MqttCallback") -> None:
        # A wired partner's receiver, registered before the tasks start; its filter is relative to <base> ("cmd/#") and
        # subscribed at every connect. The callback is synchronous, copies what it keeps and must not raise: a raise is
        # counted and logged as CALLBACK, its message still acknowledged; a retained one (flags bit 0) comes again (A.12).
        self._rel_filters.append(b"/" + topic_filter.encode())
        self._callbacks.append(callback)
        if self._base:
            self._build_topics()

    def add_topic(self, topic: str) -> int:
        # A wired partner's outbound topic, relative to <base> and registered before the tasks start; the id is what
        # publish_under() takes. Its full form is built once per settings change, so no publish allocates a topic.
        self._rel_topics.append(b"/" + topic.encode())
        if self._base:
            self._build_topics()
        return len(self._rel_topics) - 1

    def publish(self, topic: str | bytes, payload: str | bytes | bytearray | memoryview, *, qos: int = 0, retain: bool = False) -> bool:
        # Never blocks, never raises on load: a copy into a free ring slot, or False (counted) - Part A.12.
        if self._alloc_error is not None:
            return False
        name = topic.encode() if isinstance(topic, str) else topic
        data = payload.encode() if isinstance(payload, str) else payload
        if qos not in (0, 1) or (qos == 0 and self._state != _ST_CONNECTED) or self._state == _ST_DISABLED or len(data) > _OUT_PAYLOAD or not topic_name_ok(name):
            self._bump(_C_TX_DROP)
            return False
        return self._queue(name, data, qos, retain=retain)

    def publish_under(self, topic_id: int, payload: str | bytes | bytearray | memoryview, *, qos: int = 0, retain: bool = False) -> bool:
        # publish() on add_topic()'s <base>/<topic>; an id with no topic built yet (no settings read) is refused, counted.
        topics = self._topics
        return self.publish(topics[topic_id] if 0 <= topic_id < len(topics) else b"", payload, qos=qos, retain=retain)

    def reconnect(self) -> None:
        # The settings group's post_fct: the keeper ends the connection on its next tick and reads the new settings.
        self._reconfigure = True
        self._wake.set()

    async def setup(self) -> None:  # call once, before any task starter runs
        await super().setup()  # the logger first, so the failure below persists
        if self._alloc_error is not None:
            self.pr.err_s("MQTT buffers could not be allocated, client off", errno=_ERR_ALLOC)
        elif self.cfgmgr.valid:
            # The settings' encoded forms and the partners' topics live as long as the settings do: born here, inside the
            # boot list's placement reset (Part I.4(f.1)), not at the first connect after it.
            await self._read_params()
