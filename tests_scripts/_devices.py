"""The real device set, discovered from devices/*.toml rather than listed. Six test modules carried
their own copy of the same six names; a seventh device would have been generated, built and shipped
while every one of those suites silently kept testing the old six."""

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEVICES_DIR = _REPO_ROOT / "devices"

# Sorted, so parametrization order is stable across filesystems rather than inode order. The six
# hand-written lists this replaces were each in their own arbitrary order, none of which anything
# depended on - the tests_scripts/ suites are independent per device.
DEVICE_NAMES: "list[str]" = sorted(p.stem for p in DEVICES_DIR.glob("*.toml"))

# A leaked live-tree fixture (tests_scripts/conftest.py's own reclamation, scripts/test.sh's sweep)
# must never be mistaken for a real device: the pytest tier runs concurrently with everything else,
# so devices/ can genuinely hold a zz_test_*.toml for the length of one test.
DEVICE_NAMES = [name for name in DEVICE_NAMES if not name.startswith("zz_test_")]

assert DEVICE_NAMES, f"no device TOMLs found in {DEVICES_DIR} - every device-parametrized suite would silently collect nothing"


def device_toml(device: str) -> Path:
    return DEVICES_DIR / f"{device}.toml"
