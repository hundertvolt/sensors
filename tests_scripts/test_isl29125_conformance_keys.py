"""Guards the ISL29125 conformance probe against going quietly blind: every illumination-dependent
key it excludes from the real-vs-twin diff must either name a light-independent stand-in key that IS
compared, or declare, deliberately, that it has none."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests_hardware"))

import isl29125_conformance  # noqa: E402

PROBE = REPO_ROOT / "tests_hardware" / "device_scripts" / "isl29125_mock_conformance_probe.py"


def emitted_keys() -> set[str]:
    """Every key the probe actually prints - read from its source, not from a hand-kept list."""
    return set(re.findall(r'emit\(\s*"([A-Za-z0-9_]+)"', PROBE.read_text()))


def test_every_excluded_key_is_one_the_probe_actually_emits() -> None:
    # A stale exclusion silently widens nothing, but it hides that the key it named is gone - and
    # the next reader trusts the table.
    unknown = sorted(set(isl29125_conformance.PHYSICAL_KEYS) - emitted_keys())
    assert not unknown, f"PHYSICAL_KEYS excludes key(s) the probe never emits: {unknown}"


def test_every_named_stand_in_key_is_one_the_probe_actually_emits() -> None:
    keys = emitted_keys()
    missing = sorted({s for stand_ins in isl29125_conformance.PHYSICAL_KEYS.values() for s in stand_ins} - keys)
    assert not missing, f"PHYSICAL_KEYS names stand-in key(s) the probe never emits: {missing}"


def test_no_stand_in_key_is_itself_excluded_from_the_diff() -> None:
    # The whole point of a stand-in is that it gets compared; excluding one would restore the blindness.
    excluded = set(isl29125_conformance.PHYSICAL_KEYS)
    self_defeating = sorted({s for stand_ins in isl29125_conformance.PHYSICAL_KEYS.values() for s in stand_ins} & excluded)
    assert not self_defeating, f"stand-in key(s) are themselves excluded from the diff: {self_defeating}"


@pytest.mark.parametrize(
    "key",
    ["C09_read_8_from_0x0d_rollover", "E03_data_burst_8_past_end", "E05_counts_12bit_lo_range", "H07_prst4_ms", "B05_status_burst_2"],
)
def test_the_structural_properties_with_a_real_light_independent_form_declare_one(key: str) -> None:
    # Pinned by name: these five carry protocol properties the first real-silicon run found the fake
    # getting wrong (SPECIFICATION.md Part C.11.1), so losing their stand-in must fail here rather
    # than quietly reduce the probe to comparing keys that were never in doubt.
    assert isl29125_conformance.PHYSICAL_KEYS[key], f"{key} carries a real protocol property but declares no light-independent stand-in"


def test_the_past_end_behaviour_is_compared_rather_than_excluded() -> None:
    # The regression this whole file exists to prevent: "past 0x0E the part clocks zeros and does NOT
    # roll over to the device ID" is one of the five original divergences, and both keys that could
    # show it (C09, E03) carry light-dependent data bytes, so both were excluded outright.
    compared = emitted_keys() - set(isl29125_conformance.PHYSICAL_KEYS)
    assert "C09_past_end_zeros_not_rollover" in compared
    assert "E03_past_end_zeros" in compared


def test_compare_flags_a_stand_in_key_that_diverges() -> None:
    # The table is only worth checking if a divergence in a stand-in key actually fails the diff.
    real = {"C09_past_end_zeros_not_rollover": "yes", "C09_read_8_from_0x0d_rollover": "1122000000000000"}
    twin = {"C09_past_end_zeros_not_rollover": "no", "C09_read_8_from_0x0d_rollover": "aabb7d0000000000"}
    divergences = isl29125_conformance.compare(real, twin)
    assert len(divergences) == 1, divergences
    assert "C09_past_end_zeros_not_rollover" in divergences[0]


def test_compare_still_ignores_the_illumination_dependent_half() -> None:
    real = {"E01_counts_16bit_hi_range": "100,200,300"}
    twin = {"E01_counts_16bit_hi_range": "7,8,9"}
    assert isl29125_conformance.compare(real, twin) == []


def test_compare_catches_a_key_missing_from_either_side() -> None:
    # A truncated probe run must diverge, never silently compare fewer keys.
    assert isl29125_conformance.compare({"DONE": "1"}, {}) != []
    assert isl29125_conformance.compare({}, {"DONE": "1"}) != []
