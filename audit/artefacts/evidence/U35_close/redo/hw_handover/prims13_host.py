"""prims13_host.py: live TCP against the board during its flash writes: a small GET every 50 ms, back-to-back 16 KB GETs
and back-to-back 32 KB uploads, each with its latency and failures on the host clock; a scapy capture on br0 counts
retransmitted segments per direction and when they happened."""
import socket
import sys
import threading
import time

from scapy.all import IP, TCP, AsyncSniffer, conf

conf.verb = 0
BOARD, DUR = sys.argv[1], float(sys.argv[2])
stop = threading.Event()
res: dict[str, list[tuple[float, str, float]]] = {"small": [], "big": [], "up": []}


def fetch(req: bytes, want: int) -> str:
    s = socket.create_connection((BOARD, 80), timeout=6)
    try:
        s.sendall(req)
        d = b""
        while c := s.recv(4096):
            d += c
        return "ok" if len(d) >= want else "short%d" % len(d)
    finally:
        s.close()


def loop(kind: str, req: bytes, want: int, gap: float) -> None:
    while not stop.is_set():
        t = time.time()
        try:
            r = fetch(req, want)
        except OSError as e:
            r = type(e).__name__
        dt = time.time() - t
        res[kind].append((t, r, dt))
        if r != "ok" or dt > 0.5:
            print("HOST %.3f %s %s %.3fs" % (t, kind, r, dt), flush=True)
        time.sleep(gap)


UP = b"POST /up HTTP/1.0\r\nContent-Length: 32768\r\n\r\n" + b"u" * 32768
seen: dict[tuple, set] = {}
retx: list[tuple[float, str]] = []


def on_pkt(p) -> None:  # a data segment whose sequence number was already sent on that flow is a retransmission
    t, n = p[TCP], len(p[TCP].payload)
    if not n:
        return
    flow = (p[IP].src, t.sport, p[IP].dst, t.dport)
    s = seen.setdefault(flow, set())
    if t.seq in s:
        retx.append((float(p.time), "board->host" if p[IP].src == BOARD else "host->board"))
    s.add(t.seq)


sn = AsyncSniffer(iface="br0", prn=on_pkt, store=False, lfilter=lambda p: IP in p and TCP in p and BOARD in (p[IP].src, p[IP].dst) and 80 in (p[TCP].sport, p[TCP].dport))
sn.start()
time.sleep(1)
for args in (("small", b"GET / HTTP/1.0\r\n\r\n", 20, 0.05), ("big", b"GET /big HTTP/1.0\r\n\r\n", 16384, 0.0), ("up", UP, 20, 0.0)):
    threading.Thread(target=loop, args=args, daemon=True).start()
time.sleep(DUR)
stop.set()
time.sleep(7)
sn.stop()
for k, v in res.items():
    bad = [x for x in v if x[1] != "ok"]
    lat = sorted(x[2] for x in v if x[1] == "ok")
    print("SUM prims13_host", k, "n", len(v), "failed", len(bad), "lat_s p50 %.3f max %.3f" % (lat[len(lat) // 2], lat[-1]) if lat else "")
print("SUM prims13_host retransmissions", len(retx), "board->host", sum(1 for r in retx if r[1] == "board->host"),
      "at", ["%.3f %s" % r for r in retx][:40])
