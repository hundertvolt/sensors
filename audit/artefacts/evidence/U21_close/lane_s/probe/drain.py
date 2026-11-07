# Scratch probe (lane S, not in the repo): the load-drain cycle's per-loader edges and byte accounting.
ns = {"__name__": "drain_probe"}
exec(open("tests/lwip_host/test_modlwip_eagain.py").read(), ns)
REF = ns["_REFUSED"]
print("capacity first:", ns["_capacity"]())
for rnd in range(2):
    pairs = ns["_open_all"]()
    ends = [ns["_write_to_edge"](c, ns["_LOAD_PIECE"], pump=True) for c, _ in pairs]
    print("edges", [(n, "EAGAIN" if e is None else "ENOMEM") for n, e in ends])
    rec = [0] * len(pairs)
    for _ in range(3000):
        for i, (_, s) in enumerate(pairs):
            rec[i] += ns["_drain"](s)
        ns["_pump"]()
    print("received", rec)
    ns["_close"](pairs, reset=False)
