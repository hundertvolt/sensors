"""tests/_strict_json.py: accepts exactly RFC 8259 JSON, and rejects each separator slip the
interpreter's own lenient json.loads() lets through - which is the whole reason it exists."""

import json

from _strict_json import check_strict_json
from microtest import run

_VALID = (
    '{"a": 1, "b": [1, 2.5, -0.5e-3, 0, -0], "c": {"d": null, "e": true, "f": false}}',
    '{"errcount":{"SCD30":{"count":0},"WEBSERVER":{"count":1}}}',
    "  [ ]  ",
    "{}",
    '"\\u00e4 \\" \\\\ \\/ \\b\\f\\n\\r\\t"',
    "1E+10",
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
)


def test_every_valid_document_passes_as_text_and_as_bytes() -> None:
    for text in _VALID:
        check_strict_json(text)
        check_strict_json(text.encode())


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


def test_a_bytearray_body_is_checked_like_bytes() -> None:
    check_strict_json(bytearray(b'{"ok": true}'))
    raised = False
    try:
        check_strict_json(bytearray(b'{"ok": true,}'))
    except ValueError:
        raised = True
    assert raised


if __name__ == "__main__":
    run(globals())
