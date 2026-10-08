"""MQTT 3.1.1 packets for asy_mqtt_client.py: encoders that write into a caller's buffer and return the length (-1 when it
does not fit), the remaining-length decoder, topic-filter matching and the configuration shape checks. Pure: no I/O, no
logging, nothing raised on wire input (SPECIFICATION.md Part A.11)."""

from micropython import const

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    Buf = bytearray | memoryview
    Bytes = bytes | bytearray | memoryview

# Fixed-header first bytes (MQTT 3.1.1 section 2.2), the low nibble already holding the flags each type requires.
CONNECT = const(0x10)
CONNACK = const(0x20)
PUBLISH = const(0x30)
PUBACK = const(0x40)
SUBSCRIBE = const(0x82)
SUBACK = const(0x90)
PINGREQ = const(0xC0)
PINGRESP = const(0xD0)
DISCONNECT = const(0xE0)
SUBACK_FAILURE = const(0x80)
MAX_REMAINING = const(268435455)  # four length bytes (section 2.2.3); below COUNTER_CAP, so never a heap int

LENGTH_INCOMPLETE = const(-1)  # decode_remaining_length(): more bytes needed
LENGTH_MALFORMED = const(-2)  # a fifth length byte (section 2.2.3)

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
_MAX_HOST = const(253)  # RFC 1035
_MAX_LABEL = const(63)
_IPV4_PARTS = const(4)
_OCTET_DIGITS = const(3)
_OCTET_MAX = const(0xFF)
_MAX_PREFIX = const(64)
_LEN_1_BYTE = const(0x80)  # remaining lengths below these take one, two and three bytes
_LEN_2_BYTES = const(0x4000)
_LEN_3_BYTES = const(0x200000)
_SLASH = const(0x2F)
_HASH = const(0x23)
_PLUS = const(0x2B)
_DOLLAR = const(0x24)
_NUL = const(0x00)


def _byte_ok_for_topic(ch: int) -> bool:
    # A topic level byte: no NUL (section 1.5.3) and no wildcard ('+' 0x2B, '#' 0x23).
    return ch not in (_NUL, _HASH, _PLUS)


def _label_ok(label: str) -> bool:
    # An RFC 1123 host label: letters, digits and '-', not at either end, 1-63 characters.
    if not 0 < len(label) <= _MAX_LABEL or label[0] == "-" or label[-1] == "-":
        return False
    return all("0" <= ch <= "9" or "A" <= ch <= "Z" or "a" <= ch <= "z" or ch == "-" for ch in label)


def _put_fixed(buf: "Buf", first: int, remaining: int) -> int:
    # Writes the fixed header and returns its length, or -1 when the header and body cannot fit.
    size = 2 if remaining < _LEN_1_BYTE else 3 if remaining < _LEN_2_BYTES else 4 if remaining < _LEN_3_BYTES else 5
    if remaining > MAX_REMAINING or size + remaining > len(buf):
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
    # 1-23 bytes of letters, digits and '-': the set every broker accepts, plus the hostname's hyphen.
    return 0 < len(value) <= _MAX_CLIENT_ID and len(value.encode()) == len(value) and all(
        "0" <= ch <= "9" or "A" <= ch <= "Z" or "a" <= ch <= "z" or ch == "-" for ch in value
    )


def decode_remaining_length(buf: "Bytes", start: int, end: int) -> int:
    # The remaining length whose bytes start at buf[start] (section 2.2.3), LENGTH_INCOMPLETE when buf[start:end]
    # holds only part of it, LENGTH_MALFORMED past four bytes. A non-minimal encoding is read as written.
    value = 0
    shift = 0
    for i in range(start, min(end, start + 4)):
        byte = buf[i]
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value
        shift += 7
    return LENGTH_MALFORMED if end >= start + 4 else LENGTH_INCOMPLETE


def encode_connect(buf: "Buf", client_id: "Bytes", keepalive_s: int, will_topic: "Bytes", will_message: "Bytes", user: "Bytes", password: "Bytes") -> int:
    # Clean session, will at QoS 1 retained (section 3.1); user and password only when non-empty, a password
    # never without a user (section 3.1.2.9). Returns the packet length, or -1 when it does not fit.
    flags = _FLAG_CLEAN | _FLAG_WILL | _FLAG_WILL_QOS1 | _FLAG_WILL_RETAIN
    remaining = 10 + 2 + len(client_id) + 2 + len(will_topic) + 2 + len(will_message)
    if user:
        flags |= _FLAG_USER
        remaining += 2 + len(user)
        if password:
            flags |= _FLAG_PASSWORD
            remaining += 2 + len(password)
    i = _put_fixed(buf, CONNECT, remaining)
    if i < 0:
        return -1
    i = _put_str(buf, i, b"MQTT")
    buf[i] = _PROTOCOL_LEVEL
    buf[i + 1] = flags
    buf[i + 2] = (keepalive_s >> 8) & 0xFF
    buf[i + 3] = keepalive_s & 0xFF
    i = _put_str(buf, i + 4, client_id)
    i = _put_str(buf, i, will_topic)
    i = _put_str(buf, i, will_message)
    if flags & _FLAG_USER:
        i = _put_str(buf, i, user)
    if flags & _FLAG_PASSWORD:
        i = _put_str(buf, i, password)
    return i


def encode_puback(buf: "Buf", pid: int) -> int:
    # A PUBACK (section 3.4) into a buffer of at least four bytes.
    buf[0] = PUBACK
    buf[1] = 2
    buf[2] = pid >> 8
    buf[3] = pid & 0xFF
    return 4


def encode_publish(buf: "Buf", topic: "Bytes", payload: "Bytes", qos: int, pid: int, *, retain: bool, dup: bool) -> int:
    # A PUBLISH (section 3.3); the packet id is written only at QoS 1. Returns the length, or -1.
    first = PUBLISH | (qos << 1) | (_PUBLISH_RETAIN if retain else 0) | (_PUBLISH_DUP if dup and qos else 0)
    remaining = 2 + len(topic) + (2 if qos else 0) + len(payload)
    i = _put_fixed(buf, first, remaining)
    if i < 0:
        return -1
    i = _put_str(buf, i, topic)
    if qos:
        buf[i] = pid >> 8
        buf[i + 1] = pid & 0xFF
        i += 2
    buf[i : i + len(payload)] = payload
    return i + len(payload)


def encode_subscribe(buf: "Buf", pid: int, filters: tuple[bytes, ...]) -> int:
    # One SUBSCRIBE (section 3.8) requesting QoS 1 for every filter. Returns the length, or -1.
    if not filters:
        return -1
    i = _put_fixed(buf, SUBSCRIBE, 2 + sum(3 + len(f) for f in filters))
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


def host_ok(value: str) -> bool:
    # A broker address: a dotted-quad IPv4 literal or dot-separated host labels, at most 253 bytes.
    if not 0 < len(value.encode()) <= _MAX_HOST or len(value.encode()) != len(value):
        return False
    parts = value.split(".")
    if len(parts) == _IPV4_PARTS and all(p.isdigit() for p in parts):
        return all(len(p) <= _OCTET_DIGITS and int(p) <= _OCTET_MAX for p in parts)
    return all(_label_ok(p) for p in parts)


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
