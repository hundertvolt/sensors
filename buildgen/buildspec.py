"""Per-driver "what does this need from the TOML" facts: required/optional fields, which drivers
sit on a bus, and which have a real TOML-configurable `address` (SPECIFICATION.md's schema note -
datasheet-checked by Session 2, not re-derived here)."""

# The one hand-maintained per-driver table in this package - driver-class resolution
# (driver_registry.py) and `_WIRING`/`_LIMITS`/`_Default*` are all AST-derived from src/ instead.
# It can't be: Session 2's already-shipped TOML field names ("pin", "cs_pin", ...) and src/'s own
# constructor parameter names ("neopixel_pin", "spi_cs", ...) are two independently-evolved naming
# spaces, so there is no rule to derive one from the other. Adding a driver means adding a row here.

# TOML fields every instance of this driver must declare (beyond "driver"/"name_ext", which
# model.py itself already requires/defaults) - a missing one is a build-time error
# (BUILD_CHAIN_PLAN.md's "missing required pin/bus field").
REQUIRED_TOML_FIELDS: dict[str, tuple[str, ...]] = {
    "scd30": ("bus", "irq_pin"),
    "sgp40": ("bus",),
    "bmp3xx": ("bus",),
    "fram": ("bus", "cs_pin", "max_size"),
    "neopixel": ("pin",),
    "notification": (),
}

# TOML fields a driver's instances *may* declare, beyond the required ones above - present because
# the underlying constructor param has its own default (e.g. BMP3xx_Reader's own address=0x77).
OPTIONAL_TOML_FIELDS: dict[str, tuple[str, ...]] = {
    "scd30": ("trigger_sec",),
    "sgp40": (),
    "bmp3xx": ("address", "trigger_sec"),
    "fram": (),
    "neopixel": (),
    "notification": (),
}

# Every field an instance of this driver may legitimately declare (beyond "driver"/"name_ext") -
# a field outside this set is a copy-paste/typo error, not a silently-dropped no-op
# (BUILD_CHAIN_PLAN.md's "a copy-paste duplicate... plain wrong/missing/copy-pasted fields").
ALLOWED_INSTANCE_FIELDS: dict[str, frozenset[str]] = {
    driver: frozenset(REQUIRED_TOML_FIELDS[driver]) | frozenset(OPTIONAL_TOML_FIELDS[driver]) for driver in REQUIRED_TOML_FIELDS
}

# Drivers whose instances sit on a declared [bus.*] - i.e. carry a "bus" TOML field at all.
BUS_ATTACHED_DRIVERS = frozenset(REQUIRED_TOML_FIELDS) - {"neopixel", "notification"}

# Bus-attached drivers with a real, chip-datasheet-confirmed address-select pin (BMP388/390: SDO
# pin selects 0x76/0x77) - the only ones a TOML `address` field is meaningful for.
ADDRESS_CAPABLE_DRIVERS = frozenset({"bmp3xx"})

# Bus-attached drivers with no address field at all - the chip's own I2C address is fixed in
# hardware (SCD30/SGP40's own datasheets), so two such instances sharing one bus can never be told
# apart (BUILD_CHAIN_PLAN.md's "two hardwired-address instances of the same chip type sharing a
# bus with no way to distinguish them at all" case).
FIXED_ADDRESS_DRIVERS = BUS_ATTACHED_DRIVERS - ADDRESS_CAPABLE_DRIVERS - {"fram"}
