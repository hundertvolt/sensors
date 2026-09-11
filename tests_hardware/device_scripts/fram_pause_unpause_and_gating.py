"""Isolated-driver device script: the FRAM storage-pause gate against the real SPI FRAM chip -
that a pause genuinely prevents the bus write (not just returns False), that override_pause still
reaches the chip, and that a REAL machine.Timer auto-unpause actually fires (SPECIFICATION.md F.1's
soft-Timer-callback-drop gotcha makes that a hardware-only claim)."""

import asyncio

import machine

import asy_spi_driver
from asy_fram_manager import AsyFramChunk, AsyFramManager
from crc_checks import CRC8
from system_service import SystemService

CHUNK_SIZE = 32
PATTERN_A = bytes((i * 7 + 3) % 256 for i in range(CHUNK_SIZE))
PATTERN_B = bytes((i * 11 + 29) % 256 for i in range(CHUNK_SIZE))  # distinct, so a stale read can't masquerade as a fresh one

PAUSE_SEC = 2
REARM_SEC = 6
_WDT_TIMEOUT_MS = 8000
failures: list[str] = []
wdt: "machine.WDT | None" = None


async def sleep_fed(seconds: float) -> None:
    """asyncio.sleep() that keeps the watchdog fed. Load-bearing: mpremote's soft reset does NOT
    disarm an already-armed rp2 watchdog, so any device script whose own runtime exceeds the ~8s
    timeout resets the board mid-run (confirmed directly - it presents as a bare serial EIO, which
    looks nothing like a watchdog reset). Every long-running script in this directory feeds one for
    this reason; the auto-unpause windows below are what make this script one of them."""
    remaining = seconds
    while remaining > 0:
        step = min(remaining, 1.0)
        await asyncio.sleep(step)
        if wdt is not None:
            wdt.feed()
        remaining -= step


def check(msg: str, *, condition: bool) -> None:
    if not condition:
        failures.append(msg)


async def _ntp_never_synced() -> bool:
    return False


async def _check_gating(fram: AsyFramManager, chunk: AsyFramChunk) -> None:
    # 1. Baseline: unpaused round trip. Without this every later "blocked" result is ambiguous.
    check("baseline write while unpaused returned False", condition=await chunk.write(PATTERN_A))
    check("baseline read did not return the written pattern", condition=bytes(await chunk.read() or b"") == PATTERN_A)
    check("manager reported paused before anything paused it", condition=fram.get_pause() is False)

    # 2. Paused write is refused AND never reaches the chip - proven by reading the real bytes back
    #    with override_pause, which is the only way to distinguish "refused" from "silently wrote".
    fram.set_pause(value=True)
    check("get_pause() did not reflect set_pause(True)", condition=fram.get_pause() is True)
    check("write while paused returned True - the gate did not refuse it", condition=await chunk.write(PATTERN_B) is False)
    still_a = await chunk.read(override_pause=True)
    check("real chip contents changed while paused - the pause did not prevent the bus write", condition=bytes(still_a or b"") == PATTERN_A)

    # 3. Paused read is refused too.
    check("read while paused returned data - the gate did not refuse it", condition=await chunk.read() is None)

    # 4. override_pause reaches the real chip in both directions (zero callers in src/, so this
    #    escape hatch has only ever been exercised against mocks).
    check("override_pause write was refused", condition=await chunk.write(PATTERN_B, override_pause=True) is True)
    check("override_pause read did not return the overridden write", condition=bytes(await chunk.read(override_pause=True) or b"") == PATTERN_B)

    # 5. Unpausing restores normal operation.
    fram.set_pause(value=False)
    check("get_pause() did not reflect set_pause(False)", condition=fram.get_pause() is False)
    check("write after unpause was still refused", condition=await chunk.write(PATTERN_A) is True)
    check("read after unpause did not return the fresh write", condition=bytes(await chunk.read() or b"") == PATTERN_A)



async def _check_auto_unpause_timers(fram: AsyFramManager, sysfunct: SystemService, chunk: AsyFramChunk) -> None:
    # 6. The REAL auto-unpause timer. A mock Timer cannot prove this fires on an rp2 alarm pool.
    sysfunct.pause_permanent_storage(PAUSE_SEC)
    check(f"pause_permanent_storage({PAUSE_SEC}) did not pause", condition=fram.get_pause() is True)
    await sleep_fed(PAUSE_SEC + 1.5)
    check(f"real ONE_SHOT auto-unpause timer never fired after {PAUSE_SEC}s - storage stayed paused", condition=fram.get_pause() is False)
    check("write after the real auto-unpause was still refused", condition=await chunk.write(PATTERN_B) is True)

    # 7. Zero duration unpauses immediately.
    sysfunct.pause_permanent_storage(PAUSE_SEC)
    check("re-pause before the zero-duration check did not take effect", condition=fram.get_pause() is True)
    sysfunct.pause_permanent_storage(0)
    check("pause_permanent_storage(0) did not unpause immediately", condition=fram.get_pause() is False)

    # 8. Re-arm: a second pause replaces the first pending timer rather than leaving it to fire
    #    early (pause_permanent_storage() deinit()s storage_timer before re-arming).
    sysfunct.pause_permanent_storage(PAUSE_SEC)
    sysfunct.pause_permanent_storage(REARM_SEC)
    await sleep_fed(PAUSE_SEC + 1.5)  # the FIRST window has now elapsed
    check(f"storage unpaused after the superseded {PAUSE_SEC}s window - re-arm did not cancel the first timer", condition=fram.get_pause() is True)
    await sleep_fed(REARM_SEC - PAUSE_SEC + 0.5)  # now past the SECOND window too
    check(f"re-armed {REARM_SEC}s auto-unpause timer never fired", condition=fram.get_pause() is False)



async def _check_exhausted_alarm_pool(fram: AsyFramManager, sysfunct: SystemService, chunk: AsyFramChunk) -> None:
    # 9. Safety invariant under a genuinely exhausted alarm pool: storage must never be left
    #    paused with nothing able to unpause it. pause_permanent_storage() deinit()s its own
    #    storage_timer before re-arming, so whether the re-arm actually hits the ENOMEM abort path
    #    or finds the slot it just freed is an rp2 alarm-pool detail this script deliberately does
    #    not predict - both outcomes are acceptable, and the assertion is the invariant they share:
    #    the REST window is a fixed 300s no client can shorten, so a pause that neither aborts nor
    #    auto-unpauses would strand FRAM writes for five minutes with no way back.
    hogged = []
    try:
        for _ in range(64):
            hog = machine.Timer()
            hog.init(period=60_000, callback=lambda _t: None)
            hogged.append(hog)
    except OSError:
        pass  # the pool is now exhausted, which is the condition under test
    if not hogged:
        failures.append("could not construct any Timer to exhaust the alarm pool - safety check inconclusive")
    else:
        sysfunct.pause_permanent_storage(PAUSE_SEC)
        if fram.get_pause():  # not the abort path - then it must still auto-unpause on its own
            await sleep_fed(PAUSE_SEC + 1.5)
        check(
            "storage was left paused with no pending auto-unpause after the alarm pool was exhausted",
            condition=fram.get_pause() is False,
        )
        check("a real write stayed refused after the exhausted-pool pause resolved", condition=await chunk.write(PATTERN_A) is True)
    for hog in hogged:
        try:
            hog.deinit()
        except Exception:
            pass



async def _check_clear_and_timestamped(fram: AsyFramManager, chunk: AsyFramChunk) -> None:
    # 10. clear() honours the same gate as write()/read() (mock tier covers this; the real chip
    #     never has). Proven against real bytes: a refused clear leaves the payload readable.
    fram.set_pause(value=True)
    check("clear() while paused was not refused", condition=await chunk.clear() is False)
    check("a refused clear still wiped the real chip", condition=bytes(await chunk.read(override_pause=True) or b"") == PATTERN_A)
    check("clear(override_pause=True) was refused", condition=await chunk.clear(override_pause=True) is True)
    fram.set_pause(value=False)
    check("a chunk cleared with override did not read back as uninitialized", condition=await chunk.read() is None)
    check("the cleared chunk could not be rewritten", condition=await chunk.write(PATTERN_A) is True)

    # 11. The timestamped chunk variant honours the gate too - this is the shape SGP40's real VOC
    #     backup uses (AsyFramTimestampedChunk), so covering only the plain chunk above would leave
    #     the production-relevant one unproven on real hardware.
    ts_chunk = fram.get_timestamped_chunk(CHUNK_SIZE, _ntp_never_synced, crc=CRC8())
    if ts_chunk is None:
        failures.append("get_timestamped_chunk() returned None")
    else:
        # write() here returns (ntp_synced, utc, written) - the third element is the actual write
        # result; the first two report whether a real timestamp could be stamped, which is False on
        # this NTP-less isolated script and deliberately not what the pause gate is being judged on.
        *_, written = await ts_chunk.write(PATTERN_A)
        check("baseline timestamped write while unpaused failed", condition=written is True)
        fram.set_pause(value=True)
        *_, written = await ts_chunk.write(PATTERN_B)
        check("timestamped write while paused was not refused", condition=written is False)
        _valid, _ts, data = await ts_chunk.read(override_pause=True)
        check("the refused timestamped write still reached the real chip", condition=bytes(data or b"") == PATTERN_A)
        *_, written = await ts_chunk.write(PATTERN_B, override_pause=True)
        check("timestamped write with override_pause was refused", condition=written is True)
        fram.set_pause(value=False)
        _valid2, _ts2, data2 = await ts_chunk.read()
        check("timestamped read after unpause did not return the overridden write", condition=bytes(data2 or b"") == PATTERN_B)


async def _main() -> None:
    global wdt
    wdt = machine.WDT(timeout=_WDT_TIMEOUT_MS)
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram.setup():
        print("RESULT: FAIL fram.setup() failed - real FRAM chip not responding on spi0/cs5")
        return

    chunk = fram.get_chunk(CHUNK_SIZE, crc=CRC8())
    if chunk is None:
        print("RESULT: FAIL get_chunk() returned None")
        return

    sysfunct = SystemService(_ntp_never_synced, fram=fram, debug=None)
    await _check_gating(fram, chunk)
    await _check_auto_unpause_timers(fram, sysfunct, chunk)
    await _check_exhausted_alarm_pool(fram, sysfunct, chunk)
    await _check_clear_and_timestamped(fram, chunk)

    if failures:
        print(f"RESULT: FAIL {len(failures)} issue(s): {'; '.join(failures[:8])}")
    else:
        print("RESULT: PASS pause gates real writes/reads/clears (plain and timestamped chunks), override_pause bypasses, and the real auto-unpause timer fires (immediate, delayed and re-armed)")


asyncio.run(_main())
