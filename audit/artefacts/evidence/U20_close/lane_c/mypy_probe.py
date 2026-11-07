JsonValue = int | float | str | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
JsonDict = dict[str, JsonValue]


def names() -> list[str]:
    return ["a"]


def direct() -> JsonDict:
    return {"A": names()}


def copied() -> JsonDict:
    return {"A": list(names())}
