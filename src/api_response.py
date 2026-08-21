"""REST response envelope + setter-dispatch orchestration for the Microdot layer -
replaces the old, now-deleted improved-quality/api_helpers.py's ad hoc per-endpoint pipeline.
"""
# Wire shape: {"res": "OK"/"ERR", "code": int, "descr": str, "result": ...}. make_response() is a
# pure envelope/catalog primitive (no I/O, can't raise); handle_set_cmd() orchestrates one
# SensorReaderConfig's _set_dict_cfg() plus an optional post-write hook, with its own try/except as
# defense-in-depth on top of Microdot's blanket per-request catch (see SPECIFICATION.md Part A.5).

from micropython import const

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
        # Structural stand-in for microdot.Request - not on this project's mypy search path
        # (SPECIFICATION.md Part C.10's typing convention).
        @property
        def json(self) -> "Any": ...

# handle_set_cmd()'s own defense-in-depth errno, always logged onto whatever caller-supplied
# SensorReaderConfig's own self.pr this is called with (see SPECIFICATION.md Part C.7) - never a
# small number: base_classes.py already reserves errno=1-9 on every such instance (actively used by
# _error_check(), which every real caller's own read/monitor loop calls), and every individual
# driver's own numbering only starts at 10+ within its own, much lower range (BMP3XX up to 21, WIFI
# up to 18, NTP up to 20, NOTIFY up to 13). A fixed, deliberately out-of-range sentinel here is the
# only choice that can't collide with any of them regardless of which reader this ends up logging to.
_ERRNO_UNHANDLED_DISPATCH = const(99)

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
    # Parse the request body, then validate a "cmd" field against the caller's own allowed-command
    # list. A syntactically valid but non-dict JSON body (e.g. a bare list or string) is treated as
    # a genuinely invalid request (code 1), not "cmd specifier missing" (code 2).
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
    # Persist+push already happened per field inside reader._set_dict_cfg() (base_classes.py) - a
    # per-field failure is detail carried in "result", never a reason to report the overall request
    # as ERR. The post-write hook fires at most once per call, only if a field actually changed.
    try:
        results = await reader._set_dict_cfg(data, cfg_vals)
        if any(status == "Valid" for status in results.values()):
            if post_fct is not None:
                post_fct()
            if post_asy_fct is not None:
                await post_asy_fct()
        return make_response(0, descr=ok_descr, result=results)
    except Exception as e:
        # Defense-in-depth: reader._set_dict_cfg() already catches its own internal failure modes,
        # so what reaches here is almost always a caller-supplied post_fct/post_asy_fct raising -
        # produce a precise, on-brand reply rather than relying solely on Microdot's blanket catch.
        await reader.pr.err_s("Unhandled error in setter dispatch:", e, errno=_ERRNO_UNHANDLED_DISPATCH)
        return make_response(100)
