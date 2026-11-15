"""The MQTT client's writes under real back-pressure on build-lwip, the Unix port over loopback lwIP (SPECIFICATION.md
A.12): peers that never read hold the arena full, so its sends meet EAGAIN; the unsent rest stays one packet in the
transmit buffer, allocating nothing, and once the peers close every message reaches the broker whole and in order."""

import asyncio
import errno
import gc
import time

import lwip
from _async_harness import run
from _mqtt_fake_broker import FakeBroker
from _tmp_scratch import TmpScratch

from asy_mqtt_client import MQTTClient, MqttConfig

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

# Once per process: nothing else on the Unix port initialises lwIP.
lwip.reset()

_HOST = "127.0.0.1"
_BROKER_PORT = 50300
_LOADER_PORT = 50301
_scratch = TmpScratch("mqtt_lwip")
# Response, connect, backoff min/max, stable-after, QoS 1 retry, drain, tick, link poll, idle recheck, DNS: no link
# check, ping or retry falls inside the test, and the drain timeout outlasts the pressure window.
_CFG = MqttConfig("t1", 10000, 2000, 100, 400, 600, 60000, 5000, 20, 60000, 200, 100)
_MSS = 800
_MESSAGES = 8  # every outbound slot, so the old stream buffer would have grown to all of them
_PAYLOAD_BYTES = 200
_TOPIC = b"sensors/t1/x"
_PACKET_BYTES = 1 + 2 + 2 + len(_TOPIC) + _PAYLOAD_BYTES  # one PUBLISH: its type, two length bytes, the topic's prefix
_WINDOW_MS = 1000
# What the pressure window may allocate beyond an idle window of the same length: the keeper's retries none at all.
_PRESSURE_ALLOC_SLACK_B = 256
_RESUME_BOUND_MS = 1000  # every message at the broker once the peers close; measured: two ticks of retries
_POLL_MS = 5  # above modselect's 1 ms ioctl period: a shorter wait returns before lwIP's event hook runs (F.7 row 26)
_LOADERS = 2  # enough stalled peers to fill the arena (each holds TCP_WND + TCP_SND_BUF)
_MAX_WRITES = 400


async def _until(predicate: "Callable[[], bool]", timeout_ms: int) -> bool:
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        if predicate():
            return True
        await asyncio.sleep_ms(_POLL_MS)
    return predicate()


def _pump(ms: int) -> None:
    # Each sleep_ms(1) runs the variant's event hook: netif_poll_all() and sys_check_timeouts().
    for _ in range(ms):
        time.sleep_ms(1)


def _open_pair(listener: "lwip.socket") -> "tuple[lwip.socket, lwip.socket]":
    client = lwip.socket()
    client.setblocking(False)
    try:
        client.connect((_HOST, _LOADER_PORT))
    except OSError as e:
        if e.errno != errno.EINPROGRESS:
            raise
    for _ in range(500):
        try:
            server, _ = listener.accept()
        except OSError as e:
            if e.errno != errno.EAGAIN:
                raise
            _pump(1)
            continue
        server.setblocking(False)
        return client, server
    raise AssertionError("a loader connection was not accepted within 500 ms")


def _load(pairs: "list[tuple[lwip.socket, lwip.socket]]") -> None:
    # Whole-MSS writes to peers that never read, each connection to its edge: EAGAIN, or ENOMEM where this loopback
    # netif's copy for the peer met the full arena, the piece queued (F.7 row 23).
    piece = b"\x96" * _MSS
    for client, _ in pairs:
        for _ in range(_MAX_WRITES):
            try:
                if client.write(piece) is None:
                    break
            except OSError as e:
                assert e.errno == errno.ENOMEM, e
                break
            _pump(1)
        else:
            raise AssertionError(f"no edge after {_MAX_WRITES} writes")


async def _window(client: MQTTClient) -> "tuple[int, int, int]":
    # _WINDOW_MS of zero-length scheduler rounds after a baseline collection, so lwIP stays as the load left it (no
    # event hook runs, F.7 row 26): (bytes allocated, the largest remainder seen, the largest stream buffer seen).
    gc.collect()  # the measurement's baseline (SPECIFICATION.md I.4)
    before = gc.mem_alloc()
    start = time.ticks_ms()
    largest_left = largest_out_buf = 0
    while time.ticks_diff(time.ticks_ms(), start) < _WINDOW_MS:
        await asyncio.sleep_ms(0)
        stream = client._stream
        out_buf = len(stream.out_buf) if stream is not None else 0
        largest_out_buf = max(largest_out_buf, out_buf)
        largest_left = max(largest_left, client._tx_left)
    return gc.mem_alloc() - before, largest_left, largest_out_buf


def test_back_pressure_holds_one_packet_allocates_nothing_and_every_message_follows_whole_and_in_order() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_BROKER_PORT)
        await broker.start()
        client = MQTTClient(asyncio.Lock(), lambda: True, lambda: None, _CFG, cfg_path=_scratch.dir())
        await client.setup()
        task = client.start_asy_connection()
        listener = lwip.socket()
        listener.setsockopt(lwip.SOL_SOCKET, lwip.SO_REUSEADDR, 1)
        listener.bind((_HOST, _LOADER_PORT))
        listener.listen(_LOADERS)
        listener.setblocking(False)
        pairs: list[tuple[lwip.socket, lwip.socket]] = []
        try:
            body: dict[str, int | str | bool] = {"MQTTEnable": True, "MQTTHost": _HOST, "MQTTPort": _BROKER_PORT, "MQTTClientId": "t1", "MQTTWillQoS": 0}
            await client._set_dict_cfg(body, client.get_cfg_schema())
            client.reconnect()
            assert await _until(lambda: any(first == 0xC0 for first, _ in broker.packets), 5000), "no PINGREQ after the online message"
            await asyncio.sleep_ms(100)  # its PINGRESP: nothing unconfirmed, so the cap holds back none of the messages
            idle, _, _ = await _window(client)
            pairs = [_open_pair(listener) for _ in range(_LOADERS)]
            _load(pairs)
            payloads = [bytes([0x41 + n]) * _PAYLOAD_BYTES for n in range(_MESSAGES)]
            for payload in payloads:
                assert client.publish(_TOPIC, payload)
            pressure, largest_left, largest_out_buf = await _window(client)
            held = _MESSAGES - len(broker.published(_TOPIC))  # the arena's last room may take a message or two
            assert held >= _MESSAGES // 2, f"the arena was not full: only {held} message(s) held"
            assert client.is_connected()
            assert largest_out_buf == 0, f"the stream buffered {largest_out_buf} B"
            assert 0 < largest_left <= _PACKET_BYTES, f"the remainder reached {largest_left} B"
            assert pressure <= idle + _PRESSURE_ALLOC_SLACK_B, f"back-pressure allocated {pressure} B over {_WINDOW_MS} ms, idle {idle} B"
            for client_sock, server_sock in pairs:
                server_sock.close()  # the server end first: lwIP resets, freeing the unread data at once
                client_sock.close()
            pairs = []
            released = time.ticks_ms()
            assert await _until(lambda: len(broker.published(_TOPIC)) == _MESSAGES, _RESUME_BOUND_MS), "the held messages did not follow the release"
            resumed_ms = time.ticks_diff(time.ticks_ms(), released)
            assert [payload for _first, payload in broker.published(_TOPIC)] == payloads  # whole, in order
            assert client.is_connected()
            print(f"MQTT back-pressure: {held} messages held, the remainder at most {largest_left} B, {pressure} B allocated over {_WINDOW_MS} ms (idle {idle} B), all {_MESSAGES} messages {resumed_ms} ms after the release")
        finally:
            for client_sock, server_sock in pairs:
                server_sock.close()
                client_sock.close()
            listener.close()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await client._close()
            await broker.stop()

    run(scenario())


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
