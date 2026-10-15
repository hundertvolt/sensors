# SPDX-FileCopyrightText: Copyright 2019 p-doyle (Micropython-DNSServer-Captive-Portal)
# SPDX-License-Identifier: Apache-2.0
# DNSQuery derives from its main.py - changes per Apache-2.0 SS4(b): THIRD_PARTY_LICENSES.md.

"""Captive-portal DNS spoofer for hotspot/AP mode. CaptiveDNS.run() runs while the device broadcasts
its fallback hotspot; every on-subnet A/ANY query gets a canned A record pointing back at the AP's own IP, any other type an empty NOERROR reply.
Malformed/off-subnet/truncated input is dropped, never raised.
"""

import asyncio

from micropython import const

from asy_dns_client import DNS_LABEL_MAX, DNS_NAME_MAX, DNS_QTYPE_A, DNS_UDP_MAX, ipv4_to_int
from asy_print_log import DEFAULT_LOG, PrintLogHistory, make_logger
from asy_udp_socket import UDPSocket

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:

    from asy_base_classes import ErrorSource
    from asy_print_log import ErrorLog, LogConfig

_NAME = const("DNSSRV")

_ERR_INIT = const(10)
_ERR_BAD_ARG = const(21)
_ERR_UNEXPECTED = const(23)
_WRN_SOCKET_TEARDOWN = const(12)
_WRN_DNS_REPLY_DROPPED = const(41)
_WRN_DNS_RECV_FAILED = const(42)

# Backoff for a persistently-failing recvfrom() that returns (None, None) without raising - e.g. a
# bind() that never succeeded. This path once looped at zero delay, measured at ~5 warning lines a
# second in a real run (Part C.9's cascading-recovery-storm convention).
# @tunable dns_server.recv_backoff_initial_s = 0.5
_RECV_FAIL_BACKOFF_INITIAL_S = const(0.5)
# @tunable dns_server.recv_backoff_max_s = 5.0
_RECV_FAIL_BACKOFF_MAX_S = const(5.0)
# @tunable dns_server.recv_backoff_mult = 2
_RECV_FAIL_BACKOFF_MULTIPLIER = const(2)
# @tunable dns_server.error_retry_wait_s = 3
_ERROR_RETRY_WAIT_S = const(3)  # the serve loop's pause after an unexpected exception

_QTYPE_ANY = const(b"\x00\xff")  # RFC 1035 SS3.2.3 QTYPE * (ANY)


class CaptiveDNS:
    def __init__(self, log: "LogConfig" = DEFAULT_LOG) -> None:
        self.pr: PrintLogHistory = make_logger(log, _NAME)
        self.name = _NAME  # matches self.pr.name - the _ModuleLike registration shape
        # asy_webserver_service.py's registration lists key on (error_sources=).
        # mode="server" sockets receive from anyone - asy_udp_socket.py places source-address
        # trust on the caller. run() filters to the AP's own subnet before ever replying.
        self._udps = UDPSocket(("0.0.0.0", 53), mode="server")

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    def get_error_sources(self) -> "list[ErrorSource]":
        # Fan-in primitive (SPECIFICATION.md Part C.14/G.2), same shape as asy_base_classes.py's
        # SensorReader.get_error_sources() - duck-typed, not inherited (see this module's own
        # docstring: it's owned by WifiService, not itself a SensorReader subclass).
        return [self]

    def get_loggers(self) -> list[PrintLogHistory]:
        return [self.pr]

    async def reset_error_counter(self) -> bool:
        return await self.pr.reset()

    async def run(self, server_ip: str, netmask: str) -> None:
        netmask_int = ipv4_to_int(netmask)
        server_int = ipv4_to_int(server_ip)
        if netmask_int is None or server_int is None:
            # server_ip/netmask come from the OS's own wlan.ifconfig() - a startup misconfiguration,
            # not expected in normal operation, so it's worth a persisted errno.
            await self.pr.err_s("Invalid server_ip/netmask, not starting:", server_ip, netmask, errno=_ERR_BAD_ARG)
            return
        network = server_int & netmask_int
        recv_fail_backoff_s = _RECV_FAIL_BACKOFF_INITIAL_S
        try:
            while True:
                try:
                    self.pr.evt("Waiting for DNS request...")
                    # lwIP queues at most 4 datagrams per UDP socket and drops the rest uncounted (extmod/modlwip.c:299, 456-461, v1.29.0);
                    # every queued one is read before _poll() sleeps, so a burst loses only what exceeds 4 per idle poll.
                    data, addr = await self._udps.recvfrom(DNS_UDP_MAX)
                    if data is not None and addr is not None:
                        recv_fail_backoff_s = _RECV_FAIL_BACKOFF_INITIAL_S  # socket is receiving fine again
                        # One yield per datagram: while a flood keeps the socket ready nothing below this loop yields (on rp2
                        # lwIP refills the queue from PendSV while Python runs), so without it no other task would get a turn.
                        await asyncio.sleep(0)
                        try:
                            # addr[0] isn't guaranteed to be a str (confirmed: can come back as a
                            # plain int) - treated like off-subnet, not the outer except's 3s backoff.
                            addr_int = ipv4_to_int(addr[0])
                        except MemoryError:
                            raise  # a heap failure is ours, not a malformed sender: the catch-all below persists it
                        except Exception:
                            addr_int = None
                        on_subnet = addr_int is not None and (addr_int & netmask_int) == network
                        if not on_subnet:
                            self.pr.evt("Ignoring DNS request from off-subnet or malformed address", addr[0])
                            continue
                        self.pr.evt("Incoming DNS request from", addr[0], addr[1])
                        dns = DNSQuery(data, self.pr)
                        packet = dns.response(server_ip)
                        if packet is None:
                            self.pr.evt("Empty DNS query, not sending response.")
                        else:
                            sent = await self._udps.sendto(packet, addr)
                            if sent is None:
                                await self.pr.wrn_s("Reply dropped by sendto() to", addr[0], addr[1], wrnno=_WRN_DNS_REPLY_DROPPED)
                            else:
                                self.pr.evt("Replying to", addr[0], addr[1], dns.domain, "->", server_ip)
                    else:
                        # (None, None) is local: the socket never bound, or the receive raised - never a client's datagram.
                        if not self._udps.connected:
                            await self.pr.err_s("Captive DNS socket could not bind port 53.", errno=_ERR_INIT)
                        else:
                            await self.pr.wrn_s("Receiving a DNS request failed.", wrnno=_WRN_DNS_RECV_FAILED)
                        await asyncio.sleep(recv_fail_backoff_s)
                        recv_fail_backoff_s = min(
                            recv_fail_backoff_s * _RECV_FAIL_BACKOFF_MULTIPLIER, _RECV_FAIL_BACKOFF_MAX_S,
                        )

                except Exception as e:
                    # nothing supervises this task - never let an unexpected exception here kill it.
                    await self.pr.err_s("DNS Server error:", e, errno=_ERR_UNEXPECTED)
                    await asyncio.sleep(_ERROR_RETRY_WAIT_S)

        finally:
            self.pr.evt("DNS Server shutdown")
            try:
                disconnect_ok = await self._udps.disconnect()
            except Exception as e:
                # disconnect() is documented as never raising, but nothing supervises this task -
                # never let cleanup itself become the uncaught exception.
                await self.pr.err_s("DNS Server error during disconnect:", e, errno=_ERR_UNEXPECTED)
                disconnect_ok = True  # already logged above via the except-Exception branch
            if not disconnect_ok:
                # Part C.7's silent-failure-masking convention: disconnect() never raises (UDPSocket
                # owns no logger), but its bool says whether unregister()/close() succeeded - logged here
                # so a real socket or poll-slot leak over a long uptime leaves a trail.
                await self.pr.wrn_s("DNS Server socket teardown did not complete cleanly.", wrnno=_WRN_SOCKET_TEARDOWN)
            self.pr.evt("DNS Server disconnected.")


class DNSQuery:
    def __init__(self, data: bytes, pr: PrintLogHistory) -> None:
        self._data = data
        self.domain = ""
        self._question_end = 0  # set below once a full question is actually parsed
        # A root-domain query (one zero-length label) parses to the same empty self.domain a
        # truncated datagram falls back to. This flag is the only thing telling them apart, so
        # response() can answer a genuine root query instead of treating it as a failed parse.
        self._parsed_ok = False
        self.pr = pr
        # RFC 1035 section 4.1.1/4.1.2: opcode is bits 3-6 of header byte 2; the question section
        # (a length-prefixed label sequence) starts at byte 12, right after the 12-byte header.
        try:
            if data[2] & 0x80 or data[4:6] != b"\x00\x01":
                raise ValueError("not a query with exactly one question")
            tipo = (data[2] >> 3) & 15  # Opcode bits
            if tipo == 0:  # Standard query
                ini = 12
                lon = data[ini]
                while lon != 0:
                    if lon > DNS_LABEL_MAX:
                        raise ValueError("label type or length not supported")
                    self.domain += data[ini + 1 : ini + lon + 1].decode("utf-8") + "."
                    ini += lon + 1
                    lon = data[ini]
                if ini - 11 > DNS_NAME_MAX:
                    raise ValueError("name longer than 255 octets")
                # ini now points at the zero-length terminator; QTYPE+QCLASS (4 bytes) follow -
                # the end of the one question response() must echo, not the whole datagram.
                question_end = ini + 5
                if question_end > len(data):
                    # Bytes slicing would silently truncate rather than raise on a datagram that
                    # ends before QTYPE/QCLASS - raise explicitly into the "malformed" except below.
                    raise ValueError("truncated question: missing QTYPE/QCLASS")
                self._question_end = question_end
                self._parsed_ok = True
        except MemoryError:
            raise  # a heap failure is ours, not the client's: run() persists it rather than dropping a "malformed" query
        except Exception:
            # Truncated/malformed data (or non-bytes data, since this class is public) - not a
            # usable standard query. Reuses the empty-domain sentinel, no raise into run().
            self.domain = ""
            self._parsed_ok = False
        self.pr.evt("DNSQuery domain:", self.domain)

    def response(self, ip: str) -> bytes | None:
        # RFC 1035 section 4.1.1/4.1.4: a synthesized "success, recursion available" header,
        # echoing the original question back with one compressed-pointer A-record answer for A/ANY.
        self.pr.evt("DNSQuery response:", self.domain, "==>", ip)
        if self._parsed_ok:
            # This method is public and shouldn't rely on run() only passing a validated
            # server_ip - a bad ip would otherwise build a corrupt packet (wrong RDATA length).
            if ipv4_to_int(ip) is None:
                return None
            qtype = self._data[self._question_end - 4 : self._question_end - 2]
            # RFC 1035 / RFC 2308 2.2: an A or ANY query gets the A record, any other type NOERROR with no answer (NODATA) (owner, 2026-09-29).
            answer = qtype in (DNS_QTYPE_A, _QTYPE_ANY)
            packet = self._data[:2] + b"\x81\x80"
            # QDCOUNT=1 (the one parsed question); ANCOUNT=1 only for an A/ANY query
            packet += b"\x00\x01\x00\x01\x00\x00\x00\x00" if answer else b"\x00\x01\x00\x00\x00\x00\x00\x00"
            packet += self._data[12 : self._question_end]  # the one echoed question, not the rest of the datagram
            if answer:
                packet += b"\xc0\x0c"  # Pointer to domain name
                packet += b"\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04"  # Response type, ttl and resource data length -> 4 bytes
                packet += bytes(map(int, ip.split(".")))  # 4bytes of IP
            return packet
        return None
