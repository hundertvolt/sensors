from _uart_comm_harness import Pair, transfer_limits
try:
    Pair(payload_size=16, limits=transfer_limits())
    print("NOT REFUSED")
except AssertionError as e:
    print("refused:", e)
Pair(limits=transfer_limits(payload_size=16))
print("ok")
