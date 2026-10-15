"""tests_hardware/spoof_udp.py builds an IPv4+UDP datagram by hand for the off-subnet spoof attempt:
its two checksums verify against an independently computed vector, and its CLI refuses any source
outside RFC 5737's documentation ranges, so the tool can never forge a real host's address."""

import socket
import struct
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from _script_loader import load_script_module

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _spoof_udp() -> ModuleType:
    return load_script_module(_REPO_ROOT / "tests_hardware" / "spoof_udp.py", "spoof_udp_under_test")


def _ones_complement_sum(data: bytes) -> int:
    # The 16-bit one's-complement sum RFC 768/791 checksums use, computed here from scratch.
    if len(data) % 2:
        data += b"\x00"
    total = sum(struct.unpack(f">{len(data) // 2}H", data))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return int((~total) & 0xFFFF)


def test_build_datagram_matches_a_hand_computed_checksum_vector() -> None:
    src, dst, sport, dport, payload = "203.0.113.5", "198.51.100.9", 40000, 53, b"\x12\x34hello"
    datagram = _spoof_udp().build_datagram(src, dst, sport, dport, payload)

    assert datagram[0] == 0x45, "IPv4, header length 5 words"
    total_length = struct.unpack(">H", datagram[2:4])[0]
    assert total_length == len(datagram) == 20 + 8 + len(payload)
    assert datagram[9] == socket.IPPROTO_UDP
    assert datagram[12:16] == socket.inet_aton(src)
    assert datagram[16:20] == socket.inet_aton(dst)

    # IPv4 header checksum: zero the field, re-sum, compare.
    header = bytearray(datagram[:20])
    header[10:12] = b"\x00\x00"
    assert struct.unpack(">H", datagram[10:12])[0] == _ones_complement_sum(bytes(header))

    # UDP checksum over the pseudo-header + UDP header (checksum zeroed) + payload.
    udp = bytearray(datagram[20:])
    udp[6:8] = b"\x00\x00"
    pseudo = socket.inet_aton(src) + socket.inet_aton(dst) + struct.pack(">BBH", 0, socket.IPPROTO_UDP, len(udp))
    assert struct.unpack(">H", datagram[26:28])[0] == _ones_complement_sum(pseudo + bytes(udp))


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(_REPO_ROOT / "tests_hardware" / "spoof_udp.py"), *args], capture_output=True, text=True, check=False)


def test_a_source_outside_the_documentation_ranges_exits_2() -> None:
    result = _cli("--src", "192.168.1.5", "--dst", "198.51.100.9", "--dport", "53", "--payload-hex", "00")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "documentation" in (result.stdout + result.stderr).lower(), "the refusal names why the source is rejected"


def test_each_documentation_range_is_accepted_by_build_datagram() -> None:
    # RFC 5737's three TEST-NET ranges: the only sources the tool will send from.
    build = _spoof_udp().build_datagram
    for src in ("192.0.2.1", "198.51.100.254", "203.0.113.128"):
        assert build(src, "198.51.100.9", 40000, 53, b"q")[12:16] == socket.inet_aton(src)
