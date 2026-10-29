"""prims12_host.py: a UDP echo probe every 10 ms against the board during its flash writes; prints each late or lost echo
with the host's wall clock (the runner stamps the board's MARK lines with the same clock), then a summary."""
import socket
import struct
import sys
import time

BOARD, DUR = sys.argv[1], float(sys.argv[2])
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setblocking(False)
sent: dict[int, float] = {}
rtts: list[float] = []
t_end, seq, nxt = time.time() + DUR, 0, time.time()
while time.time() < t_end:
    now = time.time()
    if now >= nxt:
        s.sendto(struct.pack("<Id", seq, now), (BOARD, 5006))
        sent[seq], seq, nxt = now, seq + 1, nxt + 0.01
    try:
        d = s.recv(64)
        q, t = struct.unpack("<Id", d[:12])
        r = (time.time() - t) * 1000
        rtts.append(r)
        sent.pop(q, None)
        if r > 30:
            print("HOST %.3f late seq %d rtt_ms %.0f" % (t, q, r), flush=True)
    except BlockingIOError:
        time.sleep(0.001)
lost = sorted(k for k, v in sent.items() if v < t_end - 1)
print("HOST lost", len(lost), "at", ["%.3f" % sent[k] for k in lost][:40])
rtts.sort()
print("SUM prims12_host sent", seq, "echoed", len(rtts), "lost", len(lost), "rtt_ms p50 %.1f p99 %.1f max %.1f" % (rtts[len(rtts) // 2], rtts[int(len(rtts) * .99)], rtts[-1]))
