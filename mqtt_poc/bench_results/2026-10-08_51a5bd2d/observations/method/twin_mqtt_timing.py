"""Ad-hoc, host only (2026-10-08): the dev twin's MQTT client timed the way the bench timed the board, so the two
can be set side by side: connect, rounds and their interval, an interval change, a broker kill, a stall, disable."""

import json
import signal
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

REPO = Path("/home/nico/programming/sensors")
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests_hardware"))
import _digital_twin_ci_suite as suite  # noqa: E402
from mqtt_probe import Mosquitto, Probe, free_tcp_port, wait_for  # noqa: E402

OUT = Path(sys.argv[1])
GC = int(sys.argv[2]) if len(sys.argv) > 2 else 32768
POLL_S = 0.25
OUT.mkdir(parents=True, exist_ok=True)
t0 = time.monotonic()
res: dict = {"gc_threshold": GC, "poll_s": POLL_S, "notes": []}


def now() -> float:
    return round(time.monotonic() - t0, 3)


def st() -> dict:
    return suite._mqtt_status()


def timed(pred, limit: float) -> float | None:
    start = time.monotonic()
    ok = wait_for(pred, limit, POLL_S)
    return round(time.monotonic() - start, 2) if ok else None


module = "sensortask_dev"
plan_path = suite.GENERATED_SRC_DIR / f"{module}_wiring_plan.json"
ctx = suite.RunContext(
    micropython_bin=str(Path.home() / "pico-toolchain/micropython/ports/unix/build-standard/micropython"),
    logs_dir=OUT, device="dev", module=module, wiring_plan_path=plan_path,
    drivers=suite._drivers_in_plan(json.loads(plan_path.read_text())), gc_threshold=GC, mqtt=True,
)
suite._clean_state()
broker = Mosquitto(OUT / "broker", free_tcp_port(suite.HOST), bind=suite.HOST)
broker.start()
proc = suite._spawn(ctx, [], OUT / "twin.log")
observer = None
try:
    suite._wait_until_serving(proc, 60.0)
    observer = Probe(suite.HOST, broker.port, "twin-timing-observer", ("sensors/#",)).start()
    assert observer.wait_connected()
    body = {"SSID": "digital-twin-test-ssid", "MQTTEnable": True, "MQTTHost": suite.HOST, "MQTTPort": broker.port, "MQTTPubInterval": 10}
    t_put = now()
    res["put_enable"] = suite._http("PUT", "/networking", body)[1]
    res["connect_after_enable_s"] = timed(lambda: st().get("MQTTConnected") is True, 90)
    res["t_put_enable"] = t_put
    time.sleep(65)  # six or so rounds at 10 s
    t_fast = now()
    res["put_interval_20"] = suite._http("PUT", "/networking", {"MQTTPubInterval": 20})[1]
    res["t_put_interval_20"] = t_fast
    time.sleep(70)
    res["kills"] = []
    for _ in range(2):
        assert timed(lambda: st().get("MQTTConnected") is True, 120) is not None
        connects = st().get("MQTTConnects", -1)
        broker.stop(signal.SIGKILL)
        time.sleep(5.0)
        broker.start()
        res["kills"].append(timed(lambda c=connects: st().get("MQTTConnects", -1) > c and st().get("MQTTConnected") is True, 150))
        observer.wait_connected()
    res["stalls"] = []
    for _ in range(3):
        assert timed(lambda: st().get("MQTTConnected") is True, 150) is not None
        time.sleep(3.0)
        pings = st().get("MQTTPingTimeouts", -1)
        broker.send(signal.SIGSTOP)
        try:
            took = timed(lambda p=pings: st().get("MQTTPingTimeouts", -1) > p, 60)
        finally:
            broker.send(signal.SIGCONT)
        back = timed(lambda: st().get("MQTTConnected") is True, 150)
        res["stalls"].append({"detected_s": took, "reconnected_after_resume_s": back})
    t_off = now()
    res["put_disable"] = suite._http("PUT", "/networking", {"MQTTEnable": False})[1]
    res["t_put_disable"] = t_off
    time.sleep(5)
    lat = []
    for _ in range(20):
        s = time.monotonic()
        suite._http("GET", "/status")
        lat.append(time.monotonic() - s)
    res["rest_status_median_s_off"] = round(statistics.median(lat), 3)
    res["counters_end"] = {k: v for k, v in st().items() if k.startswith("MQTT")}
    res["errcount_mqtt"] = suite._errcount_required("MQTT")
finally:
    if observer is not None:
        res["messages"] = [{"t": round(m.at - t0, 3), "topic": m.topic, "len": len(m.payload), "retained": m.retained, "payload": m.payload.decode("utf-8", "replace")[:300]} for m in observer.received()]
        res["observer_connects"] = observer.connects
        observer.close()
    res["twin_exit"] = suite._shutdown(proc, "twin timing")
    broker.stop()
    (OUT / "twin_timing.json").write_text(json.dumps(res, indent=1))
    print("done", now())
