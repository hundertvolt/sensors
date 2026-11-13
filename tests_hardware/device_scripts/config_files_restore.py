"""Isolated-driver device script: writes back the config files a bench test saved through config_files_dump.py - the
`files` render extra, each entry "<name>:<base64 bytes>" - verbatim, one flash write per file, owned by the gated test
that passes them; reports the names it wrote. Nothing else is touched."""

import binascii

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


def _main() -> None:
    wdt = arm()
    written: list[str] = []
    for entry in BENCH.get("files", []):
        name, _, text = entry.partition(":")
        with open(name, "wb") as f:  # the owned write: the saved bytes, verbatim
            f.write(binascii.a2b_base64(text))
        written.append(name)
        wdt.feed()
    fact("written", written)
    done()


_main()
