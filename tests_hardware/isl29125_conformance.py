"""Host side of the ISL29125 mock-conformance check: runs device_scripts/
isl29125_mock_conformance_probe.py against digital_twin/_isl29125_chip.py under the MicroPython
Unix port, and diffs that against the same probe's real-hardware output key by key."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROBE = REPO_ROOT / "tests_hardware" / "device_scripts" / "isl29125_mock_conformance_probe.py"

# Keys whose value is a function of the actual light falling on the part, not of the protocol. The
# probe derives a separate yes/no key for every structural property of these, and those ARE
# compared - so nothing here is simply unchecked, only checked in a light-independent form.
PHYSICAL_KEYS = frozenset({
    "B05_green_low_byte_now",
    "B05_status_burst_2",
    "C09_read_8_from_0x0d_rollover",
    "E01_counts_16bit_hi_range",
    "E02_data_partial_read_from_0x0b",
    "E03_data_burst_8_past_end",
    "E04_counts_16bit_lo_range",
    "E05_counts_12bit_lo_range",
    "H07_prst4_ms",
})

_TWIN_ENTRY = """import sys
sys.path.insert(0, "digital_twin")
sys.path.insert(0, "src")
import machine
machine.configure_i2c_wiring("dev")
exec(open(sys.argv[1]).read())
"""


def unix_port_binary() -> Path:
    # Same location scripts/test.sh uses, and the same PICO_TOOLCHAIN_DIR override.
    toolchain_dir = Path(os.environ.get("PICO_TOOLCHAIN_DIR", Path.home() / "pico-toolchain"))
    return toolchain_dir / "micropython" / "ports" / "unix" / "build-standard" / "micropython"


def parse(output: str) -> dict[str, str]:
    """KEY=VALUE lines only - a device-side traceback or an mpremote banner is ignored, not parsed."""
    parsed: dict[str, str] = {}
    for raw in output.splitlines():
        line = raw.strip()
        key, sep, value = line.partition("=")
        if sep and key and " " not in key and not key.startswith(("File", "Traceback")):
            parsed[key] = value
    return parsed


def run_probe_against_twin(timeout_s: float = 180.0) -> dict[str, str]:
    binary = unix_port_binary()
    if not binary.is_file():
        raise FileNotFoundError(f"MicroPython Unix port not built at {binary} - run scripts/test.sh once first")
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
        handle.write(_TWIN_ENTRY)
        entry = handle.name
    try:
        env = dict(os.environ, TZ="UTC", MICROPYPATH="digital_twin:src:frozen_modules:.frozen:.")
        proc = subprocess.run(  # noqa: S603 - every argument is a repo-controlled path, no shell
            [str(binary), "-X", "heapsize=8M", entry, str(PROBE)],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout_s, check=False, env=env,
        )
    finally:
        Path(entry).unlink(missing_ok=True)
    parsed = parse(proc.stdout)
    if parsed.get("DONE") != "1":
        raise AssertionError(f"the twin probe did not run to completion (exit {proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
    return parsed


def compare(real: dict[str, str], twin: dict[str, str]) -> list[str]:
    """Returns one human-readable line per protocol-key divergence; empty means the mock is faithful."""
    divergences = []
    for key in sorted(set(real) | set(twin)):
        if key in PHYSICAL_KEYS:
            continue
        real_value, twin_value = real.get(key, "<absent>"), twin.get(key, "<absent>")
        if real_value != twin_value:
            divergences.append(f"{key}: real chip {real_value!r}, mock {twin_value!r}")
    return divergences
