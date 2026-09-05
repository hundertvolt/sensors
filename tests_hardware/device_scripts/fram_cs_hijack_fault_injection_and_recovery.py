"""Isolated-driver device script, flash-tier: real-hardware GPIO-level fault injection against
FRAM's own CS pin - closing BACKLOG.md's FRAM bus-recovery gap without needing the separate
programmable GPIO fault-injection harness open question 8 flags as "not currently provisioned".
Project-owner-proposed technique (2026-09-04): the RP2040 already fully owns FRAM's own CS pin as a
plain, software-toggled machine.Pin (asy_spi_driver.py's SPIDevice.cs_pin - not a peripheral-managed
hardware-CS line), so a self-contained on-device script can race it directly, no external fault
hardware needed at all.

**Why a CS race, not a mid-byte interrupt**: confirmed directly against asy_spi_driver.py's real
source before designing this - SPIDevice.write()/readinto() have no `await` inside their own bodies
at all (each is `async def` purely for API-shape consistency, calling the real synchronous
machine.SPI.write()/readinto() with no internal yield point), so two back-to-back
`await spidev.write(...)` calls within the same `async with self._spidev` block (e.g. FRAM_SPI._write()'s
own opcode-header-then-data-payload sequence) can never actually be interleaved by another asyncio
task - MicroPython's cooperative scheduler only switches tasks at a genuine yield. The one real,
confirmed yield point in this whole call chain is inside SPIDevice.__aenter__() itself:
`await asyncio.sleep(0.001)`, which runs *after* CS is already asserted but *before* control ever
returns to the caller to send the opcode. Both hijack scenarios below race exactly that window: a
second task, already scheduled and ready to run the instant the first one yields, forces CS back
high before the real operation's opcode/data ever gets clocked out - the real SPI peripheral has no
protocol-level awareness of CS state at all (confirmed against asy_spi_driver.py's own header
comment: "real RP2040 SPI transfers have no ACK/NAK concept... write()/readinto() never raise"), so
the operation "succeeds" completely silently from the driver's own perspective while the chip,
correctly deselected per its own datasheet ("When CS is 'H' level, device is in deselect (standby)
status... Inputs from other pins are ignored" - datasheets/fram/MB85RS2MTA-DS501-00032-3v0-E.pdf
p.2), never receives or transmits a single real bit of it.

**Confirmed empirically, not assumed (2026-09-04, this exact bench unit)**: 5/5 real trials of each
scenario landed identically every time - this is a *deterministic* race, not a flaky timing gamble,
because MicroPython's asyncio scheduler is cooperative and the synchronization below (cs_yanker does
exactly one `await asyncio.sleep(0)` before acting, guaranteeing it's next-in-line the instant
victim_writer/victim_reader yields inside __aenter__) depends on scheduling *order*, not wall-clock
timing luck. Both outcomes below are therefore asserted as hard, unconditional requirements, not
soft/observational - a race that silently missed its window must fail this script loudly, per the
project owner's own explicit direction, not be reported as a shrugged-off alternate outcome:
  - **Write hijack**: the write must never reach the chip at all - real memory at the target address
    must show the *original* data, completely unchanged, after the race. (Confirmed real outcome:
    the write silently "succeeds" from the driver's own perspective - no exception - while genuinely
    changing nothing.)
  - **Read hijack**: the returned data must NOT be the real, correct value - a coincidentally
    "sensible" result here would mean the race didn't actually intercept anything.  (Confirmed real
    outcome, 5/5 trials: the buffer comes back all zero bytes, never a raised exception and never
    the real seeded pattern - MISO's real electrical state while the chip's own SO pin is high-Z
    during deselect, not a driver-level error.)

Both scenarios end with the same two-part recovery proof: verify_present() must succeed cleanly (the
chip's own SPI protocol state machine must never be left wedged by a CS-based interruption - it's
the protocol's own built-in deselect/reset mechanism, not an exotic fault), and a completely fresh
write+read round trip at a different address must work normally afterward too.

This bench unit wires FRAM to SPI0 (sck=2, mosi=3, miso=4), CS=GPIO5, a 256KB MB85RS2MTA chip.

Run via `mpremote run <this> soft-reset`."""

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


async def _cs_yank_race(fram: FRAM_SPI, victim: "object") -> bool:
    """Shared race harness for both scenarios below. Returns whether the yanker actually ran before
    the victim's own __aenter__ sleep elapsed - a cheap, necessary-but-not-sufficient sanity check;
    the real proof each caller relies on is its own outcome-based assertion afterward, per this
    script's own module docstring."""
    cs_forced_high_early = False

    async def cs_yanker() -> None:
        nonlocal cs_forced_high_early
        await asyncio.sleep(0)
        fram._spidev.cs_pin.value(not fram._spidev.cs_active_value)  # deassert
        cs_forced_high_early = True

    await asyncio.wait_for(asyncio.gather(cs_yanker(), victim), 30.0)  # type: ignore[arg-type]
    return cs_forced_high_early


async def _assert_recovery(fram: FRAM_SPI, addr: int, wdt: machine.WDT) -> list:
    failures = []
    recovered = await fram.verify_present()  # not wrapped in `async with fram:` - self-acquires the same outer lock internally (asyncio.Lock isn't reentrant)
    wdt.feed()
    if not recovered:
        failures.append("verify_present() failed after the CS-hijack race - chip/driver did not recover")

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
        except Exception as e:  # noqa: BLE001 - any exception here is itself part of what this script observes, not a bug in the script
            write_raised = e

    yanker_ran = await _cs_yank_race(fram, victim_writer())
    if not yanker_ran:
        failures.append("write hijack: cs_yanker() never actually ran before victim_writer() completed - race did not land, nothing was tested")
    else:
        async with fram:
            write_readback = bytearray(16)
            write_readback_ok = await fram.get_values(write_readback, addr_start=_WRITE_RACE_ADDR)
        # HARD requirement (project owner direction, 2026-09-04): the hijacked write must never
        # have reached the chip - anything else means the race missed its window and this script
        # tested nothing real.
        if not write_readback_ok or bytes(write_readback) != _ORIGINAL_PATTERN:
            failures.append(
                f"write hijack: expected original data {_ORIGINAL_PATTERN.hex()} untouched (write_raised={write_raised!r}), "
                f"got {bytes(write_readback).hex()} - the hijacked write was not reliably blocked"
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
            except Exception as e:  # noqa: BLE001 - see victim_writer()'s own comment
                read_raised = e

        yanker_ran = await _cs_yank_race(fram, victim_reader())
        if not yanker_ran:
            failures.append("read hijack: cs_yanker() never actually ran before victim_reader() completed - race did not land, nothing was tested")
        else:
            # HARD requirement (project owner direction, 2026-09-04): a hijacked read must never
            # return the real, correct data - either it raises, or it comes back implausible/wrong.
            # A "sensible", correct-looking result here would mean the race missed its window.
            # Confirmed real outcome on this bench unit (5/5 trials): never raises, always comes
            # back all zero bytes (MISO's real electrical state while the chip's own SO pin is
            # high-Z during deselect) - not asserted as that *exact* value, since a different
            # unit/wiring could float differently, only that it must not equal the real data.
            if read_raised is None and bytes(hijacked_read_buf) == _READ_SEED_PATTERN:
                failures.append(f"read hijack: got back the real seeded data {_READ_SEED_PATTERN.hex()} with no exception - the race did not reliably intercept the read")
        wdt.feed()
        failures.extend(await _assert_recovery(fram, _POST_RECOVERY_ADDR_READ_HIJACK, wdt))

    if failures:
        print(f"RESULT: FAIL {len(failures)} issue(s): {'; '.join(failures)}")
    else:
        print("RESULT: PASS both write-hijack and read-hijack races landed as required, driver fully recovered from each")


asyncio.run(_main())
