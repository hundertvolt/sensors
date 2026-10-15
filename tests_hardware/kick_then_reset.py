"""The bench's ad-hoc reset: kicks every station off the bench AP, then hard-resets the board, so a board fallen back to
hotspot mode after a reset or a flash rejoins (tests_hardware/README.md "Bench traps"). Run as
`.venv/bin/python tests_hardware/kick_then_reset.py [--device D]`; exits 2 when the bench bridge is not set up."""

import argparse
import sys

import harness
from bench_control import BenchBridge


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Kick every station off the bench AP, then hard-reset the board.")
    parser.add_argument("--device", help="the board's serial device (default: $MPREMOTE_DEVICE, else the one board found by id)")
    args = parser.parse_args(argv)
    bench = BenchBridge()
    if not bench.is_configured():
        print(f"kick_then_reset: no bench AP profile {bench.ap_conn!r} - run `uv run toolchain/setup_toolchain.py env --tier bench` first", file=sys.stderr)
        return 2
    harness.kick_then_reset(harness.Board(device=args.device), bench)
    return 0


if __name__ == "__main__":
    sys.exit(main())
