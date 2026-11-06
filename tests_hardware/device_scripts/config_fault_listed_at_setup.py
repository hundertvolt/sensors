"""Isolated-driver device script: the bench build over a scratch config directory, SYSTEM's store file damaged after
the construction and before any setup reads it; the setups repair it and run_setups() lists it as a config fault. The
owned writes are the damage and its repair; every other store writes its absent file's defaults once."""

import asyncio
import errno
import json
import os

import _bench_device as device  # rendered: the bench device's generated module
import machine

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm

# A scratch directory: every other setup() finds its file absent here and writes its defaults once.
_SCRATCH_CFG_PATH = "hwtest-scratch/"
_DAMAGE = b"\x00{not json"  # what a cut write leaves (system_command_config_reset.py's own)


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
        sysfunct = device.sysfunct
        if sysfunct is None:
            raise RuntimeError("the generated build constructed no SystemService")
        path = sysfunct.cfgmgr._config_file
        with open(path, "wb") as f:  # the damage: construction reads no file, so the setups meet it first
            f.write(_DAMAGE)
        fact("damaged", sysfunct.cfgmgr.module_name)
        await sysfunct.run_setups(device._collect_setups())
        fact("config_faults", sysfunct.get_config_faults())
        with open(path) as f:
            fact("repaired", isinstance(json.load(f), dict))
    except Exception as e:  # reported; the cleanup below runs either way
        fact("failure", repr(e))
    finally:
        # The scratch directory and build_system()'s boot-phase mark go, the rig dark.
        pixel = getattr(device, "neopixel", None)  # the build constructs the rig's NeoPixel where the TOML wires one
        if pixel is not None:
            pixel.off()
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
        phase = machine.mem_backup(1)
        for i in range(len(phase)):
            phase[i] = 0
    done()


asyncio.run(_main())
