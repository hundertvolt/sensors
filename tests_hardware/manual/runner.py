"""Manual execution mode of L3/L4: primitives and the entry point for every `[MANUAL]` test, kept apart from the
automated runners so an unattended pass never waits on a human; run through `__main__.py` (tests_hardware/README.md)."""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # tests_hardware/, for `import harness`/`import bench_control`/`import http_client`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))  # for the shared summary block

import http_client
from _summary_block import Summary  # type: ignore[import-not-found]

if TYPE_CHECKING:
    from http_client import JSONObject

# A manual step's level comes from its tier: a board on USB alone is L3, the bench's WiFi makes it L4.
_LEVEL_OF_TIER = (("[USB+WiFi]", "L4"), ("[USB]", "L3"))
_NO_JUDGMENT = "no pass/fail judgment recorded"
# @tunable l4.manual_rest_timeout_s = 10.0
_REST_TIMEOUT_S = 10.0


class ManualTest(NamedTuple):
    name: str
    description: str
    tier: str  # "[USB]" or "[USB+WiFi]"
    fn: "Callable[[], None]"


_REGISTRY: list[ManualTest] = []
_judgments = [0]  # the running test's verdicts: an operator's y/n, or a scripted assertion it reached
_dut = [""]  # the DUT's address on the bench network: --dut-ip, else asked once


def _level(tier: str) -> str:
    return next((level for prefix, level in _LEVEL_OF_TIER if tier.startswith(prefix)), f"level unknown ({tier})")


def _run_one(t: ManualTest, summary: "Summary") -> bool:
    # One test: PASS only on a verdict; a return with none, an assertion or any other error fails it, named.
    name = f"{_level(t.tier)} {t.name}"
    print(f"\n{'=' * 70}\n{t.tier} {t.name}\n{t.description}\n{'=' * 70}")
    _judgments[0] = 0
    try:
        t.fn()
    except AssertionError as exc:
        print(f"--- {t.name}: FAIL - {exc} ---")
        summary.add("failed", name, str(exc))
        return False
    except Exception as exc:  # any other error fails this step, named, and the run goes on
        print(f"--- {t.name}: FAIL - {type(exc).__name__}: {exc} ---")
        summary.add("failed", name, f"{type(exc).__name__}: {exc}")
        return False
    if not _judgments[0]:
        print(f"--- {t.name}: FAIL - {_NO_JUDGMENT} ---")
        summary.add("failed", name, _NO_JUDGMENT)
        return False
    print(f"--- {t.name}: PASS (operator judged) ---")
    summary.add("passed", name)
    return True


def confirm(prompt: str = "Press Enter once done") -> None:
    # An instruction's acknowledgement only: Enter is never a verdict.
    input(f"    {prompt}... ")


def confirm_pass(prompt: str = "Did it match the expected outcome above? [y/N]") -> None:
    # The operator's verdict on what they observed: anything but y fails the test. Ctrl-C aborts the whole run (main()).
    _judgments[0] += 1
    answer = input(f"    {prompt} ").strip().lower()
    if answer not in ("y", "yes"):
        raise AssertionError("operator reported this did not match the expected outcome")


def countdown(seconds: int, message: str) -> None:
    # For the power-cycle cases where the console itself goes away mid-step: nothing listens for Enter there.
    print(f"    {message} ({seconds}s)")
    for remaining in range(seconds, 0, -1):
        print(f"    ...{remaining}s", end="\r")
        time.sleep(1)
    print("    ...0s - continuing.       ")


def dut_ip() -> str:
    if not _dut[0]:
        _dut[0] = input("    The DUT's IP (tests_hardware/README.md says how to find it without disturbing the running system): ").strip()
    return _dut[0]


def main() -> int:
    # Registration happens in __main__.py, which imports every manual module before calling this.
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="List every registered manual test and exit")
    parser.add_argument("--only", help="Run only the named test (see --list)")
    parser.add_argument("--dut-ip", default="", help="The DUT's address on the bench network (asked once when a test needs it)")
    args = parser.parse_args()
    _dut[0] = args.dut_ip
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
        try:
            if not _run_one(t, summary):
                exit_code = 1
        except KeyboardInterrupt:
            print(f"--- {t.name}: ABORTED by operator ---")
            summary.add("failed", f"{_level(t.tier)} {t.name}", "aborted by operator")
            for rest in tests[index + 1 :]:
                summary.add("skipped", f"{_level(rest.tier)} {rest.name}", "not run (run aborted)")
            summary.print(130)
            return 130
    summary.print(exit_code)
    return exit_code


def observe(prompt: str) -> str:
    # A free-text observation: the step's verdict only when the operator wrote something, never on Enter alone.
    text = input(f"    {prompt} ").strip()
    if text:
        _judgments[0] += 1
    return text


def print_instruction(text: str) -> None:
    print(f"\n>>> {text}")


def put_by_hand(path: str, body: "JSONObject") -> str:
    # A write the operator sends and owns, stated before it is spent; the step reads the answer word they report.
    print(f"\n>>> Send PUT {path} {json.dumps(body)} to {dut_ip()} now (curl, or the website).")
    return input("    Enter the result word it answered (Valid / Unchanged / Invalid / Failed): ").strip()


def record_assertion() -> None:
    # A module helper's scripted check reached its assert: that assert is the test's verdict.
    _judgments[0] += 1


def register(name: str, description: str, tier: str) -> "Callable[[Callable[[], None]], Callable[[], None]]":
    def _decorator(fn: "Callable[[], None]") -> "Callable[[], None]":
        _REGISTRY.append(ManualTest(name, description, tier, fn))
        return fn

    return _decorator


def rest_get(path: str) -> "JSONObject":
    # One read of the DUT over REST, its JSON body returned; any other status fails the step naming the answer.
    answer = http_client.fetch(dut_ip(), 80, "GET", path, timeout_s=_REST_TIMEOUT_S)
    assert answer.status_code == 200, f"GET {path} answered {answer.status_code}: {answer.body!r}"
    return answer.json()


def state_expected_outcome(text: str) -> None:
    print(f"    Expect: {text}")
