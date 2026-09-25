"""Full-stack FRAM integration for the Neopixel promotion: proves asy_neopixel_driver.py's own
PrintLogHistoryStore chunk and asy_notification_service.py's single combined one are genuinely independent, non-overlapping allocations off one shared AsyFramManager, and both survive a simulated reboot.
"""
# Matches the generated device modules' real production topology, both passing fram=fram.
# NotificationCoordinator's combined chunk covers its own fields plus every registered NotificationSignal's
# check-failure logging together, per its staged-registration design.
#
# Mirrors tests/test_fram_integration.py's established pattern: the real chain down to the simulated chip,
# not mocked at AsyFramManager's own boundary.

import asyncio

from _fram_chip_fake import FakeMB85RS64V
from _tmp_scratch import TmpScratch

import asy_spi_driver
from asy_fram_manager import AsyFramChunk, AsyFramManager
from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationCoordinator, NotificationSignal
from asy_spi_driver import SPI
from print_log import PrintLogHistoryStore

# Same one-process-per-test-file swap as the other asy_fram_* test files - see their own comments.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    from asy_notification_service import _LocalTime  # the callback contract this file's stub fills

    T = TypeVar("T")
    from print_log import ErrorLog

_FIELD_WARN_CO2 = (("WarnCO2", "int", 1600, 0, 3000, None),)

# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("notify_fram")


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def make_manager(max_size: int = 0x2000) -> "tuple[AsyFramManager, FakeMB85RS64V]":
    bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = AsyFramManager(bus, 1, max_size=max_size)
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip


class _FakeSource:
    # A controllable NotificationSignal producer (SPECIFICATION.md Part C.14.2) whose configured
    # field is always None - matches the removed _value_stub()'s own always-None return.
    async def get_data(self) -> "_FakeSource":
        return self


async def _local_time_stub() -> "_LocalTime | None":
    return None


async def _request_signal_stub(_r: int, _g: int, _b: int, _t: float) -> bool:
    return True


def make_pixel(manager: AsyFramManager) -> NeopixelDriver:
    return NeopixelDriver(0, fram=manager)


def make_notify(manager: AsyFramManager, cfg_path: str) -> NotificationCoordinator:
    # Same registration order/shape every time this helper is called - required for the FRAM
    # layout (built once in finalize()) to decode identically across a simulated reboot, matching
    # the "number and order of registered signals stays constant" invariant this design relies on.
    coordinator = NotificationCoordinator(_request_signal_stub, _local_time_stub, cfg_path=cfg_path, fram=manager)
    coordinator.register(NotificationSignal("WarnCO2", _FakeSource(), "WarnCO2", _FIELD_WARN_CO2, (1, 0, 0)))
    coordinator.finalize()
    return coordinator


def test_driver_and_notify_service_get_two_independent_non_overlapping_fram_chunks() -> None:
    manager, _chip = make_manager()
    run(manager.setup())
    pixel = make_pixel(manager)
    notify = make_notify(manager, _tmp_cfg_dir())

    async def scenario() -> None:
        await pixel.pr.setup()
        await notify.pr.setup()

    run(scenario())
    assert isinstance(pixel.pr, PrintLogHistoryStore)
    assert isinstance(notify.pr, PrintLogHistoryStore)
    assert isinstance(pixel.pr.fram, AsyFramChunk)
    assert isinstance(notify.pr.fram, AsyFramChunk)
    assert pixel.pr.fram.block_addr != notify.pr.fram.block_addr


def test_driver_and_notify_service_errors_stay_in_separate_histories() -> None:
    manager, _chip = make_manager()
    run(manager.setup())
    pixel = make_pixel(manager)
    notify = make_notify(manager, _tmp_cfg_dir())

    async def scenario() -> "tuple[ErrorLog, ErrorLog]":
        await pixel.pr.setup()
        await notify.pr.setup()
        # NeopixelDriver structurally can't fail on any of its own real code paths (see its own
        # module docstring) - this directly exercises the FRAM-backed history machinery itself,
        # not a real failure this driver would ever hit.
        await pixel.pr.err_s("driver-side", errno=1)
        await notify.pr.err_s("notify-side", errno=1)
        pixel_log = await pixel.pr.get_log("NEOPIXEL")
        notify_log = await notify.pr.get_log("NOTIFY")
        return pixel_log, notify_log

    pixel_log, notify_log = run(scenario())
    assert pixel_log["NEOPIXEL"]["ErrCount"] == 1
    assert notify_log["NOTIFY"]["ErrCount"] == 1


def test_both_histories_survive_a_simulated_reboot() -> None:
    cfg_path = _tmp_cfg_dir()  # same path across the simulated reboot, matching a real device's
    # config file persisting across a reboot too - the FRAM-side assertions below don't depend on
    # this, but it's the correct shape to model.
    manager1, chip = make_manager()
    run(manager1.setup())
    pixel1 = make_pixel(manager1)
    notify1 = make_notify(manager1, cfg_path)

    async def before_reboot() -> None:
        await pixel1.pr.setup()
        await notify1.pr.setup()
        await pixel1.pr.err_s("driver before reboot", errno=1)
        await notify1.pr.err_s("notify before reboot", errno=1)

    run(before_reboot())

    manager2, _chip2 = make_manager()
    manager2.fram._spidev.spi._spi = chip  # same underlying chip, fresh manager/driver/coordinator objects
    run(manager2.setup())
    pixel2 = make_pixel(manager2)
    notify2 = make_notify(manager2, cfg_path)  # same registration order/shape as before the reboot

    async def after_reboot() -> "tuple[ErrorLog, ErrorLog]":
        await pixel2.pr.setup()
        await notify2.pr.setup()
        pixel_log = await pixel2.pr.get_log("NEOPIXEL")
        notify_log = await notify2.pr.get_log("NOTIFY")
        return pixel_log, notify_log

    pixel_log, notify_log = run(after_reboot())
    assert pixel_log["NEOPIXEL"]["ErrNum"][-1] == 1
    assert notify_log["NOTIFY"]["ErrNum"][-1] == 1


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
