"""Isolated-driver device script: constructs real machine.Timer objects until Timer.init() raises OSError(ENOMEM)
once the RP2040's hardware alarm pool is exhausted, confirming SPECIFICATION.md Part F.1 against real silicon;
`constructed` is the free alarms at that moment, not the pool size. Reports facts; the host gives the verdict."""

import machine

# @include _shared/facts.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact

timers = []
raised = None
try:
    for _ in range(64):  # an upper bound only: the pool holds 16 alarms (pico-sdk pico/time.h), fewer are free
        t = machine.Timer()
        t.init(period=60_000, callback=lambda _t: None)  # 60 s: never expected to fire during this script
        timers.append(t)
except OSError as exc:
    raised = exc.args[0] if exc.args else None
finally:
    fact("constructed", len(timers))
    for t in timers:
        t.deinit()
fact("raised", raised is not None)
fact("errno", raised)
done()
