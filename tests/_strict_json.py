"""Strict RFC 8259 check for response bodies: MicroPython's json.loads() skips commas like whitespace (SPECIFICATION.md
F.1) and keeps the last of two equal keys (extmod/modjson.c:324, v1.29.0), so a separator slip or a doubled key would
pass every test while the browser's JSON.parse() refuses the slip outright. No src/ writer emits a key twice."""

import json

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

_WS = b" \t\r\n"
_DIGITS = b"0123456789"
_HEX = b"0123456789abcdefABCDEF"
_ESCAPES = b'"\\/bfnrt'
_LITERALS = (b"true", b"false", b"null")
_CONTROL_LIMIT = 0x20  # RFC 8259 section 7: U+0000-U+001F must be escaped inside a string

# The single bytes the scan compares against, as the ints indexing bytes yields.
_BACKSLASH = ord("\\")
_COLON = ord(":")
_COMMA = ord(",")
_DOT = ord(".")
_LBRACE = ord("{")
_LBRACKET = ord("[")
_MINUS = ord("-")
_QUOTE = ord('"')
_RBRACE = ord("}")
_RBRACKET = ord("]")
_U = ord("u")
_ZERO = ord("0")


def _check(data: bytes) -> None:
    end = _ws(data, _value(data, _ws(data, 0)))
    if end != len(data):
        raise _error(data, end, "trailing data")


def _digits(data: bytes, i: int) -> int:
    start = i
    while i < len(data) and data[i] in _DIGITS:
        i += 1
    if i == start:
        raise _error(data, i, "expected a digit")
    return i


def _error(data: bytes, i: int, what: str) -> ValueError:
    # The offset counts characters, as over the decoded text: one per byte that does not continue a UTF-8 sequence.
    at = sum(1 for byte in data[:i] if (byte & 0xC0) != 0x80)
    text = data.decode()
    return ValueError(f"not strict JSON at offset {at} ({what}): {text[max(0, at - 20) : at + 20]!r}")


def _expect(data: bytes, i: int, char: int) -> int:
    if i >= len(data) or data[i] != char:
        raise _error(data, i, f"expected {chr(char)!r}")
    return i + 1


def _members(data: bytes, i: int, close: int, member: "Callable[[bytes, int], int]") -> int:
    # One comma between members, none before the first or after the last - the separators this exists for.
    i = _ws(data, i + 1)
    if i < len(data) and data[i] == close:
        return i + 1
    while True:
        i = _ws(data, member(data, i))
        if i < len(data) and data[i] == _COMMA:
            i = _ws(data, i + 1)
            continue
        return _expect(data, i, close)


def _number(data: bytes, i: int) -> int:
    if data[i] == _MINUS:
        i += 1
    if i < len(data) and data[i] == _ZERO:
        i += 1  # no leading zeros: "01" is two tokens, which the caller then rejects
    else:
        i = _digits(data, i)
    if i < len(data) and data[i] == _DOT:
        i = _digits(data, i + 1)
    if i < len(data) and data[i] in b"eE":
        i += 1
        if i < len(data) and data[i] in b"+-":
            i += 1
        i = _digits(data, i)
    return i


def _object(data: bytes, i: int) -> int:
    # Each member's key decoded, so an escaped spelling and the plain one are the same key, and taken once per object.
    keys: set[str] = set()

    def member(data: bytes, start: int) -> int:
        end = _string(data, start)
        token = data[start:end]
        key = json.loads(token) if _BACKSLASH in token else token[1:-1].decode()
        if key in keys:
            raise _error(data, start, "duplicate key")
        keys.add(key)
        return _value(data, _ws(data, _expect(data, _ws(data, end), _COLON)))

    return _members(data, i, _RBRACE, member)


def _string(data: bytes, i: int) -> int:
    # Byte by byte: each byte of a multi-byte UTF-8 character is 0x80 or above, never a quote, backslash or control.
    i = _expect(data, i, _QUOTE)
    while i < len(data):
        byte = data[i]
        if byte == _QUOTE:
            return i + 1
        if byte < _CONTROL_LIMIT:
            raise _error(data, i, "unescaped control character")
        if byte == _BACKSLASH:
            i += 1
            if i < len(data) and data[i] == _U:
                if not all(c in _HEX for c in data[i + 1 : i + 5]) or i + 5 > len(data):
                    raise _error(data, i, "bad \\u escape")
                i += 4
            elif i >= len(data) or data[i] not in _ESCAPES:
                raise _error(data, i, "bad escape")
        i += 1
    raise _error(data, i, "unterminated string")


def _utf8(body: "bytes | bytearray | str") -> bytes:
    # The body as UTF-8 bytes: a str's len() and index walk its UTF-8 from the start (py/objstrunicode.c:116-117,
    # 164-186, v1.29.0), so a scan over one is quadratic, over bytes linear. decode() refuses invalid UTF-8, as before.
    if isinstance(body, str):
        return body.encode()
    data = bytes(body)
    data.decode()
    return data


def _value(data: bytes, i: int) -> int:
    if i >= len(data):
        raise _error(data, i, "expected a value")
    byte = data[i]
    if byte == _LBRACE:
        return _object(data, i)
    if byte == _LBRACKET:
        return _members(data, i, _RBRACKET, _value)
    if byte == _QUOTE:
        return _string(data, i)
    if byte == _MINUS or byte in _DIGITS:
        return _number(data, i)
    for literal in _LITERALS:
        if data[i : i + len(literal)] == literal:
            return i + len(literal)
    raise _error(data, i, "expected a value")


def _ws(data: bytes, i: int) -> int:
    while i < len(data) and data[i] in _WS:
        i += 1
    return i


def check_strict_json(body: "bytes | bytearray | str") -> None:
    # Raises ValueError naming the offset, in characters, unless `body` is exactly one strict JSON value.
    _check(_utf8(body))


def strict_loads(body: "bytes | bytearray | str") -> object:
    # check_strict_json(), then the decoded value: the one way a test reads a response body.
    data = _utf8(body)
    _check(data)
    return json.loads(data)
