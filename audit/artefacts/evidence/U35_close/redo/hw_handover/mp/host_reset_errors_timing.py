"""BACKLOG's ResetErrors budget (CPython, on the bench Pi, the final image serving): PUT /status {"ResetErrors": true}
timed REPEAT times beside 0-4 concurrent GET /status readers. ResetErrors wipes every FRAM-backed log for good, so it
asks first and runs only after errcount and the raw FRAM are saved (CLAUDE.md). Usage: python3 ... <board IP>."""

import http.client
import json
import sys
import threading
import time

READERS, REPEAT, TIMEOUT_S = (0, 1, 2, 3, 4), 3, 30.0


def request(ip: str, method: str, body: "dict | None" = None) -> "tuple[int, dict]":
    c = http.client.HTTPConnection(ip, 80, timeout=TIMEOUT_S)
    try:
        c.request(method, "/status", json.dumps(body) if body is not None else None, {"Content-Type": "application/json"})
        r = c.getresponse()
        return r.status, json.loads(r.read() or b"{}")
    finally:
        c.close()


def reader(ip: str, stop: threading.Event, count: list) -> None:
    while not stop.is_set():
        try:
            request(ip, "GET")
            count[0] += 1
        except (OSError, ValueError):
            count[1] += 1


def sweep(ip: str, n: int) -> str:
    stop, counts = threading.Event(), [[0, 0] for _ in range(n)]
    threads = [threading.Thread(target=reader, args=(ip, stop, counts[i])) for i in range(n)]
    for t in threads:
        t.start()
    time.sleep(1.0)
    t0 = time.monotonic()
    try:
        status, answer = request(ip, "PUT", {"ResetErrors": True})
        word = answer.get("result", {}).get("ResetErrors")
    except (OSError, ValueError) as e:
        status, word = -1, repr(e)
    elapsed = time.monotonic() - t0
    stop.set()
    for t in threads:
        t.join(TIMEOUT_S)
    return "readers=%d elapsed_s=%.2f status=%d result=%s gets=%d get_failures=%d" % (n, elapsed, status, word, sum(c[0] for c in counts), sum(c[1] for c in counts))


def main(ip: str) -> None:
    if input("errcount and the raw FRAM saved, and every FRAM log may be wiped %d times? Type 'wipe': " % (len(READERS) * REPEAT)) != "wipe":
        print("SUM reset_errors refused")
        return
    for n in READERS:
        for _ in range(REPEAT):
            print("SUM reset_errors " + sweep(ip, n))


if __name__ == "__main__":
    main(sys.argv[1])
