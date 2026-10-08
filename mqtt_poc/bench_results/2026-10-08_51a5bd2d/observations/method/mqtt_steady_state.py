"""Ad-hoc bench observation (2026-10-08): the MQTT client's real steady-state effects on the dev board.

Phases: MQTT off (baseline REST latency), on at the default 60 s interval, on at the 10 s minimum, then off.
Records every message the board publishes, REST latency per phase, the client's counters, the console
(passively) and the FRAM logs. Writes networking/mqtt only: enable, interval change, disable.
"""

import json
import statistics
import sys
import threading
import time
from pathlib import Path

REPO = Path("/home/nico/programming/sensors")
sys.path.insert(0, str(REPO / "tests_hardware"))
import http_client  # noqa: E402
from harness import Board  # noqa: E402
from mqtt_probe import Mosquitto, Probe  # noqa: E402

DUT = "192.168.85.57"
HOST = "192.168.85.75"
PORT = 18883
OUT = Path(sys.argv[1])
BASELINE_S, DEFAULT_S, FAST_S, TAIL_AFTER_OFF_S = 120, 600, 300, 30
REST_EVERY_S = 5.0
OUT.mkdir(parents=True, exist_ok=True)
t0 = time.monotonic()
log: dict = {"phases": {}, "messages": [], "counters": {}, "notes": []}


def now() -> float:
    return round(time.monotonic() - t0, 3)


def get(path: str) -> dict:
    res = http_client.fetch(DUT, 80, "GET", path, timeout_s=10.0)
    assert res.status_code == 200, (path, res.status_code)
    return res.json()


def put(body: dict) -> dict:
    res = http_client.fetch(DUT, 80, "PUT", "/networking", body, timeout_s=10.0)
    assert res.status_code == 200, (body, res.status_code, res.body)
    return res.json().get("result", {})


def mqtt_fields() -> dict:
    return {k: v for k, v in get("/status")["networking"].items() if k.startswith("MQTT")}


def sample_rest(phase: str, seconds: float) -> None:
    lat, failures = [], 0
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        start = time.monotonic()
        try:
            get("/status")
            lat.append(time.monotonic() - start)
        except Exception as e:  # noqa: BLE001 - an observation, recorded and counted
            failures += 1
            log["notes"].append(f"{now()} {phase}: GET /status failed: {e!r}")
        time.sleep(max(0.0, REST_EVERY_S - (time.monotonic() - start)))
    log["phases"][phase] = {
        "seconds": seconds, "samples": len(lat), "failures": failures,
        "median_s": round(statistics.median(lat), 3) if lat else None,
        "p90_s": round(sorted(lat)[int(0.9 * (len(lat) - 1))], 3) if lat else None,
        "max_s": round(max(lat), 3) if lat else None,
        "at": now(),
    }


board = Board()
console: list[str] = []
total_s = BASELINE_S + DEFAULT_S + FAST_S + TAIL_AFTER_OFF_S + 120


def _tail() -> None:
    # Passive, timestamped (seconds since t0): the twin needs the timing of each console line, not only the text.
    import serial  # noqa: PLC0415 - pyserial, as harness.tail_log uses
    end = time.monotonic() + total_s
    with serial.Serial(board.device, 115200, timeout=0.5) as port:
        while time.monotonic() < end:
            raw = port.readline()
            if raw:
                console.append(f"{now():.3f} " + raw.decode("utf-8", "replace").rstrip("\r\n"))


tailer = threading.Thread(target=_tail, daemon=True)
broker = Mosquitto(OUT / "broker", PORT, bind=HOST)
observer = None
try:
    cfg = get("/networking")
    base = f"{cfg['MQTTPrefix']}/{cfg['MQTTClientId']}"
    log["config_before"] = {k: v for k, v in cfg.items() if k.startswith("MQTT") and k != "MQTTPW"}
    tailer.start()
    broker.start()
    observer = Probe(HOST, PORT, "bench-steady-observer", (f"{base}/#",)).start()
    assert observer.wait_connected(), "observer could not connect"
    log["counters"]["before"] = mqtt_fields()

    sample_rest("off_baseline", BASELINE_S)

    log["put_enable"] = put({"MQTTEnable": True, "MQTTHost": HOST, "MQTTPort": PORT, "MQTTPubInterval": 60})
    t_enable = time.monotonic()
    while time.monotonic() - t_enable < 60 and mqtt_fields().get("MQTTConnected") is not True:
        time.sleep(0.5)
    log["connect_after_enable_s"] = round(time.monotonic() - t_enable, 2)
    log["counters"]["after_connect"] = mqtt_fields()
    sample_rest("on_interval_60s", DEFAULT_S)
    log["counters"]["after_60s_phase"] = mqtt_fields()

    log["put_fast"] = put({"MQTTPubInterval": 10})
    sample_rest("on_interval_10s", FAST_S)
    log["counters"]["after_10s_phase"] = mqtt_fields()

    log["put_disable"] = put({"MQTTEnable": False, "MQTTPubInterval": 60})
    sample_rest("off_after", TAIL_AFTER_OFF_S)
    log["counters"]["after_disable"] = mqtt_fields()
finally:
    try:
        put({"MQTTEnable": False, "MQTTPubInterval": 60})
    except Exception as e:  # noqa: BLE001
        log["notes"].append(f"final disable failed: {e!r}")
    if observer is not None:
        for m in observer.received():
            log["messages"].append({"t": round(m.at - t0, 3), "topic": m.topic, "len": len(m.payload), "retained": m.retained, "payload": m.payload.decode("utf-8", "replace")})
        observer.close()
    broker.stop()
    tailer.join(timeout=total_s + 30)
    (OUT / "console.txt").write_text("\n".join(console))
    try:
        log["errcount"] = get("/status")["errcount"]
    except Exception as e:  # noqa: BLE001
        log["notes"].append(f"errcount read failed: {e!r}")
    (OUT / "observation.json").write_text(json.dumps(log, indent=1))
    print("done", now())
