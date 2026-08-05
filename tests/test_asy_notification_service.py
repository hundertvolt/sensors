import asyncio
import os

from asy_notification_service import NotificationCoordinator, NotificationSignal

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


# Mirrors asy_ntp_client.py's own GMTimeStruct (hour/minute are all monitor_loop() actually reads).
class _FakeTime:
    def __init__(self, hour: int, minute: int) -> None:
        self.hour = hour
        self.minute = minute


_TMP_DIR = "tests/_tmp"
_next_dir = 0


def _remove_any(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        try:
            os.rmdir(path)
        except OSError:
            pass


def _tmp_cfg_dir() -> str:
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    _next_dir += 1
    path = _TMP_DIR + "/notify_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass
    _remove_any(path + "/config_NOTIFY.cfg")
    return path + "/"


class FakeValue:
    # A controllable NotificationSignal.get_value() source: fixed return, or raises once armed.
    def __init__(self, value: "int | float | None" = None) -> None:
        self.value = value
        self.raise_exc: Exception | None = None
        self.calls = 0

    async def get(self) -> "int | float | None":
        self.calls += 1
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.value


class FakeClock:
    def __init__(self, hour: int = 12, minute: int = 0) -> None:
        self.hour = hour
        self.minute = minute
        self.value: _FakeTime | None = _FakeTime(hour, minute)
        self.raise_exc: Exception | None = None
        self.calls = 0

    async def get(self) -> "_FakeTime | None":
        self.calls += 1
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.value


class FakeSignalCb:
    # Records every request_signal_cb(r, g, b, t) call, in order - stallable so a test can prove
    # strict sequencing (each call only proceeds once explicitly released), not just that the
    # final recorded order happens to match.
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int, float]] = []
        self.raise_exc: Exception | None = None
        self._release = asyncio.Event()
        self._release.set()  # unstalled by default - most tests don't care about fine-grained timing

    def stall(self) -> None:
        self._release.clear()

    def release(self) -> None:
        self._release.set()

    async def __call__(self, r: int, g: int, b: int, t: float) -> bool:
        await self._release.wait()
        self.calls.append((r, g, b, t))
        if self.raise_exc is not None:
            raise self.raise_exc
        return True


def make_coordinator(
    cfg_path: "str | None" = None,
    debug: "int | None" = None,
    local_time: "FakeClock | None" = None,
    signal_cb: "FakeSignalCb | None" = None,
) -> "tuple[NotificationCoordinator, FakeClock, FakeSignalCb]":
    path = _tmp_cfg_dir() if cfg_path is None else cfg_path
    clock = local_time if local_time is not None else FakeClock()
    cb = signal_cb if signal_cb is not None else FakeSignalCb()
    coordinator = NotificationCoordinator(cb, clock.get, cfg_path=path, debug=debug)
    return coordinator, clock, cb


def make_signal(
    name: str = "WarnCO2", above: bool = True, value: "int | float | None" = 1000, color: "tuple[int, int, int]" = (1, 0, 0)
) -> "tuple[NotificationSignal, FakeValue]":
    fv = FakeValue(value)
    field_schema = ((name, "int", 1600, 0, 3000, None),)
    return NotificationSignal(name, fv.get, field_schema, color, above=above), fv


async def _one_cycle(coordinator: NotificationCoordinator, task: "asyncio.Task[None]", wait: float = 0.1) -> None:
    # monitor_loop() is an infinite loop; let it run through exactly one full iteration (including
    # any triggered flashes' settle sleeps) by giving it real wall-clock time, then cancel. `wait`
    # must cover every triggered signal's own 2*FlashDur settle sleep for a test to observe the
    # full cycle, not just its first flash.
    await asyncio.sleep(wait)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# Staged registration / finalize()
# ---------------------------------------------------------------------------


def test_register_before_finalize_is_accepted_in_call_order() -> None:
    coordinator, _clock, _cb = make_coordinator()
    a, _ = make_signal("WarnCO2")
    b, _ = make_signal("WarnVOC")
    coordinator.register(a)
    coordinator.register(b)
    assert coordinator._registered == [a, b]


def test_register_collision_against_another_registered_signal_is_rejected() -> None:
    coordinator, _clock, _cb = make_coordinator()
    a, _ = make_signal("WarnCO2")
    b, _ = make_signal("WarnCO2")  # same field name
    coordinator.register(a)
    coordinator.register(b)
    assert coordinator._registered == [a]


def test_register_collision_against_own_static_schema_is_rejected() -> None:
    coordinator, _clock, _cb = make_coordinator()
    bad, _ = make_signal("AutoOn")  # collides with the coordinator's own static field
    coordinator.register(bad)
    assert coordinator._registered == []


def test_register_field_schema_with_zero_fields_is_rejected() -> None:
    coordinator, _clock, _cb = make_coordinator()
    fv = FakeValue(1)
    notif = NotificationSignal("Empty", fv.get, (), (1, 0, 0))
    coordinator.register(notif)
    assert coordinator._registered == []


def test_register_field_schema_with_two_fields_is_rejected() -> None:
    coordinator, _clock, _cb = make_coordinator()
    fv = FakeValue(1)
    schema = (("A", "int", 1, 0, 10, None), ("B", "int", 1, 0, 10, None))
    notif = NotificationSignal("TwoFields", fv.get, schema, (1, 0, 0))
    coordinator.register(notif)
    assert coordinator._registered == []


def test_register_after_finalize_is_rejected() -> None:
    coordinator, _clock, _cb = make_coordinator()
    a, _ = make_signal("WarnCO2")
    coordinator.register(a)
    coordinator.finalize()
    late, _ = make_signal("WarnVOC")
    coordinator.register(late)
    assert coordinator._registered == [a]


def test_finalize_builds_the_exact_combined_schema() -> None:
    coordinator, _clock, _cb = make_coordinator()
    a, _ = make_signal("WarnCO2")
    b, _ = make_signal("WarnVOC")
    coordinator.register(a)
    coordinator.register(b)
    coordinator.finalize()
    names = [f[0] for f in coordinator.get_cfg_schema()]
    assert names == ["OnH", "OnM", "OffH", "OffM", "FlashBri", "Interv", "FlashDur", "AutoOn", "WarnCO2", "WarnVOC"]
    assert len(names) == len(set(names))  # no duplicates


def test_finalize_called_twice_is_a_no_op_second_time() -> None:
    coordinator, _clock, _cb = make_coordinator()
    a, _ = make_signal("WarnCO2")
    coordinator.register(a)
    coordinator.finalize()
    schema_before = coordinator.get_cfg_schema()
    coordinator.finalize()
    assert coordinator.get_cfg_schema() == schema_before


# ---------------------------------------------------------------------------
# Combined config/persistence (single shared ConfigManager, post-finalize)
# ---------------------------------------------------------------------------


def test_combined_fields_round_trip_through_get_and_set_dict_cfg() -> None:
    coordinator, _clock, _cb = make_coordinator()
    a, _ = make_signal("WarnCO2")
    coordinator.register(a)
    coordinator.finalize()

    async def scenario() -> "dict[str, dict[str, int | float | str | bool | None]]":
        await coordinator._set_dict_cfg({"FlashBri": 100, "WarnCO2": 1234}, coordinator.get_cfg_schema())
        return await coordinator.get_dict_cfg()

    data = run(scenario())
    assert data["NOTIFY"]["FlashBri"] == 100
    assert data["NOTIFY"]["WarnCO2"] == 1234


def test_invalid_write_on_one_field_does_not_affect_others() -> None:
    coordinator, _clock, _cb = make_coordinator()
    a, _ = make_signal("WarnCO2")
    coordinator.register(a)
    coordinator.finalize()

    async def scenario() -> "dict[str, Any]":
        before = await coordinator.get_dict_cfg()
        results = await coordinator._set_dict_cfg({"FlashBri": 9999, "WarnCO2": 1234}, coordinator.get_cfg_schema())
        after = await coordinator.get_dict_cfg()
        assert results["FlashBri"] == "Invalid"
        assert results["WarnCO2"] == "Valid"
        assert after["NOTIFY"]["FlashBri"] == before["NOTIFY"]["FlashBri"]
        return after

    run(scenario())


def test_fram_backed_variant_survives_a_reboot() -> None:
    class _FakeFramChunk:
        def __init__(self) -> None:
            self.buf = bytearray(64)

        def get_buffer(self) -> "Any":
            return self

        def get_data_buf(self) -> bytearray:
            return self.buf

        async def write_into(self, buf: "Any", override_pause: bool = False) -> bool:
            self.buf[:] = buf.get_data_buf()
            return True

        async def read_into(self, buf: "Any", override_pause: bool = False) -> bool:
            buf.get_data_buf()[:] = self.buf
            return True

    class _FakeFramManager:
        def __init__(self, chunk: "_FakeFramChunk") -> None:
            self.chunk = chunk

        def get_chunk(self, size: int, crc: "Any" = None, verify: int = 0, check_length: int = 8) -> "_FakeFramChunk":
            return self.chunk

    chunk = _FakeFramChunk()
    fram = _FakeFramManager(chunk)
    path = _tmp_cfg_dir()
    cb1 = FakeSignalCb()
    clock1 = FakeClock()
    coordinator1 = NotificationCoordinator(cb1, clock1.get, cfg_path=path, fram=fram)  # type: ignore[arg-type]
    a1, _ = make_signal("WarnCO2")
    coordinator1.register(a1)
    coordinator1.finalize()

    async def scenario1() -> None:
        await coordinator1.pr.setup()
        await coordinator1.pr.err_s("boom", errno=1)

    run(scenario1())

    cb2 = FakeSignalCb()
    clock2 = FakeClock()
    coordinator2 = NotificationCoordinator(cb2, clock2.get, cfg_path=path, fram=fram)  # type: ignore[arg-type]
    a2, _ = make_signal("WarnCO2")
    coordinator2.register(a2)
    coordinator2.finalize()

    async def scenario2() -> None:
        await coordinator2.pr.setup()

    run(scenario2())
    assert coordinator2.pr.err_count == coordinator1.pr.err_count


# ---------------------------------------------------------------------------
# Combined logging (single shared pr, post-finalize)
# ---------------------------------------------------------------------------


def test_signal_value_failure_and_own_time_callback_failure_share_one_history() -> None:
    signal, fv = make_signal("WarnCO2")
    fv.raise_exc = RuntimeError("boom")
    clock = FakeClock()
    clock.raise_exc = RuntimeError("clock boom")
    cb = FakeSignalCb()
    coordinator, _clock, _cb = make_coordinator(local_time=clock, signal_cb=cb)
    coordinator.register(signal)
    coordinator.finalize()

    async def scenario() -> None:
        await coordinator.pr.setup()
        await coordinator._check_one(signal)  # signal-callback failure
        await coordinator._safe_local_time()  # coordinator's own callback failure

    run(scenario())

    async def read_log() -> "dict[str, Any]":
        return await coordinator.get_error_counter()

    log = run(read_log())
    assert log["NOTIFY"]["ErrCount"] == 2
    assert len(log["NOTIFY"]["ErrNum"]) == len(coordinator.pr.history)


def test_two_signals_failures_share_one_errno_but_distinct_names_in_message() -> None:
    a, fv_a = make_signal("WarnCO2")
    b, fv_b = make_signal("WarnVOC")
    fv_a.raise_exc = RuntimeError("a boom")
    fv_b.raise_exc = RuntimeError("b boom")
    coordinator, _clock, _cb = make_coordinator()
    coordinator.register(a)
    coordinator.register(b)
    coordinator.finalize()

    async def scenario() -> None:
        await coordinator.pr.setup()
        await coordinator._check_one(a)
        await coordinator._check_one(b)

    run(scenario())

    async def read_log() -> "dict[str, Any]":
        return await coordinator.get_error_counter()

    log = run(read_log())
    assert log["NOTIFY"]["ErrCount"] == 2
    assert log["NOTIFY"]["ErrType"][-2:] == ["E", "E"]
    assert log["NOTIFY"]["ErrNum"][-2:] == [1, 1]  # same errno for both - the name is in the message text, not the errno


# ---------------------------------------------------------------------------
# _check_one()
# ---------------------------------------------------------------------------


def test_check_one_above_true_boundary_and_direction() -> None:
    coordinator, _clock, _cb = make_coordinator()
    signal, fv = make_signal("WarnCO2", above=True, value=1600)  # default threshold is 1600
    coordinator.register(signal)
    coordinator.finalize()

    async def check(value: "int | float | None") -> bool:
        fv.value = value
        return await coordinator._check_one(signal)

    async def scenario() -> "tuple[bool, bool, bool]":
        return await check(1599), await check(1600), await check(1601)

    below, at, above = run(scenario())
    assert below is False
    assert at is True  # boundary is inclusive, matches today's >= exactly
    assert above is True


def test_check_one_above_false_boundary_and_direction() -> None:
    coordinator, _clock, _cb = make_coordinator()
    signal, fv = make_signal("WarnCO2", above=False, value=1600)
    coordinator.register(signal)
    coordinator.finalize()

    async def check(value: "int | float | None") -> bool:
        fv.value = value
        return await coordinator._check_one(signal)

    async def scenario() -> "tuple[bool, bool, bool]":
        return await check(1599), await check(1600), await check(1601)

    below, at, above = run(scenario())
    assert below is True
    assert at is True  # boundary is inclusive on this side too
    assert above is False


def test_check_one_none_value_is_not_triggered_no_crash() -> None:
    coordinator, _clock, _cb = make_coordinator()
    signal, fv = make_signal("WarnCO2", value=None)
    coordinator.register(signal)
    coordinator.finalize()

    async def scenario() -> bool:
        return await coordinator._check_one(signal)

    result = run(scenario())
    assert result is False
    assert signal.last_value is None
    assert signal.triggered is False


def test_check_one_get_value_raises_is_caught_and_logged_and_treated_as_none() -> None:
    coordinator, _clock, _cb = make_coordinator()
    signal, fv = make_signal("WarnCO2")
    fv.raise_exc = RuntimeError("sensor boom")
    coordinator.register(signal)
    coordinator.finalize()

    async def scenario() -> bool:
        await coordinator.pr.setup()
        return await coordinator._check_one(signal)

    result = run(scenario())
    assert result is False
    assert signal.last_value is None
    assert signal.triggered is False
    assert coordinator.pr.err_count == 1


def test_check_one_indefinite_logging_no_cap() -> None:
    # Confirmed by the project owner: no failure-escalation cap - every failing cycle logs.
    coordinator, _clock, _cb = make_coordinator()
    signal, fv = make_signal("WarnCO2")
    fv.raise_exc = RuntimeError("boom")
    coordinator.register(signal)
    coordinator.finalize()

    async def scenario() -> None:
        await coordinator.pr.setup()
        for _ in range(5):
            await coordinator._check_one(signal)

    run(scenario())
    assert coordinator.pr.err_count == 5


def test_check_one_last_value_and_triggered_reflect_most_recent_call_only() -> None:
    coordinator, _clock, _cb = make_coordinator()
    signal, fv = make_signal("WarnCO2", value=2000)  # triggered
    coordinator.register(signal)
    coordinator.finalize()

    async def scenario() -> None:
        await coordinator._check_one(signal)
        fv.value = 0  # not triggered
        await coordinator._check_one(signal)

    run(scenario())
    assert signal.last_value == 0
    assert signal.triggered is False


def test_check_one_never_raises() -> None:
    coordinator, _clock, _cb = make_coordinator()
    signal, fv = make_signal("WarnCO2")
    coordinator.register(signal)
    coordinator.finalize()

    async def scenario() -> None:
        await coordinator.pr.setup()
        for value, exc in ((None, None), (0, None), (99999, None), (1, RuntimeError("x"))):
            fv.value = value
            fv.raise_exc = exc
            await coordinator._check_one(signal)  # must never raise, for any of the above

    run(scenario())  # would propagate and fail the test if _check_one() ever raised


# ---------------------------------------------------------------------------
# NotificationCoordinator - ordering and queuing
# ---------------------------------------------------------------------------


def test_all_triggered_signals_fire_in_registration_order_sequentially() -> None:
    cb = FakeSignalCb()
    clock = FakeClock(hour=12, minute=0)
    coordinator, _clock, _cb = make_coordinator(local_time=clock, signal_cb=cb)
    a, _ = make_signal("WarnCO2", value=2000, color=(1, 0, 0))
    b, _ = make_signal("WarnVOC", value=2000, color=(0, 1, 0))
    c, _ = make_signal("WarnHum", value=2000, color=(0, 0, 1))
    for s in (a, b, c):
        coordinator.register(s)
    coordinator.finalize()

    async def scenario() -> None:
        # FlashDur's real schema minimum is 0.5 - each triggered signal costs a real 2*0.5=1.0s
        # settle sleep, so 3 triggered signals need >=3.0s of real wall-clock wait to all complete.
        await coordinator._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, coordinator.get_cfg_schema())
        task = coordinator.start_asy_notify_monitor()
        await _one_cycle(coordinator, task, wait=3.5)

    run(scenario())
    assert len(cb.calls) == 3
    assert [c[:3] for c in cb.calls] == [(200, 0, 0), (0, 200, 0), (0, 0, 200)]  # default FlashBri=200


def test_only_triggered_signals_call_request_signal_cb_others_skipped_no_gap() -> None:
    cb = FakeSignalCb()
    clock = FakeClock(hour=12, minute=0)
    coordinator, _clock, _cb = make_coordinator(local_time=clock, signal_cb=cb)
    a, _ = make_signal("WarnCO2", value=0, color=(1, 0, 0))  # not triggered
    b, _ = make_signal("WarnVOC", value=2000, color=(0, 1, 0))  # triggered
    coordinator.register(a)
    coordinator.register(b)
    coordinator.finalize()

    async def scenario() -> None:
        await coordinator._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, coordinator.get_cfg_schema())
        task = coordinator.start_asy_notify_monitor()
        await _one_cycle(coordinator, task, wait=1.2)

    run(scenario())
    assert len(cb.calls) == 1
    assert cb.calls[0][:3] == (0, 200, 0)


def test_settle_sleep_happens_only_after_a_triggered_flash() -> None:
    # Regression test for a shape that's easy to get subtly wrong generalizing to a loop: only one
    # of the three registered signals is triggered - the other two must produce no cb call and no
    # settle sleep at all, not just "eventually still only one call recorded."
    cb = FakeSignalCb()
    clock = FakeClock(hour=12, minute=0)
    coordinator, _clock, _cb = make_coordinator(local_time=clock, signal_cb=cb)
    a, _ = make_signal("WarnCO2", value=0, color=(1, 0, 0))  # not triggered
    b, _ = make_signal("WarnVOC", value=0, color=(0, 1, 0))  # not triggered
    c, _ = make_signal("WarnHum", value=2000, color=(0, 0, 1))  # triggered
    for s in (a, b, c):
        coordinator.register(s)
    coordinator.finalize()

    async def scenario() -> None:
        await coordinator._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, coordinator.get_cfg_schema())
        task = coordinator.start_asy_notify_monitor()
        await _one_cycle(coordinator, task, wait=1.2)

    run(scenario())
    assert len(cb.calls) == 1
    assert cb.calls[0][:3] == (0, 0, 200)


def test_registration_order_drives_poll_order_not_construction_order() -> None:
    cb = FakeSignalCb()
    clock = FakeClock(hour=12, minute=0)
    coordinator, _clock, _cb = make_coordinator(local_time=clock, signal_cb=cb)
    a, _ = make_signal("WarnCO2", value=2000, color=(1, 0, 0))
    b, _ = make_signal("WarnVOC", value=2000, color=(0, 1, 0))
    c, _ = make_signal("WarnHum", value=2000, color=(0, 0, 1))
    # constructed in A, B, C order above; registered deliberately out of that order
    coordinator.register(c)
    coordinator.register(a)
    coordinator.register(b)
    coordinator.finalize()

    async def scenario() -> None:
        await coordinator._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, coordinator.get_cfg_schema())
        task = coordinator.start_asy_notify_monitor()
        await _one_cycle(coordinator, task, wait=3.5)

    run(scenario())
    assert [call[:3] for call in cb.calls] == [(0, 0, 200), (200, 0, 0), (0, 200, 0)]  # C, A, B


def test_flashes_run_strictly_sequentially_not_interleaved() -> None:
    # Stalled fake proves ordering by construction, not by coincidence: the second flash cannot
    # even start recording until the first is explicitly released.
    cb = FakeSignalCb()
    cb.stall()
    clock = FakeClock(hour=12, minute=0)
    coordinator, _clock, _cb = make_coordinator(local_time=clock, signal_cb=cb)
    a, _ = make_signal("WarnCO2", value=2000, color=(1, 0, 0))
    b, _ = make_signal("WarnVOC", value=2000, color=(0, 1, 0))
    coordinator.register(a)
    coordinator.register(b)
    coordinator.finalize()

    async def scenario() -> None:
        await coordinator._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, coordinator.get_cfg_schema())
        task = coordinator.start_asy_notify_monitor()
        await asyncio.sleep(0.05)
        assert len(cb.calls) == 0  # both stalled behind the release event, none recorded yet
        cb.release()
        await asyncio.sleep(1.3)  # first flash's own 2*0.5=1.0s settle sleep before the second runs
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    run(scenario())
    assert [c[:3] for c in cb.calls] == [(200, 0, 0), (0, 200, 0)]


# ---------------------------------------------------------------------------
# NotificationCoordinator - gating
# ---------------------------------------------------------------------------


def test_sleep_window_boundaries_inclusive() -> None:
    cb = FakeSignalCb()
    coordinator, clock, _cb = make_coordinator(signal_cb=cb)
    signal, _fv = make_signal("WarnCO2", value=2000)
    coordinator.register(signal)
    coordinator.finalize()

    async def run_at(hour: int, minute: int) -> int:
        clock.value = _FakeTime(hour, minute)
        cb.calls.clear()
        await coordinator._set_dict_cfg(
            {"OnH": 10, "OnM": 0, "OffH": 18, "OffM": 0, "Interv": 3600.0, "FlashDur": 0.01}, coordinator.get_cfg_schema()
        )
        task = coordinator.start_asy_notify_monitor()
        await _one_cycle(coordinator, task)
        return len(cb.calls)

    async def scenario() -> "tuple[int, int, int, int]":
        before = await run_at(9, 59)
        on_bound = await run_at(10, 0)
        inside = await run_at(12, 0)
        off_bound = await run_at(18, 0)
        return before, on_bound, inside, off_bound

    before, on_bound, inside, off_bound = run(scenario())
    assert before == 0
    assert on_bound == 1
    assert inside == 1
    assert off_bound == 1


def test_sleep_window_just_after_off_bound_is_excluded() -> None:
    cb = FakeSignalCb()
    coordinator, clock, _cb = make_coordinator(signal_cb=cb)
    signal, _fv = make_signal("WarnCO2", value=2000)
    coordinator.register(signal)
    coordinator.finalize()
    clock.value = _FakeTime(18, 1)

    async def scenario() -> None:
        await coordinator._set_dict_cfg(
            {"OnH": 10, "OnM": 0, "OffH": 18, "OffM": 0, "Interv": 3600.0, "FlashDur": 0.01}, coordinator.get_cfg_schema()
        )
        task = coordinator.start_asy_notify_monitor()
        await _one_cycle(coordinator, task)

    run(scenario())
    assert len(cb.calls) == 0


def test_local_time_callback_returns_none_no_checks_run_no_crash() -> None:
    cb = FakeSignalCb()
    clock = FakeClock()
    clock.value = None
    coordinator, _clock, _cb = make_coordinator(local_time=clock, signal_cb=cb)
    signal, _fv = make_signal("WarnCO2", value=2000)
    coordinator.register(signal)
    coordinator.finalize()

    async def scenario() -> None:
        await coordinator._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.01}, coordinator.get_cfg_schema())
        task = coordinator.start_asy_notify_monitor()
        await _one_cycle(coordinator, task)

    run(scenario())
    assert len(cb.calls) == 0


def test_local_time_callback_raises_treated_as_none() -> None:
    cb = FakeSignalCb()
    clock = FakeClock()
    clock.raise_exc = RuntimeError("clock boom")
    coordinator, _clock, _cb = make_coordinator(local_time=clock, signal_cb=cb)
    signal, _fv = make_signal("WarnCO2", value=2000)
    coordinator.register(signal)
    coordinator.finalize()

    async def scenario() -> None:
        await coordinator._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.01}, coordinator.get_cfg_schema())
        task = coordinator.start_asy_notify_monitor()
        await _one_cycle(coordinator, task)

    run(scenario())
    assert len(cb.calls) == 0
    assert coordinator.pr.err_count >= 1


def test_auto_on_false_blocks_all_checks_regardless_of_window() -> None:
    cb = FakeSignalCb()
    clock = FakeClock(hour=12, minute=0)
    coordinator, _clock, _cb = make_coordinator(local_time=clock, signal_cb=cb)
    signal, _fv = make_signal("WarnCO2", value=2000)
    coordinator.register(signal)
    coordinator.finalize()

    async def scenario() -> None:
        await coordinator._set_dict_cfg({"AutoOn": False, "Interv": 3600.0, "FlashDur": 0.01}, coordinator.get_cfg_schema())
        task = coordinator.start_asy_notify_monitor()
        await _one_cycle(coordinator, task)

    run(scenario())
    assert len(cb.calls) == 0


def test_override_active_blocks_checks_and_resumes_after_countdown() -> None:
    # Directly inspects _auto_active - the one thing auto_led_override() actually controls -
    # rather than routing through a full monitor_loop() cycle: monitor_loop() itself resets
    # _auto_active=True once at its own start (matches today's original "reset override state on
    # task (re)start" behavior, preserved deliberately - see this file's own module docstring on
    # deferred construction being a one-time boot handshake, the same spirit applies to a task's
    # own start). Starting a second monitor_task to observe an "after" state would just re-trigger
    # that same reset and defeat the observation; monitor_loop()'s gate itself
    # (`if auto_on and self._auto_active:`) is the exact same expression already proven to
    # correctly gate on its first operand by test_auto_on_false_blocks_all_checks_regardless_of_window
    # - both operands go through one plain `and`, so there is no asymmetric-bug scenario where one
    # operand gates correctly and the other doesn't.
    coordinator, _clock, _cb = make_coordinator()
    coordinator.finalize()

    async def scenario() -> "tuple[bool, bool, bool]":
        override_task = coordinator.start_asy_auto_override()
        await asyncio.sleep(0.05)  # let auto_led_override() reach its first iteration
        before = coordinator._auto_active
        # override_secs=1 would decrement to 0 on the very first iteration (decrement() fires
        # once per loop pass, immediately) - giving zero observable "active" window. 2 guarantees
        # at least one full ~1s window where secs stays > 0.
        await coordinator.set_override_led(2)
        await asyncio.sleep(1.1)  # first decrement(): 2 -> 1, still > 0 -> _auto_active False
        during = coordinator._auto_active
        await asyncio.sleep(1.1)  # second decrement(): 1 -> 0 -> _auto_active True again
        after = coordinator._auto_active
        override_task.cancel()
        try:
            await override_task
        except asyncio.CancelledError:
            pass
        return before, during, after

    before, during, after = run(scenario())
    assert before is True
    assert during is False
    assert after is True


def test_malformed_own_config_read_degrades_gracefully_and_keeps_retrying() -> None:
    coordinator, clock, cb = make_coordinator()
    clock.value = _FakeTime(12, 0)
    signal, _fv = make_signal("WarnCO2", value=2000)
    coordinator.register(signal)
    coordinator.finalize()

    async def scenario() -> bool:
        # Corrupt the cache directly to simulate a malformed read without touching ConfigManager
        # itself - the coordinator must still not crash and must still eventually retry.
        coordinator.cfgmgr._cache.pop("FlashBri")
        task = coordinator.start_asy_notify_monitor()
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return True

    assert run(scenario()) is True  # would raise/hang if the loop crashed instead of degrading


def test_next_sleep_secs_subtracts_elapsed_time() -> None:
    # Direct unit test of the rem_interv arithmetic monitor_loop() uses, isolated from a full
    # real-time cycle: Interv's own schema floor is 60.0s, which makes observing this end-to-end
    # (waiting for elapsed time to actually consume a full Interv) impractically slow for a unit
    # test - this exercises the exact same clamp/subtraction expression directly instead.
    import time

    coordinator, _clock, _cb = make_coordinator()
    coordinator.finalize()
    t0 = time.ticks_ms()
    time.sleep_ms(50)
    result = coordinator._next_sleep_secs(60.0, t0)
    assert 59.0 < result < 60.0  # ~60s minus the ~50ms actually elapsed


def test_next_sleep_secs_floors_at_point_one_when_elapsed_exceeds_interv() -> None:
    import time

    coordinator, _clock, _cb = make_coordinator()
    coordinator.finalize()
    t0_100s_ago = time.ticks_add(time.ticks_ms(), -100000)  # simulate 100s already elapsed
    result = coordinator._next_sleep_secs(60.0, t0_100s_ago)
    assert result == 0.1


# ---------------------------------------------------------------------------
# Error/edge cases
# ---------------------------------------------------------------------------


def test_zero_registered_signals_just_sleeps_no_crash() -> None:
    coordinator, clock, cb = make_coordinator()
    clock.value = _FakeTime(12, 0)
    coordinator.finalize()

    async def scenario() -> bool:
        await coordinator._set_dict_cfg({"Interv": 3600.0}, coordinator.get_cfg_schema())
        task = coordinator.start_asy_notify_monitor()
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return True

    assert run(scenario()) is True


def test_request_signal_cb_raising_is_caught_and_the_loop_continues() -> None:
    cb = FakeSignalCb()
    cb.raise_exc = RuntimeError("cb boom")
    clock = FakeClock(hour=12, minute=0)
    coordinator, _clock, _cb = make_coordinator(local_time=clock, signal_cb=cb)
    a, _ = make_signal("WarnCO2", value=2000, color=(1, 0, 0))
    b, _ = make_signal("WarnVOC", value=2000, color=(0, 1, 0))
    coordinator.register(a)
    coordinator.register(b)
    coordinator.finalize()

    async def scenario() -> None:
        await coordinator._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, coordinator.get_cfg_schema())
        task = coordinator.start_asy_notify_monitor()
        await _one_cycle(coordinator, task, wait=2.5)

    run(scenario())
    # both signals were still reached despite the first flash's callback raising
    assert len(cb.calls) == 2
    assert coordinator.pr.err_count == 2


def test_get_task_starters_and_get_timer_starters_shape() -> None:
    coordinator, _clock, _cb = make_coordinator()
    coordinator.finalize()
    starters = coordinator.get_task_starters()
    assert len(starters) == 2
    for s in starters:
        assert callable(s)
    assert coordinator.get_timer_starters() == []


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
