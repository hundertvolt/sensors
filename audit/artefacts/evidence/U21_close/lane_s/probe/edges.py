# Scratch probe (lane S, not in the repo): every write's outcome in the hammer's load and capacity cases.
ns = {"__name__": "edges_probe"}
exec(open("tests/lwip_host/test_modlwip_eagain.py").read(), ns)
REF = ns["_REFUSED"]


def trace(sock, piece, pump, limit=400):
    out = []
    for _ in range(limit):
        w = ns["_timed_write"](sock, piece)
        out.append("E" if w is None else ("M" if w == REF else w))
        if w is None or w == REF:
            break
        if pump:
            ns["_pump"]()
    return out


def summary(out):
    n = sum(x for x in out if isinstance(x, int))
    return "%d writes, %d B, end %s, writable %s" % (len(out), n, out[-1], "?")


for rnd in range(3):
    pairs = ns["_open_all"]()
    print("round", rnd, "pairs", len(pairs))
    for i, (c, s) in enumerate(pairs[:-1]):
        out = trace(c, ns["_LOAD_PIECE"], True)
        print(" loader", i, summary(out), "POLLOUT", ns["_writable"](c))
    c, s = pairs[-1]
    out = trace(c, ns["_LOAD_PIECE"], False)
    print(" last", summary(out), "POLLOUT", ns["_writable"](c), out[:6])
    ns["_close"](pairs, reset=True)
    for k in range(3):
        pair = ns["_open_pair"]()
        out = trace(pair[0], ns["_MSS_PIECE"], True)
        print(" capacity", summary(out), "POLLOUT", ns["_writable"](pair[0]))
        ns["_close"]([pair], reset=True)
