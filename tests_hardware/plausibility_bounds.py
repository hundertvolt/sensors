"""Plausibility bounds, one (min, max, source) per quantity, each source naming its datasheet page or the src/ constant
it is read from: host tests import BOUNDS, device scripts receive it as a render extra. A bound that would fail a healthy
board is no plausibility bound."""

import ast
from pathlib import Path

_BMP3XX_DRIVER = Path(__file__).resolve().parent.parent / "src" / "asy_bmp3xx_driver.py"


def _driver_floats(path: Path) -> "dict[str, float]":
    # Every module-level `NAME = const(<number>)` of a src/ driver, read by ast: src/ is never imported host-side.
    found = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Call) and len(node.value.args) == 1:
            value = ast.literal_eval(node.value.args[0]) if isinstance(node.value.args[0], (ast.Constant, ast.UnaryOp)) else None
            if isinstance(value, float):
                found[node.targets[0].id] = value
    return found


_BMP3XX = _driver_floats(_BMP3XX_DRIVER)

# The VOC floor is 0, not the datasheet's 1: the shipped algorithm reports 0 for its first samples, and a bench
# session's first tests run inside that window after the board's reset (agent, 2026-10-14).
BOUNDS: "dict[str, tuple[float, float, str]]" = {
    "co2_ppm": (200, 10_000, "the owner's floor (owner, 2026-09-03), below the SCD30 datasheet's p.2 Table 1 calibrated range 400-10000 ppm"),
    "humidity_rh": (0.0, 100.0, "SCD30 datasheet p.2 Table 2: humidity measurement range 0-100 %RH"),
    "scd30_temp_c": (-40.0, 70.0, "SCD30 datasheet p.2 Table 3: temperature measurement range -40-70 degC"),
    "pressure_hpa": (_BMP3XX["_OP_PRESS_MIN_HPA"], _BMP3XX["_OP_PRESS_MAX_HPA"], "src/asy_bmp3xx_driver.py _OP_PRESS_MIN_HPA/_OP_PRESS_MAX_HPA (BMP3xx datasheet sec 1 Table 2 operating range)"),
    "bmp3xx_temp_c": (_BMP3XX["_OP_TEMP_MIN_C"], _BMP3XX["_OP_TEMP_MAX_C"], "src/asy_bmp3xx_driver.py _OP_TEMP_MIN_C/_OP_TEMP_MAX_C (BMP3xx datasheet sec 1 Table 2 operating range)"),
    "voc_index": (0, 500, "SGP40 datasheet p.3 Table 1: VOC Index 1-500; 0 while the algorithm's initial blackout runs, src/voc_algorithm.py _VOCALGORITHM_INITIAL_BLACKOUT"),
    "voc_raw_ticks": (0, 65_535, "SGP40 datasheet p.3 Table 1: SRAW_VOC 0-65535 ticks"),
    "lux": (0.0057, 10_000.0, "ISL29125 datasheet FN8424 p.1: 5.7 mlux (range 0) to 10,000 lux (range 1)"),
}
