"""tests_hardware/bench/dns_probe.py asks the DUT's captive DNS for any QTYPE: its query packs the QTYPE and QCLASS IN
big-endian after the encoded name, an A query stays the default, and answer_count() reads ANCOUNT without raising on
a packet cut short - the AAAA check reads an empty NOERROR reply through it (SPECIFICATION.md C.7.5)."""

import struct
from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module

_REPO_ROOT = Path(__file__).resolve().parents[1]
_QCLASS_IN = 1  # RFC 1035 3.2.4


@pytest.mark.parametrize("qtype", [1, 28, 255])
def test_build_query_packs_the_asked_qtype_and_qclass_in(qtype: int) -> None:
    query, txn_id = _dns_probe().build_query("www.example.com", qtype=qtype)
    name, packed_type, packed_class = _question(query)
    assert query[:2] == txn_id and query[4:6] == b"\x00\x01", "one question, under the returned transaction id"
    assert name == b"\x03www\x07example\x03com\x00"
    assert (packed_type, packed_class) == (qtype, _QCLASS_IN)


def test_build_query_asks_for_an_a_record_by_default() -> None:
    _name, qtype, qclass = _question(_dns_probe().build_query("captive.test")[0])
    assert (qtype, qclass) == (1, _QCLASS_IN)


@pytest.mark.parametrize(("response", "count"), [(bytes(6) + b"\x00\x02" + bytes(4), 2), (bytes(6) + b"\x00\x00" + bytes(4), 0), (bytes(7), None), (b"", None)])
def test_answer_count_reads_ancount_and_is_none_on_a_short_packet(response: bytes, count: "int | None") -> None:
    assert _dns_probe().answer_count(response) == count


def _dns_probe() -> ModuleType:
    return load_script_module(_REPO_ROOT / "tests_hardware" / "bench" / "dns_probe.py", "dns_probe_under_test")


def _question(query: bytes) -> "tuple[bytes, int, int]":
    # The QNAME bytes and the QTYPE/QCLASS pair after them, read independently of the module under test.
    pos = 12
    while query[pos]:
        pos += 1 + query[pos]
    qtype, qclass = struct.unpack(">HH", query[pos + 1 : pos + 5])
    assert pos + 5 == len(query), "nothing may follow the one question"
    return query[12 : pos + 1], qtype, qclass
