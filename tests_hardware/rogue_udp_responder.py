"""Shared background UDP responder for network-fault-injection tests: answers every datagram with a
fixed garbage payload until stopped, on the port the OS picks unless one is given, and counts each
source it answered so a test can prove the injection reached the DUT (bench_control's redirects)."""

import socket
import threading

# @tunable l4.rogue_udp_responder_recv_timeout_s = 0.5
_RECV_TIMEOUT_S = 0.5
# @tunable l4.rogue_udp_responder_join_timeout_s = 5.0
_JOIN_TIMEOUT_S = 5.0


class RogueUdpResponder:
    def __init__(self, garbage_payload: bytes, local_port: int = 0) -> None:
        self._garbage_payload = garbage_payload
        self.answered_from: dict[str, int] = {}
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(_RECV_TIMEOUT_S)  # bounds each recvfrom() so stop() can interrupt the loop promptly
        self._sock.bind(("0.0.0.0", local_port))  # binds the bench host's responder on the bench LAN
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    @property
    def port(self) -> int:
        # The bound port: the one a redirect must point at when the OS picked it.
        return int(self._sock.getsockname()[1])

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
                continue  # not counted: answered_from holds only what really went out
            self.answered_from[addr[0]] = self.answered_from.get(addr[0], 0) + 1

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=_JOIN_TIMEOUT_S)
        self._sock.close()

    def __enter__(self) -> "RogueUdpResponder":
        self.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()
