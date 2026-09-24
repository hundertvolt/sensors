"""Pins the product's own request timeouts (asy_webserver_service.py's `outer_cap_s`/`per_call_timeout_s`)
to every place that mirrors or must stay inside them - the web UI's give-up time, both tiers' ResetErrors
timeouts, the bench's connection-holding instruments. Read with ast, since src/ can't be imported here."""

import ast
import re
import socket
import sys
import threading
import time
import warnings
from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module


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


def _module_constant(source_path: Path, name: str) -> float:
    """A module-level numeric constant's literal value."""
    tree = ast.parse(source_path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, int | float) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return float(node.value.value)
    raise AssertionError(f"no module-level numeric constant {name!r} in {source_path}")


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
    # tests_hardware/ hardcodes its value, having no import path to src/, so it is the copy most
    # likely to drift. Below the cap a slow-but-legitimate reset reads as a client timeout and is
    # misdiagnosed as a network fault (BACKLOG item 24 has the measurements).

    # Only the lower bound is asserted: unlike the twin's loopback copy, this one carries extra
    # slack for real WiFi latency on the server abort's own close.
    helpers = repo_root / "tests_hardware" / "error_log_helpers.py"
    reset_timeout = _module_constant(helpers, "_RESET_ERRORS_TIMEOUT_S")
    assert reset_timeout > outer_cap_s, f"tests_hardware/error_log_helpers.py's reset timeout ({reset_timeout}s) must sit above the server's own {outer_cap_s}s cap"
    # It must also actually be the value the helper passes - a named constant that no call site uses
    # would satisfy the bound above while every real request still ran on a stale literal.
    assert "timeout_s=_RESET_ERRORS_TIMEOUT_S" in helpers.read_text(), "reset_all_error_logs() must pass _RESET_ERRORS_TIMEOUT_S, not a literal of its own"


# The two instruments that HOLD connections open against the board. Both failed silently on silicon
# when they outlived the firmware's own timeouts (SPECIFICATION.md H.7.1): the probe walked past the
# ceiling, the holder measured an idle heap. Neither timeout is per-device, so src/'s default is every device's.


@pytest.fixture(scope="session")
def per_call_timeout_s(repo_root: Path) -> float:
    return _default_for_parameter(repo_root / "src" / "asy_webserver_service.py", "per_call_timeout_s")


def _largest_shipped_ceiling(repo_root: Path) -> int:
    from buildgen.validate import device_max_connections, webserver_init_default

    shipped = [p for p in (repo_root / "devices").glob("*.toml") if not p.name.startswith("zz_test_")]
    return max([webserver_init_default(repo_root / "src", "max_connections")] + [device_max_connections(p, repo_root / "src") for p in shipped])


def test_the_ceiling_probe_can_walk_its_whole_limit_inside_the_servers_own_timeouts(repo_root: Path, outer_cap_s: float, per_call_timeout_s: float) -> None:
    # discover_max_connections() pads every held connection once per dwell_s, so the idle-read
    # timeout never fires, and needs its first connection held until the last - under the outer cap.
    harness = repo_root / "tests_hardware" / "harness.py"
    dwell_s, probe_limit = _default_for_parameter(harness, "dwell_s"), _default_for_parameter(harness, "probe_limit")
    assert dwell_s < per_call_timeout_s, f"dwell_s ({dwell_s}s) must sit under per_call_timeout_s ({per_call_timeout_s}s), or a padded connection is still closed as silent"
    assert probe_limit * dwell_s < outer_cap_s, f"a {probe_limit * dwell_s:.1f}s walk (probe_limit {probe_limit}, dwell_s {dwell_s}s) outlives the server's {outer_cap_s}s outer cap"
    assert probe_limit > _largest_shipped_ceiling(repo_root), f"probe_limit ({probe_limit}) cannot find a ceiling of {_largest_shipped_ceiling(repo_root)}"


def test_the_ceiling_holder_recycles_and_drips_inside_the_servers_own_timeouts(repo_root: Path, outer_cap_s: float, per_call_timeout_s: float) -> None:
    # test_heap_under_connection_ceiling.py keeps a ceiling full by dripping a header line (under the
    # idle-read timeout) and recycling each connection (under the whole-request cap).
    holder = repo_root / "tests_hardware" / "bench" / "test_heap_under_connection_ceiling.py"
    drip_s, recycle_s = _module_constant(holder, "_DRIP_INTERVAL_S"), _module_constant(holder, "_RECYCLE_S")
    assert drip_s < per_call_timeout_s, f"_DRIP_INTERVAL_S ({drip_s}s) must sit under per_call_timeout_s ({per_call_timeout_s}s), or a held connection is closed as silent"
    assert recycle_s < outer_cap_s, f"_RECYCLE_S ({recycle_s}s) must sit under outer_cap_s ({outer_cap_s}s), or the server reclaims the connection first and the heap is measured idle"


# ---------------------------------------------------------------------------
# The parsers' own guards. Every mirror check above is only as trustworthy as the number it reads
# out of src/, so the two ways that read can go quietly wrong - no default found, or several
# conflicting ones - are exercised directly against synthetic sources rather than assumed.
# ---------------------------------------------------------------------------


def test_conflicting_defaults_are_refused_rather_than_silently_picking_one(tmp_path: Path) -> None:
    # The drift this catches: a second overload/helper declaring the same parameter with its own
    # value. ast.walk() order is not the source order a reader would assume, so "whichever came
    # first" would pin an arbitrary one of the two and still report every mirror as in sync.
    source = tmp_path / "two_defaults.py"
    source.write_text("def serve(*, outer_cap_s: float = 15.0) -> None: ...\ndef helper(outer_cap_s: float = 30.0) -> None: ...\n")
    with pytest.raises(AssertionError, match="conflicting defaults"):
        _default_for_parameter(source, "outer_cap_s")


def test_a_parameter_that_carries_no_literal_default_is_refused(tmp_path: Path) -> None:
    # A required parameter, or one defaulting to an expression rather than a literal, leaves nothing
    # to mirror. Failing loud here is what stops the ceiling checks degrading into no-ops.
    source = tmp_path / "no_default.py"
    source.write_text("_CAP = 15.0\ndef serve(outer_cap_s: float) -> None: ...\ndef other(*, outer_cap_s: float = _CAP) -> None: ...\n")
    with pytest.raises(AssertionError, match="no literal default"):
        _default_for_parameter(source, "outer_cap_s")


def test_the_same_default_declared_twice_is_not_a_conflict(tmp_path: Path) -> None:
    # The guard must bite on disagreement only - two signatures agreeing on the ceiling is exactly
    # the mirroring this file wants, not a failure.
    source = tmp_path / "agreeing.py"
    source.write_text("def serve(*, outer_cap_s: float = 15.0) -> None: ...\ndef again(outer_cap_s: int = 15) -> None: ...\n")
    assert _default_for_parameter(source, "outer_cap_s") == 15.0


def test_defaults_are_read_from_every_argument_position(tmp_path: Path) -> None:
    # Python binds posonly/positional/kwonly defaults from two separate ast lists, and the real
    # signature has moved between those positions before. Missing one reads as "no default at all".
    posonly = tmp_path / "posonly.py"
    posonly.write_text("def serve(outer_cap_s: float = 15.0, /) -> None: ...\n")
    assert _default_for_parameter(posonly, "outer_cap_s") == 15.0
    trailing = tmp_path / "trailing.py"
    trailing.write_text("def serve(self, app: object, outer_cap_s: float = 15.0) -> None: ...\n")
    assert _default_for_parameter(trailing, "outer_cap_s") == 15.0


def test_a_missing_module_constant_is_refused_rather_than_read_as_zero(tmp_path: Path) -> None:
    # tests_hardware/'s copy is the one most likely to be renamed away, and a parser returning a
    # falsy placeholder would make the "above the cap" bound fail confusingly instead of naming it.
    source = tmp_path / "constants.py"
    source.write_text("_OTHER_TIMEOUT_S = 30.0\n")
    with pytest.raises(AssertionError, match="no module-level numeric constant"):
        _module_constant(source, "_RESET_ERRORS_TIMEOUT_S")


def test_a_non_numeric_constant_does_not_satisfy_the_lookup(tmp_path: Path) -> None:
    # A constant turned into a string/None keeps the name alive while making every comparison
    # against it meaningless - so the name matching is deliberately not enough on its own.
    source = tmp_path / "stringly.py"
    source.write_text('_RESET_ERRORS_TIMEOUT_S = "30.0"\n')
    with pytest.raises(AssertionError, match="no module-level numeric constant"):
        _module_constant(source, "_RESET_ERRORS_TIMEOUT_S")


@pytest.fixture(scope="module")
def ceiling_holder(repo_root: Path) -> ModuleType:
    sys.path.insert(0, str(repo_root / "tests_hardware"))  # the bench module's own bare imports
    with warnings.catch_warnings():  # its markers are registered by tests_hardware/conftest.py, not here
        warnings.simplefilter("ignore", pytest.PytestUnknownMarkWarning)
        return load_script_module(repo_root / "tests_hardware" / "bench" / "test_heap_under_connection_ceiling.py", "bench_ceiling_holder")


def _connections_the_holder_opens(holder: ModuleType, *, server_answers: bool, window_s: float = 0.6) -> "tuple[int, int]":
    # A loopback server that either parks every connection, as the firmware does mid-request, or
    # closes it at once, as it does on answering. Returns (connections opened, live count at the end).
    server = socket.create_server(("127.0.0.1", 0))
    server.settimeout(0.05)
    accepted: list[socket.socket] = []
    done = threading.Event()

    def serve() -> None:
        while not done.is_set():
            try:
                conn, _addr = server.accept()
            except TimeoutError:
                continue
            accepted.append(conn)
            if server_answers:
                conn.close()

    live, lock, stop = [0], threading.Lock(), threading.Event()
    threads = [threading.Thread(target=serve), threading.Thread(target=holder._park_one_connection, args=("127.0.0.1", live, lock, stop, 0.0, server.getsockname()[1]))]
    for thread in threads:
        thread.start()
    time.sleep(window_s)
    opened, at_end = len(accepted), live[0]
    stop.set()
    done.set()
    for thread in threads:
        thread.join(timeout=5.0)
    for conn in accepted:
        conn.close()
    server.close()
    return opened, at_end


def test_the_ceiling_holder_keeps_a_parked_connection_until_its_recycle_time(ceiling_holder: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # Many drips, one connection: nothing to read on a parked socket is not a reason to recycle it.
    # The shape it had raised out of the drip loop on the first empty read, recycling every drip.
    monkeypatch.setattr(ceiling_holder, "_DRIP_INTERVAL_S", 0.05)
    monkeypatch.setattr(ceiling_holder, "_RECYCLE_S", 5.0)
    assert _connections_the_holder_opens(ceiling_holder, server_answers=False) == (1, 1)


def test_the_ceiling_holder_takes_a_fresh_connection_once_the_server_answers(ceiling_holder: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ceiling_holder, "_DRIP_INTERVAL_S", 0.05)
    monkeypatch.setattr(ceiling_holder, "_RECYCLE_S", 5.0)
    opened, _live = _connections_the_holder_opens(ceiling_holder, server_answers=True)
    assert opened >= 2, opened
