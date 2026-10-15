"""Included into device scripts at render: a module's ErrorLog entry as one fact value - the (type, number) pairs the
capped history still holds, its slot count, and ErrCount, which counts past the history: a history with no free slot
and a count above its entries has lost some, so a "no error" claim needs all three (asy_print_log.py get_log())."""

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_print_log import ErrorLog


def log_record(counters: "ErrorLog", name: str) -> "dict[str, object]":
    entry = counters.get(name)
    if entry is None:
        return {"count": 0, "slots": 0, "entries": []}
    types, nums = entry["ErrType"], entry["ErrNum"]
    held = [[types[i], nums[i]] for i in range(min(len(types), len(nums))) if types[i] != "N"]  # no zip(strict=) on MicroPython
    return {"count": entry["ErrCount"], "slots": len(types), "entries": held}
