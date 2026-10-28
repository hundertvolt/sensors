"""Flash-tier chip conformance: each bus chip's raw-bus probe on silicon against the same probe on the twin at both GC
stages (conformance.py), physical keys compared only in an independent form; and the SCD30's reaction to a bad
interval write, recorded."""

import struct
from typing import Protocol

import conformance
import pytest
from harness import DEVICE_SCRIPTS_DIR, Board, parse_facts
from plausibility_bounds import BOUNDS


class _ResultNote(Protocol):
    # The root conftest's result_note fixture.
    def __call__(self, text: str, *, recovery: bool = False) -> None: ...


COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("scd30", "sgp40", "bmp3xx", "fram", "isl29125")

_GC_STAGES = (-1, 32768)
# The longest probe is the ISL29125's (~15 s of measured settles); the SCD30's waits up to one interval.
# @tunable l3.chip_conformance_probe_timeout_s = 120.0
_PROBE_TIMEOUT_S = 120.0
# Two timed measurement periods per write, each up to two intervals: generous for the bench's interval.
# @tunable l3.chip_conformance_argument_reaction_timeout_s = 240.0
_ARGUMENT_REACTION_TIMEOUT_S = 240.0
_SCD30_BOOT_MAX_MS = 2000  # "The boot-up time is < 2 s" (SCD30 Interface Description 1.1)
_SCD30_INTERVAL_RANGE_S = (2, 1800)  # "Available range: [2 ... 1800]" (1.4.3)
_BMP3XX_CHIP_IDS = ("50", "60")  # BMP384/BMP388 0x50, BMP390 0x60 (each datasheet's CHIP_ID register)
# One ISL29125 12-bit conversion: tINT 101 ms at 16 bit over 16 (p.3, p.6), per channel or per RGB cycle of three.
# @tunable l3.chip_conformance_isl29125_cycle_min_ms = 3
_ISL_CYCLE_MIN_MS = 3
# @tunable l3.chip_conformance_isl29125_cycle_max_ms = 40
_ISL_CYCLE_MAX_MS = 40


def _conformance(board: Board, table: conformance.ProbeTable) -> "tuple[dict[str, str], list[str]]":
    # The probe on the board, then on the twin at each GC stage: every divergence named with its stage.
    real = conformance.parse(board.run_isolated(table.probe, timeout_s=_PROBE_TIMEOUT_S))
    assert real.get("DONE") == "1", f"{table.probe.name} did not run to completion on the board: {real}"
    divergences: list[str] = []
    for stage in _GC_STAGES:
        twin = conformance.run_probe_on_twin(table.probe, stage)
        divergences += [f"gc.threshold({stage}) {line}" for line in conformance.compare(real, twin, table.physical_keys, table.independent_checks)]
    return real, divergences


def _words(value: str, count: int) -> "list[int] | None":
    # The 16-bit words of a raw Sensirion reply (word, CRC, ...), or None when its length or any CRC is wrong.
    try:
        raw = bytes.fromhex(value)
    except ValueError:
        return None
    if len(raw) != 3 * count or any(_crc8(raw[i : i + 2]) != raw[i + 2] for i in range(0, len(raw), 3)):
        return None
    return [(raw[i] << 8) | raw[i + 1] for i in range(0, len(raw), 3)]


def _scd30_co2_plausible(value: str) -> bool:
    words = _words(value, 6)
    if words is None:
        return False
    co2: float = struct.unpack(">f", struct.pack(">HH", words[0], words[1]))[0]
    return BOUNDS["co2_ppm"][0] <= co2 <= BOUNDS["co2_ppm"][1]


def _scd30_interval_valid(value: str) -> bool:
    words = _words(value, 1)
    return words is not None and _SCD30_INTERVAL_RANGE_S[0] <= words[0] <= _SCD30_INTERVAL_RANGE_S[1]


def _scd30_ready_valid(value: str) -> bool:
    words = _words(value, 1)
    return words is not None and words[0] in (0, 1)


def _scd30_recovery_bounded(value: str) -> bool:
    return value.isdigit() and int(value) <= _SCD30_BOOT_MAX_MS


def _bmp3xx_calibration_set(value: str) -> bool:
    # 21 raw bytes, neither erased nor floating: the part's own trimming (BMP384 datasheet 3.11.1).
    return len(value) == 42 and value not in ("0" * 42, "f" * 42)


def _bmp3xx_data_set(value: str) -> bool:
    # Pressure and temperature both converted: neither 24-bit field left at zero (3.10).
    return len(value) == 12 and value[:6] != "000000" and value[6:] != "000000"


def _isl29125_cycles_in_range(value: str) -> bool:
    cycles = [int(ms) for ms in value.split(",") if ms.isdigit()]
    return bool(cycles) and len(cycles) == len(value.split(",")) and all(_ISL_CYCLE_MIN_MS <= ms <= _ISL_CYCLE_MAX_MS for ms in cycles)


SCD30 = conformance.ProbeTable(
    DEVICE_SCRIPTS_DIR / "scd30_conformance_probe.py",
    frozenset({"A01_firmware_version_word", "A02_interval_word", "B01_data_ready_word", "B03_measurement", "C02_soft_reset_recovery_ms"}),
    {
        "A01_firmware_version_word": lambda v: _words(v, 1) is not None,
        "A02_interval_word": _scd30_interval_valid,
        "B01_data_ready_word": _scd30_ready_valid,
        "B03_measurement": _scd30_co2_plausible,
        "C02_soft_reset_recovery_ms": _scd30_recovery_bounded,
    },
)
SGP40 = conformance.ProbeTable(
    DEVICE_SCRIPTS_DIR / "sgp40_conformance_probe.py",
    frozenset({"A01_serial", "B01_self_test", "C01_raw_signal"}),
    {
        "A01_serial": lambda v: _words(v, 3) is not None,
        "B01_self_test": lambda v: _words(v, 1) is not None and v[:2] == "d4",  # 0xD4XX: all tests passed (Table 13)
        "C01_raw_signal": lambda v: _words(v, 1) is not None,
    },
)
BMP3XX = conformance.ProbeTable(
    DEVICE_SCRIPTS_DIR / "bmp3xx_conformance_probe.py",
    frozenset({"A01_chip_id", "A02_calibration", "B06_data"}),
    {"A01_chip_id": lambda v: v in _BMP3XX_CHIP_IDS, "A02_calibration": _bmp3xx_calibration_set, "B06_data": _bmp3xx_data_set},
)
# MISO's idle level is the board's, not the chip's: 0xFF means a pull-up on the breakout, under which an absent or
# silent chip reads WEL set and only the stuck-WEL warning would remain.
FRAM = conformance.ProbeTable(
    DEVICE_SCRIPTS_DIR / "fram_conformance_probe.py",
    frozenset({"A01_miso_idle_byte"}),
    {"A01_miso_idle_byte": lambda v: v == "00"},
)
ISL29125 = conformance.ISL29125._replace(
    physical_keys=conformance.ISL29125.physical_keys | {"J01_cycle_12bit_ms_series"},
    independent_checks={**conformance.ISL29125.independent_checks, "J01_cycle_12bit_ms_series": _isl29125_cycles_in_range},
)


def _crc8(data: bytes) -> int:
    # Sensirion's CRC-8: polynomial 0x31, init 0xFF, no reflection (SCD30 Interface Description 1.1.3; SGP40 Table 7).
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31 if crc & 0x80 else crc << 1) & 0xFF
    return crc


def test_scd30_matches_its_twin_fake(board: Board, scd30_measuring: str) -> None:
    _, divergences = _conformance(board, SCD30)
    assert not divergences, "the SCD30 fake diverges from the chip:\n" + "\n".join(divergences)


def test_sgp40_matches_its_twin_fake(board: Board) -> None:
    _, divergences = _conformance(board, SGP40)
    assert not divergences, "the SGP40 fake diverges from the chip:\n" + "\n".join(divergences)


def test_bmp3xx_matches_its_twin_fake(board: Board, result_note: _ResultNote) -> None:
    real, divergences = _conformance(board, BMP3XX)
    result_note(f"chip id {real.get('A01_chip_id')}, calibration block {real.get('A02_calibration')}")
    assert not divergences, "the BMP3xx fake diverges from the chip:\n" + "\n".join(divergences)


def test_fram_matches_its_twin_fake(board: Board) -> None:
    _, divergences = _conformance(board, FRAM)
    assert not divergences, "the FRAM fake diverges from the chip:\n" + "\n".join(divergences)


def test_isl29125_matches_its_twin_fake(board: Board, result_note: _ResultNote) -> None:
    real, divergences = _conformance(board, ISL29125)
    result_note(f"12-bit conversion cycle series {real.get('J01_cycle_12bit_ms_series')} ms, PRST4 {real.get('H07_prst4_ms')} ms ({real.get('H08_prst4_unit')})")
    assert not divergences, "the ISL29125 fake diverges from the chip:\n" + "\n".join(divergences)


# Recorded, not judged: the datasheet states no reaction to either write. Up to three NVM writes, restored in the script.
@pytest.mark.persistence_write
@pytest.mark.scd30_extra_write
def test_scd30_argument_reaction_is_recorded(board: Board, scd30_measuring: str, result_note: _ResultNote) -> None:
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "scd30_argument_reaction.py", timeout_s=_ARGUMENT_REACTION_TIMEOUT_S))
    assert "skipped" not in facts, f"no write was made: {facts}"
    result_note(
        f"wrong CRC: {facts['wrong_crc_write']}, accepted {facts['wrong_crc_accepted']}, period {facts['period_after_wrong_crc_ms']} ms; "
        f"zero: {facts['zero_interval_write']}, accepted {facts['zero_interval_accepted']}, period {facts['period_after_zero_ms']} ms; "
        f"partial pointer: {facts['partial_pointer_word']} (CRC valid {facts['partial_pointer_crc_ok']}), pointer restored {facts['pointer_restored']}",
    )
    assert facts["restored"] == "ok", f"the measurement interval was not put back: {facts['restored']}"
    assert facts["interval_after"] == facts["interval_before"], f"interval {facts['interval_before']} s before, {facts['interval_after']} s after"
