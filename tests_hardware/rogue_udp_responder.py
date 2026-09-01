"""Shared background UDP responder for network-fault-injection tests (BACKLOG.md's open question
#5, "real-hardware verification gap for asy_udp_socket.py/captive_dns.py" - real garbage-response
robustness, not just real unreachability, had no coverage in this tier before this file). Binds a
local UDP socket, replies to every datagram received with a fixed garbage payload until stopped -
used by both the NTP and DNS garbage-response tests via bench_control.BenchBridge's
redirect_udp_port_to_local()/clear_udp_port_redirect()."""

from __future__ import annotations

import socket
import threading


class RogueUdpResponder:
    def __init__(self, local_port: int, garbage_payload: bytes) -> None:
        self._garbage_payload = garbage_payload
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(0.5)  # bounds each recvfrom() so stop() can interrupt the loop promptly
        self._sock.bind(("0.0.0.0", local_port))
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                _data, addr = self._sock.recvfrom(4096)
            except TimeoutError:
                continue
            except OSError:
                return  # socket closed under us during stop()
            try:
                self._sock.sendto(self._garbage_payload, addr)
            except OSError:
                pass  # best-effort - a send failure here is not this responder's own test to report

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._sock.close()

    def __enter__(self) -> RogueUdpResponder:
        self.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()
