import asyncio
import select
import socket

import test_asy_wifi_service as t

client = t.make_client()
client._dns_server.pr.set_level(5)
server_addr = t._make_addr()


async def scenario():
    await t._start_real_hotspot(client, server_addr)
    cli = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cli.setblocking(False)
    target = socket.getaddrinfo(*server_addr)[0][-1]
    print("target", target)
    cli.sendto(b"\x01\x02", target)
    cli.sendto(t._dns_query_packet("after.example.com"), target)
    poller = select.poll()
    poller.register(cli, select.POLLIN)
    for _ in range(50):
        ev = list(poller.ipoll(0))
        if any(e & select.POLLIN for _f, e in ev):
            print("reply", cli.recv(512))
        await asyncio.sleep_ms(20)
    print("alive", not client._dns_server_task.done(), client._dns_server._udps.connected)
    await t._cancel(client._dns_server_task)

t.run(scenario())
