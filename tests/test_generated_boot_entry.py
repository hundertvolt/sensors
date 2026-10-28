"""Every generated boot entry is executed at L1 (each generated module and its entry runs in at least one tier): it
arms the watchdog, sets the shipped GC threshold before main(), records a console interrupt and any other exception
ending the loop, and always leaves a fresh loop; the no-autostart entry prints the start line. main() is a stub."""

import asyncio
import gc
import sys

import machine
from _generated_tree import devices, require_fresh
from _src_const import py_value

_GENERATED = "build/generated_src/"
_RR_INTERRUPTED = "stub interrupted"  # the stub's own marker: only identity with what the entry passes matters
_LOOP_ENDED = "stub loop ended"  # what the stub's record_loop_end() records


class _Stub:
    # Stands in for the device module and asy_system_service: records main()'s watchdog, the threshold at its call and
    # each reset record; main() then returns or raises `raises`.
    def __init__(self, raises: "BaseException | None" = None) -> None:
        self.RR_INTERRUPTED = _RR_INTERRUPTED  # the entry imports it by this name
        self.calls: list[tuple[object, int]] = []
        self.records: list[object] = []
        self.consoles: list[tuple[str, object, object]] = []
        self.reported: list[BaseException] = []
        self._raises = raises

    async def main(self, *, watchdog: object, **_kw: object) -> None:
        self.calls.append((watchdog, gc.threshold()))
        if self._raises is not None:
            raise self._raises

    def console(self, name: str, what: object, err: object = None) -> None:
        self.consoles.append((name, what, err))

    def report_if_fatal(self, e: BaseException) -> None:
        self.reported.append(e)

    def record_loop_end(self) -> None:
        self.records.append(_LOOP_ENDED)

    def write_reset_record(self, purpose: object) -> None:
        self.records.append(purpose)


class _InterruptingStub(_Stub):
    # main() is interrupted by an interrupt the test did not plant: the per-file timeout's SIGINT landing in the entry.
    async def main(self, *, watchdog: object, **_kw: object) -> None:
        raise KeyboardInterrupt


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
    names = ("sensortask_" + device, "asy_system_service", "asy_print_log", "micropython")
    saved_modules = {name: sys.modules.get(name) for name in names}
    saved_path, real_new_loop = sys.path[:], asyncio.new_event_loop
    micro, loops, printed = _MicropythonStub(), [], []

    def new_event_loop() -> None:
        loops.append(1)  # recorded; the process keeps its real loop

    sys.modules.update({names[0]: stub, names[1]: stub, names[2]: stub, names[3]: micro})  # type: ignore[dict-item]  # stand-ins for the modules
    asyncio.new_event_loop = new_event_loop  # type: ignore[assignment]  # the entry's finally, recorded
    raised = None
    try:
        exec(code, {"__name__": "__main__", "print": lambda *args: printed.append(args)})
    except BaseException as e:  # what escapes the entry is the observation
        if isinstance(e, KeyboardInterrupt) and e is not stub._raises:
            raise  # an interrupt the stub did not plant is the per-file timeout's: it ends the run
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


def test_any_other_exception_ending_the_loop_is_recorded_printed_and_ends_the_entry() -> None:
    # Not re-raised: rp2 soft-resets on a SystemExit leaving main.py (shared/runtime/pyexec.c:166-185, v1.29.0).
    require_fresh()
    for device in devices():
        for planted in (RuntimeError("stub"), SystemExit(3), GeneratorExit()):
            stub = _Stub(planted)
            _micro, loops, printed, raised = _boot(device, "sensortask_" + device + "_main.py", stub)
            assert raised is None, (device, planted, raised)
            assert stub.records == [_LOOP_ENDED], (device, planted, stub.records)
            assert stub.reported == [planted], (device, stub.reported)  # the stack-overflow check first, as every broad handler
            assert stub.consoles == [("SYSTEM", "event loop ended with an exception:", None)] and printed == [], (device, stub.consoles)
            assert loops == [1], device


def test_a_console_interrupt_is_recorded_before_it_propagates() -> None:
    require_fresh()
    for device in devices():
        stub = _Stub(KeyboardInterrupt())
        _micro, loops, _printed, raised = _boot(device, "sensortask_" + device + "_main.py", stub)
        assert isinstance(raised, KeyboardInterrupt), (device, raised)
        assert stub.records == [_RR_INTERRUPTED], device  # its own code, never the loop-ended one
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


def test_an_interrupt_the_stub_did_not_plant_ends_the_run() -> None:
    # Only the stub's own raise is the observation; any other interrupt is the per-file timeout's and ends the file.
    require_fresh()
    device = devices()[0]
    try:
        observed = _boot(device, "sensortask_" + device + "_main.py", _InterruptingStub())
    except KeyboardInterrupt:
        return
    raise AssertionError(f"_boot() answered an interrupt it did not plant: {observed[3]!r}")


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
