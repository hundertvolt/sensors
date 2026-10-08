import asyncio
import os

from _fram_chip_fake import FakeMB85RS64V
from _tmp_scratch import TmpScratch
from _write_counters import WriteCountingOpen, scd30_nvm_writes
from machine import I2C, Pin

import asy_config_manager as cm

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[object, object, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


_scratch = TmpScratch("write_counters")
_DIR = _scratch.dir()
_VAL_INT: "cm.ConfigSchema" = (("Count", "int", 5, 0, 10, None),)
_ADDR = 0x61


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass  # already gone


def _bus() -> I2C:
    return I2C(0, scl=Pin(1), sda=Pin(0))


def _frame(word: int, *rest: int) -> bytes:
    return bytes([word >> 8, word & 0xFF]) + bytes(rest)  # MicroPython has no [*rest] unpacking in a list


# ---------------------------------------------------------------------------
# WriteCountingOpen: counts a module's opens for writing, fails them on request, and restores `open`
# ---------------------------------------------------------------------------


def test_write_counting_open_counts_a_planted_extra_write() -> None:
    path = _DIR + "planted.cfg"
    _remove(path)
    try:
        mgr = cm.ConfigManager(path, _VAL_INT, "TEST")
        with WriteCountingOpen(cm) as fake:
            run(mgr.setup())  # no file yet: the one write of the defaults
            assert fake.writes == 1
            with cm.open(path, "w") as f:  # type: ignore[attr-defined]  # the planted extra write
                f.write("{}")
            assert (fake.writes, fake.reads) == (2, 0)
    finally:
        _remove(path)


def test_write_counting_open_counts_reads_apart_from_writes() -> None:
    path = _DIR + "reads.cfg"
    _remove(path)
    try:
        run(cm.ConfigManager(path, _VAL_INT, "TEST").setup())
        with WriteCountingOpen(cm) as fake:
            run(cm.ConfigManager(path, _VAL_INT, "TEST").setup())  # a valid file: read once, nothing written
        assert (fake.writes, fake.reads) == (0, 1)
    finally:
        _remove(path)


def test_write_counting_open_fails_each_write_with_the_given_error() -> None:
    path = _DIR + "failing.cfg"
    planted = OSError(5, "EIO")
    with WriteCountingOpen(cm, fail_writes=True, error=planted) as fake:
        for _ in range(2):
            try:
                cm.open(path, "w")  # type: ignore[attr-defined]
            except OSError as e:
                assert e is planted
            else:
                raise AssertionError("a failing write must raise")
    assert fake.writes == 2


def test_write_counting_open_restores_the_module_on_exit() -> None:
    assert not hasattr(cm, "open")
    with WriteCountingOpen(cm):
        assert hasattr(cm, "open")
    assert not hasattr(cm, "open")  # absent before, absent after: builtins.open is reached again

    def own_open(path: str, mode: str = "r") -> object:
        return (path, mode)

    cm.open = own_open
    try:
        with WriteCountingOpen(cm) as fake:
            assert cm.open is fake
        assert cm.open is own_open  # a module's own open comes back as it was
    finally:
        del cm.open


# ---------------------------------------------------------------------------
# scd30_nvm_writes(): the NVM-writing frames a fake bus logged, by command word
# ---------------------------------------------------------------------------


def test_scd30_nvm_writes_counts_every_nvm_command_and_the_stop() -> None:
    bus = _bus()
    for word in (0x0010, 0x4600, 0x5306, 0x5204, 0x5403, 0x5102):
        bus.writeto(_ADDR, _frame(word, 0x00, 0x02, 0xE3))
    bus.writeto(_ADDR, _frame(0x0104))
    assert scd30_nvm_writes(bus) == {0x0010: 1, 0x4600: 1, 0x5306: 1, 0x5204: 1, 0x5403: 1, 0x5102: 1, 0x0104: 1}


def test_scd30_nvm_writes_ignores_reads_other_commands_and_other_addresses() -> None:
    bus = _bus()
    bus.writeto(_ADDR, _frame(0x4600))  # a 2-byte frame of an argument word is a register read
    bus.writeto(_ADDR, _frame(0x0202))  # data ready
    bus.writeto(_ADDR, _frame(0x0300))  # read measurement
    bus.writeto(_ADDR, _frame(0xD304))  # soft reset: writes no NVM
    bus.writeto(0x59, _frame(0x4600, 0x00, 0x02, 0xE3))  # another chip on the bus
    bus.writeto(_ADDR, b"\x46")  # a short frame carries no word
    assert scd30_nvm_writes(bus) == {}


def test_scd30_nvm_writes_counts_a_planted_extra_write() -> None:
    bus = _bus()
    bus.writeto(_ADDR, _frame(0x5403, 0x00, 0x64, 0x00))
    assert scd30_nvm_writes(bus) == {0x5403: 1}
    bus.writeto(_ADDR, _frame(0x5403, 0x00, 0x64, 0x00))
    assert scd30_nvm_writes(bus) == {0x5403: 2}
    assert scd30_nvm_writes(_bus(), address=0x59) == {}


def test_scd30_nvm_writes_refuses_a_log_that_dropped_entries() -> None:
    bus = _bus()
    bus.log.dropped = 1
    try:
        scd30_nvm_writes(bus)
    except AssertionError:
        return
    raise AssertionError("a truncated log must not give a count")


def test_the_fram_fake_counts_every_write_command_that_reaches_its_data_phase() -> None:
    chip = FakeMB85RS64V(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    assert chip.write_transactions == 0
    chip.write(bytes([0x06]))  # WREN
    chip.write(bytes([0x02, 0x00, 0x10]))  # WRITE opcode and address: not yet a write
    assert chip.write_transactions == 0
    chip.write(b"ab")  # its data phase
    assert chip.write_transactions == 1
    assert chip.memory[0x10:0x12] == b"ab"
    chip.write(bytes([0x02, 0x00, 0x20]))  # no WREN first: the chip drops the data, the command still ran
    chip.write(b"cd")
    assert chip.write_transactions == 2
    assert chip.memory[0x20:0x22] == bytes(2)
    chip.write(bytes([0x03, 0x00, 0x10]))  # READ is no write
    chip.readinto(bytearray(2))
    assert chip.write_transactions == 2


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
