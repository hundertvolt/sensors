"""Manual-test runner: primitives + entry point for every `[MANUAL]` real-hardware test - kept
structurally separate from the automated flash/bench runner so an unattended pass never stalls on
a human. Run via `__main__.py`, never this file directly - see tests_hardware/README.md."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # tests_hardware/, for `import harness`/`import bench_control`/`import http_client`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))  # for the shared summary block

from _summary_block import Summary  # type: ignore[import-not-found]

# A manual step's level comes from its tier: a board on USB alone is L3, the bench's WiFi makes it L4.
_LEVEL_OF_TIER = (("[USB+WiFi]", "L4"), ("[USB]", "L3"))


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
    # Import side effect: registers every manual test with the decorator above. Here rather than
    # at module level, so `--list` stays fast and runner.py takes no hard dependency on each test
    # module's own imports (manual_wifi.py's harness.Board) unless a run needs them.
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

    summary = Summary(runner="run_manual_hardware_tests", unit="manual steps", levels="L3/L4 (manual mode)")
    tests = _REGISTRY if args.only is None else [t for t in _REGISTRY if t.name == args.only]
    if args.only is not None and not tests:
        print(f"no manual test named {args.only!r} - see --list", file=sys.stderr)
        summary.add("failed", f"--only {args.only}", f"no manual test named {args.only}")
        summary.print(2)
        return 2

    exit_code = 0
    for index, t in enumerate(tests):
        name = f"{_level(t.tier)} {t.name}"
        print(f"\n{'=' * 70}\n{t.tier} {t.name}\n{t.description}\n{'=' * 70}")
        try:
            t.fn()
            print(f"--- {t.name}: PASS (human-confirmed) ---")
            summary.add("passed", name)
        except AssertionError as exc:
            print(f"--- {t.name}: FAIL - {exc} ---")
            summary.add("failed", name, str(exc))
            exit_code = 1
        except KeyboardInterrupt:
            print(f"--- {t.name}: ABORTED by operator ---")
            summary.add("failed", name, "aborted by operator")
            for rest in tests[index + 1 :]:
                summary.add("skipped", f"{_level(rest.tier)} {rest.name}", "not run (run aborted)")
            summary.print(130)
            return 130
        except Exception as exc:  # any other error fails this step, named, and the run goes on
            print(f"--- {t.name}: FAIL - {type(exc).__name__}: {exc} ---")
            summary.add("failed", name, f"{type(exc).__name__}: {exc}")
            exit_code = 1

    summary.print(exit_code)
    return exit_code


def _level(tier: str) -> str:
    return next((level for prefix, level in _LEVEL_OF_TIER if tier.startswith(prefix)), f"level unknown ({tier})")


# Deliberately no `if __name__ == "__main__":` block here - running this file directly causes a
# silent no-op (see __main__.py). Use `uv run python tests_hardware/manual/__main__.py` instead.
