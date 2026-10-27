"""Isolated-driver device script, read-only on memory: closing a listening socket, and one whose listen() ran out of
heap, leaves lwIP's two TCP pcb pools as they were (SPECIFICATION.md B.14.4). The pools' addresses come from the
image's firmware.elf through the host; the script reads the pools before and after, then runs one round trip."""

import socket
import sys

import machine
import micropython

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, errors, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_HOST = "127.0.0.1"  # the listener's address changes nothing in its pcb's life, and loopback exposes no port
_PORT = 50100  # any free port: production is stopped, and the twin's loopback needs an unprivileged one
_PAYLOAD = b"listener close round trip"
_EXCHANGE_S = 2.0  # each blocking step of the twin's loopback exchange
_WORD = 0xFFFFFFFF  # machine.mem32 returns a signed small int (extmod/machine_mem.c:85, v1.29.0)
_ALIGN = 3  # memp_init_pool() starts the slots at LWIP_MEM_ALIGN(base), MEM_ALIGNMENT 4 (lwipopts_common.h:42)


def _changed(name: str, before: "list[int]", after: "list[int]", slots: "list[int]", size: int) -> "list[str]":
    # Every word of the given slots that differs between the two pictures, by slot and byte offset.
    found = []
    for slot in slots:
        for i in range(slot * size // 4, (slot + 1) * size // 4):
            if before[i] != after[i]:
                found.append(f"{name} slot {slot} +{i * 4 - slot * size} 0x{before[i]:08x}->0x{after[i]:08x}")
    return found


def _descriptor(pool: "dict[str, int]") -> "tuple[int, int, int, int]":
    # struct memp_desc without desc and stats: u16 size, u16 num, u8 *base, struct memp **tab (memp_priv.h:108-130),
    # its first word holding size and num little-endian, as the RP2040 stores it.
    desc = pool["desc"]
    first = machine.mem32[desc] & _WORD
    return (first & 0xFFFF, first >> 16, machine.mem32[desc + 4] & _WORD, machine.mem32[desc + 8] & _WORD)


def _free(words: "list[int]", head: int, start: int, size: int, num: int) -> "list[int] | None":
    # The free list walked from the picture's own words (memp.c:195-196, :259-268, :385-386); a node off a slot
    # boundary, outside the pool or past num entries marks the list broken, None.
    slots: list[int] = []
    node = head
    while node:
        offset = node - start
        if offset < 0 or offset % size or offset // size >= num or len(slots) == num:
            return None
        slots.append(offset // size)
        node = words[offset // 4]
    return slots


def _listen_refused(family: int, address: "tuple[str, int] | tuple[str, int, int, int]", backlog: int) -> bool:
    # listen() takes the LISTEN pcb, then allocates the accept queue: with the heap locked that allocation refuses,
    # leaving the socket unlistened over a LISTEN pcb (extmod/modlwip.c:1077-1099, v1.29.0); then it is closed.
    sock = _server_socket(family, address)
    refused = False
    micropython.heap_lock()
    try:
        sock.listen(backlog)
    except MemoryError:
        refused = True
    finally:
        micropython.heap_unlock()
    sock.close()
    return refused


def _matched(layout: "dict[str, tuple[int, int, int, int]]", pools: "dict[str, dict[str, int]]") -> bool:
    # The image's descriptors name the host's arrays and each pool fits its own: only then is any pool byte read.
    return bool(layout) and all(layout[n][2] == p["base"] and layout[n][3] == p["tab"] and _slots(p["base"]) + layout[n][0] * layout[n][1] <= p["base"] + p["bytes"] for n, p in pools.items())


def _port_held(family: int, address: "tuple[str, int] | tuple[str, int, int, int]", backlog: int) -> "int | None":
    # A bind without SO_REUSEADDR is refused while any pcb still holds the port; a listener there again, then closed.
    sock = socket.socket(family)
    try:
        sock.bind(address)
        sock.listen(backlog)
    except OSError as e:
        return e.errno
    finally:
        sock.close()
    return None


def _round_trip() -> "bool | int | None":
    # One exchange over loopback, True when the echo comes back whole: the twin's host stack carries it, while rp2's
    # lwIP has no loopback netif (LWIP_NETIF_LOOPBACK 0, lwip/opt.h:1792), so its route refusal's errno is the answer.
    address = socket.getaddrinfo(_HOST, _PORT)[0][-1]
    server = socket.socket()
    client = socket.socket()
    try:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(address)
        server.listen(1)
        server.settimeout(_EXCHANGE_S)
        client.settimeout(_EXCHANGE_S)
        client.connect(address)
        client.send(_PAYLOAD)
        conn = server.accept()[0]
        try:
            conn.settimeout(_EXCHANGE_S)
            conn.send(conn.recv(len(_PAYLOAD)))
        finally:
            conn.close()
        return client.recv(len(_PAYLOAD)) == _PAYLOAD
    except OSError as e:
        return e.errno
    finally:
        client.close()
        server.close()


def _server_socket(family: int, address: "tuple[str, int] | tuple[str, int, int, int]") -> socket.socket:
    # The socket asyncio.start_server() builds before its listen() (extmod/asyncio/stream.py:184-187, v1.29.0).
    sock = socket.socket(family)
    sock.setblocking(False)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    return sock


def _slots(base: int) -> int:
    return (base + _ALIGN) & ~_ALIGN


def _snapshot(layout: "dict[str, tuple[int, int, int, int]]") -> "dict[str, tuple[list[int], int]]":
    # Every pool's words and free-list head in one picture, interrupts off so lwIP's own work cannot run mid-read;
    # nothing to read, nothing disabled (the twin's machine has no disable_irq()).
    if not layout:
        return {}
    state = machine.disable_irq()  # type: ignore[attr-defined]
    try:
        return {name: ([machine.mem32[_slots(base) + 4 * i] & _WORD for i in range(size * num // 4)], machine.mem32[tab] & _WORD) for name, (size, num, base, tab) in layout.items()}
    finally:
        machine.enable_irq(state)  # type: ignore[attr-defined]


wdt = arm()
fact("platform", sys.platform)
server_info = socket.getaddrinfo(_HOST, _PORT)[0]
family, address = server_info[0], server_info[-1]
read: "dict[str, tuple[int, int, int, int]]" = {name: _descriptor(pool) for name, pool in BENCH["pools"].items()} if sys.platform == "rp2" else {}
fact("pools", read or None)
layout = read if _matched(read, BENCH["pools"]) else {}
fact("pools_matched", bool(layout))
before = _snapshot(layout)
listener = _server_socket(family, address)
listener.listen(BENCH["backlog"])
listener.close()
fact("listener_closed", True)
wdt.feed()
fact("listen_refused", _listen_refused(family, address, BENCH["backlog"]))
after = _snapshot(layout)
wdt.feed()
fact("port_held_errno", _port_held(family, address, BENCH["backlog"]))
fact("round_trip", _round_trip())
end = _snapshot(layout)
free: "dict[str, list[list[int] | None]]" = {}
used: "dict[str, int | None]" = {}
changed: "list[str]" = []
for name, (size, num, base, _tab) in layout.items():
    free[name] = [_free(snap[name][0], snap[name][1], _slots(base), size, num) for snap in (before, after, end)]
    first, second = free[name][0], free[name][1]
    if first is not None and second is not None:
        # The head is the one slot every socket() (connection pool) or listen() (listen pool) here takes and returns.
        used[name] = first[0] if first else None
        changed += _changed(name, before[name][0], after[name][0], [s for s in first if s in second and s != used[name]], size)
fact("free", free)
fact("used", used)
errors("changed", len(changed), changed)
done()
