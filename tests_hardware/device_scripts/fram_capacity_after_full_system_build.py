"""Isolated-driver device script: the real-hardware FRAM capacity check - after the bench build's construction and its
setup list, every logger of every FRAM-wired module holds a real FRAM chunk rather than a silently degraded RAM-only
fallback; the host compares the set with buildgen's. mpremote-only (tests_hardware/README.md says why)."""

import asyncio
import errno
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
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# A scratch directory: every setup() finds its file absent here and writes its defaults once, never a production file.
_SCRATCH_CFG_PATH = "hwtest-scratch/"


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
    found: list[str] = []
    ram_only: list[str] = []
    try:
        await device.build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)
        # main()'s next step, so the check reads the system as a real boot leaves it: construction allocates no chunk.
        sysfunct, fram = device.sysfunct, device.fram
        assert sysfunct is not None, "the generated build constructs SystemService unconditionally"
        await sysfunct.run_setups(device._collect_setups())
        fact("fram_present", fram is not None)
        for label in BENCH["fram_wired"]:
            for logger in getattr(device, label).get_loggers():
                if getattr(logger, "fram", None) is None:
                    ram_only.append(label + "." + logger.name)
                elif logger.name not in found:
                    found.append(logger.name)
        if fram is not None:
            fact("allocated_size", fram._allocated_size)
            fact("size", fram.size)
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
    fact("found_fram_loggers", sorted(found))
    fact("ram_only", ram_only)  # one entry per logger at most: bounded by the build
    done()


asyncio.run(_main())
