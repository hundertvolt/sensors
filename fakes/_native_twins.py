"""Plain twins of src/'s native-code functions for a host whose Unix port has no native emitter (v1.29.0 has none for
arm64): scripts/_generate_sensortask_modules.py swaps each in for its namesake in a copy under build/portable_src/, and
tests/test_native_twins.py proves each equal to its namesake wherever native code compiles."""


def _crc(buf: bytearray, start: int, end: int, crc: int, poly: int, shift: int) -> int:
    # crc_checks._crc, masked to the width at every step where the native word wraps.
    top = 0x80 << shift
    mask = (top << 1) - 1
    for i in range(start, end):
        crc ^= buf[i] << shift
        for _ in range(8):
            crc = ((crc << 1) ^ poly if crc & top else crc << 1) & mask
    return crc


def _ring_copy(dest: bytearray, start: int, ring: bytearray, pos: int, n: int, mask: int) -> int:
    # asy_uart_driver._ring_copy.
    for i in range(n):
        dest[start + i] = ring[(pos + i) & mask]
    return n
