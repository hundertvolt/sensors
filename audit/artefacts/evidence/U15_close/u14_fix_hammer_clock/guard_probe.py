# Runs the planted-stall guards of whichever tests/test_uart_comm_hazard.py is first on MICROPYPATH, for each
# stall position given, and prints one verdict per (guard, crc, position).
# Usage: micropython -X heapsize=16M guard_probe.py <substr|all> <k_list> [stall_ms]
import sys

import test_uart_comm_hazard as T

WHICH, KS = sys.argv[1], [int(x) for x in sys.argv[2].split(",")]
if len(sys.argv) > 3:
    T._PLANTED_STALL_MS = int(sys.argv[3])
names = sorted(n for n in T.__dict__ if n.startswith("test_a_host_stall_cannot_fail") and (WHICH == "all" or WHICH in n))
for k in KS:
    T._PLANTED_STALL_AFTER = k
    for name in names:
        try:
            getattr(T, name)()
            verdict = "pass"
        except Exception as e:  # noqa: BLE001
            verdict = "FAIL %s: %s" % (type(e).__name__, e)
        print("%s k=%d D=%d %s: %s" % ("ok  " if verdict == "pass" else "FLIP", k, T._PLANTED_STALL_MS, name, verdict))
sys.exit(0)
