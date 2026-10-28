"""Times one scratch flash write's synchronous calls on the real chip - the open, a 1 KiB write, the close and the
removal - each holding the loop for its whole span (SPECIFICATION.md Part F.3's flash stall row). A measurement, never
failed on the figure; the scratch file is removed before and after."""

import errno
import os
import time

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm

# A config_HWTEST_* name: a leftover is scratch the session's standard-state check names and its repair removes;
# relative, so the board's root on silicon, the twin's scratch directory there, never the host's /.
_SCRATCH = "config_HWTEST_stretch.bin"
_SCRATCH_BYTES = 1024


def _remove_leftover() -> None:
    # A run cut short (a reset skips every finally) leaves its file: removed first; ENOENT is the normal case.
    try:
        os.remove(_SCRATCH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


def _main() -> None:
    arm()
    _remove_leftover()
    data = bytes(_SCRATCH_BYTES)
    try:
        # ticks_us() is the RP2040's timer, which counts on with interrupts off, so a span holds across an erase.
        t0 = time.ticks_us()
        f = open(_SCRATCH, "wb")
        t1 = time.ticks_us()
        try:
            f.write(data)
            t2 = time.ticks_us()
        finally:
            f.close()
        t3 = time.ticks_us()
        os.remove(_SCRATCH)
        t4 = time.ticks_us()
    finally:
        _remove_leftover()
    calls = {"open": time.ticks_diff(t1, t0), "write": time.ticks_diff(t2, t1), "close": time.ticks_diff(t3, t2), "remove": time.ticks_diff(t4, t3)}
    fact("flash_calls_us", calls)
    fact("flash_call_max_us", max(calls.values()))
    fact("flash_total_us", sum(calls.values()))
    print("STRETCH flash_call_max_us=" + str(max(calls.values())) + " flash_total_us=" + str(sum(calls.values())))
    done()


_main()
