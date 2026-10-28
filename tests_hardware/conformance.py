"""Host side of the chip conformance probes: runs a probe on the twin through TwinBoard at both GC stages and diffs it
against the same probe on silicon, physical keys compared only in an independent form."""

from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import pytest
import twin_board
from harness import REPO_ROOT

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


class ProbeTable(NamedTuple):
    # One probe's host table: its script, the keys that are a function of what falls on the part rather than of the
    # protocol, and the independent form (a range, a CRC validity, a monotonic relation) a physical key must hold in both.
    probe: Path
    physical_keys: "frozenset[str]"
    independent_checks: "Mapping[str, Callable[[str], bool]]"


# The ISL29125's physical keys: the probe derives a separate yes/no key for every structural property of each, and
# those are compared verbatim - so nothing here is unchecked, only checked in a light-independent form.
ISL29125 = ProbeTable(
    REPO_ROOT / "tests_hardware" / "device_scripts" / "isl29125_mock_conformance_probe.py",
    frozenset({
        "B05_green_low_byte_now",
        "B05_status_burst_2",
        "C09_read_8_from_0x0d_rollover",
        "E01_counts_16bit_hi_range",
        "E02_data_partial_read_from_0x0b",
        "E03_data_burst_8_past_end",
        "E04_counts_16bit_lo_range",
        "E05_counts_12bit_lo_range",
        "H07_prst4_ms",
    }),
    {},
)

# @tunable l3.conformance_twin_probe_timeout_s = 180.0
_TWIN_PROBE_TIMEOUT_S = 180.0


def compare(real: "dict[str, str]", twin: "dict[str, str]", physical_keys: "frozenset[str]", independent_checks: "Mapping[str, Callable[[str], bool]]") -> "list[str]":
    # One line per divergence, empty when the twin is faithful: a protocol key verbatim, a physical key through its
    # independent form; a key one side never printed diverges whatever its kind.
    divergences = []
    for key in sorted(set(real) | set(twin)):
        real_value, twin_value = real.get(key, "<absent>"), twin.get(key, "<absent>")
        if key not in real or key not in twin or key not in physical_keys:
            if real_value != twin_value:
                divergences.append(f"{key}: real chip {real_value!r}, twin {twin_value!r}")
            continue
        check = independent_checks.get(key)
        failed = [] if check is None else [side for side, value in (("real chip", real_value), ("twin", twin_value)) if not check(value)]
        if failed:
            divergences.append(f"{key}: {' and '.join(failed)} outside its independent form (real chip {real_value!r}, twin {twin_value!r})")
    return divergences


def parse(output: str) -> "dict[str, str]":
    # KEY=VALUE lines only - a device-side traceback or an mpremote banner is ignored, not parsed.
    parsed: dict[str, str] = {}
    for raw in output.splitlines():
        line = raw.strip()
        key, sep, value = line.partition("=")
        if sep and key and " " not in key and not key.startswith(("File", "Traceback")):
            parsed[key] = value
    return parsed


def run_probe_on_twin(probe: Path, gc_threshold: int) -> "dict[str, str]":
    # The probe's KEY=VALUE lines from a TwinBoard run at `gc_threshold`; a run that never printed DONE=1 raises with its
    # output. No Unix port built skips, naming the build.
    binary = twin_board.unix_port_binary()
    if not binary.is_file():
        pytest.skip(f"MicroPython Unix port not built at {binary} - run scripts/test.sh once")
    output = twin_board.TwinBoard(_TWIN_PROBE_TIMEOUT_S, gc_threshold=gc_threshold).run_isolated(probe, timeout_s=_TWIN_PROBE_TIMEOUT_S)
    parsed = parse(output)
    if parsed.get("DONE") != "1":
        raise AssertionError(f"the twin probe {probe.name} did not run to completion at gc.threshold({gc_threshold}):\n{output}")
    return parsed
