"""PROTOTYPE twin harness: boots a generated device (dev) through digital_twin/run_generic_integration.py and attaches the
prototype MQTT client to its real WifiService. Prints MQTTSTAT/MQTTMEM lines for mqtt_poc/prototype/torture.py.
Usage: micropython run_dev_mqtt_twin.py <run_generic_integration args> -- --broker-port N [--wifi-drop T:K ...] [--hammer T:S:R ...]"""

import asyncio
import gc
import json
import sys
import time

import network
import run_generic_integration as rgi
from asy_mqtt_client import MeasurementPublisher, MqttConfig, MQTTClient


class HarnessArgs:
    def __init__(self) -> None:
        self.broker_host = "127.0.0.1"
        self.broker_port = 1883
        self.duration_s = 60.0
        self.status_ms = 2000
        self.mem_ms = 5000
        self.meas_ms = 5000
        self.wifi_drops: list[tuple[float, int]] = []  # (at_s, failed reconnect attempts before success)
        self.hammers: list[tuple[float, float, int]] = []  # (at_s, for_s, msgs per second)
        self.no_mqtt = False  # baseline: the same twin and samplers without the client


def _parse_own(argv: "list[str]") -> HarnessArgs:
    a = HarnessArgs()
    it = iter(argv)
    for arg in it:
        if arg == "--broker-port":
            a.broker_port = int(next(it))
        elif arg == "--broker-host":
            a.broker_host = next(it)
        elif arg == "--duration":
            a.duration_s = float(next(it))
        elif arg == "--status-ms":
            a.status_ms = int(next(it))
        elif arg == "--mem-ms":
            a.mem_ms = int(next(it))
        elif arg == "--meas-ms":
            a.meas_ms = int(next(it))
        elif arg == "--wifi-drop":
            t, k = next(it).split(":")
            a.wifi_drops.append((float(t), int(k)))
        elif arg == "--no-mqtt":
            a.no_mqtt = True
        elif arg == "--hammer":
            t, d, r = next(it).split(":")
            a.hammers.append((float(t), float(d), int(r)))
        else:
            raise ValueError("unrecognized harness argument: " + arg)
    return a


class Inbound:
    # The PoC's test consumers (owner decision 8.6: values and behaviours, RAM only): echo, values, everything counted.
    def __init__(self, client: MQTTClient) -> None:
        self.client = client
        base = client.cfg.prefix + "/" + client.cfg.client_id
        self.echo_topic = (base + "/echo").encode()
        self.values: dict[str, float] = {}
        self.counts = {"echo": 0, "value": 0, "value_bad": 0, "value_full": 0, "other": 0, "retained": 0}

    def on_echo(self, topic: memoryview, payload: memoryview, retained: bool) -> None:
        self.counts["echo"] += 1
        if not retained:
            self.client.publish(self.echo_topic, payload)

    def on_value(self, topic: memoryview, payload: memoryview, retained: bool) -> None:
        name = bytes(topic[topic_rfind_slash(topic) + 1 :]).decode()
        try:
            v = float(bytes(payload))
        except ValueError:
            self.counts["value_bad"] += 1
            return
        if v != v or v in (float("inf"), float("-inf")):
            self.counts["value_bad"] += 1
            return
        if name not in self.values and len(self.values) >= 8:
            self.counts["value_full"] += 1
            return
        self.values[name] = v
        self.counts["value"] += 1

    def on_any(self, topic: memoryview, payload: memoryview, retained: bool) -> None:
        if retained:
            self.counts["retained"] += 1


def topic_rfind_slash(topic: memoryview) -> int:
    i = len(topic) - 1
    while i >= 0 and topic[i] != 0x2F:
        i -= 1
    return i


async def _status_printer(client: MQTTClient, inbound: Inbound, pub: MeasurementPublisher, period_ms: int) -> None:
    while True:
        await asyncio.sleep_ms(period_ms)
        st = client.get_status()
        st["meas_pub"] = pub.published
        st["meas_err"] = pub.errors
        st["in"] = inbound.counts
        st["values"] = len(inbound.values)
        print("MQTTSTAT", "%.3f" % time.time(), json.dumps(st))


async def _mem_sampler(period_ms: int) -> None:
    # Instrumentation only, as digital_twin/run_generic_integration.py's own sampler: the collect makes samples comparable.
    while True:
        await asyncio.sleep_ms(period_ms)
        gc.collect()
        print("MQTTMEM", "%.3f" % time.time(), gc.mem_alloc(), gc.mem_free())


async def _wifi_drop(module: "object", at_s: float, failures: int) -> None:
    await asyncio.sleep(at_s)
    wlan = module.conn._wlan  # type: ignore[attr-defined]
    print("MQTTEVENT", "%.3f" % time.time(), "wifi_drop failures=%d" % failures)
    wlan.script_connect_outcomes([network.STAT_NO_AP_FOUND] * failures)
    wlan._connected = False
    wlan._status = network.STAT_IDLE
    wlan._ifconfig = ("0.0.0.0", "0.0.0.0", "0.0.0.0", "0.0.0.0")


async def _hammer(client: MQTTClient, at_s: float, for_s: float, rate: int) -> None:
    await asyncio.sleep(at_s)
    print("MQTTEVENT", "%.3f" % time.time(), "hammer start rate=%d for=%.0f" % (rate, for_s))
    topic0 = (client.cfg.prefix + "/" + client.cfg.client_id + "/hammer/q0").encode()
    topic1 = (client.cfg.prefix + "/" + client.cfg.client_id + "/hammer/q1").encode()
    payload = bytearray(b"x" * 100)
    sent = dropped = 0
    period_ms = max(1, 1000 // rate)
    end = time.ticks_add(time.ticks_ms(), int(for_s * 1000))
    i = 0
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        i += 1
        ok = client.publish(topic1 if i % 10 == 0 else topic0, payload, qos=1 if i % 10 == 0 else 0)
        if ok:
            sent += 1
        else:
            dropped += 1
        await asyncio.sleep_ms(period_ms)
    print("MQTTEVENT", "%.3f" % time.time(), "hammer end accepted=%d refused=%d" % (sent, dropped))


async def main(base_argv: "list[str]", own: HarnessArgs) -> None:
    config = rgi.parse_args(base_argv)
    gc.threshold(config.run.gc_threshold)
    twin = asyncio.create_task(rgi.main(config))
    while rgi._booted_module is None:
        await asyncio.sleep_ms(50)
    module = rgi._booted_module
    await rgi._wait_until_built(module)
    if own.no_mqtt:
        print("MQTTEVENT", "%.3f" % time.time(), "baseline run: no MQTT client")
        sampler = asyncio.create_task(_mem_sampler(own.mem_ms))
        try:
            await asyncio.sleep(own.duration_s)
        finally:
            sampler.cancel()
            twin.cancel()
            try:
                await twin
            except BaseException:  # noqa: BLE001 - shutting down
                pass
        return
    conn = module.conn
    cfg = MqttConfig(own.broker_host, own.broker_port, client_id="dev", prefix="sensors")
    client = MQTTClient(cfg, conn.get_wifi_mode_lock(), conn.network_available_locked, conn.get_dns_server_ip)
    inbound = Inbound(client)
    base = cfg.prefix + "/" + cfg.client_id + "/cmd/"
    client.add_handler(base + "echo", inbound.on_echo)
    client.add_handler(base + "value/+", inbound.on_value)
    client.add_handler(base + "#", inbound.on_any)
    sources = tuple(s for s in (getattr(module, n, None) for n in ("scd30", "sgp40", "bmp3xx", "isl29125")) if s is not None)
    pub = MeasurementPublisher(client, sources, own.meas_ms)
    print("MQTTEVENT", "%.3f" % time.time(), "attach broker=%s:%d sources=%d" % (own.broker_host, own.broker_port, len(sources)))
    tasks = [
        asyncio.create_task(client.run()),
        asyncio.create_task(pub.run()),
        asyncio.create_task(_status_printer(client, inbound, pub, own.status_ms)),
        asyncio.create_task(_mem_sampler(own.mem_ms)),
    ]
    tasks.extend(asyncio.create_task(_wifi_drop(module, t, k)) for t, k in own.wifi_drops)
    tasks.extend(asyncio.create_task(_hammer(client, t, d, r)) for t, d, r in own.hammers)
    try:
        await asyncio.sleep(own.duration_s)
    finally:
        print("MQTTFINAL", "%.3f" % time.time(), json.dumps(client.get_status()))
        for t in tasks:
            t.cancel()
        twin.cancel()
        try:
            await twin
        except BaseException:  # noqa: BLE001 - shutting down
            pass


if __name__ == "__main__":
    argv = sys.argv[1:]
    split = argv.index("--") if "--" in argv else len(argv)
    asyncio.run(main(argv[:split], _parse_own(argv[split + 1 :])))
    sys.exit(0)
