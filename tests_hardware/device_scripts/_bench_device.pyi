# Type-check-only API of the bench device's generated module, the module a device script's one marked
# `import _bench_device as device` line is rendered to (one template generates it for every device). Only the
# names the scripts in this directory call are declared.

from machine import WDT

from asy_base_classes import SetupFct, TaskStarter, TimerStarter
from asy_fram_manager import FRAMManager
from asy_sgp40_driver import SGP40_Reader
from asy_system_service import SystemService
from asy_webserver_service import WebserverService

fram: FRAMManager | None
sgp40: SGP40_Reader | None
sysfunct: SystemService | None
webserver: WebserverService | None

def _collect_setups() -> list[SetupFct]: ...
def _collect_task_names() -> list[str]: ...
def _collect_task_starters() -> list[TaskStarter]: ...
def _collect_timer_starters() -> list[TimerStarter]: ...
def _collect_trigger_starters() -> list[TimerStarter]: ...
async def build_system(*, watchdog: WDT, cfg_path: str = ..., debug: int | None = ..., web_host: str = ..., web_port: int = ...) -> None: ...
async def main(*, watchdog: WDT, cfg_path: str = ..., debug: int | None = ..., web_host: str = ..., web_port: int = ...) -> None: ...
