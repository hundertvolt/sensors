"""The C-stack peak of the bench build on silicon: the I2C leaves and the FRAM driver's SPI commands record stack_use()
by phase (setup batch, a fed window of the started tasks and timers, one GET /status); then a second GET /status writes
the deepest FRAM-backed log entry, its end apart. The host holds the peak to half of 7,936 B, not the twin's."""

import asyncio
import errno
import os
import sys

import _bench_device as device  # rendered: the bench device's generated module
import machine
import micropython
from microdot import Microdot, Request

from asy_base_classes import set_utc_valid

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Protocol

    from _shared.facts import done, fact
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

    class _Leaf(Protocol):
        def __call__(self, *args: object, **kwargs: object) -> object: ...


BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# A scratch directory: every setup() finds its file absent here and writes its defaults once, never a production file.
_SCRATCH_CFG_PATH = "hwtest-scratch/"
# PICO_STACK_SIZE 0x2000 (ports/rp2/CMakeLists.txt:661) minus MICROPY_STACK_CHECK_MARGIN 256 (ports/rp2/mpconfigport.h:125,
# py/cstack.h:43), v1.29.0: past it the check raises RuntimeError.
_C_STACK_LIMIT = 0x2000 - 256
# @tunable l3.c_stack_budget_window_ms = 10000
_WINDOW_MS = 10000  # about ten read cycles of every reader the build starts
_I2C_LEAVES = ("readfrom_into", "writeto", "writeto_then_readfrom", "get_register_bytes", "get_register_struct", "get_bits", "set_bits", "set_register_struct")
# The driver's SPI commands, where every FRAM chain ends: a wrapper on set_values() would add its own frame below it.
_FRAM_LEAVES = ("_send_and_read", "_send_and_write", "_send_command")
# Each phase's deepest reading per leaf; "provoked" is the GET /status that writes the deepest FRAM-backed log entry.
peaks: dict[str, dict[str, int]] = {"setup": {}, "run": {}, "status": {}, "provoked": {}}
_phase = ["setup"]  # the phase running, which _main() advances


async def _main() -> None:
    wdt = arm()
    try:  # an aborted run's leftover first (none: ENOENT)
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_errno", e.errno)
    os.mkdir(_SCRATCH_CFG_PATH)
    try:
        await device.build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)
        sysfunct, fram = device.sysfunct, device.fram
        assert sysfunct is not None, "the generated build constructs SystemService unconditionally"
        for bus_name in BENCH["bus"]:
            bus = getattr(device, bus_name, None)
            for leaf in _I2C_LEAVES if bus_name.startswith("i2c") and bus is not None else ():
                setattr(bus, leaf, _recording(bus_name + "." + leaf, getattr(bus, leaf)))
        driver = fram.fram if fram is not None else None
        for leaf in _FRAM_LEAVES if driver is not None else ():
            setattr(driver, leaf, _recording("fram." + leaf, getattr(driver, leaf)))
        await sysfunct.run_setups(device._collect_setups())
        _phase[0] = "run"
        await sysfunct.start_tasks(device._collect_task_starters(), task_names=device._collect_task_names())
        await sysfunct.start_timers(device._collect_trigger_starters(), device._collect_timer_starters())
        await fed_sleep_ms(wdt, _WINDOW_MS)
        webserver = device.webserver
        assert webserver is not None, "the generated build constructs the webserver unconditionally"
        app = webserver._app
        assert isinstance(app, Microdot)
        # One GET /status: the top of the deepest chain tests_scripts/test_await_depth.py finds.
        _phase[0] = "status"
        res = await app.dispatch_request(Request(app, ("127.0.0.1", 0), "GET", "/status", "1.0", {}))  # the app's real dispatch
        assert res.status_code == 200, "Microdot answers a raising handler with a 500: only a 200 ran the handler to its end"
        # Then its deepest FRAM-backed log entry, once: after a sync, the local time reads NTP's config store as setup()
        # leaves it on a directory at its path, and CFGMGR_NTP logs E34 into FRAM (asy_config_manager.py:359).
        ntp = device.ntp
        assert ntp is not None, "the bench build constructs the NTP client"
        set_utc_valid()
        ntp.cfgmgr.valid = False
        entries = ntp.cfgmgr.pr._err_count
        _phase[0] = "provoked"
        res = await app.dispatch_request(Request(app, ("127.0.0.1", 0), "GET", "/status", "1.0", {}))
        assert res.status_code == 200, "Microdot answers a raising handler with a 500: only a 200 ran the handler to its end"
        logged = ntp.cfgmgr.pr._err_count - entries
        wdt.feed()
    finally:
        pixel = getattr(device, "neopixel", None)  # the build constructs the rig's NeoPixel where the TOML wires one
        if pixel is not None:
            pixel.off()
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
        # The boot-phase mark build_system() left: cleared, so the next reset does not read as a boot failure.
        phase = machine.mem_backup(1)
        for i in range(len(phase)):
            phase[i] = 0
    quiet = [(use, name, leaf) for name in ("setup", "run", "status") for leaf, use in peaks[name].items()]
    peak, at, chain = max(quiet) if quiet else (None, None, None)
    fact("chain", chain)
    fact("phase", at)
    fact("leaf_peaks", peaks)
    fact("c_stack_peak" if sys.platform == "rp2" else "twin_c_stack_peak", peak)
    fact("c_stack_limit", _C_STACK_LIMIT)
    fact("provoked_end", max(peaks["provoked"].values(), default=None))
    fact("provoked_logged", logged)
    done()


def _recording(name: str, leaf: "_Leaf") -> "_Leaf":
    # The leaf, called as before, after its caller's stack use is recorded: the deepest chain reaching it sets the peak.
    def wrapped(*args: object, **kwargs: object) -> object:
        use = micropython.stack_use()
        table = peaks[_phase[0]]
        if use > table.get(name, 0):
            table[name] = use
        return leaf(*args, **kwargs)

    return wrapped


asyncio.run(_main())
