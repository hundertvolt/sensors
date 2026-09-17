"""Pins the product's own per-request ceiling (asy_webserver_service.py's `outer_cap_s` default) to
every place that mirrors or derives from it - the web UI's own give-up time and both test tiers'
ResetErrors client timeouts. Parsed from real source, since src/ can't be imported under CPython."""

import ast
import re
from pathlib import Path
from types import ModuleType

import pytest


def _default_for_parameter(source_path: Path, param: str) -> float:
    """The literal default of a keyword parameter, found anywhere in a module's function/method
    signatures. src/ is MicroPython-target code (`from machine import ...` at module level), so it is
    read with ast, never imported - same posonlyargs+args/defaults idiom as buildgen/defaults.py."""
    tree = ast.parse(source_path.read_text())
    # Collected rather than short-circuited on the first hit: a second signature declaring the same
    # parameter with a different default would make "the" ceiling ambiguous, and silently pinning
    # whichever one ast happened to reach first is exactly the drift this file exists to catch.
    found: set[float] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        args = node.args
        # Only keyword-position parameters carry a default here; zip the tail of args/posonlyargs
        # with the defaults list, plus the kwonly pairs, exactly as Python binds them.
        positional = args.posonlyargs + args.args
        # Both zips are equal-length by construction (the slice takes exactly as many parameters as
        # there are defaults; ast keeps kwonlyargs/kw_defaults in step), so strict=True can only
        # fire on a genuine ast-shape surprise.
        pairs = list(zip(positional[len(positional) - len(args.defaults):], args.defaults, strict=True))
        pairs += [(a, d) for a, d in zip(args.kwonlyargs, args.kw_defaults, strict=True) if d is not None]
        for arg, default in pairs:
            if arg.arg == param and isinstance(default, ast.Constant) and isinstance(default.value, int | float):
                found.add(float(default.value))
    assert found, f"no literal default for {param!r} found in {source_path}"
    assert len(found) == 1, f"{param!r} is declared with conflicting defaults {sorted(found)} in {source_path} - there is no single ceiling left to mirror"
    return found.pop()


def _keyword_in_call(source_path: Path, func_name: str, keyword: str) -> float:
    """The literal value passed as `keyword=` by a call inside `func_name`."""
    tree = ast.parse(source_path.read_text())
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == func_name):
            continue
        for call in ast.walk(node):
            if not isinstance(call, ast.Call):
                continue
            for kw in call.keywords:
                if kw.arg == keyword and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, int | float):
                    return float(kw.value.value)
    raise AssertionError(f"no literal {keyword}= found in {func_name}() in {source_path}")


@pytest.fixture(scope="session")
def outer_cap_s(repo_root: Path) -> float:
    return _default_for_parameter(repo_root / "src" / "asy_webserver_service.py", "outer_cap_s")


def test_the_web_ui_gives_up_exactly_at_the_servers_own_ceiling(repo_root: Path, outer_cap_s: float) -> None:
    # CLAUDE.md's src/<->js/ cross-language mirror obligation (SPECIFICATION.md Part G) applied to
    # the one number that decides whether a slow request is a server abort the UI can report or a
    # client-side give-up it cannot explain. Only the two ends being equal makes the first true.
    js_text = (repo_root / "js" / "poll-manager.js").read_text()
    match = re.search(r"export const DEFAULT_TIMEOUT_MS = (\d+);", js_text)
    assert match is not None, "js/poll-manager.js no longer declares DEFAULT_TIMEOUT_MS - update this mirror check with it"
    assert float(match.group(1)) / 1000.0 == outer_cap_s, f"js/poll-manager.js's DEFAULT_TIMEOUT_MS ({match.group(1)}ms) must mirror asy_webserver_service.py's outer_cap_s ({outer_cap_s}s)"


def test_the_ci_suites_mirrored_copy_of_the_ceiling_has_not_drifted(ci_suite: ModuleType, outer_cap_s: float) -> None:
    # _SERVER_OUTER_CAP_S carries a "keep in sync" comment and nothing enforced it; a drift would
    # silently make _RESET_ERRORS_TIMEOUT_S wrong in whichever direction the cap moved.
    assert outer_cap_s == ci_suite._SERVER_OUTER_CAP_S, f"scripts/_digital_twin_ci_suite.py's _SERVER_OUTER_CAP_S ({ci_suite._SERVER_OUTER_CAP_S}) no longer mirrors asy_webserver_service.py's outer_cap_s ({outer_cap_s})"


def test_the_ci_suites_reset_errors_timeout_can_actually_fire_as_a_server_abort(ci_suite: ModuleType, outer_cap_s: float) -> None:
    # A client timeout at or below the cap pre-empts the server's own abort and reports only
    # "something took too long"; far above it, the timeout is inert and says nothing about the real
    # budget (the flat 20.0 this replaced was exactly that). Just above is the one useful placement.
    assert outer_cap_s < ci_suite._RESET_ERRORS_TIMEOUT_S <= outer_cap_s + 5.0, f"_RESET_ERRORS_TIMEOUT_S ({ci_suite._RESET_ERRORS_TIMEOUT_S}) must sit just above the server's own {outer_cap_s}s cap so the suite observes the server's abort, not a bare client timeout"


def test_the_bench_tiers_reset_errors_timeout_sits_above_the_same_ceiling(repo_root: Path, outer_cap_s: float) -> None:
    # tests_hardware/ hardcodes its own value rather than deriving it (it has no import path to
    # src/), so it is the copy most likely to drift. Below the cap, a slow-but-legitimate reset on
    # real hardware reads as a client timeout and gets misdiagnosed as a network fault.
    reset_timeout = _keyword_in_call(repo_root / "tests_hardware" / "error_log_helpers.py", "reset_all_error_logs", "timeout_s")
    assert reset_timeout > outer_cap_s, f"tests_hardware/error_log_helpers.py's reset timeout ({reset_timeout}s) must sit above the server's own {outer_cap_s}s cap"
