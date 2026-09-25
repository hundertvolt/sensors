"""Strict RFC 8259 check for response bodies. MicroPython's json.loads() accepts a leading, doubled or
missing comma ('{,"a":1 "b":2}' parses), so a separator bug in a streamed body would pass every test
while the browser's JSON.parse() rejects the page's data outright."""

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

_WS = " \t\r\n"
_DIGITS = "0123456789"
_HEX = "0123456789abcdefABCDEF"
_ESCAPES = '"\\/bfnrt'
_LITERALS = ("true", "false", "null")
_CONTROL_LIMIT = 0x20  # RFC 8259 section 7: U+0000-U+001F must be escaped inside a string


def _error(text: str, i: int, what: str) -> ValueError:
    return ValueError(f"not strict JSON at offset {i} ({what}): {text[max(0, i - 20) : i + 20]!r}")


def _ws(text: str, i: int) -> int:
    while i < len(text) and text[i] in _WS:
        i += 1
    return i


def _expect(text: str, i: int, char: str) -> int:
    if i >= len(text) or text[i] != char:
        raise _error(text, i, f"expected {char!r}")
    return i + 1


def _string(text: str, i: int) -> int:
    i = _expect(text, i, '"')
    while i < len(text):
        char = text[i]
        if char == '"':
            return i + 1
        if ord(char) < _CONTROL_LIMIT:
            raise _error(text, i, "unescaped control character")
        if char == "\\":
            i += 1
            if i < len(text) and text[i] == "u":
                if not all(c in _HEX for c in text[i + 1 : i + 5]) or i + 5 > len(text):
                    raise _error(text, i, "bad \\u escape")
                i += 4
            elif i >= len(text) or text[i] not in _ESCAPES:
                raise _error(text, i, "bad escape")
        i += 1
    raise _error(text, i, "unterminated string")


def _digits(text: str, i: int) -> int:
    start = i
    while i < len(text) and text[i] in _DIGITS:
        i += 1
    if i == start:
        raise _error(text, i, "expected a digit")
    return i


def _number(text: str, i: int) -> int:
    if text[i] == "-":
        i += 1
    if i < len(text) and text[i] == "0":
        i += 1  # no leading zeros: "01" is two tokens, which the caller then rejects
    else:
        i = _digits(text, i)
    if i < len(text) and text[i] == ".":
        i = _digits(text, i + 1)
    if i < len(text) and text[i] in "eE":
        i += 1
        if i < len(text) and text[i] in "+-":
            i += 1
        i = _digits(text, i)
    return i


def _members(text: str, i: int, close: str, member: "Callable[[str, int], int]") -> int:
    # One comma between members, none before the first or after the last - the separators this exists for.
    i = _ws(text, i + 1)
    if i < len(text) and text[i] == close:
        return i + 1
    while True:
        i = _ws(text, member(text, i))
        if i < len(text) and text[i] == ",":
            i = _ws(text, i + 1)
            continue
        return _expect(text, i, close)


def _pair(text: str, i: int) -> int:
    i = _ws(text, _string(text, i))
    return _value(text, _ws(text, _expect(text, i, ":")))


def _value(text: str, i: int) -> int:
    if i >= len(text):
        raise _error(text, i, "expected a value")
    char = text[i]
    if char == "{":
        return _members(text, i, "}", _pair)
    if char == "[":
        return _members(text, i, "]", _value)
    if char == '"':
        return _string(text, i)
    if char == "-" or char in _DIGITS:
        return _number(text, i)
    for literal in _LITERALS:
        if text[i : i + len(literal)] == literal:
            return i + len(literal)
    raise _error(text, i, "expected a value")


def check_strict_json(body: "bytes | bytearray | str") -> None:
    """Raises ValueError naming the offset unless `body` is exactly one strict JSON value."""
    text = body if isinstance(body, str) else bytes(body).decode()
    end = _ws(text, _value(text, _ws(text, 0)))
    if end != len(text):
        raise _error(text, end, "trailing data")

