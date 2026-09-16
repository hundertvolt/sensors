"""Twin-tier coverage for the UART crossover link (SPECIFICATION.md Part J.7): builds the real
buildgen-generated sensortask_dev object graph against the digital twin's own buses, joins its two
UART peripherals across the bench rig's jumper, and drives real transfers while the rest of the
task graph runs. sensortask_dev.py itself is never hand-written or committed - scripts/test.sh
pre-generates it into build/generated_src/ (first on MICROPYPATH) via buildgen before this file
ever runs; `import sensortask_dev` below resolves to that generated module."""

import asyncio
import sys
import time

sys.path.insert(0, "ext")  # the real vendored ext/microdot.py sensortask_dev.py transitively imports
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

# Required of any entry point booting a sensortask_* module under the twin, and this file builds
# the real dev graph repeatedly: growing the Unix port's pollfds array corrupts non-fd poll
# objects already in it, and this driver registers exactly such an object per UART.
prewarm_poll_set()

# Must run before AsyUDPSocket is constructed (DNSServer, inside AsyConnTime.__init__): this
# Unix-port build rejects a plain (host, port) tuple in bind()/connect()/sendto().
patch_asy_udp_socket_for_unix_port()

import sensortask_dev  # noqa: E402
from _tmp_scratch import TmpScratch  # noqa: E402
from machine import LinkPoller, UARTLink  # noqa: E402

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from types import ModuleType
    from typing import Any, TypeVar

    T = TypeVar("T")

    from machine import UART as TwinUART
    from machine import UARTLink as TwinLink

# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that module's
# own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("twin_uart")


def run(coro: "Coroutine[Any, Any, T]", limit: int = 30) -> "T":
    return asyncio.run(asyncio.wait_for(coro, limit))


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


def fakes() -> "tuple[TwinUART, TwinUART]":
    # The twin machine.UART objects behind the two drivers. Narrowed in one place: every call site
    # would otherwise repeat the same pair of None checks the module-level globals require.
    dev = sensortask_dev
    assert dev.uart0 is not None and dev.uart1 is not None
    fake_a, fake_b = dev.uart0._uart, dev.uart1._uart
    assert fake_a is not None and fake_b is not None
    return fake_a, fake_b


def build_linked_system() -> "TwinLink":
    # The real dev object graph, its two UART peripherals joined the way the bench jumper joins
    # them (GP0<->GP9, GP1<->GP8). The pollers are then swapped for the bounded stand-in: a real
    # select.poll() never re-checks a Python object's ioctl(), so readiness would never be seen.
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    dev = sensortask_dev
    assert dev.uart0 is not None and dev.uart1 is not None
    assert dev.uart_link_init is not None and dev.uart_link_resp is not None
    fake_a, fake_b = fakes()
    link = UARTLink(fake_a, fake_b)
    dev.uart0.poller = LinkPoller(fake_a)
    dev.uart1.poller = LinkPoller(fake_b)
    return link


async def exchange(work: "Coroutine[Any, Any, T]") -> "T":
    # The initiator's call returning does not mean the responder is finished: it still has its last
    # read to complete, and the twin delivers by real wire time. Cutting the listener off would
    # strand a frame for the next exchange - a harness artefact, so the harness waits it out.
    #
    # Drives the responder's own UART_Comm.uart_listen() directly, not UartLinkExerciser's real
    # get_task_starters() listen loop - deliberately, so this file's callback-storage assertions
    # (test_a_payload_larger_than_one_chunk_crosses_the_jumper_intact) go through the harness's own
    # controlled single round rather than a free-running task. UartLinkExerciser's own message
    # dispatch (_message_callback writing _last_echo) is covered separately by
    # tests/test_asy_uart_link_driver.py's echo-round-trip test, which drives the real task instead.
    dev = sensortask_dev
    assert dev.uart_link_resp is not None
    listener = asyncio.create_task(dev.uart_link_resp._comm.uart_listen())
    try:
        return await work
    finally:
        await _settle_listener(listener)


async def _settle_listener(listener: "asyncio.Task[Any]") -> None:
    try:
        await asyncio.wait_for(listener, 5)
    except asyncio.TimeoutError:
        listener.cancel()
        try:
            await listener
        except asyncio.CancelledError:  # the expected outcome; anything else is a real failure
            pass


# ---------------------------------------------------------------------------
# The dev wiring itself
# ---------------------------------------------------------------------------


def test_both_instances_are_constructed_and_registered() -> None:
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None and dev.uart_link_resp is not None
    sources = dev._collect_error_sources()
    # get_error_sources() delegates entirely to the inner UART_Comm (asy_uart_link_driver.py's own
    # comment) - the flattened error_sources list holds each _comm, not the UartLinkExerciser wrapper.
    assert dev.uart_link_init._comm in sources
    assert dev.uart_link_resp._comm in sources
    setters = dev._collect_level_setters()
    assert dev.uart_link_init.pr.set_level in setters or len(setters) > 0
    assert dev.uart_link_resp.get_task_starters()  # the responder owns the listen task
    # The initiator's own task list is its exercise loop (asy_uart_link_driver.py), not empty the
    # way bare UART_Comm.get_task_starters() would be for an initiator role - one entry, not zero.
    assert len(dev.uart_link_init.get_task_starters()) == 1


def test_the_two_instances_have_distinct_names_and_loggers() -> None:
    # A shared logger would merge two links' histories into a single /status entry and
    # make a fault unattributable to an end.
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None and dev.uart_link_resp is not None
    assert dev.uart_link_init.name != dev.uart_link_resp.name
    assert dev.uart_link_init.pr is not dev.uart_link_resp.pr
    assert dev.uart_link_init.name == dev.uart_link_init.pr.name
    assert dev.uart_link_resp.name == dev.uart_link_resp.pr.name


def test_both_instances_share_one_set_of_protocol_parameters() -> None:
    # payload_size and timeout are out-of-band agreements that must match on both ends,
    # and nothing is negotiated - a mismatch desyncs the link outright and cannot self-heal.
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None and dev.uart_link_resp is not None
    initiator, responder = dev.uart_link_init._comm, dev.uart_link_resp._comm
    assert initiator.payload_size == responder.payload_size
    assert initiator.timeout == responder.timeout
    assert initiator.frame_size == responder.frame_size


def test_the_two_ends_sit_on_distinct_peripherals_with_sized_buffers() -> None:
    # Both on one id would re-init the first's peripheral and leave one link object silently
    # owning nothing. a default-sized rxbuf drops a frame's tail at this payload size.
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart0 is not None and dev.uart1 is not None
    fake_a, fake_b = fakes()
    assert fake_a.id != fake_b.id
    frame_size = dev.uart_link_init._comm.frame_size  # type: ignore[union-attr]
    for driver in (dev.uart0, dev.uart1):
        assert driver.rxbuf >= frame_size
        assert driver.poll_wait_ms < 10  # single-digit, or poll latency dominates throughput


def test_both_ends_get_their_own_real_fram_chunk() -> None:
    # AsyFramManager is a bump-pointer allocator, so instantiation order *is* the on-chip
    # layout - an inserted chunk would turn every previously persisted log into garbage. dev.toml
    # wires fram_target = "fram" on both uart_link instances (WP3), each getting its own chunk -
    # a shared one would merge two links' histories into a single unattributable /status entry.
    build_linked_system()
    dev = sensortask_dev
    assert dev.fram is not None
    assert dev.uart_link_init is not None and dev.uart_link_resp is not None
    assert hasattr(dev.uart_link_init.pr, "fram") and dev.uart_link_init.pr.fram is not None
    assert hasattr(dev.uart_link_resp.pr, "fram") and dev.uart_link_resp.pr.fram is not None
    assert dev.uart_link_init.pr.fram is not dev.uart_link_resp.pr.fram


# ---------------------------------------------------------------------------
# Real transfers inside the real object graph
# ---------------------------------------------------------------------------


def test_a_get_and_a_set_both_complete_with_no_errors_counted() -> None:
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None and dev.uart_link_resp is not None
    initiator, responder = dev.uart_link_init._comm, dev.uart_link_resp._comm

    answer = run(exchange(initiator.uart_get(0x01)))
    assert answer is not None
    assert bytes(answer) == b"dev-uart-crossover"

    assert run(exchange(initiator.uart_set(0x02, b"round trip"))) is True

    for comm in (initiator, responder):
        counts = run(comm.get_error_counter())
        assert counts[comm.name]["ErrCount"] == 0, f"{comm.name} counted an error on a clean link"


def test_a_payload_larger_than_one_chunk_crosses_the_jumper_intact() -> None:
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None and dev.uart_link_resp is not None
    payload = bytes((i * 5) & 0xFF for i in range(140))  # spans three data chunks at payload_size 48
    assert run(exchange(dev.uart_link_init._comm.uart_set(0x02, payload))) is True
    # The responder's own _last_echo is only ever written by _message_callback, which
    # exchange()'s harness-controlled uart_listen() round does NOT invoke (see exchange()'s own
    # comment) - so this stays unset here, the same "the callback stores nothing itself" fact
    # main's own original test recorded, just checked against the real storage location now.
    assert dev.uart_link_resp._last_echo is None


def test_one_sided_silence_forces_a_resync_and_both_sides_recover() -> None:
    # The realistic one-sided fault, and the recovery the whole design exists for.
    link = build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None and dev.uart_link_resp is not None
    initiator, responder = dev.uart_link_init._comm, dev.uart_link_resp._comm
    direction = link.direction_from(fakes()[1])
    direction.silent = True
    assert run(exchange(initiator.uart_set(0x02, b"lost")), limit=60) is False
    assert initiator._holdoff_active is True

    direction.silent = False
    run(responder.clear(), limit=60)
    assert run(exchange(initiator.uart_set(0x02, b"back")), limit=60) is True


# ---------------------------------------------------------------------------
# Concurrency inside the real task graph
# ---------------------------------------------------------------------------


def test_a_transfer_does_not_starve_other_tasks() -> None:
    # Every wait in the protocol yields, so a maximum-length transfer must not stall the
    # Neopixel animation or a sensor trigger. A plain co-running ticker is the cheapest proof.
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None and dev.uart_link_resp is not None
    initiator = dev.uart_link_init._comm
    ticks = []

    async def ticker() -> None:
        while True:
            ticks.append(time.ticks_ms())
            await asyncio.sleep_ms(2)

    async def scenario() -> bool:
        background = asyncio.create_task(ticker())
        try:
            return await exchange(initiator.uart_set(0x02, bytes(240)))
        finally:
            background.cancel()

    assert run(scenario(), limit=60) is True
    assert len(ticks) > 5, "other tasks made no progress during the transfer"


def test_the_link_keeps_working_while_the_rest_of_the_graph_runs() -> None:
    # The link and the rest of the system have to coexist, not merely each work alone.
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None and dev.sysfunct is not None
    initiator = dev.uart_link_init._comm

    async def scenario() -> "list[Any]":
        noise = [asyncio.create_task(dev.sysfunct.get_uptime()) for _ in range(4)]  # type: ignore[union-attr]
        results = [await exchange(initiator.uart_get(0x01))]
        for task in noise:
            await task
        return results

    results = run(scenario(), limit=60)
    assert results[0] is not None


def test_a_forced_collection_mid_transfer_does_not_break_the_link() -> None:
    # timeout is sized well above the measured worst-case collection pause, so a GC landing
    # mid-frame must not read as an inter-part timeout.
    import gc

    build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None
    initiator = dev.uart_link_init._comm

    async def scenario() -> bool:
        async def collector() -> None:
            for _ in range(6):
                gc.collect()
                await asyncio.sleep_ms(3)

        background = asyncio.create_task(collector())
        try:
            return await exchange(initiator.uart_set(0x02, bytes(120)))
        finally:
            background.cancel()

    assert run(scenario(), limit=60) is True


def test_a_maximum_length_train_completes_and_still_yields() -> None:
    # The massive singular load: the longest transaction this protocol can express, 254 data chunks
    # at payload_size 48. One transfer, hundreds of stop-and-wait round trips - the case where a
    # single non-yielding step anywhere in the read or write path would be most visible.
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None
    initiator = dev.uart_link_init._comm
    payload = bytes((i * 7) & 0xFF for i in range(48 * 254))
    ticks = []  # unannotated, like the sibling ticker above: ticks_ms() is an opaque _TicksMs

    async def ticker() -> None:
        while True:
            ticks.append(time.ticks_ms())
            await asyncio.sleep_ms(2)

    async def scenario() -> bool:
        background = asyncio.create_task(ticker())
        try:
            return await exchange(initiator.uart_set(0x02, payload))
        finally:
            background.cancel()

    assert run(scenario(), limit=240) is True, "the maximum-length train did not complete"
    # Progress, not a rate: the ticker must have been scheduled throughout, which it cannot be if
    # any step held the loop for the whole transfer.
    assert len(ticks) > 50, f"other tasks ran only {len(ticks)} times across a 254-chunk transfer"
    counts = run(initiator.get_error_counter())
    assert counts[initiator.name]["ErrCount"] == 0, "the longest legal transfer logged an error"


def test_many_back_to_back_transfers_do_not_degrade_or_leak() -> None:
    # Massive repeated load rather than one big transfer: the counters, the UID space and the
    # buffers all have to survive being cycled, not just used once. The UID wraps at 0xFE, so this
    # deliberately runs past one whole wrap.
    import gc

    link = build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None
    initiator = dev.uart_link_init._comm
    rounds = 300
    fake_a, fake_b = fakes()

    def _clear_wire_logs() -> None:
        # The twin records every delivered byte in an unbounded wire_log. Over this many transfers
        # that is ~95kB of test instrumentation, which would otherwise be measured as the leak this
        # test is looking for - it is the harness growing, not the driver.
        link.direction_from(fake_a).wire_log = bytearray()
        link.direction_from(fake_b).wire_log = bytearray()

    async def scenario() -> "tuple[int, int]":
        _clear_wire_logs()
        gc.collect()
        before = gc.mem_free()
        ok = 0
        for i in range(rounds):
            if await exchange(initiator.uart_get(0x01)) is not None:
                ok += 1
            if not i % 20:
                _clear_wire_logs()
        _clear_wire_logs()
        gc.collect()
        return ok, before - gc.mem_free()

    ok, leaked = run(scenario(), limit=300)
    assert ok == rounds, f"only {ok}/{rounds} transfers succeeded across a full UID wrap"
    counts = run(initiator.get_error_counter())
    assert counts[initiator.name]["ErrCount"] == 0, f"{rounds} clean transfers logged an error"
    # Buffers are preallocated per instance, so a steady-state loop must not grow the heap. The
    # bound is generous - this asserts "no per-transfer leak", not an allocation budget.
    assert leaked < 8192, f"{leaked} bytes not reclaimed across {rounds} transfers - a per-transfer leak"


def test_the_link_survives_sustained_allocation_pressure() -> None:
    # Resource exhaustion rather than contention: a heap being churned hard underneath the link,
    # which is what turns a latent one-big-allocation design into a failure (Part I). The link must
    # either complete or degrade cleanly - never raise out, and never corrupt a payload.
    import gc

    build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None
    initiator = dev.uart_link_init._comm
    stop: list[bool] = []

    async def churn() -> None:
        held: list[bytearray] = []
        while not stop:
            try:
                held.append(bytearray(1024))
            except MemoryError:  # the pressure this test exists to create
                held = []
                gc.collect()
            if len(held) > 32:
                held = held[16:]
            await asyncio.sleep_ms(1)

    async def scenario() -> "list[bool]":
        background = asyncio.create_task(churn())
        try:
            out = []
            for _ in range(10):
                # The suppression below: MicroPython has no `await` inside a comprehension, so
                # ruff's suggested rewrite does not compile on the target interpreter at all.
                out.append(await exchange(initiator.uart_set(0x02, bytes(200))))  # noqa: PERF401
            return out
        finally:
            stop.append(True)
            background.cancel()
            await asyncio.sleep_ms(5)

    results = run(scenario(), limit=180)
    assert all(isinstance(r, bool) for r in results), "a transfer returned something other than its documented bool"
    assert any(results), "every transfer failed under allocation pressure - the link did not degrade, it stopped"


def _hammer_with_the_graph_running(threshold: int) -> None:
    # The combined case: the link hammered flat out while the rest of the real dev graph runs, with
    # the heap watched throughout. Run under MicroPython's own default (-1, no proactive
    # collection) as well as the project's chosen 32768, per CLAUDE.md's stress-test rule - a
    # hammer that only survives with proactive collection is hiding the defect the rule exists for.
    import gc

    link = build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None and dev.sysfunct is not None
    initiator = dev.uart_link_init._comm
    fake_a, fake_b = fakes()
    original = gc.threshold()
    gc.threshold(threshold)

    def clear_wire_logs() -> None:
        # The twin records every delivered byte in an unbounded wire_log - about 15kB over this
        # many transactions. That is the harness growing, not the driver, and measuring it as a
        # leak is exactly the mistake Part E.7 warns about.
        link.direction_from(fake_a).wire_log = bytearray()
        link.direction_from(fake_b).wire_log = bytearray()

    async def scenario() -> "tuple[int, int]":
        noise = [asyncio.create_task(_uptime_noise(dev)) for _ in range(3)]
        try:
            for _ in range(20):  # absorb one-time cost before the window opens
                await exchange(initiator.uart_get(0x01))
            clear_wire_logs()
            gc.collect()
            before = gc.mem_free()
            ok = 0
            for i in range(120):
                if await exchange(initiator.uart_get(0x01)) is not None:
                    ok += 1
                if not i % 20:
                    clear_wire_logs()
            clear_wire_logs()
            gc.collect()
            return ok, before - gc.mem_free()
        finally:
            for task in noise:
                task.cancel()
            await asyncio.sleep_ms(5)

    try:
        ok, leaked = run(scenario(), limit=300)
    finally:
        gc.threshold(original)
    assert ok == 120, f"only {ok}/120 hammered transactions completed at gc.threshold({threshold})"
    counts = run(initiator.get_error_counter())
    assert counts[initiator.name]["ErrCount"] == 0, f"errors logged under hammer at gc.threshold({threshold})"
    assert leaked < 8192, f"{leaked} bytes retained across 120 hammered transactions at gc.threshold({threshold})"


async def _uptime_noise(dev: "ModuleType") -> None:
    # A co-running consumer of the same event loop, so the hammer is never the only thing scheduled.
    while True:
        await dev.sysfunct.get_uptime()
        await asyncio.sleep_ms(1)


def test_hammering_the_link_beside_the_graph_holds_at_the_gc_default() -> None:
    _hammer_with_the_graph_running(-1)


def test_hammering_the_link_beside_the_graph_holds_at_the_chosen_gc_threshold() -> None:
    _hammer_with_the_graph_running(32768)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
