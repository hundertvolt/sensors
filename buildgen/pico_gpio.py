"""The Pico W's fixed GPIO-to-peripheral mapping, transcribed row by row from the RP2040 datasheet's
Table 279 (F1 SPI, F2 UART, F3 I2C; printed pp.237-238) - see SPECIFICATION.md Part L.6.5. GPIO23/24/25/29
drive the wireless chip on the Pico W (Pico W datasheet, printed p.7), so they are never offered."""

WIRELESS_RESERVED_GPIOS = frozenset({23, 24, 25, 29})
_GPIO_MIN = 0
_GPIO_MAX = 29

# Table 279 as printed: (gpio, spi bus, spi role, uart bus, uart role, i2c bus, i2c role), SPI's RX/TX
# written as the miso/mosi a bus field names. Every user GPIO has one function of each kind; only the
# roles a bus field can claim below are offered (a chip select is any free GPIO, UART CTS/RTS unused).
_TABLE_279: "tuple[tuple[int, str, str, str, str, str, str], ...]" = (
    (0, "spi0", "miso", "uart0", "tx", "i2c0", "sda"),
    (1, "spi0", "csn", "uart0", "rx", "i2c0", "scl"),
    (2, "spi0", "sck", "uart0", "cts", "i2c1", "sda"),
    (3, "spi0", "mosi", "uart0", "rts", "i2c1", "scl"),
    (4, "spi0", "miso", "uart1", "tx", "i2c0", "sda"),
    (5, "spi0", "csn", "uart1", "rx", "i2c0", "scl"),
    (6, "spi0", "sck", "uart1", "cts", "i2c1", "sda"),
    (7, "spi0", "mosi", "uart1", "rts", "i2c1", "scl"),
    (8, "spi1", "miso", "uart1", "tx", "i2c0", "sda"),
    (9, "spi1", "csn", "uart1", "rx", "i2c0", "scl"),
    (10, "spi1", "sck", "uart1", "cts", "i2c1", "sda"),
    (11, "spi1", "mosi", "uart1", "rts", "i2c1", "scl"),
    (12, "spi1", "miso", "uart0", "tx", "i2c0", "sda"),
    (13, "spi1", "csn", "uart0", "rx", "i2c0", "scl"),
    (14, "spi1", "sck", "uart0", "cts", "i2c1", "sda"),
    (15, "spi1", "mosi", "uart0", "rts", "i2c1", "scl"),
    (16, "spi0", "miso", "uart0", "tx", "i2c0", "sda"),
    (17, "spi0", "csn", "uart0", "rx", "i2c0", "scl"),
    (18, "spi0", "sck", "uart0", "cts", "i2c1", "sda"),
    (19, "spi0", "mosi", "uart0", "rts", "i2c1", "scl"),
    (20, "spi0", "miso", "uart1", "tx", "i2c0", "sda"),
    (21, "spi0", "csn", "uart1", "rx", "i2c0", "scl"),
    (22, "spi0", "sck", "uart1", "cts", "i2c1", "sda"),
    (23, "spi0", "mosi", "uart1", "rts", "i2c1", "scl"),
    (24, "spi1", "miso", "uart1", "tx", "i2c0", "sda"),
    (25, "spi1", "csn", "uart1", "rx", "i2c0", "scl"),
    (26, "spi1", "sck", "uart1", "cts", "i2c1", "sda"),
    (27, "spi1", "mosi", "uart1", "rts", "i2c1", "scl"),
    (28, "spi1", "miso", "uart0", "tx", "i2c0", "sda"),
    (29, "spi1", "csn", "uart0", "rx", "i2c0", "scl"),
)
# The roles a [bus.*] wire field claims (validate.py's _BUS_PIN_ROLE), per peripheral kind.
_I2C_BUS_ROLES = frozenset({"sda", "scl"})
_SPI_BUS_ROLES = frozenset({"miso", "sck", "mosi"})
_UART_BUS_ROLES = frozenset({"tx", "rx"})


def _role_tables() -> "tuple[dict[int, tuple[str, str]], dict[int, tuple[str, str]], dict[int, tuple[str, str]]]":
    # Each kind's (bus, role) per offered GPIO: Table 279's rows minus the wireless four and the unclaimable roles.
    i2c: dict[int, tuple[str, str]] = {}
    spi: dict[int, tuple[str, str]] = {}
    uart: dict[int, tuple[str, str]] = {}
    for gpio, spi_bus, spi_role, uart_bus, uart_role, i2c_bus, i2c_role in _TABLE_279:
        if gpio in WIRELESS_RESERVED_GPIOS:
            continue
        if i2c_role in _I2C_BUS_ROLES:
            i2c[gpio] = (i2c_bus, i2c_role)
        if spi_role in _SPI_BUS_ROLES:
            spi[gpio] = (spi_bus, spi_role)
        if uart_role in _UART_BUS_ROLES:
            uart[gpio] = (uart_bus, uart_role)
    return i2c, spi, uart


I2C_ROLE, SPI_ROLE, UART_ROLE = _role_tables()


def gpio_exists(pin: int) -> bool:
    # Is this a real, usable Pico W GPIO number - in range and not wireless-reserved? Doesn't
    # imply any particular peripheral function is available on it (see I2C_ROLE/SPI_ROLE for that).
    return _GPIO_MIN <= pin <= _GPIO_MAX and pin not in WIRELESS_RESERVED_GPIOS
