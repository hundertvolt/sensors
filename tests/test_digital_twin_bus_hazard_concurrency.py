"""Digital-twin tier: boots the REAL sensortask_wozi.py and sensortask_dev.py object graphs (full
build_system() + the real task/timer starters, matching test_digital_twin_sensortask_integration.py's
own test_watchdog_is_never_starved_while_every_real_task_runs_concurrently pattern) against the real
digital_twin buses, and proves SPECIFICATION.md Part C.8's locking model holds under genuine
concurrent load - at twin speed/determinism, not real hardware. Complements
tests_hardware/flash/test_bus_concurrency.py (real hardware, dev variant only, since wozi is never
physically flashed per CLAUDE.md's hard rule) and tests/test_bus_hazard_multi_device.py (fast mock
bus, no real chip-protocol fidelity): this is the only tier that can exercise wozi's own real
SGP40+BMP3xx pairing at all, since wozi never touches real silicon.

Bus topology exercised here (both real, current wirings - see sensortask_wozi.py/sensortask_dev.py's
own construction comments and digital_twin/machine.py's _wire_i2c_devices(), the canonical
per-variant topology declaration used by both this file and the twin itself):
  - wozi (default profile): i2c1 = SGP40 + BMP3xx sharing a bus; i2c0 = SCD30 alone.
  - dev:                    i2c1 = SCD30 + SGP40 sharing a bus; i2c0 = BMP3xx alone.

**Standing rule - read before adding a new bus-facing device to src/ or a new variant to
sensortask_*.py:** add a matching boot+concurrency test here for the new topology too, and update
digital_twin/machine.py's own _wire_i2c_devices() first (this file's own boot will otherwise fail
loudly with a NAK, not silently miss coverage) - see SPECIFICATION.md Part C.8's own note on this.
"""

import asyncio
import sys

sys.path.insert(0, "ext")  # same convention as test_digital_twin_sensortask_integration.py's own comment
sys.path.insert(0, "digital_twin")

import machine  # noqa: E402

import sensortask_dev  # noqa: E402
import sensortask_wozi  # noqa: E402

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


_TMP_DIR = "tests/_tmp"
_next_dir = 0
_next_port = 19400  # a fresh, non-privileged, test-file-local range - avoids any TIME_WAIT/port
# collision with test_digital_twin_sensortask_integration.py's own 19100+ range in the (unlikely,
# since each tests/test_*.py file is its own Unix-port process) event both ever ran in one process.


def _sweep_stale_tmp_dirs(prefix: str) -> None:
    import os

    try:
        entries = os.listdir(_TMP_DIR)
    except OSError:
        return
    for entry in entries:
        if not entry.startswith(prefix):
            continue
        dir_path = _TMP_DIR + "/" + entry
        try:
            for filename in os.listdir(dir_path):
                try:
                    os.remove(dir_path + "/" + filename)
                except OSError:
                    pass
            os.rmdir(dir_path)
        except OSError:
            pass


_sweep_stale_tmp_dirs("dtbh_")


def _tmp_cfg_dir() -> str:
    import os

    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    _next_dir += 1
    path = _TMP_DIR + "/dtbh_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass
    return path + "/"


def _next_test_port() -> int:
    global _next_port
    _next_port += 1
    return _next_port


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _feed_watchdog_periodically(watchdog: "Any") -> None:
    while True:
        watchdog.feed()
        await asyncio.sleep(1.0)


_GENERAL_CALL_ENTRY = ("writeto", 0x00, b"\x06", True)


async def _run_real_task_graph_and_assert_healthy(module: "Any", shared_bus_log: "Any", run_seconds: float) -> None:
    # Shared scenario body for both variants below - starts the exact real timer/task starters
    # build_system() itself would (module._collect_task_starters()/_collect_timer_starters()),
    # matching test_watchdog_is_never_starved_while_every_real_task_runs_concurrently's own proven
    # pattern, then asserts the real concurrent run produced fresh data from every sensor and never
    # starved the watchdog - not just "didn't crash".
    assert module.watchdog is not None and module.sysfunct is not None
    assert module.sgp_reader is not None and module.bmp_reader is not None and module.scd_reader is not None
    await module.sysfunct.start_timers(module._collect_timer_starters())
    tasks = [starter() for starter in module._collect_task_starters()]
    tasks.append(asyncio.get_event_loop().create_task(_feed_watchdog_periodically(module.watchdog)))
    try:
        await asyncio.sleep(run_seconds)
        assert module.watchdog.would_have_triggered_count == 0

        sgp_data = await module.sgp_reader.get_data()
        bmp_data = await module.bmp_reader.get_data()
        scd_data = await module.scd_reader.get_data()
        assert sgp_data.VOC is not None, "SGP40 never produced real data under concurrent bus load"
        assert bmp_data.Pres is not None, "BMP3xx never produced real data under concurrent bus load"
        assert scd_data.CO2 is not None, "SCD30 never produced real data under concurrent bus load"

        # The real SGP40_I2C._reset() general-call broadcast (SPECIFICATION.md Part C.8's "Known
        # structural gap" finding) must have actually fired at least once during this run (SGP40's
        # own real startup path always calls it), landing concurrently with its bus-sharing
        # sibling's own real startup/running - proof the whole system stays healthy through that,
        # not just that the broadcast is theoretically harmless in isolation.
        assert _GENERAL_CALL_ENTRY in shared_bus_log, "SGP40's general-call reset never fired during this run - test isn't exercising the real hazard window"
    finally:
        for task in tasks:
            await _cancel(task)


def test_wozi_real_task_graph_survives_concurrent_bus_load_including_a_real_general_call() -> None:
    # wozi's real, production wiring: SGP40 + BMP3xx share i2c1 (never SCD30, on i2c0 alone) - the
    # one pairing real hardware can never confirm, since wozi is never physically flashed
    # (CLAUDE.md's hard rule) - this twin run is the actual, complete verification for it.
    machine.configure_i2c_wiring("wozi")
    port = _next_test_port()

    async def scenario() -> None:
        await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert sensortask_wozi.i2c1 is not None and sensortask_wozi.i2c1._i2c is not None
        await _run_real_task_graph_and_assert_healthy(sensortask_wozi, sensortask_wozi.i2c1._i2c.log, run_seconds=9.0)

    run_timed(scenario(), timeout_s=20.0)


def test_dev_real_task_graph_survives_concurrent_bus_load_including_a_real_general_call() -> None:
    # dev's real bench wiring: SCD30 + SGP40 share i2c1 (BMP3xx alone on i2c0) - the pairing
    # tests_hardware/flash/test_bus_concurrency.py exercises on real hardware; this twin run gives
    # the same pairing fast, deterministic, every-CI-push coverage alongside that real-hardware proof.
    machine.configure_i2c_wiring("dev")
    port = _next_test_port()

    async def scenario() -> None:
        await sensortask_dev.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
        assert sensortask_dev.i2c1 is not None and sensortask_dev.i2c1._i2c is not None
        await _run_real_task_graph_and_assert_healthy(sensortask_dev, sensortask_dev.i2c1._i2c.log, run_seconds=9.0)

    run_timed(scenario(), timeout_s=20.0)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
