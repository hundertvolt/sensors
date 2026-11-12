"""Host half of dns_idle_poll.py (CPython, run on the bench Pi once the board prints READY): QUERIES A-queries to the
board's port 53, each after SILENCE_S of quiet, then a back-to-back burst, each reply's round trip timed. Usage:
python3 host_dns_query_timing.py <board IP>. Sends DNS queries only; changes nothing on the host's network."""

import socket
import struct
import sys
import time

QUERIES, SILENCE_S, BURST = 5, 3.0, 4  # a burst inside lwIP's 4-datagram queue per socket


def query(qid: int) -> bytes:
    name = b"".join(bytes((len(p),)) + p for p in (b"example", b"com")) + b"\x00"
    return struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, 0) + name + struct.pack(">HH", 1, 1)


def main(ip: str) -> None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2.0)
    after_silence = []
    for i in range(QUERIES):
        time.sleep(SILENCE_S)
        t = time.monotonic()
        s.sendto(query(i), (ip, 53))
        try:
            s.recvfrom(512)
            after_silence.append(round((time.monotonic() - t) * 1000, 1))
        except OSError:
            after_silence.append(None)
    t = time.monotonic()
    for i in range(BURST):
        s.sendto(query(100 + i), (ip, 53))
    burst = []
    for _ in range(BURST):
        try:
            s.recvfrom(512)
            burst.append(round((time.monotonic() - t) * 1000, 1))
        except OSError:
            burst.append(None)
    print("SUM dns_idle after_silence_ms=%s" % after_silence)
    print("SUM dns_idle burst_ms=%s" % burst)


if __name__ == "__main__":
    main(sys.argv[1])
