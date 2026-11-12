"""Isolated-driver device script, read-only: every production config_*.cfg file of the board's filesystem root, each as
its verbatim bytes in base64 under one `files` fact (name -> text), so a bench test can save them before a config reset
and write them back after. Opens each file for reading only and writes nothing; the real WiFi credential is in them."""

import binascii
import os

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm

_PREFIX = "config_"
_SUFFIX = ".cfg"


def _main() -> None:
    wdt = arm()
    files: dict[str, str] = {}
    for name in sorted(os.listdir()):
        if name.startswith(_PREFIX) and name.endswith(_SUFFIX):
            with open(name, "rb") as f:
                files[name] = binascii.b2a_base64(f.read()).decode().strip()
            wdt.feed()
    fact("files", files)
    done()


_main()
