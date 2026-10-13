"""Boots a generated device module as its boot entry does, for every test tier: one WDT with the boot
entry's own timeout, construction, then the one-time setup list. The caller loads the module itself,
at its own named site (SPECIFICATION.md F.1); this file loads nothing by name."""

import json
import os

import machine

from asy_config_manager import config_filename

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from types import ModuleType

    from machine import WDT

# RFC 5737 TEST-NET-1: a literal address routed nowhere, so no sync attempt resolves a name or leaves the host;
# no fallback server either. The product's own flat config-file format, two keys of the NTP store.
_OFFLINE_NTP_CONFIG = {"NTPHost": "192.0.2.1", "DNSFallback": ""}
_WATCHDOG_LINE = "watchdog = WDT(timeout="


def _src_str_const(path: str, name: str) -> str:
    # A shipped string const()'s value, read from its source: a const() is not a module attribute on MicroPython.
    with open(path) as f:
        for line in f:
            if line.startswith(name + " = const("):
                value: str = json.loads(line.split("const(", 1)[1].split(")", 1)[0])
                return value
    raise AssertionError(name + " not found in " + path)


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


def write_offline_ntp_config(cfg_dir: str) -> None:
    # Only when absent: a file a test planted, or an earlier boot of the same directory wrote, stays as it is.
    path = config_filename(cfg_dir, _src_str_const("src/asy_ntp_client.py", "_NAME"))
    try:
        os.stat(path)
    except OSError:
        with open(path, "w") as f:
            f.write(json.dumps(_OFFLINE_NTP_CONFIG))
