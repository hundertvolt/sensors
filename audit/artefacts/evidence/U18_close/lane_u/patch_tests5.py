import sys
p = sys.argv[1]
s = open(p).read()

def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (old[:100], n)
    s = s.replace(old, new)

rep('''import asy_print_log
import asy_udp_socket
from asy_udp_socket import UDPSocket
''', '''import asy_print_log
import asy_udp_socket
from asy_dns_client import DNS_UDP_MAX
from asy_udp_socket import UDPSocket
''')

rep('''    # Mirrors asy_captive_dns.py's exact call shape: a server-mode socket bound to ("0.0.0.0", port),
    # recvfrom(4096), conditional sendto(response, addr) - including the real bind-any-interface
    # then receive-via-127.0.0.1 path that every other test in this file skips.
    port = _make_port()
    server_addr = ("0.0.0.0", port)
    query = b"\\x00\\x01fake-dns-query"
    response = b"\\x00\\x01fake-dns-response"

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None, bytes]:
        server = UDPSocket(server_addr, mode="server")
        client = _AdversarialPeer(_make_addr())
        try:
            await server._connect()
            client.send(query, ("127.0.0.1", port))
            data, addr = await server.recvfrom(4096, timeout_ms=_LONG_REPLY_TIMEOUT_MS)''', '''    # Mirrors asy_captive_dns.py's exact call shape: a server-mode socket bound to ("0.0.0.0", port),
    # recvfrom(DNS_UDP_MAX), conditional sendto(response, addr) - including the real bind-any-interface
    # then receive-via-127.0.0.1 path that every other test in this file skips.
    port = _make_port()
    server_addr = ("0.0.0.0", port)
    client_addr = _make_addr()
    query = b"\\x00\\x01fake-dns-query"
    response = b"\\x00\\x01fake-dns-response"

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None, bytes]:
        server = UDPSocket(server_addr, mode="server")
        client = _AdversarialPeer(client_addr)
        try:
            await server._connect()
            client.send(query, ("127.0.0.1", port))
            data, addr = await server.recvfrom(DNS_UDP_MAX, timeout_ms=_LONG_REPLY_TIMEOUT_MS)''')
rep('''    data, addr, reply = run(scenario())
    assert data == query
    # addr's exact representation is platform-opaque on this Unix-port build too (recvfrom()
    # returns a raw bytearray sockaddr, the same quirk _make_addr()/resolve_addr() work around) -
    # only its existence, used to route the reply below, is this test's concern.
    assert addr is not None
    assert reply == response''', '''    data, addr, reply = run(scenario())
    assert data == query
    assert addr == client_addr  # the sender, as the (host, port) tuple every received address is
    assert reply == response''')

# --- M. fifth pass
rep('''# mutation of _addr/_conn_tries can still reach the shapes it was meant to prevent. Closed by''',
    '''# mutation of _addr can still reach the shapes it was meant to prevent. Closed by''')
start = s.index('def test_connect_self_heals_when_conn_tries_mutated_to_a_non_int() -> None:')
end = s.index('def test_connect_treats_a_mutated_mode_as_server_like_without_crashing() -> None:')
s = s[:start] + s[end:]

# --- N. concurrency
rep('''    # _connect() retry could null self._sock/self.poller out from under it. disconnect() now takes
    # the same lock, waiting for the attempt (bounded by conn_tries * the backoff) instead.
    bad_addr = _unbindable_addr()

    async def scenario() -> tuple[bool, int]:
        sock = UDPSocket(bad_addr, mode="server", conn_tries=3)''', '''    # _connect() retry could null self._sock/self.poller out from under it. disconnect() now takes
    # the same lock, waiting for the attempt (bounded by one backoff) instead.
    bad_addr = _unbindable_addr()

    async def scenario() -> tuple[bool, int]:
        sock = UDPSocket(bad_addr, mode="server")''')
rep('''    assert elapsed >= 1000  # disconnect() genuinely waited for the ~1.5s (3 tries) retry cycle''',
    '''    # disconnect() waited out the one backoff the failed attempt holds the lock for
    assert elapsed >= int(_src_const("_RETRY_BACKOFF_S") * 1000) - int(_FIRST_ATTEMPT_S * 1000), elapsed''')

rep('''    # A coroutine calling a public method while another's _connect() was mid-retry used to get a
    # spurious None immediately instead of waiting. B's sendto() must block until A's connect
    # resolves and then genuinely succeed, not start a redundant retry of its own.
    bad_addr = _unbindable_addr()
    good_addr = _make_addr()

    async def scenario() -> tuple[bool, int | None]:
        sock = UDPSocket(bad_addr, mode="server", conn_tries=3)
        try:
            a_task = asyncio.create_task(sock._connect())
            await asyncio.sleep(0.1)  # A has failed its first attempt, is backing off

            async def fix_address_soon() -> None:
                await asyncio.sleep(0.5)
                sock._addr = good_addr

            fixer = asyncio.create_task(fix_address_soon())
            b_task = asyncio.create_task(sock.sendto(b"x", good_addr))
            await a_task
            await fixer
            b_result = await b_task''', '''    # A coroutine calling a public method while another's _connect() was mid-retry used to get a
    # spurious None immediately instead of waiting. B's sendto() must block until A's attempt
    # resolves, then genuinely succeed on the fresh attempt it makes once A's has failed.
    bad_addr = _unbindable_addr()
    good_addr = _make_addr()

    async def scenario() -> tuple[bool, int | None]:
        sock = UDPSocket(bad_addr, mode="server")
        try:
            a_task = asyncio.create_task(sock._connect())
            await asyncio.sleep(0.1)  # A has failed its first attempt, is backing off
            sock._addr = good_addr  # the fault clears while A still holds the lock
            b_task = asyncio.create_task(sock.sendto(b"x", good_addr))
            await a_task
            b_result = await b_task''')
rep('''        sock = UDPSocket(bad_addr, mode="server", conn_tries=5)''', '''        sock = UDPSocket(bad_addr, mode="server")''')
rep('''        sock = UDPSocket(bad_addr, mode="server", conn_tries=3)''', '''        sock = UDPSocket(bad_addr, mode="server")''')

# --- O. sixth pass
rep('''# Sixth pass: ready()'s mask/timeout_ms/wait_time_ms and write_and_recvfrom()'s tries were never''',
    '''# Sixth pass: ready()'s mask/timeout_ms and write_and_recvfrom()'s tries were never''')
start = s.index('def test_ready_returns_false_sentinel_for_a_malformed_wait_time_ms() -> None:')
end = s.index('def test_ready_returns_false_sentinel_for_a_malformed_mask() -> None:')
s = s[:start] + s[end:]
rep('''            task = asyncio.create_task(sock.ready(select.POLLIN, timeout_ms=-1, wait_time_ms=20))  # waits forever''',
    '''            task = asyncio.create_task(sock.ready(select.POLLIN, timeout_ms=-1))  # waits forever''')

open(p, "w").write(s)
