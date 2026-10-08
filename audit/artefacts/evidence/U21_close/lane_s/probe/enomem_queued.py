# Scratch probe (lane S, not in the repo): does a write that raised ENOMEM still deliver its bytes?
ns = {"__name__": "enomem_probe"}
exec(open("tests/lwip_host/test_modlwip_eagain.py").read(), ns)
pairs = ns["_open_all"]()
c0, s0 = pairs[0]
c1, s1 = pairs[1]
n0, end0 = ns["_write_to_edge"](c0, ns["_LOAD_PIECE"], pump=True)
w1 = ns["_timed_write"](c1, b"\x11" * 256)
print("loader0", n0, "end", end0, "| loader1 first write ->", w1)
s0.close()  # unread data: RST, loader 0's queue freed on the next pump
ns["_pump"](200)
got = b""
for _ in range(200):
    try:
        got += s1.recv(1024)
    except OSError:
        pass
    ns["_pump"]()
print("loader1's peer received", len(got), "B", "all 0x11" if got == b"\x11" * len(got) else "other bytes")
