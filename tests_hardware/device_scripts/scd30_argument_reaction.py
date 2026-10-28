"""Records how the SCD30 takes a measurement-interval write (0x4600, NVM-held) with a wrong argument CRC and one of 0
with a correct CRC: each read back and the period then in effect timed, the original put back in finally. At most
three NVM writes; STATE "interval_write_loop" instead alternates the interval for the manual power-cut step."""

import asyncio
import time

from machine import I2C, Pin

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _mpy_shed.time_mp import _TicksMs
    from _shared.facts import done, fact
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# The command words and the argument CRC (Interface Description 1.4.3-1.4.5; CRC-8, polynomial 0x31, init 0xFF, 1.1.3).
CMD_INTERVAL, CMD_DATA_READY, CMD_READ_MEASUREMENT = 0x4600, 0x0202, 0x0300
_CRC_POLY, _CRC_INIT = 0x31, 0xFF
_INTERVAL_MIN_S, _INTERVAL_MAX_S = 2, 1800  # "Available range: [2 ... 1800]" (1.4.3)
_RP2_I2C_TIMEOUT_US = 50000  # machine.I2C's own default (ports/rp2/machine_i2c.c:38, v1.29.0)
# "the read header should be send with a delay of > 3ms following the write sequence" (1.4.4).
# @tunable l3.scd30_argument_reaction_read_delay_ms = 5
_READ_DELAY_MS = 5
# @tunable l3.scd30_argument_reaction_ready_poll_ms = 100
_READY_POLL_MS = 100
# Two data-ready events at the original interval, with one interval and this slack to spare.
# @tunable l3.scd30_argument_reaction_period_slack_ms = 2000
_PERIOD_SLACK_MS = 2000
# The power-cut loop: at most this many writes, spaced so the operator's cut can land between two of them.
# @tunable l3.scd30_argument_reaction_loop_writes = 20
_LOOP_WRITES = 20
# @tunable l3.scd30_argument_reaction_loop_step_ms = 500
_LOOP_STEP_MS = 500


def _crc8(data: bytes) -> int:
    crc = _CRC_INIT
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ _CRC_POLY) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def _hex(data: bytes) -> str:
    return "".join(f"{b:02x}" for b in data)


def _neighbour(interval: int) -> int:
    # One second away and still inside the range, so a write of it changes the read-back.
    return interval + 1 if interval < _INTERVAL_MAX_S else interval - 1


class Chip:
    def __init__(self, i2c: I2C, address: int, wdt: "machine.WDT") -> None:
        self.i2c, self.address, self.wdt = i2c, address, wdt

    def set_interval(self, value: int, crc: int) -> str:
        # One argument write; whether the chip acknowledged every byte is part of what is recorded.
        try:
            self.i2c.writeto(self.address, bytes([CMD_INTERVAL >> 8, CMD_INTERVAL & 0xFF, value >> 8, value & 0xFF, crc]))
        except OSError as exc:
            return f"OSError:{exc.args[0]}"
        return "acked"

    async def read_after(self, frame: bytes, nbytes: int) -> bytes:
        # A write, the read-header delay, then a separate read: the SCD30 takes no repeated start (1.1).
        self.i2c.writeto(self.address, frame)
        await fed_sleep_ms(self.wdt, _READ_DELAY_MS)
        buf = bytearray(nbytes)
        self.i2c.readfrom_into(self.address, buf)
        return bytes(buf)

    async def word(self, cmd: int) -> "tuple[int, bool]":
        reply = await self.read_after(bytes([cmd >> 8, cmd & 0xFF]), 3)
        return (reply[0] << 8) | reply[1], _crc8(reply[:2]) == reply[2]


async def _partial_pointer(chip: Chip, original: int) -> None:
    # Only the command's first byte, then a read: what a register pointer cut short answers; the full command after it.
    try:
        reply = await chip.read_after(bytes([CMD_INTERVAL >> 8]), 3)
        fact("partial_pointer_word", _hex(reply))
        fact("partial_pointer_crc_ok", _crc8(reply[:2]) == reply[2])
    except OSError as exc:
        fact("partial_pointer_word", f"OSError:{exc.args[0]}")
        fact("partial_pointer_crc_ok", False)
    fact("pointer_restored", await chip.word(CMD_INTERVAL) == (original, True))


async def _period_ms(chip: Chip, bound_ms: int) -> "int | None":
    # The measurement period now in effect: the gap between two data-ready events, each read out to clear it.
    stamps: list[_TicksMs] = []
    start = time.ticks_ms()
    while len(stamps) < 2 and time.ticks_diff(time.ticks_ms(), start) < bound_ms:
        if (await chip.word(CMD_DATA_READY))[0] == 1:
            await chip.read_after(bytes([CMD_READ_MEASUREMENT >> 8, CMD_READ_MEASUREMENT & 0xFF]), 18)
            stamps.append(time.ticks_ms())
        await fed_sleep_ms(chip.wdt, _READY_POLL_MS)
    return time.ticks_diff(stamps[1], stamps[0]) if len(stamps) == 2 else None


async def _reactions(chip: Chip, original: int) -> None:
    # A changed value with a wrong CRC (so an accepted write shows in the read-back), then 0 with a correct one.
    bound_ms = 2 * original * 1000 + _PERIOD_SLACK_MS
    changed = _neighbour(original)
    fact("wrong_crc_value", changed)
    fact("wrong_crc_write", chip.set_interval(changed, _crc8(bytes([changed >> 8, changed & 0xFF])) ^ 0xFF))
    readback = await chip.word(CMD_INTERVAL)
    fact("wrong_crc_readback", list(readback))
    fact("wrong_crc_accepted", readback[0] == changed)
    fact("period_after_wrong_crc_ms", await _period_ms(chip, bound_ms))
    fact("zero_interval_write", chip.set_interval(0, _crc8(bytes(2))))
    readback = await chip.word(CMD_INTERVAL)
    fact("zero_interval_readback", list(readback))
    fact("zero_interval_accepted", readback[0] == 0)
    fact("period_after_zero_ms", await _period_ms(chip, bound_ms))


async def _write_loop(chip: Chip, original: int) -> None:
    # The interval and its neighbour in turn, a banner after each write for the operator watching the console.
    for n in range(1, _LOOP_WRITES + 1):
        value = _neighbour(original) if n % 2 else original
        chip.set_interval(value, _crc8(bytes([value >> 8, value & 0xFF])))
        print(f"WROTE {n} {value}")
        await fed_sleep_ms(chip.wdt, _LOOP_STEP_MS)
    fact("loop_writes", _LOOP_WRITES)


async def main() -> None:
    wdt = arm()
    chip_facts = BENCH["instances"]["scd30"]
    bus = BENCH["bus"][chip_facts["bus"]]
    i2c = I2C(bus["id"], scl=Pin(bus["scl_pin"]), sda=Pin(bus["sda_pin"]), freq=bus["frequency"], timeout=bus.get("timeout", _RP2_I2C_TIMEOUT_US))
    chip = Chip(i2c, BENCH["addresses"]["scd30"], wdt)
    original, crc_ok = await chip.word(CMD_INTERVAL)
    fact("interval_before", original)
    fact("interval_before_crc_ok", crc_ok)
    if not crc_ok or not _INTERVAL_MIN_S <= original <= _INTERVAL_MAX_S:
        fact("skipped", "no valid interval to restore, so nothing is written")
        done()
        return
    try:
        if BENCH.get("STATE") == "interval_write_loop":
            await _write_loop(chip, original)
        else:
            await _partial_pointer(chip, original)
            await _reactions(chip, original)
    finally:
        # Put back only when changed: an unchanged interval costs no further NVM write.
        if await chip.word(CMD_INTERVAL) != (original, True):
            chip.set_interval(original, _crc8(bytes([original >> 8, original & 0xFF])))
        after = await chip.word(CMD_INTERVAL)
        fact("interval_after", after[0])
        fact("restored", "ok" if after == (original, True) else f"interval {after[0]}, crc_ok {after[1]}")
    done()


asyncio.run(main())
