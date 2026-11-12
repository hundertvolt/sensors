"""The MQTT client against a scripted broker on loopback (tests/_mqtt_fake_broker.py): connect, session and will,
gating (the hotspot's too) and backoff, QoS 0/1 both ways, the unconfirmed-bytes cap, the partner API, its faults."""

import asyncio
import gc
import io
import json
import socket
import time

from _async_harness import run
from _error_codes import code
from _mqtt_fake_broker import FakeBroker, encode_length, publish_packet, read_str
from _port_bands import PortAllocator
from _recording_print import record_prints
from _src_const import src_int
from _tmp_scratch import TmpScratch

import asy_mqtt_client
from asy_mqtt_client import MQTTClient, MqttConfig
from asy_print_log import LogConfig

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

    from asy_mqtt_client import MqttCallback
    from asy_print_log import ErrorLog

    Consumers = tuple[tuple[str, MqttCallback], ...]  # (filter below <base>, callback), registered before the tasks start

# This file's own port band (SPECIFICATION.md E.1: below 32768, outside every neighbour's band); one port per broker.
_PORTS = PortAllocator("test_asy_mqtt_client")
_scratch = TmpScratch("mqtt")

# Short timings, so a scenario takes well under a second per phase: client id, response, connect, backoff min/max,
# stable-after, QoS 1 retry, drain, tick, link poll, idle recheck and DNS timeout. The ping interval is the
# MQTTPingInterval setting, 180 s by default: no idle ping within a test, only the one confirming each publish.
_CFG = MqttConfig("t1", 800, 500, 100, 400, 600, 200, 300, 20, 50, 200, 100)
# A response deadline no test outlives: no ping a test causes waits on the broker's wire behind a packet the test
# feeds a byte at a time.
_QUIET_CFG = MqttConfig("t1", 3000, 500, 100, 400, 600, 200, 300, 20, 50, 200, 100)
_WAIT_MS = 8000  # every wait polls; the bound only matters on a failure
# No in-session QoS 1 retry within a test: every PUBLISH sent again is one the session sent again.
_SESSION_CFG = MqttConfig("t1", 3000, 500, 100, 400, 600, 60000, 300, 20, 50, 200, 100)
_R_STALLED: int = src_int("src/asy_mqtt_client.py", "_R_STALLED")  # the client's const()-folded teardown reason
_R_UNEXPECTED: int = src_int("src/asy_mqtt_client.py", "_R_UNEXPECTED")
_SLOT_INFLIGHT: int = src_int("src/asy_mqtt_client.py", "_SLOT_INFLIGHT")
_ST_CONNECTED: int = src_int("src/asy_mqtt_client.py", "_ST_CONNECTED")
_C_CONSUMER_ERR: int = src_int("src/asy_mqtt_client.py", "_C_CONSUMER_ERR")


def _ignore(_topic: memoryview, _payload: memoryview, _flags: int) -> None:
    pass


_COMMANDS: "Consumers" = (("cmd/#", _ignore),)  # a partner's subscription, as the exerciser registers it


def count(client: MQTTClient, key: str) -> int:
    value = client.get_link_status()[key]
    assert isinstance(value, int)
    return value


def _port() -> int:
    return _PORTS.next()


def _make_client(*, link: "Callable[[], bool] | None" = None, consumers: "Consumers" = (), config: MqttConfig = _CFG) -> MQTTClient:
    client = MQTTClient(asyncio.Lock(), link or (lambda: True), lambda: None, config, cfg_path=_scratch.dir())
    for topic_filter, callback in consumers:
        client.add_consumer(topic_filter, callback)
    return client


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
    await client.setup()
    return [client.start_asy_connection()]


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
    *, link: "Callable[[], bool] | None" = None, consumers: "Consumers" = (), config: MqttConfig = _CFG, fields: "dict[str, int | str | bool] | None" = None,
) -> "tuple[FakeBroker, MQTTClient, list[asyncio.Task[None]]]":
    broker = FakeBroker(_port())
    await broker.start()
    client = _make_client(link=link, consumers=consumers, config=config)
    tasks = await start(client)
    await configure(client, broker.port, **(fields or {}))
    client.reconnect()  # the settings group's post_fct, as a PUT runs it
    return broker, client, tasks


def test_connects_with_a_clean_session_and_a_will_then_subscribes_and_publishes_online() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(consumers=_COMMANDS)
        try:
            assert await until(lambda: len(broker.published(b"sensors/t1/status")) == 1)
            connect = broker.connects[0]
            assert connect["client_id"] == b"t1"
            assert connect["flags"] == 0x02 | 0x04 | 0x08 | 0x20  # clean, will, will QoS 1, will retain; no credentials
            assert connect["keepalive"] == 180 + 1  # the interval setting plus the response deadline, in whole seconds
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
        client = _make_client()
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
        client = _make_client()
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
        client = _make_client()
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
    config = MqttConfig("t1", 800, 500, 100, 400, 600, 200, 300, 20, 50, 60000, 100)  # an idle recheck of a minute

    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = _make_client(config=config)
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
        client = _make_client()
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
        client = _make_client()
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
        client = _make_client()
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
    config = MqttConfig("t1", 250, 500, 100, 400, 600, 200, 300, 20, 50, 200, 100)

    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.answer_pings = False
        await broker.start()
        client = _make_client(config=config)
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
        client = _make_client()
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
        client = _make_client()
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
        client = _make_client()
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
        client = _make_client()
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
    client = _make_client()
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
    got: list[tuple[bytes, bytes, int]] = []

    def consumer(topic: memoryview, payload: memoryview, flags: int) -> None:
        got.append((bytes(topic), bytes(payload), flags))

    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.after_subscribe = [publish_packet(b"sensors/t1/ext/temp", b"21.5", qos=1, pid=0x0102, retain=True)]
        await broker.start()
        client = _make_client(consumers=(("cmd/#", _ignore), ("ext/#", consumer)))
        tasks = await start(client)
        try:
            await configure(client, broker.port)
            client.reconnect()
            assert await until(lambda: len(got) == 1)
            assert got[0] == (b"sensors/t1/ext/temp", b"21.5", 0x03)  # the flag bits: QoS 1, retained
            subscribes = [body for first, body in broker.packets if first == 0x82]
            filters = []
            i = 2
            while i < len(subscribes[0]):
                flt, i = read_str(subscribes[0], i)
                filters.append(flt)
                i += 1
            assert filters == [b"sensors/t1/cmd/#", b"sensors/t1/ext/#"]  # each below the base, in registration order
            assert await until(lambda: any(first == 0x40 and body == b"\x01\x02" for first, body in broker.packets))
            status = client.get_link_status()
            assert status["MQTTRxMsgs"] == 1
            assert status["MQTTLastRxTopic"] == "sensors/t1/ext/temp"
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_raising_consumer_is_logged_and_its_message_still_acknowledged() -> None:
    def consumer(_topic: memoryview, _payload: memoryview, _flags: int) -> None:
        raise ValueError("consumer fault")

    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.after_subscribe = [publish_packet(b"sensors/t1/ext/x", b"1", qos=1, pid=7)]
        await broker.start()
        client = _make_client(consumers=(("ext/#", consumer),))
        tasks = await start(client)
        try:
            await configure(client, broker.port)
            client.reconnect()
            assert await until(lambda: any(first == 0x40 for first, _b in broker.packets))
            assert await until(lambda: client._counts[_C_CONSUMER_ERR] == 1)
            await asyncio.sleep_ms(100)
            assert code("E", "CALLBACK") in await errnums(client)
            assert client.is_connected()
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_message_on_a_partners_filter_is_counted_and_its_topic_shown() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(consumers=_COMMANDS)
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

    def consumer(_topic: memoryview, payload: memoryview, _flags: int) -> None:
        got.append(bytes(payload))

    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.after_subscribe = [publish_packet(b"sensors/t1/ext/big", b"B" * 5000), publish_packet(b"sensors/t1/ext/small", b"ok")]
        await broker.start()
        client = _make_client(consumers=(("ext/#", consumer),))
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
        client = _make_client(consumers=_COMMANDS)
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
        client = _make_client()
        await client.setup()
        schema = client.get_cfg_schema()
        bad = {"MQTTHost": "bad host", "MQTTClientId": "a b", "MQTTPrefix": "a/#", "MQTTUser": "a\x00b"}
        results = await client._set_dict_cfg(bad, schema)
        assert results == dict.fromkeys(bad, "Invalid")
        nums = await errnums(client)
        assert nums == [code("E", "BAD_ARG")]
        good = {"MQTTHost": "", "MQTTClientId": "node-1", "MQTTPrefix": "home/sensors", "MQTTUser": "", "MQTTPW": "pw"}
        results = await client._set_dict_cfg(good, schema)
        assert all(v in ("Valid", "Unchanged") for v in results.values()), results
        results = await client._set_dict_cfg({"MQTTPort": 0}, schema)
        assert results == {"MQTTPort": "Invalid"}

    run(scenario())


def test_get_masks_the_password() -> None:
    async def scenario() -> None:
        client = _make_client()
        await client.setup()
        await client._set_dict_cfg({"MQTTPW": "secret"}, client.get_cfg_schema())
        cfg = (await client.get_dict_cfg())["MQTT"]
        assert cfg["MQTTPW"] == "********"
        assert cfg["MQTTClientId"] == "t1"  # the build's default (the device hostname)
        assert set(cfg) == {
            "MQTTEnable", "MQTTHost", "MQTTPort", "MQTTUser", "MQTTPW", "MQTTClientId", "MQTTPrefix", "MQTTPingInterval",
            "MQTTPersistent", "MQTTWillTopic", "MQTTOnlineMsg", "MQTTWillMsg", "MQTTWillQoS", "MQTTWillRetain",
        }

    run(scenario())


def test_an_invalid_build_default_client_id_falls_back() -> None:
    client = _make_client(config=MqttConfig("bad id!", 250, 500, 100, 400, 600, 200, 300, 20, 50, 200, 100))
    assert client._val_client_id[0][2] == "SensorNode"


def test_a_stored_value_out_of_shape_keeps_the_client_off_with_one_warning() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = _make_client()
        await client.setup()
        await configure(client, broker.port)
        await client.cfgmgr.flush_pending()
        client.cfgmgr._cache["MQTTPrefix"] = "a/#"  # as a hand-edited file would hold it
        tasks = [client.start_asy_connection()]
        try:
            await asyncio.sleep_ms(700)
            assert broker.connections == 0
            log = await client.get_error_counter()
            assert log["MQTT"]["ErrCount"] == 1
            assert log["MQTT"]["ErrNum"][-1] == code("W", "STORED_DEFAULT")
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_host_out_of_shape_is_refused_at_put_and_a_stored_one_keeps_the_client_off() -> None:
    # Like NTPHost: the hostName shape at PUT, and again at use, where a hand-edited file gets one warning and no connection attempt.
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = _make_client()
        await client.setup()
        results = await client._set_dict_cfg({"MQTTHost": "bad host"}, client.get_cfg_schema())
        assert results == {"MQTTHost": "Invalid"}
        await configure(client, broker.port)
        await client.cfgmgr.flush_pending()
        client.cfgmgr._cache["MQTTHost"] = "bad host"  # as a hand-edited file would hold it
        tasks = [client.start_asy_connection()]
        try:
            await asyncio.sleep_ms(700)
            assert broker.connections == 0
            assert await errnums(client) == [code("E", "BAD_ARG"), code("W", "STORED_DEFAULT")]  # the PUT's refusal, then one warning
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_the_shape_corpus_judges_the_broker_host_and_empty_is_off() -> None:
    # One corpus, the judges NTPHost already has (SPECIFICATION.md G.2); "" is the schema special, the client off.
    with open("tests/_radio_shape_cases.json") as f:
        cases = json.load(f)["hostName"]
    assert cases["accept"] and cases["reject"]

    async def put(value: str) -> str:
        client = _make_client()
        await client.setup()
        assert (await client._set_dict_cfg({"MQTTHost": "broker"}, client.get_cfg_schema())) == {"MQTTHost": "Valid"}
        return (await client._set_dict_cfg({"MQTTHost": value}, client.get_cfg_schema()))["MQTTHost"]

    async def scenario() -> None:
        for value in cases["accept"]:
            assert await put(value) == "Valid", value
        for value in cases["reject"]:
            assert await put(value) == "Invalid", value
        assert await put("") == "Valid"  # below the 1-character minimum, taken as the special

    run(scenario())


_UNCONFIRMED_MAX: int = src_int("src/asy_mqtt_client.py", "_UNCONFIRMED_MAX")  # the client's cap, read from source
_CAP_MESSAGES = 7  # the ring's eight slots, less the online status still in flight
_CAP_PAYLOAD = b"m" * 380  # about 388 B on the wire, so five fit under the cap and the sixth must wait


def _client_bytes_after_connect(broker: FakeBroker) -> int:
    return sum(1 + len(encode_length(len(body))) + len(body) for first, body in broker.packets if first & 0xF0 != 0x10)


def _pings(broker: FakeBroker, n: int) -> int:
    # PINGREQs on the n-th connection, 0 before it exists.
    return sum(1 for first, _body in _sent_on(broker, n) if first == 0xC0) if len(broker.connect_packets) > n else 0


def _kinds(broker: FakeBroker, n: int) -> "list[int]":
    return [first & 0xF0 for first, _body in _sent_on(broker, n)] if len(broker.connect_packets) > n else []


def test_the_ping_interval_takes_off_and_defaults_to_three_minutes() -> None:
    # Owner, 2026-10-13: the ping interval a setting that can be turned off, '3 min' its default.
    async def scenario() -> None:
        client = _make_client()
        await client.setup()
        cfg = (await client.get_dict_cfg())["MQTT"]
        assert cfg["MQTTPingInterval"] == 180
        schema = client.get_cfg_schema()
        cases = (
            ("MQTTPingInterval", 0, "Valid"), ("MQTTPingInterval", 10, "Valid"), ("MQTTPingInterval", 3600, "Valid"),
            ("MQTTPingInterval", 9, "Invalid"), ("MQTTPingInterval", 3601, "Invalid"),
        )
        for key, value, verdict in cases:
            assert (await client._set_dict_cfg({key: value}, schema))[key] == verdict, (key, value)

    run(scenario())


def test_the_keepalive_is_the_ping_interval_plus_the_response_deadline_and_zero_when_off() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client()
        try:
            assert await until(lambda: len(broker.connects) == 1)
            assert broker.connects[0]["keepalive"] == 181  # 180 s and the 800 ms deadline rounded up
            await configure(client, broker.port, MQTTPingInterval=30)
            client.reconnect()
            assert await until(lambda: len(broker.connects) == 2)
            assert broker.connects[1]["keepalive"] == 31
            await configure(client, broker.port, MQTTPingInterval=0)
            client.reconnect()
            assert await until(lambda: len(broker.connects) == 3)
            assert broker.connects[2]["keepalive"] == 0  # no idle ping promised, so none the broker may wait for
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_idle_pings_follow_the_interval_setting() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = _make_client()
        client._ping_unit_ms = 20  # one setting second lasts 20 ms here: an interval of 10 pings every 200 ms
        tasks = await start(client)
        try:
            await configure(client, broker.port, MQTTPingInterval=10)
            client.reconnect()
            assert await until(lambda: _pings(broker, 0) >= 1)  # the online message's confirmation
            before = _pings(broker, 0)
            await asyncio.sleep_ms(1000)
            assert 3 <= _pings(broker, 0) - before <= 7, _kinds(broker, 0)
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_with_pings_off_an_idle_connection_sends_none_and_a_publish_still_gets_one() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = _make_client()
        client._ping_unit_ms = 20
        tasks = await start(client)
        try:
            await configure(client, broker.port, MQTTPingInterval=0)
            client.reconnect()
            assert await until(lambda: _pings(broker, 0) == 1)  # the online message's confirmation alone
            await asyncio.sleep_ms(600)  # three intervals of the smallest setting
            assert _pings(broker, 0) == 1, _kinds(broker, 0)
            assert client.publish("sensors/t1/event", "open the window")
            assert await until(lambda: _pings(broker, 0) == 2)
            assert _kinds(broker, 0)[-2:] == [0x30, 0xC0], _kinds(broker, 0)  # the event, then the ping confirming it
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_publish_written_while_a_ping_is_out_gets_a_ping_of_its_own() -> None:
    # The outstanding PINGREQ went before the event, so its PINGRESP confirms nothing written after it.
    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.ping_delay_ms = 300
        await broker.start()
        client = _make_client(consumers=_COMMANDS)
        tasks = await start(client)
        try:
            await configure(client, broker.port)
            client.reconnect()
            assert await until(lambda: _pings(broker, 0) == 1)
            assert client.publish("sensors/t1/event", "open the window")
            assert await until(lambda: _pings(broker, 0) == 2)
            assert _kinds(broker, 0) == [0x80, 0x30, 0xC0, 0x30, 0xC0], _kinds(broker, 0)
            assert client.is_connected()
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_with_pings_off_a_publish_into_a_silent_broker_ends_the_link_and_a_qos1_event_goes_again() -> None:
    # The use the owner named (2026-10-13): an event sent at detection time, over a link no idle ping has checked.
    config = MqttConfig("t1", 800, 500, 100, 400, 600, 60000, 300, 20, 50, 200, 100)  # no QoS 1 retry within the test

    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(config=config, fields={"MQTTPingInterval": 0})
        try:
            assert await until(lambda: _pings(broker, 0) == 1 and not client._ping_out)
            broker.answer_pings = False
            broker.ack_publishes = False
            assert client.publish("sensors/t1/event", "open the window", qos=1)
            assert await until(lambda: count(client, "MQTTPingTimeouts") == 1)
            assert client.get_link_status()["MQTTLastReason"] == "no pingresp"
            broker.answer_pings = True
            broker.ack_publishes = True
            assert await until(lambda: len(broker.connects) == 2)
            assert await until(lambda: any(_publish_fields(first, body)[0] == b"sensors/t1/event" for first, body in _sent_on(broker, 1) if first & 0xF0 == 0x30))
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_unconfirmed_bytes_stop_at_the_cap_and_ask_for_an_early_ping() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(config=_QUIET_CFG)
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
        broker, client, tasks = await broker_and_client(config=_QUIET_CFG)
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

    async def drain(self) -> None:
        await asyncio.sleep_ms(60000)

    async def readinto(self, _buf: memoryview) -> int:
        await asyncio.sleep_ms(60000)
        return 0

    async def wait_closed(self) -> None:
        pass

    def write(self, buf: "bytes | bytearray | memoryview") -> None:
        self.written.append(bytes(buf))


def test_a_drain_timeout_ends_the_connection() -> None:
    # The cancellation rule: a timed-out drain cancelled a socket waiter, so the connection must end in that tick.
    async def scenario() -> int:
        client = _make_client()
        await client.setup()
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
        client = _make_client()
        await client.setup()
        client._base = b"sensors/t1"
        stream = _StallingStream()
        stream.out_buf = b"x" * 2049
        client._new_connection()
        return await client._serve(stream)

    assert run(scenario()) == _R_STALLED


class _FaultyStream(_StallingStream):
    # A read that raises what no socket raises: the reader's task top is all that stands between it and the loop.
    async def readinto(self, _buf: memoryview) -> int:
        raise ValueError("reader fault")


def test_an_unexpected_reader_fault_is_logged_once_by_its_task_top() -> None:
    # The reader is a create_task() target outside the starters, so its top logs (SPECIFICATION.md C.9); the keeper's
    # own end entry then adds nothing, one occurrence being one entry (C.7.1).
    async def scenario() -> "tuple[int, list[int], object]":
        client = _make_client()
        await client.setup()
        client._new_connection()
        await client._reader_loop(_FaultyStream())
        await client._log_end(client._reader_end, 0)
        log: ErrorLog = await client.get_error_counter()
        return client._reader_end, await errnums(client), log["MQTT"]["ErrCount"]

    assert run(scenario()) == (_R_UNEXPECTED, [code("E", "UNEXPECTED")], 1)


def test_no_client_buffer_needs_more_contiguous_heap_than_the_receive_buffer() -> None:
    # Contiguous chunk splitting: the outbound ring is one preallocated stream per slot, never one 3 KB block.
    client = _make_client()
    sizes = [len(v) for v in client.__dict__.values() if isinstance(v, (bytearray, memoryview))]
    assert max(sizes) == 1024, sizes
    assert len(client._slots) == 8, client._slots
    assert all(isinstance(slot, io.BytesIO) for slot in client._slots)


def test_settings_and_topics_are_born_at_setup_and_kept_while_unchanged() -> None:
    # Survivor placement: an enabled client's encoded settings and its partners' topics and filters are built inside the
    # boot list, and a reconnect with the same settings keeps those objects rather than re-birthing them in the run phase.
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        cfg_dir = _scratch.dir()
        writer = MQTTClient(asyncio.Lock(), lambda: True, lambda: None, _CFG, cfg_path=cfg_dir)
        await writer.setup()
        await configure(writer, broker.port)
        await writer.cfgmgr.flush_pending()  # on disk before the next client's setup() reads it
        client = MQTTClient(asyncio.Lock(), lambda: True, lambda: None, _CFG, cfg_path=cfg_dir)
        topic_id = client.add_topic("link/echo")  # a partner registers at its construction, before any setup()
        client.add_consumer("cmd/#", _ignore)
        await client.setup()  # a boot with the client enabled
        born = (client._base, client._status_topic, client._client_id, client._host, client._topics[topic_id], client._filters[0])
        assert born[:2] == (b"sensors/t1", b"sensors/t1/status"), born
        assert born[4:] == (b"sensors/t1/link/echo", b"sensors/t1/cmd/#"), born
        tasks = [client.start_asy_connection()]
        try:
            assert await until(client.is_connected)
            assert client.publish_under(topic_id, b"one", qos=1)
            assert await until(lambda: len(broker.published(b"sensors/t1/link/echo")) == 1)
            client.reconnect()  # unchanged settings: a new connection, the same long-lived objects
            assert await until(lambda: count(client, "MQTTConnects") == 2 and client.is_connected())
            kept = (client._base, client._status_topic, client._client_id, client._host, client._topics[topic_id], client._filters[0])
            assert all(kept[i] is born[i] for i in range(len(born))), kept
            await configure(client, broker.port, MQTTPrefix="other")
            client.reconnect()
            assert await until(lambda: count(client, "MQTTConnects") == 3 and client.is_connected())
            assert (client._base, client._status_topic, client._filters) == (b"other/t1", b"other/t1/status", (b"other/t1/cmd/#",))
            assert client.publish_under(topic_id, b"two", qos=1)
            assert await until(lambda: len(broker.published(b"other/t1/link/echo")) == 1)
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_online_goes_out_with_the_subscribe_not_a_tick_later() -> None:
    # The bench board's online reached the broker 0.9 s after a reconnect's CONNACK: a GET /status held the loop past
    # the keeper's next tick. Written in the same step as the SUBSCRIBE, it waits on no wake; this tick is 2 s.
    slow_tick = MqttConfig("t1", 3000, 500, 100, 400, 600, 200, 300, 2000, 50, 200, 100)

    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(config=slow_tick)
        try:
            assert await until(client.is_connected)
            assert await until(lambda: len(broker.published(b"sensors/t1/status")) == 1, 1000)
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
        client = _make_client()
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


def test_a_failed_buffer_allocation_prints_its_text_at_level_1() -> None:
    # The caught MemoryError's own line goes out through the client's logger from level 1 up, nothing at level 0 (the
    # memory gates read it, SPECIFICATION.md I.4(e)); setup() then persists the ALLOC entry, the test above.
    for level in (0, 1):
        asy_mqtt_client.bytearray = _Starved()  # type: ignore[attr-defined]
        try:
            with record_prints() as recorder:
                MQTTClient(asyncio.Lock(), lambda: True, lambda: None, _CFG, cfg_path=_scratch.dir(), log=LogConfig(None, 10, level))
        finally:
            asy_mqtt_client.bytearray = bytearray  # type: ignore[attr-defined]
        assert len(recorder.lines) == level, recorder.lines
    assert recorder.lines[0][0] == "MQTT", recorder.lines
    assert "starved" in recorder.text(), recorder.lines


def test_the_link_status_has_every_published_field() -> None:
    status = _make_client().get_link_status()
    assert set(status) == {
        "MQTTState", "MQTTConnected", "MQTTBroker", "MQTTUptime", "MQTTConnects", "MQTTTeardowns", "MQTTLastReason",
        "MQTTTxMsgs", "MQTTTxDropped", "MQTTRxMsgs", "MQTTRxDropped", "MQTTPingTimeouts", "MQTTShortSessions", "MQTTLastRxTopic",
    }
    assert status["MQTTState"] == "disabled"
    assert status["MQTTBroker"] is None
    assert status["MQTTLastRxTopic"] is None


def test_the_starters_and_fan_in_follow_the_service_shape() -> None:
    client = _make_client()
    assert client.get_task_starters() == [client.start_asy_connection]
    assert client.get_timer_starters() == []
    assert client.get_error_sources() == [client, client.cfgmgr]
    assert client.name == "MQTT"
    assert client.cfgmgr.name == "CFGMGR_MQTT"


def test_a_long_length_prefix_is_split_across_reads() -> None:
    got: list[bytes] = []

    def consumer(_topic: memoryview, payload: memoryview, _flags: int) -> None:
        got.append(bytes(payload))

    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(consumers=(("ext/#", consumer),), config=_QUIET_CFG)
        try:
            assert await until(client.is_connected)
            packet = publish_packet(b"sensors/t1/ext/p", b"P" * 200)  # a two-byte remaining length
            assert packet[1:3] == encode_length(218)
            await broker.send_split(packet)  # one byte per write: every split point the parser can meet
            assert await until(lambda: got == [b"P" * 200])
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def _sent_on(broker: FakeBroker, n: int) -> "list[tuple[int, bytes]]":
    # What the client sent on the connection of the broker's n-th CONNECT (0-based), that CONNECT excluded.
    return broker.connect_packets[n][1:]


def _flags(broker: FakeBroker, n: int) -> int:
    flags = broker.connects[n]["flags"]
    assert isinstance(flags, int)
    return flags


def _publish_fields(first: int, body: bytes) -> "tuple[bytes, int, bytes]":
    # (topic, packet id or 0, payload) of one PUBLISH the client sent.
    topic, i = read_str(body, 0)
    if (first >> 1) & 3:
        return topic, (body[i] << 8) | body[i + 1], body[i + 2 :]
    return topic, 0, body[i:]


def test_the_status_settings_shape_the_will_and_the_online_and_offline_messages() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client()
        try:
            assert await until(lambda: len(broker.published(b"sensors/t1/status")) == 1)
            await configure(client, broker.port, MQTTWillTopic="home/dev/avail", MQTTOnlineMsg="up", MQTTWillMsg="down", MQTTWillQoS=0, MQTTWillRetain=False)
            client.reconnect()
            assert await until(lambda: len(broker.published(b"home/dev/avail")) == 1)
            assert broker.published(b"sensors/t1/status")[-1] == (0x31, b"offline")  # the old status, as it was set
            connect = broker.connects[1]
            assert connect["flags"] == 0x02 | 0x04  # clean, a will at QoS 0, not retained
            assert connect["will_topic"] == b"home/dev/avail"
            assert connect["will_message"] == b"down"
            assert broker.published(b"home/dev/avail")[0] == (0x30, b"up")  # the will's QoS and retain flag
            await configure(client, broker.port, MQTTPrefix="other")  # an entered topic no longer follows the prefix
            client.reconnect()
            assert await until(lambda: len(broker.published(b"home/dev/avail")) == 3)
            assert broker.published(b"home/dev/avail")[1] == (0x30, b"down")  # the offline message before the DISCONNECT
            assert broker.connects[2]["will_topic"] == b"home/dev/avail"
            assert broker.disconnects == 2
            assert await errnums(client) == []
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_put_refuses_status_settings_outside_their_shape_and_takes_the_rest() -> None:
    async def scenario() -> None:
        client = _make_client()
        await client.setup()
        schema = client.get_cfg_schema()
        bad: tuple[tuple[str, int | str], ...] = (
            ("MQTTWillTopic", "$SYS/x"), ("MQTTWillTopic", "a/#"), ("MQTTWillTopic", "a/+/b"), ("MQTTWillTopic", "x" * 129),
            ("MQTTWillTopic", "ä" * 65), ("MQTTWillMsg", "a\x00b"), ("MQTTWillMsg", "ä" * 33), ("MQTTOnlineMsg", ""),
            ("MQTTOnlineMsg", "x" * 65), ("MQTTWillQoS", 2), ("MQTTWillQoS", -1),
        )
        for key, value in bad:
            assert (await client._set_dict_cfg({key: value}, schema)) == {key: "Invalid"}, (key, value)
        good: dict[str, str | int | bool] = {"MQTTWillTopic": "home/dev/avail", "MQTTWillMsg": "down", "MQTTOnlineMsg": "up", "MQTTWillQoS": 0, "MQTTWillRetain": False, "MQTTPersistent": True}
        results = await client._set_dict_cfg(good, schema)
        assert all(v == "Valid" for v in results.values()), results
        assert (await client._set_dict_cfg({"MQTTWillTopic": ""}, schema)) == {"MQTTWillTopic": "Valid"}  # back to <base>/status

    run(scenario())


def test_a_persistent_session_connects_without_clean_session_and_keeps_its_will() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = _make_client()
        tasks = await start(client)
        try:
            await configure(client, broker.port, MQTTPersistent=True)
            client.reconnect()
            assert await until(client.is_connected)
            connect = broker.connects[0]
            assert connect["flags"] == 0x04 | 0x08 | 0x20  # no clean session; the will as before
            assert connect["session_present"] == 0
            assert broker.sessions == {b"t1"}
            assert await errnums(client) == []
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_resumed_session_gets_its_unacknowledged_qos1_again_first_with_their_ids_and_dup() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.ack_publishes = False
        await broker.start()
        client = _make_client(config=_SESSION_CFG, consumers=_COMMANDS)
        tasks = await start(client)
        try:
            await configure(client, broker.port, MQTTPersistent=True)
            client.reconnect()
            assert await until(client.is_connected)
            assert client.publish("q/1", b"a", qos=1)
            assert client.publish("q/1", b"b", qos=1)
            assert await until(lambda: len(broker.published(b"q/1")) == 2)
            first_ids = [_publish_fields(f, b)[1] for f, b in broker.packets if f & 0xF0 == 0x30 and _publish_fields(f, b)[0] == b"q/1"]
            broker.ack_publishes = True
            await broker.drop()
            assert await until(lambda: len(broker.connects) == 2 and client.is_connected())
            assert broker.connects[1]["session_present"] == 1
            assert await until(lambda: any(f == 0x82 for f, _b in _sent_on(broker, 1)))
            sent = _sent_on(broker, 1)
            # The first session's online message was unacknowledged too: all three again, oldest first, before anything new.
            assert [f & 0x0E for f, _b in sent[:3]] == [0x0A, 0x0A, 0x0A]  # QoS 1 with DUP
            assert [_publish_fields(f, b)[2] for f, b in sent[:3]] == [b"online", b"a", b"b"]
            assert [_publish_fields(f, b)[1] for f, b in sent[1:3]] == first_ids  # their original packet ids
            assert sent[3][0] == 0x82  # then the SUBSCRIBE, a resumed session included
            assert await until(lambda: count(client, "MQTTTxMsgs") >= 4)
            assert count(client, "MQTTTxDropped") == 0
            assert set(await errnums(client)) <= {code("E", "MQTT_LOST")}  # the drop itself, if anything
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_resumed_sessions_resend_past_the_byte_cap_goes_after_the_next_ping_not_a_retry_later() -> None:
    # Six 380 B messages pass the 2,000 B unconfirmed cap: the rest follows the next PINGRESP, not mqtt.qos1_retry_ms (60 s).
    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.ack_publishes = False
        await broker.start()
        client = _make_client(config=_SESSION_CFG)
        tasks = await start(client)
        try:
            await configure(client, broker.port, MQTTPersistent=True)
            client.reconnect()
            assert await until(client.is_connected)
            payloads = [bytes([0x41 + n]) * 380 for n in range(6)]
            for payload in payloads:
                assert client.publish("q/big", payload, qos=1)
            assert await until(lambda: len(broker.published(b"q/big")) == len(payloads))
            broker.ack_publishes = True
            await broker.drop()
            assert await until(lambda: len(broker.connects) == 2 and client.is_connected())

            def resent() -> "list[bytes]":
                return [b for f, b in _sent_on(broker, 1) if f & 0xF0 == 0x30 and _publish_fields(f, b)[0] == b"q/big"]

            assert await until(lambda: len(resent()) == len(payloads), timeout_ms=3000)
            assert [_publish_fields(0x3A, b)[2] for b in resent()] == payloads  # in their original order
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_session_the_broker_lost_gets_its_unacknowledged_qos1_as_new_messages() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.ack_publishes = False
        await broker.start()
        client = _make_client(config=_SESSION_CFG)
        tasks = await start(client)
        try:
            await configure(client, broker.port, MQTTPersistent=True)
            client.reconnect()
            assert await until(client.is_connected)
            assert client.publish("q/1", b"a", qos=1)
            assert await until(lambda: len(broker.published(b"q/1")) == 1)
            old_id = next(_publish_fields(f, b)[1] for f, b in broker.packets if f & 0xF0 == 0x30 and _publish_fields(f, b)[0] == b"q/1")
            broker.sessions.clear()  # as a restarted broker without persistence would have it
            broker.ack_publishes = True
            await broker.drop()
            assert await until(lambda: len(broker.published(b"q/1")) == 2)
            assert broker.connects[1]["session_present"] == 0
            resent = [(f, _publish_fields(f, b)) for f, b in _sent_on(broker, 1) if f & 0xF0 == 0x30 and _publish_fields(f, b)[0] == b"q/1"]
            assert len(resent) == 1
            first, (_topic, pid, payload) = resent[0]
            assert first == 0x32  # QoS 1, no DUP: a new message
            assert payload == b"a"
            assert pid != old_id
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_session_present_on_a_clean_session_is_a_malformed_connack() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        broker.force_session_present = True
        await broker.start()
        client = _make_client()
        tasks = await start(client)
        try:
            await configure(client, broker.port)
            client.reconnect()
            for _ in range(200):
                if code("E", "MQTT_PROTOCOL") in await errnums(client):
                    break
                await asyncio.sleep_ms(20)
            assert code("E", "MQTT_PROTOCOL") in await errnums(client)
            assert not client.is_connected()
            assert broker.packets == [(f, b) for f, b in broker.packets if f == 0x10]  # nothing past the CONNECT
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_new_packet_id_skips_the_ids_still_in_flight() -> None:
    client = _make_client()
    client._pid = 65534
    client._slot_state[0] = _SLOT_INFLIGHT
    client._slot_pid[0] = 65535
    client._slot_state[1] = _SLOT_INFLIGHT
    client._slot_pid[1] = 1
    assert client._next_pid() == 2  # 65535 and 1 are taken; the counter wraps past 0, which is never an id
    assert client._next_pid() == 3


def test_a_changed_client_id_retires_the_old_persistent_session_first() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = _make_client()
        tasks = await start(client)
        try:
            await configure(client, broker.port, MQTTPersistent=True, MQTTUser="u", MQTTPW="p")
            client.reconnect()
            assert await until(client.is_connected)
            assert broker.sessions == {b"t1"}
            await configure(client, broker.port, MQTTClientId="t2")
            client.reconnect()
            assert await until(lambda: len(broker.connects) == 3 and client.is_connected())
            assert _sent_on(broker, 0)[-1] == (0xE0, b"")  # the old connection ended with its own DISCONNECT
            retire = broker.connects[1]
            assert retire["client_id"] == b"t1"
            assert retire["flags"] == 0x02 | 0x80 | 0x40  # clean, no will; the old credentials
            assert _sent_on(broker, 1) == [(0xE0, b"")]  # nothing but the DISCONNECT
            assert broker.connects[2]["client_id"] == b"t2"
            assert _flags(broker, 2) & 0x02 == 0
            assert broker.sessions == {b"t2"}
            assert await errnums(client) == []
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_prefix_change_retires_the_session_even_under_the_same_client_id() -> None:
    # The session would keep the partners' subscriptions under the old base; a clean connect is the only way to drop them.
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = _make_client()
        tasks = await start(client)
        try:
            await configure(client, broker.port, MQTTPersistent=True)
            client.reconnect()
            assert await until(client.is_connected)
            await configure(client, broker.port, MQTTPrefix="home")
            client.reconnect()
            assert await until(lambda: len(broker.connects) == 3 and client.is_connected())
            assert broker.connects[1]["client_id"] == b"t1"
            assert broker.connects[1]["flags"] == 0x02
            assert _flags(broker, 2) & 0x02 == 0
            assert broker.connects[2]["session_present"] == 0  # a fresh session, with only the new filters
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_switching_persistence_off_needs_no_retire_the_clean_connect_discards_it() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = _make_client()
        tasks = await start(client)
        try:
            await configure(client, broker.port, MQTTPersistent=True)
            client.reconnect()
            assert await until(client.is_connected)
            await configure(client, broker.port, MQTTPersistent=False)
            client.reconnect()
            assert await until(lambda: len(broker.connects) == 2 and client.is_connected())
            await asyncio.sleep_ms(300)
            assert len(broker.connects) == 2
            assert _flags(broker, 1) & 0x02
            assert broker.sessions == set()
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_switching_the_client_off_retires_its_persistent_session() -> None:
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = _make_client()
        tasks = await start(client)
        try:
            await configure(client, broker.port, MQTTPersistent=True)
            client.reconnect()
            assert await until(client.is_connected)
            await configure(client, broker.port, MQTTEnable=False)
            client.reconnect()
            assert await until(lambda: len(broker.connects) == 2 and broker.disconnects == 2)
            assert broker.connects[1]["flags"] == 0x02
            await asyncio.sleep_ms(300)
            assert len(broker.connects) == 2
            assert broker.sessions == set()
            assert client.get_link_status()["MQTTState"] == "disabled"
            assert await errnums(client) == []
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_retire_that_fails_logs_one_warning_and_the_client_moves_on() -> None:
    async def scenario() -> None:
        old = FakeBroker(_port())
        new = FakeBroker(_port())
        await old.start()
        await new.start()
        client = _make_client()
        tasks = await start(client)
        try:
            await configure(client, old.port, MQTTPersistent=True)
            client.reconnect()
            assert await until(client.is_connected)
            old.connack_rc = 5  # the old broker now refuses this client
            await configure(client, new.port)
            client.reconnect()
            assert await until(lambda: len(new.connects) == 1 and client.is_connected())
            assert len(old.connects) == 2
            assert old.sessions == {b"t1"}  # left to the broker's expiry
            assert await errnums(client) == [code("W", "MQTT_RETIRE_FAILED")]  # one occurrence, one kind: no error with it
        finally:
            await stop(client, tasks, old)
            await new.stop()

    run(scenario())


def test_a_session_left_by_the_previous_boot_is_retired_too() -> None:
    # The first settings read inherits the session: the keeper retires it before ever connecting with the new identity.
    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        link = [False]
        client = _make_client(link=lambda: link[0])
        await client.setup()
        await configure(client, broker.port, MQTTPersistent=True)  # as the previous boot stored it
        tasks = [client.start_asy_connection()]
        try:
            await asyncio.sleep_ms(100)
            await configure(client, broker.port, MQTTClientId="t2")
            client.reconnect()
            await asyncio.sleep_ms(100)
            link[0] = True
            assert await until(lambda: len(broker.connects) == 2 and client.is_connected())
            assert broker.connects[0]["client_id"] == b"t1"
            assert broker.connects[0]["flags"] == 0x02
            assert broker.connects[1]["client_id"] == b"t2"
        finally:
            await stop(client, tasks, broker)

    run(scenario())


# ---- the partner API: filters and topics below <base>, registered before the tasks start ----


def _subscribed(broker: FakeBroker, n: int) -> "list[list[bytes]]":
    # The filters of each SUBSCRIBE on the broker's n-th connection, in order; none before it exists.
    found: list[list[bytes]] = []
    for first, body in _sent_on(broker, n) if len(broker.connect_packets) > n else []:
        if first == 0x82:
            filters = []
            i = 2
            while i < len(body):
                flt, i = read_str(body, i)
                assert body[i] == 1, body  # QoS 1 asked for every filter
                i += 1
                filters.append(flt)
            found.append(filters)
    return found


def test_without_a_partner_no_subscribe_goes_out() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client()
        try:
            assert await until(lambda: len(broker.published(b"sensors/t1/status")) == 1)
            await asyncio.sleep_ms(100)
            assert _subscribed(broker, 0) == []
            assert client._filters == ()
            assert await errnums(client) == []
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_partners_filters_are_subscribed_below_the_base_at_every_connect() -> None:
    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(consumers=(("link/echo", _ignore), ("cmd/#", _ignore)))
        try:
            assert await until(lambda: len(_subscribed(broker, 0)) == 1)
            assert _subscribed(broker, 0) == [[b"sensors/t1/link/echo", b"sensors/t1/cmd/#"]]  # one SUBSCRIBE, registration order
            await broker.drop()
            assert await until(lambda: len(broker.connects) == 2 and len(_subscribed(broker, 1)) == 1)
            assert _subscribed(broker, 1) == [[b"sensors/t1/link/echo", b"sensors/t1/cmd/#"]]
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_each_message_reaches_every_partner_whose_filter_matches_and_no_other() -> None:
    got: list[tuple[str, bytes, int]] = []

    def on_cmd(topic: memoryview, _payload: memoryview, flags: int) -> None:
        got.append(("cmd", bytes(topic), flags))

    def on_all(topic: memoryview, _payload: memoryview, flags: int) -> None:
        got.append(("all", bytes(topic), flags))

    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(consumers=(("cmd/#", on_cmd), ("#", on_all)), config=_QUIET_CFG)
        try:
            assert await until(lambda: len(_subscribed(broker, 0)) == 1)
            assert _subscribed(broker, 0) == [[b"sensors/t1/cmd/#", b"sensors/t1/#"]]
            await broker.send(publish_packet(b"sensors/t1/cmd/a", b"1"))
            await broker.send(publish_packet(b"sensors/t1/other", b"2", retain=True))
            await broker.send(publish_packet(b"sensors/t2/cmd/a", b"3"))  # another device's tree
            await broker.send(publish_packet(b"cmd/a", b"4"))  # outside every base
            assert await until(lambda: count(client, "MQTTRxMsgs") == 4)
            assert got == [("cmd", b"sensors/t1/cmd/a", 0), ("all", b"sensors/t1/cmd/a", 0), ("all", b"sensors/t1/other", 1)], got
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_partners_topic_is_published_below_the_base_and_follows_a_prefix_change() -> None:
    got: list[bytes] = []

    def on_echo(topic: memoryview, _payload: memoryview, _flags: int) -> None:
        got.append(bytes(topic))

    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = _make_client(consumers=(("link/echo", on_echo),))
        first = client.add_topic("link/echo")
        second = client.add_topic("x/y")
        assert (first, second) == (0, 1)
        tasks = await start(client)
        try:
            await configure(client, broker.port)
            client.reconnect()
            assert await until(client.is_connected)
            assert client.publish_under(second, b"p", qos=1)
            assert await until(lambda: broker.published(b"sensors/t1/x/y") == [(0x32, b"p")])
            await configure(client, broker.port, MQTTPrefix="home")
            client.reconnect()
            assert await until(lambda: len(broker.connects) == 2 and client.is_connected())
            assert client.publish_under(second, "q")
            assert await until(lambda: broker.published(b"home/t1/x/y") == [(0x30, b"q")])
            await broker.send(publish_packet(b"sensors/t1/link/echo", b"old"))  # the old base: no partner's any more
            await broker.send(publish_packet(b"home/t1/link/echo", b"new"))
            assert await until(lambda: count(client, "MQTTRxMsgs") == 2)
            assert got == [b"home/t1/link/echo"], got
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_publish_under_refuses_an_unknown_id_and_a_topic_not_built_yet_and_counts_both() -> None:
    client = _make_client()
    topic_id = client.add_topic("link/echo")
    client._state = _ST_CONNECTED  # connected with no socket and no settings read: the base is not known
    assert client._topics == []
    assert not client.publish_under(topic_id, b"x")
    assert not client.publish_under(topic_id + 1, b"x")
    assert not client.publish_under(-1, b"x")
    assert count(client, "MQTTTxDropped") == 3
    client._base = b"sensors/t1"
    later = client.add_topic("late")  # registered once the base is known: built at once
    assert client._topics == [b"sensors/t1/link/echo", b"sensors/t1/late"]
    assert client.publish_under(later, b"x")
    assert not client.publish_under(later + 1, b"x")
    assert count(client, "MQTTTxDropped") == 4


def test_a_partners_publish_allocates_no_more_than_a_publish_on_the_same_topic() -> None:
    # The topic is built once per settings change, so a round of a partner's publishing allocates nothing of its own.
    client = _make_client()
    topic_id = client.add_topic("link/echo")
    client._base = b"sensors/t1"
    client._build_topics()
    client._state = _ST_CONNECTED  # no keeper runs: each QoS 0 message takes a slot, the oldest giving way
    topic = client._topics[topic_id]
    payload = bytearray(4)

    def relay(topic: bytes, payload: bytearray) -> bool:
        # One Python call deeper, as publish_under() is: build-settrace allocates per call (SPECIFICATION.md E.5.2).
        return client.publish(topic, payload, qos=0, retain=False)

    def direct(n: int) -> int:
        gc.collect()  # the baseline of the measurement (SPECIFICATION.md I.4)
        before = gc.mem_alloc()
        for _ in range(n):
            relay(topic, payload)
        return gc.mem_alloc() - before

    def under(n: int) -> int:
        gc.collect()
        before = gc.mem_alloc()
        for _ in range(n):
            client.publish_under(topic_id, payload)
        return gc.mem_alloc() - before

    direct(1)
    under(1)
    assert under(50) <= direct(50), (under(50), direct(50))


# ---- the hotspot (owner, 2026-11-12: "... inactive when in Hotspot mode - limited available ports!") ----


class _CountingSocket:
    # Shadows asy_mqtt_client's module-global `socket` for one test: every socket() and getaddrinfo() call counted.
    AF_INET = socket.AF_INET
    SOCK_STREAM = socket.SOCK_STREAM

    def __init__(self) -> None:
        self.sockets = 0
        self.lookups = 0

    def getaddrinfo(self, *args: object) -> object:
        self.lookups += 1
        return socket.getaddrinfo(*args)  # type: ignore[arg-type]

    def socket(self, *args: int) -> object:
        self.sockets += 1
        return socket.socket(*args)


def test_in_hotspot_mode_the_client_opens_no_socket_and_asks_for_no_name() -> None:
    # network_available_locked() reads false in hotspot mode: no socket, no DNS or mDNS question and no DNS server read,
    # a session left behind waiting too; the same client connects once the link is back, so the counters do count.
    link = [False]
    asked: list[str] = []
    dns_reads = [0]
    real_resolve = asy_mqtt_client.resolve_ipv4
    counting = _CountingSocket()

    async def resolve(host: str, *_args: object, **_kw: object) -> str:
        asked.append(host)
        return "127.0.0.1"

    def dns_server() -> None:
        dns_reads[0] += 1

    async def scenario() -> None:
        broker = FakeBroker(_port())
        await broker.start()
        client = MQTTClient(asyncio.Lock(), lambda: link[0], dns_server, _CFG, cfg_path=_scratch.dir())
        await client.setup()
        await configure(client, broker.port, MQTTHost="broker.local", MQTTPersistent=True)
        tasks = [client.start_asy_connection()]
        try:
            await asyncio.sleep_ms(100)
            await configure(client, broker.port, MQTTHost="broker.local", MQTTClientId="t2")  # leaves t1's session behind
            client.reconnect()
            await asyncio.sleep_ms(8 * _CFG.link_poll_ms)
            assert (asked, dns_reads[0], counting.sockets, counting.lookups, broker.connections) == ([], 0, 0, 0, 0)
            assert client.get_link_status()["MQTTState"] == "waiting"
            assert await errnums(client) == []
            link[0] = True
            assert await until(lambda: len(broker.connects) == 2 and client.is_connected())
            assert [c["client_id"] for c in broker.connects] == [b"t1", b"t2"]  # the retire, then the new identity
            assert asked == ["broker.local", "broker.local"] and counting.sockets == 2
        finally:
            await stop(client, tasks, broker)

    asy_mqtt_client.resolve_ipv4 = resolve
    asy_mqtt_client.socket = counting  # type: ignore[assignment]
    try:
        run(scenario())
    finally:
        asy_mqtt_client.resolve_ipv4 = real_resolve
        asy_mqtt_client.socket = socket


async def _closed_after(client: MQTTClient) -> int:
    # Milliseconds from the call until the connection's socket is closed, polled at 2 ms; -1 past _WAIT_MS.
    since = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), since) < _WAIT_MS:
        if client._stream is None and not client.is_connected():
            return time.ticks_diff(time.ticks_ms(), since)
        await asyncio.sleep_ms(2)
    return -1


_HOTSPOT_CFG = MqttConfig("t1", 3000, 500, 100, 400, 600, 200, 300, 20, 200, 200, 100)  # a 200 ms link poll, 20 ms ticks
_POLL_SLACK_MS = 40  # the test's own 2 ms polling and a scheduler turn or two


def test_entering_the_hotspot_closes_the_connection_within_a_link_poll_and_a_tick_with_no_entry() -> None:
    link = [True]

    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(link=lambda: link[0], config=_HOTSPOT_CFG)
        try:
            assert await until(client.is_connected)
            await asyncio.sleep_ms(_HOTSPOT_CFG.link_poll_ms // 3)  # off the keeper's poll grid
            link[0] = False
            took = await _closed_after(client)
            assert 0 <= took <= _HOTSPOT_CFG.link_poll_ms + _HOTSPOT_CFG.tick_ms + _POLL_SLACK_MS, took
            assert await until(lambda: broker.closed_by_client == 1)
            status = client.get_link_status()
            assert (status["MQTTState"], status["MQTTLastReason"]) == ("waiting", "link down")
            await asyncio.sleep_ms(4 * _HOTSPOT_CFG.link_poll_ms)
            assert broker.connections == 1  # nothing new while the hotspot runs
            assert await errnums(client) == []
        finally:
            await stop(client, tasks, broker)

    run(scenario())


def test_a_link_lost_under_a_busy_wifi_lock_closes_at_the_first_tick_after_it() -> None:
    # A mode switch holds the WiFi lock: the check waits for it rather than a whole further link poll.
    link = [True]

    async def scenario() -> None:
        broker, client, tasks = await broker_and_client(link=lambda: link[0], config=_HOTSPOT_CFG)
        lock = client.wifi_mode_lock
        try:
            assert await until(client.is_connected)
            await lock.acquire()  # as WifiService holds it across the switch to the hotspot
            link[0] = False
            await asyncio.sleep_ms(_HOTSPOT_CFG.link_poll_ms * 3 // 2)  # a poll falls due while the lock is held
            assert client.is_connected()  # the availability call needs the lock
            lock.release()
            took = await _closed_after(client)
            assert 0 <= took <= _HOTSPOT_CFG.tick_ms + _POLL_SLACK_MS, took
            assert await errnums(client) == []
        finally:
            if lock.locked():
                lock.release()
            await stop(client, tasks, broker)

    run(scenario())


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
