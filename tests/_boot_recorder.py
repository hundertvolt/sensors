"""Records a generated device's boot from outside, in run order: each module's construction and setup unit,
SystemService's phase marks and feeds, and every step main() awaits. Entering supervise_tasks() stops the run;
restore() undoes every wrap. It imports no fake, so every test tier can use it."""

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Protocol

    from asy_system_service import SystemService

    class _SetUp(Protocol):
        async def setup(self) -> bool: ...

# The steps main() awaits that SystemService owns; build_system() is the module's, ntp_force_sync() NTPClient's.
_SERVICE_STEPS = ("run_setups", "start_tasks", "start_timers")


class _StopError(Exception):
    # Raised where main() enters supervise_tasks(), which never returns: the recorded boot ends there.
    pass


class BootRecorder:
    def __init__(self, module: "ModuleType") -> None:
        # The module must have been built once in this process: its globals name the classes whose constructions
        # and setup units are recorded. Each entry is (kind, name); the names resolve when entries() is read.
        self._module = module
        self._entries: list[tuple[str, object]] = []
        self._saved: list[tuple[object, str, object, bool]] = []  # (owner, attribute, original, owned by the owner)
        self._phases = {getattr(module, name): name for name in dir(module) if name.startswith("BOOT_")}
        classes: list[type[_SetUp]] = []
        for name in dir(module):
            obj = getattr(module, name)
            if not name.startswith("_") and not isinstance(obj, type) and hasattr(obj, "setup") and hasattr(obj, "get_loggers") and type(obj) not in classes:
                classes.append(type(obj))
        if not classes:
            raise ValueError(f"{module.__name__} holds no constructed module yet: build it once before recording")
        service = module.SystemService
        for step in _SERVICE_STEPS:
            self._wrap_step(service, step)
        self._wrap_step(module.NTPClient, "ntp_force_sync")
        self._wrap_step(module, "build_system")
        self._wrap_service(service)
        for cls in classes:
            self._wrap_module_class(cls)

    def _record(self, kind: str, ref: object) -> None:
        self._entries.append((kind, ref))

    def _replace(self, owner: object, attribute: str, wrapper: object) -> None:
        owned = not isinstance(owner, type) or attribute in owner.__dict__
        self._saved.append((owner, attribute, getattr(owner, attribute), owned))
        setattr(owner, attribute, wrapper)

    def _wrap_module_class(self, cls: "type[_SetUp]") -> None:
        # Both originals are read before either wrap, so neither wrapper ever calls the other.
        real_init = cls.__init__
        real_setup = cls.setup

        def init(obj: "_SetUp", *args: object, **kwargs: object) -> None:
            self._record("construct", obj)
            real_init(obj, *args, **kwargs)

        async def setup(obj: "_SetUp") -> bool:
            self._record("setup", obj)
            return await real_setup(obj)

        self._replace(cls, "__init__", init)
        self._replace(cls, "setup", setup)

    def _wrap_service(self, service: "type[SystemService]") -> None:
        real_phase = service.boot_phase
        real_feed = service.feed_watchdog

        def boot_phase(obj: "SystemService", phase: int) -> None:
            self._record("phase", self._phases.get(phase, str(phase)))
            real_phase(obj, phase)

        def feed_watchdog(obj: "SystemService") -> None:
            self._record("feed", "")
            real_feed(obj)

        async def supervise_tasks(obj: "SystemService") -> None:
            self._record("call", "supervise_tasks")
            raise _StopError(f"{obj!r} entered supervise_tasks()")

        self._replace(service, "boot_phase", boot_phase)
        self._replace(service, "feed_watchdog", feed_watchdog)
        self._replace(service, "supervise_tasks", supervise_tasks)

    def _wrap_step(self, owner: object, attribute: str) -> None:
        real = getattr(owner, attribute)

        async def step(*args: object, **kwargs: object) -> object:
            self._record("call", attribute)
            result = await real(*args, **kwargs)
            self._record("return", attribute)
            return result

        self._replace(owner, attribute, step)

    def entries(self) -> "list[tuple[str, str]]":
        # Each recorded object named by the module global that holds it after the boot; an object no global holds
        # keeps its repr, so a construction the module never kept shows up rather than vanishing.
        names = {id(getattr(self._module, name)): name for name in dir(self._module) if not name.startswith("_")}
        return [(kind, ref if isinstance(ref, str) else names.get(id(ref), repr(ref))) for kind, ref in self._entries]

    def restore(self) -> None:
        for owner, attribute, original, owned in reversed(self._saved):
            if owned:
                setattr(owner, attribute, original)
            else:
                delattr(owner, attribute)
        self._saved = []

    def stopped_by(self, exc: BaseException) -> bool:
        return isinstance(exc, _StopError)
