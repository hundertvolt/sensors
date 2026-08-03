"""Generalized REST response envelope + setter-dispatch orchestration for the Microdot layer -
the replacement for improved-quality/api_helpers.py's cmd_post_check()/special_err/
generic_error_return() ad hoc per-endpoint pipeline. Every response keeps the same wire shape the
legacy pipeline already used ({"res": "OK"/"ERR", "code": int, "descr": str, "result": ...}), so no
endpoint's client-visible contract changes. Two independent pieces: make_response() is a pure
envelope/catalog primitive (no I/O, can't raise); handle_set_cmd() orchestrates one
SensorReaderConfig's base_classes.py-owned _set_dict_cfg() plus an optional post-write hook, with
its own try/except as defense-in-depth on top of Microdot's blanket per-request catch (see
CLAUDE.md's "Microdot / REST layer" section - that catch alone is safe, this is an extra layer of
precision, not a gap it leaves open).
"""

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, Protocol

    from base_classes import SensorReaderConfig
    from config_manager import ConfigSchema

    ResponseEnvelope = dict[str, "str | int | dict[str, Any]"]

    class _RequestLike(Protocol):
        # Structural stand-in for microdot.Request (ext/microdot.py - not on this project's mypy
        # search path, see pyproject.toml's [tool.mypy] mypy_path/files) - mirrors print_log.py's
        # own _FramManager/_FramChunk Protocols: describes only the one property parse_cmd_request
        # actually touches, so this module stays decoupled from microdot's concrete shape and needs
        # no import of it at all, typed or otherwise.
        @property
        def json(self) -> "Any": ...

# Standard code -> default message catalog. A caller can override any standard code's text (pass
# descr=...) or use an entirely different code with its own text (any code not listed here) -
# generalizes the legacy special_err closed Literal enum into an open set, same envelope shape.
_STANDARD_CODES: "dict[int, str]" = {
    0: "Command executed",
    1: "Invalid JSON request",
    2: "Command specifier missing",
    3: "Invalid command",
    4: "Internal config read error",
    5: "Internal config write error",
    100: "Generic command error",
}


def make_response(code: int, descr: "str | None" = None, result: "dict[str, Any] | None" = None) -> "ResponseEnvelope":
    # Pure and total: never raises, no I/O. code == 0 is the only "OK" outcome (matches every
    # existing endpoint's convention); everything else is "ERR", standard or caller-defined alike.
    if descr is None:
        descr = _STANDARD_CODES.get(code, "Unknown error")
    return {
        "res": "OK" if code == 0 else "ERR",
        "code": code,
        "descr": descr,
        "result": {} if result is None else result,
    }


def parse_cmd_request(request: "_RequestLike", keys: "list[str]") -> "tuple[dict[str, Any] | None, ResponseEnvelope | None]":
    # Mirrors improved-quality/api_helpers.py's cmd_pre_check(): parse the request body, then
    # validate a "cmd" field against the caller's own allowed-command list - unchanged in spirit
    # from the legacy pipeline, this part never needed special_err's closed-enum generalization.
    # One deliberate precision improvement over the legacy version: a syntactically valid but
    # non-dict JSON body (e.g. a bare list or string) is treated as a genuinely invalid request
    # (code 1) rather than falling through to "cmd specifier missing" (code 2).
    try:
        req_json = request.json
    except Exception:  # request.json has no internal guarding (see CLAUDE.md) - a malformed body
        # or bad encoding raises straight out of the property access.
        req_json = None
    if not isinstance(req_json, dict):
        return None, make_response(1)
    if "cmd" not in req_json:
        return None, make_response(2)
    if req_json["cmd"] not in keys:
        return None, make_response(3)
    return req_json, None


async def handle_set_cmd(
    reader: "SensorReaderConfig",
    data: "dict[str, int | float | str | bool | None]",
    cfg_vals: "ConfigSchema",
    post_fct: "Callable[[], None] | None" = None,
    post_asy_fct: "Callable[[], Coroutine[Any, Any, None]] | None" = None,
    ok_descr: "str | None" = None,
) -> "ResponseEnvelope":
    # Persist+push already happened, individually per field, inside reader._set_dict_cfg() (see
    # base_classes.py) - a per-field failure there is detail carried in "result", never a reason to
    # report the overall request as ERR: the request itself was validly processed and dispatched.
    # The one post-write hook fires at most once per call, only if at least one field actually
    # changed (project decision: one hook per endpoint, not one per field) - mirrors the legacy
    # pipeline's post_fct/post_asy_fct, unconditional on every field that changed alike.
    try:
        results = await reader._set_dict_cfg(data, cfg_vals)
        if any(status == "Valid" for status in results.values()):
            if post_fct is not None:
                post_fct()
            if post_asy_fct is not None:
                await post_asy_fct()
        return make_response(0, descr=ok_descr, result=results)
    except Exception as e:
        # Defense-in-depth: reader._set_dict_cfg() already catches its own internal failure modes
        # (a misbehaving _set_mgr_cfg override, a raising push callback - see base_classes.py), so
        # what actually reaches here is almost always a caller-supplied post_fct/post_asy_fct
        # raising, or some other genuinely unexpected failure - either way, always produce a
        # precise, on-brand reply here rather than relying solely on Microdot's own blanket catch.
        await reader.pr.err_s("Unhandled error in setter dispatch:", e, errno=1)
        return make_response(100)
