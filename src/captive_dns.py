# SPDX-FileCopyrightText: Copyright 2019 p-doyle (Micropython-DNSServer-Captive-Portal) - the
# DNSQuery class's packet parsing/building is a derivative of that project's main.py (identical
# field layout/byte values); see src/LICENSE-captive_dns and THIRD_PARTY_LICENSES.md. Changed here
# per Apache-2.0 §4(b): ported to asyncio/AsyUDPSocket, added type hints, PrintLogHistory-backed
# logging/errno reporting, off-subnet request filtering, recv-failure backoff, and the root-domain
# query fix (self._parsed_ok replacing the empty-domain sentinel).
# SPDX-License-Identifier: Apache-2.0

"""Captive-portal DNS spoofer for hotspot/AP mode. DNSServer.run() runs while the device broadcasts
its fallback hotspot; every on-subnet query gets a canned A-record pointing back at the AP's own IP, landing any client on the config page.
Malformed/off-subnet/truncated input is dropped, never raised.
"""

import asyncio

from micropython import const

from asy_udp_socket import AsyUDPSocket
from print_log import PrintLogHistory, make_logger

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_fram_manager import AsyFramManager

_NAME = const("DNSSRV")

# Backoff for a persistently-failing recvfrom() that returns (None, None) without ever raising
# (e.g. a bind() that never actually succeeded - see SPECIFICATION.md Part C.9's
# cascading-recovery-storm convention: this path previously looped at zero delay, measured at ~5
# wrn_s() lines/second continuously in a real end-to-end run). Distinct from the broad
# except-Exception backoff below, which already had its own flat 3s pause for a genuinely
# unexpected exception.
_RECV_FAIL_BACKOFF_INITIAL_S = const(0.5)
_RECV_FAIL_BACKOFF_MAX_S = const(5.0)
_RECV_FAIL_BACKOFF_MULTIPLIER = const(2)


def _ipv4_to_int(ip: str) -> int | None:
    # RFC 791 section 3.2 dotted-quad -> 32-bit big-endian form, for subnet math below. Never
    # raises for a malformed-but-str value; matches asy_dns_client.py's _is_ipv4_literal().
    parts = ip.split(".")
    if len(parts) != 4:
        return None
    octets = []
    for part in parts:
        if not part.isdigit() or not (0 <= int(part) <= 255):
            return None
        octets.append(int(part))
    a, b, c, d = octets
    return (a << 24) | (b << 16) | (c << 8) | d


class DNSServer:
    def __init__(
        self,
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        self.pr: PrintLogHistory = make_logger(fram, history_length, debug, _NAME)
        self.name = _NAME  # matches self.pr.name - the _ModuleLike registration shape
        # asy_webserver_service.py's registration lists key on (error_sources=).
        # mode="server" sockets receive from anyone - asy_udp_socket.py places source-address
        # trust on the caller. run() filters to the AP's own subnet before ever replying.
        self.udps = AsyUDPSocket(("0.0.0.0", 53), mode="server")

    async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:
        return await self.pr.get_log()

    async def reset_error_counter(self) -> None:
        await self.pr.reset()

    async def run(self, server_ip: str, netmask: str) -> None:
        netmask_int = _ipv4_to_int(netmask)
        server_int = _ipv4_to_int(server_ip)
        if netmask_int is None or server_int is None:
            # server_ip/netmask come from the OS's own wlan.ifconfig() - a startup misconfiguration,
            # not expected in normal operation, so it's worth a persisted errno.
            await self.pr.err_s("Invalid server_ip/netmask, not starting:", server_ip, netmask, errno=1)
            return
        network = server_int & netmask_int
        recv_fail_backoff_s = _RECV_FAIL_BACKOFF_INITIAL_S
        while True:
            try:
                self.pr.evt("Waiting for DNS request...")
                data, addr = await self.udps.recvfrom(4096)
                if data is not None and addr is not None:
                    recv_fail_backoff_s = _RECV_FAIL_BACKOFF_INITIAL_S  # socket is receiving fine again
                    try:
                        # addr[0] isn't guaranteed to be a str (confirmed: can come back as a
                        # plain int) - treated like off-subnet, not the outer except's 3s backoff.
                        addr_int = _ipv4_to_int(addr[0])
                    except Exception:
                        addr_int = None
                    on_subnet = addr_int is not None and (addr_int & netmask_int) == network
                    if not on_subnet:
                        self.pr.evt(f"Ignoring DNS request from off-subnet or malformed address {addr[0]!r}")
                        continue
                    self.pr.evt(f"Incoming DNS request from {addr[0]:s}:{addr[1]}...")
                    dns = DNSQuery(data, self.pr)
                    packet = dns.response(server_ip)
                    if packet is None:
                        self.pr.evt("Empty DNS query, not sending response.")
                    else:
                        sent = await self.udps.sendto(packet, addr)
                        if sent is None:
                            await self.pr.wrn_s(f"Reply to {addr[0]:s}:{addr[1]} dropped by sendto().", wrnno=1)
                        else:
                            self.pr.evt(f"Replying to {addr[0]:s}:{addr[1]}: {dns.domain:s} -> {server_ip:s}")
                else:  # data or address is None
                    await self.pr.wrn_s("Invalid DNS request data or address, not sending response.", wrnno=2)
                    await asyncio.sleep(recv_fail_backoff_s)
                    recv_fail_backoff_s = min(
                        recv_fail_backoff_s * _RECV_FAIL_BACKOFF_MULTIPLIER, _RECV_FAIL_BACKOFF_MAX_S
                    )

            except asyncio.CancelledError:
                self.pr.evt("DNS Server shutdown")
                break

            except Exception as e:
                # nothing supervises this task - never let an unexpected exception here kill it.
                await self.pr.err_s("DNS Server error:", e, errno=2)
                await asyncio.sleep(3)

        try:
            disconnect_ok = await self.udps.disconnect()
        except asyncio.CancelledError:
            # A second cancellation delivered while this cleanup await is in flight - already
            # shutting down, nothing more to do.
            disconnect_ok = True
        except Exception as e:
            # disconnect() is documented as never raising, but nothing supervises this task -
            # never let cleanup itself become the uncaught exception.
            await self.pr.err_s("DNS Server error during disconnect:", e, errno=3)
            disconnect_ok = True  # already logged above via the except-Exception branch
        if not disconnect_ok:
            # SPECIFICATION.md Part C.7's silent-failure-masking convention: disconnect() itself
            # never raises (AsyUDPSocket has no logger of its own by design), but its bool return now
            # reports whether unregister()/close() actually succeeded - log it here so a real
            # socket/poll-slot leak
            # over a long uptime leaves a trail instead of silently disappearing.
            await self.pr.wrn_s("DNS Server socket teardown did not complete cleanly.", wrnno=3)
        self.pr.evt("DNS Server disconnected.")


class DNSQuery:
    def __init__(self, data: bytes, pr: PrintLogHistory) -> None:
        self.data = data
        self.domain = ""
        self._question_end = 0  # set below once a full question is actually parsed
        # A root-domain query (a single zero-length label, ".") parses to the same empty
        # self.domain a truncated/malformed datagram falls back to - this flag is the only thing
        # that tells them apart, so response() can still answer a genuine root query (BACKLOG.md's
        # "can't be told apart from a failed parse" entry).
        self._parsed_ok = False
        self.pr = pr
        # RFC 1035 section 4.1.1/4.1.2: opcode is bits 3-6 of header byte 2; the question section
        # (a length-prefixed label sequence) starts at byte 12, right after the 12-byte header.
        try:
            tipo = (data[2] >> 3) & 15  # Opcode bits
            if tipo == 0:  # Standard query
                ini = 12
                lon = data[ini]
                while lon != 0:
                    self.domain += data[ini + 1 : ini + lon + 1].decode("utf-8") + "."
                    ini += lon + 1
                    lon = data[ini]
                # ini now points at the zero-length terminator; QTYPE+QCLASS (4 bytes) follow -
                # the end of the one question response() must echo, not the whole datagram.
                question_end = ini + 5
                if question_end > len(data):
                    # Bytes slicing would silently truncate rather than raise on a datagram that
                    # ends before QTYPE/QCLASS - raise explicitly into the "malformed" except below.
                    raise ValueError("truncated question: missing QTYPE/QCLASS")
                self._question_end = question_end
                self._parsed_ok = True
        except Exception:
            # Truncated/malformed data (or non-bytes data, since this class is public) - not a
            # usable standard query. Reuses the empty-domain sentinel, no raise into run().
            self.domain = ""
            self._parsed_ok = False
        self.pr.evt("DNSQuery domain:", self.domain)

    def response(self, ip: str) -> bytes | None:
        # RFC 1035 section 4.1.1/4.1.4: a synthesized "success, recursion available" header,
        # echoing the original question back with one compressed-pointer A-record answer.
        self.pr.evt("DNSQuery response:", self.domain, "==>", ip)
        if self._parsed_ok:
            # This method is public and shouldn't rely on run() only passing a validated
            # server_ip - a bad ip would otherwise build a corrupt packet (wrong RDATA length).
            if _ipv4_to_int(ip) is None:
                return None
            packet = self.data[:2] + b"\x81\x80"
            # QDCOUNT=1, ANCOUNT=1, NSCOUNT=0, ARCOUNT=0 - hardcoded, not echoed from the original
            # header: this class always parses/echoes exactly one question and one answer.
            packet += b"\x00\x01\x00\x01\x00\x00\x00\x00"
            packet += self.data[12 : self._question_end]  # the one echoed question, not the rest of the datagram
            packet += b"\xc0\x0c"  # Pointer to domain name
            packet += b"\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04"  # Response type, ttl and resource data length -> 4 bytes
            packet += bytes(map(int, ip.split(".")))  # 4bytes of IP
            return packet
        return None
