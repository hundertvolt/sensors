# lane C scratch: plant one D ms interpreter stall after the k-th UART-module sleep in each named test,
# on the poll-round clock (mode "clock") or on the wall clock (mode "wall", the control).
import sys
import time

import asy_uart_comm
import asy_uart_driver
import asyncio

mode, D, names = sys.argv[2], int(sys.argv[3]), sys.argv[4].split(",")
ks = [int(k) for k in sys.argv[5].split(",")]
src = open(sys.argv[1]).read().replace('if __name__ == "__main__":', 'if False:')
g = {"__name__": "x"}
exec(src, g)
Base = g["PollRoundClock"]


def make(k):
    class Stalling(Base):
        def __init__(self, stall_after=0, stall_ms=0):
            super().__init__(stall_after=k, stall_ms=D)

        def __enter__(self):
            r = super().__enter__()
            self.arm()
            if mode == "wall":  # keep the stall, drop the virtual time: the modules read the real clock
                asy_uart_comm.time = asy_uart_driver.time = time
            return r

    return Stalling


fails = {}
for name in names:
    for k in ks:
        g["PollRoundClock"] = make(k)
        print("RUN", name, k)
        try:
            g[name]()
        except Exception as e:  # noqa: BLE001
            fails.setdefault(name, []).append(k)
            print("FLIP", name, k, repr(e)[:120])
print("MODE", mode, "D", D, "fails", fails)
