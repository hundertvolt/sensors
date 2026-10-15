#!/usr/bin/env python3
"""Sends one hand-built IPv4+UDP datagram from a forged source, for the bench's off-subnet NTP/DNS
spoof attempt (needs root: raw IPPROTO_RAW). Refuses any --src outside RFC 5737's documentation
ranges, so it can only ever forge a documentation address, never a real host's."""

import argparse
import ipaddress
import socket
import struct
import sys

# RFC 5737's three TEST-NET blocks: the only sources this tool will forge.
_DOCUMENTATION_NETWORKS = (ipaddress.ip_network("192.0.2.0/24"), ipaddress.ip_network("198.51.100.0/24"), ipaddress.ip_network("203.0.113.0/24"))


def _checksum(data: bytes) -> int:
    # The 16-bit one's-complement sum RFC 768/791 use; an odd length is padded with a zero byte.
    if len(data) % 2:
        data += b"\x00"
    total = sum(struct.unpack(f">{len(data) // 2}H", data))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return int((~total) & 0xFFFF)


def build_datagram(src: str, dst: str, sport: int, dport: int, payload: bytes) -> bytes:
    # One IPv4 datagram carrying a UDP packet, both checksums filled in. IPPROTO_RAW expects the
    # whole IP header, so the kernel computes nothing for us.
    src_bytes, dst_bytes = socket.inet_aton(src), socket.inet_aton(dst)
    udp_length = 8 + len(payload)
    udp = struct.pack(">HHHH", sport, dport, udp_length, 0) + payload
    pseudo = src_bytes + dst_bytes + struct.pack(">BBH", 0, socket.IPPROTO_UDP, udp_length)
    udp = udp[:6] + struct.pack(">H", _checksum(pseudo + udp)) + udp[8:]

    total_length = 20 + udp_length
    header = struct.pack(">BBHHHBBH", 0x45, 0, total_length, 0, 0, 64, socket.IPPROTO_UDP, 0) + src_bytes + dst_bytes
    header = header[:10] + struct.pack(">H", _checksum(header)) + header[12:]
    return header + udp


def _documentation_address(value: str) -> str:
    address = ipaddress.ip_address(value)
    if not any(address in net for net in _DOCUMENTATION_NETWORKS):
        raise argparse.ArgumentTypeError(f"--src {value} is not a documentation address (RFC 5737: 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24); this tool forges only those")
    return value


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True, type=_documentation_address, help="forged source address (RFC 5737 documentation range only)")
    parser.add_argument("--dst", required=True, help="destination address")
    parser.add_argument("--sport", type=int, default=40000, help="source UDP port")
    parser.add_argument("--dport", required=True, type=int, help="destination UDP port")
    parser.add_argument("--payload-hex", required=True, help="UDP payload as hex")
    args = parser.parse_args(argv)
    datagram = build_datagram(args.src, args.dst, args.sport, args.dport, bytes.fromhex(args.payload_hex))
    with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW) as sock:
        sock.sendto(datagram, (args.dst, 0))
    print(f"sent {len(datagram)} bytes from {args.src} to {args.dst}:{args.dport}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
