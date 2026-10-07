# CI's type check failed on U10; the local passes before 08:28 are unexplained

CI's `lint-and-typecheck` on 41b47f1 failed the main mypy pass: `tests/test_asy_udp_socket.py:5`
`from asyncio import core as asyncio_core` - the MicroPython stubs carry no `asyncio.core` (a private module).
Lane B added the import (c7a9727); the test reads the private task queue. Fix: the
`import asyncio.core as ...  # type: ignore[import-not-found]` form `digital_twin/unix_port_poll_prewarm.py` already
uses, with a one-line reason; 64/64 on the Unix port, all three mypy passes clean with a cold cache.

Open: the same tree passed locally four times (the gate on 798cc44 at about 07:17 in wt-u8, and three runs in a fresh
worktree at 41b47f1 between 08:27 and 08:28, one under Python 3.12); every run from about 08:29 on, in fresh and old
worktrees, cold cache or warm, fails exactly as CI did. Same mypy (2.4.0), same stub versions (rp2 1.29.0.post1,
stdlib 1.29.0.post2), no `asyncio/core*` on any search path found. The earlier passes are kept here with the failures;
the cause is open finding OF-24.
