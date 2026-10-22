"""A local NTP server for twin and Unix-port runs (owner, 2026-10-02): answers each client request on loopback with the
host's UTC time, so a booted twin syncs without reaching a public host; its test knobs make it silent, unsynchronised,
malformed or implausible."""

import asyncio
import errno
import select
import socket
import struct
import time

# 1900 to 1970 in seconds (RFC 5905); a local copy, pinned to src/asy_ntp_client.py's by tests/test_digital_twin_ntp.py
_NTP_EPOCH_DELTA = 2208988800
# the project's counter cap (SPECIFICATION.md G.2), a local copy: this module imports nothing from digital_twin/
_COUNTER_CAP = 0x3FFFFFFF
_PACKET_LEN = 48  # RFC 5905 7.3: the header a request and a reply carry
_MODE_CLIENT = 3
_MODE_SERVER = 4
_VERSION = 3  # what the product's request carries (src/asy_ntp_client.py _NTP_REQUEST)
_LI_UNSYNCHRONIZED = 3
# Below the client's 2025 plausibility floor, and above its 2100 ceiling once the client reads it as the next NTP era.
_IMPLAUSIBLE_UNIX_S = 1000000000
# @tunable twin.ntp_responder_poll_ms = 10
_POLL_MS = 10
# @tunable twin.ntp_responder_take_rounds = 20
_TAKE_ROUNDS = 20  # a waiting responder tries the held port again every 20 rounds (200 ms)
_MODES = ("serve", "silent", "unsync", "short", "implausible")
_host_time = time.time  # bound at import: the runner's wall clock rebinds each module's `time`, never what this serves

TEST_API = ("mode", "offset_s")


def ntp_reply(unix_s: int, *, leap: int = 0, stratum: int = 1) -> bytes:
    # The 48-byte server reply: LI, version 3, mode 4, the stratum, and unix_s as the Transmit Timestamp's seconds.
    header = bytes(((leap << 6) | (_VERSION << 3) | _MODE_SERVER, stratum)) + bytes(38)
    return header + struct.pack("!I", (unix_s + _NTP_EPOCH_DELTA) & 0xFFFFFFFF) + bytes(4)


class NtpResponder:
    # One responder holds its port: bound without SO_REUSEADDR, a second one in the namespace is refused EADDRINUSE and
    # waits (holding False), taking the port in serve() once the holder closes it, so two never share a fixed port.
    def __init__(self, port: int, host: str = "127.0.0.1") -> None:
        self.port = port
        self.mode = "serve"  # twin-only test knob: one of _MODES
        self.offset_s = 0  # twin-only test knob: added to the served time, a server whose clock differs from the host's
        self.requests = 0  # client requests answered per mode, saturating at _COUNTER_CAP
        self.ignored = 0  # datagrams that were no 48-byte client request, saturating likewise
        self._addr = socket.getaddrinfo(host, port)[0][-1]  # a raw sockaddr: this build's bind() takes no tuple
        self._sock: socket.socket | None = None
        self._poller = select.poll()
        self._closed = False
        self.holding = self._take()

    def _reply(self) -> "bytes | None":
        if self.mode not in _MODES:
            raise ValueError(f"NtpResponder.mode {self.mode!r} - expected one of {_MODES}")
        now = int(_host_time()) + self.offset_s
        if self.mode == "silent":
            return None
        if self.mode == "unsync":
            return ntp_reply(now, leap=_LI_UNSYNCHRONIZED, stratum=0)
        if self.mode == "short":
            return ntp_reply(now)[: _PACKET_LEN - 1]
        if self.mode == "implausible":
            return ntp_reply(_IMPLAUSIBLE_UNIX_S)
        return ntp_reply(now)

    def _take(self) -> bool:
        # Binds the port if free; False when another socket holds it (any other bind failure raises).
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind(self._addr)
        except OSError as e:
            sock.close()
            if e.errno != errno.EADDRINUSE:
                raise
            return False
        sock.setblocking(False)
        self._poller.register(sock, select.POLLIN)
        self._sock = sock
        return True

    def close(self) -> None:
        self._closed = True
        if self._sock is not None:
            self._poller.unregister(self._sock)
            self._sock.close()
            self._sock = None
        self.holding = False

    async def serve(self) -> None:
        # One round per poll period, never blocking the loop and never waiting in a real poll with a timeout
        # (CLAUDE.md's bounded-poller rule); cancelled by its owner.
        rounds = 0
        while True:
            rounds += 1
            if not self.holding and not self._closed and rounds % _TAKE_ROUNDS == 0:
                self.holding = self._take()
            self.serve_one()
            await asyncio.sleep_ms(_POLL_MS)

    def serve_one(self) -> bool:
        # At most one datagram per call, never blocking: True when a client request was taken.
        # ipoll(0) returns an always-truthy iterator on this port - iterate and check the flags.
        if self._sock is None or not any(event & select.POLLIN for _obj, event in self._poller.ipoll(0)):
            return False
        try:
            data, addr = self._sock.recvfrom(_PACKET_LEN + 1)
        except OSError as e:
            if e.errno != errno.EAGAIN:  # a wake-up with nothing to read is the one expected miss
                raise
            return False
        if len(data) != _PACKET_LEN or data[0] & 0x07 != _MODE_CLIENT:
            self.ignored = self.ignored + 1 if self.ignored < _COUNTER_CAP else _COUNTER_CAP
            return False
        self.requests = self.requests + 1 if self.requests < _COUNTER_CAP else _COUNTER_CAP
        reply = self._reply()
        if reply is not None:
            self._sock.sendto(reply, addr)
        return True
