"""Minimal, dependency-free NTP reply-crafting helper for the connected-socket source-address-
filtering check in test_network_resilience.py (BACKLOG.md's open question #5) - hand-rolled rather
than pulling in a dependency, matching this project's own preference for small hand-rolled
protocol code over a new one (see dns_probe.py's own module docstring for the same reasoning)."""

from __future__ import annotations

import struct

_NTP_EPOCH_DELTA = 2208988800  # 1900 -> 1970, matches src/asy_ntp_client.py's own const of the same name


def build_reply(unix_time: int) -> bytes:
    """A single, standard-shaped 48-byte NTP server reply (stratum 1, synchronized) whose Transmit
    Timestamp encodes `unix_time` - the exact fields src/asy_ntp_client.py's own _parse_ntp_reply()
    reads (leap indicator + stratum from byte 0/1, big-endian seconds from bytes 40:44; every other
    field, including Origin Timestamp, is confirmed unchecked by that method, so left at 0)."""
    header = bytes([0x24, 0x01, 0x06, 0xEC])  # LI=0, VN=4, Mode=4 (server); stratum=1; poll=6; precision=0xEC
    root_delay = b"\x00\x00\x00\x00"
    root_dispersion = b"\x00\x00\x00\x00"
    reference_id = b"GPS\x00"
    reference_ts = b"\x00" * 8
    origin_ts = b"\x00" * 8
    receive_ts = b"\x00" * 8
    transmit_ts = struct.pack(">I", (unix_time + _NTP_EPOCH_DELTA) & 0xFFFFFFFF) + b"\x00\x00\x00\x00"
    return header + root_delay + root_dispersion + reference_id + reference_ts + origin_ts + receive_ts + transmit_ts
