"""The firmware's task names for a hand-built starter list: `<logger name>.<starter name>`, the form the generated
_collect_task_names() gives each starter (buildgen/codegen.py), so a test names its tasks as main() does."""

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Protocol

    from asy_base_classes import TaskStarter

    class _Named(Protocol):
        @property
        def name(self) -> str: ...

    class _TaskOwner(Protocol):
        def get_task_starters(self) -> "list[TaskStarter]": ...

        @property
        def pr(self) -> _Named: ...


def task_name(owner: "_TaskOwner", starter: "TaskStarter") -> str:
    return f"{owner.pr.name}.{starter.__name__}"


def task_names_of(*owners: "_TaskOwner") -> "list[str]":
    # Each owner's starters in get_task_starters() order: _collect_task_names()'s list for these modules.
    return [task_name(owner, starter) for owner in owners for starter in owner.get_task_starters()]
