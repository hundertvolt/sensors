"""MQTTLinkDriver, dev's MQTT exerciser, over a real MQTTClient and the scripted loopback broker routing its probe back:
round trips and failures counted, nothing sent or counted while disconnected, the device's commands counted, callbacks
that never raise or allocate, and the module shape the generated device module wires (SPECIFICATION.md A.12)."""

import asyncio
import gc
import time

from _async_harness import run
from _mqtt_fake_broker import FakeBroker, publish_packet
from _port_bands import PortAllocator
from _src_const import src_int
from _tmp_scratch import TmpScratch

import asy_mqtt_link_driver
from asy_base_classes import COUNTER_CAP
from asy_mqtt_client import MQTTClient, MqttConfig
from asy_mqtt_link_driver import MQTTLinkDriver

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

_PORTS = PortAllocator("test_asy_mqtt_link_driver")
_scratch = TmpScratch("mqtt_link")
# Short client timings, as tests/test_asy_mqtt_client.py's, with no QoS 1 retry within a test: a probe goes out once.
_CFG = MqttConfig("t1", 3000, 500, 100, 400, 600, 60000, 300, 20, 50, 200, 100)
_WAIT_MS = 8000  # every wait polls; the bound only matters on a failure
_EXERCISE_PERIOD_MS: int = src_int("src/asy_mqtt_link_driver.py", "_EXERCISE_PERIOD_MS")
_C_CONSUMER_ERR: int = src_int("src/asy_mqtt_client.py", "_C_CONSUMER_ERR")
_ECHO = b"sensors/t1/link/echo"


class _Rounds:
    # Shadows asy_mqtt_link_driver's module-global `asyncio` for one test: each period's sleep waits for next_round(),
    # so a round runs exactly when the test asks; every period asked for is recorded.
    def __init__(self) -> None:
        self.periods: list[int] = []
        self._go = asyncio.Event()

    async def asleep(self) -> None:
        # Returns once the loop has run its first round and sleeps.
        while not self.periods:
            await asyncio.sleep_ms(1)

    def create_task(self, coro: "Coroutine[object, object, None]") -> "asyncio.Task[None]":
        return asyncio.create_task(coro)

    async def next_round(self) -> None:
        # Ends the current sleep; returns once the loop sleeps again, its round done.
        asked = len(self.periods)
        self._go.set()
        while len(self.periods) == asked:
            await asyncio.sleep_ms(1)

    async def sleep_ms(self, ms: int) -> None:
        self.periods.append(ms)
        await self._go.wait()
        self._go.clear()


def _with_rounds(scenario: "Callable[[_Rounds], Coroutine[object, object, None]]") -> None:
    rounds = _Rounds()
    asy_mqtt_link_driver.asyncio = rounds  # type: ignore[assignment]
    try:
        run(scenario(rounds))
    finally:
        asy_mqtt_link_driver.asyncio = asyncio


def _client(link: "Callable[[], bool] | None" = None) -> MQTTClient:
    return MQTTClient(asyncio.Lock(), link or (lambda: True), lambda: None, _CFG, cfg_path=_scratch.dir())


async def until(predicate: "Callable[[], bool]", timeout_ms: int = _WAIT_MS) -> bool:
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        if predicate():
            return True
        await asyncio.sleep_ms(10)
    return predicate()


async def _started(rounds: _Rounds, *, link: "Callable[[], bool] | None" = None, enable: bool = True) -> "tuple[FakeBroker, MQTTClient, MQTTLinkDriver, list[asyncio.Task[None]]]":
    # A routing broker, the client and its exerciser built as the generated module builds them, the tasks started; with
    # `enable` the client is configured for the broker and, the link up, connected with its subscription in place.
    broker = FakeBroker(_PORTS.next())
    broker.route = True
    await broker.start()
    client = _client(link)
    link_driver = MQTTLinkDriver(client=client)
    await client.setup()
    tasks = [client.start_asy_connection(), link_driver.start_asy_exercise()]
    await rounds.asleep()
    if enable:
        body: dict[str, int | str | bool] = {"MQTTEnable": True, "MQTTHost": "127.0.0.1", "MQTTPort": broker.port, "MQTTClientId": "t1"}
        results = await client._set_dict_cfg(body, client.get_cfg_schema())
        assert all(v in ("Valid", "Unchanged") for v in results.values()), results
        client.reconnect()
    return broker, client, link_driver, tasks


async def _online(broker: FakeBroker, client: MQTTClient) -> bool:
    # Connected, and the broker has read the online message, which follows the SUBSCRIBE on the wire.
    return await until(lambda: client.is_connected() and len(broker.published(b"sensors/t1/status")) == 1)


async def _transfers_reach(link: MQTTLinkDriver, n: int) -> bool:
    return await until(lambda: link._transfers == n)


async def _stop(broker: FakeBroker, client: MQTTClient, tasks: "list[asyncio.Task[None]]") -> None:
    for task in tasks:
        task.cancel()
    for task in tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass
    await client._close()
    await broker.stop()


def test_the_exerciser_registers_below_the_base_and_shares_the_clients_logger() -> None:
    # The shape the generated module wires: the client is its one wiring, it keeps no logger, setting, store or route of
    # its own, and its one task joins the supervised starters.
    client = _client()
    link = MQTTLinkDriver(client=client)
    assert link.pr is client.pr
    assert link.name == client.name == "MQTT"
    assert client._rel_topics == [b"/link/echo"]
    assert client._rel_filters == [b"/link/echo", b"/cmd/#"]
    assert link.get_task_starters() == [link.start_asy_exercise]
    assert link.get_timer_starters() == []
    assert link.get_error_sources() == []
    assert link.get_loggers() == []
    assert not hasattr(link, "cfgmgr")
    assert not hasattr(link, "setup")
    assert not hasattr(link, "add_routes")
    assert run(link.get_link_status()) == {"Transfers": 0, "Failures": 0, "Commands": 0}


def test_a_probe_routed_back_through_the_broker_is_one_transfer() -> None:
    async def scenario(rounds: _Rounds) -> None:
        broker, client, link, tasks = await _started(rounds)
        try:
            assert await _online(broker, client)
            await rounds.next_round()
            assert await until(lambda: link._transfers == 1)
            probes = broker.published(_ECHO)
            assert probes == [(0x32, b"\x00\x00\x00\x01")], probes  # QoS 1, not retained, its sequence number
            await rounds.next_round()
            assert await until(lambda: link._transfers == 2)
            assert broker.published(_ECHO)[1] == (0x32, b"\x00\x00\x00\x02")
            assert await link.get_link_status() == {"Transfers": 2, "Failures": 0, "Commands": 0}
            assert client.get_link_status()["MQTTTxDropped"] == 0
            assert rounds.periods == [_EXERCISE_PERIOD_MS] * len(rounds.periods), rounds.periods
        finally:
            await _stop(broker, client, tasks)

    _with_rounds(scenario)


def test_a_probe_that_never_comes_back_is_one_failure_at_the_next_round() -> None:
    async def scenario(rounds: _Rounds) -> None:
        broker, client, link, tasks = await _started(rounds)
        try:
            assert await _online(broker, client)
            broker.route = False  # the broker takes the probe, acknowledges it and delivers it nowhere
            await rounds.next_round()
            assert await until(lambda: len(broker.published(_ECHO)) == 1)
            await asyncio.sleep_ms(100)
            assert (link._transfers, link._failures) == (0, 0)  # not failed before its round is over
            broker.route = True
            await rounds.next_round()
            assert link._failures == 1  # counted as the next round starts
            assert await until(lambda: link._transfers == 1)
            assert await link.get_link_status() == {"Transfers": 1, "Failures": 1, "Commands": 0}
        finally:
            await _stop(broker, client, tasks)

    _with_rounds(scenario)


def test_no_probe_goes_out_and_nothing_is_counted_while_the_client_is_off() -> None:
    async def scenario(rounds: _Rounds) -> None:
        broker, client, link, tasks = await _started(rounds, enable=False)  # the client's shipped default: off
        try:
            for _ in range(3):
                await rounds.next_round()
            await asyncio.sleep_ms(100)
            assert broker.connections == 0
            assert await link.get_link_status() == {"Transfers": 0, "Failures": 0, "Commands": 0}
            assert client.get_link_status()["MQTTTxDropped"] == 0  # not even a refused publish
        finally:
            await _stop(broker, client, tasks)

    _with_rounds(scenario)


def test_no_probe_goes_out_and_nothing_is_counted_while_the_hotspot_runs() -> None:
    async def scenario(rounds: _Rounds) -> None:
        broker, client, link, tasks = await _started(rounds, link=lambda: False)  # enabled, but no network: the hotspot
        try:
            for _ in range(3):
                await rounds.next_round()
            await asyncio.sleep_ms(100)
            assert broker.connections == 0
            assert client.get_link_status()["MQTTState"] == "waiting"
            assert await link.get_link_status() == {"Transfers": 0, "Failures": 0, "Commands": 0}
            assert client.get_link_status()["MQTTTxDropped"] == 0
        finally:
            await _stop(broker, client, tasks)

    _with_rounds(scenario)


def test_a_probe_lost_with_the_link_fails_once_and_none_goes_out_until_it_is_back() -> None:
    up = [True]

    async def scenario(rounds: _Rounds) -> None:
        broker, client, link, tasks = await _started(rounds, link=lambda: up[0])
        try:
            assert await _online(broker, client)
            broker.route = False
            await rounds.next_round()
            assert await until(lambda: len(broker.published(_ECHO)) == 1)
            up[0] = False
            assert await until(lambda: not client.is_connected())
            for _ in range(3):
                await rounds.next_round()
            assert await link.get_link_status() == {"Transfers": 0, "Failures": 1, "Commands": 0}
            assert len(broker.published(_ECHO)) == 1  # nothing new while down
        finally:
            await _stop(broker, client, tasks)

    _with_rounds(scenario)


def test_a_retained_stale_or_reshaped_echo_counts_nothing() -> None:
    async def scenario(rounds: _Rounds) -> None:
        broker, client, link, tasks = await _started(rounds)
        try:
            assert await _online(broker, client)
            broker.route = False
            await rounds.next_round()
            assert await until(lambda: len(broker.published(_ECHO)) == 1)
            probe = broker.published(_ECHO)[0][1]
            for payload, retain in ((probe, True), (b"\x00\x00\x00\x02", False), (probe + b"\x00", False), (probe[:3], False), (b"", False)):
                await broker.send(publish_packet(_ECHO, payload, retain=retain))
            assert await until(lambda: client.get_link_status()["MQTTRxMsgs"] == 5)
            assert link._transfers == 0
            await broker.send(publish_packet(_ECHO, probe, qos=1, pid=9))
            await broker.send(publish_packet(_ECHO, probe))  # a duplicate: the probe already came back
            assert await until(lambda: client.get_link_status()["MQTTRxMsgs"] == 7)
            assert await link.get_link_status() == {"Transfers": 1, "Failures": 0, "Commands": 0}
        finally:
            await _stop(broker, client, tasks)

    _with_rounds(scenario)


def test_messages_below_the_cmd_tree_are_counted_and_the_client_shows_their_topic() -> None:
    async def scenario(rounds: _Rounds) -> None:
        broker, client, link, tasks = await _started(rounds)
        try:
            assert await _online(broker, client)
            await broker.send(publish_packet(b"sensors/t1/cmd/hello", b"yo"))
            await broker.send(publish_packet(b"sensors/t1/cmd", b"", retain=True))  # "cmd/#" takes its parent level too
            await broker.send(publish_packet(b"sensors/t1/cmdx", b"no"))  # another level: not a command
            await broker.send(publish_packet(b"sensors/t2/cmd/a/b", b"no", qos=1, pid=3))  # another device's
            assert await until(lambda: client.get_link_status()["MQTTRxMsgs"] == 4)
            assert await link.get_link_status() == {"Transfers": 0, "Failures": 0, "Commands": 2}
            assert client.get_link_status()["MQTTLastRxTopic"] == "sensors/t2/cmd/a/b"
        finally:
            await _stop(broker, client, tasks)

    _with_rounds(scenario)


def test_the_probe_shares_the_ring_with_another_publisher_and_each_message_arrives() -> None:
    # Two users of one client's outbound ring: the exerciser's probes and a module publishing QoS 1 messages between them.
    async def scenario(rounds: _Rounds) -> None:
        broker, client, link, tasks = await _started(rounds)
        try:
            assert await _online(broker, client)
            for i in range(3):
                assert client.publish("sensors/t1/other", bytes([i]), qos=1)
                await rounds.next_round()
                assert client.publish("sensors/t1/other", bytes([i + 10]), qos=1)
                assert await _transfers_reach(link, i + 1)  # back before the next round
            assert await until(lambda: len(broker.published(b"sensors/t1/other")) == 6)
            assert link._failures == 0
            assert client.get_link_status()["MQTTTxDropped"] == 0
        finally:
            await _stop(broker, client, tasks)

    _with_rounds(scenario)


def test_the_callbacks_never_raise_and_allocate_nothing_on_any_message() -> None:
    client = _client()
    link = MQTTLinkDriver(client=client)
    link._probe[3] = 7
    topic = memoryview(_ECHO)
    payloads = [memoryview(b""), memoryview(b"\x00\x00\x00\x07"), memoryview(b"\x00\x00\x00\x07\x00"), memoryview(bytes(range(256)) * 4)]

    def calls() -> None:
        for flags in range(16):
            for payload in payloads:
                link._pending = True
                link._on_echo(topic, payload, flags)
                link._on_command(topic, payload, flags)

    calls()  # warm: every path taken once
    link._transfers = link._commands = 0
    gc.collect()  # the baseline of the measurement (SPECIFICATION.md I.4)
    before = gc.mem_alloc()
    calls()
    assert gc.mem_alloc() - before == 0
    assert link._transfers == 8  # the matching payload, at each flag value without RETAIN
    assert link._commands == 64


def test_every_counter_saturates_at_the_cap() -> None:
    async def scenario(rounds: _Rounds) -> None:
        client = _client()
        link = MQTTLinkDriver(client=client)
        task = link.start_asy_exercise()
        try:
            await rounds.asleep()
            link._transfers = link._failures = link._commands = COUNTER_CAP
            link._pending = True
            await rounds.next_round()  # the probe still out fails; the client is off, so nothing else
            link._pending = True
            link._on_echo(memoryview(_ECHO), memoryview(link._probe), 0)
            link._on_command(memoryview(b"sensors/t1/cmd/x"), memoryview(b""), 0)
            assert await link.get_link_status() == {"Transfers": COUNTER_CAP, "Failures": COUNTER_CAP, "Commands": COUNTER_CAP}
            assert not link._pending
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    _with_rounds(scenario)


def test_a_consumer_fault_never_comes_from_the_exerciser_on_any_traffic() -> None:
    # End to end: every message the broker can route to its two filters leaves the client's consumer-fault count at 0.
    async def scenario(rounds: _Rounds) -> None:
        broker, client, link, tasks = await _started(rounds)
        try:
            assert await _online(broker, client)
            for payload in (b"", b"\xff", b"x" * 900, b"\x00\x00\x00\x01"):
                await broker.send(publish_packet(_ECHO, payload, qos=1, pid=5, retain=True))
                await broker.send(publish_packet(b"sensors/t1/cmd/z", payload))
            await rounds.next_round()
            assert await until(lambda: link._transfers == 1 and client.get_link_status()["MQTTRxMsgs"] == 9)
            assert client._counts[_C_CONSUMER_ERR] == 0
            assert (await link.get_link_status())["Commands"] == 4
        finally:
            await _stop(broker, client, tasks)

    _with_rounds(scenario)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
