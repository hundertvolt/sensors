"""Minimal, dependency-free DNS query/response helpers for the captive-DNS checks in
test_hotspot_role_reversal.py (HARDWARE_TEST_PLAN.md §11.5 stage 3) - hand-rolled rather than
pulling in dnspython (not a project dependency, and this only needs a single fixed query shape),
matching this project's own preference for small hand-rolled protocol code over a new dependency
(see digital_twin/_http_client.py's own module docstring for the same reasoning applied to HTTP)."""

from __future__ import annotations

import secrets
import socket
import struct

_DNS_PORT = 53


def build_query(hostname: str) -> bytes:
    """A single-question, standard A-record query - the exact shape src/captive_dns.py's
    DNSQuery/DNSServer expects (confirmed by reading that module in full during this session's own
    HARDWARE_TEST_PLAN.md §11.1 research)."""
    txn_id = secrets.token_bytes(2)
    header = txn_id + bytes([0x01, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # standard query, 1 question
    question = b""
    for label in hostname.split("."):
        question += bytes([len(label)]) + label.encode()
    question += b"\x00"  # root terminator
    question += struct.pack(">HH", 1, 1)  # QTYPE=A, QCLASS=IN
    return header + question, txn_id


def query(server_ip: str, hostname: str, timeout_s: float = 5.0, raw_query: bytes | None = None) -> bytes | None:
    """Sends `raw_query` (or a freshly-built one for `hostname`) to `server_ip:53` over UDP and
    returns the raw response bytes, or None on timeout - never raises on a timeout, since "no
    response" is itself a real, assertable outcome for several of this file's own tests (a
    malformed/off-subnet query is expected to get silently dropped, not answered)."""
    payload = raw_query if raw_query is not None else build_query(hostname)[0]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout_s)
        sock.sendto(payload, (server_ip, _DNS_PORT))
        try:
            data, _addr = sock.recvfrom(512)
        except TimeoutError:
            return None
        return data


def extract_answer_ip(response: bytes) -> str | None:
    """Parses just enough of a standard single-answer A-record response to pull out the answered
    IPv4 address - src/captive_dns.py's own DNSQuery.response() always answers with exactly one
    A record (confirmed by reading that module in full), so this deliberately doesn't handle the
    general multi-answer/multi-type case."""
    if len(response) < 12:
        return None
    ancount = struct.unpack(">H", response[6:8])[0]
    if ancount < 1:
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
