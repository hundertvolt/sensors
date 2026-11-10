"""The PC tiers' asyncio exception handler: the product's PrintLog report at level 1, so every unretrieved task
exception prints and one that died of an exhausted heap still reaches the memory gates (SPECIFICATION.md Part I.4(e)).
Call `install()` first in any entry point that runs the firmware; `SystemService.start_tasks()` then keeps it."""

import asyncio

from asy_print_log import PrintLog

MARKER = "UNRETRIEVED TASK EXCEPTION:"  # never a memory gate's word: only the printed exception may carry one
report_unretrieved = PrintLog(level=1, name=MARKER).report_unretrieved  # level 1 prints errors, as the device scripts do


def install() -> None:
    asyncio.get_event_loop().set_exception_handler(report_unretrieved)
