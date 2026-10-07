"""PROTOTYPE host driver for the MQTT PoC twin try: real mosquitto on a free port, the dev twin with the prototype client,
broker- and network-side faults on a timeline (kill, stall, blackhole, takeover, floods), then a recovery/heap summary.
Run as root from the repo root: python3 mqtt_poc/prototype/torture.py --gc-threshold -1 --out <dir>."""

import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MICROPYPATH = "mqtt_poc/prototype:build/generated_src:src:digital_twin:ext:frozen_modules:.frozen"
MEMORY_MARKERS = ("MemoryError", "memory allocation failed")
BASE = "sensors/dev"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Broker:
    def __init__(self, port: int, out: Path) -> None:
        self.port = port
        self.conf = out / "mosquitto.conf"
        self.conf.write_text(f"listener {port} 127.0.0.1\nallow_anonymous true\npersistence false\nconnection_messages true\nlog_type error\nlog_type warning\nlog_type notice\nlog_type information\n")
        self.log = open(out / "mosquitto.log", "a")  # noqa: SIM115 - lives as long as the broker
        self.proc: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        self.proc = subprocess.Popen(["mosquitto", "-c", str(self.conf)], stdout=self.log, stderr=subprocess.STDOUT)
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", self.port), 0.2).close()
                return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("mosquitto did not start")

    def signal(self, sig: int) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.send_signal(sig)

    def stop(self, sig: int = signal.SIGTERM) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.send_signal(sig)
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.proc = None


class Observer:
    # mosquitto_sub on sensors/#, restarted whenever it exits (it does on broker loss).
    def __init__(self, port: int, out: Path) -> None:
        self.port = port
        self.path = out / "observer.log"
        self.stop_flag = False
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self) -> None:
        with open(self.path, "a") as f:
            while not self.stop_flag:
                p = subprocess.Popen(["mosquitto_sub", "-h", "127.0.0.1", "-p", str(self.port), "-t", "sensors/#", "-q", "1", "-i", "observer", "-F", "%U %r %t %l %p"], stdout=f, stderr=subprocess.DEVNULL)
                while p.poll() is None and not self.stop_flag:
                    time.sleep(0.2)
                if p.poll() is None:
                    p.terminate()
                    p.wait()
                time.sleep(0.5)


def pub(port: int, topic: str, lines: "list[str] | None" = None, message: "str | None" = None, qos: int = 0, retain: bool = False) -> None:
    cmd = ["mosquitto_pub", "-h", "127.0.0.1", "-p", str(port), "-t", topic, "-q", str(qos)]
    if retain:
        cmd.append("-r")
    if lines is not None:
        subprocess.run([*cmd, "-l"], input="\n".join(lines) + "\n", text=True, timeout=60, check=False, capture_output=True)
    else:
        subprocess.run([*cmd, "-m", message or ""], timeout=20, check=False, capture_output=True)


def blackhole(port: int, on: bool) -> None:
    op = "-I" if on else "-D"
    for spec in (["--dport", str(port)], ["--sport", str(port)]):
        subprocess.run(["iptables", op, "INPUT", "-i", "lo", "-p", "tcp", *spec, "-j", "DROP"], check=False, capture_output=True)


class Timeline:
    def __init__(self, t0: float, out: Path) -> None:
        self.t0 = t0
        self.log = open(out / "events.log", "a")  # noqa: SIM115

    def at(self, t: float) -> None:
        delay = self.t0 + t - time.time()
        if delay > 0:
            time.sleep(delay)

    def mark(self, what: str) -> None:
        line = f"{time.time():.3f} +{time.time() - self.t0:6.1f}s {what}"
        print(line, flush=True)
        self.log.write(line + "\n")
        self.log.flush()


def scenario(tl: Timeline, broker: Broker, port: int) -> None:
    tl.at(25)
    tl.mark("inbound burst: 200 QoS0 echo, 100 QoS1 values, 5 oversize, 6 bad values, 100 retained")
    pub(port, f"{BASE}/cmd/echo", lines=[f"e{i}" for i in range(200)])
    pub(port, f"{BASE}/cmd/value/temp", lines=[f"{20 + i / 10:.1f}" for i in range(100)], qos=1)
    for _ in range(5):
        pub(port, f"{BASE}/cmd/big", message="B" * 5000, qos=1)
    for bad in ("nan", "abc", "1e999", "", "inf", "-inf"):
        pub(port, f"{BASE}/cmd/value/bad", message=bad, qos=1)
    for i in range(20):
        pub(port, f"{BASE}/cmd/value/v{i}", message=str(i), qos=1)
    for i in range(100):
        pub(port, f"{BASE}/cmd/r/{i}", message=f"retained-{i}", retain=True)

    tl.at(55)
    tl.mark("broker SIGKILL")
    broker.stop(signal.SIGKILL)
    tl.at(80)
    tl.mark("broker restart")
    broker.start()

    tl.at(110)
    tl.mark("broker SIGSTOP (stall, connections stay open)")
    broker.signal(signal.SIGSTOP)
    tl.at(150)
    tl.mark("broker SIGCONT")
    broker.signal(signal.SIGCONT)

    tl.at(180)
    tl.mark("iptables blackhole on the broker port (silent path loss)")
    blackhole(port, on=True)
    tl.at(220)
    tl.mark("blackhole removed")
    blackhole(port, on=False)

    tl.at(250)
    tl.mark("client-id takeover: a second client connects as 'dev' for 15 s")
    thief = subprocess.Popen(["mosquitto_sub", "-h", "127.0.0.1", "-p", str(port), "-i", "dev", "-t", "x/y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tl.at(265)
    thief.terminate()
    thief.wait()
    tl.mark("takeover client gone")

    tl.at(290)
    tl.mark("(twin side) outbound hammer 200 msg/s for 30 s - scheduled in the harness")
    tl.at(330)
    tl.mark("(twin side) WiFi drop with 2 failed reconnects - scheduled in the harness")

    tl.at(430)
    tl.mark("sustained inbound flood: echo QoS0 as fast as mosquitto_pub sends, 20000 messages")
    pub(port, f"{BASE}/cmd/echo", lines=[f"f{i}" for i in range(20000)])
    tl.mark("flood sent")

    tl.at(470)
    tl.mark("broker graceful restart (SIGTERM)")
    broker.stop(signal.SIGTERM)
    broker.start()

    tl.at(510)
    tl.mark("broker SIGKILL, left down for 70 s (backoff to its cap)")
    broker.stop(signal.SIGKILL)
    tl.at(580)
    tl.mark("broker restart")
    broker.start()


def analyse(out: Path, events_t0: float) -> "dict[str, object]":
    twin = (out / "twin.log").read_text(errors="replace")
    stats = [(float(m.group(1)), json.loads(m.group(2))) for m in re.finditer(r"^MQTTSTAT (\S+) (.*)$", twin, re.M)]
    mem = [(float(m.group(1)), int(m.group(2)), int(m.group(3))) for m in re.finditer(r"^MQTTMEM (\S+) (\d+) (\d+)$", twin, re.M)]
    final = re.search(r"^MQTTFINAL \S+ (.*)$", twin, re.M)
    markers = {m: twin.count(m) for m in MEMORY_MARKERS}
    tracebacks = twin.count("Traceback")
    connect_times = []
    prev = None
    for t, s in stats:
        if prev is not None and s["connects"] > prev:
            connect_times.append(round(t - events_t0, 1))
        prev = s["connects"]
    obs = (out / "observer.log").read_text(errors="replace").splitlines() if (out / "observer.log").exists() else []
    status_msgs = [(round(float(line.split()[0]) - events_t0, 1), line.split(" ", 4)[-1]) for line in obs if f" {BASE}/status " in line]
    topics: dict[str, int] = {}
    for line in obs:
        parts = line.split(" ", 4)
        if len(parts) >= 3:
            key = parts[2]
            key = re.sub(r"/r/\d+$", "/r/<i>", key)
            key = re.sub(r"/value/v\d+$", "/value/v<i>", key)
            topics[key] = topics.get(key, 0) + 1
    alloc = [a for _, a, _ in mem]
    return {
        "memory_markers": markers,
        "tracebacks": tracebacks,
        "final": json.loads(final.group(1)) if final else None,
        "connects_at_s": connect_times,
        "status_topic_seen": status_msgs,
        "observer_topic_counts": topics,
        "heap_alloc_after_collect": {"samples": len(alloc), "first": alloc[:3], "min": min(alloc, default=None), "max": max(alloc, default=None), "last": alloc[-3:]},
        "heap_series": [(round(t - events_t0, 1), a, f) for t, a, f in mem],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gc-threshold", default="-1")
    ap.add_argument("--heapsize", default="")
    ap.add_argument("--duration", type=float, default=640.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--micropython", default=str(Path.home() / "pico-toolchain/micropython/ports/unix/build-standard/micropython"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    port = free_port()
    blackhole(port, on=False)
    broker = Broker(port, out)
    broker.start()
    observer = Observer(port, out)
    observer.thread.start()
    cmd = [args.micropython]
    if args.heapsize:
        cmd += ["-X", f"heapsize={args.heapsize}"]
    cmd += [
        "mqtt_poc/prototype/run_dev_mqtt_twin.py", "--module", "sensortask_dev", "--wiring-plan", "build/generated_src/sensortask_dev_wiring_plan.json",
        "--device", "dev", "--host", "127.0.0.1", "--port", str(free_port()), "--fram-state-path", "", "--scd30-state-path", "", "--gc-threshold", args.gc_threshold,
        "--", "--broker-port", str(port), "--duration", str(args.duration), "--hammer", "290:30:200", "--wifi-drop", "330:2",
    ]
    env = dict(os.environ, MICROPYPATH=MICROPYPATH, TZ="UTC")
    t0 = time.time()
    with open(out / "twin.log", "w") as tw:
        twin = subprocess.Popen(cmd, cwd=REPO, env=env, stdout=tw, stderr=subprocess.STDOUT)  # noqa: S603 - fixed argv
        tl = Timeline(t0, out)
        tl.mark(f"start broker_port={port} gc_threshold={args.gc_threshold} heapsize={args.heapsize or 'default'}")
        try:
            scenario(tl, broker, port)
            twin.wait(timeout=args.duration + 60)
        except subprocess.TimeoutExpired:
            tl.mark("twin did not exit in time - SIGINT")
            twin.send_signal(signal.SIGINT)
            twin.wait(30)
        finally:
            blackhole(port, on=False)
            broker.signal(signal.SIGCONT)
            observer.stop_flag = True
            broker.stop()
            if twin.poll() is None:
                twin.kill()
    tl.mark(f"twin exit code {twin.returncode}")
    summary = analyse(out, t0)
    summary["twin_exit"] = twin.returncode
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    printable = {k: v for k, v in summary.items() if k != "heap_series"}
    print(json.dumps(printable, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
