"""The one catalog of notification's warn signals (SPECIFICATION.md Part L.4): codegen renders each
signal's threshold schema and colour from it, the definitions generator its web field."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WarnSignal:
    name: str  # the signal's config key, e.g. "WarnCO2"
    const_name: str  # the generated module's threshold-schema constant
    field_type: str  # "int" | "float", the schema's type word
    default: int | float
    min: int | float
    max: int | float
    color: tuple[int, int, int]  # per-channel weight (0/1) of the flash, scaled by FlashBri
    label: str
    unit: str | None  # None: the web field shows no unit


# Keyed by the notification's TOML wiring key. Fixed by the generator, identical on every device
# (agent, 2026-09-09): a new signal is a code change here, never a TOML field.
WARN_SIGNALS: dict[str, WarnSignal] = {
    "warn_co2": WarnSignal("WarnCO2", "_FIELD_WARN_CO2", "int", 1600, 0, 3000, (1, 0, 0), "CO2 Warning Threshold", "ppm"),
    "warn_voc": WarnSignal("WarnVOC", "_FIELD_WARN_VOC", "int", 350, 0, 500, (0, 1, 0), "VOC Warning Threshold", None),
    "warn_hum": WarnSignal("WarnHum", "_FIELD_WARN_HUM", "float", 65.0, 0.0, 100.0, (0, 0, 1), "Humidity Warning Threshold", "%"),
}
