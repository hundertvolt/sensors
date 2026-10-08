"""The patched modlwip send path on build-lwip, the Unix port over loopback lwIP (SPECIFICATION.md B.14): each
non-blocking write is bounded at every pool edge, a reading peer gets every byte, capacity returns. One listener
serves the whole file, never closed: modlwip's close() trips lwIP's LISTEN-state assert, which aborts here."""

import errno
import gc
import select
import time

import lwip

# One write's bound; the unpatched ERR_MEM loop holds a non-blocking write for up to 10,000 ms
# (extmod/modlwip.c, 200 rounds of mp_hal_delay_ms(50)).
# @tunable l1.lwip_host_write_bound_ms = 250
_WRITE_BOUND_MS = 250
# How long a fresh connection's handshake may take before the pool counts as exhausted.
# @tunable l1.lwip_host_connect_bound_ms = 200
_CONNECT_BOUND_MS = 200
# Covers modlwip's 10 s close-abort (MICROPY_PY_LWIP_TCP_CLOSE_TIMEOUT_MS) with margin.
# @tunable l1.lwip_host_recovery_s = 15
_RECOVERY_S = 15
# @tunable l1.lwip_host_rounds = 20
_ROUNDS = 20
# @tunable l1.lwip_host_spin_rounds = 1000
_SPIN_ROUNDS = 1000
# One drain() round on this host includes select's own 1 ms poll() sleep (modselect.c); the
# unpatched path sleeps 50 ms per round instead, so the bound stays well below that.
# @tunable l1.lwip_host_spin_round_max_us = 20000
_SPIN_ROUND_MAX_US = 20000
# @tunable l1.lwip_host_spin_round_alloc_max_b = 64
_SPIN_ROUND_ALLOC_MAX_B = 64

_HOST = "127.0.0.1"
_PORT = 50000
_PATTERN_PIECE = 256
_QUEUE_PIECE = b"\x5a" * 16
_SEGMENT_PIECE = b"\x3c"
_PATTERN_BYTES = 32768
_PATTERN_PERIOD = 251
# recv() hands back at most one received segment, never more than this.
_RECV_CHUNK = 1024
_PATTERN = bytes(i % _PATTERN_PERIOD for i in range(_PATTERN_PERIOD + _RECV_CHUNK))
_SETTLE_MS = 100
# What _timed_write() returns for a write() that raised ENOMEM: tcp_output found no arena for a
# loopback copy, and the piece may still be queued (modlwip reports tcp_output's error after tcp_write).
_REFUSED = -1
_MAX_WRITES = 400
_ARENA_FULL_WRITES = 20
_FILL_ATTEMPTS = 10


def _lwip_table() -> "dict[str, int]":
    # versions.toml's [lwip] table, the values build-lwip was compiled with (read here, as the build does).
    table: dict[str, int] = {}
    section = ""
    with open("toolchain/versions.toml") as f:
        for raw in f:
            line = raw.split("#", 1)[0].strip()
            if line.startswith("["):
                section = line
            elif section == "[lwip]" and "=" in line:
                name, value = line.split("=", 1)
                table[name.strip()] = int(value.strip())
    return table


_LWIP = _lwip_table()
_MSS = _LWIP["TCP_MSS"]
_MSS_PIECE = b"\x96" * _MSS
_SEGMENT_POOL = _LWIP["MEMP_NUM_TCP_SEG"]
# lwIP's own default for the per-connection queue limit (lib/lwip/src/include/lwip/opt.h).
_QUEUE_LIMIT = (4 * _LWIP["TCP_SND_BUF"] + (_MSS - 1)) // _MSS

# Once per process: nothing else on the Unix port initialises lwIP, and a second lwip_init()
# would re-add the loopback netif under live pcbs.
lwip.reset()


def _listen() -> "lwip.socket":
    listener = lwip.socket()
    listener.setsockopt(lwip.SOL_SOCKET, lwip.SO_REUSEADDR, 1)
    listener.bind((_HOST, _PORT))
    listener.listen(2)
    listener.setblocking(False)
    return listener


_LISTENER = _listen()  # never closed - the header says why


def _assert_patched_edge(sock: "lwip.socket", edge: str) -> None:
    # EAGAIN with POLLOUT set is the patched ERR_MEM branch; with POLLOUT clear it is the send buffer.
    assert _writable(sock), f"the {edge} edge arrived with POLLOUT clear: that is the send-buffer edge (tcp_sndbuf 0), not the patched ERR_MEM branch - adjust the piece size"


def _capacity() -> int:
    # A fresh connection's total, in MSS pieces, to a peer that never reads, up to its edge.
    pair = _open_pair()
    assert pair is not None, "a fresh connection could not be opened"
    try:
        return _write_until_eagain(pair[0], _MSS_PIECE, pump=True)
    finally:
        _close([pair], reset=True)


def _close(pairs: "list[tuple[lwip.socket, lwip.socket]]", *, reset: bool) -> None:
    # reset: the server side first, which lwIP answers with RST while data sits unread, so the
    # client's queue goes at once; otherwise the client first, a graceful close.
    for client, server in pairs:
        for sock in (server, client) if reset else (client, server):
            sock.close()
    _pump(_SETTLE_MS)


def _drain(server: "lwip.socket") -> int:
    # Everything readable now, without waiting.
    got = 0
    while True:
        try:
            chunk = server.recv(_RECV_CHUNK)
        except OSError as e:
            if e.errno == errno.EAGAIN:
                return got
            raise
        if not chunk:
            return got
        got += len(chunk)


def _drain_all(pairs: "list[tuple[lwip.socket, lwip.socket]]", owed: int) -> None:
    # Until the first peer has what it is owed, then a further fast-timer period in which nothing more
    # arrives at any peer.
    deadline = time.ticks_add(time.ticks_ms(), _RECOVERY_S * 1000)
    received = [0] * len(pairs)
    expected = [owed] + [0] * (len(pairs) - 1)
    while received != expected:
        assert time.ticks_diff(deadline, time.ticks_ms()) > 0, f"the readers drained {received} of {expected} B within {_RECOVERY_S} s"
        for i, (_, server) in enumerate(pairs):
            received[i] += _drain(server)
        _pump()
    _pump(_SETTLE_MS * 3)
    for i, (_, server) in enumerate(pairs):
        received[i] += _drain(server)
    assert received == expected, f"the readers received {received} B, owed {expected} B"


def _load(pairs: "list[tuple[lwip.socket, lwip.socket]]") -> int:
    # The first client fills the arena with whole-MSS writes to a peer that never reads, until its
    # zero-window EAGAIN holds after a settle; every other client's MSS write then finds no room for its
    # segment and EAGAINs before anything is sent. Returns the bytes the first peer is owed.
    owed = 0
    for _ in range(_FILL_ATTEMPTS):
        written = _write_until_eagain(pairs[0][0], _MSS_PIECE, pump=True)
        owed += written
        if written == 0 and owed > 0:
            break
        _pump(_SETTLE_MS)
    else:
        raise AssertionError(f"the arena still took writes after {_FILL_ATTEMPTS} settles ({owed} B)")
    for index, (client, _) in enumerate(pairs[1:], 1):
        assert _timed_write(client, _MSS_PIECE) is None, f"loader {index}'s first write into the full arena was not EAGAIN"
    return owed


def _load_drain_close() -> None:
    pairs = _open_all()
    try:
        assert len(pairs) >= 2, f"the pcb pool admitted {len(pairs)} pair(s)"
        _drain_all(pairs, _load(pairs))
    finally:
        _close(pairs, reset=False)


def _open_all() -> "list[tuple[lwip.socket, lwip.socket]]":
    # Every pair the pool admits; each pair is two pcbs here, both ends being in this process.
    pairs: list[tuple[lwip.socket, lwip.socket]] = []
    while len(pairs) < 2 * _LWIP["MEMP_NUM_TCP_PCB"]:
        pair = _open_pair()
        if pair is None:
            break
        pairs.append(pair)
    return pairs


def _open_pair() -> "tuple[lwip.socket, lwip.socket] | None":
    # A connected (client, server) pair, or None when the pcb pool cannot hold one more: socket()
    # raises ENOMEM, or the SYN finds no pcb and accept() delivers nothing within the bound.
    try:
        client = lwip.socket()
    except OSError as e:
        if e.errno == errno.ENOMEM:
            return None
        raise
    client.setblocking(False)
    try:
        client.connect((_HOST, _PORT))
    except OSError as e:
        if e.errno != errno.EINPROGRESS:
            client.close()
            raise
    deadline = time.ticks_add(time.ticks_ms(), _CONNECT_BOUND_MS)
    while True:
        try:
            server, _ = _LISTENER.accept()  # non-blocking: pumps once, then EAGAIN
        except OSError as e:
            if e.errno != errno.EAGAIN:
                client.close()
                raise
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                client.close()
                return None
            continue
        server.setblocking(False)
        return client, server


def _pump(ms: int = 1) -> None:
    # Each sleep_ms(1) runs the variant's event hook: netif_poll_all() and sys_check_timeouts().
    for _ in range(ms):
        time.sleep_ms(1)


def _recovered(reference: int) -> int:
    # Pumps until a fresh connection's capacity is within one MSS of reference; returns that capacity.
    deadline = time.ticks_add(time.ticks_ms(), _RECOVERY_S * 1000)
    while True:
        capacity = _capacity()
        if abs(capacity - reference) <= _MSS:
            return capacity
        assert time.ticks_diff(deadline, time.ticks_ms()) > 0, f"capacity {capacity} B is not back within one MSS of {reference} B after {_RECOVERY_S} s"
        _pump(_SETTLE_MS)


def _timed_write(sock: "lwip.socket", piece: "bytes | memoryview") -> "int | None":
    # write()'s result, None on EAGAIN, or _REFUSED for ENOMEM; every call timed against the bound.
    start = time.ticks_ms()
    failure = None
    try:
        written: int | None = sock.write(piece)
    except OSError as e:
        failure = e
        written = _REFUSED
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    assert elapsed <= _WRITE_BOUND_MS, f"one write() took {elapsed} ms, bound {_WRITE_BOUND_MS} ms"
    assert failure is None or failure.errno == errno.ENOMEM, f"write() raised {failure!r} after {elapsed} ms"
    return written


def _writable(sock: "lwip.socket") -> bool:
    # One readiness check with timeout 0: it never waits, on a real lwIP socket.
    poller = select.poll()
    poller.register(sock, select.POLLOUT)
    return any(events & select.POLLOUT for _, events in poller.ipoll(0))


def _write_to_edge(sock: "lwip.socket", piece: bytes, *, pump: bool) -> "tuple[int, int | None]":
    # (bytes written, how the run ended: None for EAGAIN, _REFUSED for ENOMEM), every write bounded.
    total = 0
    for _ in range(_MAX_WRITES):
        written = _timed_write(sock, piece)
        if written is None or written == _REFUSED:
            return total, written
        assert written == len(piece), f"write() took {written} of {len(piece)} B after {total} B"
        total += written
        if pump:
            _pump()
    raise AssertionError(f"no edge after {_MAX_WRITES} writes of {len(piece)} B ({total} B written)")


def _write_until_eagain(sock: "lwip.socket", piece: bytes, *, pump: bool) -> int:
    total, ended = _write_to_edge(sock, piece, pump=pump)
    assert ended is None, f"the edge after {total} B was ENOMEM from tcp_output (no arena for the loopback copy), not EAGAIN"
    return total


def test_a_write_to_a_peer_that_stopped_reading_returns_within_the_bound() -> None:
    # Every pair the pool admits; all but one hold the arena full with peers that never read, then the
    # last one's writes stay bounded too (the unpatched build holds each of them for 10 s).
    pairs = _open_all()
    try:
        print(f"lwIP host pool: {len(pairs)} connection pairs admitted (MEMP_NUM_TCP_PCB {_LWIP['MEMP_NUM_TCP_PCB']}, two pcbs per pair)")
        assert len(pairs) >= 2, f"the pcb pool admitted {len(pairs)} pair(s), the test needs two"
        _load(pairs[:-1])
        client, server = pairs[-1]
        assert _timed_write(client, _MSS_PIECE) is None, "the last connection's first write was not EAGAIN"
        _assert_patched_edge(client, "arena")
        for _ in range(_ARENA_FULL_WRITES):
            assert _timed_write(client, _MSS_PIECE) is None, "a write into the full arena was not EAGAIN"
            _pump()
            assert _drain(server) == 0
    finally:
        _close(pairs, reset=True)


def test_the_queue_limit_edge() -> None:
    # TCP_NODELAY sends each 16 B piece as its own segment; with no pump no ACK frees one, so the
    # connection's own segment count reaches TCP_SND_QUEUELEN while its send buffer still has room.
    pair = _open_pair()
    assert pair is not None
    client, _ = pair
    try:
        client.setsockopt(lwip.IPPROTO_TCP, lwip.TCP_NODELAY, 1)
        written = _write_until_eagain(client, _QUEUE_PIECE, pump=False)
        _assert_patched_edge(client, "queue-limit")
        assert written == _QUEUE_LIMIT * len(_QUEUE_PIECE), f"EAGAIN after {written} B, the queue limit is {_QUEUE_LIMIT} segments of {len(_QUEUE_PIECE)} B"
    finally:
        _close([pair], reset=True)


def test_the_segment_pool_edge() -> None:
    # One-byte segments, round robin over three connections so that none reaches its own queue
    # limit: the shared MEMP_NUM_TCP_SEG pool is what runs out, an arena far from full.
    pairs = [_open_pair() for _ in range(3)]
    opened = [pair for pair in pairs if pair is not None]
    try:
        assert len(opened) == 3, f"only {len(opened)} of 3 connections opened"
        for client, _ in opened:
            client.setsockopt(lwip.IPPROTO_TCP, lwip.TCP_NODELAY, 1)
        segments = 0
        for turn in range(_SEGMENT_POOL + 3):
            client = opened[turn % 3][0]
            written = _timed_write(client, _SEGMENT_PIECE)
            assert written != _REFUSED, f"ENOMEM after {segments} segments: the arena ran out before the segment pool"
            if written is None:
                _assert_patched_edge(client, "segment-pool")
                assert segments == _SEGMENT_POOL, f"EAGAIN after {segments} segments, the pool holds {_SEGMENT_POOL}"
                return
            segments += 1
        raise AssertionError(f"no EAGAIN after {segments} one-byte segments, the pool holds {_SEGMENT_POOL}")
    finally:
        _close(opened, reset=True)


def test_a_reading_peer_receives_every_byte_intact() -> None:
    # The writer sends a known pattern in phases: while the reader holds off, its window closes and the
    # arena fills to the edge; then the reader drains everything, and gets every byte write() took, in order.
    pair = _open_pair()
    assert pair is not None
    writer, reader = pair
    try:
        sent = received = eagains = 0
        deadline = time.ticks_add(time.ticks_ms(), _RECOVERY_S * 1000)
        while received < _PATTERN_BYTES:
            while sent < _PATTERN_BYTES:
                offset = sent % _PATTERN_PERIOD
                piece = memoryview(_PATTERN)[offset : offset + min(_PATTERN_PIECE, _PATTERN_BYTES - sent)]
                written = _timed_write(writer, piece)
                assert written != _REFUSED, f"a writing phase ended in ENOMEM after {sent} B, not at the zero-window EAGAIN"
                if written is None:
                    if eagains == 0:
                        _assert_patched_edge(writer, "arena")
                    eagains += 1
                    break
                assert written == len(piece), f"write() took {written} of {len(piece)} B"
                sent += written
                _pump()
            while received < sent:
                assert time.ticks_diff(deadline, time.ticks_ms()) > 0, f"{received} of {sent} B arrived within {_RECOVERY_S} s"
                _pump()
                while True:
                    try:
                        chunk = reader.recv(_RECV_CHUNK)
                    except OSError as e:
                        assert e.errno == errno.EAGAIN, f"recv() raised {e!r}"
                        break
                    offset = received % _PATTERN_PERIOD
                    assert chunk == _PATTERN[offset : offset + len(chunk)], f"the bytes at offset {received} differ from what was written"
                    received += len(chunk)
        print(f"intact-data run: {eagains} writing phases, each ended in EAGAIN, over {_PATTERN_BYTES} B")
        assert received == sent == _PATTERN_BYTES
        assert eagains > 0, "no writing phase ended at the patched EAGAIN edge"
    finally:
        _close([pair], reset=True)


def test_capacity_returns_after_the_peers_close() -> None:
    baseline = _capacity()
    _load_drain_close()
    _recovered(baseline)


def test_repeated_rounds_stay_stable() -> None:
    # The load, drain and close cycle again and again: no drift and no leak in the arena or the pools.
    reference = _capacity()
    for _ in range(_ROUNDS):
        _load_drain_close()
        _recovered(reference)


def test_the_eagain_spin_round_is_bounded() -> None:
    # At the queue-limit edge, what asyncio's drain() repeats while a connection spins: write() of the
    # remaining memoryview slice returns None, a timeout-0 poll reports POLLOUT; no pump in between.
    pair = _open_pair()
    assert pair is not None
    client, _ = pair
    try:
        client.setsockopt(lwip.IPPROTO_TCP, lwip.TCP_NODELAY, 1)
        _write_until_eagain(client, _QUEUE_PIECE, pump=False)
        poller = select.poll()
        poller.register(client, select.POLLOUT)
        for _ in poller.ipoll(0):
            pass  # ipoll's result tuple is allocated once, on first use; asyncio's poller already has it
        remaining = memoryview(_MSS_PIECE)
        slowest_us = largest_b = collections = 0
        for _ in range(_SPIN_ROUNDS):
            allocated = gc.mem_alloc()
            start = time.ticks_us()
            written = client.write(remaining[0:])
            writable = False
            for _, events in poller.ipoll(0):
                writable = bool(events & select.POLLOUT)
            elapsed_us = time.ticks_diff(time.ticks_us(), start)
            grown = gc.mem_alloc() - allocated
            assert written is None and writable, f"the spin ended: write() returned {written}, POLLOUT {writable}"
            if grown < 0:
                # A collection ran inside this round (the shipped threshold's stage): its pause is the
                # collector's, not the spin's, so the round is counted and left out of both maxima.
                collections += 1
                continue
            slowest_us = max(slowest_us, elapsed_us)
            largest_b = max(largest_b, grown)
        print(f"EAGAIN spin: slowest round {slowest_us} us, largest allocation {largest_b} B over {_SPIN_ROUNDS - collections} rounds ({collections} with a collection)")
        assert collections < _SPIN_ROUNDS, "every round ran a collection: nothing measured"
        assert slowest_us <= _SPIN_ROUND_MAX_US, f"a spin round took {slowest_us} us, bound {_SPIN_ROUND_MAX_US} us"
        assert largest_b <= _SPIN_ROUND_ALLOC_MAX_B, f"a spin round allocated {largest_b} B, bound {_SPIN_ROUND_ALLOC_MAX_B} B"
    finally:
        _close([pair], reset=True)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
