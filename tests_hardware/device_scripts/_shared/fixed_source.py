"""Included into device scripts at render: a fixed temperature_source/humidity_source stand-in (SPECIFICATION.md
Part L.6.3), the get_data() -> object-with-.value contract asy_sgp40_driver.py's own _Default* providers keep, for a
script that builds an SGP40 reader without the sensor graph that would feed it."""

from collections import namedtuple

_FixedValue = namedtuple("_FixedValue", ("value",))


class FixedSource:
    def __init__(self, value: float) -> None:
        self._data = _FixedValue(value)

    async def get_data(self) -> "_FixedValue":
        return self._data
