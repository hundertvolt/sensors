"""The Pico W's real, fixed GPIO-to-peripheral mapping, transcribed from
RP-008312-DS-2-pico-w-datasheet.pdf Figure 2 (printed p.4) - see
SPECIFICATION.md Part L.6.5."""

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

# (tx_gpio, rx_gpio, uart_id), an irregular set with no arithmetic stride unlike _I2C_PAIRS/
# _SPI_BLOCKS, transcribed from Figure 2's per-pin labels (pico-w-datasheet.pdf, printed p.4).
# GP0/GP1 is UART0's default pairing per the legend; the other four are equally legal.

# A GPIO absent from this table has no UART function in Figure 2, the same convention the I2C and
# SPI tables use. GPIO23/24/25/29 never appear in that user-GPIO table at all, being
# wireless-reserved (p.7), and gpio_exists()'s own exclusion still applies on top.

# asy_uart_driver.py's module comment names GPIO24/25 and GPIO28/29 - a true claim about the
# RP2040 die's silicon mux, not about this board's broken-out header pins. It does not
# contradict this table.
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
