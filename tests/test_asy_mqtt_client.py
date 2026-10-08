import asyncio
import json
import time

from _error_codes import code
from _mqtt_fake_broker import FakeBroker, encode_length, publish_packet, read_str
from _tmp_scratch import TmpScratch

import asy_mqtt_client
from asy_mqtt_client import MQTTClient, MqttConfig, MqttConsumer

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import TypeVar

    from asy_mqtt_client import _Source
    from asy_print_log import ErrorLog

    T = TypeVar("T")

# This file's own port band (SPECIFICATION.md E.1: below 32768, outside every neighbour's band); one port per broker.
_PORT_BASE = 28000
_ports = [_PORT_BASE]
_scratch = TmpScratch("mqtt")

# Short timings, so a scenario takes well under a second per phase: client id, keepalive, ping, response, connect,
# backoff min/max, stable-after, QoS 1 retry, drain, tick, link poll, idle recheck, DNS timeout and tries.
_CFG = MqttConfig("t1", 60, 1000, 800, 500, 100, 400, 600, 200, 300, 20, 50, 200, 100, 1)
_WAIT_MS = 8000  # every wait polls; the bound only matters on a failure
_R_STALLED = 7  # asy_mqtt_client.py's const()-folded teardown reason - mirrored, not importable


def run(coro: "Coroutine[object, object, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def count(client: MQTTClient, key: str) -> int:
    value = client.get_link_status()[key]
    assert isinstance(value, int)
    return value


def _port() -> int:
    _ports[0] += 1
    return _ports[0]


def make_client(*, link: "Callable[[], bool] | None" = None, consumers: "tuple[MqttConsumer, ...]" = (), sources: "tuple[_Source, ...]" = (), config: MqttConfig = _CFG) -> MQTTClient:
    return MQTTClient(asyncio.Lock(), link or (lambda: True), lambda: None, config, sources=sources, consumers=consumers, cfg_path=_scratch.dir())


async def until(predicate: "Callable[[], bool]", timeout_ms: int = _WAIT_MS) -> bool:
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        if predicate():
            return True
        await asyncio.sleep_ms(10)
    return predicate()


async def configure(client: MQTTClient, port: int, **fields: "int | str | bool") -> None:
    body: dict[str, int | str | bool] = {"MQTTEnable": True, "MQTTHost": "127.0.0.1", "MQTTPort": port, "MQTTClientId": "t1"}
    body.update(fields)
    results = await client._set_dict_cfg(body, client.get_cfg_schema())
    assert all(v in ("Valid", "Unchanged") for v in results.values()), results


async def start(client: MQTTClient) -> "list[asyncio.Task[None]]":
    assert await client.setup()
    return [client.start_asy_connection(), client.start_asy_publish()]


async def stop(client: MQTTClient, tasks: "list[asyncio.Task[None]]", broker: "FakeBroker | None" = None) -> None:
    for task in tasks:
        task.cancel()
    for task in tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass
    await client._close()
    if broker is not None:
        await broker.stop()


async def errnums(client: MQTTClient) -> "list[int]":
    log: ErrorLog = await client.get_error_counter()
    nums = log["MQTT"]["ErrNum"]
    assert isinstance(nums, list)
    return [n for n in nums if n]


async def broker_and_client(
    *, link: "Callable[[], bool] | None" = None, consumers: "tuple[MqttConsumer, ...]" = (), sources: "tuple[_Source, ...]" = (), config: MqttConfig = _CFG,
) -> "tuple[FakeBroker, MQTTClient, list[asyncio.Task[None]]]":
    broker = FakeBroker(_port())
    await broker.start()
    client = make_client(link=link, consumers=consumers, sources=sources, config=config)
    tasks = await start(client)
    await configure(client, broker.port)
    client.reconnect()  # the settings group's post_fct, as a PUT runs it
    return broker, client, tasks


def test_connects_with_a_clean_session_and_a_will_then_subscribes_and_publishes_online() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client()
        try:
            assert await until(lambda: len(broker.published(b"sensors/t1/status")) == 1)
            connect = broker.connects[0]
            assert connect["client_id"] == b"t1"
            assert connect["flags"] == 0x02 | 0x04 | 0x08 | 0x20  # clean, will, will QoS 1, will retain; no credentials
            assert connect["keepalive"] == _CFG.keepalive_s
            assert connect["will_topic"] == b"sensors/t1/status"
            assert connect["will_message"] == b"offline"
            subscribes = [body for first, body in broker.packets if first == 0x82]
            assert len(subscribes) == 1
            flt, i = read_str(subscribes[0], 2)
            assert flt == b"sensors/t1/cmd/#"
            assert subscribes[0][i] == 1
            first, payload = broker.published(b"sensors/t1/status")[0]
            assert first & 0x07 == 0x03  # QoS 1, retained
            assert payload == b"online"
            status = client.get_link_status()
            assert status["MQTTState"] == "connected"
            assert status["MQTTConnected"] is True
            assert status["MQTTBroker"] == "127.0.0.1"
            assert status["MQTTConnects"] == 1
            assert (await client.get_data()).Connected is True
            assert await errnums(client) == []
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_credentials_are_sent_only_when_set() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = make_client()
        tasks = await start(client)
        try:
            await configure(client, broker.port, MQTTUser="u", MQTTPW="secret")
            client.reconnect()
            assert await until(lambda: len(broker.connects) == 1)
            assert broker.connects[0]["user"] == b"u"
            assert broker.connects[0]["password"] == b"secret"
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_disabled_client_opens_no_connection_and_logs_nothing() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = make_client()
        tasks = await start(client)
        try:
            await configure(client, broker.port, MQTTEnable=False)
            client.reconnect()
            await asyncio.sleep_ms(600)
            assert broker.connections == 0
            assert client.get_link_status()["MQTTState"] == "disabled"
            assert await errnums(client) == []
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_an_enabled_client_without_a_host_stays_off() -> None:
    async def scenario() -> None:
        client = make_client()
        tasks = await start(client)
        try:
            await configure(client, 1883, MQTTHost="")
            client.reconnect()
            await asyncio.sleep_ms(300)
            assert client.get_link_status()["MQTTState"] == "disabled"
            assert await errnums(client) == []
        finally:
            await stop(client, tasks)

    run(scenario())


def test_a_reconnect_wakes_a_disabled_client_at_once() -> None:
    config = MqttConfig("t1", 60, 1000, 800, 500, 100, 400, 600, 200, 300, 20, 50, 60000, 100, 1)  # an idle recheck of a minute

    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = make_client(config=config)
        tasks = await start(client)
        try:
            await asyncio.sleep_ms(100)  # the keeper is idling on the disabled default
            await configure(client, broker.port)
            client.reconnect()
            assert await until(lambda: broker.connections == 1, timeout_ms=2000)
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_down_link_is_waited_out_without_a_connection_or_a_log() -> None:
    link = [False]

    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(link=lambda: link[0])
        try:
            await asyncio.sleep_ms(400)
            assert broker.connections == 0
            assert client.get_link_status()["MQTTState"] == "waiting"
            link[0] = True
            assert await until(client.is_connected)
            assert await errnums(client) == []
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_losing_the_link_ends_the_connection_quietly_and_it_returns_with_the_link() -> None:
    link = [True]

    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(link=lambda: link[0])
        try:
            assert await until(client.is_connected)
            link[0] = False
            assert await until(lambda: not client.is_connected())
            assert client.get_link_status()["MQTTLastReason"] == "link down"  # set with the state, in one step
            link[0] = True
            assert await until(lambda: broker.connections == 2)
            assert await until(client.is_connected)
            assert await errnums(client) == []  # WIFI logs its own loss
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_raising_link_callback_is_logged_and_read_as_down() -> None:
    def broken() -> bool:
        raise ValueError("broken callback")

    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(link=broken)
        try:
            assert await until(lambda: client.get_link_status()["MQTTState"] == "waiting")
            await asyncio.sleep_ms(100)
            assert broker.connections == 0
            assert code("E", "CALLBACK") in await errnums(client)
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_refused_connack_is_logged_and_retried_on_a_growing_backoff() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.connack_rc = 5  # not authorized
        await broker.start()
        client = make_client()
        tasks = await start(client)
        try:
            await configure(client, broker.port)
            client.reconnect()
            assert await until(lambda: broker.connections >= 3)
            assert not client.is_connected()
            assert client._backoff_ms > _CFG.backoff_min_ms
            nums = await errnums(client)
            assert nums[-1] == code("E", "MQTT_REFUSED")
            assert code("E", "MQTT_CONNECT") not in nums
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_no_listener_is_a_connect_failure_and_the_backoff_caps() -> None:
    async def scenario() -> None:
        client = make_client()
        tasks = await start(client)
        try:
            await configure(client, _port())  # nothing listens there
            client.reconnect()
            assert await until(lambda: client._backoff_ms == _CFG.backoff_max_ms)
            assert client.get_link_status()["MQTTLastReason"] == "connect failed"
            assert (await errnums(client))[-1] == code("E", "MQTT_CONNECT")
            log = await client.get_error_counter()
            assert log["MQTT"]["ErrCount"] >= 3  # one per attempt, one history slot (the newest-entry rule)
            assert (await errnums(client)).count(code("E", "MQTT_CONNECT")) == 1
        finally:
            await stop(client, tasks)

    run(scenario())


def test_an_unresolvable_broker_name_is_logged_as_dns() -> None:
    real = asy_mqtt_client.resolve_ipv4

    async def no_answer(*_args: object, **_kw: object) -> None:
        return None

    async def scenario() -> None:
        client = make_client()
        tasks = await start(client)
        try:
            await configure(client, 1883, MQTTHost="broker.invalid")
            client.reconnect()
            assert await until(lambda: client._backoff_ms > _CFG.backoff_min_ms)
            assert (await errnums(client))[-1] == code("E", "MQTT_DNS")
        finally:
            await stop(client, tasks)

    asy_mqtt_client.resolve_ipv4 = no_answer
    try:
        run(scenario())
    finally:
        asy_mqtt_client.resolve_ipv4 = real


def test_a_missing_pingresp_ends_the_connection_and_the_client_reconnects() -> None:
    config = MqttConfig("t1", 60, 300, 250, 500, 100, 400, 600, 200, 300, 20, 50, 200, 100, 1)

    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.answer_pings = False
        await broker.start()
        client = make_client(config=config)
        tasks = await start(client)
        try:
            await configure(client, broker.port)
            client.reconnect()
            assert await until(lambda: broker.connections >= 2)
            assert count(client, "MQTTPingTimeouts") >= 1
            assert code("E", "MQTT_NO_PINGRESP") in await errnums(client)
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_short_sessions_warn_once_per_episode() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.close_after_connack = True  # what a takeover by a second client with this id looks like
        await broker.start()
        client = make_client()
        tasks = await start(client)
        try:
            await configure(client, broker.port)
            client.reconnect()
            assert await until(lambda: count(client, "MQTTShortSessions") >= 5, timeout_ms=8000)
            log = await client.get_error_counter()
            types = log["MQTT"]["ErrType"]
            nums = log["MQTT"]["ErrNum"]
            assert isinstance(types, list) and isinstance(nums, list)
            warnings = [nums[i] for i in range(len(types)) if types[i] == "W"]  # zip() has no strict= on MicroPython
            assert warnings == [code("W", "MQTT_SHORT_SESSIONS")]
            assert code("E", "MQTT_LOST") in nums
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_only_a_stable_session_resets_the_backoff() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.close_after_connack = True
        await broker.start()
        client = make_client()
        tasks = await start(client)
        try:
            await configure(client, broker.port)
            client.reconnect()
            assert await until(lambda: client._backoff_ms == _CFG.backoff_max_ms, timeout_ms=6000)
            broker.close_after_connack = False
            assert await until(client.is_connected, timeout_ms=3000)
            assert client._backoff_ms == _CFG.backoff_max_ms  # not on CONNACK
            assert await until(lambda: client._backoff_ms == _CFG.backoff_min_ms, timeout_ms=3000)
            assert client._short_streak == 0
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_an_unacknowledged_qos1_message_is_resent_with_dup_then_given_up() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.ack_publishes = False
        await broker.start()
        client = make_client()
        tasks = await start(client)
        try:
            await configure(client, broker.port)
            client.reconnect()
            assert await until(client.is_connected)
            assert client.publish("x/y", b"once", qos=1)
            assert await until(lambda: count(client, "MQTTTxDropped") >= 1)
            sent = broker.published(b"x/y")
            assert len(sent) == 3  # mqtt.qos1_max_tries
            assert sent[0][0] & 0x08 == 0
            assert all(first & 0x08 for first, _p in sent[1:])
            pids = {(body[5], body[6]) for first, body in broker.packets if first & 0xF0 == 0x30 and body[2:5] == b"x/y"}
            assert len(pids) == 1
            assert client.is_connected()  # a give-up is counted, never a teardown
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_qos1_queued_while_down_is_sent_after_the_connect() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = make_client()
        tasks = await start(client)
        try:
            await configure(client, broker.port, MQTTEnable=False)
            client.reconnect()
            await asyncio.sleep_ms(50)
            assert not client.publish("q/1", b"a", qos=1)  # disabled: nothing queues
            await configure(client, broker.port)
            client.reconnect()
            assert await until(lambda: client.get_link_status()["MQTTState"] != "disabled")
            assert await until(client.is_connected)
            await broker.stop()
            assert await until(lambda: not client.is_connected())
            assert client.publish("q/1", b"held", qos=1)  # down, not disabled: QoS 1 waits for the next session
            assert not client.publish("q/0", b"lost")  # QoS 0 never waits
            broker = FakeBroker(broker.port)
            await broker.start()
            assert await until(lambda: len(broker.published(b"q/1")) == 1, timeout_ms=6000)
            assert broker.published(b"q/1")[0][1] == b"held"
            assert broker.published(b"q/0") == []
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_publish_refuses_and_counts_what_it_cannot_send() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client()
        try:
            assert await until(client.is_connected)
            before = count(client, "MQTTTxDropped")
            assert not client.publish("a/+", b"x")
            assert not client.publish("a/#", b"x")
            assert not client.publish("", b"x")
            assert not client.publish("t" * 129, b"x")
            assert not client.publish("a/b", b"x" * 385)
            assert not client.publish("a/b", b"x", qos=2)
            assert count(client, "MQTTTxDropped") == before + 6
            assert client.publish("a/b", "text payload")
            assert await until(lambda: len(broker.published(b"a/b")) == 1)
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_full_ring_lets_qos0_give_way_first() -> None:
    client = make_client()
    client._state = 3  # connected, with no socket: no keeper runs in this test, so nothing is flushed
    for i in range(7):
        assert client.publish("q1", bytes([i]), qos=1)
    assert client.publish("q0", b"old")
    assert client.publish("q0", b"new")  # the ring is full: the queued QoS 0 message gives way
    assert count(client, "MQTTTxDropped") == 1
    assert client.publish("q1", b"x", qos=1)  # and gives way to QoS 1 too
    assert count(client, "MQTTTxDropped") == 2
    assert not client.publish("q1", b"y", qos=1)  # eight QoS 1 messages: nothing gives way
    assert not client.publish("q0", b"z")
    assert count(client, "MQTTTxDropped") == 4
    assert [bytes(client._slot_topic[i] or b"") for i in range(8)] == [b"q1"] * 8


def test_inbound_qos1_is_acknowledged_by_the_keeper_and_dispatched() -> None:
    got: list[tuple[bytes, bytes, bool]] = []

    def consumer(topic: memoryview, payload: memoryview, retained: bool) -> None:  # noqa: FBT001 - the callback's shape
        got.append((bytes(topic), bytes(payload), retained))

    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.after_subscribe = [publish_packet(b"ext/temp", b"21.5", qos=1, pid=0x0102, retain=True)]
        await broker.start()
        client = make_client(consumers=(MqttConsumer("ext/#", consumer),))
        tasks = await start(client)
        try:
            await configure(client, broker.port)
            client.reconnect()
            assert await until(lambda: len(got) == 1)
            assert got[0] == (b"ext/temp", b"21.5", True)
            subscribes = [body for first, body in broker.packets if first == 0x82]
            filters = []
            i = 2
            while i < len(subscribes[0]):
                flt, i = read_str(subscribes[0], i)
                filters.append(flt)
                i += 1
            assert filters == [b"sensors/t1/cmd/#", b"ext/#"]
            assert await until(lambda: any(first == 0x40 and body == b"\x01\x02" for first, body in broker.packets))
            status = client.get_link_status()
            assert status["MQTTRxMsgs"] == 1
            assert status["MQTTLastRxTopic"] == "ext/temp"
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_raising_consumer_is_logged_and_its_message_still_acknowledged() -> None:
    def consumer(_topic: memoryview, _payload: memoryview, _retained: bool) -> None:  # noqa: FBT001 - the callback's shape
        raise ValueError("consumer fault")

    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.after_subscribe = [publish_packet(b"ext/x", b"1", qos=1, pid=7)]
        await broker.start()
        client = make_client(consumers=(MqttConsumer("ext/#", consumer),))
        tasks = await start(client)
        try:
            await configure(client, broker.port)
            client.reconnect()
            assert await until(lambda: any(first == 0x40 for first, _b in broker.packets))
            assert await until(lambda: client._counts[8] == 1)
            await asyncio.sleep_ms(100)
            assert code("E", "CALLBACK") in await errnums(client)
            assert client.is_connected()
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_the_own_cmd_topic_is_counted_and_shown() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client()
        try:
            assert await until(client.is_connected)
            await broker.send(publish_packet(b"sensors/t1/cmd/hello", b"yo"))
            assert await until(lambda: count(client, "MQTTRxMsgs") == 1)
            assert client.get_link_status()["MQTTLastRxTopic"] == "sensors/t1/cmd/hello"
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_an_oversize_packet_is_discarded_and_the_next_one_parsed() -> None:
    got: list[bytes] = []

    def consumer(_topic: memoryview, payload: memoryview, _retained: bool) -> None:  # noqa: FBT001 - the callback's shape
        got.append(bytes(payload))

    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.after_subscribe = [publish_packet(b"ext/big", b"B" * 5000), publish_packet(b"ext/small", b"ok")]
        await broker.start()
        client = make_client(consumers=(MqttConsumer("ext/#", consumer),))
        tasks = await start(client)
        try:
            await configure(client, broker.port)
            client.reconnect()
            assert await until(lambda: got == [b"ok"])
            assert count(client, "MQTTRxDropped") == 1
            assert client.is_connected()
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_fifth_length_byte_closes_with_a_protocol_error() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client()
        try:
            assert await until(client.is_connected)
            await broker.send(b"\x30\xff\xff\xff\xff\x01")
            assert await until(lambda: client.get_link_status()["MQTTLastReason"] == "protocol error")
            assert code("E", "MQTT_PROTOCOL") in await errnums(client)
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_an_unexpected_packet_closes_with_a_protocol_error() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client()
        try:
            assert await until(client.is_connected)
            await broker.send(b"\x20\x02\x00\x00")  # a second CONNACK
            assert await until(lambda: client.get_link_status()["MQTTLastReason"] == "protocol error")
            assert code("E", "MQTT_PROTOCOL") in await errnums(client)
            assert await until(lambda: broker.connections == 2)
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_refused_subscription_is_logged_and_the_connection_stays() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.suback_code = 0x80
        await broker.start()
        client = make_client()
        tasks = await start(client)
        try:
            await configure(client, broker.port)
            client.reconnect()
            assert await until(client.is_connected)
            await asyncio.sleep_ms(150)
            assert code("E", "MQTT_SUB_REFUSED") in await errnums(client)
            assert client.is_connected()
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_reconnect_says_disconnect_and_uses_the_new_settings() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client()
        try:
            assert await until(client.is_connected)
            await configure(client, broker.port, MQTTPrefix="home", MQTTClientId="t2")
            client.reconnect()
            assert await until(lambda: len(broker.connects) == 2)
            assert broker.disconnects == 1  # the client ended it itself: the broker drops the will
            assert broker.published(b"sensors/t1/status")[-1] == (0x31, b"offline")  # so it sets the old status itself
            assert broker.connects[1]["client_id"] == b"t2"
            assert broker.connects[1]["will_topic"] == b"home/t2/status"
            assert await until(lambda: len(broker.published(b"home/t2/status")) == 1)
            assert client.get_link_status()["MQTTLastReason"] == "reconfigured"
            assert await errnums(client) == []
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_put_refuses_strings_outside_their_mqtt_shape() -> None:
    async def scenario() -> None:
        client = make_client()
        assert await client.setup()
        schema = client.get_cfg_schema()
        bad = {"MQTTClientId": "a b", "MQTTPrefix": "a/#", "MQTTUser": "a\x00b"}
        results = await client._set_dict_cfg(bad, schema)
        assert results == dict.fromkeys(bad, "Invalid")
        nums = await errnums(client)
        assert nums == [code("E", "BAD_ARG")]
        good = {"MQTTHost": "", "MQTTClientId": "node-1", "MQTTPrefix": "home/sensors", "MQTTUser": "", "MQTTPW": "pw"}
        results = await client._set_dict_cfg(good, schema)
        assert all(v in ("Valid", "Unchanged") for v in results.values()), results
        results = await client._set_dict_cfg({"MQTTPort": 0, "MQTTPubInterval": 5}, schema)
        assert results == {"MQTTPort": "Invalid", "MQTTPubInterval": "Invalid"}

    run(scenario())


def test_get_masks_the_password() -> None:
    async def scenario() -> None:
        client = make_client()
        assert await client.setup()
        await client._set_dict_cfg({"MQTTPW": "secret"}, client.get_cfg_schema())
        cfg = (await client.get_dict_cfg())["MQTT"]
        assert cfg["MQTTPW"] == "********"
        assert cfg["MQTTClientId"] == "t1"  # the build's default (the device hostname)
        assert set(cfg) == {"MQTTEnable", "MQTTHost", "MQTTPort", "MQTTUser", "MQTTPW", "MQTTClientId", "MQTTPrefix", "MQTTPubInterval"}

    run(scenario())


def test_an_invalid_build_default_client_id_falls_back() -> None:
    client = make_client(config=MqttConfig("bad id!", 60, 300, 250, 500, 100, 400, 600, 200, 300, 20, 50, 200, 100, 1))
    assert client._val_client_id[0][2] == "SensorNode"


def test_a_stored_value_out_of_shape_keeps_the_client_off_with_one_warning() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = make_client()
        assert await client.setup()
        await configure(client, broker.port)
        await client.cfgmgr.flush_pending()
        client.cfgmgr._cache["MQTTPrefix"] = "a/#"  # as a hand-edited file would hold it
        tasks = [client.start_asy_connection(), client.start_asy_publish()]
        try:
            await asyncio.sleep_ms(700)
            assert broker.connections == 0
            log = await client.get_error_counter()
            assert log["MQTT"]["ErrCount"] == 1
            assert log["MQTT"]["ErrNum"][-1] == code("W", "STORED_DEFAULT")
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_host_out_of_shape_is_taken_at_put_and_keeps_the_client_off() -> None:
    # Like NTPHost: a length-only check at PUT, the shape at use, one warning and no connection attempt.
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = make_client()
        assert await client.setup()
        results = await client._set_dict_cfg({"MQTTHost": "bad host"}, client.get_cfg_schema())
        assert results == {"MQTTHost": "Valid"}
        await configure(client, broker.port, MQTTHost="bad host")
        tasks = [client.start_asy_connection(), client.start_asy_publish()]
        try:
            await asyncio.sleep_ms(700)
            assert broker.connections == 0
            log = await client.get_error_counter()
            assert log["MQTT"]["ErrCount"] == 1
            assert log["MQTT"]["ErrNum"][-1] == code("W", "STORED_DEFAULT")
        finally:
            await stop(client, tasks, broker)

    run(scenario())


# Mirrors asy_mqtt_client's const-folded _UNCONFIRMED_MAX, which no test can import.
# @tunable mqtt.unconfirmed_max_bytes = 2000
_UNCONFIRMED_MAX = 2000
# A ping interval no test outlives, so every PINGREQ these tests see is one the byte cap asked for.
_CAP_CFG = MqttConfig("t1", 60, 60000, 3000, 500, 100, 400, 600, 200, 300, 20, 50, 200, 100, 1)
_CAP_MESSAGES = 7  # the ring's eight slots, less the online status still in flight
_CAP_PAYLOAD = b"m" * 380  # about 388 B on the wire, so five fit under the cap and the sixth must wait


def _client_bytes_after_connect(broker: FakeBroker) -> int:
    return sum(1 + len(encode_length(len(body))) + len(body) for first, body in broker.packets if first & 0xF0 != 0x10)


def test_unconfirmed_bytes_stop_at_the_cap_and_ask_for_an_early_ping() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(config=_CAP_CFG)
        broker.answer_pings = False  # nothing ever confirms: the cap is all that stops the writes
        try:
            assert await until(client.is_connected)
            assert all(client.publish("t/x", _CAP_PAYLOAD) for _ in range(_CAP_MESSAGES))
            assert await until(lambda: any(first == 0xC0 for first, _ in broker.packets))
            await asyncio.sleep_ms(300)  # several ticks: nothing more may follow the held message
            assert _client_bytes_after_connect(broker) <= _UNCONFIRMED_MAX
            assert len(broker.published(b"t/x")) < _CAP_MESSAGES
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_pingresp_releases_the_held_messages() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(config=_CAP_CFG)
        try:
            assert await until(client.is_connected)
            assert all(client.publish("t/x", _CAP_PAYLOAD) for _ in range(_CAP_MESSAGES))
            assert await until(lambda: len(broker.published(b"t/x")) == _CAP_MESSAGES)
            assert _client_bytes_after_connect(broker) > _UNCONFIRMED_MAX  # more than one cap's worth, through pings
            assert any(first == 0xC0 for first, _ in broker.packets)  # the interval is a minute: the cap sent it
            assert client.is_connected()
        finally:
            await stop(client, tasks, broker)

    run(scenario())


class _StallingStream:
    # A stream whose drain never completes: pure asyncio, no poller behind it (CLAUDE.md's bounded-fake rule).
    def __init__(self) -> None:
        self.out_buf = b"pending"
        self.written: list[bytes] = []

    def write(self, buf: "bytes | bytearray | memoryview") -> None:
        self.written.append(bytes(buf))

    async def drain(self) -> None:
        await asyncio.sleep_ms(60000)

    async def readinto(self, _buf: memoryview) -> int:
        await asyncio.sleep_ms(60000)
        return 0

    async def wait_closed(self) -> None:
        pass


def test_a_drain_timeout_ends_the_connection() -> None:
    # The cancellation rule: a timed-out drain cancelled a socket waiter, so the connection must end in that tick.
    async def scenario() -> int:
        client = make_client()
        assert await client.setup()
        client._base = b"sensors/t1"
        stream = _StallingStream()
        client._new_connection()
        start_ms = time.ticks_ms()
        reason = await client._serve(stream)
        assert time.ticks_diff(time.ticks_ms(), start_ms) < _CFG.drain_timeout_ms + 500
        return reason

    assert run(scenario()) == _R_STALLED


def test_a_backlog_past_its_cap_ends_the_connection() -> None:
    async def scenario() -> int:
        client = make_client()
        assert await client.setup()
        client._base = b"sensors/t1"
        stream = _StallingStream()
        stream.out_buf = b"x" * 2049
        client._new_connection()
        return await client._serve(stream)

    assert run(scenario()) == _R_STALLED


def test_measurements_are_published_as_json_with_null_for_non_finite() -> None:
    class Source:
        async def get_dict_data(self) -> "dict[str, dict[str, object]]":
            return {"SCD30": {"CO2": 612, "Temp": float("nan"), "Hum": float("inf"), "TS": None, "RGB": {"R": float("-inf"), "G": 0.5}}}

    config = MqttConfig("t1", 60, 1000, 800, 500, 100, 400, 600, 200, 300, 20, 50, 200, 100, 1)

    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(sources=(Source(),), config=config)
        try:
            assert await until(client.is_connected)  # the publisher's first round follows the CONNACK by itself
            assert await until(lambda: len(broker.published(b"sensors/t1/measurements/SCD30")) == 1)
            first, payload = broker.published(b"sensors/t1/measurements/SCD30")[0]
            assert first == 0x30  # QoS 0, not retained
            assert json.loads(payload) == {"CO2": 612, "Temp": None, "Hum": None, "TS": None, "RGB": {"R": None, "G": 0.5}}
            assert b"nan" not in payload and b"inf" not in payload
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_raising_source_is_logged_and_the_others_still_published() -> None:
    class Broken:
        async def get_dict_data(self) -> "dict[str, dict[str, object]]":
            raise ValueError("source fault")

    class Good:
        async def get_dict_data(self) -> "dict[str, dict[str, object]]":
            return {"BMP3XX": {"Pres": 1005.3}}

    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(sources=(Broken(), Good()))
        try:
            assert await until(client.is_connected)
            assert await until(lambda: len(broker.published(b"sensors/t1/measurements/BMP3XX")) == 1)
            assert code("E", "SOURCE") in await errnums(client)
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_restarted_keeper_closes_the_previous_connection_first() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client()
        try:
            assert await until(client.is_connected)
            first_reader = client._reader
            assert first_reader is not None
            tasks[0].cancel()  # as a supervisor sees a task end
            try:
                await tasks[0]
            except asyncio.CancelledError:
                pass
            tasks[0] = client.start_asy_connection()  # its restart, on the same object
            assert await until(lambda: broker.connections == 2)
            assert await until(lambda: broker.closed_by_client >= 1)
            assert await until(client.is_connected)
            assert client._reader is not first_reader
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_keeper_cancelled_during_its_teardown_still_ends() -> None:
    # A cancellation that lands while a connection is being torn down ends the keeper; none is swallowed.
    link = [True]

    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(link=lambda: link[0])
        try:
            assert await until(client.is_connected)
            for delay_ms in (0, 1, 5, 20, 45):
                link[0] = False
                await asyncio.sleep_ms(delay_ms + _CFG.link_poll_ms)
                tasks[0].cancel()
                try:
                    await asyncio.wait_for_ms(tasks[0], 1000)
                except asyncio.CancelledError:
                    pass
                assert tasks[0].done()
                link[0] = True
                tasks[0] = client.start_asy_connection()
                assert await until(client.is_connected)
        finally:
            await stop(client, tasks, broker)

    run(scenario())


class _Starved:
    # Shadows asy_mqtt_client's module-global `bytearray` for one call, the tests/ way of failing an allocation.
    def __init__(self) -> None:
        self.fired = 0

    def __call__(self, *args: int) -> bytearray:
        if not self.fired:
            self.fired += 1
            raise MemoryError("starved")
        return bytearray(*args)


def test_a_failed_buffer_allocation_keeps_the_client_off_and_is_logged() -> None:
    starved = _Starved()
    asy_mqtt_client.bytearray = starved  # type: ignore[attr-defined]
    try:
        client = make_client()
    finally:
        asy_mqtt_client.bytearray = bytearray  # type: ignore[attr-defined]
    assert starved.fired == 1

    async def scenario() -> None:
        tasks = await start(client)
        try:
            await configure(client, 1883)
            client.reconnect()
            await asyncio.sleep_ms(200)
            status = client.get_link_status()
            assert status["MQTTState"] == "no memory"
            assert status["MQTTConnects"] == 0
            assert not client.publish("a/b", b"x", qos=1)
            assert await errnums(client) == [code("E", "ALLOC")]
        finally:
            await stop(client, tasks)

    run(scenario())


def test_the_link_status_has_every_published_field() -> None:
    status = make_client().get_link_status()
    assert set(status) == {
        "MQTTState", "MQTTConnected", "MQTTBroker", "MQTTUptime", "MQTTConnects", "MQTTTeardowns", "MQTTLastReason",
        "MQTTTxMsgs", "MQTTTxDropped", "MQTTRxMsgs", "MQTTRxDropped", "MQTTPingTimeouts", "MQTTShortSessions", "MQTTLastRxTopic",
    }
    assert status["MQTTState"] == "disabled"
    assert status["MQTTBroker"] is None
    assert status["MQTTLastRxTopic"] is None


def test_the_starters_and_fan_in_follow_the_service_shape() -> None:
    client = make_client()
    assert client.get_task_starters() == [client.start_asy_connection, client.start_asy_publish]
    assert client.get_timer_starters() == []
    assert client.get_error_sources() == [client, client.cfgmgr]
    assert client.name == "MQTT"
    assert client.cfgmgr.name == "CFGMGR_MQTT"


def test_a_long_length_prefix_is_split_across_reads() -> None:
    got: list[bytes] = []

    def consumer(_topic: memoryview, payload: memoryview, _retained: bool) -> None:  # noqa: FBT001 - the callback's shape
        got.append(bytes(payload))

    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(consumers=(MqttConsumer("ext/#", consumer),))
        try:
            assert await until(client.is_connected)
            packet = publish_packet(b"ext/p", b"P" * 200)  # a two-byte remaining length
            assert packet[1:3] == encode_length(207)
            for i in range(len(packet)):  # one byte per write: every split point the parser can meet
                await broker.send(packet[i : i + 1])
            assert await until(lambda: got == [b"P" * 200])
        finally:
            await stop(client, tasks, broker)

    run(scenario())


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
