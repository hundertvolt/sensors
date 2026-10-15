ns = {"__name__": "probe"}
exec(open("tests/test_asy_captive_dns.py").read(), ns)
res = []
for _ in range(10):
    for name in ("test_run_yields_once_per_datagram_while_the_socket_stays_ready", "test_run_answers_queued_queries_back_to_back"):
        try:
            ns[name]()
            res.append("P")
        except AssertionError:
            res.append("F:" + name[:20])
print(" ".join(res))
