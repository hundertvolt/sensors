"""Twin-tier coverage of the generated UART crossover link (SPECIFICATION.md J.7) on the device tests/_twin_devices.py
finds wiring a uart_link pair, its two peripherals joined as the bench jumper joins them, plus pair-level CRC16 and
mismatch cases."""

import asyncio
import sys
import time

sys.path.insert(0, "ext")  # the real vendored ext/microdot.py every generated device module transitively imports
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why
sys.path.insert(0, "digital_twin/unixport")  # the UDP shim's directory (digital_twin/README.md "_unix_port_udp_addr_shim.py")

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

# Required of any entry point booting a sensortask_* module under the twin, and this file builds
# the device's real graph repeatedly: growing the Unix port's pollfds array corrupts non-fd poll
# objects already in it, and this driver registers exactly such an object per UART.
prewarm_poll_set()

# Must run before UDPSocket is constructed (CaptiveDNS, inside WifiService.__init__): this
# Unix-port build rejects a plain (host, port) tuple in bind()/connect()/sendto().
patch_asy_udp_socket_for_unix_port()

import machine  # noqa: E402 - imported after the prewarm and the UDP shim
import microtest  # noqa: E402 - imported after the prewarm and the UDP shim
import network  # noqa: E402 - imported after the prewarm and the UDP shim
import rp2  # noqa: E402 - imported after the prewarm and the UDP shim
import run_generic_integration  # noqa: E402 - imported after the prewarm and the UDP shim
from _async_harness import cancel_all, run  # noqa: E402 - imported after the prewarm and the UDP shim
from _digital_twin_construction_scenarios import load_device  # noqa: E402 - imported after the prewarm and the UDP shim
from _error_codes import code  # noqa: E402 - imported after the prewarm and the UDP shim
from _offline_ntp_config import write_offline_ntp_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _src_const import src_bytes  # noqa: E402 - imported after the prewarm and the UDP shim
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_devices import device_with, wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim
from _uart_comm_harness import PollRoundClock, accept_set, copied_out, echo_get, transfer_limits  # noqa: E402 - imported after the prewarm and the UDP shim
from machine import WDT, LinkPoller, UARTLink  # noqa: E402 - imported after the prewarm and the UDP shim

import asy_uart_comm  # noqa: E402 - imported after the prewarm and the UDP shim
import asy_uart_driver  # noqa: E402 - imported after the prewarm and the UDP shim
import asy_uart_link_driver  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_crc_checks import CRC16  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_uart_comm import ROLE_INITIATOR, ROLE_RESPONDER, ResponderCallbacks, TransferLimits, UARTComm  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_uart_link_driver import UARTLinkDriver  # noqa: E402 - imported after the prewarm and the UDP shim

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import TypeVar

    T = TypeVar("T")

    from launch import _Plan
    from machine import UART as TwinUART
    from machine import UARTLink as TwinLink

    from asy_base_classes import PieceBuffer

# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that module's
# own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("twin_uart")
microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)
_DEVICE = device_with("uart_link")
module = load_device(_DEVICE)
_BUSES = wiring_plan(_DEVICE)["uart"]  # the two bus globals the plan names: "initiator_bus" and "responder_bus"
assert _BUSES is not None, f"{_DEVICE}'s plan wires no uart pair"
_ends: "dict[str, UARTLinkDriver]" = {}
# Each end's (port, tx, rx, bus, role, limits), read once off the latest build for the CRC16 pairs.
_specs: "list[tuple[int, int, int, asy_uart_driver.UART, str, TransferLimits]]" = []
_BANNER: bytes = src_bytes("src/asy_uart_link_driver.py", "_BANNER")

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
# @tunable l2.uart_link_leak_warmup_rounds = 20
_LEAK_WARMUP_ROUNDS = 20
# Heap retained per transfer, read after a collection at two transfer counts: a rate, never an absolute delta. Calibrated
# on the Unix port (agent, 2026-10-14): at most 0.6 B clean, 78 B with a planted 16-byte-per-transfer leak.
# @tunable l2.uart_link_leak_rate_bytes_per_transfer = 16
_LEAK_RATE_BYTES_PER_TRANSFER = 16
# @tunable l2.uart_link_crc16_rounds = 3
_CRC16_ROUNDS = 3
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


async def _boot_device(cfg_path: str) -> None:
    # The generated main()'s first two steps: build_system() with the watchdog a boot entry arms, then the setup list.
    write_offline_ntp_config(cfg_path)
    await module.build_system(watchdog=WDT(timeout=run_generic_integration._WDT_TIMEOUT_MS), cfg_path=cfg_path)
    await module.sysfunct.run_setups(module._collect_setups())


def _build_device() -> None:
    machine.reset_peripherals()  # each build is a new board: fresh buses and chips on the device's own plan
    network.reset_interfaces()
    machine.configure_wiring(wiring_plan(_DEVICE))
    rp2.DMA.reset_registry()  # each build is a boot: the soft reset before it frees every DMA channel
    _run(_boot_device(_tmp_cfg_dir()))
    _ends.clear()  # this build's two link ends, found once here rather than on every exchange
    for role in (ROLE_INITIATOR, ROLE_RESPONDER):
        found = [value for value in (getattr(module, name) for name in dir(module)) if isinstance(value, UARTLinkDriver) and value._role == role]
        assert len(found) == 1, f"{_DEVICE} builds {len(found)} {role} link drivers, not one"
        _ends[role] = found[0]


def _bus(role_bus: str) -> "asy_uart_driver.UART":
    # The bus global the plan's "uart" key names for "initiator_bus" or "responder_bus".
    assert _BUSES is not None
    bus = getattr(module, _BUSES[role_bus])  # type: ignore[literal-required]  # one of the pair's two keys
    assert isinstance(bus, asy_uart_driver.UART), (role_bus, bus)
    return bus


def _claim_every_free_channel() -> "list[rp2.DMA]":
    # Stands in for the channels an earlier build's links still hold: twelve exist (rp2_dma.c:357-366).
    claimed = []
    while True:
        try:
            claimed.append(rp2.DMA())
        except OSError:
            return claimed


class _BackToBack:
    # asy_uart_link_driver's asyncio with every sleep a bare yield: what the exerciser uses of it, nothing more.
    get_event_loop = staticmethod(asyncio.get_event_loop)

    @staticmethod
    async def sleep_ms(_ms: int) -> None:
        await asyncio.sleep_ms(0)


def _crc16_pair() -> "tuple[UARTLinkDriver, UARTLinkDriver, TwinLink]":
    # The device's two link ends rebuilt over CRC16 buses on a new board, every bus and link parameter read off its
    # build, joined as the jumper joins them with bounded pollers; set up at synchronous scope (CLAUDE.md, asyncio.run()).
    if not _specs:
        if not _ends:  # no earlier test built the device: its parameters need one build
            build_linked_system()
        for key, role in (("initiator_bus", ROLE_INITIATOR), ("responder_bus", ROLE_RESPONDER)):
            bus, comm = _bus(key), _link(role)._comm
            fake = bus._uart
            assert fake is not None
            limits = TransferLimits(comm._payload_size, comm._timeout, comm._chunk_bytes, comm._max_transfer_bytes)
            _specs.append((fake.id, fake.tx.id, fake.rx.id, bus, role, limits))
    machine.reset_peripherals()
    rp2.DMA.reset_registry()
    buses, ends = [], []
    for port, tx, rx, bus, role, limits in _specs:
        crc_bus = asy_uart_driver.UART(port, tx, rx, baudrate=bus.baudrate, rxbuf=bus.rxbuf, txbuf=bus._txbuf, rx_ring=bus.rx_ring, poll_wait_ms=bus.poll_wait_ms, poll_idle_ms=bus.poll_idle_ms, crc=CRC16())
        buses.append(crc_bus)
        ends.append(UARTLinkDriver(crc_bus, role, limits=limits, name_ext=role))
    fake_a, fake_b = buses[0]._uart, buses[1]._uart
    assert fake_a is not None and fake_b is not None
    link = UARTLink(fake_a, fake_b)
    buses[0].poller = LinkPoller(fake_a)  # type: ignore[assignment]
    buses[1].poller = LinkPoller(fake_b)  # type: ignore[assignment]
    initiator, responder = ends
    assert _run(initiator.setup()) is True and _run(responder.setup()) is True
    return initiator, responder, link


def _errnos(comm: UARTComm) -> "list[int]":
    # Errors only: ErrNum holds both kinds and ErrType tells them apart. Indexed, not zip()ed: MicroPython has no strict=.
    entry = _run(comm.get_error_counter())[comm.name]
    nums, kinds = entry["ErrNum"], entry["ErrType"]
    return [nums[i] for i in range(len(nums)) if kinds[i] == "E"]


async def _exercised(initiator: UARTLinkDriver, responder: UARTLinkDriver, done: "Callable[[], bool]") -> None:
    # The pair's own loops, started as a boot starts them (the responder's listen, the initiator's exercise), until `done`.
    tasks = [start() for start in responder.get_task_starters() + initiator.get_task_starters()]
    try:
        while not done():
            await asyncio.sleep_ms(_TICKER_STEP_MS)
    finally:
        await cancel_all(tasks)


def _hammer_with_the_graph_running(threshold: int) -> None:
    # The combined case: the link hammered flat out while the rest of the device's real graph runs, with the heap
    # watched throughout. Run under MicroPython's own default (no proactive collection) as well as the
    # project's 32768 - a hammer that only survives with proactive collection hides the defect.
    import gc

    link = build_linked_system()
    assert module.sysfunct is not None
    initiator = _link(ROLE_INITIATOR)._comm
    fake_a, fake_b = fakes()
    original = gc.threshold()
    gc.threshold(threshold)

    def clear_wire_logs() -> None:
        # The twin records every delivered byte in an unbounded wire_log - about 15kB over this
        # many transactions. That is the harness growing, not the driver, and measuring it as a
        # leak is exactly the mistake Part E.7 warns about.
        link.direction_from(fake_a).wire_log.clear()
        link.direction_from(fake_b).wire_log.clear()

    async def hammered(rounds: int) -> int:
        noise = [asyncio.create_task(_uptime_noise()) for _ in range(_HAMMER_NOISE_CONSUMERS)]
        try:
            ok = 0
            for i in range(rounds):
                if await exchange(initiator.uart_get(0x01)) is not None:
                    ok += 1
                if not i % 20:
                    clear_wire_logs()
            return ok
        finally:
            for task in noise:
                task.cancel()
            await asyncio.sleep_ms(_CANCEL_SETTLE_MS)

    # The warm-up absorbs one-time cost; the window is its own run, so the heap is read with no run's task record held.
    try:
        _run(hammered(_HAMMER_WARMUP_ROUNDS), limit=_HAMMER_LIMIT_S)
        clear_wire_logs()
        gc.collect()
        free_n1 = gc.mem_free()
        ok = _run(hammered(_HAMMER_ROUNDS), limit=_HAMMER_LIMIT_S)
        clear_wire_logs()
        gc.collect()
        rate = (free_n1 - gc.mem_free()) / _HAMMER_ROUNDS
    finally:
        gc.threshold(original)
    assert ok == _HAMMER_ROUNDS, f"only {ok}/{_HAMMER_ROUNDS} hammered transactions completed at gc.threshold({threshold})"
    counts = _run(initiator.get_error_counter())
    assert counts[initiator.name]["ErrCount"] == 0, f"errors logged under hammer at gc.threshold({threshold})"
    assert rate < _LEAK_RATE_BYTES_PER_TRANSFER, f"{rate:.1f} bytes retained per hammered transaction at gc.threshold({threshold})"


def _link(role: str) -> UARTLinkDriver:
    # The last build's one UART link driver of `role`.
    return _ends[role]


def _run(coro: "Coroutine[object, object, T]", limit: int = _RUN_LIMIT_S, clock: "PollRoundClock | None" = None) -> "T":
    # Every run on the poll-round clock (SPECIFICATION.md J.7): both ends share this interpreter, so on the wall
    # clock a host stall would spend the peer's reply budget and fail a correct link.
    with clock if clock is not None else PollRoundClock():
        return run(coro, limit)


async def _settle_listener(listener: "asyncio.Task[object]") -> None:
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


def _traces(comm: UARTComm) -> "set[tuple[str, int]]":
    # Every error and warning kind the comm's history holds, as (ErrType, ErrNum).
    entry = _run(comm.get_error_counter())[comm.name]
    nums, kinds = entry["ErrNum"], entry["ErrType"]
    return {(kinds[i], nums[i]) for i in range(len(nums)) if kinds[i] != "N"}


async def _uptime_noise() -> None:
    # A co-running consumer of the same event loop, so the hammer is never the only thing scheduled.
    while True:
        await module.sysfunct.get_uptime()
        await asyncio.sleep_ms(_NOISE_STEP_MS)


def build_linked_system() -> "TwinLink":
    # The device's real object graph, its two UART peripherals joined the way the bench jumper joins them (each TX to
    # the other's RX), its pollers swapped for the twin's own LinkPoller.
    # Bounded stand-in, never a real select.poll(): the fake's readiness must be scripted, not polled in real time (CLAUDE.md "Known hang cause").
    _build_device()
    fake_a, fake_b = fakes()
    link = UARTLink(fake_a, fake_b)
    _bus("initiator_bus").poller = LinkPoller(fake_a)  # type: ignore[assignment]
    _bus("responder_bus").poller = LinkPoller(fake_b)  # type: ignore[assignment]
    return link


async def exchange(work: "Coroutine[object, object, T]") -> "T":
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
    listener = asyncio.create_task(_link(ROLE_RESPONDER)._comm.uart_listen())
    try:
        return await work
    finally:
        await _settle_listener(listener)


def fakes() -> "tuple[TwinUART, TwinUART]":
    # The twin machine.UART objects behind the two drivers. Narrowed in one place: every call site
    # would otherwise repeat the same pair of None checks the module-level globals require.
    fake_a, fake_b = _bus("initiator_bus")._uart, _bus("responder_bus")._uart
    assert fake_a is not None and fake_b is not None
    return fake_a, fake_b


def test_every_build_starts_with_every_dma_channel_free() -> None:
    # A process that rebuilds the device's graph would otherwise run out of channels on its third build,
    # each link claiming two in its setup; four builds, each after every channel was taken.
    for _ in range(4):
        stale = _claim_every_free_channel()
        assert stale, "no channel was free to plant before this build"
        build_linked_system()
        assert all(channel.channel == 0xFF for channel in stale), "a channel held before the build was still claimed after it"


# ---------------------------------------------------------------------------
# The device's wiring itself
# ---------------------------------------------------------------------------


def test_the_generic_runner_joins_the_two_buses_its_wiring_plan_names() -> None:
    # The twin runner wires the device's jumper from the generated plan's "uart" key alone: the two bus globals it names.
    _build_device()
    plan: _Plan = cast("_Plan", wiring_plan(_DEVICE))
    link = run_generic_integration._wire_uart_crossover(module, plan)
    assert link is not None, "the runner wired no link for the device's uart_link pair"
    assert link.endpoints == fakes(), "the runner joined other UARTs than the device's two buses"
    answer = _run(exchange(_link(ROLE_INITIATOR)._comm.uart_get(0x01)))
    assert copied_out(answer) == _BANNER, "the runner's jumper carried no banner"


def test_both_instances_are_constructed_and_registered() -> None:
    build_linked_system()
    sources = module._collect_error_sources()
    # get_error_sources() delegates entirely to the inner UARTComm (asy_uart_link_driver.py's own
    # comment) - the flattened error_sources list holds each _comm, not the UARTLinkDriver wrapper.
    assert _link(ROLE_INITIATOR)._comm in sources
    assert _link(ROLE_RESPONDER)._comm in sources
    setters = module._collect_level_setters()
    assert _link(ROLE_INITIATOR).pr.set_level in setters or len(setters) > 0
    assert _link(ROLE_RESPONDER).get_task_starters()  # the responder owns the listen task
    # The initiator's own task list is its exercise loop (asy_uart_link_driver.py), not empty the
    # way bare UARTComm.get_task_starters() would be for an initiator role - one entry, not zero.
    assert len(_link(ROLE_INITIATOR).get_task_starters()) == 1


def test_the_two_instances_have_distinct_names_and_loggers() -> None:
    # A shared logger would merge two links' histories into a single /status entry and
    # make a fault unattributable to an end.
    build_linked_system()
    assert _link(ROLE_INITIATOR).name != _link(ROLE_RESPONDER).name
    assert _link(ROLE_INITIATOR).pr is not _link(ROLE_RESPONDER).pr
    assert _link(ROLE_INITIATOR).name == _link(ROLE_INITIATOR).pr.name
    assert _link(ROLE_RESPONDER).name == _link(ROLE_RESPONDER).pr.name


def test_both_instances_share_one_set_of_protocol_parameters() -> None:
    # payload_size and timeout are out-of-band agreements that must match on both ends,
    # and nothing is negotiated - a mismatch desyncs the link outright and cannot self-heal.
    build_linked_system()
    initiator, responder = _link(ROLE_INITIATOR)._comm, _link(ROLE_RESPONDER)._comm
    assert initiator._payload_size == responder._payload_size
    assert initiator._timeout == responder._timeout
    assert initiator._frame_size == responder._frame_size


def test_the_two_ends_sit_on_distinct_peripherals_with_sized_buffers() -> None:
    # Both on one id would re-init the first's peripheral and leave one link object silently
    # owning nothing. a default-sized rxbuf drops a frame's tail at this payload size.
    build_linked_system()
    fake_a, fake_b = fakes()
    assert fake_a.id != fake_b.id
    frame_size = _link(ROLE_INITIATOR)._comm._frame_size
    for driver in (_bus("initiator_bus"), _bus("responder_bus")):
        assert driver.rxbuf >= frame_size
        assert driver.poll_wait_ms < 10  # single-digit, or poll latency dominates throughput


def test_both_ends_get_their_own_real_fram_chunk() -> None:
    # FRAMManager is a bump-pointer allocator, so instantiation order IS the on-chip layout of this
    # build. The device's TOML wires fram_target on both uart_link instances (WP3), each with its own chunk - a
    # shared one would merge two links' histories.
    build_linked_system()
    assert module.fram is not None
    initiator_fram, responder_fram = (getattr(_link(role).pr, "fram", None) for role in (ROLE_INITIATOR, ROLE_RESPONDER))
    assert initiator_fram is not None and responder_fram is not None and initiator_fram is not responder_fram


# ---------------------------------------------------------------------------
# Real transfers inside the real object graph
# ---------------------------------------------------------------------------


def test_a_get_and_a_set_both_complete_with_no_errors_counted() -> None:
    build_linked_system()
    initiator, responder = _link(ROLE_INITIATOR)._comm, _link(ROLE_RESPONDER)._comm

    answer = _run(exchange(initiator.uart_get(0x01)))
    assert copied_out(answer) == _BANNER

    assert _run(exchange(initiator.uart_set(0x02, b"round trip"))) is True

    for comm in (initiator, responder):
        counts = _run(comm.get_error_counter())
        assert counts[comm.name]["ErrCount"] == 0, f"{comm.name} counted an error on a clean link"


def test_a_payload_larger_than_one_chunk_crosses_the_jumper_intact() -> None:
    build_linked_system()
    payload = bytes((i * 5) & 0xFF for i in range(140))  # spans three data chunks at payload_size 48
    assert _run(exchange(_link(ROLE_INITIATOR)._comm.uart_set(0x02, payload))) is True
    # The responder's _last_echo is only ever written by _message_callback, which exchange()'s harness-
    # controlled uart_listen() round does not invoke - so it stays unset here, the same "the callback stores
    # nothing itself" fact the original test recorded, now checked against the real storage location.
    assert _link(ROLE_RESPONDER)._last_echo is None


def test_one_sided_silence_forces_a_resync_and_both_sides_recover() -> None:
    # The realistic one-sided fault, and the recovery the whole design exists for.
    link = build_linked_system()
    initiator, responder = _link(ROLE_INITIATOR)._comm, _link(ROLE_RESPONDER)._comm
    direction = link.direction_from(fakes()[1])
    direction.silent = True
    assert _run(exchange(initiator.uart_set(0x02, b"lost")), limit=_EXCHANGE_LIMIT_S) is False
    assert initiator._holdoff_active is True

    direction.silent = False
    _run(responder.clear(), limit=_EXCHANGE_LIMIT_S)
    assert _run(exchange(initiator.uart_set(0x02, b"back")), limit=_EXCHANGE_LIMIT_S) is True


def test_a_payload_size_mismatch_is_diagnosed_as_unintelligible() -> None:
    # A responder whose payload_size is 8 over its peer's, on the device's own jumpered buses at real wire time: each frame dies
    # inside its failing read, so only the bytes that read dropped can raise the mismatch diagnostic (J.6).
    build_linked_system()
    initiator = _link(ROLE_INITIATOR)._comm
    limits = transfer_limits(payload_size=initiator._payload_size + 8, timeout=initiator._timeout)
    callbacks = ResponderCallbacks(echo_get(b"v"), accept_set(), None)
    responder = UARTComm(_bus("responder_bus"), ROLE_RESPONDER, limits=limits, callbacks=callbacks, name="UART_MISMATCH")
    assert _run(responder.setup()) is True

    async def scenario() -> None:
        for _ in range(4):  # the diagnostic waits for a streak of resyncs, so one failed exchange must not trip it
            listener = asyncio.create_task(responder.uart_listen())
            await initiator.uart_set(0x02, b"nonsense")
            await responder.clear()
            await _settle_listener(listener)

    _run(scenario(), limit=_EXCHANGE_LIMIT_S)
    unintelligible = code("E", "UART_LINK_UNINTELLIGIBLE")
    responder_codes, initiator_codes = _errnos(responder), _errnos(initiator)
    assert unintelligible in responder_codes, f"the mismatched responder never reported the link unintelligible: {responder_codes}"
    assert code("E", "UART_NO_ACK") in initiator_codes, f"the initiator never reported its missing acknowledgements: {initiator_codes}"
    assert unintelligible not in initiator_codes, f"the initiator, which received nothing, reported the link unintelligible: {initiator_codes}"


def test_a_crc16_exerciser_pair_completes_its_rounds() -> None:
    # The device's own link parameters with CRC16 on both buses: the exerciser's rounds land, none fails, nothing logged.
    # Its period sleep a bare yield, the rounds back to back: the period is not under test.
    initiator, responder, _link_pair = _crc16_pair()
    asy_uart_link_driver.asyncio = _BackToBack()  # type: ignore[assignment, attr-defined]
    try:
        _run(_exercised(initiator, responder, lambda: initiator._transfers + initiator._failures >= _CRC16_ROUNDS), limit=_EXCHANGE_LIMIT_S)
    finally:
        asy_uart_link_driver.asyncio = asyncio  # type: ignore[attr-defined]
    assert initiator._failures == 0, f"{initiator._failures} CRC16 exercise rounds failed on a clean link"
    for end in (initiator, responder):
        assert _traces(end._comm) == set(), f"{end.name} logged {_traces(end._comm)} on a clean CRC16 link"


def test_a_crc16_exerciser_pair_catches_a_corrupted_byte() -> None:
    # One byte flipped mid-frame in the initiator's first request: the responder's CRC check drops the frame, the round
    # counts as a failure, the next round is clean, and each history holds only what that explains.
    initiator, responder, link = _crc16_pair()
    request = link.direction_from(link.endpoints[0])
    request.corrupt_indices[request.offered + initiator._comm._frame_size // 2] = 0xFF
    _run(_exercised(initiator, responder, lambda: initiator._transfers + initiator._failures >= 2), limit=_EXCHANGE_LIMIT_S)
    assert (initiator._failures, initiator._transfers) == (1, 1), f"{initiator._failures} of two rounds failed for one corrupted byte"
    bus = responder._comm._uart
    assert bus is not None and bus.discarded_bytes >= initiator._comm._frame_size, "the responder's CRC check dropped no frame"
    # The dropped frame reads as the responder's failed listen read, its unanswered request as the initiator's missing ACK.
    assert _traces(responder._comm) == {("E", code("E", "TIMEOUT"))}, f"the responder logged {_traces(responder._comm)}"
    assert _traces(initiator._comm) == {("E", code("E", "UART_NO_ACK"))}, f"the initiator logged {_traces(initiator._comm)}"


# ---------------------------------------------------------------------------
# Concurrency inside the real task graph
# ---------------------------------------------------------------------------


def test_a_transfer_does_not_starve_other_tasks() -> None:
    # Every wait in the protocol yields, so a maximum-length transfer must not stall the
    # Neopixel animation or a sensor trigger. A plain co-running ticker is the cheapest proof.
    build_linked_system()
    initiator = _link(ROLE_INITIATOR)._comm
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

    assert _run(scenario(), limit=_EXCHANGE_LIMIT_S) is True
    assert len(ticks) > 5, "other tasks made no progress during the transfer"


def test_the_link_keeps_working_while_the_rest_of_the_graph_runs() -> None:
    # The link and the rest of the system have to coexist, not merely each work alone.
    build_linked_system()
    assert module.sysfunct is not None
    initiator = _link(ROLE_INITIATOR)._comm

    async def scenario() -> "list[PieceBuffer | None]":
        noise = [asyncio.create_task(module.sysfunct.get_uptime()) for _ in range(_COEXIST_NOISE_TASKS)]
        results = [await exchange(initiator.uart_get(0x01))]
        for task in noise:
            await task
        return results

    results = _run(scenario(), limit=_EXCHANGE_LIMIT_S)
    assert results[0] is not None


def test_a_collection_length_pause_mid_transfer_does_not_break_the_link() -> None:
    # A synchronous stop-the-world pause the length of the worst measured collection (Part I): the tested
    # property - a pause mid-frame is not an inter-part timeout - without depending on today's heap.
    build_linked_system()
    initiator = _link(ROLE_INITIATOR)._comm

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

    assert _run(scenario(), limit=_EXCHANGE_LIMIT_S) is True


def test_a_maximum_length_train_completes_and_still_yields() -> None:
    # The massive singular load: the longest transaction this protocol can express, 254 data chunks at payload_size 48,
    # where one non-yielding step in the read or write path would be most visible. A host stall past the 1000 ms reply
    # timeout lands mid-train: the deadlines count poll rounds.
    build_linked_system()
    initiator = _link(ROLE_INITIATOR)._comm
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
    completed = _run(scenario(), limit=_MAX_TRAIN_LIMIT_S, clock=clock)
    assert clock.disarm(), "the planted host stall never fired: the train did not reach it"
    assert completed is True, "the maximum-length train did not complete"
    # Progress, not a rate: the ticker must have been scheduled throughout, which it cannot be if
    # any step held the loop for the whole transfer.
    assert len(ticks) > 50, f"other tasks ran only {len(ticks)} times across a 254-chunk transfer"
    counts = _run(initiator.get_error_counter())
    assert counts[initiator.name]["ErrCount"] == 0, "the longest legal transfer logged an error"


def test_many_back_to_back_transfers_do_not_degrade_or_leak() -> None:
    # Massive repeated load rather than one big transfer: the counters, the UID space and the
    # buffers all have to survive being cycled, not just used once. The UID wraps at 0xFE, so this
    # deliberately runs past one whole wrap.
    import gc

    link = build_linked_system()
    initiator = _link(ROLE_INITIATOR)._comm
    rounds = _LEAK_ROUNDS
    fake_a, fake_b = fakes()

    def _clear_wire_logs() -> None:
        # The twin keeps up to 4 KB of delivered bytes per direction in wire_log: test instrumentation
        # that would otherwise be measured as the leak this test is looking for - the harness growing
        # to its cap, not the driver.
        link.direction_from(fake_a).wire_log.clear()
        link.direction_from(fake_b).wire_log.clear()

    async def transfers(count: int) -> int:
        ok = 0
        for i in range(count):
            if await exchange(initiator.uart_get(0x01)) is not None:
                ok += 1
            if not i % 20:
                _clear_wire_logs()
        return ok

    # The heap is read outside a run, so the record of the tasks a run made is gone by then: after the warm-up and at the end.
    ok = _run(transfers(_LEAK_WARMUP_ROUNDS), limit=_HAMMER_LIMIT_S)
    _clear_wire_logs()
    gc.collect()
    free_n1 = gc.mem_free()
    ok += _run(transfers(rounds - _LEAK_WARMUP_ROUNDS), limit=_HAMMER_LIMIT_S)
    _clear_wire_logs()
    gc.collect()
    rate = (free_n1 - gc.mem_free()) / (rounds - _LEAK_WARMUP_ROUNDS)
    assert ok == rounds, f"only {ok}/{rounds} transfers succeeded across a full UID wrap"
    counts = _run(initiator.get_error_counter())
    assert counts[initiator.name]["ErrCount"] == 0, f"{rounds} clean transfers logged an error"
    # Buffers are preallocated per instance, so a steady-state loop retains nothing per transfer: this asserts "no
    # per-transfer leak", not an allocation budget.
    assert rate < _LEAK_RATE_BYTES_PER_TRANSFER, f"{rate:.1f} bytes retained per transfer after the warm-up - a per-transfer leak"


def test_the_link_survives_sustained_allocation_pressure() -> None:
    # Resource exhaustion rather than contention: a heap being churned hard underneath the link,
    # which is what turns a latent one-big-allocation design into a failure (Part I). The link must
    # either complete or degrade cleanly - never raise out, and never corrupt a payload.
    build_linked_system()
    initiator = _link(ROLE_INITIATOR)._comm
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
                out.append(await exchange(initiator.uart_set(0x02, bytes(200))))
            return out
        finally:
            stop.append(True)
            background.cancel()
            await asyncio.sleep_ms(_CANCEL_SETTLE_MS)

    results = _run(scenario(), limit=_CHURN_LIMIT_S)
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
