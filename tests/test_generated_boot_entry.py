"""Every generated boot entry is executed at L1 (each generated module and its entry runs in at least one tier): it arms
the watchdog, sets the shipped GC threshold before main(), records a console interrupt and always leaves a fresh loop;
the no-autostart entry prints the manual start line and starts nothing. main() and the reset record are stubs."""

import asyncio
import gc
import sys

import machine
from _generated_tree import devices, require_fresh
from _src_const import py_value

_GENERATED = "build/generated_src/"
_RR_INTERRUPTED = "stub interrupted"  # the stub's own marker: only identity with what the entry passes matters


class _Stub:
    # Stands in for the device module and asy_system_service: records main()'s watchdog, the threshold at its call and
    # each reset record; main() then returns or raises `raises`.
    def __init__(self, raises: "BaseException | None" = None) -> None:
        self.RR_INTERRUPTED = _RR_INTERRUPTED  # the entry imports it by this name
        self.calls: list[tuple[object, int]] = []
        self.records: list[object] = []
        self._raises = raises

    async def main(self, *, watchdog: object, **_kw: object) -> None:
        self.calls.append((watchdog, gc.threshold()))
        if self._raises is not None:
            raise self._raises

    def write_reset_record(self, purpose: object) -> None:
        self.records.append(purpose)


class _MicropythonStub:
    # The entry's `micropython`: records the emergency buffer it asks for.
    def __init__(self) -> None:
        self.buffers: list[int] = []

    def alloc_emergency_exception_buf(self, size: int) -> None:
        self.buffers.append(size)


def _boot(device: str, entry: str, stub: _Stub) -> "tuple[_MicropythonStub, list[int], list[tuple[object, ...]], BaseException | None]":
    # Executes one entry from this synchronous scope with the stubs in sys.modules; everything it changes comes back.
    with open(_GENERATED + entry) as f:
        code = compile(f.read(), _GENERATED + entry, "exec")
    names = ("sensortask_" + device, "asy_system_service", "micropython")
    saved_modules = {name: sys.modules.get(name) for name in names}
    saved_path, real_new_loop = sys.path[:], asyncio.new_event_loop
    micro, loops, printed = _MicropythonStub(), [], []

    def new_event_loop() -> None:
        loops.append(1)  # recorded; the process keeps its real loop

    sys.modules.update({names[0]: stub, names[1]: stub, names[2]: micro})  # type: ignore[dict-item]  # stand-ins for the modules
    asyncio.new_event_loop = new_event_loop  # type: ignore[assignment]  # the entry's finally, recorded
    raised = None
    try:
        exec(code, {"__name__": "__main__", "print": lambda *args: printed.append(args)})  # noqa: S102 - the generated entry itself
    except BaseException as e:  # what escapes the entry is the observation
        raised = e
    finally:
        asyncio.new_event_loop = real_new_loop
        sys.path[:] = saved_path
        for name, module in saved_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
    return micro, loops, printed, raised


def _shipped_threshold(device: str) -> int:
    # The threshold the entry itself sets: what main() must already run under.
    with open(_GENERATED + "sensortask_" + device + "_main.py") as f:
        lines = [line for line in f if line.startswith("gc.threshold(")]
    assert len(lines) == 1, lines
    return int(lines[0][len("gc.threshold(") : lines[0].index(")")])


def test_each_entry_arms_the_watchdog_and_sets_the_threshold_before_main() -> None:
    require_fresh()
    timeout = py_value("buildgen/validate.py", "_WDT_TIMEOUT_MS")
    for device in devices():
        stub = _Stub()
        micro, loops, _printed, raised = _boot(device, "sensortask_" + device + "_main.py", stub)
        assert raised is None, (device, raised)
        assert len(stub.calls) == 1, device
        watchdog, threshold = stub.calls[0]
        assert isinstance(watchdog, machine.WDT) and watchdog.timeout == timeout, (device, watchdog)
        assert threshold == _shipped_threshold(device) > 0, (device, threshold)
        assert micro.buffers == [100], device  # the entry ran past its emergency buffer
        assert loops == [1], device  # the finally left a fresh loop
        assert stub.records == [], device


def test_a_raising_main_propagates_and_the_finally_still_runs() -> None:
    require_fresh()
    for device in devices():
        stub = _Stub(RuntimeError("stub"))
        _micro, loops, _printed, raised = _boot(device, "sensortask_" + device + "_main.py", stub)
        assert isinstance(raised, RuntimeError) and raised.args == ("stub",), (device, raised)
        assert loops == [1], device
        assert stub.records == [], device  # only an interrupt is recorded


def test_a_console_interrupt_is_recorded_before_it_propagates() -> None:
    require_fresh()
    for device in devices():
        stub = _Stub(KeyboardInterrupt())
        _micro, loops, _printed, raised = _boot(device, "sensortask_" + device + "_main.py", stub)
        assert isinstance(raised, KeyboardInterrupt), (device, raised)
        assert stub.records == [_RR_INTERRUPTED], device
        assert loops == [1], device


def test_the_no_autostart_entry_prints_the_start_line_and_starts_nothing() -> None:
    require_fresh()
    timeout = py_value("buildgen/validate.py", "_WDT_TIMEOUT_MS")
    for device in devices():
        stub = _Stub()
        micro, loops, printed, raised = _boot(device, "sensortask_" + device + "_main_noautostart.py", stub)
        assert raised is None, (device, raised)
        assert printed == [(f"from machine import WDT; asyncio.run(main(watchdog=WDT(timeout={timeout})))",)], (device, printed)
        assert stub.calls == [] and stub.records == [] and loops == [], device
        assert micro.buffers == [100], device


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
