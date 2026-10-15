"""Reads a src/ module's folded const() values at test time: const() names do not survive compilation (py/parse.c:857,
v1.29.0), so tests take them from the source text instead of copying them; the typed readers raise on a value of another
type. py_value() reads a host file's plain literal the generator emits (buildgen/). NTP_EPOCH_DELTA is RFC 5905's."""

NTP_EPOCH_DELTA = 2208988800  # RFC 5905 section 6, 1900 -> 1970

_MARK = " = const("
_cache: "dict[str, dict[str, object]]" = {}


def _is_name(text: str) -> bool:
    # An identifier at the line's start: what a module-level binding begins with (MicroPython's str has no isidentifier()).
    return bool(text) and not text[0].isdigit() and all(char == "_" or char.isalpha() or char.isdigit() for char in text)


def _call_end(line: str, start: int) -> int:
    # The index of the parenthesis closing the one opened just before `start`, past string literals and nested brackets.
    depth = 1
    quote = ""
    i = start
    while i < len(line):
        char = line[i]
        if quote:
            if char == "\\":
                i += 1
            elif char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unclosed const( in: " + line)


def _wrong_type(path: str, name: str, value: object, kind: str) -> TypeError:
    return TypeError(f"{name} in {path} is {value!r}, not {kind}")


def py_value(path: str, name: str) -> object:
    # The literal of a module-level `NAME = <literal>` line of a host file, e.g. the watchdog timeout buildgen emits.
    with open(path) as f:
        for line in f:
            head, mark, rest = line.partition(" = ")
            if mark and head == name:
                return eval(rest, {})  # noqa: S307 - one literal of a repository file; eval() skips its comment
    raise KeyError(f"{name} is not a module-level binding in {path}")


def src_bytes(path: str, name: str) -> bytes:
    value = src_const(path, name)
    if not isinstance(value, bytes):
        raise _wrong_type(path, name, value, "bytes")
    return value


def src_const(path: str, name: str) -> object:
    values = src_consts(path)
    if name not in values:
        raise KeyError(f"{name} is not a const() in {path}")
    return values[name]


def src_consts(path: str) -> "dict[str, object]":
    # Every module-level const() binding of `path`, read once per process; a binding's value may use earlier ones.
    values = _cache.get(path)
    if values is None:
        values = {}
        with open(path) as f:
            for line in f:
                name, mark, rest = line.partition(_MARK)
                if mark and _is_name(name):
                    expr = rest[: _call_end(rest, 0)]
                    values[name] = eval(expr, dict(values))  # noqa: S307 - the expression of a src/ const() line
        _cache[path] = values
    return values


def src_float(path: str, name: str) -> float:
    # An int is a float's value too (a const(5) timeout read as seconds); a bool is neither.
    value = src_const(path, name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _wrong_type(path, name, value, "a float")
    return value


def src_int(path: str, name: str) -> int:
    value = src_const(path, name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise _wrong_type(path, name, value, "an int")
    return value


def src_strs(path: str, name: str) -> "tuple[str, ...]":
    value = src_const(path, name)
    if not isinstance(value, tuple) or not all(isinstance(item, str) for item in value):
        raise _wrong_type(path, name, value, "a tuple of str")
    return value
