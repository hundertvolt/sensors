"""Isolated-driver device script: the clamped read path must never hold the CPU for a frame still
arriving on the wire (SPECIFICATION.md Part F.5.8). Measures the real C calls, since the stall is a
timing property of the peripheral that no fake reproduces and no code review makes visible."""
# Raw machine.UART on purpose: this pins the behaviour the driver's clamp exists to avoid, so it
# stays true independently of how asy_uart_driver is arranged internally.

import select
import time

from machine import UART, Pin

BAUDRATE = 115200
FRAME = 53  # one whole framed frame at the bench's payload_size=48
TRIALS = 5
# The unclamped read holds the CPU for the frame's remaining wire time (~4.4ms measured); a clamped
# one only copies what already arrived. A third of the wire time is far above the ~280us measured
# worst case and far below the ~4.4ms failure, so it separates the two without being brittle.
_WIRE_US = FRAME * 10 * 1000000 // BAUDRATE
_CLAMPED_MAX_US = _WIRE_US // 3


def _drain(uart: "UART") -> None:
    while uart.any():
        uart.read()


def main() -> None:
    u0 = UART(0, baudrate=BAUDRATE, tx=Pin(0), rx=Pin(1), rxbuf=512, txbuf=512, timeout=0, timeout_char=1)
    u1 = UART(1, baudrate=BAUDRATE, tx=Pin(8), rx=Pin(9), rxbuf=512, txbuf=512, timeout=0, timeout_char=1)
    poller = select.poll()
    poller.register(u1, select.POLLIN)
    buf = bytearray(FRAME)
    frame = bytes(range(FRAME))
    failures = []
    unclamped_worst = 0
    clamped_worst = 0
    ready_bytes_seen = []

    for _ in range(TRIALS):
        _drain(u1)
        u0.write(frame)
        while not any(ev & select.POLLIN for _, ev in poller.ipoll(0)):
            pass
        ready_bytes_seen.append(u1.any())
        t0 = time.ticks_us()
        u1.readinto(buf, FRAME)  # asks for the whole frame: the pre-fix shape
        unclamped_worst = max(unclamped_worst, time.ticks_diff(time.ticks_us(), t0))
        time.sleep_ms(30)

        _drain(u1)
        u0.write(frame)
        got = 0
        while got < FRAME:
            if not any(ev & select.POLLIN for _, ev in poller.ipoll(0)):
                continue
            want = min(FRAME - got, u1.any())
            if not want:
                continue
            t0 = time.ticks_us()
            read = u1.readinto(memoryview(buf)[got:], want)  # asks only for what arrived
            clamped_worst = max(clamped_worst, time.ticks_diff(time.ticks_us(), t0))
            got += read or 0
        time.sleep_ms(30)

    u0.deinit()
    u1.deinit()

    # POLLIN firing on a nearly empty buffer is the precondition for the whole finding: if the
    # peripheral only reported readiness once a frame had landed, no clamp would be needed.
    if max(ready_bytes_seen) >= FRAME:
        failures.append(f"POLLIN only fired with {max(ready_bytes_seen)} bytes buffered - this board does not show the hazard")
    if unclamped_worst < _CLAMPED_MAX_US:
        failures.append(f"an unclamped read cost only {unclamped_worst}us - the measurement is not exercising the stall")
    if clamped_worst > _CLAMPED_MAX_US:
        failures.append(f"a clamped read held the CPU for {clamped_worst}us, over the {_CLAMPED_MAX_US}us bound")

    if failures:
        print("RESULT: FAIL " + "; ".join(failures))
    else:
        print(
            f"RESULT: PASS clamped read worst {clamped_worst}us vs unclamped {unclamped_worst}us "
            f"(frame wire time {_WIRE_US}us, POLLIN fired at {min(ready_bytes_seen)}-{max(ready_bytes_seen)} bytes)",
        )


main()
