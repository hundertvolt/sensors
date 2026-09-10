"""The Pico W's real, fixed GPIO-to-peripheral mapping (RP-008312-DS-2-pico-w-datasheet.pdf,
Figure 2, printed p.4 - transcribed and verified directly against the datasheet, not from
training memory; see BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md §4.3 axis 10 for the full
derivation, including the GP23/24/25/29-reserved inference). This project targets the Pico W
alone (project owner confirmed) so this table is a fixed constant, not board-parameterized.

Two independent facts per claimed pin: whether the GPIO number itself is a real, usable pin
(0-29, excluding the four wireless-reserved numbers) - applies to every claimed pin device-wide -
and, for a bus's own wire pins only, which peripheral index and role (SDA/SCL, MISO/CSn/SCK/MOSI)
that specific GPIO is hardwired to."""

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


I2C_ROLE = _build_i2c_role()
SPI_ROLE = _build_spi_role()


def gpio_exists(pin: int) -> bool:
    """Is this a real, usable Pico W GPIO number - in range and not wireless-reserved? Doesn't
    imply any particular peripheral function is available on it (see I2C_ROLE/SPI_ROLE for that)."""
    return _GPIO_MIN <= pin <= _GPIO_MAX and pin not in WIRELESS_RESERVED_GPIOS
