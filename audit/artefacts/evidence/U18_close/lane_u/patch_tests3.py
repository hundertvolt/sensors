import sys
p = sys.argv[1]
s = open(p).read()

def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (old[:100], n)
    s = s.replace(old, new)

rep('''# ---------------------------------------------------------------------------
# ready()'s default wait_time_ms must not busy-spin
# ---------------------------------------------------------------------------


class _RecordingAsyncio:
    # asyncio is a read-only builtin on MicroPython (the same reason _RaisingSocketModule below
    # replaces asy_udp_socket's own module-level `socket` name), so this wraps the real module,
    # recording every sleep_ms() duration while still sleeping, keeping ready()'s logic intact.
    def __init__(self, real: "ModuleType") -> None:
        self._real = real
        self.sleep_ms_calls: list[int] = []

    def sleep_ms(self, ms: int) -> "Awaitable[None]":
        self.sleep_ms_calls.append(ms)
        # Bound to its own local first: a module attribute is statically untyped, and this
        # wrapper's own callers (ready()'s poll loop) do await what it hands back.
        sleeper: Awaitable[None] = self._real.sleep_ms(ms)
        return sleeper

    def __getattr__(self, name: str) -> object:
        return getattr(self._real, name)


def test_ready_default_wait_time_ms_does_not_busy_spin() -> None:
    # wait_time_ms defaulted to 0, which busy-polls ipoll(0)+sleep_ms(0) ~9000x/sec while idle
    # (~180x the rate at 20ms) - pure CPU churn on RP2040's single core for the two real callers
    # that never override it. Proves the fixed 20ms default is what ready() actually uses.
    addr = _make_addr()
    recorder = _RecordingAsyncio(asy_udp_socket.asyncio)
    asy_udp_socket.asyncio = recorder  # type: ignore[assignment]
    try:
        sock = UDPSocket(addr, mode="server")
        try:
            run(sock.ready(select.POLLIN, timeout_ms=_READY_EMPTY_TIMEOUT_MS))  # nothing ever arrives
        finally:
            run(sock.disconnect())
    finally:
        asy_udp_socket.asyncio = recorder._real

    assert len(recorder.sleep_ms_calls) > 0
    assert all(ms == 20 for ms in recorder.sleep_ms_calls)
''', '''# ---------------------------------------------------------------------------
# ready()'s two poll rates: _POLL_WAIT_MS with a deadline, _POLL_IDLE_MS without one
# ---------------------------------------------------------------------------


class _EnoughRoundsError(Exception):
    pass


class _RecordingAsyncio:
    # asyncio is a frozen Python package whose attributes tests may assign (test_asy_bmp3xx_driver.py patches asyncio.sleep);
    # this wraps it instead so the recording also sees ready()'s own sleep_ms() calls through asy_udp_socket's module-level
    # name, the way _RaisingSocketModule replaces the read-only C `socket`. stop_after > 0 ends a wait with no deadline.
    def __init__(self, real: "ModuleType", stop_after: int = 0) -> None:
        self._real = real
        self.sleep_ms_calls: list[int] = []
        self._stop_after = stop_after

    def sleep_ms(self, ms: int) -> "Awaitable[None]":
        self.sleep_ms_calls.append(ms)
        if self._stop_after and len(self.sleep_ms_calls) >= self._stop_after:
            raise _EnoughRoundsError
        # Bound to its own local first: a module attribute is statically untyped, and this
        # wrapper's own callers (ready()'s poll loop) do await what it hands back.
        sleeper: Awaitable[None] = self._real.sleep_ms(ms)
        return sleeper

    def __getattr__(self, name: str) -> object:
        return getattr(self._real, name)


def _record_ready_sleeps(timeout_ms: int, stop_after: int = 0) -> "list[int]":
    # ready(POLLIN) on a bound socket nothing ever reaches; a wait with no deadline ends at the recorder's stop_after.
    recorder = _RecordingAsyncio(asy_udp_socket.asyncio, stop_after)
    asy_udp_socket.asyncio = recorder  # type: ignore[assignment]
    try:
        sock = UDPSocket(_make_addr(), mode="server")
        try:
            run(sock.ready(select.POLLIN, timeout_ms=timeout_ms))
            assert not stop_after, "ready() returned with nothing to read and no deadline"
        except _EnoughRoundsError:
            pass
        finally:
            run(sock.disconnect())
    finally:
        asy_udp_socket.asyncio = recorder._real
    return recorder.sleep_ms_calls


def test_ready_with_a_deadline_polls_at_the_transaction_rate() -> None:
    # A wait with a deadline sits inside an exchange (DNS, NTP): every round sleeps _POLL_WAIT_MS, never
    # a busy-spin of ipoll(0)+sleep_ms(0) on RP2040's single core.
    sleeps = _record_ready_sleeps(_READY_EMPTY_TIMEOUT_MS)
    assert len(sleeps) > 0
    assert all(ms == _src_const("_POLL_WAIT_MS") for ms in sleeps), sleeps


def test_ready_without_a_deadline_polls_at_the_idle_rate() -> None:
    # A wait with no deadline is a listen that may never be answered (the captive DNS): every round
    # sleeps the slower _POLL_IDLE_MS (SPECIFICATION.md F.5.9's shape).
    sleeps = _record_ready_sleeps(-1, stop_after=2)
    assert len(sleeps) == 2, sleeps
    assert all(ms == _src_const("_POLL_IDLE_MS") for ms in sleeps), sleeps


# lwIP's per-socket UDP receive queue on rp2: extmod/modlwip.c:299 LWIP_INCOMING_PACKET_QUEUE_LEN, v1.29.0.
_LWIP_UDP_QUEUE_LEN = 4


def test_queued_datagrams_are_read_without_an_idle_sleep() -> None:
    # Every ready() reads ipoll(0) before it sleeps, so a listener drains a full lwIP queue back to back:
    # no poll round sleeps between the queued datagrams, and the whole drain fits inside one _POLL_IDLE_MS.
    addr = _make_addr()
    recorder = _RecordingAsyncio(asy_udp_socket.asyncio)

    async def scenario() -> "tuple[list[bytes | None], int]":
        server = UDPSocket(addr, mode="server")
        peer = _AdversarialPeer(_make_addr())
        try:
            await server._connect()
            for i in range(_LWIP_UDP_QUEUE_LEN):
                peer.send(f"q-{i}".encode(), addr)
            await asyncio.sleep(_KERNEL_QUEUE_S)  # all queued before the drain starts
            asy_udp_socket.asyncio = recorder  # type: ignore[assignment]
            got: list[bytes | None] = []
            t0 = time.ticks_ms()
            for _ in range(_LWIP_UDP_QUEUE_LEN):
                data, _ = await server.recvfrom(64)  # no deadline: the captive DNS listen's call
                got.append(data)
            return got, time.ticks_diff(time.ticks_ms(), t0)
        finally:
            asy_udp_socket.asyncio = recorder._real
            peer.close()
            await server.disconnect()

    got, elapsed = run(scenario())
    assert got == [f"q-{i}".encode() for i in range(_LWIP_UDP_QUEUE_LEN)]
    assert recorder.sleep_ms_calls == [], recorder.sleep_ms_calls
    assert elapsed < _src_const("_POLL_IDLE_MS"), elapsed
''')

open(p, "w").write(s)
