"""Twin-tier coverage for the UART crossover link (SPECIFICATION.md Part J.7): the real generated
sensortask_dev object graph on the twin's buses, its two UART peripherals joined across the bench
jumper, driving real transfers while the rest of the task graph runs."""

import asyncio
import json
import sys
import time

sys.path.insert(0, "ext")  # the real vendored ext/microdot.py sensortask_dev.py transitively imports
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why
sys.path.insert(0, "digital_twin/unixport")  # the UDP shim's directory (digital_twin/README.md "_unix_port_udp_addr_shim.py")

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

# Required of any entry point booting a sensortask_* module under the twin, and this file builds
# the real dev graph repeatedly: growing the Unix port's pollfds array corrupts non-fd poll
# objects already in it, and this driver registers exactly such an object per UART.
prewarm_poll_set()

# Must run before UDPSocket is constructed (CaptiveDNS, inside WifiService.__init__): this
# Unix-port build rejects a plain (host, port) tuple in bind()/connect()/sendto().
patch_asy_udp_socket_for_unix_port()

import rp2  # noqa: E402
import run_generic_integration  # noqa: E402
import sensortask_dev  # noqa: E402
from _error_codes import code  # noqa: E402
from _tmp_scratch import TmpScratch  # noqa: E402
from _uart_comm_harness import PollRoundClock, accept_set, copied_out, echo_get, transfer_limits  # noqa: E402
from machine import LinkPoller, UARTLink, configure_i2c_wiring  # noqa: E402

import asy_uart_comm  # noqa: E402
from asy_uart_comm import ROLE_RESPONDER, ResponderCallbacks, UARTComm  # noqa: E402

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
_DEV_WIRING_PLAN = "build/generated_src/sensortask_dev_wiring_plan.json"  # written by buildgen before any test runs

# @tunable l2.uart_link_run_limit_s = 30
_RUN_LIMIT_S = 30
# @tunable l2.uart_link_listener_settle_s = 5
_LISTENER_SETTLE_S = 5
# @tunable l2.uart_link_exchange_limit_s = 60
_EXCHANGE_LIMIT_S = 60
# @tunable l2.uart_link_ticker_step_ms = 2
_TICKER_STEP_MS = 2
# @tunable l2.uart_link_pause_step_ms = 3
_PAUSE_STEP_MS = 3
# @tunable l2.uart_link_pause_rounds = 6
_PAUSE_ROUNDS = 6
# The worst measured collection pause, mirrored from asy_uart_comm.py (a _-prefixed const() is no module attribute)
# @tunable uart.gc_pause_worst_ms = 21
_WORST_GC_PAUSE_MS = 21
# @tunable l2.uart_link_max_train_limit_s = 240
_MAX_TRAIN_LIMIT_S = 240
# A host stall past the link's 1000 ms reply timeout, after this many UART sleeps (mid-train: about 4350 in all)
_MAX_TRAIN_STALL_MS = 1100
_MAX_TRAIN_STALL_AFTER = 2000
# @tunable l2.uart_link_hammer_limit_s = 300
_HAMMER_LIMIT_S = 300
# @tunable l2.uart_link_leak_rounds = 300
_LEAK_ROUNDS = 300
# @tunable l2.uart_link_leak_budget_bytes = 8192
_LEAK_BUDGET_BYTES = 8192
# @tunable l2.uart_link_hammer_rounds = 120
_HAMMER_ROUNDS = 120
# @tunable l2.uart_link_hammer_warmup_rounds = 20
_HAMMER_WARMUP_ROUNDS = 20
# @tunable l2.uart_link_hammer_noise_consumers = 3
_HAMMER_NOISE_CONSUMERS = 3
# @tunable l2.uart_link_churn_step_ms = 1
_CHURN_STEP_MS = 1
# @tunable l2.uart_link_cancel_settle_ms = 5
_CANCEL_SETTLE_MS = 5
# @tunable l2.uart_link_churn_limit_s = 180
_CHURN_LIMIT_S = 180
# @tunable l2.uart_link_churn_transfers = 10
_CHURN_TRANSFERS = 10
# @tunable l2.uart_link_noise_step_ms = 1
_NOISE_STEP_MS = 1
# @tunable l2.uart_link_coexist_noise_tasks = 4
_COEXIST_NOISE_TASKS = 4


def _build_dev() -> None:
    configure_i2c_wiring("dev")  # dev's own chips: wozi's default plan puts an 8 KB FRAM under dev's 256 KB manager
    rp2.DMA.reset_registry()  # each build is a boot: the soft reset before it frees every DMA channel
    run(sensortask_dev.build_system(cfg_path=_tmp_cfg_dir()))
    dev = sensortask_dev
    assert dev.uart0 is not None and dev.uart1 is not None
    assert dev.uart_link_init is not None and dev.uart_link_resp is not None


def _claim_every_free_channel() -> "list[rp2.DMA]":
    # Stands in for the channels an earlier build's links still hold: twelve exist (rp2_dma.c:357-366).
    claimed = []
    while True:
        try:
            claimed.append(rp2.DMA())
        except OSError:
            return claimed


def _errnos(comm: UARTComm) -> "list[int]":
    # Errors only: ErrNum holds both kinds and ErrType tells them apart. Indexed, not zip()ed: MicroPython has no strict=.
    entry = run(comm.get_error_counter())[comm.name]
    nums, kinds = entry["ErrNum"], entry["ErrType"]
    return [nums[i] for i in range(len(nums)) if kinds[i] == "E"]


def _hammer_with_the_graph_running(threshold: int) -> None:
    # The combined case: the link hammered flat out while the rest of the real dev graph runs, with the heap
    # watched throughout. Run under MicroPython's own default (no proactive collection) as well as the
    # project's 32768 - a hammer that only survives with proactive collection hides the defect.
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
        link.direction_from(fake_a).wire_log.clear()
        link.direction_from(fake_b).wire_log.clear()

    async def scenario() -> "tuple[int, int]":
        noise = [asyncio.create_task(_uptime_noise(dev)) for _ in range(_HAMMER_NOISE_CONSUMERS)]
        try:
            for _ in range(_HAMMER_WARMUP_ROUNDS):  # absorb one-time cost before the window opens
                await exchange(initiator.uart_get(0x01))
            clear_wire_logs()
            gc.collect()
            before = gc.mem_free()
            ok = 0
            for i in range(_HAMMER_ROUNDS):
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
            await asyncio.sleep_ms(_CANCEL_SETTLE_MS)

    try:
        ok, leaked = run(scenario(), limit=_HAMMER_LIMIT_S)
    finally:
        gc.threshold(original)
    assert ok == _HAMMER_ROUNDS, f"only {ok}/{_HAMMER_ROUNDS} hammered transactions completed at gc.threshold({threshold})"
    counts = run(initiator.get_error_counter())
    assert counts[initiator.name]["ErrCount"] == 0, f"errors logged under hammer at gc.threshold({threshold})"
    assert leaked < _LEAK_BUDGET_BYTES, f"{leaked} bytes retained across {_HAMMER_ROUNDS} hammered transactions at gc.threshold({threshold})"


async def _settle_listener(listener: "asyncio.Task[Any]") -> None:
    try:
        await asyncio.wait_for(listener, _LISTENER_SETTLE_S)
    except asyncio.TimeoutError:
        listener.cancel()
        try:
            await listener
        except asyncio.CancelledError:  # the expected outcome; anything else is a real failure
            pass


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


async def _uptime_noise(dev: "ModuleType") -> None:
    # A co-running consumer of the same event loop, so the hammer is never the only thing scheduled.
    while True:
        await dev.sysfunct.get_uptime()
        await asyncio.sleep_ms(_NOISE_STEP_MS)


def build_linked_system() -> "TwinLink":
    # The real dev object graph, its two UART peripherals joined the way the bench jumper joins
    # them (GP0<->GP9, GP1<->GP8). The pollers are then swapped for the bounded stand-in: a real
    # select.poll() never re-checks a Python object's ioctl(), so readiness would never be seen.
    _build_dev()
    dev = sensortask_dev
    assert dev.uart0 is not None and dev.uart1 is not None
    fake_a, fake_b = fakes()
    link = UARTLink(fake_a, fake_b)
    dev.uart0.poller = LinkPoller(fake_a)  # type: ignore[assignment]
    dev.uart1.poller = LinkPoller(fake_b)  # type: ignore[assignment]
    return link


async def exchange(work: "Coroutine[Any, Any, T]") -> "T":
    # The initiator's call returning does not mean the responder is finished: it still has its last
    # read to complete, and the twin delivers by real wire time. Cutting the listener off would
    # strand a frame for the next exchange - a harness artefact, so the harness waits it out.
    #
    # Drives the responder's own UARTComm.uart_listen() directly rather than UARTLinkDriver's real
    # listen-loop task, deliberately, so this file's callback-storage assertions go through the harness's
    # controlled single round instead of a free-running task.
    #
    # UARTLinkDriver's own message dispatch is covered separately by tests/test_asy_uart_link_driver.py's
    # echo-round-trip test, which drives the real task instead.
    dev = sensortask_dev
    assert dev.uart_link_resp is not None
    listener = asyncio.create_task(dev.uart_link_resp._comm.uart_listen())
    try:
        return await work
    finally:
        await _settle_listener(listener)


def fakes() -> "tuple[TwinUART, TwinUART]":
    # The twin machine.UART objects behind the two drivers. Narrowed in one place: every call site
    # would otherwise repeat the same pair of None checks the module-level globals require.
    dev = sensortask_dev
    assert dev.uart0 is not None and dev.uart1 is not None
    fake_a, fake_b = dev.uart0._uart, dev.uart1._uart
    assert fake_a is not None and fake_b is not None
    return fake_a, fake_b


def run(coro: "Coroutine[Any, Any, T]", limit: int = _RUN_LIMIT_S, clock: "PollRoundClock | None" = None) -> "T":
    # Every run on the poll-round clock (SPECIFICATION.md J.7): both ends share this interpreter, so on the wall
    # clock a host stall would spend the peer's reply budget and fail a correct link.
    with clock if clock is not None else PollRoundClock():
        return asyncio.run(asyncio.wait_for(coro, limit))


def test_every_build_starts_with_every_dma_channel_free() -> None:
    # A process that rebuilds dev's graph would otherwise run out of channels on its third build,
    # each link claiming two in its setup; four builds, each after every channel was taken.
    for _ in range(4):
        stale = _claim_every_free_channel()
        assert stale, "no channel was free to plant before this build"
        build_linked_system()
        assert all(channel.channel == 0xFF for channel in stale), "a channel held before the build was still claimed after it"


# ---------------------------------------------------------------------------
# The dev wiring itself
# ---------------------------------------------------------------------------


def test_the_generic_runner_joins_the_two_buses_its_wiring_plan_names() -> None:
    # The twin runner wires dev's jumper from the generated plan's "uart" key alone: the two bus globals it names.
    _build_dev()
    with open(_DEV_WIRING_PLAN) as f:
        plan = json.load(f)
    link = run_generic_integration._wire_uart_crossover(sensortask_dev, plan)
    assert link is not None, "the runner wired no link for dev's uart_link pair"
    assert link.endpoints == fakes(), "the runner joined other UARTs than dev's two buses"
    assert sensortask_dev.uart_link_init is not None
    answer = run(exchange(sensortask_dev.uart_link_init._comm.uart_get(0x01)))
    assert copied_out(answer) == b"dev-uart-crossover", "the runner's jumper carried no banner"


def test_both_instances_are_constructed_and_registered() -> None:
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None and dev.uart_link_resp is not None
    sources = dev._collect_error_sources()
    # get_error_sources() delegates entirely to the inner UARTComm (asy_uart_link_driver.py's own
    # comment) - the flattened error_sources list holds each _comm, not the UARTLinkDriver wrapper.
    assert dev.uart_link_init._comm in sources
    assert dev.uart_link_resp._comm in sources
    setters = dev._collect_level_setters()
    assert dev.uart_link_init.pr.set_level in setters or len(setters) > 0
    assert dev.uart_link_resp.get_task_starters()  # the responder owns the listen task
    # The initiator's own task list is its exercise loop (asy_uart_link_driver.py), not empty the
    # way bare UARTComm.get_task_starters() would be for an initiator role - one entry, not zero.
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
    assert initiator._payload_size == responder._payload_size
    assert initiator._timeout == responder._timeout
    assert initiator._frame_size == responder._frame_size


def test_the_two_ends_sit_on_distinct_peripherals_with_sized_buffers() -> None:
    # Both on one id would re-init the first's peripheral and leave one link object silently
    # owning nothing. a default-sized rxbuf drops a frame's tail at this payload size.
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart0 is not None and dev.uart1 is not None
    fake_a, fake_b = fakes()
    assert fake_a.id != fake_b.id
    frame_size = dev.uart_link_init._comm._frame_size  # type: ignore[union-attr]
    for driver in (dev.uart0, dev.uart1):
        assert driver.rxbuf >= frame_size
        assert driver.poll_wait_ms < 10  # single-digit, or poll latency dominates throughput


def test_both_ends_get_their_own_real_fram_chunk() -> None:
    # FRAMManager is a bump-pointer allocator, so instantiation order IS the on-chip layout of this
    # build. dev.toml wires fram_target on both uart_link instances (WP3), each with its own chunk - a
    # shared one would merge two links' histories.
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
    assert copied_out(answer) == b"dev-uart-crossover"

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
    # The responder's _last_echo is only ever written by _message_callback, which exchange()'s harness-
    # controlled uart_listen() round does not invoke - so it stays unset here, the same "the callback stores
    # nothing itself" fact the original test recorded, now checked against the real storage location.
    assert dev.uart_link_resp._last_echo is None


def test_one_sided_silence_forces_a_resync_and_both_sides_recover() -> None:
    # The realistic one-sided fault, and the recovery the whole design exists for.
    link = build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None and dev.uart_link_resp is not None
    initiator, responder = dev.uart_link_init._comm, dev.uart_link_resp._comm
    direction = link.direction_from(fakes()[1])
    direction.silent = True
    assert run(exchange(initiator.uart_set(0x02, b"lost")), limit=_EXCHANGE_LIMIT_S) is False
    assert initiator._holdoff_active is True

    direction.silent = False
    run(responder.clear(), limit=_EXCHANGE_LIMIT_S)
    assert run(exchange(initiator.uart_set(0x02, b"back")), limit=_EXCHANGE_LIMIT_S) is True


def test_a_payload_size_mismatch_is_diagnosed_as_unintelligible() -> None:
    # A responder whose payload_size is 8 over its peer's, on dev's own jumpered buses at real wire time: each frame dies
    # inside its failing read, so only the bytes that read dropped can raise the mismatch diagnostic (J.6).
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart1 is not None and dev.uart_link_init is not None
    initiator = dev.uart_link_init._comm
    limits = transfer_limits(payload_size=initiator._payload_size + 8, timeout=initiator._timeout)
    callbacks = ResponderCallbacks(echo_get(b"v"), accept_set(), None)
    responder = UARTComm(dev.uart1, ROLE_RESPONDER, limits=limits, callbacks=callbacks, name="UART_MISMATCH")
    assert run(responder.setup()) is True

    async def scenario() -> None:
        for _ in range(4):  # the diagnostic waits for a streak of resyncs, so one failed exchange must not trip it
            listener = asyncio.create_task(responder.uart_listen())
            await initiator.uart_set(0x02, b"nonsense")
            await responder.clear()
            await _settle_listener(listener)

    run(scenario(), limit=_EXCHANGE_LIMIT_S)
    unintelligible = code("E", "UART_LINK_UNINTELLIGIBLE")
    responder_codes, initiator_codes = _errnos(responder), _errnos(initiator)
    assert unintelligible in responder_codes, f"the mismatched responder never reported the link unintelligible: {responder_codes}"
    assert code("E", "UART_NO_ACK") in initiator_codes, f"the initiator never reported its missing acknowledgements: {initiator_codes}"
    assert unintelligible not in initiator_codes, f"the initiator, which received nothing, reported the link unintelligible: {initiator_codes}"


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
            await asyncio.sleep_ms(_TICKER_STEP_MS)

    async def scenario() -> bool:
        background = asyncio.create_task(ticker())
        try:
            return await exchange(initiator.uart_set(0x02, bytes(240)))
        finally:
            background.cancel()

    assert run(scenario(), limit=_EXCHANGE_LIMIT_S) is True
    assert len(ticks) > 5, "other tasks made no progress during the transfer"


def test_the_link_keeps_working_while_the_rest_of_the_graph_runs() -> None:
    # The link and the rest of the system have to coexist, not merely each work alone.
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None and dev.sysfunct is not None
    initiator = dev.uart_link_init._comm

    async def scenario() -> "list[Any]":
        noise = [asyncio.create_task(dev.sysfunct.get_uptime()) for _ in range(_COEXIST_NOISE_TASKS)]  # type: ignore[union-attr]
        results = [await exchange(initiator.uart_get(0x01))]
        for task in noise:
            await task
        return results

    results = run(scenario(), limit=_EXCHANGE_LIMIT_S)
    assert results[0] is not None


def test_a_collection_length_pause_mid_transfer_does_not_break_the_link() -> None:
    # A synchronous stop-the-world pause the length of the worst measured collection (Part I): the tested
    # property - a pause mid-frame is not an inter-part timeout - without depending on today's heap.
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None
    initiator = dev.uart_link_init._comm

    async def scenario() -> bool:
        async def pauser() -> None:
            for _ in range(_PAUSE_ROUNDS):
                time.sleep_ms(_WORST_GC_PAUSE_MS)  # no task runs, as in a collection; the wire keeps delivering
                for _ in range(_WORST_GC_PAUSE_MS):  # and the deadlines see it: the run's clock reads 1 ms per call
                    asy_uart_comm.time.ticks_ms()  # type: ignore[attr-defined]
                await asyncio.sleep_ms(_PAUSE_STEP_MS)

        background = asyncio.create_task(pauser())
        try:
            return await exchange(initiator.uart_set(0x02, bytes(120)))
        finally:
            background.cancel()

    assert run(scenario(), limit=_EXCHANGE_LIMIT_S) is True


def test_a_maximum_length_train_completes_and_still_yields() -> None:
    # The massive singular load: the longest transaction this protocol can express, 254 data chunks at payload_size 48,
    # where one non-yielding step in the read or write path would be most visible. A host stall past the 1000 ms reply
    # timeout lands mid-train: the deadlines count poll rounds.
    build_linked_system()
    dev = sensortask_dev
    assert dev.uart_link_init is not None
    initiator = dev.uart_link_init._comm
    payload = bytes((i * 7) & 0xFF for i in range(48 * 254))
    ticks = []  # unannotated, like the sibling ticker above: ticks_ms() is an opaque _TicksMs

    async def ticker() -> None:
        while True:
            ticks.append(time.ticks_ms())
            await asyncio.sleep_ms(_TICKER_STEP_MS)

    async def scenario() -> bool:
        background = asyncio.create_task(ticker())
        try:
            return await exchange(initiator.uart_set(0x02, payload))
        finally:
            background.cancel()

    clock = PollRoundClock(stall_after=_MAX_TRAIN_STALL_AFTER, stall_ms=_MAX_TRAIN_STALL_MS)
    clock.arm()
    completed = run(scenario(), limit=_MAX_TRAIN_LIMIT_S, clock=clock)
    assert clock.disarm(), "the planted host stall never fired: the train did not reach it"
    assert completed is True, "the maximum-length train did not complete"
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
    rounds = _LEAK_ROUNDS
    fake_a, fake_b = fakes()

    def _clear_wire_logs() -> None:
        # The twin keeps up to 4 KB of delivered bytes per direction in wire_log: test instrumentation
        # that would otherwise be measured as the leak this test is looking for - the harness growing
        # to its cap, not the driver.
        link.direction_from(fake_a).wire_log.clear()
        link.direction_from(fake_b).wire_log.clear()

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

    ok, leaked = run(scenario(), limit=_HAMMER_LIMIT_S)
    assert ok == rounds, f"only {ok}/{rounds} transfers succeeded across a full UID wrap"
    counts = run(initiator.get_error_counter())
    assert counts[initiator.name]["ErrCount"] == 0, f"{rounds} clean transfers logged an error"
    # Buffers are preallocated per instance, so a steady-state loop must not grow the heap. The
    # bound is generous - this asserts "no per-transfer leak", not an allocation budget.
    assert leaked < _LEAK_BUDGET_BYTES, f"{leaked} bytes not reclaimed across {rounds} transfers - a per-transfer leak"


def test_the_link_survives_sustained_allocation_pressure() -> None:
    # Resource exhaustion rather than contention: a heap being churned hard underneath the link,
    # which is what turns a latent one-big-allocation design into a failure (Part I). The link must
    # either complete or degrade cleanly - never raise out, and never corrupt a payload.
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
            if len(held) > 32:
                held = held[16:]
            await asyncio.sleep_ms(_CHURN_STEP_MS)

    async def scenario() -> "list[bool]":
        background = asyncio.create_task(churn())
        try:
            out = []
            for _ in range(_CHURN_TRANSFERS):
                # The suppression below: MicroPython has no `await` inside a comprehension, so
                # ruff's suggested rewrite does not compile on the target interpreter at all.
                out.append(await exchange(initiator.uart_set(0x02, bytes(200))))  # noqa: PERF401
            return out
        finally:
            stop.append(True)
            background.cancel()
            await asyncio.sleep_ms(_CANCEL_SETTLE_MS)

    results = run(scenario(), limit=_CHURN_LIMIT_S)
    assert all(isinstance(r, bool) for r in results), "a transfer returned something other than its documented bool"
    assert any(results), "every transfer failed under allocation pressure - the link did not degrade, it stopped"


def test_hammering_the_link_beside_the_graph_holds_at_the_gc_default() -> None:
    _hammer_with_the_graph_running(-1)


def test_hammering_the_link_beside_the_graph_holds_at_the_chosen_gc_threshold() -> None:
    # @tunable gc.threshold_bytes = 32768
    _hammer_with_the_graph_running(32768)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
