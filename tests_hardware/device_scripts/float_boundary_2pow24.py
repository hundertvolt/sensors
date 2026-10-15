"""Isolated-driver device script: the RP2040's firmware is MICROPY_FLOAT_IMPL_FLOAT (24-bit mantissa, SPECIFICATION.md
Part F.1), which the double-precision Unix-port rig cannot reproduce. Takes ints either side of 2**24 through the
config layer's float coercion and reports what came back; the host decides."""

from asy_config_manager import _coerce_float

# @include _shared/facts.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact

# Below the boundary every int round-trips exactly on any build.
_BELOW = 2**24 - 1
# The smallest int a 24-bit mantissa cannot hold: it rounds to 2**24 (round to even). Compared with int(),
# never with float(above): that is recomputed on the same single-precision hardware and would always match.
_ABOVE = 2**24 + 1

below = _coerce_float(_BELOW)
above = _coerce_float(_ABOVE)
fact("below_exact", below is not None and below == float(_BELOW) and int(below) == _BELOW)
fact("above_value", None if above is None else int(above))
fact("above_rounded_to_2pow24", above is not None and int(above) == 2**24)
done()
