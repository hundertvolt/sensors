"""tests_hardware/rogue_udp_responder.py on localhost: it binds the port the OS picks, reports that
port, answers every datagram with its payload and counts each source it answered, so a garbage test
can prove its injection reached the board before judging it."""

import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests_hardware"))
from rogue_udp_responder import RogueUdpResponder

_PAYLOAD = b"\xde\xad\xbe\xef garbage"


def _ask(port: int) -> "tuple[bytes, str]":
    # One datagram to the responder from a fresh socket; returns the reply and our own address.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.settimeout(5.0)
        client.bind(("127.0.0.1", 0))
        client.sendto(b"query", ("127.0.0.1", port))
        reply, _ = client.recvfrom(4096)
        return reply, client.getsockname()[0]


def test_it_binds_the_port_the_os_picks_and_reports_it() -> None:
    with RogueUdpResponder(_PAYLOAD) as responder:
        assert responder.port > 0, "port 0 asks the OS for a free port; the bound one is what a redirect needs"
        reply, _ = _ask(responder.port)
    assert reply == _PAYLOAD


def test_it_counts_each_source_it_answered() -> None:
    with RogueUdpResponder(_PAYLOAD) as responder:
        assert responder.answered_from == {}, "nothing answered before any datagram"
        _, source = _ask(responder.port)
        _ask(responder.port)
    assert responder.answered_from == {source: 2}, responder.answered_from


def test_a_given_port_is_still_honoured() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind(("127.0.0.1", 0))
        free = probe.getsockname()[1]
    with RogueUdpResponder(_PAYLOAD, local_port=free) as responder:
        assert responder.port == free
