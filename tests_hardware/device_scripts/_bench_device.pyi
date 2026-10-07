# Type-check-only API of the bench device's generated module, the module a device script's one marked
# `import _bench_device as device` line is rendered to (one template generates it for every device). Only the
# names the scripts in this directory call are declared.

from asy_base_classes import TaskStarter, TimerStarter
from asy_sgp40_driver import SGP40_Reader
from asy_system_service import SystemService

sysfunct: SystemService | None
sgp40: SGP40_Reader | None

async def build_system(*, cfg_path: str = ..., debug: int | None = ..., web_host: str = ..., web_port: int = ...) -> None: ...
def _collect_task_starters() -> list[TaskStarter]: ...
def _collect_timer_starters() -> list[TimerStarter]: ...
def _collect_trigger_starters() -> list[TimerStarter]: ...
