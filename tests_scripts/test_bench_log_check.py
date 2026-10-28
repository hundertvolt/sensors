"""tests_hardware/bench/conftest.py's no_unprovoked_log_entry on faked GET /status reads: a new E or W entry in any
logger fails the test naming the logger, code, catalog name and test, unless provokes_log("<why>", entries...) names it;
a malformed marker is refused, at collection too; ends_unreachable carries a read on; the hotspot module's route."""

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


_REFUSED = ("WEBSERVER", "W", "HTTP_REFUSED")
_MARK = pytest.mark.provokes_log("the burst is refused at the ceiling", _REFUSED).mark
_UNREACHABLE = pytest.mark.ends_unreachable.mark


class _Node:
    def __init__(self, mark: "pytest.Mark | None", *more: "pytest.Mark", nodeid: str = "tests_hardware/bench/test_x.py::test_case") -> None:
        self.nodeid = nodeid
        self.path = Path(__file__).resolve().parents[1] / nodeid.split("::", 1)[0]
        self.marks = [m for m in (mark, *more) if m is not None]

    def get_closest_marker(self, marker_name: str) -> "pytest.Mark | None":
        return next((m for m in self.marks if m.name == marker_name), None)


class _Request:
    def __init__(self, mark: "pytest.Mark | None" = None, *more: "pytest.Mark", nodeid: str = "tests_hardware/bench/test_x.py::test_case") -> None:
        self.node = _Node(mark, *more, nodeid=nodeid)


class _Board:
    # GET /status answers from a list of errcount objects, one per read; reads past the list fail the test.
    def __init__(self, reads: "Sequence[Mapping[str, object] | OSError]") -> None:
        self.reads = list(reads)
        self.hosts: list[str] = []

    def fetch(self, host: str, _port: int, method: str, path: str, *_a: object, **_k: object) -> http_client.HttpResponse:
        if method == "PUT":
            return http_client.HttpResponse(200, {}, json.dumps({"res": "OK", "result": {"ResetErrors": "Valid"}}).encode())
        assert path == "/status", path
        self.hosts.append(host)
        assert self.reads, "a read the case did not expect"
        read = self.reads.pop(0)
        if isinstance(read, OSError):  # a board unreachable at this read
            raise read
        return http_client.HttpResponse(200, {}, json.dumps({"errcount": read}).encode())


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


def _drive(monkeypatch: pytest.MonkeyPatch, reads: "Sequence[Mapping[str, object] | OSError]", *, mark: "pytest.Mark | None" = None, more: "Sequence[pytest.Mark]" = (), during: "Callable[[], None]" = lambda: None, board: "_Board | None" = None, conftest: "ModuleType | None" = None, nodeid: str = "tests_hardware/bench/test_x.py::test_case") -> _Board:
    # The fixture's setup, the test body (`during`), then its teardown, against a board answering `reads` in turn.
    board = board if board is not None else _Board(reads)
    monkeypatch.setattr(http_client, "fetch", board.fetch)
    monkeypatch.setattr(evidence, "save_text", lambda *_a: Path("unused"))
    module = conftest if conftest is not None else _bench_conftest()
    gen: Generator[None, None, None] = module.no_unprovoked_log_entry.__wrapped__(_Request(mark, *more, nodeid=nodeid), lambda: _DUT_IP)
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


def test_a_marked_test_is_read_and_the_entries_it_names_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    refused = code("W", "HTTP_REFUSED")
    board = _drive(monkeypatch, [{"WEBSERVER": _entry(0)}, {"WEBSERVER": _entry(2, ("W", refused), ("W", refused))}], mark=_MARK)
    assert board.hosts == [_DUT_IP, _DUT_IP], board.hosts


def test_an_entry_a_marked_test_does_not_name_fails_naming_it(monkeypatch: pytest.MonkeyPatch) -> None:
    # The set is per logger: the same code in another logger is outside it, as is another code in the named one.
    refused, no_reply, timeout = code("W", "HTTP_REFUSED"), code("E", "NTP_NO_REPLY"), code("W", "HTTP_CALL_TIMEOUT")
    before = {"WEBSERVER": _entry(0), "NTP": _entry(0), "WIFI": _entry(0)}
    after = {"WEBSERVER": _entry(2, ("W", refused), ("W", timeout)), "NTP": _entry(1, ("E", no_reply)), "WIFI": _entry(1, ("W", refused))}
    with pytest.raises(AssertionError) as caught:
        _drive(monkeypatch, [before, after], mark=_MARK)
    text = str(caught.value)
    assert f"NTP E{no_reply} NTP_NO_REPLY" in text and f"WEBSERVER W{timeout} HTTP_CALL_TIMEOUT" in text and f"WIFI W{refused} HTTP_REFUSED" in text, text
    assert f"WEBSERVER W{refused} " not in text and "test_x.py::test_case" in text, text


def test_an_entry_a_marked_test_names_need_not_appear(monkeypatch: pytest.MonkeyPatch) -> None:
    quiet = {"WEBSERVER": _entry(0)}
    _drive(monkeypatch, [quiet, quiet], mark=_MARK)


def _clear() -> None:
    error_log_helpers.reset_all_error_logs(_DUT_IP, "case")


def _clear_twice() -> None:
    _clear()
    _clear()


def test_an_entry_logged_then_cleared_inside_an_unmarked_test_fails_it(monkeypatch: pytest.MonkeyPatch) -> None:
    # Reads: before, the clear's own read before its PUT, after - the entry lives only in the middle one.
    garbage = code("E", "NTP_MALFORMED")
    with pytest.raises(AssertionError, match=f"NTP E{garbage} NTP_MALFORMED"):
        _drive(monkeypatch, [{"NTP": _entry(0)}, {"NTP": _entry(1, ("E", garbage))}, {"NTP": _entry(0)}], during=_clear)


def test_a_clear_with_nothing_before_it_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    old = {"WIFI": _entry(1, ("W", code("W", "WLAN_TO_HOTSPOT")))}
    board = _drive(monkeypatch, [old, old, {"WIFI": _entry(0)}], during=_clear)
    assert board.hosts == [_DUT_IP] * 3, board.hosts


def test_a_marked_tests_entry_before_its_clear_inside_the_set_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    refused = code("W", "HTTP_REFUSED")
    _drive(monkeypatch, [{"WEBSERVER": _entry(0)}, {"WEBSERVER": _entry(1, ("W", refused))}, {"WEBSERVER": _entry(0)}], mark=_MARK, during=_clear)


def test_an_entry_before_a_clear_outside_a_marked_tests_set_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    refused, timeout = code("W", "HTTP_REFUSED"), code("W", "HTTP_CALL_TIMEOUT")
    with pytest.raises(AssertionError) as caught:
        _drive(monkeypatch, [{"WEBSERVER": _entry(0)}, {"WEBSERVER": _entry(2, ("W", refused), ("W", timeout))}, {"WEBSERVER": _entry(0)}], mark=_MARK, during=_clear)
    text = str(caught.value)
    assert f"WEBSERVER W{timeout} HTTP_CALL_TIMEOUT" in text and f"W{refused} " not in text, text


def test_every_segment_between_two_clears_is_checked_and_each_entry_named_once(monkeypatch: pytest.MonkeyPatch) -> None:
    # before -> 1st clear's read (continues), -> 2nd clear's read (all newer), -> after (all newer). WIFI's entry lives
    # in the first clear's read alone: the first clear erased it, so only that segment shows it.
    raised, no_reply, to_hotspot = code("E", "TASK_RAISED"), code("E", "NTP_NO_REPLY"), code("W", "WLAN_TO_HOTSPOT")
    reads = [
        {"SYSTEM": _entry(0), "NTP": _entry(0), "WIFI": _entry(0)},
        {"SYSTEM": _entry(0), "NTP": _entry(1, ("E", no_reply)), "WIFI": _entry(1, ("W", to_hotspot))},
        {"SYSTEM": _entry(1, ("E", raised)), "NTP": _entry(1, ("E", no_reply)), "WIFI": _entry(0)},
        {"SYSTEM": _entry(0), "NTP": _entry(0), "WIFI": _entry(0)},
    ]
    with pytest.raises(AssertionError) as caught:
        _drive(monkeypatch, reads, during=_clear_twice)
    text = str(caught.value)
    assert f"SYSTEM E{raised} TASK_RAISED" in text and text.count(f"NTP E{no_reply} NTP_NO_REPLY") == 1 and f"WIFI W{to_hotspot} WLAN_TO_HOTSPOT" in text, text


def test_a_clear_keeps_the_read_it_takes_before_its_put_and_adds_no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    # One GET (saved to the evidence, then kept parsed for the check) and the one PUT: no extra read, no extra write.
    seen = {"NTP": _entry(1, ("E", code("E", "NTP_NO_REPLY")))}
    calls: list[str] = []
    board = _Board([seen])

    def fetch(host: str, port: int, method: str, path: str, *a: object, **k: object) -> http_client.HttpResponse:
        calls.append(f"{method} {path}")
        return board.fetch(host, port, method, path, *a, **k)

    saved: list[str] = []

    def save_text(name: str, text: str) -> Path:
        saved.append(f"{name}:{text}")
        return Path(name)

    monkeypatch.setattr(http_client, "fetch", fetch)
    monkeypatch.setattr(evidence, "save_text", save_text)
    made = error_log_helpers.clears_made()
    _clear()
    assert calls == ["GET /status", "PUT /status"] and error_log_helpers.clears_made() == made + 1, calls
    kept = error_log_helpers.reads_before_clears(made)
    assert kept == [seen], kept
    assert len(saved) == 1 and saved[0].startswith("errcount-case.json:") and '"errcount"' in saved[0], saved


_MALFORMED = [
    pytest.mark.provokes_log.mark,
    pytest.mark.provokes_log("  ", _REFUSED).mark,
    pytest.mark.provokes_log(_REFUSED).mark,
    pytest.mark.provokes_log("why", _REFUSED, reason="why").mark,
    pytest.mark.provokes_log("a reason alone").mark,
    pytest.mark.provokes_log("why", ("WEBSERVER", "W")).mark,
    pytest.mark.provokes_log("why", ["WEBSERVER", "W", "HTTP_REFUSED"]).mark,
    pytest.mark.provokes_log("why", ("WEBSERVER", "X", "HTTP_REFUSED")).mark,
    pytest.mark.provokes_log("why", ("", "W", "HTTP_REFUSED")).mark,
    pytest.mark.provokes_log("why", ("WEBSERVER", "W", "NO_SUCH_NAME")).mark,
    pytest.mark.provokes_log("why", ("WIFI", "E", "WLAN_OFF")).mark,
    pytest.mark.provokes_log("why", ("WEBSERVER", "E", "HTTP_REFUSED")).mark,
]


@pytest.mark.parametrize("mark", _MALFORMED)
def test_a_marker_without_its_reason_and_live_entries_fails_the_test(monkeypatch: pytest.MonkeyPatch, mark: "pytest.Mark") -> None:
    # The reason, then each entry as (logger, "E" or "W", catalog name) with a live row: a retired name (WLAN_OFF) or a
    # name of the other kind is refused as an unknown one is.
    with pytest.raises(pytest.fail.Exception, match="test_case: provokes_log"):
        _drive(monkeypatch, [], mark=mark)


class _Item:
    def __init__(self, nodeid: str, mark: "pytest.Mark | None") -> None:
        node = _Node(mark, nodeid=nodeid)
        self.nodeid, self.path, self.get_closest_marker = node.nodeid, node.path, node.get_closest_marker


def test_collection_refuses_a_malformed_marker_naming_each_test() -> None:
    good = _Item("tests_hardware/bench/test_x.py::test_good", _MARK)
    bare = _Item("tests_hardware/bench/test_x.py::test_reason_alone", pytest.mark.provokes_log("a reason alone").mark)
    stale = _Item("tests_hardware/bench/test_y.py::test_stale", pytest.mark.provokes_log("why", ("WIFI", "E", "WLAN_OFF")).mark)
    hook = _bench_conftest().pytest_collection_modifyitems
    hook(None, [good, _Item("tests_hardware/bench/test_x.py::test_unmarked", None)])
    with pytest.raises(pytest.UsageError) as caught:
        hook(None, [good, bare, stale])
    text = str(caught.value)
    assert "test_reason_alone" in text and "test_stale" in text and "WLAN_OFF" in text and "test_good" not in text, text


def test_a_test_that_ends_unreachable_hands_its_first_read_to_the_next_read(monkeypatch: pytest.MonkeyPatch) -> None:
    # A: after-read refused (carried); B: its before-read answers, so A's window ends there and B is checked on its own.
    to_hotspot = code("W", "WLAN_TO_HOTSPOT")
    module = _bench_conftest()
    mark_a = pytest.mark.provokes_log("the streak fails", ("WIFI", "W", "WLAN_TO_HOTSPOT")).mark
    _drive(monkeypatch, [{"WIFI": _entry(0)}, ConnectionRefusedError(111, "refused")], mark=mark_a, more=[_UNREACHABLE], conftest=module, nodeid="tests_hardware/bench/test_x.py::test_a")
    gained = {"WIFI": _entry(1, ("W", to_hotspot))}
    _drive(monkeypatch, [gained, gained], conftest=module, nodeid="tests_hardware/bench/test_x.py::test_b")


def test_an_entry_outside_the_carried_set_fails_naming_the_carried_test(monkeypatch: pytest.MonkeyPatch) -> None:
    silent = code("W", "WLAN_SILENT")
    module = _bench_conftest()
    mark_a = pytest.mark.provokes_log("the streak fails", ("WIFI", "W", "WLAN_TO_HOTSPOT")).mark
    _drive(monkeypatch, [{"WIFI": _entry(0)}, TimeoutError("timed out")], mark=mark_a, more=[_UNREACHABLE], conftest=module, nodeid="tests_hardware/bench/test_x.py::test_a")
    with pytest.raises(AssertionError, match=f"test_x.py::test_a logged WIFI W{silent} WLAN_SILENT"):
        _drive(monkeypatch, [{"WIFI": _entry(1, ("W", silent))}, {"WIFI": _entry(1, ("W", silent))}], conftest=module, nodeid="tests_hardware/bench/test_x.py::test_b")


def test_a_next_test_that_cannot_read_either_extends_the_carried_window(monkeypatch: pytest.MonkeyPatch) -> None:
    # B's before-read refused too: its window starts at A's read, and the union of both sets admits what it logged.
    to_hotspot, silent, raised = code("W", "WLAN_TO_HOTSPOT"), code("W", "WLAN_SILENT"), code("E", "TASK_RAISED")
    module = _bench_conftest()
    mark_a = pytest.mark.provokes_log("the first streak fails", ("WIFI", "W", "WLAN_TO_HOTSPOT")).mark
    mark_b = pytest.mark.provokes_log("the second streak goes silent", ("WIFI", "W", "WLAN_SILENT")).mark
    _drive(monkeypatch, [{"WIFI": _entry(0), "SYSTEM": _entry(0)}, OSError(113, "no route")], mark=mark_a, more=[_UNREACHABLE], conftest=module, nodeid="tests_hardware/bench/test_x.py::test_a")
    both = {"WIFI": _entry(2, ("W", to_hotspot), ("W", silent)), "SYSTEM": _entry(0)}
    _drive(monkeypatch, [OSError(113, "no route"), both], mark=mark_b, conftest=module, nodeid="tests_hardware/bench/test_x.py::test_b")
    _drive(monkeypatch, [{"WIFI": _entry(0), "SYSTEM": _entry(0)}, OSError(113, "no route")], mark=mark_a, more=[_UNREACHABLE], conftest=module, nodeid="tests_hardware/bench/test_x.py::test_a")
    with pytest.raises(AssertionError, match=f"test_a \\+ tests_hardware/bench/test_x.py::test_b logged SYSTEM E{raised} TASK_RAISED"):
        _drive(monkeypatch, [OSError(113, "no route"), {"WIFI": _entry(0), "SYSTEM": _entry(1, ("E", raised))}], mark=mark_b, conftest=module, nodeid="tests_hardware/bench/test_x.py::test_b")


def test_a_window_still_carried_at_the_session_end_is_checked_then(monkeypatch: pytest.MonkeyPatch) -> None:
    raised = code("E", "TASK_RAISED")
    module = _bench_conftest()
    _drive(monkeypatch, [{"SYSTEM": _entry(0)}, OSError(113, "no route")], mark=_MARK, more=[_UNREACHABLE], conftest=module)
    board = _Board([{"SYSTEM": _entry(1, ("E", raised))}])
    monkeypatch.setattr(http_client, "fetch", board.fetch)
    settle: Generator[None, None, None] = module.log_check_carry_settled.__wrapped__(_DUT_IP)
    next(settle)
    with pytest.raises(AssertionError, match=f"test_x.py::test_case logged SYSTEM E{raised} TASK_RAISED"):
        next(settle)
    assert not board.reads and board.hosts == [_DUT_IP], board.hosts


def test_an_unreadable_end_without_ends_unreachable_still_fails_plainly(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(pytest.fail.Exception, match="cannot read the loggers after the test"):
        _drive(monkeypatch, [{"WEBSERVER": _entry(0)}, ConnectionRefusedError(111, "refused")], mark=_MARK)


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


def test_provokes_log_and_ends_unreachable_are_in_the_one_marker_table() -> None:
    assert "provokes_log" in markers.MARKERS and "reason" in markers.MARKERS["provokes_log"] and "catalog name" in markers.MARKERS["provokes_log"]
    assert "ends_unreachable" in markers.MARKERS and "carries" in markers.MARKERS["ends_unreachable"]


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

