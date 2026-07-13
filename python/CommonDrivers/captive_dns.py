import socket
import asyncio
from asy_udp_socket import AsyUDPSocket

class DNSServer:
    def __init__(self, debug=False):
        self.udps = AsyUDPSocket(("0.0.0.0", 53), mode="server")
        self.debug = debug
        
    async def run(self, server_ip):
        while True:
            try:
                if self.debug: print("Waiting for DNS request...")
                data, addr = await self.udps.recvfrom(4096)
                if self.debug: print("Incoming DNS request from {:s}:{}...".format(addr[0], addr[1]))

                DNS = DNSQuery(data, debug=self.debug)
                packet = DNS.response(server_ip)
                if packet is None:
                    if self.debug: print("Empty DNS query, not sending response.")
                else:
                    await self.udps.sendto(packet, addr)
                    if self.debug: print("Replying to {:s}:{}: {:s} -> {:s}".format(addr[0], addr[1], DNS.domain, server_ip))

            except asyncio.CancelledError:
                if self.debug: print("DNS Server shutdown")
                break

            except Exception as e:
                if self.debug: print("DNS Server error:", e)
                await asyncio.sleep(3)

        await self.udps.disconnect()
        if self.debug: print("DNS Server disconnected.")

class DNSQuery:
    def __init__(self, data, debug=False):
        self.data = data
        self.domain = ''
        self.debug = debug
        tipo = (data[2] >> 3) & 15  # Opcode bits
        if tipo == 0:  # Standard query
            ini = 12
            lon = data[ini]
            while lon != 0:
                self.domain += data[ini + 1:ini + lon + 1].decode('utf-8') + '.'
                ini += lon + 1
                lon = data[ini]
        if self.debug: print("DNSQuery domain:" + self.domain)

    def response(self, ip):
        if self.debug: print("DNSQuery response: {} ==> {}".format(self.domain, ip))
        if self.domain:
            packet = self.data[:2] + b'\x81\x80'
            packet += self.data[4:6] + self.data[4:6] + b'\x00\x00\x00\x00'  # Questions and Answers Counts
            packet += self.data[12:]  # Original Domain Name Question
            packet += b'\xC0\x0C'  # Pointer to domain name
            packet += b'\x00\x01\x00\x01\x00\x00\x00\x3C\x00\x04'  # Response type, ttl and resource data length -> 4 bytes
            packet += bytes(map(int, ip.split('.')))  # 4bytes of IP
            return packet
        return None
