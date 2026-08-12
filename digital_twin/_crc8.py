"""Independent CRC-8 reimplementation (Sensirion polynomial 0x31, init 0xFF) shared by
_sgp40_chip.py/_scd30_chip.py - both real drivers import src/crc_checks.py's own CRC8 for this same
polynomial. Deliberately a second, independent implementation rather than importing crc_checks.py:
a bug shared between the twin's own response-building and the driver's own validation couldn't hide
behind a self-consistent round trip, matching tests/test_asy_sgp40_driver.py's own `_crc8()`
helper's identical rationale.
"""

_CRC_POLY = 0x31


def crc8(data: bytes) -> int:
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ _CRC_POLY) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def word(value: int) -> bytes:
    # 16-bit big-endian payload + its own CRC-8 trailer - the word shape both SGP40 and SCD30 use
    # for every command argument/reply.
    payload = bytes([(value >> 8) & 0xFF, value & 0xFF])
    return payload + bytes([crc8(payload)])
