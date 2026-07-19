import asyncio
from asy_udp_socket import AsyUDPSocket


def _ipv4_to_int(ip: str) -> int:
    a, b, c, d = (int(octet) for octet in ip.split("."))
    return (a << 24) | (b << 16) | (c << 8) | d


class DNSServer:
    def __init__(self, debug: bool = False) -> None:
        # mode="server" sockets are unconnected and receive from anyone - asy_udp_socket.py's own
        # docstring is explicit that source-address trust is this caller's responsibility, not the
        # transport's. This is a captive-portal DNS server meant to answer only clients already on
        # the AP's own subnet, so run() filters by that subnet before ever building a response.
        self.udps = AsyUDPSocket(("0.0.0.0", 53), mode="server")
        self.debug = debug

    async def run(self, server_ip: str, netmask: str) -> None:
        netmask_int = _ipv4_to_int(netmask)
        network = _ipv4_to_int(server_ip) & netmask_int
        while True:
            try:
                if self.debug:
                    print("Waiting for DNS request...")
                data, addr = await self.udps.recvfrom(4096)
                if data is not None and addr is not None:
                    try:
                        on_subnet = (_ipv4_to_int(addr[0]) & netmask_int) == network
                    except (TypeError, ValueError, AttributeError):
                        # addr[0] not a well-formed dotted-quad string - confirmed directly this is
                        # reachable in this project's MicroPython Unix-port test environment (a
                        # bound-via-resolved-sockaddr AsyUDPSocket returns an opaque raw sockaddr
                        # from recvfrom() there, not a (host, port) tuple - a pre-existing, already
                        # documented quirk, see BACKLOG.md). AttributeError: addr[0] isn't even a
                        # str (e.g. a raw int byte, confirmed directly - '.split' doesn't exist on
                        # int). Treated the same as off-subnet: ignore rather than fall through to
                        # the broad `except Exception` below, which would stall the whole server
                        # (and every other waiting client) for 3s per packet.
                        on_subnet = False
                    if not on_subnet:
                        if self.debug:
                            print("Ignoring DNS request from off-subnet or malformed address {!r}".format(addr[0]))
                        continue
                    if self.debug:
                        print("Incoming DNS request from {:s}:{}...".format(addr[0], addr[1]))
                    dns = DNSQuery(data, debug=self.debug)
                    packet = dns.response(server_ip)
                    if packet is None:
                        if self.debug:
                            print("Empty DNS query, not sending response.")
                    else:
                        await self.udps.sendto(packet, addr)
                        if self.debug:
                            print(
                                "Replying to {:s}:{}: {:s} -> {:s}".format(
                                    addr[0], addr[1], dns.domain, server_ip
                                )
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
    def __init__(self, data: bytes | bytearray, debug: bool = False) -> None:
        self.data = data
        self.domain = ""
        self.debug = debug
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
            # data too short (fewer than 3 bytes for the opcode, or truncated mid-label) or a
            # label containing invalid UTF-8 - confirmed directly reachable from a malformed or
            # truncated UDP datagram, not just a hypothetical. Reset rather than propagate: an
            # uncaught exception here reaches run()'s broad except-Exception handler and stalls
            # the whole server (every other waiting client too) for 3s per bad packet. An empty
            # domain is already the file's existing sentinel for "don't respond" (see the
            # tipo != 0 case and response()'s `if self.domain:` gate), so this reuses it rather
            # than introducing a new one.
            self.domain = ""
        if self.debug:
            print("DNSQuery domain:" + self.domain)

    def response(self, ip: str) -> bytes | None:
        if self.debug:
            print("DNSQuery response: {} ==> {}".format(self.domain, ip))
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
