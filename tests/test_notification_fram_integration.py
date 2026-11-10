"""Full-stack FRAM integration of the Neopixel and the notification service off one shared FRAMManager: the pixel, which
has nothing it can fail at, takes no FRAM chunk even with a FRAM store in its config; the service's one chunk is the
first allocated, and its history survives a simulated reboot. Mocked at the SPI bus, not at FRAMManager's boundary."""

from _async_harness import run
from _error_codes import code
from _fram_builders import make_fram_manager
from _tmp_scratch import TmpScratch

from asy_base_classes import ValueRef
from asy_fram_manager import FRAMChunk, FRAMManager
from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationService, NotificationSignal
from asy_print_log import LogConfig, PrintLogHistoryStore

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_notification_service import _LocalTime  # the callback contract this file's stub fills
    from asy_print_log import ErrorLog

_FIELD_WARN_CO2 = (("WarnCO2", "int", 1600, 0, 3000, None),)
_PLANTED = code("E", "CALLBACK")  # any catalog code; the tests pin separation and survival, not the code

# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("notify_fram")


async def _local_time_stub() -> "_LocalTime | None":
    return None


class _FakeSource:
    # A producer whose field is always None: the test pins the chunk layout, not a threshold.
    WarnCO2 = None

    async def get_data(self) -> "_FakeSource":
        return self


def _make_notify(manager: FRAMManager, cfg_path: str) -> NotificationService:
    # The same signals in the same order every time: the FRAM layout must decode identically across
    # the simulated reboot.
    return NotificationService(
        _request_signal_stub,
        _local_time_stub,
        (NotificationSignal("WarnCO2", ValueRef(_FakeSource(), "WarnCO2"), _FIELD_WARN_CO2, (1, 0, 0)),),
        cfg_path=cfg_path,
        log=LogConfig(manager, 10, None),
    )


def _make_pixel(manager: FRAMManager) -> NeopixelDriver:
    return NeopixelDriver(0, log=LogConfig(manager, 10, None))


async def _request_signal_stub(_r: int, _g: int, _b: int, _t: float) -> bool:
    return True


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


def test_the_pixel_takes_no_fram_chunk_and_the_service_takes_the_first() -> None:
    manager, _chip = make_fram_manager()
    run(manager.setup())
    pixel = _make_pixel(manager)
    notify = _make_notify(manager, _tmp_cfg_dir())
    run(notify.setup())
    alone, _chip2 = make_fram_manager()
    run(alone.setup())
    first = alone.get_chunk(8, owner="probe")
    assert type(pixel.pr).__name__ == "PrintLog", type(pixel.pr)  # a console printer: no history, no store
    assert isinstance(notify.pr, PrintLogHistoryStore)
    assert isinstance(notify.pr.fram, FRAMChunk) and isinstance(first, FRAMChunk)
    assert notify.pr.fram._block_addr[0] == first._block_addr[0]  # nothing was allocated before it


def test_the_service_history_survives_a_simulated_reboot() -> None:
    cfg_path = _tmp_cfg_dir()  # same path across the simulated reboot, as a real device's config file
    manager1, chip = make_fram_manager()
    run(manager1.setup())
    _make_pixel(manager1)
    notify1 = _make_notify(manager1, cfg_path)

    async def before_reboot() -> None:
        await notify1.setup()
        await notify1.pr.err_s("notify before reboot", errno=_PLANTED)

    run(before_reboot())

    manager2, _chip2 = make_fram_manager(chip=chip)  # same underlying chip, fresh manager/driver/coordinator objects
    run(manager2.setup())
    _make_pixel(manager2)
    notify2 = _make_notify(manager2, cfg_path)  # same registration order/shape as before the reboot

    async def after_reboot() -> "ErrorLog":
        await notify2.setup()
        return await notify2.pr.get_log("NOTIFY")

    assert run(after_reboot())["NOTIFY"]["ErrNum"][-1] == _PLANTED


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
