"""status_load.py READERS SECONDS PATH: GET load on $DUT_IP, prints the status codes."""
import collections, os, sys, threading, time, urllib.request, urllib.error
ip = os.environ["DUT_IP"]; n, dur, path = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
stop = threading.Event(); codes = collections.Counter()
def reader():
    while not stop.is_set():
        try:
            with urllib.request.urlopen(f"http://{ip}{path}", timeout=8) as a: a.read(); codes[a.status] += 1
        except urllib.error.HTTPError as e: codes[e.code] += 1
        except Exception as e: codes[type(e).__name__] += 1
        time.sleep(0.05)
ts = [threading.Thread(target=reader, daemon=True) for _ in range(n)]; [t.start() for t in ts]
time.sleep(dur); stop.set(); [t.join(12) for t in ts]
print("readers", n, "dur", dur, path, dict(codes))
