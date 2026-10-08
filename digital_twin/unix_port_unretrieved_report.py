"""The PC tiers' asyncio exception handler: prints every unretrieved task exception at every DebugLevel, so a task that died of an exhausted heap still reaches the memory gates (SPECIFICATION.md Part I.4(e)); the firmware's own report stays silent at level 0.
Call `install()` first in any entry point that runs the firmware - tests/microtest.py's run() and every twin launcher; `SystemService.start_tasks()` then keeps it rather than installing its own.
Same allocation-free, never-raising body as `PrintLog.report_unretrieved()` (SPECIFICATION.md Part F.1); only the level gate differs."""

import asyncio
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asyncio.events import _Context  # asyncio's handler context, dict[str, Any] in the stub

MARKER = "UNRETRIEVED TASK EXCEPTION:"  # never a memory gate's word: only the printed exception may carry one


def install() -> None:
    asyncio.get_event_loop().set_exception_handler(report_unretrieved)


def report_unretrieved(_loop: object, context: "_Context") -> None:
    # Fixed-argument print() and print_exception() take no heap; nothing escapes into the loop, and the finally
    # releases the dead task and exception asyncio's own context dict would otherwise keep.
    try:
        try:
            print(MARKER, context["message"])
            sys.print_exception(context["exception"])
        finally:
            context["exception"] = None
            context["future"] = None
    except Exception:  # an escape would end asyncio.run()
        pass
