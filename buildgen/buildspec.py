"""Per-driver "what does this need from the TOML" facts: required/optional fields, which drivers
sit on a bus, and which have a real TOML-configurable `address` (SPECIFICATION.md's schema note -
datasheet-checked by Session 2, not re-derived here)."""

# The one hand-maintained per-driver table here; everything else buildgen needs is AST-derived
# from src/. It cannot be derived: the shipped TOML field names and src/'s constructor parameter
# names are two independently-evolved naming spaces. Adding a driver adds a row (Part L.6).

# TOML fields every instance of this driver must declare (beyond "driver"/"name_ext", which
# model.py itself already requires/defaults) - a missing one is a build-time error
# (SPECIFICATION.md Part L.5's "missing required pin/bus field").
REQUIRED_TOML_FIELDS: dict[str, tuple[str, ...]] = {
    "scd30": ("bus", "irq_pin"),
    "sgp40": ("bus",),
    "bmp3xx": ("bus",),
    "isl29125": ("bus", "irq_pin"),
    "fram": ("bus", "cs_pin", "max_size"),
    "neopixel": ("pin",),
    "notification": (),
    "uart_link": ("bus", "role"),
}

# TOML fields a driver's instances *may* declare, beyond the required ones above - present because
# the underlying constructor param has its own default (e.g. BMP3xx_Reader's own address=0x77).
OPTIONAL_TOML_FIELDS: dict[str, tuple[str, ...]] = {
    "scd30": ("trigger_sec",),
    "sgp40": (),
    "bmp3xx": ("address", "trigger_sec"),
    # No "address": 0x44 is hard-wired (no address-select pin, datasheet p15), so this belongs in
    # FIXED_ADDRESS_DRIVERS. irq_pull_up exists because the INT line is open-drain (p6): a board
    # with its own external pull-up sets it false so the internal one is not engaged too.
    "isl29125": ("trigger_sec", "irq_pull_up"),
    "fram": (),
    "neopixel": (),
    "notification": (),
    "uart_link": (),
}

# Every field an instance of this driver may legitimately declare (beyond "driver"/"name_ext") -
# a field outside this set is a copy-paste/typo error, not a silently-dropped no-op
# (SPECIFICATION.md Part L.5's "a copy-paste duplicate... plain wrong/missing/copy-pasted fields").
ALLOWED_INSTANCE_FIELDS: dict[str, frozenset[str]] = {
    driver: frozenset(REQUIRED_TOML_FIELDS[driver]) | frozenset(OPTIONAL_TOML_FIELDS[driver]) for driver in REQUIRED_TOML_FIELDS
}

# Drivers whose instances sit on a declared [bus.*] - i.e. carry a "bus" TOML field at all.
BUS_ATTACHED_DRIVERS = frozenset(REQUIRED_TOML_FIELDS) - {"neopixel", "notification"}

# Which bus kind each bus-attached driver's "bus" field must resolve to. Without it a TOML typo
# pairing a uart_link with an i2c bus built cleanly - the bus only had to exist - and failed at
# boot inside UART_Comm with a raw AttributeError. Every BUS_ATTACHED_DRIVERS member belongs here.
BUS_KIND_BY_DRIVER: dict[str, str] = {
    "scd30": "i2c",
    "sgp40": "i2c",
    "bmp3xx": "i2c",
    "isl29125": "i2c",
    "fram": "spi",
    "uart_link": "uart",
}

# Bus-attached drivers with a real, chip-datasheet-confirmed address-select pin (BMP388/390: SDO
# pin selects 0x76/0x77) - the only ones a TOML `address` field is meaningful for.
ADDRESS_CAPABLE_DRIVERS = frozenset({"bmp3xx"})

# Bus-attached drivers with no address field: the chip's address is fixed in hardware, so two
# instances on one bus cannot be told apart (Part L.5). "uart_link" joins them for a related
# reason - a UART is point-to-point and has no address concept at all.
FIXED_ADDRESS_DRIVERS = BUS_ATTACHED_DRIVERS - ADDRESS_CAPABLE_DRIVERS - {"fram"}
