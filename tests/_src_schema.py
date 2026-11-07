"""src_schema() reads a src/ module's config schema const(), typed as asy_config_manager's ConfigSchema. It is apart
from _src_const.py because host code shares that module (tests_hardware/bench/_load.py), and the host type-check
sees no src/."""

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

from _src_const import src_const

if TYPE_CHECKING:
    from asy_config_manager import ConfigSchema


def src_schema(path: str, name: str) -> "ConfigSchema":
    # A config schema's shape: a tuple of (name, type, default, min, max, special) rows, each named and typed by str.
    value = src_const(path, name)
    if not isinstance(value, tuple) or not all(isinstance(row, tuple) and len(row) == 6 and isinstance(row[0], str) and isinstance(row[1], str) for row in value):
        raise TypeError(f"{name} in {path} is {value!r}, not a config schema")
    return value
