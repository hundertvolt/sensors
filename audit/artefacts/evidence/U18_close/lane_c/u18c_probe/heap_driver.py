ns = {"__name__": "probe"}
exec(open("tests/test_asy_captive_dns.py").read(), ns)
asyncio = ns["asyncio"]
for label, incoming in (("data", (ns["_HeapFailingParse"](), ("127.0.0.5", 5000))), ("host", (ns["make_query"](["a", "io"]), (ns["_HeapFailingParse"](), 5000)))):
    fake = ns["_FakeUDPS"]([incoming])
    async def scenario():
        server = ns["CaptiveDNS"](log=ns["LogConfig"](None, 10, 1))
        server._udps = fake
        task = asyncio.create_task(server.run("127.0.0.1", "255.0.0.0"))
        ok = await ns["_wait_until"](lambda: server.pr._err_count >= 1)
        await ns["_cancel"](task)
        return ok, server.pr._err_count
    print(label, ns["run"](scenario()))
