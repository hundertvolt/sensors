# U30 L0: the 28 "already landed" steps, checked at 4ac9a7f (lead, 2026-10-20, during U29's gate; re-run on <BASE>)

Every step the planner listed as landed was located by a distinctive anchor of its change text (not a line number):
2, 19b (tests/_webserver_concurrency_scenarios.py absent; scripts/_digital_twin_scenarios.py present), 22, 23, 24
(`_CMD_ECHO` echo path on `PieceBuffer`s; `_memory_churn_loop`'s `except MemoryError` keeps `held = []`, no collect),
25 (`# @include _shared/heap_probe.py`), 26, 27, 28, 29 (`grep_guard`, the checker call), 68, 79 (the header, word for
word), 87, 100 (`FastAsyncSleep`), 111 and 120 (in place; U29 refined both on the owner's 2026-10-20 timeout rule: the
`max_attempts` comment and placement, and the pytest tier's attempts loop: later owner decision, recorded, no U30 work),
113, 125, 126, 127, 128 (the header and the argparse note), 129 (`_STACK_EXHAUSTED_MESSAGE`, the twin-only knob
comment), 132, 133 and 134 (both files absent), 135, 137 (`### Faults, hangs and modes`, twin README), 139.

One part not landed: step 139's end form compares the twin's stack fault with `asy_print_log._STACK_EXHAUSTED`, which
C1 creates; today the launch test compares with `_recursion_message()`. Assigned to C1 (files_C1_extra.txt), with C1's
L1 pinning the constant against the interpreter's own message.
