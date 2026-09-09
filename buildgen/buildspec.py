"""Per-driver "what does this need from the TOML" facts: which TOML fields are required, which
drivers sit on a bus at all, and which bus-attached drivers have a real, TOML-configurable
`address` field (SPECIFICATION.md's own schema note: "A device address field only exists for chips
with a logically-selectable address" - checked against each chip's datasheet by Session 2, not
re-derived here).

This is the one piece of hand-maintained per-driver knowledge beyond driver-class resolution
(buildgen.driver_registry) and `_WIRING` (buildgen.wiring) - necessary because Session 2's already-
shipped TOML field names (`pin`, `cs_pin`, `irq_pin`, `bus`, ...) and `src/`'s own constructor
parameter names (`neopixel_pin`, `spi_cs`, `irq_pin`, ...) are two independently-evolved naming
spaces, the same kind of split BUILD_CHAIN_PLAN.md's quality bar already documents for wiring
identity vs instance_name(). See this session's PR description for why this couldn't be derived
automatically the way driver-class resolution and `_WIRING` are."""

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
