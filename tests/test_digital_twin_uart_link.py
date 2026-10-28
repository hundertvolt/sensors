"""Twin-tier coverage of the generated UART crossover link (SPECIFICATION.md J.7) on the device tests/_twin_devices.py
finds wiring a uart_link pair, its two peripherals joined as the bench jumper joins them, plus pair-level CRC16 and
mismatch cases."""

import asyncio
import gc
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
from _async_harness import cancel, cancel_all, run  # noqa: E402 - imported after the prewarm and the UDP shim
from _digital_twin_construction_scenarios import load_device  # noqa: E402 - imported after the prewarm and the UDP shim
from _error_codes import code  # noqa: E402 - imported after the prewarm and the UDP shim
from _fake_time import DrivenTime  # noqa: E402 - imported after the prewarm and the UDP shim
from _generated_module import ERROR_LEVEL, write_error_level_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _http_client import build_request, parse_status_line  # noqa: E402 - imported after the prewarm and the UDP shim
from _offline_ntp_config import write_offline_ntp_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _src_const import src_bytes, src_int  # noqa: E402 - imported after the prewarm and the UDP shim
from _strict_json import strict_loads  # noqa: E402 - imported after the prewarm and the UDP shim
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_devices import device_with, wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim
from _uart_comm_harness import PollRoundClock, accept_set, copied_out, echo_get, transfer_limits  # noqa: E402 - imported after the prewarm and the UDP shim
from machine import WDT, LinkPoller, UARTLink  # noqa: E402 - imported after the prewarm and the UDP shim

import asy_uart_comm  # noqa: E402 - imported after the prewarm and the UDP shim
import asy_uart_driver  # noqa: E402 - imported after the prewarm and the UDP shim
import asy_uart_link_driver  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_config_manager import VALID  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_crc_checks import CRC16  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_print_log import DEFAULT_LOG, LogConfig  # noqa: E402 - imported after the prewarm and the UDP shim
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

    from asy_base_classes import JsonDict, PieceBuffer

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
_watchdog: "list[WDT]" = []  # the latest build's watchdog, as its boot entry arms it
_LINK_MODULES = (asy_uart_driver, asy_uart_comm, asy_uart_link_driver)  # every module holding the link's clock
_virtual_now = [0]  # where the last driven run left the clock: a deadline one run stores stays comparable in the next
# Each end's (port, tx, rx, bus, role, limits), read once off the latest build for the CRC16 pairs.
_specs: "list[tuple[int, int, int, asy_uart_driver.UART, str, TransferLimits]]" = []
_BANNER: bytes = src_bytes("src/asy_uart_link_driver.py", "_BANNER")
_ERROR_LOG = LogConfig(None, DEFAULT_LOG.history_length, ERROR_LEVEL)  # a link end built here logs as the booted device's

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
# A host stall past the link's 1000 ms reply timeout, after this many ticker rounds (mid-train: about 1550 in all)
_MAX_TRAIN_STALL_MS = 1100
_MAX_TRAIN_STALL_AFTER = 750
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
# The hazard run under API load (owner, 2026-10-21, asked "Leave the UART hazards under API load untested?": "b - system
# shall be proven stable unter max load allover"): readers GET /status meanwhile, each response write a pause as a
# socket's send is, so requests stay in flight while the link's driven clock moves.
# @tunable l2.uart_link_hazard_readers = 3
_HAZARD_READERS = 3
# @tunable l2.uart_link_hazard_write_pause_ms = 1
_HAZARD_WRITE_PAUSE_MS = 1
# Each reader starts a GET at every multiple of this on the driven clock and pauses its writes on that clock too, so a
# run serves the same reads on any host and at either GC stage (agent, 2026-10-21).
# @tunable l2.uart_link_hazard_read_period_ms = 2500
_HAZARD_READ_PERIOD_MS = 2500
# From the request to the run's end on the driven clock, exact on any host: the measured figure, no margin (agent, 2026-10-21).
# @tunable l2.uart_link_hazard_run_virtual_ms = 208370
_HAZARD_RUN_VIRTUAL_MS = 208370
_EXERCISE_PERIOD_MS = src_int("src/asy_uart_link_driver.py", "_EXERCISE_PERIOD_MS")
_HAZARD_RECOVERY_ATTEMPTS = src_int("src/asy_uart_link_driver.py", "_HAZARD_RECOVERY_ATTEMPTS")
_NO_WRN = src_int("src/asy_print_log.py", "_NO_WRN")  # a warning slot's offset in a stored log
_UID_MAX = src_int("src/asy_uart_comm.py", "_UID_MAX")
# The first-chunk boundary values J.3/J.4 accept, as the bench host judges them (tests_hardware/flash/test_uart_crossover.py).
_LEGAL = {"cmd": lambda v: v == asy_uart_comm.CMD_SET, "size": lambda v: v == 1, "chunks": lambda v: v >= 2, "cur_chunk": lambda v: v == 1, "uid": lambda v: v <= _UID_MAX}
_ONE_COMPLETION = ([True, False], [False, True])  # two initiations at once: one completes, one is refused, either order


async def _api(method: str, path: str, body: "dict[str, object] | None" = None, clock: "DrivenTime | None" = None) -> "tuple[int, JsonDict]":
    conn = _Conn(build_request(method, path, "127.0.0.1", body), clock)
    await module.webserver._serve(conn, conn)
    return conn.response()


def test_a_raw_write_that_fails_in_the_sweep_reads_as_no_verdict() -> None:
    # On the twin wire at dev's limits: a planted failed raw write for an illegal value reads None, not the "not ACKed"
    # that value is expected to give, so the judge counts it; the legal value after it is ACKed and the link recovers.
    link = build_linked_system()
    initiator, responder = _link(ROLE_INITIATOR), _link(ROLE_RESPONDER)
    bus = initiator._uart
    assert bus is not None
    real_write = initiator._write_raw
    written: list[int] = []

    async def planted(frame: bytearray) -> bool:
        written.append(frame[1])
        return len(written) > 1 and await real_write(frame)

    initiator._write_raw = planted  # type: ignore[method-assign]
    fields = (("cmd", 1, (0x00, asy_uart_comm.CMD_SET)),)
    got: list[object] = []

    async def go(clock: DrivenTime) -> None:
        loops = [start() for start in responder.get_task_starters()]

        async def sweep() -> None:
            room = initiator._frame + bus.crc.length()  # the CRC's room in both, as the exerciser sizes them
            got.append(await initiator._sweep_fields(bytearray(room), bytearray(room)))

        task = asyncio.create_task(sweep())
        try:
            await clock.run_until(task.done, _HAZARD_RUN_VIRTUAL_MS)
        finally:
            for each in loops:
                each.cancel()
            await clock.run_until(lambda: all(each.done() for each in loops), 0)

    swept = asy_uart_link_driver._HAZARD_FIELDS
    asy_uart_link_driver._HAZARD_FIELDS = fields  # type: ignore[assignment]  # one illegal value, then the legal one
    try:
        with DrivenTime(*_LINK_MODULES, sleeps=True) as clock:
            _wire_on(link, clock)
            try:
                run(go(clock), _RUN_LIMIT_S)
            finally:
                del link._now_us  # the class's own wire clock again
    finally:
        asy_uart_link_driver._HAZARD_FIELDS = swept
    assert written == [0x00, asy_uart_comm.CMD_SET], f"the sweep did not write the planted value, then the legal one: {written}"
    assert got == [[["cmd", [None, True], True]]] and got[0] != _expected_sweep(fields), f"the failed raw write did not read as no verdict: {got}"


async def _boot_device(cfg_path: str) -> WDT:
    # The generated main()'s first two steps: build_system() with the watchdog a boot entry arms, then the setup list.
    write_offline_ntp_config(cfg_path)
    write_error_level_config(cfg_path)
    watchdog = WDT(timeout=run_generic_integration._WDT_TIMEOUT_MS)
    await module.build_system(watchdog=watchdog, cfg_path=cfg_path, debug=ERROR_LEVEL)
    await module.sysfunct.run_setups(module._collect_setups())
    return watchdog


def _build_device() -> None:
    machine.reset_peripherals()  # each build is a new board: fresh buses and chips on the device's own plan
    network.reset_interfaces()
    machine.configure_wiring(wiring_plan(_DEVICE))
    rp2.DMA.reset_registry()  # each build is a boot: the soft reset before it frees every DMA channel
    _watchdog[:] = [_run(_boot_device(_tmp_cfg_dir()))]
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
        ends.append(UARTLinkDriver(crc_bus, role, limits=limits, name_ext=role, log=_ERROR_LOG))
    fake_a, fake_b = buses[0]._uart, buses[1]._uart
    assert fake_a is not None and fake_b is not None
    link = UARTLink(fake_a, fake_b)
    buses[0].poller = LinkPoller(fake_a)  # type: ignore[assignment]
    buses[1].poller = LinkPoller(fake_b)  # type: ignore[assignment]
    initiator, responder = ends
    assert _run(initiator.setup()) is True and _run(responder.setup()) is True
    return initiator, responder, link


def _driven(link: "TwinLink", work: "Callable[[DrivenTime], Coroutine[object, object, T]]", limit: int = _RUN_LIMIT_S) -> "T":
    # `work` on one driven clock over the link's modules and wire, on from the last run's instant, ended when it ends:
    # a reply budget counts the link's own waits, never the host's load or speed, and no wait costs wall time (J.7).
    with DrivenTime(*_LINK_MODULES, now=_virtual_now[0], sleeps=True) as clock:
        _wire_on(link, clock)
        try:
            return run(_until_done(clock, work(clock), limit * 1000), limit)
        finally:
            del link._now_us  # the class's own wire clock again
            _virtual_now[0] = clock.now


def _errnos(comm: UARTComm) -> "list[int]":
    # Errors only: ErrNum holds both kinds and ErrType tells them apart. Indexed, not zip()ed: MicroPython has no strict=.
    entry = _run(comm.get_error_counter())[comm.name]
    nums, kinds = entry["ErrNum"], entry["ErrType"]
    return [nums[i] for i in range(len(nums)) if kinds[i] == "E"]


async def _exercised(clock: DrivenTime, initiator: UARTLinkDriver, responder: UARTLinkDriver, done: "Callable[[], bool]") -> None:
    # The pair's own loops, started as a boot starts them (the responder's listen, the initiator's exercise), until `done`.
    tasks = [start() for start in responder.get_task_starters() + initiator.get_task_starters()]
    try:
        while not done():
            await clock._sleep_ms(_TICKER_STEP_MS)
    finally:
        await cancel_all(tasks)


def _expected_sweep(fields: "tuple[tuple[str, int, tuple[int, ...]], ...]") -> "list[object]":
    # The field sweep's verdicts J.3/J.4 give: each value ACKed exactly when legal, then one clean exchange per field.
    return [[name, [_LEGAL[name](value) for value in values], True] for name, _offset, values in fields]


async def _feed(watchdog: WDT) -> None:
    # Stands in for the boot's own feeder on the real loop: a feed late past the timeout is a loop held that long.
    while True:
        watchdog.feed()
        await asyncio.sleep_ms(watchdog.timeout // 4)


def _hammer_with_the_graph_running() -> None:
    # The combined case: the link hammered flat out while the rest of the device's real graph runs, with the heap
    # watched throughout, at its process's GC stage: scripts/test.sh runs this file at gc.threshold(-1) and again at
    # 32768 (SPECIFICATION.md I.4(e)/(f)).
    link = build_linked_system()
    assert module.sysfunct is not None
    initiator = _link(ROLE_INITIATOR)._comm
    fake_a, fake_b = fakes()

    def clear_wire_logs() -> None:
        # The twin records every delivered byte in an unbounded wire_log - about 15kB over this
        # many transactions. That is the harness growing, not the driver, and measuring it as a
        # leak is exactly the mistake Part E.7 warns about.
        link.direction_from(fake_a).wire_log.clear()
        link.direction_from(fake_b).wire_log.clear()

    async def hammered(clock: DrivenTime, rounds: int) -> int:
        noise = [asyncio.create_task(_uptime_noise(clock)) for _ in range(_HAMMER_NOISE_CONSUMERS)]
        try:
            ok = 0
            for i in range(rounds):
                if await exchange(clock, initiator.uart_get(0x01)) is not None:
                    ok += 1
                if not i % 20:
                    clear_wire_logs()
            return ok
        finally:
            for task in noise:
                task.cancel()
            await clock._sleep_ms(_CANCEL_SETTLE_MS)

    # The warm-up absorbs one-time cost; the window is its own run, so the heap is read with no run's task record held.
    _driven(link, lambda clock: hammered(clock, _HAMMER_WARMUP_ROUNDS), limit=_HAMMER_LIMIT_S)
    clear_wire_logs()
    gc.collect()
    free_n1 = gc.mem_free()
    ok = _driven(link, lambda clock: hammered(clock, _HAMMER_ROUNDS), limit=_HAMMER_LIMIT_S)
    clear_wire_logs()
    gc.collect()
    rate = (free_n1 - gc.mem_free()) / _HAMMER_ROUNDS
    stage = gc.threshold()
    assert ok == _HAMMER_ROUNDS, f"only {ok}/{_HAMMER_ROUNDS} hammered transactions completed at gc.threshold({stage})"
    counts = _run(initiator.get_error_counter())
    assert counts[initiator.name]["ErrCount"] == 0, f"errors logged under hammer at gc.threshold({stage})"
    assert rate < _LEAK_RATE_BYTES_PER_TRANSFER, f"{rate:.1f} bytes retained per hammered transaction at gc.threshold({stage})"


def _hazard_report(status: "JsonDict") -> "JsonDict":
    # The initiator's hazard report as GET /status carries it, under its maintenance key.
    sensors = status["sensors"]
    assert isinstance(sensors, dict), status
    report = sensors[_link(ROLE_INITIATOR).name]
    assert isinstance(report, dict), sensors
    return report


def _link(role: str) -> UARTLinkDriver:
    # The last build's one UART link driver of `role`.
    return _ends[role]


class _Readers:
    # The API load's record: each read's start on the driven clock, answers served, any not 200, and how many showed
    # the hazard run pending.
    def __init__(self) -> None:
        self.starts: list[int] = []
        self.served = 0
        self.not_ok: list[int] = []
        self.saw_pending = 0


def _persisted(role: str) -> "list[tuple[str, int]]":
    # One end's log as its FRAM chunk holds it, what a reboot restores: (ErrType, ErrNum) per used slot, oldest first.
    stored = _run(_link(role).pr._read())
    assert isinstance(stored, tuple), f"the {role} end's FRAM log did not read back: {stored}"
    return [("W", entry - _NO_WRN) if entry > _NO_WRN else ("E", entry) for entry in stored[1] if entry not in (0, _NO_WRN)]


async def _read_status_repeatedly(readers: _Readers, clock: DrivenTime) -> None:
    while True:
        await clock._sleep_ms(_HAZARD_READ_PERIOD_MS - clock.now % _HAZARD_READ_PERIOD_MS)
        readers.starts.append(clock.now)
        status_code, status = await _api("GET", "/status", clock=clock)
        readers.served += 1
        if status_code != 200:
            if len(readers.not_ok) < 8:  # a few name the failure; more add nothing
                readers.not_ok.append(status_code)
        elif _hazard_report(status)["Pending"] is True:
            readers.saw_pending += 1


def _run(coro: "Coroutine[object, object, T]", limit: int = _RUN_LIMIT_S) -> "T":
    # A run with no exchange in it (a boot, a setup, a log read) on the poll-round clock (SPECIFICATION.md J.7).
    with PollRoundClock():
        return run(coro, limit)


class _Conn:
    # One in-memory connection for the device's own WebserverService._serve(), its whole HTTP path but the accept: the
    # request's bytes in, the response's out, one object for both halves as start_server() hands its callback one Stream.
    def __init__(self, request: bytes, clock: "DrivenTime | None") -> None:
        self._rx = request
        self._tx: list[bytes] = []
        self._clock = clock

    def get_extra_info(self, name: str) -> object:
        return ("127.0.0.1", 54321) if name == "peername" else None

    async def aclose(self) -> None:
        pass

    async def awrite(self, data: bytes) -> None:
        self._tx.append(bytes(data))
        if self._clock is None:
            await asyncio.sleep_ms(_HAZARD_WRITE_PAUSE_MS)
        else:
            await self._clock._sleep_ms(_HAZARD_WRITE_PAUSE_MS)

    def close(self) -> None:
        pass

    async def read(self, n: int) -> bytes:
        data, self._rx = self._rx[:n], self._rx[n:]
        return data

    async def readexactly(self, n: int) -> bytes:
        if len(self._rx) < n:
            raise EOFError  # as extmod/asyncio/stream.py's Stream.readexactly()
        return await self.read(n)

    def response(self) -> "tuple[int, JsonDict]":
        raw = b"".join(self._tx)
        end = raw.find(b"\r\n\r\n")
        assert end > 0, f"no response head: {raw[:80]!r}"
        body = strict_loads(raw[end + 4 :])
        assert isinstance(body, dict), f"the response body is no object: {body!r}"
        return parse_status_line(raw[: raw.find(b"\r\n")]), body


async def _settle_listener(clock: DrivenTime, listener: "asyncio.Task[object]") -> None:
    try:
        await clock._wait_ms(listener, _LISTENER_SETTLE_S * 1000)
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


async def _until_done(clock: DrivenTime, work: "Coroutine[object, object, T]", limit_ms: int) -> "T":
    # `work` as a task, the clock driven until it ends: its result, its failure, or run_until()'s past limit_ms.
    task = asyncio.create_task(work)
    try:
        await clock.run_until(task.done, limit_ms)
    except BaseException:
        await cancel(task)
        raise
    return await task


async def _uptime_noise(clock: DrivenTime) -> None:
    # A co-running consumer of the same event loop, so the hammer is never the only thing scheduled.
    while True:
        await module.sysfunct.get_uptime()
        await clock._sleep_ms(_NOISE_STEP_MS)


def _wire_on(link: "TwinLink", clock: DrivenTime) -> None:
    # The twin wire's byte times on the driven clock too, from its real offset or the end of the last transmission an
    # earlier driven run scheduled, whichever is later: a frame then takes its wire time on its reader's clock.
    base_us, base_ms = max(link._now_us(), *link._next_free_us), clock.now
    link._now_us = lambda: base_us + (clock.now - base_ms) * 1000  # type: ignore[method-assign]


def build_linked_system() -> "TwinLink":
    # The device's real object graph, its two UART peripherals joined the way the bench jumper joins them (each TX to the
    # other's RX), its pollers swapped for the twin's own LinkPoller. Bounded stand-in, never a real select.poll(): the
    # fake's readiness must be scripted, not polled in real time (CLAUDE.md "Known hang cause").
    _build_device()
    fake_a, fake_b = fakes()
    link = UARTLink(fake_a, fake_b)
    _bus("initiator_bus").poller = LinkPoller(fake_a)  # type: ignore[assignment]
    _bus("responder_bus").poller = LinkPoller(fake_b)  # type: ignore[assignment]
    return link


async def exchange(clock: DrivenTime, work: "Coroutine[object, object, T]") -> "T":
    # The initiator's call returning does not mean the responder is finished: it still has its last
    # read to complete, and the twin delivers by wire time. Cutting the listener off would
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
        await _settle_listener(clock, listener)


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
    answer = _driven(link, lambda clock: exchange(clock, _link(ROLE_INITIATOR)._comm.uart_get(0x01)))
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
    link = build_linked_system()
    initiator, responder = _link(ROLE_INITIATOR)._comm, _link(ROLE_RESPONDER)._comm

    answer = _driven(link, lambda clock: exchange(clock, initiator.uart_get(0x01)))
    assert copied_out(answer) == _BANNER

    assert _driven(link, lambda clock: exchange(clock, initiator.uart_set(0x02, b"round trip"))) is True

    for comm in (initiator, responder):
        counts = _run(comm.get_error_counter())
        assert counts[comm.name]["ErrCount"] == 0, f"{comm.name} counted an error on a clean link"


def test_a_payload_larger_than_one_chunk_crosses_the_jumper_intact() -> None:
    link = build_linked_system()
    payload = bytes((i * 5) & 0xFF for i in range(140))  # spans three data chunks at payload_size 48
    assert _driven(link, lambda clock: exchange(clock, _link(ROLE_INITIATOR)._comm.uart_set(0x02, payload))) is True
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
    assert _driven(link, lambda clock: exchange(clock, initiator.uart_set(0x02, b"lost")), limit=_EXCHANGE_LIMIT_S) is False
    assert initiator._holdoff_active is True

    direction.silent = False
    _driven(link, lambda _clock: responder.clear(), limit=_EXCHANGE_LIMIT_S)
    assert _driven(link, lambda clock: exchange(clock, initiator.uart_set(0x02, b"back")), limit=_EXCHANGE_LIMIT_S) is True


def test_a_payload_size_mismatch_is_diagnosed_as_unintelligible() -> None:
    # A responder whose payload_size is 8 over its peer's, on the device's own jumpered buses at wire time: each frame dies
    # inside its failing read, so only the bytes that read dropped can raise the mismatch diagnostic (J.6).
    link = build_linked_system()
    initiator = _link(ROLE_INITIATOR)._comm
    limits = transfer_limits(payload_size=initiator._payload_size + 8, timeout=initiator._timeout)
    callbacks = ResponderCallbacks(echo_get(b"v"), accept_set(), None)
    responder = UARTComm(_bus("responder_bus"), ROLE_RESPONDER, limits=limits, callbacks=callbacks, name="UART_MISMATCH", log=_ERROR_LOG)
    assert _run(responder.setup()) is True

    async def scenario(clock: DrivenTime) -> None:
        for _ in range(4):  # the diagnostic waits for a streak of resyncs, so one failed exchange must not trip it
            listener = asyncio.create_task(responder.uart_listen())
            await initiator.uart_set(0x02, b"nonsense")
            await responder.clear()
            await _settle_listener(clock, listener)

    _driven(link, scenario, limit=_EXCHANGE_LIMIT_S)
    unintelligible = code("E", "UART_LINK_UNINTELLIGIBLE")
    responder_codes, initiator_codes = _errnos(responder), _errnos(initiator)
    assert unintelligible in responder_codes, f"the mismatched responder never reported the link unintelligible: {responder_codes}"
    assert code("E", "UART_NO_ACK") in initiator_codes, f"the initiator never reported its missing acknowledgements: {initiator_codes}"
    assert unintelligible not in initiator_codes, f"the initiator, which received nothing, reported the link unintelligible: {initiator_codes}"


def test_a_crc16_exerciser_pair_completes_its_rounds() -> None:
    # The device's own link parameters with CRC16 on both buses: the exerciser's rounds land, none fails, nothing logged.
    # Its period sleeps on the driven clock, so the rounds take no wall time: the period is not under test.
    initiator, responder, link = _crc16_pair()
    _driven(link, lambda clock: _exercised(clock, initiator, responder, lambda: initiator._transfers + initiator._failures >= _CRC16_ROUNDS), limit=_EXCHANGE_LIMIT_S)
    assert initiator._failures == 0, f"{initiator._failures} CRC16 exercise rounds failed on a clean link"
    for end in (initiator, responder):
        assert _traces(end._comm) == set(), f"{end.name} logged {_traces(end._comm)} on a clean CRC16 link"


def test_a_crc16_exerciser_pair_catches_a_corrupted_byte() -> None:
    # One byte flipped mid-frame in the initiator's first request: the responder's CRC check drops the frame, the round
    # counts as a failure, the next round is clean, and each history holds only what that explains.
    initiator, responder, link = _crc16_pair()
    request = link.direction_from(link.endpoints[0])
    request.corrupt_indices[request.offered + initiator._comm._frame_size // 2] = 0xFF
    _driven(link, lambda clock: _exercised(clock, initiator, responder, lambda: initiator._transfers + initiator._failures >= 2), limit=_EXCHANGE_LIMIT_S)
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
    link = build_linked_system()
    initiator = _link(ROLE_INITIATOR)._comm
    ticks = []

    async def ticker(clock: DrivenTime) -> None:
        while True:
            ticks.append(time.ticks_ms())
            await clock._sleep_ms(_TICKER_STEP_MS)

    async def scenario(clock: DrivenTime) -> bool:
        background = asyncio.create_task(ticker(clock))
        try:
            return await exchange(clock, initiator.uart_set(0x02, bytes(240)))
        finally:
            background.cancel()

    assert _driven(link, scenario, limit=_EXCHANGE_LIMIT_S) is True
    assert len(ticks) > 5, "other tasks made no progress during the transfer"


def test_the_link_keeps_working_while_the_rest_of_the_graph_runs() -> None:
    # The link and the rest of the system have to coexist, not merely each work alone.
    link = build_linked_system()
    assert module.sysfunct is not None
    initiator = _link(ROLE_INITIATOR)._comm
    payload = bytes((i * 5) & 0xFF for i in range(140))  # spans three data chunks at payload_size 48

    async def scenario(clock: DrivenTime) -> "tuple[PieceBuffer | None, bool, list[bool]]":
        # The noise consumers run through both exchanges, the banner GET and a multi-chunk SET, and are ended after.
        noise = [asyncio.create_task(_uptime_noise(clock)) for _ in range(_COEXIST_NOISE_TASKS)]
        try:
            answer = await exchange(clock, initiator.uart_get(0x01))
            sent = await exchange(clock, initiator.uart_set(0x02, payload))
            return answer, sent, [task.done() for task in noise]
        finally:
            await cancel_all(noise)

    answer, sent, ended = _driven(link, scenario, limit=_EXCHANGE_LIMIT_S)
    assert copied_out(answer) == _BANNER
    assert sent is True, "the 140-byte SET failed while the noise tasks ran"
    assert not any(ended), f"a noise task ended before both exchanges did: {ended}"


def test_a_collection_length_pause_mid_transfer_does_not_break_the_link() -> None:
    # A synchronous stop-the-world pause the length of the worst measured collection (Part I): the tested
    # property - a pause mid-frame is not an inter-part timeout - without depending on today's heap.
    link = build_linked_system()
    initiator = _link(ROLE_INITIATOR)._comm

    async def scenario(clock: DrivenTime) -> bool:
        async def pauser() -> None:
            for _ in range(_PAUSE_ROUNDS):
                clock.advance(_WORST_GC_PAUSE_MS)  # no task runs, as in a collection; the wire keeps delivering
                await clock._sleep_ms(_PAUSE_STEP_MS)

        background = asyncio.create_task(pauser())
        try:
            return await exchange(clock, initiator.uart_set(0x02, bytes(120)))
        finally:
            background.cancel()

    assert _driven(link, scenario, limit=_EXCHANGE_LIMIT_S) is True


def test_a_maximum_length_train_completes_and_still_yields() -> None:
    # The massive singular load: the longest transaction this protocol can express, 254 data chunks at payload_size 48,
    # where one non-yielding step in the read or write path would be most visible. A host stall past the 1000 ms reply
    # timeout lands mid-train: the deadlines count the driven clock.
    link = build_linked_system()
    initiator = _link(ROLE_INITIATOR)._comm
    payload = bytes((i * 7) & 0xFF for i in range(48 * 254))
    ticks = []  # unannotated, like the sibling ticker above: ticks_ms() is an opaque _TicksMs
    stalled: list[bool] = []

    async def ticker(clock: DrivenTime) -> None:
        while True:
            ticks.append(time.ticks_ms())
            if len(ticks) == _MAX_TRAIN_STALL_AFTER:
                time.sleep_ms(_MAX_TRAIN_STALL_MS)  # the whole interpreter blocked: a host deschedule
                stalled.append(True)
            await clock._sleep_ms(_TICKER_STEP_MS)

    async def scenario(clock: DrivenTime) -> bool:
        background = asyncio.create_task(ticker(clock))
        try:
            return await exchange(clock, initiator.uart_set(0x02, payload))
        finally:
            background.cancel()

    completed = _driven(link, scenario, limit=_MAX_TRAIN_LIMIT_S)
    assert stalled, "the planted host stall never fired: the train did not reach it"
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

    async def transfers(clock: DrivenTime, count: int) -> int:
        ok = 0
        for i in range(count):
            if await exchange(clock, initiator.uart_get(0x01)) is not None:
                ok += 1
            if not i % 20:
                _clear_wire_logs()
        return ok

    # The heap is read outside a run, so the record of the tasks a run made is gone by then: after the warm-up and at the end.
    ok = _driven(link, lambda clock: transfers(clock, _LEAK_WARMUP_ROUNDS), limit=_HAMMER_LIMIT_S)
    _clear_wire_logs()
    gc.collect()
    free_n1 = gc.mem_free()
    ok += _driven(link, lambda clock: transfers(clock, rounds - _LEAK_WARMUP_ROUNDS), limit=_HAMMER_LIMIT_S)
    _clear_wire_logs()
    gc.collect()
    rate = (free_n1 - gc.mem_free()) / (rounds - _LEAK_WARMUP_ROUNDS)
    assert ok == rounds, f"only {ok}/{rounds} transfers succeeded across a full UID wrap"
    counts = _run(initiator.get_error_counter())
    assert counts[initiator.name]["ErrCount"] == 0, f"{rounds} clean transfers logged an error"
    # Buffers are preallocated per instance, so a steady-state loop retains nothing per transfer: this asserts "no
    # per-transfer leak", not an allocation budget.
    assert rate < _LEAK_RATE_BYTES_PER_TRANSFER, f"{rate:.1f} bytes retained per transfer after the warm-up - a per-transfer leak"


def test_every_train_crosses_intact_while_the_heap_churns() -> None:
    # Heap churn beside the link, 1 KB blocks allocated and dropped, so at gc.threshold(32768) collections land
    # mid-transfer. Every train arrives intact with nothing logged, and a failed allocation fails the test.
    link = build_linked_system()
    initiator, responder = _link(ROLE_INITIATOR)._comm, _link(ROLE_RESPONDER)._comm
    stop: list[bool] = []
    churned = [0]

    async def churn(clock: DrivenTime) -> None:
        held: list[bytearray] = []
        while not stop:
            held.append(bytearray(1024))
            churned[0] += 1024
            if len(held) > 32:
                held = held[16:]
            await clock._sleep_ms(_CHURN_STEP_MS)

    async def scenario(clock: DrivenTime) -> "list[bool]":
        background = asyncio.create_task(churn(clock))
        try:
            out = []
            for i in range(_CHURN_TRANSFERS):
                payload = bytes((i + j) & 0xFF for j in range(200))
                listener = asyncio.create_task(responder.uart_listen())
                sent = await initiator.uart_set(0x02, payload)
                heard = await clock._wait_ms(listener, _LISTENER_SETTLE_S * 1000)
                out.append(sent is True and heard.cmd_id == 0x02 and heard.payload is not None and copied_out(heard.payload) == payload)
            return out
        finally:
            stop.append(True)
            await background  # ends at its next step; an exception it raised surfaces here

    results = _driven(link, scenario, limit=_CHURN_LIMIT_S)
    assert len(results) == _CHURN_TRANSFERS and all(results), f"a train failed or arrived altered under heap churn: {results}"
    for comm in (initiator, responder):
        assert _run(comm.get_error_counter())[comm.name]["ErrCount"] == 0, f"{comm.name} logged an error under heap churn"
    stage = gc.threshold()
    assert stage < 0 or churned[0] > stage, f"the churn allocated {churned[0]} bytes, short of one collection at gc.threshold({stage})"


def test_hammering_the_link_beside_the_graph_holds() -> None:
    _hammer_with_the_graph_running()


def test_a_hazard_run_put_through_the_api_while_readers_hammer_it_reports_every_verdict() -> None:
    # The run started by PUT /status on the device's own webserver while readers GET /status, its verdicts read back
    # through the API, the echo resumed, no webserver error and no reboot. The link runs on the driven clock (agent,
    # 2026-10-21): in one interpreter the readers' work is never charged to a reply budget (J.7), and dev's timeout stands.
    link = build_linked_system()
    initiator, responder = _link(ROLE_INITIATOR), _link(ROLE_RESPONDER)
    watchdog = _watchdog[0]
    readers = _Readers()

    async def go(clock: DrivenTime) -> "tuple[tuple[int, JsonDict], int, int, tuple[int, JsonDict]]":
        feeder = asyncio.create_task(_feed(watchdog))
        loops = [start() for start in responder.get_task_starters() + initiator.get_task_starters()]
        load = [asyncio.create_task(_read_status_repeatedly(readers, clock)) for _ in range(_HAZARD_READERS)]
        try:
            await clock.run_until(lambda: initiator._transfers == 1, _EXERCISE_PERIOD_MS)
            start = clock.now
            put = await _api("PUT", "/status", {"UartHazards": True})
            elapsed = await clock.run_until(lambda: initiator._hazard_runs == 1 and not initiator._hazard_pending, _HAZARD_RUN_VIRTUAL_MS)
            await clock.run_until(lambda: initiator._transfers == 2, _EXERCISE_PERIOD_MS)
            final = await _api("GET", "/status")
        finally:
            await cancel_all(load + [feeder])
            for task in loops:
                task.cancel()
            await clock.run_until(lambda: all(task.done() for task in loops), 0)
        return put, start, elapsed, final

    with DrivenTime(*_LINK_MODULES, sleeps=True) as clock:
        _wire_on(link, clock)
        try:
            put, start, elapsed, final = run(go(clock), _HAMMER_LIMIT_S)
        finally:
            del link._now_us  # the class's own wire clock again
    during = len([at for at in readers.starts if start <= at <= start + elapsed])
    print(f"hazard run: {elapsed} virtual ms, {during} reads started during it, {readers.served} served in all, {readers.saw_pending} saw it pending")
    assert put[0] == 200 and put[1]["result"] == {"UartHazards": VALID}, f"PUT /status did not start the run: {put}"
    assert readers.not_ok == [], f"a reader was answered {readers.not_ok} under the hazard run"
    periods = (start + elapsed) // _HAZARD_READ_PERIOD_MS - (start - 1) // _HAZARD_READ_PERIOD_MS
    assert during == _HAZARD_READERS * periods, f"{during} reads started during the run, not one per reader at each of its {periods} period starts"
    assert during >= _HAZARD_READERS and readers.saw_pending > 0, f"the readers did not load the API during the run: {during} reads, {readers.saw_pending} saw it pending"
    assert final[0] == 200, final
    report = _hazard_report(final[1])
    assert report["Runs"] == 1 and report["Pending"] is False, report
    last = report["Last"]
    assert isinstance(last, dict), report
    two = last["TwoInitiations"]
    assert two in _ONE_COMPLETION, f"two initiations at once were not one completion and one refusal: {last}"
    crossing = last["Crossed"]
    assert isinstance(crossing, list) and len(crossing) == 4, last
    wrote, crossed, attempts, recovered = crossing
    assert wrote is True and crossed is False, f"the SET crossing the peer's answer did not fail: {crossing}"
    assert recovered is True and attempts in range(1, _HAZARD_RECOVERY_ATTEMPTS + 1), f"the link did not recover within {_HAZARD_RECOVERY_ATTEMPTS} attempts: {crossing}"
    fields = asy_uart_link_driver._HAZARD_FIELDS
    sweep = last["FieldSweep"]
    assert isinstance(sweep, list) and len(sweep) == len(fields), f"the field sweep left a field out: {sweep}"
    for entry, expected in zip(sweep, _expected_sweep(fields)):
        assert entry == expected, f"the ACKs against J.3/J.4 per value (None: its raw write failed), or the clean exchange after them: {entry}, not {expected}"
    assert 0 < elapsed <= _HAZARD_RUN_VIRTUAL_MS, f"the hazard run took {elapsed} virtual ms, its bound {_HAZARD_RUN_VIRTUAL_MS}"
    assert initiator._failures == 0, f"the hazard run counted into the echo's failures: {initiator._failures}"
    assert _errnos(initiator._comm) == [code("E", "UART_REENTRANT"), code("E", "UART_NO_ACK")], f"not the refusal and the crossing's stale ACK alone: {_errnos(initiator._comm)}"
    persisted = {role: _persisted(role) for role in (ROLE_INITIATOR, ROLE_RESPONDER)}  # as dev's website says of the run
    assert persisted[ROLE_INITIATOR] == [("E", code("E", "UART_REENTRANT")), ("E", code("E", "UART_NO_ACK"))], f"the initiator's FRAM log lacks its provoked faults: {persisted}"
    assert set(persisted[ROLE_RESPONDER]) == {("W", code("W", "UART_CMD_DECLINED")), ("E", code("E", "UART_FRAME_INVALID"))}, f"the responder's FRAM log lacks the sweep's provoked faults: {persisted}"
    web = _run(module.webserver.get_error_counter())[module.webserver.pr.name]
    assert "E" not in web["ErrType"], f"the webserver logged an error under the hazard run: {web}"
    assert watchdog.would_have_triggered_count == 0 and machine.reset_count == 0, "the hazard run under API load starved the watchdog or reset the board"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
