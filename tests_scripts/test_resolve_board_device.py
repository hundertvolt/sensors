"""Covers tests_hardware/harness.py's resolve_board_device() over fabricated /sys, /dev and
by-id trees: which device it identifies (USB vendor ID, never a bare ttyACM scan) and which name
it returns for it (the stable by-id symlink). No hardware - the directories are injectable."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

from harness import _NO_BOARD_DEVICE, HardwareNotAvailableError, resolve_board_device

_PICO_VENDOR = "2e8a"
_ARDUINO_VENDOR = "2341"  # the bench's UART peer: a real ACM device that is NOT the board under test


class _Tree:
    """One fabricated host: `/sys/class/tty`, `/dev` and `/dev/serial/by-id`, laid out exactly as
    the kernel does (by-id entries are `../../ttyACMx` relative symlinks)."""

    def __init__(self, root: Path) -> None:
        self.sys_tty = root / "sys" / "class" / "tty"
        self.dev = root / "dev"
        self.by_id = self.dev / "serial" / "by-id"
        self._usb = root / "sys" / "devices" / "usb"
        for d in (self.sys_tty, self.dev, self.by_id, self._usb):
            d.mkdir(parents=True, exist_ok=True)

    def add(self, tty: str, vendor: str, *, by_id_name: str | None = None) -> None:
        usb_device = self._usb / tty
        interface = usb_device / f"{tty}:1.0"
        interface.mkdir(parents=True)
        (usb_device / "idVendor").write_text(f"{vendor}\n")
        (self.sys_tty / tty).mkdir()
        (self.sys_tty / tty / "device").symlink_to(interface)
        (self.dev / tty).write_text("")
        if by_id_name is not None:
            (self.by_id / by_id_name).symlink_to(Path("..") / ".." / tty)

    def resolve(self) -> str:
        return resolve_board_device(by_id_dir=self.by_id, sys_tty_dir=self.sys_tty, dev_dir=self.dev)


def _pico_by_id(serial_no: str) -> str:
    return f"usb-MicroPython_Board_in_FS_mode_{serial_no}-if00"


def test_a_single_board_resolves_to_its_stable_by_id_symlink(tmp_path: Path) -> None:
    tree = _Tree(tmp_path)
    tree.add("ttyACM0", _PICO_VENDOR, by_id_name=_pico_by_id("e66130100f372d34"))
    # The by-id name, not /dev/ttyACM0: the index moves when a hard reset re-enumerates the device.
    assert tree.resolve() == str(tree.by_id / _pico_by_id("e66130100f372d34"))


def test_a_foreign_acm_device_is_never_selected_even_when_it_sorts_first(tmp_path: Path) -> None:
    # The regression this consolidation exists for: the bench's Arduino UART peer enumerating ahead
    # of the board. A bare `sorted(/dev/ttyACM*)[0]` scan would hand back the Arduino and let
    # mpremote open ITS port; vendor-ID identification cannot.
    tree = _Tree(tmp_path)
    tree.add("ttyACM0", _ARDUINO_VENDOR)
    tree.add("ttyACM1", _PICO_VENDOR, by_id_name=_pico_by_id("e66130100f372d34"))
    assert tree.resolve() == str(tree.by_id / _pico_by_id("e66130100f372d34"))


def test_a_foreign_acm_device_alone_reports_no_board_rather_than_being_opened(tmp_path: Path) -> None:
    tree = _Tree(tmp_path)
    tree.add("ttyACM0", _ARDUINO_VENDOR)
    assert tree.resolve() == _NO_BOARD_DEVICE


def test_two_boards_is_a_hard_error_naming_both_rather_than_a_silent_pick(tmp_path: Path) -> None:
    tree = _Tree(tmp_path)
    tree.add("ttyACM0", _PICO_VENDOR, by_id_name=_pico_by_id("aaaaaaaaaaaaaaaa"))
    tree.add("ttyACM1", _PICO_VENDOR, by_id_name=_pico_by_id("bbbbbbbbbbbbbbbb"))
    with pytest.raises(HardwareNotAvailableError) as excinfo:
        tree.resolve()
    assert "ttyACM0" in str(excinfo.value) and "ttyACM1" in str(excinfo.value)
    assert "MPREMOTE_DEVICE" in str(excinfo.value), "the error must name the escape hatch, not just refuse"


def test_nothing_attached_yields_a_path_that_cannot_exist(tmp_path: Path) -> None:
    # The `board` fixture skips on an unreachable device, so this tier stays collectible with
    # nothing attached - which requires a path that fails to open, not a raise.
    assert _Tree(tmp_path).resolve() == _NO_BOARD_DEVICE
    assert not Path(_NO_BOARD_DEVICE).exists()


def test_an_unreadable_sysfs_still_resolves_through_the_by_id_glob(tmp_path: Path) -> None:
    # Identification falls back to the by-id name, which is Pico-specific in its own right, so the
    # fallback cannot pick a stranger either.
    tree = _Tree(tmp_path)
    tree.add("ttyACM0", _PICO_VENDOR, by_id_name=_pico_by_id("e66130100f372d34"))
    missing_sysfs = tmp_path / "sys" / "class" / "absent"
    assert resolve_board_device(by_id_dir=tree.by_id, sys_tty_dir=missing_sysfs, dev_dir=tree.dev) == str(
        tree.by_id / _pico_by_id("e66130100f372d34"),
    )


def test_a_board_with_no_by_id_entry_falls_back_to_its_dev_node(tmp_path: Path) -> None:
    tree = _Tree(tmp_path)
    tree.add("ttyACM0", _PICO_VENDOR)
    assert tree.resolve() == str(tree.dev / "ttyACM0")
