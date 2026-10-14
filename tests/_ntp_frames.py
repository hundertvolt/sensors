"""The NTP test frames: make_ntp_reply() builds a synchronized server's 48-byte reply (RFC 5905: LI 0, VN 3, mode 4,
stratum 1, the Transmit Timestamp's seconds at offset 40), and FakeNtpServer answers one request on a loopback UDP port
the caller owns, as a real independent socket, not the product's UDPSocket."""

import asyncio
import errno
import select
import socket
import struct

from _src_const import NTP_EPOCH_DELTA


class FakeNtpServer:
    # The product sends to port 123, which needs root: a test points it here (tests/_udp_port_redirect.py). The poll
    # budget is the caller's: `poll_tries` rounds of `poll_ms` before serve_once() gives up on a request.
    def __init__(self, port: int, *, poll_ms: int, poll_tries: int) -> None:
        self.port = port
        self._poll_ms = poll_ms
        self._poll_tries = poll_tries
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(socket.getaddrinfo("127.0.0.1", port)[0][-1])  # a raw socket: this build's bind() takes the sockaddr
        self.sock.setblocking(False)
        self.poller = select.poll()
        self.poller.register(self.sock, select.POLLIN)

    def close(self) -> None:
        self.sock.close()

    async def serve_once(self, reply: "bytes | None") -> None:
        # Answers exactly one request with `reply`; None takes the request and never answers it.
        for _ in range(self._poll_tries):
            # ipoll(0) returns an always-truthy iterator on this port - iterate and check the flags.
            if any(event & select.POLLIN for _obj, event in self.poller.ipoll(0)):
                try:
                    _data, from_addr = self.sock.recvfrom(1024)
                except OSError as e:
                    if e.errno != errno.EAGAIN:  # only a wake-up with nothing to read is expected; anything else is the rig failing
                        raise
                    await asyncio.sleep_ms(self._poll_ms)
                    continue
                if reply is not None:
                    self.sock.sendto(reply, from_addr)
                return
            await asyncio.sleep_ms(self._poll_ms)


def make_ntp_reply(unix_seconds: int) -> bytes:
    header = b"\x1c\x01" + bytes(38)  # LI=0/VN=3/Mode=4 (server), Stratum=1 (synchronized), Poll..Receive Timestamp zeroed
    return header + struct.pack("!I", (unix_seconds + NTP_EPOCH_DELTA) & 0xFFFFFFFF) + bytes(4)  # seconds, zeroed fraction
