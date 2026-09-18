"""Isolated-driver device script: real-hardware GPIO-level fault injection against FRAM's CS pin -
deasserts CS from inside an in-flight write/read (no external fault hardware needed - the RP2040
already owns CS as a software-toggled Pin). See tests_hardware/README.md's FRAM CS-hijack finding."""

import asyncio

import machine

import asy_spi_driver
from asy_fram_driver import FRAM_SPI
from print_log import PrintLogHistory

_WRITE_RACE_ADDR = 0x9000  # scratch addresses, disjoint from every other device script's own regions
_READ_RACE_ADDR = 0x9100
_POST_RECOVERY_ADDR_WRITE_HIJACK = 0x9200
_POST_RECOVERY_ADDR_READ_HIJACK = 0x9300

_ORIGINAL_PATTERN = bytes(range(16))
_HIJACKED_WRITE_PATTERN = bytes((0xAA,) * 16)  # deliberately distinct from _ORIGINAL_PATTERN
_READ_SEED_PATTERN = bytes(range(0x60, 0x70))  # deliberately distinct from every other pattern above
_POST_RECOVERY_PATTERN = bytes(range(0x40, 0x50))


class _CsHijack:
    """Deasserts CS from inside the victim's own transfer, at the driver's synchronous seam. The
    earlier form raced an `await asyncio.sleep(0)` task into the CS window; measure A made that
    window non-yielding, so the race could no longer land (§7D.5)."""

    def __init__(self, fram: FRAM_SPI, payload_len: int) -> None:
        self._spidev = fram._spidev
        self._payload_len = payload_len  # the command buffers around it are 1 or 5 bytes, never this
        self._write_sync = self._spidev.write_sync
        self._readinto_sync = self._spidev.readinto_sync
        self.injected_with_cs_asserted = False

    def _yank(self) -> None:
        cs, active = self._spidev.cs_pin, self._spidev.cs_active_value
        # Reading an output pin back gives its driven level on rp2, so this is real proof the
        # injection landed while the victim held CS rather than before or after its envelope.
        self.injected_with_cs_asserted = cs.value() == active
        cs.value(not active)

    def install_for_write(self) -> None:
        def hijacked(buf: "bytes | bytearray | memoryview") -> None:
            if len(buf) == self._payload_len and not self.injected_with_cs_asserted:
                self._yank()  # deselect the chip before its payload can reach it
            self._write_sync(buf)

        self._spidev.write_sync = hijacked  # type: ignore[method-assign]

    def install_for_read(self) -> None:
        def hijacked(buf: "bytearray | memoryview", write_value: int = 0x00) -> None:
            if len(buf) == self._payload_len and not self.injected_with_cs_asserted:
                self._yank()
            self._readinto_sync(buf, write_value)

        self._spidev.readinto_sync = hijacked  # type: ignore[method-assign]

    def remove(self) -> None:
        self._spidev.write_sync = self._write_sync  # type: ignore[method-assign]
        self._spidev.readinto_sync = self._readinto_sync  # type: ignore[method-assign]


async def _assert_recovery(fram: FRAM_SPI, addr: int, wdt: machine.WDT) -> list[str]:
    failures = []
    recovered = await fram.verify_present()  # not wrapped in `async with fram:` - self-acquires the same outer lock internally (asyncio.Lock isn't reentrant)
    wdt.feed()
    if not recovered:
        failures.append("verify_present() failed after the CS hijack - chip/driver did not recover")

    async with fram:
        clean_write_ok = await fram.set_values(_POST_RECOVERY_PATTERN, addr_start=addr)
    async with fram:
        clean_readback = bytearray(len(_POST_RECOVERY_PATTERN))
        clean_read_ok = await fram.get_values(clean_readback, addr_start=addr)

    if not clean_write_ok:
        failures.append("post-recovery set_values() failed outright")
    if not clean_read_ok or bytes(clean_readback) != _POST_RECOVERY_PATTERN:
        failures.append(f"post-recovery get_values() returned {bytes(clean_readback).hex()}, expected {_POST_RECOVERY_PATTERN.hex()}")
    return failures


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    spi0 = asy_spi_driver.SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    fram = FRAM_SPI(spi0, 5, logger=PrintLogHistory(name="FRAMCSHIJACK"), max_size=0x40000)
    await fram.setup()
    if not fram.initialized:
        print("RESULT: FAIL fram.setup() did not reach initialized=True - device not found?")
        return

    failures = []

    # --- Scenario 1: write hijack ---------------------------------------------------------------
    async with fram:
        ok = await fram.set_values(_ORIGINAL_PATTERN, addr_start=_WRITE_RACE_ADDR)
    if not ok:
        print("RESULT: FAIL could not seed the write-race region before starting the hijack")
        return
    wdt.feed()

    write_raised: BaseException | None = None

    async def victim_writer() -> None:
        nonlocal write_raised
        try:
            async with fram:
                await fram.set_values(_HIJACKED_WRITE_PATTERN, addr_start=_WRITE_RACE_ADDR)
        except Exception as e:
            write_raised = e

    hijack = _CsHijack(fram, len(_HIJACKED_WRITE_PATTERN))
    hijack.install_for_write()
    try:
        await asyncio.wait_for(victim_writer(), 30.0)
    finally:
        hijack.remove()
    if not hijack.injected_with_cs_asserted:
        failures.append("write hijack: CS was never observed asserted at the payload transfer - nothing was injected, so nothing was tested")
    else:
        async with fram:
            write_readback = bytearray(16)
            write_readback_ok = await fram.get_values(write_readback, addr_start=_WRITE_RACE_ADDR)
        # Hard requirement: the hijacked write must never have reached the chip. CS was proven
        # deasserted before its payload transfer, so a landed write would be a real finding.
        if not write_readback_ok or bytes(write_readback) != _ORIGINAL_PATTERN:
            failures.append(
                f"write hijack: expected original data {_ORIGINAL_PATTERN.hex()} untouched (write_raised={write_raised!r}), "
                f"got {bytes(write_readback).hex()} - the payload reached the chip although CS was deasserted first",
            )
    wdt.feed()
    failures.extend(await _assert_recovery(fram, _POST_RECOVERY_ADDR_WRITE_HIJACK, wdt))

    # --- Scenario 2: read hijack -------------------------------------------------------------
    async with fram:
        ok = await fram.set_values(_READ_SEED_PATTERN, addr_start=_READ_RACE_ADDR)
    if not ok:
        failures.append("read hijack: could not seed the read-race region before starting the hijack")
    else:
        wdt.feed()
        read_raised: BaseException | None = None
        hijacked_read_buf = bytearray(16)

        async def victim_reader() -> None:
            nonlocal read_raised
            try:
                async with fram:
                    await fram.get_values(hijacked_read_buf, addr_start=_READ_RACE_ADDR)
            except Exception as e:
                read_raised = e

        hijack = _CsHijack(fram, len(hijacked_read_buf))
        hijack.install_for_read()
        try:
            await asyncio.wait_for(victim_reader(), 30.0)
        finally:
            hijack.remove()
        if not hijack.injected_with_cs_asserted:
            failures.append("read hijack: CS was never observed asserted at the payload transfer - nothing was injected, so nothing was tested")
        # Hard requirement: a hijacked read must never return the real, correct data - a
        # "sensible" result would mean the deassertion did not take effect. Not asserted against a
        # specific wrong value (a different unit could float differently on a deselected MISO).
        elif read_raised is None and bytes(hijacked_read_buf) == _READ_SEED_PATTERN:
            failures.append(f"read hijack: got back the real seeded data {_READ_SEED_PATTERN.hex()} with no exception - the read completed although CS was deasserted first")
        wdt.feed()
        failures.extend(await _assert_recovery(fram, _POST_RECOVERY_ADDR_READ_HIJACK, wdt))

    if failures:
        print(f"RESULT: FAIL {len(failures)} issue(s): {'; '.join(failures)}")
    else:
        print("RESULT: PASS both write-hijack and read-hijack injections landed as required, driver fully recovered from each")


asyncio.run(_main())
