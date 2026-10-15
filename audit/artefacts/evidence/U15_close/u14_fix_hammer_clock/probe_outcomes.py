# Records each GET's result and the initiator's/responder's errnos across one faulted-hammer body (no stall).
# Usage: micropython -X heapsize=16M probe_outcomes.py <nocrc|crc16> <gc_threshold>
import gc
import sys

import test_uart_comm_hazard as T
from asy_crc_checks import CRC16
from asy_uart_comm import UARTComm

CRC = None if sys.argv[1] == "nocrc" else CRC16
gc.threshold(int(sys.argv[2]))
results = bytearray(400)
n = [0]
real_get = UARTComm.uart_get


async def get(self, *a, **k):  # noqa: ANN001,ANN002,ANN003,ANN202
    r = await real_get(self, *a, **k)
    results[n[0]] = 0 if r is None else 1
    n[0] += 1
    return r


UARTComm.uart_get = get
pairs = []
real_hp = T.hazard_pair


def hp(*a, **k):  # noqa: ANN002,ANN003,ANN202
    p = real_hp(*a, **k)
    pairs.append(p)
    return p


T.hazard_pair = hp
T._hammer_faulted(CRC)
print("gets=%d outcomes (1=ok):" % n[0], list(results[:n[0]]))
print("failures burst1=%d burst2=%d" % (list(results[:30]).count(0), list(results[30:60]).count(0)))
print("initiator errnos:", T.errnos(pairs[0].initiator))
print("responder errnos:", T.errnos(pairs[0].responder))
