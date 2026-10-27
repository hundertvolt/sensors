"""The UDP shim binds a server's wildcard on the process's own loopback address, TEST_TWIN_HOST: two Unix-port processes
binding one fixed port each keep their own datagrams, where on one shared address the socket bound last takes every
datagram either sends (digital_twin/README.md "_unix_port_udp_addr_shim.py")."""

import os
import socket
import subprocess
import threading
from pathlib import Path

import pytest
from _script_loader import load_script_module

_REPO_ROOT = Path(__file__).resolve().parent.parent
# The allocation-failure markers every gate shares (tests_scripts/test_memory_error_gate_agreement.py).
_MEMORY_ERROR_MARKERS: tuple[str, ...] = tuple(load_script_module(_REPO_ROOT / "tests_hardware" / "harness.py", "harness_for_twin_host").MEMORY_ERROR_MARKERS)
_BURST = 6  # the sensortask integration file's own DNS burst
_PROBE_TIMEOUT_S = 60  # a probe still running then is killed, so a hung one fails the test instead of stalling the tier
_STAGES = ("-1", "32768")
# One process's server-mode wildcard UDPSocket through the shim: prints the address the shim bound it on, sends its
# burst to that address on the first input line, then counts what its own socket received on the second.
_PROBE = """\
import asyncio
import gc
import socket
import sys

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port

patch_asy_udp_socket_for_unix_port()
from asy_udp_socket import UDPSocket

stage, port, burst = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
gc.threshold(stage)


async def main():
    server = UDPSocket(("0.0.0.0", port), mode="server")
    await server._connect()
    host = ".".join(str(b) for b in server._addr[4:8])
    print("bound", server.connected, host)
    sys.stdin.readline()
    peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for i in range(burst):
        peer.sendto(bytes([0, i]), socket.getaddrinfo(host, port)[0][-1])
    peer.close()
    print("sent", burst)
    sys.stdin.readline()
    received = 0
    while (await server.recvfrom(512, timeout_ms=200))[0] is not None:
        received += 1
    print("received", received)
    await server.disconnect()


asyncio.run(main())
"""


class _Probe:
    # One probe process, its output lines so far; killed at _PROBE_TIMEOUT_S, so a line it never prints reads as "".
    def __init__(self, micropython_bin: Path, cwd: Path, stage: str, port: int, burst: int, twin_host: "str | None") -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("TEST_DEVICE", "TEST_TWIN_HOST")}
        env |= {"MICROPYPATH": f"{_REPO_ROOT / 'src'}:{_REPO_ROOT / 'digital_twin' / 'unixport'}:.frozen", "TZ": "UTC"}
        if twin_host is not None:
            env["TEST_TWIN_HOST"] = twin_host
        self.out: list[str] = []
        self.proc = subprocess.Popen([str(micropython_bin), "-X", "heapsize=16M", "probe.py", stage, str(port), str(burst)], cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self._timer = threading.Timer(_PROBE_TIMEOUT_S, self.proc.kill)
        self._timer.start()

    def close(self) -> int:
        # The probe's exit code once its remaining output is read; the timer stopped either way.
        try:
            rest, _ = self.proc.communicate(timeout=_PROBE_TIMEOUT_S)
            self.out.append(rest)
        finally:
            self._timer.cancel()
            self.proc.kill()
        return self.proc.returncode

    def line(self) -> str:
        assert self.proc.stdout is not None
        text = self.proc.stdout.readline()
        self.out.append(text)
        assert text, f"the probe printed no further line: {''.join(self.out)!r}"
        return text.strip()

    def send(self) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write("\n")
        self.proc.stdin.flush()


def _free_udp_port() -> int:
    # A port the OS hands out now; the probes bind it on addresses of their own, never on 127.0.0.1.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _marked(probes: "list[_Probe]") -> "list[str]":
    return [line for probe in probes for line in "".join(probe.out).splitlines() if any(marker in line for marker in _MEMORY_ERROR_MARKERS)]


def _probe_file(tmp_path: Path) -> Path:
    (tmp_path / "probe.py").write_text(_PROBE, encoding="utf-8")
    return tmp_path


def _run_alone(micropython_bin: Path, tmp_path: Path, stage: str, twin_host: "str | None") -> "tuple[int, str]":
    # One probe with no burst taken through both steps: its exit code and its whole output.
    probe = _Probe(micropython_bin, _probe_file(tmp_path), stage, _free_udp_port(), 0, twin_host)
    try:
        probe.send()
        probe.send()
    except BrokenPipeError:
        pass  # a probe that already exited: its output says why
    code = probe.close()
    assert not _marked([probe]), _marked([probe])
    return code, "".join(probe.out)


@pytest.mark.parametrize("stage", _STAGES)
def test_a_burst_to_a_processs_own_server_reaches_that_process_alone(micropython_bin: Path, tmp_path: Path, stage: str) -> None:
    # The sender binds first and the other process last, the socket one shared address would hand every datagram to;
    # the sender's burst to its own server's address must reach its own listener alone.
    cwd, port = _probe_file(tmp_path), _free_udp_port()
    probes: list[_Probe] = []
    try:
        sender = _Probe(micropython_bin, cwd, stage, port, _BURST, "127.0.0.2")
        probes.append(sender)
        sender_bound = sender.line()
        other = _Probe(micropython_bin, cwd, stage, port, 0, "127.0.0.3")
        probes.append(other)
        other_bound = other.line()
        for step in ("sent", "received"):
            for probe in (other, sender):
                probe.send()
            lines = [sender.line(), other.line()]
            assert all(text.startswith(step) for text in lines), lines
        own, leaked = (int(text.split()[-1]) for text in lines)
        codes = [probe.close() for probe in probes]
    finally:
        for probe in probes:
            probe.proc.kill()
    assert (leaked, own) == (0, _BURST), f"the process bound last ({other_bound}) received {leaked} of the other's {_BURST} datagrams; the sender's own listener ({sender_bound}) received {own}"
    assert (sender_bound, other_bound) == ("bound True 127.0.0.2", "bound True 127.0.0.3")
    assert codes == [0, 0], [("".join(probe.out)) for probe in probes]
    assert not _marked(probes), _marked(probes)


@pytest.mark.parametrize("stage", _STAGES)
def test_without_a_twin_host_a_server_binds_127_0_0_1(micropython_bin: Path, tmp_path: Path, stage: str) -> None:
    # Where every host-side talker (the CI suite, the scenario harness, the tests_scripts twins) reaches a twin.
    code, out = _run_alone(micropython_bin, tmp_path, stage, None)
    assert code == 0, out
    assert out.splitlines()[0] == "bound True 127.0.0.1", out


@pytest.mark.parametrize("stage", _STAGES)
@pytest.mark.parametrize("value", ["192.0.2.1", "localhost", "", "127.0.0"])
def test_a_twin_host_off_the_loopback_fails_the_patch_naming_it(micropython_bin: Path, tmp_path: Path, stage: str, value: str) -> None:
    # A misconfigured runner fails every file at its import, before a server binds anywhere.
    code, out = _run_alone(micropython_bin, tmp_path, stage, value)
    assert code != 0, out
    assert f"ValueError: TEST_TWIN_HOST={value!r} is no IPv4 loopback address (127.0.0.0/8)" in out, out
    assert "bound" not in out, out
