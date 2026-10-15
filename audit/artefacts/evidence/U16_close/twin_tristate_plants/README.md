# Twin tier: the FRAM chunk read's tri-state, seen failing first

Six tests in `tests/test_digital_twin_fram.py` pin the chunk read on the real twin chip and bus: a valid read (True,
the bytes), a blank chunk (False, no busy marker), a persistent chip read fault (None, chip untouched), a persistent
bus overrun (None, then False on the leftover BUSY markers, healed by a write), the timestamped chunk's tri-state,
and silence while the chip is lost. Seven planted defects in a scratch copy of `src/asy_fram_manager.py` (never
committed) each fail at least one test (`planted_D*.log`): fault -> False (3 fail), leftover BUSY -> fault (2), blank
takes a marker (1), lost check removed (1), timestamped None -> False (2), valid never True (4), fault re-initialises
block 0 (1). The real code: 30/30 at gc -1 and at 32768 (`real_stage_e.log`, `real_stage_f.log`), no memory markers.
