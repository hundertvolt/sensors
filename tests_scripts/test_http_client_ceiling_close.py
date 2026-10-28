"""Covers tests_hardware/http_client.py's refusal class, which the bench tests use to tell a connection-ceiling refusal
from a real transport failure: fetch() raises CeilingRefusedError only for a close before any response byte. A wrong
refusal is the dangerous direction: it retries a genuine defect away, or files it in the "expected refusal" bucket."""

import email.message
import errno
import http.client
import io
import sys
import urllib.error
import urllib.request
from pathlib import Path
from types import ModuleType

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

import http_client

# What _serve()'s reject-when-full branch actually looks like from the client: it closes without
# writing a response, so the kernel's TCP state decides which of these the client sees. The bench
# measured the reset and the empty-read forms on real silicon.
_CEILING_SHAPES = (
    ConnectionResetError(errno.ECONNRESET, "Connection reset by peer"),
    ConnectionAbortedError(errno.ECONNABORTED, "Software caused connection abort"),
    BrokenPipeError(errno.EPIPE, "Broken pipe"),
    http.client.BadStatusLine(""),
    http.client.RemoteDisconnected("Remote end closed connection without response"),
)

# Everything a real failure arrives as. A timeout is the one worth naming: the DUT accepted the
# connection and then failed to answer, which is exactly the bug a retry would paper over.
_REAL_FAILURE_SHAPES = (
    TimeoutError("timed out"),
    ConnectionRefusedError(errno.ECONNREFUSED, "Connection refused"),
    OSError(errno.EHOSTUNREACH, "No route to host"),
    http.client.BadStatusLine("garbage"),
)


class _Opened:
    # urlopen()'s response: a status, headers and a body read in pieces - or a transport error once the body is read.
    def __init__(self, status: int, body: "bytes | BaseException") -> None:
        self.headers = email.message.Message()
        self.status = status
        self._body = body

    def __enter__(self) -> "_Opened":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def read(self, amt: int = -1) -> bytes:
        if isinstance(self._body, BaseException):
            raise self._body
        chunk, self._body = (self._body, b"") if amt < 0 else (self._body[:amt], self._body[amt:])
        return chunk


class _ReadCounting(io.BytesIO):
    # An HTTPError's body stream counting what was read off it, which outlives the stream's close.
    def __init__(self, body: bytes) -> None:
        super().__init__(body)
        self.consumed = 0

    def read(self, size: "int | None" = -1) -> bytes:
        chunk = super().read(size)
        self.consumed += len(chunk)
        return chunk


def _bench_module() -> ModuleType:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware" / "bench"))
    import test_bus_concurrency_under_api_load as bench

    return bench


@pytest.mark.parametrize("exc", _CEILING_SHAPES, ids=lambda e: type(e).__name__)
def test_a_ceiling_close_before_any_byte_is_a_refusal_from_fetch(monkeypatch: pytest.MonkeyPatch, exc: BaseException) -> None:
    _urlopen_raising(monkeypatch, exc)
    with pytest.raises(http_client.CeilingRefusedError) as info:
        http_client.fetch("dut", 80, "GET", "/status")
    assert info.value.__cause__ is exc and http_client.is_ceiling_close(info.value)


@pytest.mark.parametrize("exc", _CEILING_SHAPES, ids=lambda e: type(e).__name__)
def test_the_same_shape_is_a_refusal_through_urlerrors_reason(monkeypatch: pytest.MonkeyPatch, exc: BaseException) -> None:
    # urllib.request wraps the transport error rather than letting it through.
    wrapped = urllib.error.URLError(exc)
    _urlopen_raising(monkeypatch, wrapped)
    with pytest.raises(http_client.CeilingRefusedError) as info:
        http_client.fetch("dut", 80, "GET", "/status")
    assert info.value.__cause__ is wrapped


@pytest.mark.parametrize("exc", [*_REAL_FAILURE_SHAPES, *(urllib.error.URLError(e) for e in _REAL_FAILURE_SHAPES[:3])], ids=lambda e: type(e).__name__ + ("" if not isinstance(e, urllib.error.URLError) else f"({type(e.reason).__name__})"))
def test_a_real_transport_failure_is_never_taken_for_a_refusal(monkeypatch: pytest.MonkeyPatch, exc: BaseException) -> None:
    # The biting direction: a refusal here makes test_bus_concurrency_under_api_load.py retry a real defect away and
    # test_network_resilience.py file it under "refused" instead of "other". A garbled status line is an answer.
    _urlopen_raising(monkeypatch, exc)
    with pytest.raises(type(exc)) as info:
        http_client.fetch("dut", 80, "GET", "/status")
    assert info.value is exc and not http_client.is_ceiling_close(info.value)


def test_a_close_after_the_first_byte_is_a_response_cut_short_never_a_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    cut = ConnectionResetError(errno.ECONNRESET, "Connection reset by peer")
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_k: _Opened(200, cut))
    with pytest.raises(ConnectionResetError) as info:
        http_client.fetch("dut", 80, "GET", "/status")
    assert info.value is cut and not http_client.is_ceiling_close(info.value)


def test_remote_disconnected_is_covered_by_the_tuple_rather_than_named_in_it() -> None:
    # RemoteDisconnected subclasses ConnectionResetError and BadStatusLine, so listing it separately would be
    # redundant - but only while that holds.
    assert http.client.RemoteDisconnected not in http_client.CEILING_CLOSE
    assert issubclass(http.client.RemoteDisconnected, http_client.CEILING_CLOSE)


def test_an_httperror_is_a_real_answer_and_never_a_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    # A non-2xx carries a status line, which a closed-at-the-ceiling socket does not: fetch() returns it as a response.
    _urlopen_raising(monkeypatch, urllib.error.HTTPError("http://dut/status", 503, "Service Unavailable", email.message.Message(), io.BytesIO(b'{"error": "busy"}')))
    response = http_client.fetch("dut", 80, "GET", "/status")
    assert (response.status_code, response.json(), response.drained) == (503, {"error": "busy"}, False)


def test_a_reason_that_is_not_an_exception_does_not_confuse_the_predicate(monkeypatch: pytest.MonkeyPatch) -> None:
    # urllib.error.URLError accepts any object as its reason, and a str one is common ("[SSL] ...").
    textual = urllib.error.URLError("some textual reason")
    _urlopen_raising(monkeypatch, textual)
    with pytest.raises(urllib.error.URLError) as info:
        http_client.fetch("dut", 80, "GET", "/status")
    assert info.value is textual and not http_client.is_ceiling_close(Exception())


@pytest.mark.parametrize("answer", ["opened", "httperror"])
def test_read_body_false_drains_the_body_unkept_and_json_refuses_it(monkeypatch: pytest.MonkeyPatch, answer: str) -> None:
    body = b'{"x": "' + b"y" * 10_000 + b'"}'
    stream = _ReadCounting(body)
    opened = _Opened(200, body)
    if answer == "opened":
        monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_k: opened)
    else:
        _urlopen_raising(monkeypatch, urllib.error.HTTPError("http://dut/x", 404, "Not Found", email.message.Message(), stream))
    response = http_client.fetch("dut", 80, "GET", "/x", read_body=False)
    left = opened.read() if answer == "opened" else body[stream.consumed :]
    assert (response.body, response.drained, left) == (b"", True, b""), "the body was kept, or not read off the connection"
    with pytest.raises(ValueError, match="drained"):
        response.json()


@pytest.mark.parametrize("body", [b"[1, 2]", b"3", b'"text"', b"null"])
def test_json_refuses_any_value_but_an_object(body: bytes) -> None:
    with pytest.raises(TypeError, match="not an object"):
        http_client.HttpResponse(200, {}, body).json()


def _urlopen_raising(monkeypatch: pytest.MonkeyPatch, exc: BaseException) -> None:
    def urlopen(*_args: object, **_kwargs: object) -> object:
        raise exc

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)


def test_the_bench_retry_wrapper_counts_each_ceiling_retry_and_the_report_clears_them(monkeypatch: pytest.MonkeyPatch) -> None:
    # The config-write arms' ceiling-vs-reset discriminator reaches the run record as a test note: a
    # print is dropped by capture on a passing test, so the count must survive there, exact.
    bench = _bench_module()
    outcomes: list[BaseException | None] = [http_client.CeilingRefusedError("refused"), http_client.CeilingRefusedError("refused"), None]

    def fake_fetch(*_args: object, **_kwargs: object) -> http_client.HttpResponse:
        outcome = outcomes.pop(0)
        if outcome is not None:
            raise outcome
        return http_client.HttpResponse(200, {}, b"{}")

    monkeypatch.setattr(http_client, "fetch", fake_fetch)
    monkeypatch.setattr(bench.time, "sleep", lambda _s: None)
    notes: list[str] = []
    bench._take_ceiling_retries()
    assert bench.fetch("dut", 80, "GET", "/sensors").status_code == 200
    bench._report_ceiling_retries(notes.append, "arm")
    bench._report_ceiling_retries(notes.append, "again")
    assert notes == ["CEILING_RETRIES arm: {'GET /sensors': 2}", "CEILING_RETRIES again: none"]


@pytest.mark.parametrize("failure", [TimeoutError("timed out"), ConnectionResetError(errno.ECONNRESET, "reset inside the body")], ids=["timeout", "cut-short"])
def test_the_bench_retry_wrapper_never_counts_a_real_failure(monkeypatch: pytest.MonkeyPatch, failure: OSError) -> None:
    bench = _bench_module()

    def fake_fetch(*_args: object, **_kwargs: object) -> http_client.HttpResponse:
        raise failure

    monkeypatch.setattr(http_client, "fetch", fake_fetch)
    notes: list[str] = []
    bench._take_ceiling_retries()
    with pytest.raises(type(failure)):
        bench.fetch("dut", 80, "PUT", "/sensors", {"x": 1})
    bench._report_ceiling_retries(notes.append, "arm")
    assert notes == ["CEILING_RETRIES arm: none"]


def test_every_bench_test_in_the_module_notes_its_ceiling_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    # Any test's GET workers retry through fetch(), not only the two config-write arms: an autouse
    # fixture notes what is left at the end of every test, so no retried refusal is lost on a pass.
    bench = _bench_module()
    fixture = bench._ceiling_retries_noted
    assert getattr(fixture, "_fixture_function_marker", None) is not None or hasattr(fixture, "_pytestfixturefunction"), "_ceiling_retries_noted must be a pytest fixture"
    notes: list[str] = []
    gen = bench._noted_ceiling_retries(notes.append)
    next(gen)
    with bench._ceiling_retries_lock:
        bench._ceiling_retries["GET /status"] = 1
    with pytest.raises(StopIteration):
        next(gen)
    assert notes == ["CEILING_RETRIES rest of the test: {'GET /status': 1}"]
    gen = bench._noted_ceiling_retries(notes.append)
    next(gen)
    with pytest.raises(StopIteration):
        next(gen)
    assert len(notes) == 1, "a test with no retried refusal adds no note"
