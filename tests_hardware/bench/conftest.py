"""Bench-tier fixtures: the board must run the image this round built (its record beside the .uf2 against GET /system's
build date, device and lwIP ensemble; check_image() mid-session), and no test may leave an E or W entry in any logger
beyond those its provokes_log("<why>", (logger, kind, catalog name), ...) names (no_unprovoked_log_entry)."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, NoReturn, Protocol

import error_log_helpers
import harness
import http_client
import micropython_overrides
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

# @tunable l4.board_image_system_timeout_s = 10.0
_SYSTEM_TIMEOUT_S = 10.0
_REFLASH = "manual step: reflash the round's standard image (scripts/build_firmware.py), or rebuild from this tree"
_TICK_OFFSET = "the board runs the tick-offset test image"
_BENCH_DIR = Path(__file__).resolve().parent


class _SessionNote(Protocol):
    # The root conftest's session_note fixture: record_session_note() bound to this session.
    def __call__(self, text: str, *, recovery: bool = False, source: str) -> None: ...


class _Carry(NamedTuple):
    # A window an ends_unreachable test left open: its first read, the clears made by then, the entries admitted, the tests.
    before: "dict[str, error_log_helpers.ErrcountEntry]"
    clears: int
    expected: "frozenset[tuple[str, str, int]]"
    tests: "tuple[str, ...]"


# The one window still open, if any: set at an unanswered end, closed at the next read that answers.
_CARRIED: "list[_Carry]" = []


class _StandardStateExit(Protocol):
    # The root conftest's standard_state_exit fixture: the console message, then the failed session start.
    def __call__(self, deviations: "Sequence[tuple[str, str, str, str]]") -> NoReturn: ...


def record_path(option: "str | None", bench_device: str) -> Path:
    # --image-record when given (a throwaway worktree's record), else the bench device's own beside its .uf2.
    return Path(option) if option else harness.REPO_ROOT / "build" / f"firmware-{bench_device}.json"


def load_record(path: Path) -> "dict[str, object]":
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        pytest.exit(f"no image record at {path}: build the bench image with scripts/build_firmware.py before a bench run", returncode=1)
    if not isinstance(record, dict):
        pytest.exit(f"the image record at {path} holds no JSON object: rebuild it with scripts/build_firmware.py", returncode=1)
    return record


def image_deviations(record: "dict[str, object]", build: object, bench_device: str, *, allow_rollover: bool) -> "list[tuple[str, str, str, str]]":
    # Each way the board's image differs from the record this round built, as standard-state deviations; none is repaired.
    found: list[tuple[str, str, str, str]] = []
    if record.get("device") != bench_device:
        found.append(("image device", repr(record.get("device")), repr(bench_device), _REFLASH))
    board_date = build.get("BuildDate") if isinstance(build, dict) else f"no build object ({build!r})"
    if board_date != record.get("BuildDate"):
        found.append(("image BuildDate", repr(board_date), repr(record.get("BuildDate")), _REFLASH))
    lwip, max_connections = record.get("lwip"), record.get("maxConnections")
    problems = [f"the record carries no lwip macros or maxConnections ({lwip!r}, {max_connections!r})"]
    if isinstance(lwip, dict) and all(isinstance(v, int) for v in lwip.values()) and isinstance(max_connections, int):
        problems = micropython_overrides.check_lwip_ensemble(lwip, max_connections)
    if problems:
        found.append(("image lwIP ensemble", "; ".join(problems), "no finding", _REFLASH))
    configured = harness.configured_max_connections(bench_device)
    if max_connections != configured:
        found.append(("image maxConnections", repr(max_connections), f"{configured} (this tree's device TOML)", _REFLASH))
    overrides = record.get("overrides")
    if isinstance(overrides, list) and micropython_overrides.TICK_OFFSET_DIR_NAME in overrides and not allow_rollover:
        found.append(("tick-offset test image", _TICK_OFFSET, "the round's standard image", "manual step: reflash the round's standard image"))
    return found


def check_image(dut_ip: str, record: "dict[str, object]", *, allow_rollover: bool = False) -> "list[tuple[str, str, str, str]]":
    # The board's GET /system build against the record, strict: anything but a 200 object is itself a deviation.
    res = http_client.fetch(dut_ip, 80, "GET", "/system", timeout_s=_SYSTEM_TIMEOUT_S)
    try:
        body = res.json() if res.status_code == 200 else None
    except (ValueError, TypeError):  # no JSON, or a JSON value other than an object
        body = None
    build = body.get("build") if isinstance(body, dict) else f"GET /system {res.status_code} {res.body[:80]!r}"
    return image_deviations(record, build, harness.bench_device(), allow_rollover=allow_rollover)


@pytest.fixture(scope="session", autouse=True)
def board_image(dut_ip: str, bench_device_name: str, request: pytest.FixtureRequest, standard_state_exit: _StandardStateExit, session_note: _SessionNote) -> "dict[str, object]":
    path = record_path(request.config.getoption("--image-record"), bench_device_name)
    record = load_record(path)
    deviations = check_image(dut_ip, record, allow_rollover=request.config.getoption("--allow-multi-day-rollover"))
    if deviations:
        standard_state_exit(deviations)
    which = f"overrides {record.get('overrides')!r}, uartCrc {record.get('uartCrc')!r}, BuildDate {record.get('BuildDate')!r}"
    if record.get("dirty") is True:
        session_note(f"local-only image: revert after this round ({which})", source="board_image")
    else:
        session_note(f"image: {which}", source="board_image")
    return record


@pytest.fixture
def log_check_host(dut_ip: str) -> "Callable[[], str]":
    # Where no_unprovoked_log_entry reads GET /status, asked at each read; a module reaching the board another way
    # overrides it.
    return lambda: dut_ip


@pytest.fixture(autouse=True)
def no_unprovoked_log_entry(request: pytest.FixtureRequest, log_check_host: "Callable[[], str]") -> "Iterator[None]":
    # GET /status before and after each bench test, clearing and writing nothing: an E or W entry in any logger beyond the
    # test's provokes_log set fails it, before any clear it made too. An unanswered ends_unreachable end carries its window.
    test, expected = request.node.nodeid, _expected_entries(request.node)
    window = _Carry({}, error_log_helpers.clears_made(), expected, (test,))
    if _CARRIED:
        carried = _CARRIED.pop()
        read = _try_read_logs(log_check_host)
        if read is None:
            window = carried._replace(expected=carried.expected | expected, tests=(*carried.tests, test))
        else:
            _check(carried, read)
            window = window._replace(before=read)
    else:
        window = window._replace(before=_read_logs(log_check_host, test, "before"))
    yield
    if request.node.get_closest_marker("ends_unreachable") is None:
        _check(window, _read_logs(log_check_host, test, "after"))
        return
    after = _try_read_logs(log_check_host)
    if after is None:
        _CARRIED.append(window)
    else:
        _check(window, after)


@pytest.fixture(scope="session", autouse=True)
def log_check_carry_settled(dut_ip: str) -> "Iterator[None]":
    # A window still carried when the session ends is checked against one last read of the board.
    yield
    if _CARRIED:
        carried = _CARRIED.pop()
        _check(carried, _read_logs(lambda: dut_ip, " + ".join(carried.tests), "after"))


def pytest_collection_modifyitems(config: "pytest.Config | None", items: "list[pytest.Item]") -> None:
    # A bench test's provokes_log is refused at collection unless it names its reason and live catalog entries.
    del config
    refused = [f"{item.nodeid}: {problem}" for item in items if Path(item.path).is_relative_to(_BENCH_DIR) and (problem := _marker_problem(item)) is not None]
    if refused:
        raise pytest.UsageError("malformed provokes_log marker(s):\n" + "\n".join(refused))


def _check(window: _Carry, after: "dict[str, error_log_helpers.ErrcountEntry]") -> None:
    error_log_helpers.assert_no_unprovoked_entry(window.before, after, " + ".join(window.tests), pre_clear=error_log_helpers.reads_before_clears(window.clears), expected=window.expected)


def _expected_entries(node: "pytest.Item") -> "frozenset[tuple[str, str, int]]":
    marker = node.get_closest_marker("provokes_log")
    if marker is None:
        return frozenset()
    try:
        return error_log_helpers.provoked_entries(tuple(marker.args), marker.kwargs)[1]
    except ValueError as exc:
        pytest.fail(f"{node.nodeid}: {exc}", pytrace=False)


def _marker_problem(item: "pytest.Item") -> "str | None":
    marker = item.get_closest_marker("provokes_log")
    try:
        if marker is not None:
            error_log_helpers.provoked_entries(tuple(marker.args), marker.kwargs)
    except ValueError as exc:
        return str(exc)
    return None


def _read_logs(log_check_host: "Callable[[], str]", test: str, when: str) -> "dict[str, error_log_helpers.ErrcountEntry]":
    # One GET /status under the helpers' own read timeout; a board unreachable or still booting at a test's bound fails
    # that test by name, with no traceback, rather than hanging or raising a transport error out of the fixture.
    host = log_check_host()
    try:
        return error_log_helpers.get_errcount(host)
    except (OSError, http_client.HTTP_ERROR, AssertionError, ValueError, TypeError) as exc:
        pytest.fail(f"{test}: the log check cannot read the loggers {when} the test - GET /status on {host}: {exc!r}; a test must leave the board serving", pytrace=False)


def _try_read_logs(log_check_host: "Callable[[], str]") -> "dict[str, error_log_helpers.ErrcountEntry] | None":
    # The same bounded read for a window that may stay open: None where the board does not answer.
    try:
        return error_log_helpers.get_errcount(log_check_host())
    except (OSError, http_client.HTTP_ERROR, AssertionError, ValueError, TypeError):
        return None
