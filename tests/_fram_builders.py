"""make_fram_manager(): a FRAMManager over the FRAM chip fake on SPI bus 0, as the tests' FRAM-backed modules use it.
`part` builds another chip class (a bigger part, a fault-injecting subclass); `chip` builds over an existing chip
instead, so a simulated reboot's fresh manager meets the memory the last one wrote."""

from _fram_chip_fake import FakeMB85RS64V

import asy_spi_driver
from asy_fram_manager import FRAMManager
from asy_print_log import DEFAULT_LOG, LogConfig
from asy_spi_driver import SPI


def make_fram_manager(
    max_size: int = 0x2000, part: "type[FakeMB85RS64V]" = FakeMB85RS64V, *, chip: "FakeMB85RS64V | None" = None, history_length: "int | None" = None,
) -> "tuple[FRAMManager, FakeMB85RS64V]":
    saved = asy_spi_driver._SPI
    asy_spi_driver._SPI = part  # type: ignore[misc]  # the chip fake is what asy_spi_driver constructs, for this bus only
    try:
        bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    finally:
        asy_spi_driver._SPI = saved  # type: ignore[misc]
    log = DEFAULT_LOG if history_length is None else LogConfig(None, history_length, None)
    manager = FRAMManager(bus, 1, max_size=max_size, log=log)
    if chip is not None:
        manager.fram._spidev.spi._spi = chip
    own = manager.fram._spidev.spi._spi
    assert isinstance(own, FakeMB85RS64V)
    return manager, own
