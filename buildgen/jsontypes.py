"""The host JSON shapes buildgen writes: the website definitions, the API reference, the expected facts."""

from typing import TypeAlias

JsonValue: TypeAlias = str | int | float | bool | list["JsonValue"] | dict[str, "JsonValue"] | None
JsonDict: TypeAlias = dict[str, JsonValue]
