"""Boots a generated device module as its boot entry does, for every test tier: one WDT with the boot
entry's own timeout, construction, then the one-time setup list. The caller loads the module itself,
at its own named site (SPECIFICATION.md F.1); this file loads nothing by name."""

import json
import sys

if "digital_twin/unixport" not in sys.path:
    sys.path.append("digital_twin/unixport")  # the NTP config writer's fake-free directory, behind tests/ on the path

import machine
from _fram_chip_fake import FakeMB85RS2MTA, FakeMB85RS64V
from _generated_tree import require_fresh
from _offline_ntp_config import write_offline_ntp_config

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from types import ModuleType

    from machine import WDT

require_fresh()  # every caller loads a generated module, and this file reads its boot entry

_WATCHDOG_LINE = "watchdog = WDT(timeout="

_BLANK = bytes(4096)


class _FakeMB85RS2MTA(FakeMB85RS2MTA):
    # The 256 KB part as a device wires it: a subclass, since build_system() offers no post-construction hook.
    # One array for every build of the process, blank at each construction: a fresh 256 KB array needs one free
    # run that long, which a long scenario's survivors left nowhere on the settrace binary (12 MemoryErrors).
    _array: "bytearray | None" = None
    _holder: "_FakeMB85RS2MTA | None" = None

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.SIZE = 0  # shadows the class value while the base constructor runs, so it allocates no array
        super().__init__(*args, **kwargs)
        del self.SIZE
        cls = _FakeMB85RS2MTA
        if cls._array is None:
            cls._array = bytearray(self.SIZE)
        for start in range(0, self.SIZE, len(_BLANK)):
            cls._array[start : start + len(_BLANK)] = _BLANK
        if cls._holder is not None:
            cls._holder.memory = None  # type: ignore[assignment]  # an earlier build's chip fails loudly, never writes this one
        cls._holder = self
        self.size = self.SIZE
        self.memory = cls._array
        self._addr_width = 3  # the 3-byte address of a part above 64 KB (DS501-00032 p.9)


# Same "keyed by the real chip's own max_size" table digital_twin/machine.py's _FRAM_RDID_BY_MAX_SIZE
# uses, for the identical reason - derived from each device's own real FRAM. A third real size needs
# one new entry here, the same narrow addition twin_wiring.py's own table would need.
_FRAM_FAKE_BY_MAX_SIZE: "dict[int, type[FakeMB85RS64V]]" = {
    0x2000: FakeMB85RS64V,
    0x40000: _FakeMB85RS2MTA,
}


def _watchdog_timeout_ms(module: "ModuleType", device: str) -> int:
    # The timeout the device's own boot entry arms, read from that file beside the module: never a copied value.
    if module.__name__ != "sensortask_" + device or not module.__file__:
        raise ValueError(f"{module.__name__} is not the loaded module of device {device!r}")
    folder = module.__file__.rsplit("/", 1)[0] if "/" in module.__file__ else "."
    path = folder + "/sensortask_" + device + "_main.py"
    with open(path) as f:
        found = [line.strip() for line in f if line.strip().startswith(_WATCHDOG_LINE)]
    if len(found) != 1:
        raise ValueError(f"{path} arms {len(found)} watchdogs, not one `{_WATCHDOG_LINE}<ms>)` line")
    return int(found[0][len(_WATCHDOG_LINE) :].split(")", 1)[0])


def boot_entry_watchdog(module: "ModuleType", device: str) -> "WDT":
    # The one WDT the device's boot entry arms first, for a caller that drives main() itself.
    return machine.WDT(timeout=_watchdog_timeout_ms(module, device))


async def boot_generated(module: "ModuleType", device: str, *, offline_ntp: bool = True, **kwargs: "str | int | None") -> "tuple[ModuleType, WDT]":
    # The boot entry's order up to its main(): the watchdog first, then construction and the setup list.
    # kwargs are build_system()'s own; offline_ntp writes the offline NTP config into cfg_path first.
    if offline_ntp:
        cfg_path = kwargs.get("cfg_path")
        if not isinstance(cfg_path, str) or not cfg_path:
            raise ValueError("offline_ntp needs a cfg_path to write into, never the working directory")
        write_offline_ntp_config(cfg_path)
    watchdog = boot_entry_watchdog(module, device)
    await module.build_system(watchdog=watchdog, **kwargs)
    await module.sysfunct.run_setups(module._collect_setups())
    return module, watchdog


def fram_fake_class(device: str) -> "type[FakeMB85RS64V]":
    # The device's FRAM fake, by its plan's one SPI attachment (unpacking fails loudly on any other count): here, beside
    # the boot, so the heap probe (tests/_boot_contiguity_probe.py) boots without the scenario library's import-time state.
    with open(f"build/generated_src/sensortask_{device}_wiring_plan.json") as f:
        (spi_attachment,) = json.load(f)["spi"].values()
    return _FRAM_FAKE_BY_MAX_SIZE[spi_attachment["max_size"]]
