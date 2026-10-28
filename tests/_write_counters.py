"""Write counters kept outside the product: WriteCountingOpen counts a module's flash-filesystem opens,
scd30_nvm_writes() counts the SCD30 NVM-writing frames a fake I2C bus logged. Runs under the MicroPython
Unix port; a planted extra write shows in either count (tests/test_write_counters.py)."""

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from machine import I2C

_real_open = open
_ABSENT = object()
_OPEN = "open"  # the module global WriteCountingOpen shadows

# SCD30 commands that write its non-volatile memory (Interface Description v1.0): 0x0010 continuous measurement
# with ambient pressure (1.4.1), 0x4600 interval (1.4.3), 0x5306 ASC and 0x5204 FRC's calibration curve (1.4.6),
# 0x5403 temperature offset (1.4.7), 0x5102 altitude (1.4.8).
_NVM_ARG_WORDS = (0x0010, 0x4600, 0x5306, 0x5204, 0x5403, 0x5102)
_NVM_STOP_WORD = 0x0104  # 1.4.2 stop, no argument: changes the measurement status 1.4.1 keeps in NVM
_ARG_FRAME_LEN = 5  # command word, argument word, its CRC (1.1.2-1.1.3); a 2-byte frame of such a word is a read


class WriteCountingOpen:
    # Replaces `module`'s own `open` (module globals shadow builtins), counting every open for writing,
    # the only way that module reaches the flash, and optionally failing each one; restored on exit.
    def __init__(self, module: object, *, fail_writes: bool = False, error: "BaseException | None" = None) -> None:
        self.module = module
        self.writes = 0
        self.reads = 0
        self.fail_writes = fail_writes
        self.error = OSError(28, "ENOSPC") if error is None else error
        self._saved: object = _ABSENT

    def __call__(self, path: str, mode: str = "r") -> object:
        if "w" in mode:
            self.writes += 1
            if self.fail_writes:
                raise self.error
        else:
            self.reads += 1
        return _real_open(path, mode)

    def __enter__(self) -> "WriteCountingOpen":
        self._saved = getattr(self.module, _OPEN, _ABSENT)
        setattr(self.module, _OPEN, self)
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._saved is _ABSENT:
            delattr(self.module, _OPEN)
        else:
            setattr(self.module, _OPEN, self._saved)


def scd30_nvm_writes(fake_i2c: "I2C", address: int = 0x61) -> "dict[int, int]":
    # {command word: frames sent} over every NVM-writing frame `fake_i2c` logged to `address`. A
    # truncated log would undercount, so a log that dropped entries fails here instead.
    assert fake_i2c.log.dropped == 0, "the fake I2C log dropped entries: the count would be short"
    counts: dict[int, int] = {}
    for entry in fake_i2c.log:
        if entry[0] != "writeto" or entry[1] != address or len(entry[2]) < 2:
            continue
        frame = entry[2]
        word = (frame[0] << 8) | frame[1]
        if (len(frame) == _ARG_FRAME_LEN and word in _NVM_ARG_WORDS) or (len(frame) == 2 and word == _NVM_STOP_WORD):
            counts[word] = counts.get(word, 0) + 1
    return counts
