"""PROTOTYPE MQTT 3.1.1 client (QoS 0/1, clean session, plain TCP) for the PoC's twin torture try - not src/ code.
One keeper task owns writes, pings, deadlines and reconnects; one reader task per connection owns reads; neither is
cancelled alone (mqtt_poc/RESEARCH.md section 4 fact 5). Buffers are allocated once; the idle path allocates nothing."""

import asyncio
import errno
import json
import socket
import struct
from time import ticks_diff, ticks_ms

from asy_dns_client import resolve_ipv4
from asy_print_log import PrintLogHistory
from micropython import const

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any, Callable

_CONNECT = const(0x10)
_CONNACK = const(0x20)
_PUBLISH = const(0x30)
_PUBACK = const(0x40)
_SUBSCRIBE = const(0x82)
_SUBACK = const(0x90)
_PINGREQ = const(0xC0)
_PINGRESP = const(0xD0)
_DISCONNECT = const(0xE0)
_COUNTER_CAP = const(0x3FFFFFFF)  # counters stop at 2**30 - 1 (project rule: small ints, never a heap int)
_EINPROGRESS = getattr(errno, "EINPROGRESS", 115)
_SLOT_FREE = const(0)
_SLOT_QUEUED = const(1)
_SLOT_INFLIGHT = const(2)

# Teardown reasons, kept as ints so a reason costs no allocation; _REASONS maps them for the status line.
_R_NONE = const(0)
_R_READER = const(1)
_R_LINK = const(2)
_R_PING = const(3)
_R_BACKLOG = const(4)
_R_DRAIN = const(5)
_R_PROTOCOL = const(6)
_R_IO = const(7)
_REASONS = ("none", "reader", "link", "ping", "backlog", "drain", "protocol", "io")


class MqttConfig:
    # Plain attribute bag; the real module would take a generated namedtuple (NtpTiming shape).
    def __init__(self, host: str, port: int = 1883, client_id: str = "dev", prefix: str = "sensors", user: str = "", password: str = "") -> None:
        self.host = host
        self.port = port
        self.client_id = client_id
        self.prefix = prefix
        self.user = user
        self.password = password
        self.keepalive_s = 30
        self.ping_interval_ms = 10000
        self.response_timeout_ms = 5000
        self.connect_timeout_ms = 5000
        self.tick_ms = 100
        self.backoff_min_ms = 2000
        self.backoff_max_ms = 30000
        self.stable_after_ms = 15000
        self.link_poll_ms = 1000
        self.rx_buf = 1024
        self.tx_buf = 640
        self.out_slots = 16
        self.out_payload_max = 512
        self.max_out_backlog = 2048
        self.drain_timeout_ms = 3000
        self.qos1_retry_ms = 5000
        self.qos1_max_tries = 3


class MQTTClient:
    def __init__(self, cfg: MqttConfig, wifi_mode_lock: "asyncio.Lock", network_available_locked: "Callable[[], bool]", get_dns_server: "Callable[[], str | None]") -> None:
        self.cfg = cfg
        self.pr = PrintLogHistory(level=4, name="MQTT")
        self._lock = wifi_mode_lock
        self._net_ok = network_available_locked
        self._get_dns = get_dns_server
        self._rx = bytearray(cfg.rx_buf)
        self._rxmv = memoryview(self._rx)
        self._rx_len = 0
        self._discard = 0
        self._tx = bytearray(cfg.tx_buf)
        self._txmv = memoryview(self._tx)
        self._ack = bytearray(4)
        n = cfg.out_slots
        self._out_buf = [bytearray(cfg.out_payload_max) for _ in range(n)]
        self._out_len = [0] * n
        self._out_topic: list[str | bytes | None] = [None] * n
        self._out_qos = [0] * n
        self._out_retain = [False] * n
        self._out_state = [_SLOT_FREE] * n
        self._out_seq = [0] * n
        self._out_pid = [0] * n
        self._out_sent = [0] * n
        self._out_tries = [0] * n
        self._seq = 0
        self._pid = 0
        base = cfg.prefix + "/" + cfg.client_id
        self.status_topic = base + "/status"
        self.cmd_filter = base + "/cmd/#"
        self._subs: list[tuple[str, int]] = [(self.cmd_filter, 1)]
        self._handlers: list[tuple[bytes, Callable[[memoryview, memoryview, bool], None]]] = []
        self._stream: Any = None
        self._connected = False
        self._reader_failed = False
        self._ping_out = False
        self._ping_sent = 0
        self._last_ping = 0
        self._connected_at = 0
        self._backoff_ms = cfg.backoff_min_ms
        self._subscribed = False
        self._last_err = ""
        self._link_ok_last = True
        self._last_link_check = 0
        self.c = {k: 0 for k in ("connects", "connect_fail", "teardowns", "pub_tx", "pub_drop", "pub_ack", "pub_retx", "pub_giveup", "rx_pub", "rx_oversize", "rx_qos1", "pings", "ping_timeouts", "link_down_waits", "suback_fail", "handler_err", "proto_err", "dns_fail")}
        self.last_reason = "none"

    # ---- public API ----

    def add_handler(self, topic_filter: str, handler: "Callable[[memoryview, memoryview, bool], None]") -> None:
        self._handlers.append((topic_filter.encode(), handler))

    def publish(self, topic: "str | bytes", payload: "bytes | bytearray | memoryview | str", qos: int = 0, retain: bool = False) -> bool:
        # Never blocks and never raises on load: copies into a free slot, or answers False (counted).
        data = payload.encode() if isinstance(payload, str) else payload
        if len(data) > self.cfg.out_payload_max or qos not in (0, 1) or (qos == 0 and not self._connected):
            self._bump("pub_drop")
            return False
        i = self._free_slot(qos)
        if i < 0:
            self._bump("pub_drop")
            return False
        self._out_buf[i][0 : len(data)] = data
        self._out_len[i] = len(data)
        self._out_topic[i] = topic
        self._out_qos[i] = qos
        self._out_retain[i] = retain
        self._out_tries[i] = 0
        self._seq = (self._seq + 1) & _COUNTER_CAP
        self._out_seq[i] = self._seq
        self._out_state[i] = _SLOT_QUEUED
        return True

    def is_connected(self) -> bool:
        return self._connected

    def get_status(self) -> "dict[str, Any]":
        d = dict(self.c)
        d["connected"] = self._connected
        d["backoff_ms"] = self._backoff_ms
        d["queued"] = sum(1 for s in self._out_state if s != _SLOT_FREE)
        d["last_reason"] = self.last_reason
        d["last_err"] = self._last_err
        return d

    async def run(self) -> None:
        # The one supervised task: never ends on a remote fault (SPEC C.7.2); every exit path closes the socket.
        while True:
            if not await self._wait_link():
                await asyncio.sleep_ms(self.cfg.link_poll_ms)
                continue
            reason = _R_NONE
            reader = None
            try:
                if await self._open():
                    reader = asyncio.create_task(self._reader())
                    reason = await self._serve()
            except asyncio.CancelledError:
                self._try_write_disconnect()
                raise
            except OSError as e:
                self._last_err = repr(e)
                reason = _R_IO
            except Exception as e:  # noqa: BLE001 - a remote or local fault must never end this task
                self._last_err = repr(e)
                self._bump("proto_err")
                reason = _R_PROTOCOL
            finally:
                if reader is not None:
                    reader.cancel()
                    try:
                        await reader
                    except BaseException:  # noqa: BLE001 - the reader's own end, whatever it was
                        pass
                await self._close()
            if reason != _R_NONE:
                self.last_reason = _REASONS[reason]
                self._bump("teardowns")
                self.pr.evt("connection down:", _REASONS[reason], self._last_err)
            if reason == _R_LINK:
                continue  # a link outage is waited out, not backed off
            await self._backoff()

    # ---- connection lifecycle ----

    async def _wait_link(self) -> bool:
        async with self._lock:  # waiting here is fine: nothing is connected
            try:
                ok = self._net_ok()
            except Exception:  # noqa: BLE001 - caller-supplied callback
                ok = False
        if not ok and self._link_ok_last:
            self._bump("link_down_waits")
        self._link_ok_last = ok
        return ok

    async def _link_still_up(self) -> bool:
        if self._lock.locked():
            return True  # WifiService busy: no news; the ping deadline covers a silent loss
        async with self._lock:
            try:
                return self._net_ok()
            except Exception:  # noqa: BLE001
                return False

    async def _open(self) -> bool:
        dns = self._get_dns()
        ip = await resolve_ipv4(self.cfg.host, () if dns is None else (dns,))
        if ip is None:
            self._bump("dns_fail")
            self._last_err = "dns"
            return False
        addr = socket.getaddrinfo(ip, self.cfg.port)[0][-1]  # numeric host only: no DNS query (SPEC F.2)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(False)
        self._stream = asyncio.StreamReader(s)
        try:
            s.connect(addr)
        except OSError as e:
            if e.errno != _EINPROGRESS:
                return self._fail_connect(e)
        try:
            self._stream.write(self._txmv[: self._enc_connect()])
            await asyncio.wait_for_ms(self._stream.drain(), self.cfg.connect_timeout_ms)
            self._rx_len = 0
            self._discard = 0
            while self._rx_len < 4:
                n = await asyncio.wait_for_ms(self._stream.readinto(self._rxmv[self._rx_len :]), self.cfg.response_timeout_ms)
                if not n:
                    return self._fail_connect(OSError("closed before CONNACK"))
                self._rx_len += n
        except (OSError, asyncio.TimeoutError) as e:
            return self._fail_connect(e)
        if self._rx[0] != _CONNACK or self._rx[1] != 2 or self._rx[3] != 0:
            return self._fail_connect(OSError("CONNACK refused rc=%d" % self._rx[3]))
        self._compact(4)
        self._connected = True
        self._connected_at = ticks_ms()
        self._last_ping = self._connected_at
        self._ping_out = False
        self._reader_failed = False
        self._subscribed = False
        self._bump("connects")
        self.pr.evt("connected to", ip, "after backoff", self._backoff_ms)
        self._requeue_inflight()
        self.publish(self.status_topic, b"online", qos=1, retain=True)
        return True

    def _fail_connect(self, e: "BaseException") -> bool:
        self._last_err = repr(e)
        self._bump("connect_fail")
        return False

    async def _close(self) -> None:
        self._connected = False
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                await stream.wait_closed()  # Stream.close() is a no-op (RESEARCH.md section 4 fact 4)
            except OSError:
                pass

    async def _backoff(self) -> None:
        await asyncio.sleep_ms(self._backoff_ms)
        self._backoff_ms = min(self._backoff_ms * 2, self.cfg.backoff_max_ms)

    def _try_write_disconnect(self) -> None:
        if self._stream is not None and self._connected:
            try:
                self._stream.write(b"\xe0\x00")
            except OSError:
                pass

    # ---- serving ----

    async def _serve(self) -> int:
        cfg = self.cfg
        while True:
            await asyncio.sleep_ms(cfg.tick_ms)  # sleep_ms allocates nothing
            if self._reader_failed:
                return _R_READER
            now = ticks_ms()
            if ticks_diff(now, self._last_link_check) >= cfg.link_poll_ms:
                self._last_link_check = now
                if not await self._link_still_up():  # once a second: the lock round trip allocates
                    return _R_LINK
            if not self._subscribed:
                self._write(self._enc_subscribe())
                self._subscribed = True
            if self._ping_out:
                if ticks_diff(now, self._ping_sent) > cfg.response_timeout_ms:
                    self._bump("ping_timeouts")
                    self._last_err = "no PINGRESP"
                    return _R_PING
            elif ticks_diff(now, self._last_ping) >= cfg.ping_interval_ms:
                self._tx[0] = _PINGREQ
                self._tx[1] = 0
                self._write(2)
                self._ping_out = True
                self._ping_sent = now
                self._last_ping = now
                self._bump("pings")
            self._flush_out(now)
            out = self._stream.out_buf
            if len(out) > cfg.max_out_backlog:
                self._last_err = "send backlog %d" % len(out)
                return _R_BACKLOG
            if out:
                try:
                    await asyncio.wait_for_ms(self._stream.drain(), cfg.drain_timeout_ms)
                except asyncio.TimeoutError:
                    self._last_err = "drain timeout"
                    return _R_DRAIN
            if self._backoff_ms != cfg.backoff_min_ms and ticks_diff(now, self._connected_at) > cfg.stable_after_ms and not self._ping_out:
                self._backoff_ms = cfg.backoff_min_ms  # reset only once the link proved stable: a flapping peer cannot drive a fast loop

    def _write(self, n: int) -> None:
        self._stream.write(self._txmv[:n])  # writes straight through, or queues behind an unfinished drain

    def _flush_out(self, now: int) -> None:
        cfg = self.cfg
        for _ in range(cfg.out_slots):
            i = self._oldest(_SLOT_QUEUED)
            if i < 0:
                break
            self._send_slot(i, dup=False)
            if self._out_qos[i] == 0:
                self._out_state[i] = _SLOT_FREE
            else:
                self._out_state[i] = _SLOT_INFLIGHT
                self._out_sent[i] = now
            self._bump("pub_tx")
        for i in range(cfg.out_slots):
            if self._out_state[i] == _SLOT_INFLIGHT and ticks_diff(now, self._out_sent[i]) > cfg.qos1_retry_ms:
                if self._out_tries[i] >= cfg.qos1_max_tries:
                    self._out_state[i] = _SLOT_FREE
                    self._bump("pub_giveup")
                else:
                    self._send_slot(i, dup=True)
                    self._out_sent[i] = now
                    self._bump("pub_retx")

    def _send_slot(self, i: int, *, dup: bool) -> None:
        if self._out_tries[i] == 0 or not dup:
            self._pid = self._pid % 65535 + 1
            self._out_pid[i] = self._pid
        self._out_tries[i] += 1
        n = self._enc_publish(i, dup=dup)
        self._write(n)

    def _requeue_inflight(self) -> None:
        # Clean session: the broker forgot every in-flight id, so unacknowledged QoS 1 messages go again as new.
        for i in range(self.cfg.out_slots):
            if self._out_state[i] == _SLOT_INFLIGHT:
                self._out_state[i] = _SLOT_QUEUED
                self._out_tries[i] = 0
            elif self._out_state[i] == _SLOT_QUEUED and self._out_qos[i] == 0:
                self._out_state[i] = _SLOT_FREE

    # ---- reader ----

    async def _reader(self) -> None:
        try:
            while True:
                if self._rx_len >= len(self._rx):
                    self._last_err = "rx buffer full"
                    break
                n = await self._stream.readinto(self._rxmv[self._rx_len :])
                if n is None:
                    continue
                if n == 0:
                    self._last_err = "EOF from broker"
                    break
                if self._discard:
                    if n <= self._discard:
                        self._discard -= n
                        continue
                    self._rx[0 : n - self._discard] = self._rxmv[self._discard : n]
                    n -= self._discard
                    self._discard = 0
                self._rx_len += n
                if not self._parse():
                    break
        except OSError as e:
            self._last_err = repr(e)
        self._reader_failed = True

    def _parse(self) -> bool:
        while self._rx_len >= 2:
            rem, hdr = self._decode_len()
            if rem < 0:
                return hdr == 0  # hdr 0: incomplete length bytes; -1: malformed
            total = hdr + rem
            if total > len(self._rx):
                self._bump("rx_oversize")
                self._discard = total - self._rx_len
                self._rx_len = 0
                return True
            if self._rx_len < total:
                return True
            if not self._handle(hdr, total):
                return False
            self._compact(total)
        return True

    def _decode_len(self) -> "tuple[int, int]":
        mult, value, i = 1, 0, 1
        while i < 5:
            if i >= self._rx_len:
                return -1, 0
            b = self._rx[i]
            value += (b & 0x7F) * mult
            i += 1
            if not b & 0x80:
                return value, i
            mult *= 128
        self._bump("proto_err")
        return -1, -1

    def _compact(self, used: int) -> None:
        left = self._rx_len - used
        if left > 0:
            self._rx[0:left] = self._rxmv[used : self._rx_len]
        self._rx_len = left

    def _handle(self, hdr: int, total: int) -> bool:
        b0 = self._rx[0]
        kind = b0 & 0xF0
        if kind == _PUBLISH:
            return self._on_publish(b0, hdr, total)
        if kind == _PUBACK:
            pid = (self._rx[hdr] << 8) | self._rx[hdr + 1]
            for i in range(self.cfg.out_slots):
                if self._out_state[i] == _SLOT_INFLIGHT and self._out_pid[i] == pid:
                    self._out_state[i] = _SLOT_FREE
                    self._bump("pub_ack")
                    break
            return True
        if kind == _PINGRESP:
            self._ping_out = False
            return True
        if kind == _SUBACK:
            for j in range(hdr + 2, total):
                if self._rx[j] == 0x80:
                    self._bump("suback_fail")
            return True
        self._bump("proto_err")
        self._last_err = "unexpected packet 0x%02x" % b0
        return False

    def _on_publish(self, b0: int, hdr: int, total: int) -> bool:
        qos = (b0 >> 1) & 3
        tlen = (self._rx[hdr] << 8) | self._rx[hdr + 1]
        t0 = hdr + 2
        p0 = t0 + tlen
        if qos > 1 or p0 > total:
            self._bump("proto_err")
            self._last_err = "bad PUBLISH"
            return False
        if qos == 1:
            self._ack[0] = _PUBACK
            self._ack[1] = 2
            self._ack[2] = self._rx[p0]
            self._ack[3] = self._rx[p0 + 1]
            self._stream.write(self._ack)
            p0 += 2
            self._bump("rx_qos1")
        self._bump("rx_pub")
        topic = self._rxmv[t0 : t0 + tlen]
        payload = self._rxmv[p0:total]
        for flt, handler in self._handlers:
            if _topic_matches(flt, topic):
                try:
                    handler(topic, payload, bool(b0 & 1))
                except Exception:  # noqa: BLE001 - a consumer's fault must not end the reader (guarded dispatch, SPEC G.2)
                    self._bump("handler_err")
        return True

    # ---- encoders (into the preallocated tx buffer) ----

    def _enc_connect(self) -> int:
        cfg = self.cfg
        cid = cfg.client_id.encode()
        will_t = self.status_topic.encode()
        flags = 0x02 | 0x04 | 0x08 | 0x20  # clean session, will flag, will QoS 1, will retain
        body = 10 + 2 + len(cid) + 2 + len(will_t) + 2 + 7
        if cfg.user:
            flags |= 0x80
            body += 2 + len(cfg.user)
            if cfg.password:
                flags |= 0x40
                body += 2 + len(cfg.password)
        i = self._fixed(_CONNECT, body)
        self._tx[i : i + 6] = b"\x00\x04MQTT"
        self._tx[i + 6] = 4
        self._tx[i + 7] = flags
        struct.pack_into(">H", self._tx, i + 8, cfg.keepalive_s)
        i += 10
        i = self._put_str(i, cid)
        i = self._put_str(i, will_t)
        i = self._put_str(i, b"offline")
        if cfg.user:
            i = self._put_str(i, cfg.user.encode())
            if cfg.password:
                i = self._put_str(i, cfg.password.encode())
        return i

    def _enc_subscribe(self) -> int:
        body = 2 + sum(2 + len(t) + 1 for t, _ in self._subs)
        i = self._fixed(_SUBSCRIBE, body)
        self._pid = self._pid % 65535 + 1
        struct.pack_into(">H", self._tx, i, self._pid)
        i += 2
        for t, q in self._subs:
            i = self._put_str(i, t.encode())
            self._tx[i] = q
            i += 1
        return i

    def _enc_publish(self, s: int, *, dup: bool) -> int:
        t = self._out_topic[s]
        topic = t if isinstance(t, bytes) else t.encode()  # type: ignore[union-attr]  # pass bytes to avoid this copy
        qos = self._out_qos[s]
        n = self._out_len[s]
        body = 2 + len(topic) + (2 if qos else 0) + n
        b0 = _PUBLISH | (qos << 1) | (0x08 if dup else 0) | (1 if self._out_retain[s] else 0)
        i = self._fixed(b0, body)
        i = self._put_str(i, topic)
        if qos:
            struct.pack_into(">H", self._tx, i, self._out_pid[s])
            i += 2
        self._tx[i : i + n] = self._out_buf[s][:n]
        return i + n

    def _fixed(self, b0: int, rem: int) -> int:
        self._tx[0] = b0
        i = 1
        while True:
            b = rem & 0x7F
            rem >>= 7
            self._tx[i] = b | (0x80 if rem else 0)
            i += 1
            if not rem:
                return i

    def _put_str(self, i: int, s: "bytes") -> int:
        struct.pack_into(">H", self._tx, i, len(s))
        self._tx[i + 2 : i + 2 + len(s)] = s
        return i + 2 + len(s)

    # ---- slot bookkeeping ----

    def _free_slot(self, qos: int) -> int:
        for i in range(self.cfg.out_slots):
            if self._out_state[i] == _SLOT_FREE:
                return i
        oldest, best = -1, 0
        for i in range(self.cfg.out_slots):  # full: overwrite the oldest queued QoS 0, never a QoS 1
            if self._out_state[i] == _SLOT_QUEUED and self._out_qos[i] == 0 and (oldest < 0 or self._out_seq[i] < best):
                oldest, best = i, self._out_seq[i]
        if oldest >= 0:
            self._bump("pub_drop")
        return oldest

    def _oldest(self, state: int) -> int:
        oldest, best = -1, 0
        for i in range(self.cfg.out_slots):
            if self._out_state[i] == state and (oldest < 0 or self._out_seq[i] < best):
                oldest, best = i, self._out_seq[i]
        return oldest

    def _bump(self, key: str) -> None:
        v = self.c[key]
        if v < _COUNTER_CAP:
            self.c[key] = v + 1


def _topic_matches(flt: bytes, topic: memoryview) -> bool:
    # MQTT filter match ('+' one level, '#' the rest) without building any string.
    fi, ti, fn, tn = 0, 0, len(flt), len(topic)
    while fi < fn:
        c = flt[fi]
        if c == 0x23:  # '#'
            return True
        if c == 0x2B:  # '+'
            while ti < tn and topic[ti] != 0x2F:
                ti += 1
            fi += 1
            continue
        if ti >= tn or topic[ti] != c:
            return False
        fi += 1
        ti += 1
    return ti == tn



class MeasurementPublisher:
    # Owner decision 8.7: each module's measurements as JSON in the REST key scheme, one message per module.
    def __init__(self, client: MQTTClient, sources: "tuple[Any, ...]", interval_ms: int = 10000) -> None:
        self.client = client
        self.sources = sources
        self.interval_ms = interval_ms
        self._topics: dict[str, bytes] = {}
        self.published = 0
        self.errors = 0

    async def run(self) -> None:
        base = self.client.cfg.prefix + "/" + self.client.cfg.client_id + "/"
        while True:
            await asyncio.sleep_ms(self.interval_ms)
            if not self.client.is_connected():
                continue
            for src in self.sources:
                try:
                    data = await src.get_dict_data()
                    for name, values in data.items():
                        topic = self._topics.get(name)
                        if topic is None:
                            topic = (base + name).encode()
                            self._topics[name] = topic
                        if self.client.publish(topic, json.dumps(values)):
                            self.published += 1
                except Exception:  # noqa: BLE001 - one module's fault must not stop the others
                    self.errors += 1
