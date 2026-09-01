"""Real entry point for the manual-test runner - run this file, never runner.py directly.

Why this thin wrapper exists (a real bug found and fixed during this session, not a stylistic
preference): running `python3 tests_hardware/manual/runner.py` directly makes Python load that file
as the `__main__` module, while every test_*.py file's own `from runner import register, ...`
imports a SEPARATE module instance literally named `runner` (found on sys.path) - two distinct
module objects, each with its own separate `_REGISTRY` list. Decorators in the test files populate
the `runner`-named instance's registry; `main()` running as `__main__` reads its own, different,
permanently-empty one. The result was a silent no-op: exit 0, zero output, `--list` showing nothing,
no exception anywhere to point at the cause. Confirmed directly by tracing both module instances'
`id()`/`_REGISTRY` in a running interpreter, not guessed. This file sidesteps the whole problem by
always importing runner.py as a plain module (never running it as `__main__` itself), so there is
only ever one `runner` module instance for both the decorators and main() to share."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import runner  # noqa: E402

if __name__ == "__main__":
    sys.exit(runner.main())
