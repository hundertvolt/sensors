"""Isolated-driver device script: the FRAM storage-pause gate against the real chip - a pause genuinely prevents the
bus write rather than only returning False, and the auto-unpause deadline is met on the real uptime tick (Part F.1,
C.9). The chunk is cleared after setup and zeroed on the way out; a check whose premise failed is reported skipped."""

import asyncio

import machine

import asy_spi_driver
from asy_crc_checks import CRC8
from asy_fram_manager import FRAMChunk, FRAMManager, FRAMTimestampedChunk
from asy_system_service import SystemService

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, errors, fact
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

CHUNK_SIZE = 32
PATTERN_A = bytes((i * 7 + 3) % 256 for i in range(CHUNK_SIZE))
PATTERN_B = bytes((i * 11 + 29) % 256 for i in range(CHUNK_SIZE))  # distinct, so a stale read can't masquerade as a fresh one

# @tunable l3.fram_pause_unpause_and_gating_pause_s = 2
_PAUSE_S = 2
# @tunable l3.fram_pause_unpause_and_gating_rearm_s = 6
_REARM_S = 6
# @tunable l3.fram_pause_unpause_and_gating_pause_margin_s = 1.5
_PAUSE_MARGIN_S = 1.5  # the unpause lands at most one 1 s uptime pass late, so 0.5 s of headroom is left
# @tunable l3.fram_pause_unpause_and_gating_rearm_margin_s = 0.5
_REARM_MARGIN_S = 0.5
_POOL_BOUND = 64  # above the real alarm pool, which is small and fixed (timer_alarm_pool_exhaustion.py measures it)
failures: list[str] = []
skipped: list[str] = []
wdt: "machine.WDT | None" = None


async def _check_auto_unpause_timers(fram: FRAMManager, sysfunct: SystemService, chunk: FRAMChunk) -> None:
    # 5. The auto-unpause deadline, tested by the uptime pass on the board's real tick timer.
    check(f"pause_permanent_storage({_PAUSE_S}) answered False", condition=sysfunct.pause_permanent_storage(_PAUSE_S))
    check(f"pause_permanent_storage({_PAUSE_S}) did not pause", condition=fram.get_pause() is True)
    await _sleep_fed_s(_PAUSE_S + _PAUSE_MARGIN_S)
    check(f"the auto-unpause deadline never ended the pause after {_PAUSE_S}s - storage stayed paused", condition=fram.get_pause() is False)
    check("write after the real auto-unpause was still refused", condition=await chunk.write(PATTERN_B) is True)

    # 6. Zero duration unpauses immediately.
    sysfunct.pause_permanent_storage(_PAUSE_S)
    check("re-pause before the zero-duration check did not take effect", condition=fram.get_pause() is True)
    sysfunct.pause_permanent_storage(0)
    check("pause_permanent_storage(0) did not unpause immediately", condition=fram.get_pause() is False)

    # 7. Re-arm: a second pause replaces the first pending deadline rather than leaving it to end
    #    the pause early.
    sysfunct.pause_permanent_storage(_PAUSE_S)
    sysfunct.pause_permanent_storage(_REARM_S)
    await _sleep_fed_s(_PAUSE_S + _PAUSE_MARGIN_S)  # the FIRST window has now elapsed
    check(f"storage unpaused after the superseded {_PAUSE_S}s window - the second pause did not replace the first deadline", condition=fram.get_pause() is True)
    await _sleep_fed_s(_REARM_S - _PAUSE_S + _REARM_MARGIN_S)  # now past the SECOND window too
    check(f"the re-armed {_REARM_S}s auto-unpause deadline never ended the pause", condition=fram.get_pause() is False)


async def _check_clear_and_timestamped(fram: FRAMManager, chunk: FRAMChunk) -> None:
    # 9. clear() honours the same gate as write()/read() (mock tier covers this; the real chip
    #    never has). Proven against real bytes: a refused clear leaves the payload readable once unpaused.
    #    The payload is written here: step 8 writes it only when its own premise held.
    check("the payload write before the clear check was refused", condition=await chunk.write(PATTERN_A) is True)
    fram.set_pause(value=True)
    check("clear() while paused was not refused", condition=await chunk.clear() is False)
    fram.set_pause(value=False)
    check("a refused clear still wiped the real chip", condition=bytes(await chunk.read() or b"") == PATTERN_A)
    check("clear() after unpausing was refused", condition=await chunk.clear() is True)
    check("a cleared chunk did not read back as uninitialized", condition=await chunk.read() is None)
    check("the cleared chunk could not be rewritten", condition=await chunk.write(PATTERN_A) is True)

    # 10. The timestamped chunk variant honours the gate too - this is the shape SGP40's real VOC
    #     backup uses (FRAMTimestampedChunk), so covering only the plain chunk above would leave
    #     the production-relevant one unproven on real hardware.
    ts_chunk = fram.get_timestamped_chunk(CHUNK_SIZE, _ntp_never_synced, crc=CRC8(), owner="fram_pause_unpause_and_gating_ts")
    if ts_chunk is None:
        skipped.append("timestamped gate: get_timestamped_chunk() returned None")
    else:
        try:
            await _check_timestamped(fram, ts_chunk)
        finally:
            fact("ts_cleared_last", await ts_chunk.clear())


async def _check_exhausted_alarm_pool(fram: FRAMManager, sysfunct: SystemService, chunk: FRAMChunk) -> None:
    # 8. Safety invariant under an exhausted alarm pool: storage is never left paused with nothing
    #    able to unpause it. A pause arms no timer, so the pool cannot refuse it; the uptime tick
    #    armed before the pool ran out ends it.
    hogged = []
    exhausted = False
    try:
        for _ in range(_POOL_BOUND):
            hog = machine.Timer()
            hog.init(period=60_000, callback=lambda _t: None)
            hogged.append(hog)
    except OSError:
        exhausted = True  # the pool is now exhausted, which is the condition under test
    if not hogged or not exhausted:
        skipped.append(f"exhausted-pool pause: {len(hogged)} Timers armed, pool exhausted {exhausted} - the premise did not hold")
    else:
        check("pause_permanent_storage() answered False with the alarm pool exhausted", condition=sysfunct.pause_permanent_storage(_PAUSE_S))
        await _sleep_fed_s(_PAUSE_S + _PAUSE_MARGIN_S)
        check(
            "storage was left paused with no pending auto-unpause after the alarm pool was exhausted",
            condition=fram.get_pause() is False,
        )
        check("a real write stayed refused after the exhausted-pool pause resolved", condition=await chunk.write(PATTERN_A) is True)
    deinit_failures: list[str] = []
    for hog in hogged:
        try:
            hog.deinit()
        except OSError as e:  # a hog left armed holds an alarm the next script would miss: reported, never swallowed
            deinit_failures.append(repr(e))
    errors("hog_deinit_failures", len(deinit_failures), deinit_failures)


async def _check_gating(fram: FRAMManager, chunk: FRAMChunk) -> None:
    # 1. Baseline: unpaused round trip. Without this every later "blocked" result is ambiguous.
    check("baseline write while unpaused returned False", condition=await chunk.write(PATTERN_A))
    check("baseline read did not return the written pattern", condition=bytes(await chunk.read() or b"") == PATTERN_A)
    check("manager reported paused before anything paused it", condition=fram.get_pause() is False)

    # 2. Paused write is refused AND never reaches the chip - proven by unpausing and reading the
    #    real bytes back: the old pattern there tells "refused" from "silently wrote".
    fram.set_pause(value=True)
    check("get_pause() did not reflect set_pause(True)", condition=fram.get_pause() is True)
    check("write while paused returned True - the gate did not refuse it", condition=await chunk.write(PATTERN_B) is False)
    fram.set_pause(value=False)
    still_a = await chunk.read()
    check("real chip contents changed while paused - the pause did not prevent the bus write", condition=bytes(still_a or b"") == PATTERN_A)

    # 3. Paused read is refused too.
    fram.set_pause(value=True)
    check("read while paused returned data - the gate did not refuse it", condition=await chunk.read() is None)

    # 4. Unpausing restores normal operation; PATTERN_B is not on the chip yet, so the read-back is fresh.
    fram.set_pause(value=False)
    check("get_pause() did not reflect set_pause(False)", condition=fram.get_pause() is False)
    check("write after unpause was still refused", condition=await chunk.write(PATTERN_B) is True)
    check("read after unpause did not return the fresh write", condition=bytes(await chunk.read() or b"") == PATTERN_B)


async def _check_timestamped(fram: FRAMManager, ts_chunk: FRAMTimestampedChunk) -> None:
    # write() returns (written, ntp_synced, utc); only the first is judged here (no NTP in an isolated script).
    written, *_ = await ts_chunk.write(PATTERN_A)
    check("baseline timestamped write while unpaused failed", condition=written is True)
    fram.set_pause(value=True)
    written, *_ = await ts_chunk.write(PATTERN_B)
    check("timestamped write while paused was not refused", condition=written is False)
    fram.set_pause(value=False)
    _valid, _ts, data = await ts_chunk.read()
    check("the refused timestamped write still reached the real chip", condition=bytes(data or b"") == PATTERN_A)
    written, *_ = await ts_chunk.write(PATTERN_B)
    check("timestamped write after unpausing was refused", condition=written is True)
    _valid2, _ts2, data2 = await ts_chunk.read()
    check("timestamped read after unpause did not return the fresh write", condition=bytes(data2 or b"") == PATTERN_B)


async def _main() -> None:
    global wdt
    wdt = arm()
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "fram")
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    fram = FRAMManager(spi, chip["cs_pin"], BENCH["fram_max_size"])
    fact("setup", await fram.setup())
    chunk = fram.get_chunk(CHUNK_SIZE, crc=CRC8(), owner="fram_pause_unpause_and_gating")
    fact("allocated", chunk is not None)
    if chunk is None:
        done()
        return
    sysfunct = SystemService(_ntp_never_synced, storage=fram)
    sysfunct.start_uptime_timer()  # the uptime pass that tests the auto-unpause deadline once a second
    status_task = sysfunct.start_asy_status()
    try:
        fact("cleared_first", await chunk.clear())
        await _check_gating(fram, chunk)
        await _check_auto_unpause_timers(fram, sysfunct, chunk)
        await _check_exhausted_alarm_pool(fram, sysfunct, chunk)
        await _check_clear_and_timestamped(fram, chunk)
    finally:
        status_task.cancel()
        fram.set_pause(value=False)
        fact("cleared_last", await chunk.clear())
    errors("failures", len(failures), failures)
    errors("skipped", len(skipped), skipped)
    done()


async def _ntp_never_synced() -> bool:
    return False


async def _sleep_fed_s(seconds: float) -> None:
    # The shared fed wait (_shared/watchdog.py) in this script's seconds.
    if wdt is not None:
        await fed_sleep_ms(wdt, int(seconds * 1000))


def check(msg: str, *, condition: bool) -> None:
    if not condition:
        failures.append(msg)


asyncio.run(_main())
