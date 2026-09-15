"""Host-side parser for the MEMPRESSURE lines tests_hardware/device_modules/memory_pressure.py
prints. Keeps the driver/DUT separation of SPECIFICATION.md Part E.9: the instrument reports over
the serial log, the host reads it there, and nothing interrupts the live system to ask."""

from __future__ import annotations

import re
from dataclasses import dataclass

_REPORT_RE = re.compile(r"MEMPRESSURE mode=(\S+) blocks=(\d+) drops=(\d+) allocfail=(\d+) free=(\d+)")
_ACTIVE_RE = re.compile(r"MEMPRESSURE ACTIVE mode=(\S+) headroom=(\d+) hold_blocks=(\d+) threshold=(-?\d+)")


@dataclass(frozen=True)
class PressureSample:
    mode: str
    blocks: int
    drops: int
    alloc_failures: int
    free: int


def parse_samples(lines: list[str]) -> list[PressureSample]:
    samples = []
    for line in lines:
        m = _REPORT_RE.search(line)
        if m:
            samples.append(PressureSample(m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))))
    return samples


def saw_activation(lines: list[str]) -> bool:
    return any(_ACTIVE_RE.search(line) for line in lines)


def assert_instrument_healthy(samples: list[PressureSample], window_description: str) -> None:
    """The instrument must have been running AND must not itself have run out of memory - a
    fragment-mode allocation failure means its headroom is mis-sized for this workload, so the run
    measured starvation rather than the design under test (SPECIFICATION.md Part I.6)."""
    assert samples, f"no MEMPRESSURE report lines observed during {window_description} - the churn instrument was not running, so this run proves nothing about behaviour under allocator pressure"
    progressed = samples[-1].blocks - samples[0].blocks
    assert progressed > 0, f"the churn instrument made no progress during {window_description} (blocks stuck at {samples[0].blocks}) - it was starved, so nothing was actually under pressure"
    failures = samples[-1].alloc_failures
    assert failures == 0, f"the churn instrument itself hit {failures} MemoryError(s) during {window_description} - its headroom is mis-calibrated for this workload, so this run proves nothing about the code under test"
