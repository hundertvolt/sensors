"""REST response envelope and settings-group setter dispatch for the Microdot layer; every function returns a well-defined value, never raises."""
# Wire shape: {"res": "OK"/"ERR", "code": int, "descr": str, "result": ...}; make_response() is pure and total.
# handle_set_cmd() drives one module's _set_dict_cfg() plus an optional post-write hook and returns the per-field
# outcome, a hook failure included, which the endpoint's OK envelope carries (SPECIFICATION.md Parts A.5 and C.5.3).

from micropython import const

from asy_config_manager import FAILED, VALID
from asy_print_log import report_if_fatal

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Protocol

    from asy_base_classes import AsyncCallback, JsonMapping, SensorReaderConfig
    from asy_config_manager import ConfigSchema, WriteValidity

    ResponseEnvelope = dict[str, "str | int | JsonMapping"]

    class _Holder(Protocol):
        def hold(self, closable: object) -> None: ...

    class _RequestLike(Protocol):
        # Structural stand-in for microdot.Request: typed via the vendored upstream stub (ext/typings/microdot/),
        # which leaves get/put/route unannotated (v2.7.0).
        @property
        def json(self) -> object: ...

        @property
        def sock(self) -> "tuple[_Holder, _Holder]": ...  # read-only, so any holder pair satisfies it

# Global catalog numbers, valid on any logger.
_ERR_CALLBACK = const(14)

# The one envelope code catalog (SPECIFICATION.md C.5.3): every code listed has a producer; a shaped HTTP
# error uses its status as its code.
_STANDARD_CODES: dict[int, str] = {
    0: "Command executed",
    1: "Invalid JSON request",
    400: "Bad request",
    404: "Not found",
    405: "Method not allowed",
    413: "Payload too large",
    500: "Internal server error",
}
_UNKNOWN_DESCR = const("Unknown error")  # the descr of a code the catalog does not list


async def handle_set_cmd(
    reader: "SensorReaderConfig",
    data: "JsonMapping",
    cfg_vals: "ConfigSchema",
    post_fct: "Callable[[], None] | None" = None,
    post_asy_fct: "AsyncCallback | None" = None,
) -> "WriteValidity":
    # Persist and push already ran per field in reader._set_dict_cfg(); a per-field outcome is detail in the endpoint's
    # "result". The post-write hook runs once per call, only after a changed field: one hook per endpoint, not one per
    # field, as legacy's post_fct/post_asy_fct (agent, 2026-08-03).
    results = await reader._set_dict_cfg(data, cfg_vals)
    if any(status == VALID for status in results.values()):
        try:
            if post_fct is not None:
                post_fct()
            if post_asy_fct is not None:
                await post_asy_fct()
        except Exception as e:
            report_if_fatal(e)
            await reader.pr.err_s("Post-write hook failed:", e, errno=_ERR_CALLBACK)
            results = dict.fromkeys(results, FAILED)
    return results


def make_response(code: int, descr: str | None = None, result: "JsonMapping | None" = None) -> "ResponseEnvelope":
    # Pure and total: never raises, no I/O. code == 0 is the only "OK" outcome (matches every existing
    # endpoint's convention), every other code "ERR"; an uncatalogued code without descr reads "Unknown error".
    if descr is None:
        descr = _STANDARD_CODES.get(code, _UNKNOWN_DESCR)
    return {
        "res": "OK" if code == 0 else "ERR",
        "code": code,
        "descr": descr,
        "result": {} if result is None else result,
    }

