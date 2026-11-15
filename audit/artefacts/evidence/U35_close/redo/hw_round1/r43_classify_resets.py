#!/usr/bin/env python3
"""Relay 43: classify each TCP connection to the DUT's port 80 in a tcpdump capture by how the board ended it.

Reads `tcpdump -nn -tt -S -A -r <pcap>` text on stdin. Usage: tcpdump ... | python3 r43_classify_resets.py DUT_IP BODY_CAP
Classes: answered (the board sent response bytes), reset at the handshake (the board reset it before acknowledging any
request byte: modlwip's full accept queue), reset after queueing (request bytes acknowledged, no response byte: the
server's ceiling refusal or close), closed with no response byte (FIN), no SYN-ACK, unfinished."""

import collections
import re
import sys

HDR = re.compile(r"^(\d+\.\d+) IP (\d+(?:\.\d+){3})\.(\d+) > (\d+(?:\.\d+){3})\.(\d+): Flags \[([^\]]*)\](.*)$")
SEQ = re.compile(r"\bseq (\d+)(?::(\d+))?")
ACK = re.compile(r"\back (\d+)")
LEN = re.compile(r"\blength (\d+)")
CLEN = re.compile(r"Content-Length: *(\d+)", re.IGNORECASE)
REQ = re.compile(r"\b(GET|PUT|POST|DELETE|HEAD) (/\S*) HTTP/1\.[01]")
RESP = re.compile(r"HTTP/1\.[01] (\d{3})")


def main() -> int:
    dut, cap = sys.argv[1], int(sys.argv[2])
    conns: dict[int, dict] = collections.defaultdict(lambda: {"isn": None, "synack": False, "syn_count": 0, "board_max_ack": 0,
                                                              "board_data": False, "rst_t": None, "rst_ack_before": None, "fin": False,
                                                              "hs_ack_t": None, "req": None, "clen": None, "status": None})
    current = None  # (port, from_board) of the packet whose -A text follows
    for line in sys.stdin:
        m = HDR.match(line)
        if not m:
            if current is not None:
                port, from_board = current
                c = conns[port]
                if from_board:
                    if c["status"] is None and (r := RESP.search(line)):
                        c["status"] = r.group(1)
                else:
                    if c["req"] is None and (r := REQ.search(line)):
                        c["req"] = f"{r.group(1)} {r.group(2)}"
                    if c["clen"] is None and (r := CLEN.search(line)):
                        c["clen"] = int(r.group(1))
            continue
        t, src, sport, dst, dport, flags, rest = float(m.group(1)), m.group(2), int(m.group(3)), m.group(4), int(m.group(5)), m.group(6), m.group(7)
        if src == dut and sport == 80:
            port, from_board = dport, True
        elif dst == dut and dport == 80:
            port, from_board = sport, False
        else:
            current = None
            continue
        current = (port, from_board)
        c = conns[port]
        seq, ack, length = SEQ.search(rest), ACK.search(rest), LEN.search(rest)
        n = int(length.group(1)) if length else 0
        if from_board:
            if "S" in flags:
                c["synack"] = True
            if n > 0 and "R" not in flags:
                c["board_data"] = True
            if "R" in flags and c["rst_t"] is None:
                c["rst_t"], c["rst_ack_before"] = t, c["board_max_ack"]
            if "F" in flags:
                c["fin"] = True
            if ack and "R" not in flags:
                c["board_max_ack"] = max(c["board_max_ack"], int(ack.group(1)))
        else:
            if flags == "S":
                c["syn_count"] += 1
                if seq and c["isn"] is None:
                    c["isn"] = int(seq.group(1))
            elif flags == "." and c["hs_ack_t"] is None and n == 0:
                c["hs_ack_t"] = t
    tally: collections.Counter = collections.Counter()
    gaps: dict[str, list[float]] = collections.defaultdict(list)
    for c in conns.values():
        if not c["synack"]:
            kind = "no SYN-ACK"
        elif c["board_data"]:
            kind = f"answered {c['status'] or '?'}"
        elif c["rst_t"] is not None and c["isn"] is not None and c["rst_ack_before"] <= c["isn"] + 1:
            kind = "reset at the handshake (no request byte acknowledged)"
        elif c["rst_t"] is not None:
            kind = "reset after queueing (request acknowledged, no response byte)"
        elif c["fin"]:
            kind = "closed with no response byte"
        else:
            kind = "unfinished"
        size = "?" if c["clen"] is None else ("within cap" if c["clen"] <= cap else "over cap")
        tally[(kind, c["req"] or "(no request seen)", size)] += 1
        if c["rst_t"] is not None and c["hs_ack_t"] is not None and not c["board_data"]:
            gaps[kind].append((c["rst_t"] - c["hs_ack_t"]) * 1000)
        if c["syn_count"] > 1:
            tally[("SYN retransmitted", c["req"] or "(no request seen)", size)] += 1
    print(f"connections: {len(conns)}")
    for (kind, req, size), count in sorted(tally.items()):
        print(f"{count:4d}  {kind} | {req} | {size}")
    for kind, values in sorted(gaps.items()):
        values.sort()
        print(f"handshake ACK -> board RST, {kind}: n={len(values)} min {values[0]:.1f} ms, median {values[len(values) // 2]:.1f} ms, max {values[-1]:.1f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
