"""tests/_strict_json.py: accepts exactly RFC 8259 JSON, and rejects each separator slip the
interpreter's own lenient json.loads() lets through - which is the whole reason it exists."""

import json

import _strict_json
from _strict_json import check_strict_json, strict_loads

_VALID = (
    '{"a": 1, "b": [1, 2.5, -0.5e-3, 0, -0], "c": {"d": null, "e": true, "f": false}}',
    '{"errcount":{"SCD30":{"count":0},"WEBSERVER":{"count":1}}}',
    "  [ ]  ",
    "{}",
    '"\\u00e4 \\" \\\\ \\/ \\b\\f\\n\\r\\t"',
    "1E+10",
    '{"gr\u00fc\u00dfe": "caf\u00e9 \u20ac \U0001f600", "\u00e4": ["\u00f6"]}',  # raw non-ASCII, one to four bytes each
)

_LENIENTLY_PARSED = (
    '{,"a":1}',  # the streamed dict's first-key comma
    '{"a":1 "b":2}',  # a missing separator between members
    '{"a":1,,"b":2}',
    "[1 2]",
    "[1,]",
    '{"a":1,}',
)

_MALFORMED = (
    "",
    "{",
    '{"a"}',
    '{"a":}',
    "{'a': 1}",
    "[01]",
    "[1.]",
    "[.5]",
    "[+1]",
    "[nan]",
    "[Infinity]",
    '"a\nb"',
    '"\\x41"',
    '"\\u12"',
    '"open',
    "{} {}",
    "tru",
    '"\u00e4\x01"',
    '["\u00e4", \u00e4]',
)


def test_every_valid_document_passes_and_one_extra_comma_fails() -> None:
    # The rejection half keeps the positive one honest: an accept-all recogniser passes the first two calls only.
    for text in _VALID:
        check_strict_json(text)
        check_strict_json(text.encode())
        raised = ""
        try:
            check_strict_json(text + ",")
        except ValueError as e:
            raised = str(e)
        assert "not strict JSON" in raised, text


def test_the_separator_slips_json_loads_accepts_are_rejected() -> None:
    for text in _LENIENTLY_PARSED:
        json.loads(text)  # the interpreter's own parser takes it, so only this check stands in the way
        raised = ""
        try:
            check_strict_json(text)
        except ValueError as e:
            raised = str(e)
        assert "not strict JSON" in raised, text


def test_every_malformed_document_is_rejected_with_its_offset() -> None:
    for text in _MALFORMED:
        raised = ""
        try:
            check_strict_json(text.encode())
        except ValueError as e:
            raised = str(e)
        assert "not strict JSON at offset" in raised, text


def test_an_offset_counts_characters_however_many_bytes_precede_it() -> None:
    # The scan runs over UTF-8 bytes; the offset it names still counts characters, as indexing the decoded text did.
    for text, offset in (('["\u00e4\u20ac", 1,]', 9), ('"\u00e4\U0001f600\x01"', 3)):
        for body in (text, text.encode()):
            raised = ""
            try:
                check_strict_json(body)
            except ValueError as e:
                raised = str(e)
            assert f"not strict JSON at offset {offset} (" in raised, (text, raised)


def test_the_scan_indexes_bytes_never_a_str() -> None:
    # A str's len() and index walk its UTF-8 from the start (py/objstrunicode.c:116-117, 164-186, v1.29.0), so a scan
    # over one is quadratic in the body's length: a str body is scanned as its UTF-8 bytes, like every other body.
    seen: list[type] = []
    real = _strict_json._ws

    def spy(data: bytes, i: int) -> int:
        seen.append(type(data))
        return real(data, i)

    _strict_json._ws = spy
    try:
        check_strict_json('{"\u00e4": [1, "x"]}')
        strict_loads(bytearray(b"[1]"))
    finally:
        _strict_json._ws = real
    assert seen and all(kind is bytes for kind in seen), seen


def test_a_bytearray_body_is_checked_like_bytes() -> None:
    check_strict_json(bytearray(b'{"ok": true}'))
    raised = False
    try:
        check_strict_json(bytearray(b'{"ok": true,}'))
    except ValueError:
        raised = True
    assert raised


def test_the_interpreters_own_dumps_emits_text_no_json_parser_accepts() -> None:
    # The emit-side counterpart of everything above, pinned so a version bump surfaces a change:
    # json.dumps() never raises here, where CPython would (SPECIFICATION.md Part F.1). A route that
    # lets a non-finite value through therefore ships a body the browser rejects, silently.
    for value in (float("inf"), -float("inf")):
        text = json.dumps({"v": value})
        raised = ""
        try:
            check_strict_json(text.encode())
        except ValueError as e:
            raised = str(e)
        assert "not strict JSON at offset" in raised, text
    assert json.dumps(b"x") == '"x"'  # bytes, dumped as a string rather than refused


def test_a_duplicate_key_is_refused_however_it_is_spelled() -> None:
    # json.loads() keeps the last of two equal keys; the browser's reading of such a body is not the device's.
    for text in ('{"a":1,"a":2}', '{"\\/":1,"/":2}', '{"\\u0041":1,"A":2}', '{"x":{"a":1,"a":2}}'):
        json.loads(text)
        raised = ""
        try:
            check_strict_json(text)
        except ValueError as e:
            raised = str(e)
        assert "duplicate key" in raised, text


def test_nested_objects_keep_their_own_keys() -> None:
    check_strict_json('{"a":{"x":1},"b":{"x":2},"x":[{"x":3},{"x":4}]}')
    raised = ""
    try:
        check_strict_json('{"a":{"x":1},"b":{"x":2,"x":3}}')  # the same shape, one inner object holding a key twice
    except ValueError as e:
        raised = str(e)
    assert "duplicate key" in raised


def test_strict_loads_returns_the_decoded_value_of_a_strict_body_only() -> None:
    assert strict_loads(b'{"a": 1}') == {"a": 1}
    assert strict_loads(bytearray(b"[1, 2]")) == [1, 2]
    assert strict_loads('"text"') == "text"
    raised = ""
    try:
        strict_loads(b'{"a": 1,}')
    except ValueError as e:
        raised = str(e)
    assert "not strict JSON" in raised


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
