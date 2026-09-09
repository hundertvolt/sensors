"""Manual-test runner: primitives + entry point for every `[MANUAL]` real-hardware test - kept
structurally separate from the automated flash/bench runner so an unattended pass never stalls on
a human. Run via `__main__.py`, never this file directly - see tests_hardware/README.md."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # tests_hardware/, for `import harness`/`import bench_control`/`import http_client`


def print_instruction(text: str) -> None:
    print(f"\n>>> {text}")


def state_expected_outcome(text: str) -> None:
    print(f"    Expect: {text}")


def confirm(prompt: str = "Press Enter once done") -> None:
    input(f"    {prompt}... ")


def confirm_pass(prompt: str = "Did it match the expected outcome above? [y/N]") -> None:
    """For the tests that end in a human visual/instrument judgment call rather than a script-only
    assertion - a real y/n answer, not Ctrl-C (which aborts the *entire* run, per main()'s own
    handling, not just this one test)."""
    answer = input(f"    {prompt} ").strip().lower()
    if answer not in ("y", "yes"):
        raise AssertionError("operator reported this did not match the expected outcome")


def countdown(seconds: int, message: str) -> None:
    """For the genuine power-cycle cases where the console itself goes away mid-step - a bare
    countdown, not a confirm() prompt, since nothing is listening to press Enter on."""
    print(f"    {message} ({seconds}s)")
    for remaining in range(seconds, 0, -1):
        print(f"    ...{remaining}s", end="\r")
        time.sleep(1)
    print("    ...0s - continuing.       ")


class ManualTest(NamedTuple):
    name: str
    description: str
    tier: str  # "[USB]" or "[USB+WiFi]"
    fn: Callable[[], None]


_REGISTRY: list[ManualTest] = []


def register(name: str, description: str, tier: str) -> Callable[[Callable[[], None]], Callable[[], None]]:
    def _decorator(fn: Callable[[], None]) -> Callable[[], None]:
        _REGISTRY.append(ManualTest(name, description, tier, fn))
        return fn

    return _decorator


def main() -> int:
    # Import side effect: registers every manual test with the decorator above. Done here, not at
    # module level, so `--list` stays fast and `runner.py` itself has no hard dependency on every
    # individual test module's own imports (e.g. manual_wifi.py's harness.Board) unless a run
    # actually needs them.
    import manual_bus_electrical  # noqa: F401
    import manual_persistence  # noqa: F401
    import manual_sensor_accuracy  # noqa: F401
    import manual_toolchain  # noqa: F401
    import manual_wifi  # noqa: F401

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="List every registered manual test and exit")
    parser.add_argument("--only", help="Run only the named test (see --list)")
    args = parser.parse_args()

    if args.list:
        for t in _REGISTRY:
            print(f"{t.tier} {t.name}: {t.description}")
        return 0

    tests = _REGISTRY if args.only is None else [t for t in _REGISTRY if t.name == args.only]
    if args.only is not None and not tests:
        print(f"no manual test named {args.only!r} - see --list", file=sys.stderr)
        return 2

    failures = []
    for t in tests:
        print(f"\n{'=' * 70}\n{t.tier} {t.name}\n{t.description}\n{'=' * 70}")
        try:
            t.fn()
            print(f"--- {t.name}: PASS (human-confirmed) ---")
        except AssertionError as exc:
            print(f"--- {t.name}: FAIL - {exc} ---")
            failures.append(t.name)
        except KeyboardInterrupt:
            print(f"--- {t.name}: ABORTED by operator ---")
            return 130

    if failures:
        print(f"\n{len(failures)}/{len(tests)} manual test(s) failed: {', '.join(failures)}")
        return 1
    print(f"\nAll {len(tests)} manual test(s) passed.")
    return 0


# Deliberately no `if __name__ == "__main__":` block here - running this file directly causes a
# silent no-op (see __main__.py). Use `uv run python tests_hardware/manual/__main__.py` instead.
