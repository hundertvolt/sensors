"""Isolated-driver device script: confirms the real, deployed `sensortask_dev` object graph's total
FRAM chunk allocation fits the real MB85RS2MTA chip's own capacity, and that every FRAM-backed
module actually got a real chunk - see tests_hardware/README.md's Eleventh pass."""

import asyncio

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

# Dynamic, not a static `import sensortask_dev` (unlike this file's own sibling
# heap_headroom_after_full_system_build.py) - see tests_hardware/README.md's Eleventh pass for why;
# same __import__() convention tests/test_sensortask.py already uses, no loss of type-checking.
sensortask_dev: "Any" = __import__("sensortask_dev")

_FRAM_CHUNK_MODULE_NAMES = ("scd30", "sgp40", "bmp3xx", "isl29125", "neopixel", "notification")


def _module_chunk_problem(instance: object, name: str) -> "str | None":
    pr = getattr(instance, "pr", None)
    if pr is None:
        return f"{name} has no .pr logger at all"
    if not hasattr(pr, "fram"):
        return f"{name}'s logger was never constructed with fram= at all"
    if pr.fram is None:
        return f"{name}'s FRAM-backed logger chunk allocation failed (FRAM out of capacity)"
    return None


async def _main() -> None:
    try:
        await sensortask_dev.build_system(cfg_path="", web_host="127.0.0.1", web_port=8080)
    except Exception as e:
        print(f"RESULT: FAIL build_system() raised on real hardware: {e!r}")
        return

    fram = sensortask_dev.fram
    if fram is None:
        print("RESULT: FAIL sensortask_dev.fram (AsyFramManager) was not constructed")
        return
    if fram.allocated_size > fram.size:
        print(f"RESULT: FAIL AsyFramManager over-allocated: {fram.allocated_size} > {fram.size} bytes")
        return

    sysfunct = sensortask_dev.sysfunct
    if sysfunct is None:
        print("RESULT: FAIL sensortask_dev.sysfunct was not constructed")
        return
    problem = _module_chunk_problem(sysfunct, "sysfunct")
    if problem is not None:
        print(f"RESULT: FAIL {problem}")
        return

    for name in _FRAM_CHUNK_MODULE_NAMES:
        instance = getattr(sensortask_dev, name, None)
        if instance is None:  # not every driver is on every device.toml - dev's own is fixed, but
            continue  # keep this generic rather than hardcoding dev's exact instance set twice.
        problem = _module_chunk_problem(instance, name)
        if problem is not None:
            print(f"RESULT: FAIL {problem}")
            return

    sgp40 = sensortask_dev.sgp40
    if sgp40 is not None and sgp40.ts_storage is None:
        print("RESULT: FAIL sgp40's VOC-backup timestamped FRAM chunk allocation failed (FRAM out of capacity)")
        return

    print(f"RESULT: PASS real FRAM allocation fits: {fram.allocated_size}/{fram.size} bytes, every module got a real chunk")


asyncio.run(_main())
