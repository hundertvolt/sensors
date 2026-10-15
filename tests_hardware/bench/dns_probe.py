"""Minimal, dependency-free DNS query/response helpers for test_hotspot_role_reversal.py's
captive-DNS checks - hand-rolled rather than pulling in dnspython, matching this project's
preference for small hand-rolled protocol code over a new dependency."""

import secrets
import socket
import struct

_DNS_PORT = 53
_QTYPE_A = 1  # RFC 1035 3.2.2
_QCLASS_IN = 1  # RFC 1035 3.2.4
_ANCOUNT_END = 8  # the header's ANCOUNT is bytes 6-7
# @tunable l4.dns_probe_query_timeout_s = 5.0
_QUERY_TIMEOUT_S = 5.0


def answer_count(response: bytes) -> int | None:
    # The header's ANCOUNT, None for a packet too short to hold it.
    if len(response) < _ANCOUNT_END:
        return None
    return int(struct.unpack(">H", response[6:_ANCOUNT_END])[0])


def build_query(hostname: str, qtype: int = _QTYPE_A) -> tuple[bytes, bytes]:
    # A single-question, standard query for `qtype` (class IN) - the shape src/asy_captive_dns.py's
    # DNSQuery/CaptiveDNS parses.
    txn_id = secrets.token_bytes(2)
    header = txn_id + bytes([0x01, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # standard query, 1 question
    question = b""
    for label in hostname.split("."):
        question += bytes([len(label)]) + label.encode()
    question += b"\x00"  # root terminator
    question += struct.pack(">HH", qtype, _QCLASS_IN)
    return header + question, txn_id


def extract_answer_ip(response: bytes) -> str | None:
    # The captive DNS answers an A/ANY query with exactly one A record and every other type with an empty NOERROR
    # reply (SPECIFICATION.md C.7.5), so this reads one A record's address and handles no other answer shape.
    if len(response) < 12:
        return None
    ancount = answer_count(response)
    if ancount is None or ancount < 1:
        return None
    # Skip the header (12 bytes) and the echoed question section (a name, ending at the first
    # zero-length label, plus QTYPE+QCLASS = 4 bytes) to reach the answer section.
    pos = 12
    while pos < len(response) and response[pos] != 0:
        label_len = response[pos]
        if label_len & 0xC0:  # a compression pointer this early would be unusual - bail out cleanly
            return None
        pos += 1 + label_len
    pos += 1 + 4  # the zero-length terminator, then QTYPE+QCLASS
    # Answer record: NAME (possibly a compression pointer, 2 bytes) + TYPE(2) + CLASS(2) + TTL(4) + RDLENGTH(2) + RDATA
    if response[pos] & 0xC0:
        pos += 2
    else:
        while pos < len(response) and response[pos] != 0:
            pos += 1 + response[pos]
        pos += 1
    pos += 2 + 2 + 4  # TYPE, CLASS, TTL
    rdlength = struct.unpack(">H", response[pos : pos + 2])[0]
    pos += 2
    if rdlength != 4 or pos + 4 > len(response):
        return None
    return socket.inet_ntoa(response[pos : pos + 4])


def query(server_ip: str, hostname: str, timeout_s: float = _QUERY_TIMEOUT_S, raw_query: bytes | None = None) -> bytes | None:
    # Sends `raw_query` (or a freshly-built one for `hostname`) to `server_ip:53` over UDP,
    # returning the raw response or None on timeout - never raises, since "no response" is itself a
    # real, assertable outcome (a malformed/off-subnet query should be silently dropped).
    payload = raw_query if raw_query is not None else build_query(hostname)[0]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout_s)
        sock.sendto(payload, (server_ip, _DNS_PORT))
        try:
            data, _addr = sock.recvfrom(512)
        except TimeoutError:
            return None
        return data
