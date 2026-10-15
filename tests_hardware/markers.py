"""The one marker table: tests_hardware/conftest.py registers it, and so does tests_scripts/conftest.py,
which loads bench modules carrying these marks. Each gate names what it spends and the flag that
selects it (--allow-<marker>, or --soak-duration for the one valued gate)."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

MARKERS: dict[str, str] = {
    "soak_duration": "passive observation over one named duration; skipped unless --soak-duration",
    "multi_day_rollover": "the tick rollover observed over REST on the tick-offset test image, about 2 h; skipped unless --allow-multi-day-rollover",
    "flash_cycle": "reflashes the board (flash wear); skipped unless --allow-flash-cycle",
    "persistence_write": (
        "the test itself spends a limited-endurance write - the RP2040 flash filesystem, or SCD30 NVM: a PUT /sensors to the "
        "SCD30 spends one write per changed field, one per AmbPres or ForceCalRef sent and one per ContMeas=false, none for an "
        "unchanged TempOffset/MeasInterval/Altitude/SelfCal - deselected unless --allow-persistence-write; a shared "
        "prerequisite write stays unmarked, tests_hardware/README.md"
    ),
    "scd30_extra_write": "further SCD30 NVM writes beyond what persistence_write admits; always carried with it; deselected unless both flags",
    "neopixel_sweep": "needs the NeoPixel-to-ISL29125 rig; skipped unless --allow-neopixel-sweep",
    "toolchain_reverify": "full toolchain re-verification; skipped unless --allow-toolchain-reverify",
    "destructive_last": "informational: runs after every other test of its module",
    "role_reversal": "informational: the bench radio stops hosting br0-wifi-ap to join the DUT's own hotspot",
    "over_provisioned_image": "informational: meaningful only on a deliberately over-provisioned build (HEAP_FRAGMENTATION_MEASUREMENTS.md archive §7R.2, image B)",
}


def register(config: "pytest.Config") -> None:
    for name, text in MARKERS.items():
        config.addinivalue_line("markers", f"{name}: {text}")
