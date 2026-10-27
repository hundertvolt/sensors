"""Every I2C chip of the device named by TEST_DEVICE is reset once by its reader's setup, after its identity check,
when the generated graph boots on the twin buses: the clean state each _init_*() episode starts from (SPECIFICATION.md
F.2). The resets are each datasheet's soft-reset write, recorded at the twin's machine.I2C."""

import os
import sys

sys.path.insert(0, "ext")  # the vendored ext/microdot.py every generated device module imports
sys.path.insert(0, "digital_twin")  # see tests/test_digital_twin_sgp40.py's own comment for why
sys.path.insert(0, "digital_twin/unixport")  # the UDP shim's directory (digital_twin/README.md "_unix_port_udp_addr_shim.py")

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

prewarm_poll_set()  # before any poll object is registered (digital_twin/README.md "Known gaps")
patch_asy_udp_socket_for_unix_port()  # before any UDPSocket is constructed (digital_twin/README.md "_unix_port_udp_addr_shim.py")

PER_DEVICE = True
_device = os.getenv("TEST_DEVICE")
if not _device:
    raise RuntimeError("run through scripts/test.sh, or set TEST_DEVICE to one of devices/*.toml")
device: str = _device

import asyncio  # noqa: E402 - imported after the prewarm and the UDP shim

import machine  # noqa: E402 - imported after the prewarm and the UDP shim
import microtest  # noqa: E402 - imported after the prewarm and the UDP shim
import network  # noqa: E402 - imported after the prewarm and the UDP shim
import run_generic_integration  # noqa: E402 - imported after the prewarm and the UDP shim
from _async_harness import cancel, run_timed  # noqa: E402 - imported after the prewarm and the UDP shim
from _digital_twin_construction_scenarios import load_device  # noqa: E402 - imported after the prewarm and the UDP shim
from _fake_time import DrivenTime  # noqa: E402 - imported after the prewarm and the UDP shim
from _generated_module import ERROR_LEVEL, boot_entry_watchdog, write_error_level_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _offline_ntp_config import write_offline_ntp_config  # noqa: E402 - imported after the prewarm and the UDP shim
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_devices import wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Protocol, TypeVar

    from launch import _Plan

    T = TypeVar("T")

    class SensorReader(Protocol):
        # What a test here asks of a bus-attached reader: its sample and its streak.
        _datastruct: object
        _err_cnt_internal: int

    class Transfer(Protocol):
        # One of machine.I2C's transfer methods, whatever its arguments.
        def __call__(self, *args: object, **kwargs: object) -> object: ...


# Each driver's soft reset as the bytes its setup writes: (to the chip's own address, or None for the general call).
_RESET_WRITES = {
    "scd30": (True, b"\xd3\x04"),  # soft reset 0xD304, Interface Description 1.4.10
    "bmp3xx": (True, b"\x7e\xb6"),  # CMD register 0x7E, softreset 0xB6, DS001 4.3.22
    "isl29125": (True, b"\x00\x46"),  # 0x46 written to register 0x00 resets every register, FN8424 p9
    "sgp40": (False, b"\x06"),  # the general call reset to address 0x00, SGP40 datasheet Table 17
}
_READS = ("readfrom_into", "readfrom_mem")  # the twin's read forms; readfrom_mem_into delegates
# @tunable l2.setup_resets_wait_s = 60.0
_WAIT_S = 60.0
# @tunable l2.setup_resets_run_bound_s = 60.0
_RUN_BOUND_S = 60.0
# The reading field that proves a driver read (as the bus-hazard tier's _I2C_DRIVER_HEALTH_FIELD).
_HEALTH_FIELD = {"scd30": "CO2", "sgp40": "VOC", "bmp3xx": "Pres", "isl29125": "Lux"}

_scratch = TmpScratch("dt_setup_resets_" + device)  # per device: two devices' jobs of this file may run at once
microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)
module = load_device(device)
plan = wiring_plan(device)


def _attachments() -> "list[tuple[str, str, int]]":
    # (bus, driver, address) for every I2C chip of the plan, in bus order.
    return [(bus, a["driver"], a["address"]) for bus in sorted(plan["buses"]) for a in plan["buses"][bus]]


async def _driven(clock: "DrivenTime", what: str, coro: "Coroutine[object, object, T]") -> "T":
    task = asyncio.get_event_loop().create_task(coro)
    await _until(clock, what, task.done)
    return await task


def _recorded(seen: "list[tuple[str, int, bytes]]", op: str, real: "Transfer") -> "Transfer":
    # The transfer as it was, each call recorded as (op, address, the bytes a write sent).
    def transfer(*args: object, **kwargs: object) -> object:
        data = b""
        if op == "writeto":
            data = bytes(cast("bytes", args[1]))
        seen.append((op, cast("int", args[0]), data))
        return real(*args, **kwargs)

    return transfer


async def _start() -> "asyncio.Task[None]":
    # The setup list, then the tasks and timers under the real supervisor, as main() starts them.
    runner_plan: _Plan = cast("_Plan", plan)
    run_generic_integration._wire_uart_crossover(module, runner_plan)  # before the setups (CLAUDE.md "Known hang cause")
    sysfunct = module.sysfunct
    await sysfunct.run_setups(module._collect_setups())
    await sysfunct.start_tasks(module._collect_task_starters(), task_names=module._collect_task_names())
    await sysfunct.start_timers(module._collect_trigger_starters(), module._collect_timer_starters())
    return asyncio.get_event_loop().create_task(sysfunct.supervise_tasks())


async def _stop_graph(supervisor: "asyncio.Task[None]") -> None:
    sysfunct = module.sysfunct
    await cancel(supervisor)
    for task in sysfunct._tasks:
        if task is not None:
            await cancel(task)
    conn = getattr(module, "conn", None)
    if conn is not None and conn._dns_server_task is not None:  # started inside the WiFi service, not by start_tasks()
        await cancel(conn._dns_server_task)


async def _until(clock: "DrivenTime", what: str, condition: "Callable[[], bool]") -> None:
    try:
        await clock.run_until(condition, int(_WAIT_S * 1000))
    except AssertionError as e:
        raise AssertionError(f"{device}: {what} - {e}") from None


def test_every_chip_is_reset_once_by_its_setup_after_its_identity_check() -> None:
    # The graph booted on one driven clock until every reader read once: per chip, exactly one reset write, and a
    # read from the chip before it (setup identifies the chip first, so a wrong chip is never reset).
    async def scenario(clock: "DrivenTime") -> "dict[str, list[tuple[str, int, bytes]]]":
        machine.reset_peripherals()
        network.reset_interfaces()
        machine.configure_wiring(plan)
        cfg_path = _scratch.dir()
        write_offline_ntp_config(cfg_path)
        write_error_level_config(cfg_path)
        watchdog = boot_entry_watchdog(module, device)
        await _driven(clock, "the construction never finished", module.build_system(watchdog=watchdog, cfg_path=cfg_path, debug=ERROR_LEVEL, web_host="127.0.0.1", web_port=0))
        seen: dict[str, list[tuple[str, int, bytes]]] = {}
        for bus_name in sorted(plan["buses"]):
            fake = getattr(module, bus_name)._i2c
            seen[bus_name] = []
            for op in ("writeto",) + _READS:  # MicroPython has no starred item in a tuple display
                setattr(fake, op, _recorded(seen[bus_name], op, getattr(fake, op)))
        readers: list[tuple[str, SensorReader]] = [(a["driver"], getattr(module, a["driver"] + ("_" + a["name_ext"] if a["name_ext"] else ""))) for bus in sorted(plan["buses"]) for a in plan["buses"][bus]]
        supervisor = await _driven(clock, "the setups and the graph never started", _start())
        try:
            await _until(clock, "a reader never read once", lambda: all(r._err_cnt_internal == 0 and getattr(r._datastruct, _HEALTH_FIELD[d]) is not None for d, r in readers))
        finally:
            await _driven(clock, "the graph never stopped", _stop_graph(supervisor))
        return seen

    async def on_clock() -> "dict[str, list[tuple[str, int, bytes]]]":
        # One driven clock for every src module holding asyncio and the twin's machine and network (as the timer-pool tier).
        with DrivenTime(*[m for name, m in sorted(sys.modules.items()) if (name.startswith("asy_") or name in ("machine", "network")) and getattr(m, "asyncio", None) is asyncio], sleeps=True) as clock:
            return await scenario(clock)

    seen = run_timed(on_clock(), timeout_s=_RUN_BOUND_S)
    for bus_name, driver, address in _attachments():
        own, reset = _RESET_WRITES[driver]
        target = address if own else 0x00
        log = seen[bus_name]
        resets = [i for i, (op, to, data) in enumerate(log) if op == "writeto" and to == target and data == reset]
        assert len(resets) == 1, f"{device} {bus_name}: {driver} got {len(resets)} reset write(s) {reset!r} to {target:#04x}, expected one"
        reads = [i for i, (op, to, _data) in enumerate(log) if op in _READS and to == address]
        assert reads and reads[0] < resets[0], f"{device} {bus_name}: {driver} was reset before any read identified it (reads at {reads[:3]}, reset at {resets[0]})"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
