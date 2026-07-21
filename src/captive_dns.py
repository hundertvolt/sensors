"""Captive-portal DNS spoofer for hotspot/AP mode. One caller: async_connect.py's
DNSServer.run(), started only while the device is broadcasting its own fallback hotspot. Every
on-subnet query gets a canned A-record response pointing back at the AP's own IP, regardless of
the name asked for, so any client on the hotspot lands on the device's own config page.

Never inspects anything beyond the DNS header/question section and the source address; a
subnet-mismatched, malformed, or truncated packet is silently dropped rather than raising - see
DNSServer.run()'s and DNSQuery.__init__'s own comments for the specific guards.
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
        except (TypeError, ValueError):
            # server_ip/netmask come from the OS's own wlan.ifconfig(); guard anyway rather than
            # let a malformed one raise out of the task with nothing supervising it.
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
                    except (TypeError, ValueError, AttributeError):
                        # addr[0] not a well-formed dotted-quad string (e.g. a raw sockaddr byte -
                        # see BACKLOG.md). Treat like off-subnet rather than the 3s backoff below.
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
                                print(
                                    f"Replying to {addr[0]:s}:{addr[1]}: {dns.domain:s} -> {server_ip:s}"
                                )
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

        await self.udps.disconnect()
        if self.debug:
            print("DNS Server disconnected.")


class DNSQuery:
    def __init__(self, data: bytes, debug: bool = False) -> None:
        self.data = data
        self.domain = ""
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
        except (IndexError, UnicodeError):
            # Truncated/malformed datagram - reuse the existing "not a standard query" empty-
            # domain sentinel instead of raising into run()'s 3s per-packet backoff.
            self.domain = ""
        if self.debug:
            print("DNSQuery domain:" + self.domain)

    def response(self, ip: str) -> bytes | None:
        # RFC 1035 section 4.1.1/4.1.4: a synthesized "success, recursion available" header,
        # echoing the original question back with one compressed-pointer A-record answer.
        if self.debug:
            print(f"DNSQuery response: {self.domain} ==> {ip}")
        if self.domain:
            packet = self.data[:2] + b"\x81\x80"
            packet += (
                self.data[4:6] + self.data[4:6] + b"\x00\x00\x00\x00"
            )  # Questions and Answers Counts
            packet += self.data[12:]  # Original Domain Name Question
            packet += b"\xc0\x0c"  # Pointer to domain name
            packet += b"\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04"  # Response type, ttl and resource data length -> 4 bytes
            packet += bytes(map(int, ip.split(".")))  # 4bytes of IP
            return packet
        return None
