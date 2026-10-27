"""tests_hardware/bench/conftest.py's no_unprovoked_log_entry on faked GET /status reads: a new E or W entry in any
logger fails the test naming the logger, code, catalog name and test; provokes_log("<why>") exempts a test and a
marker without its reason is refused; the hotspot module reads through the route its tests use at that moment."""

import json
import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests_hardware" / "bench"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests_hardware"))
import error_log_helpers
import evidence
import harness
import http_client
import markers
from _script_loader import load_script_module

from tests._error_codes import code, name

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterator, Mapping, Sequence

_TESTS_HARDWARE = Path(__file__).resolve().parents[1] / "tests_hardware"
_DUT_IP = "192.0.2.10"
_GATEWAY_IP = "192.168.4.1"


def _entry(counter: int, *slots: "tuple[str, int]") -> "dict[str, object]":
    history = [{"type": t, "num": n} for t, n in slots]
    return {"counter": counter, "history": [{"type": "N", "num": 0}] * (3 - len(history)) + history}


class _Node:
    def __init__(self, mark: "pytest.Mark | None") -> None:
        self.nodeid = "tests_hardware/bench/test_x.py::test_case"
        self.mark = mark

    def get_closest_marker(self, marker_name: str) -> "pytest.Mark | None":
        return self.mark if self.mark is not None and self.mark.name == marker_name else None


class _Request:
    def __init__(self, mark: "pytest.Mark | None" = None) -> None:
        self.node = _Node(mark)


class _Board:
    # GET /status answers from a list of errcount objects, one per read; reads past the list fail the test.
    def __init__(self, reads: "Sequence[Mapping[str, object]]") -> None:
        self.reads = list(reads)
        self.hosts: list[str] = []

    def fetch(self, host: str, _port: int, method: str, path: str, *_a: object, **_k: object) -> http_client.HttpResponse:
        if method == "PUT":
            return http_client.HttpResponse(200, {}, json.dumps({"res": "OK", "result": {"ResetErrors": "Valid"}}).encode())
        assert path == "/status", path
        self.hosts.append(host)
        assert self.reads, "a read the case did not expect"
        return http_client.HttpResponse(200, {}, json.dumps({"errcount": self.reads.pop(0)}).encode())


class _UnreadableBoard(_Board):
    # Read number `fail_at` fails as a board unreachable or still booting does: a transport error, or a non-200.
    def __init__(self, reads: "Sequence[Mapping[str, object]]", fail_at: int, failure: "OSError | int") -> None:
        super().__init__(reads)
        self.fail_at, self.failure = fail_at, failure
        self.timeouts: list[object] = []

    def fetch(self, host: str, _port: int, method: str, path: str, *_a: object, **_k: object) -> http_client.HttpResponse:
        if method == "GET" and len(self.hosts) == self.fail_at:
            self.hosts.append(host)
            self.timeouts.append(_k.get("timeout_s"))
            if isinstance(self.failure, int):
                return http_client.HttpResponse(self.failure, {}, b"booting")
            raise self.failure
        return super().fetch(host, _port, method, path, *_a, **_k)


def _bench_conftest() -> ModuleType:
    return load_script_module(_TESTS_HARDWARE / "bench" / "conftest.py", "bench_conftest_log_check")


def _drive(monkeypatch: pytest.MonkeyPatch, reads: "Sequence[Mapping[str, object]]", *, mark: "pytest.Mark | None" = None, during: "Callable[[], None]" = lambda: None, host: str = _DUT_IP, board: "_Board | None" = None) -> _Board:
    # The fixture's setup, the test body (`during`), then its teardown, against a board answering `reads` in turn.
    board = board if board is not None else _Board(reads)
    monkeypatch.setattr(http_client, "fetch", board.fetch)
    monkeypatch.setattr(evidence, "save_text", lambda *_a: Path("unused"))
    gen: Generator[None, None, None] = _bench_conftest().no_unprovoked_log_entry.__wrapped__(_Request(mark), lambda: host)
    next(gen)
    during()
    with pytest.raises(StopIteration):
        next(gen)
    assert not board.reads, f"reads left unread: {board.reads}"
    return board


def test_the_bench_check_is_an_autouse_fixture() -> None:
    fixture = _bench_conftest().no_unprovoked_log_entry
    assert getattr(fixture, "_fixture_function_marker", None) is not None and fixture._fixture_function_marker.autouse


def test_a_new_warning_fails_naming_the_logger_code_catalog_name_and_test(monkeypatch: pytest.MonkeyPatch) -> None:
    refused = code("W", "HTTP_REFUSED")
    with pytest.raises(AssertionError) as caught:
        _drive(monkeypatch, [{"WEBSERVER": _entry(0), "WIFI": _entry(0)}, {"WEBSERVER": _entry(1, ("W", refused)), "WIFI": _entry(0)}])
    text = str(caught.value)
    assert f"WEBSERVER W{refused} HTTP_REFUSED" in text and "test_x.py::test_case" in text and "WIFI" not in text, text


def test_a_new_error_fails_too(monkeypatch: pytest.MonkeyPatch) -> None:
    no_reply = code("E", "NTP_NO_REPLY")
    with pytest.raises(AssertionError, match=f"NTP E{no_reply} NTP_NO_REPLY"):
        _drive(monkeypatch, [{"NTP": _entry(0)}, {"NTP": _entry(1, ("E", no_reply))}])


def test_entries_older_than_the_test_and_no_new_one_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    old = {"WIFI": _entry(2, ("W", code("W", "WLAN_TO_HOTSPOT")), ("W", code("W", "WLAN_SILENT")))}
    board = _drive(monkeypatch, [old, old])
    assert board.hosts == [_DUT_IP, _DUT_IP], board.hosts


def test_an_entry_after_a_fallen_counter_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    # A clear the check did not see (a reboot's RAM-only loggers, a direct ResetErrors): the counter falls, yet the
    # entry logged after it is new.
    raised = code("E", "TASK_RAISED")
    with pytest.raises(AssertionError, match=f"SYSTEM E{raised} TASK_RAISED"):
        _drive(monkeypatch, [{"SYSTEM": _entry(3, ("E", raised), ("E", code("E", "TIMER")))}, {"SYSTEM": _entry(1, ("E", raised))}])


def test_a_clear_through_the_helper_then_the_same_history_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    # The one case the reads alone cannot tell from "nothing happened": the clear count tells it.
    garbage = code("E", "NTP_MALFORMED")
    same = {"NTP": _entry(1, ("E", garbage))}
    with pytest.raises(AssertionError, match=f"NTP E{garbage} NTP_MALFORMED"):
        _drive(monkeypatch, [same, same, same], during=lambda: error_log_helpers.reset_all_error_logs(_DUT_IP, "case"))


def test_a_repeat_of_the_newest_entry_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    # A repeat of the newest code spends no slot: the counter grows and the history reads the same.
    timeout = code("W", "HTTP_CALL_TIMEOUT")
    with pytest.raises(AssertionError, match=f"WEBSERVER W{timeout} HTTP_CALL_TIMEOUT"):
        _drive(monkeypatch, [{"WEBSERVER": _entry(1, ("W", timeout))}, {"WEBSERVER": _entry(2, ("W", timeout))}])


def test_a_logger_on_one_side_only_fails_as_a_shape_change(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(AssertionError, match="appeared \\['NEW'\\]"):
        _drive(monkeypatch, [{"WIFI": _entry(0)}, {"WIFI": _entry(0), "NEW": _entry(0)}])


def test_a_marked_test_is_exempt_and_never_read(monkeypatch: pytest.MonkeyPatch) -> None:
    board = _drive(monkeypatch, [], mark=pytest.mark.provokes_log("the test cuts NTP on purpose").mark)
    assert board.hosts == [], board.hosts


@pytest.mark.parametrize("mark", [pytest.mark.provokes_log.mark, pytest.mark.provokes_log("  ").mark, pytest.mark.provokes_log(reason="why").mark, pytest.mark.provokes_log("a", "b").mark])
def test_a_marker_without_its_one_reason_is_refused(monkeypatch: pytest.MonkeyPatch, mark: "pytest.Mark") -> None:
    with pytest.raises(pytest.fail.Exception, match="provokes_log takes one non-empty reason"):
        _drive(monkeypatch, [], mark=mark)


@pytest.mark.parametrize(("fail_at", "failure", "when"), [(0, TimeoutError("timed out"), "before"), (1, ConnectionRefusedError(111, "refused"), "after"), (1, 503, "after")])
def test_a_board_that_cannot_answer_fails_the_test_plainly_and_bounded(monkeypatch: pytest.MonkeyPatch, fail_at: int, failure: "OSError | int", when: str) -> None:
    # A board unreachable or still booting at a test's bounds: one read under the helpers' own timeout, then a failure
    # naming the test and the read, with no traceback - never a hang or a bare transport error from the fixture.
    board = _UnreadableBoard([{"WIFI": _entry(0)}], fail_at, failure)
    with pytest.raises(pytest.fail.Exception) as caught:
        _drive(monkeypatch, [], board=board)
    text = str(caught.value)
    assert "test_x.py::test_case" in text and f"cannot read the loggers {when} the test" in text and _DUT_IP in text, text
    assert caught.value.pytrace is False, "the failure carries a traceback"
    assert board.timeouts == [error_log_helpers._ERRCOUNT_TIMEOUT_S], board.timeouts


def test_provokes_log_is_in_the_one_marker_table() -> None:
    assert "provokes_log" in markers.MARKERS and "reason" in markers.MARKERS["provokes_log"]


def test_the_catalog_name_of_a_code_and_of_none() -> None:
    assert name("W", code("W", "HTTP_REFUSED")) == "HTTP_REFUSED" and name("E", code("E", "TASK_RAISED")) == "TASK_RAISED"
    assert name("W", 255) is None and name("X", 1) is None


def test_gained_entries_lines_the_reads_up_and_refuses_a_history_it_does_not_continue() -> None:
    a, b, c = ("W", 36), ("W", 37), ("W", 38)
    before = error_log_helpers.ErrcountEntry(counter=2, history=[{"type": t, "num": n} for t, n in (("N", 0), a, b)])
    shifted = error_log_helpers.ErrcountEntry(counter=3, history=[{"type": t, "num": n} for t, n in (a, b, c)])
    cleared = error_log_helpers.ErrcountEntry(counter=1, history=[{"type": t, "num": n} for t, n in (("N", 0), ("N", 0), c)])
    assert error_log_helpers.gained_entries(before, shifted) == [c]
    assert error_log_helpers.gained_entries(before, before) == []
    assert error_log_helpers.gained_entries(before, cleared) is None


def _hotspot() -> ModuleType:
    return load_script_module(_TESTS_HARDWARE / "bench" / "test_hotspot_role_reversal.py", "hotspot_log_check")


class _Bench:
    def __init__(self) -> None:
        self.gateway = _GATEWAY_IP

    def gateway_ip(self) -> str:
        if not self.gateway:
            raise harness.HardwareTestFailureError("no lease")
        return self.gateway


def test_the_hotspot_module_reads_through_its_gateway_until_the_radio_leaves_it() -> None:
    bench = _Bench()
    host = _hotspot().log_check_host.__wrapped__(bench, _DUT_IP, _GATEWAY_IP)
    assert host() == _GATEWAY_IP
    bench.gateway = ""
    assert host() == _DUT_IP


def test_the_hotspot_modules_gain_raises_where_the_history_does_not_continue() -> None:
    module = _hotspot()
    before = error_log_helpers.ErrcountEntry(counter=1, history=[{"type": "N", "num": 0}, {"type": "W", "num": 79}])
    after = error_log_helpers.ErrcountEntry(counter=2, history=[{"type": "W", "num": 79}, {"type": "W", "num": 80}])
    assert module._gained_entries(before, after) == [("W", 80)]
    with pytest.raises(harness.HardwareTestFailureError, match="does not continue"):
        module._gained_entries(after, before)


@pytest.fixture(autouse=True)
def _no_leftover_modules() -> "Iterator[None]":
    yield
    for module_name in ("bench_conftest_log_check", "hotspot_log_check"):
        sys.modules.pop(module_name, None)

