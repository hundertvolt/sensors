"""Covers tests_hardware/http_client.py's is_ceiling_close(), the predicate two bench tests use to
tell a connection-ceiling refusal from a real transport failure. A wrong True is the dangerous
direction: it retries a genuine defect away, or files it in the "expected refusal" bucket."""

import errno
import http.client
import sys
import urllib.error
from pathlib import Path
from types import ModuleType

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

import http_client

# What _serve()'s reject-when-full branch actually looks like from the client: it closes without
# writing a response, so the kernel's TCP state decides which of these the client sees. F10/F11
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
    ValueError("not an OSError at all"),
)


@pytest.mark.parametrize("exc", _CEILING_SHAPES, ids=lambda e: type(e).__name__)
def test_every_ceiling_close_shape_is_recognised_directly(exc: BaseException) -> None:
    assert http_client.is_ceiling_close(exc), f"{type(exc).__name__} is how the ceiling's own close reaches a client"


@pytest.mark.parametrize("exc", _CEILING_SHAPES, ids=lambda e: type(e).__name__)
def test_the_same_shape_is_recognised_through_urlerrors_reason(exc: BaseException) -> None:
    # The shape both call sites actually see: they catch what http_client.fetch() raises, and
    # urllib.request wraps the transport error rather than letting it through.
    assert http_client.is_ceiling_close(urllib.error.URLError(exc)), f"URLError(reason={type(exc).__name__}) must be recognised through .reason"


@pytest.mark.parametrize("exc", _REAL_FAILURE_SHAPES, ids=lambda e: type(e).__name__)
def test_a_real_transport_failure_is_never_taken_for_a_refusal(exc: BaseException) -> None:
    # The biting direction. A True here makes test_bus_concurrency_under_api_load.py retry a real
    # defect away and test_network_resilience.py file it under "refused" instead of "other".
    assert not http_client.is_ceiling_close(exc), f"{type(exc).__name__} is a real failure, not the server closing at its ceiling"
    assert not http_client.is_ceiling_close(urllib.error.URLError(exc)), f"URLError(reason={type(exc).__name__}) is a real failure too"


def test_remote_disconnected_is_covered_by_the_tuple_rather_than_named_in_it() -> None:
    # The docstring's own claim, pinned: RemoteDisconnected subclasses ConnectionResetError and
    # BadStatusLine, so listing it separately would be redundant - but only while that holds.
    assert http.client.RemoteDisconnected not in http_client.CEILING_CLOSE
    assert issubclass(http.client.RemoteDisconnected, http_client.CEILING_CLOSE)


def test_an_httperror_is_a_real_answer_and_never_a_refusal() -> None:
    # fetch() already turns a non-2xx into an HttpResponse, so this only arrives when urllib raises
    # one past that - either way it carries a status line, which a closed-at-the-ceiling socket does not.
    exc = urllib.error.HTTPError("http://dut/status", 503, "Service Unavailable", {}, None)  # type: ignore[arg-type]
    assert not http_client.is_ceiling_close(exc)


def test_a_reason_that_is_not_an_exception_does_not_confuse_the_predicate() -> None:
    # urllib.error.URLError accepts any object as its reason, and a str one is common
    # ("[SSL] ..."). getattr's isinstance check has to hold for that, not just for exceptions.
    assert not http_client.is_ceiling_close(urllib.error.URLError("some textual reason"))
    assert not http_client.is_ceiling_close(Exception())


def _bench_module() -> ModuleType:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware" / "bench"))
    import test_bus_concurrency_under_api_load as bench

    return bench


def test_the_bench_retry_wrapper_counts_each_ceiling_retry_and_the_report_clears_them(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # The config-write arms' ceiling-vs-reset discriminator: a gated run prints these, so the count must be exact.
    bench = _bench_module()
    outcomes: list[BaseException | None] = [ConnectionResetError(errno.ECONNRESET, "reset"), ConnectionResetError(errno.ECONNRESET, "reset"), None]

    def fake_fetch(*_args: object, **_kwargs: object) -> http_client.HttpResponse:
        outcome = outcomes.pop(0)
        if outcome is not None:
            raise outcome
        return http_client.HttpResponse(200, {}, b"{}")

    monkeypatch.setattr(http_client, "fetch", fake_fetch)
    monkeypatch.setattr(bench.time, "sleep", lambda _s: None)
    bench._report_ceiling_retries("clear")
    assert bench.fetch("dut", 80, "GET", "/sensors").status_code == 200
    bench._report_ceiling_retries("arm")
    bench._report_ceiling_retries("again")
    lines = capsys.readouterr().out.splitlines()
    assert "CEILING_RETRIES arm: {'GET /sensors': 2}" in lines
    assert "CEILING_RETRIES again: none" in lines


def test_the_bench_retry_wrapper_never_counts_a_real_failure(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    bench = _bench_module()

    def fake_fetch(*_args: object, **_kwargs: object) -> http_client.HttpResponse:
        raise TimeoutError("timed out")

    monkeypatch.setattr(http_client, "fetch", fake_fetch)
    bench._report_ceiling_retries("clear")
    with pytest.raises(TimeoutError):
        bench.fetch("dut", 80, "PUT", "/sensors", {"x": 1})
    bench._report_ceiling_retries("arm")
    assert "CEILING_RETRIES arm: none" in capsys.readouterr().out.splitlines()
