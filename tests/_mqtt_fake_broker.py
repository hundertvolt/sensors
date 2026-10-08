"""A scripted MQTT 3.1.1 broker for tests/test_asy_mqtt_client.py, on a real loopback socket (asyncio.start_server):
it records every packet the client sends and answers by its flags, so a test can produce the faults a real broker only
shows on demand - a refused CONNACK, a missing PINGRESP or PUBACK, a malformed length, an oversize PUBLISH, a stall."""

import asyncio

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Protocol

    class _Server(Protocol):
        def close(self) -> None: ...
        async def wait_closed(self) -> None: ...


def read_str(body: bytes, i: int) -> "tuple[bytes, int]":
    n = (body[i] << 8) | body[i + 1]
    return body[i + 2 : i + 2 + n], i + 2 + n


def publish_packet(topic: bytes, payload: bytes, qos: int = 0, pid: int = 1, *, retain: bool = False) -> bytes:
    body = bytes([len(topic) >> 8, len(topic) & 0xFF]) + topic + (bytes([pid >> 8, pid & 0xFF]) if qos else b"") + payload
    return bytes([0x30 | (qos << 1) | (1 if retain else 0)]) + encode_length(len(body)) + body


def encode_length(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | 0x80 if value else byte)
        if not value:
            return bytes(out)


class FakeBroker:
    def __init__(self, port: int) -> None:
        self.port = port
        self.connects: list[dict[str, bytes | int]] = []
        self.packets: list[tuple[int, bytes]] = []  # (first byte, body) of every packet the client sent
        self.connack_rc: int | None = 0  # None: never answer CONNECT
        self.answer_pings = True
        self.ack_publishes = True
        self.suback_code = 1
        self.close_after_connack = False
        self.stop_reading = False  # after the CONNACK, never read again (the broker stalls)
        self.after_subscribe: list[bytes] = []  # raw packets sent once the SUBACK is out
        self.connections = 0
        self.disconnects = 0  # DISCONNECT packets received
        self.closed_by_client = 0  # EOFs seen
        self._writers: list[asyncio.StreamWriter] = []
        self._server: _Server | None = None

    async def _client(self, reader: "asyncio.StreamReader", writer: "asyncio.StreamWriter") -> None:
        self.connections += 1
        self._writers.append(writer)
        try:
            while True:
                first = (await reader.readexactly(1))[0]
                value = 0
                shift = 0
                while True:
                    byte = (await reader.readexactly(1))[0]
                    value |= (byte & 0x7F) << shift
                    shift += 7
                    if not byte & 0x80:
                        break
                body = await reader.readexactly(value) if value else b""
                self.packets.append((first, body))
                if not await self._react(first, body, writer):
                    break
        except (EOFError, OSError):
            self.closed_by_client += 1
        finally:
            if writer in self._writers:
                self._writers.remove(writer)
            try:
                await writer.wait_closed()
            except OSError:
                pass

    async def _react(self, first: int, body: bytes, writer: "asyncio.StreamWriter") -> bool:
        # False ends this connection from the broker's side.
        kind = first & 0xF0
        if kind == 0x10:
            client_id, i = read_str(body, 10)
            flags = body[7]
            will_topic, i = read_str(body, i)
            will_message, i = read_str(body, i)
            user = password = b""
            if flags & 0x80:
                user, i = read_str(body, i)
            if flags & 0x40:
                password, i = read_str(body, i)
            self.connects.append({"client_id": client_id, "flags": flags, "keepalive": (body[8] << 8) | body[9], "will_topic": will_topic, "will_message": will_message, "user": user, "password": password})
            if self.connack_rc is None:
                return True
            writer.write(bytes([0x20, 2, 0, self.connack_rc]))
            await writer.drain()
            if self.close_after_connack or self.connack_rc:
                return False
            while self.stop_reading:
                await asyncio.sleep_ms(50)
            return True
        if kind == 0x80:
            filters = 0
            i = 2
            while i < len(body):
                _flt, i = read_str(body, i)
                i += 1
                filters += 1
            writer.write(bytes([0x90, 2 + filters, body[0], body[1]] + [self.suback_code] * filters))
            for packet in self.after_subscribe:
                writer.write(packet)
            await writer.drain()
            return True
        if kind == 0x30:
            qos = (first >> 1) & 3
            if qos and self.ack_publishes:
                tlen = (body[0] << 8) | body[1]
                writer.write(bytes([0x40, 2, body[2 + tlen], body[3 + tlen]]))
                await writer.drain()
            return True
        if kind == 0xC0:
            if self.answer_pings:
                writer.write(b"\xd0\x00")
                await writer.drain()
            return True
        if kind == 0xE0:
            self.disconnects += 1
            return False
        return True

    def published(self, topic: bytes) -> "list[tuple[int, bytes]]":
        # (first byte, payload) of every PUBLISH the client sent to `topic`.
        found = []
        for first, body in self.packets:
            if first & 0xF0 == 0x30:
                t, i = read_str(body, 0)
                if t == topic:
                    found.append((first, body[i + (2 if (first >> 1) & 3 else 0) :]))
        return found

    async def send(self, packet: bytes) -> None:
        for writer in list(self._writers):
            writer.write(packet)
            await writer.drain()

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._client, "127.0.0.1", self.port)

    async def stop(self) -> None:
        for writer in list(self._writers):
            try:
                await writer.wait_closed()
            except OSError:
                pass
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
