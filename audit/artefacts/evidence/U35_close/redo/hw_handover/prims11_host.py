"""prims11_host.py: clients that vanish without a word, emulated from the bench host with scapy on br0. Each takes an unused
LAN address (ARP-checked first) and a locally administered MAC, opens TCP to the board and sends part of a request, or all
of it and then ACKs nothing, or only a SYN, then answers nothing, ARP included; a real kernel client probes every 2 s."""
import random
import socket
import sys
import threading
import time

from scapy.all import ARP, IP, TCP, AsyncSniffer, Ether, Raw, conf, sendp, srp

conf.verb = 0
IFACE, BOARD, PORT, T0 = "br0", sys.argv[1], 80, time.time()


def now() -> float:
    return time.time() - T0


def log(*a: object) -> None:
    print("HOST t=%.1f" % now(), *a, flush=True)


cands = ["192.168.85.%d" % i for i in range(200, 254)]
ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=cands), iface=IFACE, timeout=2, retry=1)
used = {r[ARP].psrc for _, r in ans}
free = [c for c in cands if c not in used]
ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=BOARD), iface=IFACE, timeout=2, retry=2)
BMAC = ans[0][1][ARP].hwsrc
log("board mac", BMAC, "free addresses", len(free), "of", len(cands))


class Fake:
    def __init__(self, ip: str, i: int, mode: str) -> None:
        self.ip, self.mac, self.mode, self.alive = ip, "02:5e:00:00:00:%02x" % i, mode, True
        self.sport, self.isn = random.randint(20000, 60000), random.randint(0, 2**31)
        self.synack, self.rcv, self.t_gone, self.after, self.result = threading.Event(), 0, 0.0, [], ""


fakes: dict[str, Fake] = {}


def on_pkt(p: Ether) -> None:
    if ARP in p and p[ARP].op == 1 and p[ARP].pdst in fakes:
        f = fakes[p[ARP].pdst]
        if f.alive:
            sendp(Ether(dst=p[ARP].hwsrc, src=f.mac) / ARP(op=2, hwsrc=f.mac, psrc=f.ip, hwdst=p[ARP].hwsrc, pdst=p[ARP].psrc), iface=IFACE)
        else:
            f.after.append((now(), "ARP", 0))
    elif IP in p and TCP in p and p[IP].src == BOARD and p[IP].dst in fakes:
        f, t = fakes[p[IP].dst], p[TCP]
        if not f.alive:
            f.after.append((now(), str(t.flags), len(t.payload)))
        elif "S" in t.flags and "A" in t.flags:
            f.rcv = t.seq + 1
            f.synack.set()


def open_fake(f: Fake) -> None:
    e, ip = Ether(src=f.mac, dst=BMAC), IP(src=f.ip, dst=BOARD)
    sendp(e / ip / TCP(sport=f.sport, dport=PORT, flags="S", seq=f.isn, window=2920, options=[("MSS", 1460)]), iface=IFACE)
    if f.mode == "syn_only":
        time.sleep(0.2)
    elif not f.synack.wait(3):
        f.result = "no_synack"
    else:
        seq = f.isn + 1
        sendp(e / ip / TCP(sport=f.sport, dport=PORT, flags="A", seq=seq, ack=f.rcv, window=2920), iface=IFACE)
        data = b"GET / HTTP/1.1\r\nHost: b\r\n" if f.mode == "head" else b"GET /big HTTP/1.0\r\n\r\n"
        sendp(e / ip / TCP(sport=f.sport, dport=PORT, flags="PA", seq=seq, ack=f.rcv, window=2920) / Raw(data), iface=IFACE)
        time.sleep(0.3)
    f.result = f.result or "open"
    f.alive, f.t_gone = False, now()


probes: list[tuple[float, str, float]] = []
stop = threading.Event()


def probe_loop() -> None:
    while not stop.is_set():
        t = now()
        s = socket.socket()
        s.settimeout(4)
        try:
            s.connect((BOARD, PORT))
            s.sendall(b"GET / HTTP/1.0\r\n\r\n")
            d = b""
            while c := s.recv(512):
                d += c
            res = "ok" if d.endswith(b"ok\n") else "short"
        except Exception as e:  # noqa: BLE001
            res = type(e).__name__
        finally:
            s.close()
        probes.append((t, res, now() - t))
        if res != "ok":
            log("probe", res, "%.2fs" % (now() - t))
        time.sleep(2)


def probe_summary(a: float, b: float) -> str:
    ps = [p for p in probes if a <= p[0] < b]
    bad = [p for p in ps if p[1] != "ok"]
    worst = max((p[2] for p in ps if p[1] == "ok"), default=0)
    span = "%.0f-%.0f" % (bad[0][0], bad[-1][0]) if bad else "-"
    return "probes %d ok %d failed %d worst_ok_s %.2f failed_span_t %s" % (len(ps), len(ps) - len(bad), len(bad), worst, span)


sn = AsyncSniffer(iface=IFACE, prn=on_pkt, store=False, lfilter=lambda p: ARP in p or (IP in p and p[IP].src == BOARD))
sn.start()
time.sleep(1)
threading.Thread(target=probe_loop, daemon=True).start()
n = 0
marks = [now()]
time.sleep(15)
for mode, count, settle in (("head", 6, 120), ("big_noack", 10, 150), ("syn_only", 8, 150)):
    marks.append(now())
    for _ in range(count):
        f = Fake(free[n], n + 1, mode)
        fakes[f.ip] = f
        n += 1
        open_fake(f)
    log("phase", mode, "opened", sum(1 for f in fakes.values() if f.mode == mode and f.result == "open"), "of", count)
    time.sleep(settle)
marks.append(now())
stop.set()
time.sleep(3)
sn.stop()
for i, name in enumerate(("baseline", "head", "big_noack", "syn_only")):
    print("SUM prims11_host", name, probe_summary(marks[i], marks[i + 1]))
for f in fakes.values():
    tcp = [a for a in f.after if a[1] != "ARP"]
    flags = sorted({a[1] for a in tcp})
    last = tcp[-1][0] - f.t_gone if tcp else 0
    print("SUM prims11_host fake", f.ip, f.mode, f.result, "pkts_after", len(tcp), "data_pkts", sum(1 for a in tcp if a[2]), "flags", flags,
          "last_pkt_after_s %.1f" % last, "arp_asks", sum(1 for a in f.after if a[1] == "ARP"))
