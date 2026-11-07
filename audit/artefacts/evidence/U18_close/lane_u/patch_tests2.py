import sys
p = sys.argv[1]
s = open(p).read()

def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (old[:100], n)
    s = s.replace(old, new)

# --- E. failed send test after the exhaust test
rep('''    data, from_addr = run(scenario())
    assert data is None
    assert from_addr is None


# ---------------------------------------------------------------------------
# _connect() retry/self-heal
# ---------------------------------------------------------------------------


class _AdversarialPeer:''', '''    data, from_addr = run(scenario())
    assert data is None
    assert from_addr is None


def test_a_failed_send_returns_without_waiting_for_a_reply() -> None:
    # A try whose write() failed never sent its request, so nothing can answer it: write_and_recvfrom()
    # moves on at once instead of waiting out timeout_ms for a reply that cannot come.
    addr = _make_addr()

    async def scenario() -> "tuple[tuple[bytes | None, tuple[str, int] | None], int]":
        client = UDPSocket(addr, mode="client")
        try:
            await client._connect()
            assert client._sock is not None
            client._sock = _FailingSocket(client._sock, "write", OSError("injected send failure"))  # type: ignore[assignment]
            t0 = time.ticks_ms()
            result = await client.write_and_recvfrom(b"x", 64, timeout_ms=_REPLY_TIMEOUT_MS, tries=1)
            return result, time.ticks_diff(time.ticks_ms(), t0)
        finally:
            await client.disconnect()

    result, elapsed = run(scenario())
    assert result == (None, None)
    assert elapsed < _REPLY_TIMEOUT_MS // 2, elapsed


# ---------------------------------------------------------------------------
# _connect() retry/self-heal
# ---------------------------------------------------------------------------


class _AdversarialPeer:''')

# --- F. the peer binds through _raw and sends to a tuple through send()
rep('''        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(addr)
        self.sock.setblocking(False)

    async def send_after(''', '''        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(_raw(addr))
        self.sock.setblocking(False)

    def send(self, data: bytes, target: tuple[str, int]) -> None:  # to a UDPSocket under test, by its plain tuple
        self.sock.sendto(data, _raw(target))

    async def send_after(''')

for old, new in (
    ("peer.sock.sendto(oversized, addr)", "peer.send(oversized, addr)"),
    ('peer.sock.sendto(b"", addr)', 'peer.send(b"", addr)'),
    ('peer.sock.sendto(f"pkt-{i}".encode(), addr)', 'peer.send(f"pkt-{i}".encode(), addr)'),
    ('peer.sock.sendto(b"data", addr)', 'peer.send(b"data", addr)'),
    ('peer.sock.sendto(b"real query", addr)', 'peer.send(b"real query", addr)'),
    ('peer.sock.sendto(b"next real query", addr)', 'peer.send(b"next real query", addr)'),
):
    rep(old, new)
rep('peer.sock.sendto(b"real data", addr)', 'peer.send(b"real data", addr)', count=2)

open(p, "w").write(s)
