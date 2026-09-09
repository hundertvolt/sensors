"""Minimal, dependency-free NTP reply-crafting helper for test_network_resilience.py's
connected-socket source-address-filtering check (see dns_probe.py for the same hand-rolled-over-
imported-dependency approach)."""

from __future__ import annotations

import struct

_NTP_EPOCH_DELTA = 2208988800  # 1900 -> 1970, matches src/asy_ntp_client.py's own const of the same name


def build_reply(unix_time: int) -> bytes:
    """A standard 48-byte NTP server reply (stratum 1) whose Transmit Timestamp encodes `unix_time` -
    the only fields src/asy_ntp_client.py's _parse_ntp_reply() actually reads."""
    header = bytes([0x24, 0x01, 0x06, 0xEC])  # LI=0, VN=4, Mode=4 (server); stratum=1; poll=6; precision=0xEC
    root_delay = b"\x00\x00\x00\x00"
    root_dispersion = b"\x00\x00\x00\x00"
    reference_id = b"GPS\x00"
    reference_ts = b"\x00" * 8
    origin_ts = b"\x00" * 8
    receive_ts = b"\x00" * 8
    transmit_ts = struct.pack(">I", (unix_time + _NTP_EPOCH_DELTA) & 0xFFFFFFFF) + b"\x00\x00\x00\x00"
    return header + root_delay + root_dispersion + reference_id + reference_ts + origin_ts + receive_ts + transmit_ts
