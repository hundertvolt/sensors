"""fakes/_native_twins.py against the native functions they stand in for: equal results over seeded random inputs where
native code compiles; on a host with no native emitter both modules import the twins themselves, as the output says."""

from _native_twins import _crc as twin_crc
from _native_twins import _ring_copy as twin_ring_copy

from asy_uart_driver import _ring_copy
from crc_checks import _crc

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Iterator

_WIDTHS = ((0, (0x31, 0x07, 0xFF)), (8, (0x1021, 0x8005, 0xFFFF)), (24, (0x04C11DB7, 0x1EDC6F41, 0xFFFFFFFF)))  # shift, polys


def _lcg(seed: int) -> "Iterator[int]":
    # The same sequence on every host, so a failure names inputs that reproduce.
    state = seed
    while True:
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        yield state


def _same(original: object, twin: object) -> bool:
    # The module's own function or the twin it imported in its place: one object either way.
    return original is twin


def test_both_modules_import_the_native_functions_or_both_the_twins() -> None:
    swapped = [_same(_crc, twin_crc), _same(_ring_copy, twin_ring_copy)]
    assert swapped in ([False, False], [True, True]), swapped
    print("no native emitter on this host: the twins stand in" if swapped[0] else "the native functions under test")


def test_crc_twin_equals_the_native_crc_at_every_width() -> None:
    rand = _lcg(1)
    for shift, polys in _WIDTHS:
        top = 0x80 << shift
        for poly in polys:
            for _ in range(40):
                size = next(rand) % 300
                buf = bytearray(next(rand) & 0xFF for _ in range(size))
                start = next(rand) % (size + 1)
                end = start + next(rand) % (size - start + 1)
                init = next(rand) & ((top << 1) - 1)
                assert _crc(buf, start, end, init, poly, shift) == twin_crc(buf, start, end, init, poly, shift), (shift, poly, size, start, end, init)


def test_ring_copy_twin_equals_the_native_ring_copy() -> None:
    rand = _lcg(2)
    for size in (8, 64, 512):
        ring = bytearray(next(rand) & 0xFF for _ in range(size))
        for _ in range(40):
            pos, n, start = next(rand) % size, next(rand) % (size + 1), next(rand) % 16
            native, twin = bytearray(start + n + 4), bytearray(start + n + 4)
            assert _ring_copy(native, start, ring, pos, n, size - 1) == twin_ring_copy(twin, start, ring, pos, n, size - 1) == n  # type: ignore[arg-type]  # ptr8 parameters take any buffer
            assert native == twin, (size, pos, n, start)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
