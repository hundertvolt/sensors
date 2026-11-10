"""Included into device scripts at render: the product's own unretrieved-task report at the error level, so it prints
whatever level the board's config holds; installed before main(), as the firmware keeps a handler already set."""

import asyncio

from asy_print_log import PrintLog

_REPORT = PrintLog(level=1, name="UNRETRIEVED TASK EXCEPTION:")


def report_unretrieved() -> None:
    asyncio.get_event_loop().set_exception_handler(_REPORT.report_unretrieved)
