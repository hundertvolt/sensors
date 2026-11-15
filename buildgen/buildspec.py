"""Per-driver "what does this need from the TOML" facts: required/optional fields, which drivers
sit on a bus, and which have a real TOML-configurable `address` (SPECIFICATION.md's schema note -
each fact datasheet-checked, not re-derived here)."""

# One of the two tables buildgen keeps by hand (owner, 2026-09-18; the other is definitions.py's
# status/errcount catalog): TOML field names and constructor parameter names are independent naming
# spaces. A resolvable driver without its row is a named build error (Part L.6.6).

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
    "mqtt": (),
    "mqtt_link": (),
}

# TOML fields a driver's instances *may* declare, beyond the required ones above - present because
# the underlying constructor param has its own default (e.g. BMP3XX_Reader's own address=0x77).
OPTIONAL_TOML_FIELDS: dict[str, tuple[str, ...]] = {
    "scd30": ("trigger_s",),
    "sgp40": (),
    "bmp3xx": ("address", "trigger_s"),
    # No "address": 0x44 is hard-wired (no address-select pin, datasheet p15), so this belongs in
    # FIXED_ADDRESS_DRIVERS. irq_pull_up exists because the INT line is open-drain (p6): a board
    # with its own external pull-up sets it false so the internal one is not engaged too.
    "isl29125": ("trigger_s", "irq_pull_up"),
    "fram": (),
    "neopixel": (),
    "notification": (),
    "uart_link": ("crc", "max_transfer_bytes"),
    "mqtt": (),
    "mqtt_link": (),
}

# Every field an instance of this driver may legitimately declare (beyond "driver"/"name_ext") -
# a field outside this set is a copy-paste/typo error, not a silently-dropped no-op
# (SPECIFICATION.md Part L.5's "a copy-paste duplicate... plain wrong/missing/copy-pasted fields").
ALLOWED_INSTANCE_FIELDS: dict[str, frozenset[str]] = {
    driver: frozenset(REQUIRED_TOML_FIELDS[driver]) | frozenset(OPTIONAL_TOML_FIELDS[driver]) for driver in REQUIRED_TOML_FIELDS
}

# Drivers whose instances sit on a declared [bus.*] - i.e. carry a "bus" TOML field at all.
BUS_ATTACHED_DRIVERS = frozenset(REQUIRED_TOML_FIELDS) - {"neopixel", "notification", "mqtt", "mqtt_link"}

# Which bus kind each bus-attached driver's "bus" field must resolve to. Without it a TOML typo
# pairing a uart_link with an i2c bus built cleanly - the bus only had to exist - and failed at
# boot inside UARTComm with a raw AttributeError. Every BUS_ATTACHED_DRIVERS member belongs here.
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

# The mandatory modules every device builds, never [[instance]] entries: each by its generated name, and its src/ file.
MANDATORY_FILES: dict[str, str] = {
    "sysfunct": "asy_system_service.py", "conn": "asy_wifi_service.py", "ntp": "asy_ntp_client.py",
    "webserver": "asy_webserver_service.py", "dns": "asy_captive_dns.py",
}

# CRC mode of a uart_link end -> (crc_checks class, width in bytes); held equal to src/crc_checks.py by a test
UART_CRC_MODES: dict[str, tuple[str, int]] = {"none": ("CRCPass", 0), "crc16": ("CRC16", 2)}
