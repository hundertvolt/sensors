"""Isolated-driver device script: GPIO-level fault injection against the FRAM's chip select - deasserted inside a
write's payload, a read's payload and a WREN, then held inactive across two writes until the driver declares the chip
lost - each followed by recovery (the RP2040 owns CS as a GPIO, so no extra hardware). Reports facts per scenario."""

import asyncio

import asy_spi_driver
from asy_fram_driver import FRAM_SPI
from asy_print_log import PrintLogHistory

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_SCRATCH_REGIONS = ((0x9000, 0x400),)
_BASE = _SCRATCH_REGIONS[0][0]
# Each scenario's 16 bytes, as offsets into the region (every raw call adds _BASE).
_WRITE_RACE_AT = 0x000
_WREN_RACE_AT = 0x080
_READ_RACE_AT = 0x100
_CHIP_LOST_AT = 0x180
_POST_RECOVERY_WRITE_HIJACK_AT = 0x200
_POST_RECOVERY_READ_HIJACK_AT = 0x300

_ORIGINAL_PATTERN = bytes(range(16))
_HIJACKED_WRITE_PATTERN = bytes((0xAA,) * 16)
_READ_SEED_PATTERN = bytes(range(0x60, 0x70))
_POST_RECOVERY_PATTERN = bytes(range(0x40, 0x50))
_WREN = b"\x06"  # MB85RS2MTA datasheet p.6: Write Enable Latch set, its own one-byte CS cycle
# @tunable l3.fram_cs_hijack_fault_injection_and_recovery_victim_bound_s = 30.0
_VICTIM_BOUND_S = 30.0
_LOST_AFTER_WRITES = 2  # the driver probes the chip after this many write-latch faults in a row (_PROBE_AT)


class _CsHijack:
    # Deasserts CS from inside the victim's own transfer, at the driver's synchronous seam: the CS window does not
    # yield, so a racing task cannot land in it.

    def __init__(self, fram: FRAM_SPI, payload: "int | bytes") -> None:
        self._spidev = fram._spidev
        self._payload = payload  # a payload length, or the exact one-byte command to deselect inside
        self._write_sync = self._spidev.write_sync
        self._readinto_sync = self._spidev.readinto_sync
        self._session_begin = self._spidev.session_begin
        self.injected_with_cs_asserted = False

    def _hit(self, buf: "bytes | bytearray | memoryview") -> bool:
        if self.injected_with_cs_asserted:
            return False
        return len(buf) == self._payload if isinstance(self._payload, int) else bytes(buf) == self._payload

    def _yank(self) -> None:
        cs, active = self._spidev._cs_pin, self._spidev._cs_active_value
        # An output pin reads back its driven level on rp2: proof the injection landed while the victim held CS.
        self.injected_with_cs_asserted = cs.value() == active
        cs.value(not active)

    def hold_inactive(self) -> None:
        # Every CS cycle starts deselected: the chip sees no command at all, as if it had gone from the bus.
        def deselected() -> bool:
            began = self._session_begin()
            self._yank()
            return began

        self._spidev.session_begin = deselected  # type: ignore[method-assign]

    def install_for_read(self) -> None:
        def hijacked(buf: "bytearray | memoryview", write_value: int = 0x00) -> bool:
            if self._hit(buf):
                self._yank()
            return self._readinto_sync(buf, write_value)

        self._spidev.readinto_sync = hijacked  # type: ignore[method-assign]

    def install_for_write(self) -> None:
        def hijacked(buf: "bytes | bytearray | memoryview") -> bool:
            if self._hit(buf):
                self._yank()  # deselect the chip before the bytes reach it
            return self._write_sync(buf)

        self._spidev.write_sync = hijacked  # type: ignore[method-assign]

    def remove(self) -> None:
        self._spidev.write_sync = self._write_sync  # type: ignore[method-assign]
        self._spidev.readinto_sync = self._readinto_sync  # type: ignore[method-assign]
        self._spidev.session_begin = self._session_begin  # type: ignore[method-assign]


async def _readback(fram: FRAM_SPI, offset: int, size: int) -> "bytes | None":
    buf = bytearray(size)
    async with fram:
        ok = await fram.get_values(buf, addr_start=_BASE + offset)
    return bytes(buf) if ok else None


async def _recovered(fram: FRAM_SPI, offset: int, wdt: "machine.WDT") -> bool:
    # verify_present() takes the outer lock itself (asyncio.Lock is not reentrant), then a clean write reads back.
    present = await fram.verify_present()
    wdt.feed()
    readback = bytearray(len(_POST_RECOVERY_PATTERN))
    async with fram:
        wrote = await fram.set_values(_POST_RECOVERY_PATTERN, addr_start=_BASE + offset)
    async with fram:
        read = await fram.get_values(readback, addr_start=_BASE + offset)
    return present and wrote and read and readback == _POST_RECOVERY_PATTERN


async def _victim_read(fram: FRAM_SPI, buf: bytearray, offset: int) -> "str | None":
    try:
        async with fram:
            await fram.get_values(buf, addr_start=_BASE + offset)
    except Exception as e:  # recorded as the scenario's fact; the host decides
        return repr(e)
    return None


async def _victim_write(fram: FRAM_SPI, buf: bytes, offset: int) -> "str | None":
    try:
        async with fram:
            await fram.set_values(buf, addr_start=_BASE + offset)
    except Exception as e:  # recorded as the scenario's fact; the host decides
        return repr(e)
    return None


async def _main() -> None:
    wdt = arm()
    raised_in_tasks: list[str] = []
    asyncio.get_event_loop().set_exception_handler(lambda _loop, context: raised_in_tasks.append(repr(context.get("exception"))))
    chip = BENCH["instances"]["fram"]
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    logger = PrintLogHistory(name="FRAMCSHIJACK")
    fram = FRAM_SPI(spi, chip["cs_pin"], logger=logger, max_size=BENCH["fram_max_size"])
    await fram.setup()
    fact("initialized", fram.initialized)
    if not fram.initialized:
        done()
        return

    # 1: the payload of a write deselected, which the chip never takes (owner, 2026-09-04, below).
    async with fram:
        seeded = await fram.set_values(_ORIGINAL_PATTERN, addr_start=_BASE + _WRITE_RACE_AT)
    hijack = _CsHijack(fram, len(_HIJACKED_WRITE_PATTERN))
    hijack.install_for_write()
    try:
        raised = await asyncio.wait_for(_victim_write(fram, _HIJACKED_WRITE_PATTERN, _WRITE_RACE_AT), _VICTIM_BOUND_S)
    finally:
        hijack.remove()
    # Hard requirement (owner, 2026-09-04): the hijacked write never reaches the chip.
    readback = await _readback(fram, _WRITE_RACE_AT, len(_ORIGINAL_PATTERN))
    fact("write_hijack", {"seeded": seeded, "injected": hijack.injected_with_cs_asserted, "raised": raised, "readback_ok": readback == _ORIGINAL_PATTERN, "recovered": await _recovered(fram, _POST_RECOVERY_WRITE_HIJACK_AT, wdt)})

    # 2: the payload of a read deselected, which returns no real data (owner, 2026-09-04, below).
    async with fram:
        seeded = await fram.set_values(_READ_SEED_PATTERN, addr_start=_BASE + _READ_RACE_AT)
    victim_buf = bytearray(len(_READ_SEED_PATTERN))
    hijack = _CsHijack(fram, len(victim_buf))
    hijack.install_for_read()
    try:
        raised = await asyncio.wait_for(_victim_read(fram, victim_buf, _READ_RACE_AT), _VICTIM_BOUND_S)
    finally:
        hijack.remove()
    # Hard requirement (owner, 2026-09-04): a hijacked read never returns the real data.
    fact("read_hijack", {"seeded": seeded, "injected": hijack.injected_with_cs_asserted, "raised": raised, "real_data_returned": raised is None and victim_buf == _READ_SEED_PATTERN, "recovered": await _recovered(fram, _POST_RECOVERY_READ_HIJACK_AT, wdt)})

    # 3: the first WREN of a write deselected - the driver's one WREN retry lands the write.
    hijack = _CsHijack(fram, _WREN)
    hijack.install_for_write()
    try:
        raised = await asyncio.wait_for(_victim_write(fram, _HIJACKED_WRITE_PATTERN, _WREN_RACE_AT), _VICTIM_BOUND_S)
    finally:
        hijack.remove()
    readback = await _readback(fram, _WREN_RACE_AT, len(_HIJACKED_WRITE_PATTERN))
    fact("wren_dropped", {"injected": hijack.injected_with_cs_asserted, "raised": raised, "readback_ok": readback == _HIJACKED_WRITE_PATTERN})
    wdt.feed()

    # 4: CS held inactive across two writes - the driver declares the chip lost; released, setup() brings it back.
    hijack = _CsHijack(fram, 0)
    hijack.hold_inactive()
    try:
        for _ in range(_LOST_AFTER_WRITES):
            async with fram:
                await fram.set_values(_HIJACKED_WRITE_PATTERN, addr_start=_BASE + _CHIP_LOST_AT)
    finally:
        hijack.remove()
    lost = {"initialized_after": fram.initialized, "errnos": [code for code in logger.history if code]}
    try:
        lost["setup_after_release"] = await fram.setup()
    except (OSError, RuntimeError) as e:  # a chip that stays unidentified: the scenario's own failure
        lost["setup_after_release"] = repr(e)
    lost["recovered"] = fram.initialized and await _recovered(fram, _CHIP_LOST_AT, wdt)
    fact("chip_lost", lost)
    fact("system_task_exceptions", raised_in_tasks)
    done()


asyncio.run(_main())
