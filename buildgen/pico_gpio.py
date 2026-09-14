"""The Pico W's real, fixed GPIO-to-peripheral mapping, transcribed from
RP-008312-DS-2-pico-w-datasheet.pdf Figure 2 (printed p.4) - see
BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md's "Pico W GPIO / bus pin legality" section."""

WIRELESS_RESERVED_GPIOS = frozenset({23, 24, 25, 29})
_GPIO_MIN = 0
_GPIO_MAX = 29

# (sda_gpio, scl_gpio, i2c_bus_id) - alternates I2C0/I2C1 every 2 GPIOs; even=SDA, odd=SCL within
# each pair. GP22/GP28 have no I2C function at all (simply absent from this table).
_I2C_PAIRS = (
    (0, 1, "i2c0"),
    (2, 3, "i2c1"),
    (4, 5, "i2c0"),
    (6, 7, "i2c1"),
    (8, 9, "i2c0"),
    (10, 11, "i2c1"),
    (12, 13, "i2c0"),
    (14, 15, "i2c1"),
    (16, 17, "i2c0"),
    (18, 19, "i2c1"),
    (20, 21, "i2c0"),
    (26, 27, "i2c1"),
)

# (block_start_gpio, spi_bus_id) - each block is 4 contiguous GPIOs, roles fixed at
# offset 0=MISO(RX)/1=CSn/2=SCK/3=MOSI(TX) within the block. GP20-22/GP26-28 have no SPI function.
_SPI_BLOCKS = ((0, "spi0"), (4, "spi0"), (8, "spi1"), (12, "spi1"), (16, "spi0"))
_SPI_ROLE_BY_OFFSET = {0: "miso", 1: "csn", 2: "sck", 3: "mosi"}

# (tx_gpio, rx_gpio, uart_id) - unlike _I2C_PAIRS/_SPI_BLOCKS this is an irregular set of specific
# GPIO pairs (no fixed arithmetic stride); transcribed directly from Figure 2's per-pin UART0/UART1
# labels (RP-008312-DS-2-pico-w-datasheet.pdf, Figure 2, printed p.4). GP0/GP1 is UART0's own
# "default" pairing per the datasheet's own legend; the other four pairs are equally legal alternates.
# GP2/3/6/7/10/11/14/15/18/19/20/21/22/26/27/28 have no UART function shown at all (simply absent
# from Figure 2, same convention as _I2C_PAIRS/_SPI_BLOCKS). GPIO23/24/25/29 are wireless-reserved
# (printed p.7: dedicated CYW43439 SPI/IRQ/ADC-sense functions) and are not part of Figure 2's user
# GPIO table at all, so they were never candidates for this table in the first place - same as
# I2C_ROLE/SPI_ROLE above, gpio_exists()'s WIRELESS_RESERVED_GPIOS exclusion still applies uniformly
# on top. src/asy_uart_driver.py's own module comment (GPIO24/25=UART1, GPIO28/29=UART0) is a true
# but board-inapplicable claim about the RP2040 die's silicon-level mux capability, not a claim about
# this board's own broken-out header pins - it does not contradict this table.
_UART_PAIRS = (
    (0, 1, "uart0"),
    (4, 5, "uart1"),
    (8, 9, "uart1"),
    (12, 13, "uart0"),
    (16, 17, "uart0"),
)


def _build_i2c_role() -> "dict[int, tuple[str, str]]":
    role: dict[int, tuple[str, str]] = {}
    for sda, scl, bus in _I2C_PAIRS:
        role[sda] = (bus, "sda")
        role[scl] = (bus, "scl")
    return role


def _build_spi_role() -> "dict[int, tuple[str, str]]":
    role: dict[int, tuple[str, str]] = {}
    for start, bus in _SPI_BLOCKS:
        for offset, name in _SPI_ROLE_BY_OFFSET.items():
            role[start + offset] = (bus, name)
    return role


def _build_uart_role() -> "dict[int, tuple[str, str]]":
    role: dict[int, tuple[str, str]] = {}
    for tx, rx, bus in _UART_PAIRS:
        role[tx] = (bus, "tx")
        role[rx] = (bus, "rx")
    return role


I2C_ROLE = _build_i2c_role()
SPI_ROLE = _build_spi_role()
UART_ROLE = _build_uart_role()


def gpio_exists(pin: int) -> bool:
    """Is this a real, usable Pico W GPIO number - in range and not wireless-reserved? Doesn't
    imply any particular peripheral function is available on it (see I2C_ROLE/SPI_ROLE for that)."""
    return _GPIO_MIN <= pin <= _GPIO_MAX and pin not in WIRELESS_RESERVED_GPIOS
