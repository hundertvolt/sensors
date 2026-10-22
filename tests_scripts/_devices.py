"""The real device set, found in devices/*.toml, not listed (scripts/_devices.sh: same rule for the shell runners), and
the tests' shared queries: DEVICE_NAMES, device_toml(), devices_with(driver), bench_device(), so a seventh device joins
every suite unedited and a test needing a device with a property picks it from the TOMLs, never by name."""

from pathlib import Path

import tomllib

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


def bench_device(devices_dir: Path = DEVICES_DIR) -> str:
    # The one device whose TOML sets [device] bench = true, as tests_hardware/harness.py's bench_device() reads it;
    # none or several fails naming the files. A leaked zz_test_* fixture never counts.
    flagged = []
    for path in sorted(devices_dir.glob("*.toml")):
        table = tomllib.loads(path.read_text(encoding="utf-8")).get("device", {})
        if not path.stem.startswith("zz_test_") and isinstance(table, dict) and table.get("bench") is True:
            flagged.append(path.name)
    if len(flagged) != 1:
        raise AssertionError(f"[device] bench = true is set in {flagged or 'no device TOML'} under {devices_dir} - exactly one board is on the bench")
    return flagged[0].removesuffix(".toml")


def device_toml(device: str) -> Path:
    return DEVICES_DIR / f"{device}.toml"


def devices_with(driver: str) -> "list[str]":
    # The devices whose TOML declares at least one [[instance]] of `driver`, in DEVICE_NAMES' order.
    found = []
    for device in DEVICE_NAMES:
        instances = tomllib.loads(device_toml(device).read_text(encoding="utf-8")).get("instance", [])
        if any(isinstance(i, dict) and i.get("driver") == driver for i in instances):
            found.append(device)
    return found
