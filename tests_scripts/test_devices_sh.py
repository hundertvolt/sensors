"""scripts/_devices.sh, the shell runners' derived device set: derived_devices lists tests_scripts/_devices.py's
DEVICE_NAMES without the zz_test_ fixtures, distinct_devices one per hardware_family, both fail on an empty
devices/, and require_device refuses every other name with exit 2, listing them; off the real tree, on a copy."""

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, distinct_devices

REPO_ROOT = Path(__file__).resolve().parent.parent
_LIB = REPO_ROOT / "scripts" / "_devices.sh"
_TIMEOUT_S = 30


def _call(lib: Path, *lines: str) -> subprocess.CompletedProcess[str]:
    # A caller in the runners' own shell mode, sourcing the library and running the given lines.
    script = "\n".join(["set -euo pipefail", f"source {shlex.quote(str(lib))}", *lines])
    return subprocess.run(["/bin/bash", "-c", script], capture_output=True, text=True, check=False, timeout=_TIMEOUT_S)


def _tree(tmp_path: Path, *stems: str, families: "dict[str, str] | None" = None) -> Path:
    # A throwaway checkout holding the library and a devices/ with one fixture TOML per stem, naming its family if given.
    (tmp_path / "scripts").mkdir()
    shutil.copy2(_LIB, tmp_path / "scripts" / "_devices.sh")
    (tmp_path / "devices").mkdir()
    for stem in stems:
        family = (families or {}).get(stem)
        text = "# fixture\n" if family is None else f'[device]\nname = "{stem}"\nhardware_family = "{family}"\n\n[device.wiring]\n'
        (tmp_path / "devices" / f"{stem}.toml").write_text(text, encoding="utf-8")
    return tmp_path / "scripts" / "_devices.sh"


def test_the_shell_set_equals_the_python_set_over_the_real_devices() -> None:
    done = _call(_LIB, "derived_devices")
    assert (done.returncode, done.stderr) == (0, ""), done
    assert done.stdout.splitlines() == DEVICE_NAMES


def test_a_fixture_toml_is_never_a_device_and_the_order_is_the_byte_order(tmp_path: Path) -> None:
    lib = _tree(tmp_path, "fixture_b", "Fixture_c", "zz_test_x", "fixture_a")
    done = _call(lib, "derived_devices")
    assert (done.returncode, done.stdout.splitlines()) == (0, ["Fixture_c", "fixture_a", "fixture_b"]), done


@pytest.mark.parametrize("function", ["derived_devices", "distinct_devices"])
def test_an_empty_devices_directory_fails_naming_it(tmp_path: Path, function: str) -> None:
    lib = _tree(tmp_path, "zz_test_only")
    done = _call(lib, f'devices="$({function})"', "echo proceeded")
    assert (done.returncode, done.stdout) == (1, ""), done
    assert done.stderr.strip() == "error: no devices/*.toml found"


def test_the_distinct_set_is_one_device_per_hardware_family_over_the_real_devices() -> None:
    done = _call(_LIB, "distinct_devices")
    assert (done.returncode, done.stderr) == (0, ""), done
    assert done.stdout.splitlines() == distinct_devices()


def test_two_devices_of_one_family_yield_one_entry_and_a_familyless_device_stays(tmp_path: Path) -> None:
    # The first of a family in byte order stands for it, the device tests/_twin_devices.py's distinct_wirings() picks.
    lib = _tree(tmp_path, "fixture_c", "fixture_b", "fixture_a", "fixture_d", families={"fixture_c": "f", "fixture_b": "f", "fixture_d": "g"})
    done = _call(lib, "distinct_devices")
    assert (done.returncode, done.stdout.splitlines(), done.stderr) == (0, ["fixture_a", "fixture_b", "fixture_d"], ""), done
    assert done.stdout.splitlines() == distinct_devices(tmp_path / "devices")
    done = _call(lib, "require_device fixture_c", "echo proceeded")
    assert (done.returncode, done.stdout, done.stderr) == (0, "proceeded\n", ""), "every member of a family stays a device"


def test_a_derived_device_is_accepted_silently(tmp_path: Path) -> None:
    lib = _tree(tmp_path, "fixture_a", "fixture_b")
    done = _call(lib, "require_device fixture_b", "echo proceeded")
    assert (done.returncode, done.stdout, done.stderr) == (0, "proceeded\n", "")


@pytest.mark.parametrize("name", ["no_such_device", "zz_test_x", "", "../devices/fixture_a", "fixture_a.toml"], ids=["unknown", "fixture", "empty", "path", "file-name"])
def test_every_other_name_exits_2_listing_the_valid_devices(tmp_path: Path, name: str) -> None:
    lib = _tree(tmp_path, "fixture_b", "fixture_a", "zz_test_x")
    done = _call(lib, f"require_device {shlex.quote(name)}", "echo proceeded")
    assert (done.returncode, done.stdout) == (2, ""), done
    assert done.stderr.strip() == f"error: no devices/{name}.toml - valid devices: fixture_a fixture_b"


def test_the_library_refuses_to_run_as_a_script() -> None:
    done = subprocess.run(["/bin/bash", str(_LIB)], capture_output=True, text=True, check=False, timeout=_TIMEOUT_S)
    assert (done.returncode, done.stderr.strip()) == (2, "error: source scripts/_devices.sh, do not run it")


def test_sourcing_it_changes_none_of_the_callers_shell_options(tmp_path: Path) -> None:
    # Read in the calling shell itself: a $(...) would not show errexit, which bash clears in command substitutions.
    before, after = tmp_path / "before", tmp_path / "after"
    probe = f'opts() {{ printf "%s\\n" "$-"; set +o; shopt -p; }}; opts >{before}; source {shlex.quote(str(_LIB))}; opts >{after}'
    done = subprocess.run(["/bin/bash", "-c", probe], capture_output=True, text=True, check=False, timeout=_TIMEOUT_S)
    assert (done.returncode, done.stderr) == (0, ""), done
    assert after.read_text(encoding="utf-8") == before.read_text(encoding="utf-8")
