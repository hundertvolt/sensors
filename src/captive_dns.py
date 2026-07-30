"""Captive-portal DNS spoofer for hotspot/AP mode. Called only by async_connect.py's
DNSServer.run() while the device broadcasts its fallback hotspot; every on-subnet query gets a
canned A-record pointing back at the AP's own IP, landing any client on the config page.

Malformed/off-subnet/truncated input is dropped, never raised - see BACKLOG.md for the full
design rationale and review history.
"""

import asyncio

from asy_udp_socket import AsyUDPSocket


def _ipv4_to_int(ip: str) -> int:
    # RFC 791 section 3.2 dotted-quad -> its 32-bit big-endian form, for subnet math below.
    a, b, c, d = (int(octet) for octet in ip.split("."))
    if not (0 <= a <= 255 and 0 <= b <= 255 and 0 <= c <= 255 and 0 <= d <= 255):
        raise ValueError(f"octet out of range: {ip!r}")
    return (a << 24) | (b << 16) | (c << 8) | d


class DNSServer:
    def __init__(self, debug: bool = False) -> None:
        # mode="server" sockets receive from anyone - asy_udp_socket.py places source-address
        # trust on the caller. run() filters to the AP's own subnet before ever replying.
        self.udps = AsyUDPSocket(("0.0.0.0", 53), mode="server")
        self.debug = debug

    async def run(self, server_ip: str, netmask: str) -> None:
        try:
            netmask_int = _ipv4_to_int(netmask)
            network = _ipv4_to_int(server_ip) & netmask_int
        except Exception:
            # server_ip/netmask come from the OS's own wlan.ifconfig(); guard broadly since nothing
            # supervises this task (CancelledError is exempt - it's a BaseException, not Exception).
            if self.debug:
                print("DNSServer: invalid server_ip/netmask, not starting:", server_ip, netmask)
            return
        while True:
            try:
                if self.debug:
                    print("Waiting for DNS request...")
                data, addr = await self.udps.recvfrom(4096)
                if data is not None and addr is not None:
                    try:
                        on_subnet = (_ipv4_to_int(addr[0]) & netmask_int) == network
                    except Exception:
                        # addr[0] not a well-formed dotted-quad string (e.g. a raw sockaddr byte -
                        # see BACKLOG.md) - treated like off-subnet, not the 3s backoff below.
                        on_subnet = False
                    if not on_subnet:
                        if self.debug:
                            print(f"Ignoring DNS request from off-subnet or malformed address {addr[0]!r}")
                        continue
                    if self.debug:
                        print(f"Incoming DNS request from {addr[0]:s}:{addr[1]}...")
                    dns = DNSQuery(data, debug=self.debug)
                    packet = dns.response(server_ip)
                    if packet is None:
                        if self.debug:
                            print("Empty DNS query, not sending response.")
                    else:
                        sent = await self.udps.sendto(packet, addr)
                        if self.debug:
                            if sent is None:
                                print(f"Reply to {addr[0]:s}:{addr[1]} dropped by sendto().")
                            else:
                                print(f"Replying to {addr[0]:s}:{addr[1]}: {dns.domain:s} -> {server_ip:s}")
                else:  # data or address is None
                    if self.debug:
                        print("Invalid DNS request data or address, not sending response.")

            except asyncio.CancelledError:
                if self.debug:
                    print("DNS Server shutdown")
                break

            except Exception as e:
                if self.debug:
                    print("DNS Server error:", e)
                await asyncio.sleep(3)

        try:
            await self.udps.disconnect()
        except asyncio.CancelledError:
            # A second cancellation delivered while this cleanup await is in flight - already
            # shutting down, nothing more to do.
            pass
        except Exception as e:
            # disconnect() is documented as never raising, but nothing supervises this task -
            # never let cleanup itself become the uncaught exception.
            if self.debug:
                print("DNS Server error during disconnect:", e)
        if self.debug:
            print("DNS Server disconnected.")


class DNSQuery:
    def __init__(self, data: bytes, debug: bool = False) -> None:
        self.data = data
        self.domain = ""
        self._question_end = 0  # set below once a full question is actually parsed
        self.debug = debug
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
        except Exception:
            # Truncated/malformed data (or non-bytes data, since this class is public) - not a
            # usable standard query. Reuses the empty-domain sentinel, no raise into run().
            self.domain = ""
        if self.debug:
            print("DNSQuery domain:" + self.domain)

    def response(self, ip: str) -> bytes | None:
        # RFC 1035 section 4.1.1/4.1.4: a synthesized "success, recursion available" header,
        # echoing the original question back with one compressed-pointer A-record answer.
        if self.debug:
            print(f"DNSQuery response: {self.domain} ==> {ip}")
        if self.domain:
            try:
                # This method is public and shouldn't rely on run() only passing a validated
                # server_ip - a bad ip would otherwise build a corrupt packet (wrong RDATA length).
                _ipv4_to_int(ip)
            except Exception:
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
