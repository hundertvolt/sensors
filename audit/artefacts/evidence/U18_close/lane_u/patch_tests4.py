import sys
p = sys.argv[1]
s = open(p).read()

def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (old[:100], n)
    s = s.replace(old, new)

rep('''            return await sock.ready(select.POLLIN, timeout_ms=_RECV_TIMEOUT_MS, wait_time_ms=10)''',
    '''            return await sock.ready(select.POLLIN, timeout_ms=_RECV_TIMEOUT_MS)''')

# --- J. _connect() retry/self-heal
rep('''    # socket would not work: SO_REUSEADDR, set by _connect() itself, lets a second UDP socket bind.
    return socket.getaddrinfo("10.255.255.254", 51999)[0][-1]  # type: ignore[return-value]


def test_conn_tries_retries_within_a_single_connect_call() -> None:
    bad_addr = _unbindable_addr()
    good_addr = _make_addr()

    async def scenario() -> bool:
        contender = UDPSocket(bad_addr, mode="server", conn_tries=3)
        try:

            async def fix_address_soon() -> None:
                await asyncio.sleep(0.6)  # after >=1 failed attempt (0.5s backoff), before conn_tries=3 is exhausted (1.5s)
                contender._addr = good_addr

            fixer = asyncio.create_task(fix_address_soon())
            await contender._connect()  # early attempt(s) fail against bad_addr, then addr is fixed mid-retry
            await fixer
            return contender.connected
        finally:
            await contender.disconnect()

    assert run(scenario())


def test_connect_self_heals_after_conn_tries_exhausted() -> None:
    # Bug: once self._sock was created, a fully-exhausted conn_tries left _connect() a permanent
    # no-op (self._sock stayed non-None) - the object was stuck forever. It must now tear itself
    # down so a later call gets a fresh attempt.
    bad_addr = _unbindable_addr()
    good_addr = _make_addr()

    async def scenario() -> tuple[bool, bool, bool]:
        contender = UDPSocket(bad_addr, mode="server", conn_tries=1)
        try:
            await contender._connect()  # exhausts its single try against an unbindable address''',
    '''    # socket would not work: SO_REUSEADDR, set by _connect() itself, lets a second UDP socket bind.
    return ("10.255.255.254", 51999)


def test_connect_self_heals_after_a_failed_bind() -> None:
    # Bug: once self._sock was created, a failed attempt left _connect() a permanent
    # no-op (self._sock stayed non-None) - the object was stuck forever. It must now tear itself
    # down so a later call gets a fresh attempt.
    bad_addr = _unbindable_addr()
    good_addr = _make_addr()

    async def scenario() -> tuple[bool, bool, bool]:
        contender = UDPSocket(bad_addr, mode="server")
        try:
            await contender._connect()  # its one attempt fails against an unbindable address''')

# --- ms test
rep('''# ---------------------------------------------------------------------------
# ready()'s wait_time_ms must be milliseconds, not seconds
# ---------------------------------------------------------------------------


def test_ready_wait_time_ms_is_milliseconds_not_seconds() -> None:
    # Bug: ready() used to call asyncio.sleep(wait_time_ms) (seconds), not asyncio.sleep_ms() -
    # a wait_time_ms=10 would sleep 10 real seconds per poll cycle instead of 10ms. Prove a
    # bounded-timeout call actually completes in tens of milliseconds, not multiple real seconds.
    addr = _make_addr()

    async def scenario() -> int:
        sock = UDPSocket(addr, mode="server")
        try:
            t0 = time.ticks_ms()
            result = await sock.ready(select.POLLIN, timeout_ms=_MS_CHECK_TIMEOUT_MS, wait_time_ms=10)
            assert result is False  # nothing ever arrives
            return time.ticks_diff(time.ticks_ms(), t0)
        finally:
            await sock.disconnect()

    elapsed = run(scenario())
    assert elapsed < _MS_CHECK_ELAPSED_MAX_MS  # generously below the 10000ms+ the old seconds-interpretation bug would take
''', '''# ---------------------------------------------------------------------------
# ready()'s poll rates must be milliseconds, not seconds
# ---------------------------------------------------------------------------


def test_ready_sleeps_milliseconds_not_seconds() -> None:
    # Bug: ready() used to call asyncio.sleep() (seconds), not asyncio.sleep_ms(), so a 20 ms rate slept 20
    # real seconds per round. Both rates reach sleep_ms() as whole milliseconds (20 and 100, never 0.02 or
    # 0.1), and a bounded call completes in tens of milliseconds, not multiple real seconds.
    t0 = time.ticks_ms()
    with_deadline = _record_ready_sleeps(_MS_CHECK_TIMEOUT_MS)
    elapsed = time.ticks_diff(time.ticks_ms(), t0)
    without_deadline = _record_ready_sleeps(-1, stop_after=1)
    assert with_deadline and all(isinstance(ms, int) and ms == _src_const("_POLL_WAIT_MS") for ms in with_deadline), with_deadline
    assert without_deadline == [_src_const("_POLL_IDLE_MS")] and isinstance(without_deadline[0], int), without_deadline
    assert elapsed < _MS_CHECK_ELAPSED_MAX_MS  # generously below the 10000ms+ the old seconds-interpretation bug would take
''')

# --- K. the context-manager section goes
start = s.index('''# ---------------------------------------------------------------------------
# async with support
# ---------------------------------------------------------------------------''')
end = s.index('''# ---------------------------------------------------------------------------
# Integration-level: the exact real-world call patterns''')
s = s[:start] + s[end:]

# --- L. NTP patterns pass tries=1; DNS pattern with tuples
rep('''            msg, add = await cli.write_and_recvfrom(ntp_request, 1024, timeout_ms=_LONG_REPLY_TIMEOUT_MS)''',
    '''            msg, add = await cli.write_and_recvfrom(ntp_request, 1024, timeout_ms=_LONG_REPLY_TIMEOUT_MS, tries=1)''')
rep('''            msg, add = await cli.write_and_recvfrom(ntp_request, 1024, timeout_ms=_UNREACHABLE_TIMEOUT_MS)''',
    '''            msg, add = await cli.write_and_recvfrom(ntp_request, 1024, timeout_ms=_UNREACHABLE_TIMEOUT_MS, tries=1)''')
rep('''            msg, _ = await cli.write_and_recvfrom(ntp_request, 1024, timeout_ms=_LONG_REPLY_TIMEOUT_MS)''',
    '''            msg, _ = await cli.write_and_recvfrom(ntp_request, 1024, timeout_ms=_LONG_REPLY_TIMEOUT_MS, tries=1)''')

rep('''    port = _make_port()
    server_addr = resolve_addr("0.0.0.0", port)
    client_target_addr = resolve_addr("127.0.0.1", port)
''', '''    port = _make_port()
    server_addr = ("0.0.0.0", port)
''')
rep('''        client = _AdversarialPeer(_make_addr())
        try:
            await server._connect()
            client.sock.sendto(query, client_target_addr)''', '''        client = _AdversarialPeer(_make_addr())
        try:
            await server._connect()
            client.send(query, ("127.0.0.1", port))''')

open(p, "w").write(s)
