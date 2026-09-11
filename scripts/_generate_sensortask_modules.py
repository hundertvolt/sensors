#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Pre-generates every real device's `sensortask_<device>.py` via `buildgen` into
`build/generated_src/` (gitignored, regenerated fresh every run) - the mechanism that lets every
test statically importing `sensortask_wozi`/`sensortask_dev` keep working unchanged now that
neither hand-written file exists any more (BUILD_CHAIN_PLAN.md's Session 6 finish criterion).
Deliberately NOT written into `src/` itself: `src/` is fully-reviewed, hand-committed code under
ruff/mypy's strict scope (CLAUDE.md), and freshly generated output has no business there."""

# Usage: uv run scripts/_generate_sensortask_modules.py
# Called by scripts/test.sh, scripts/typecheck.sh, scripts/run_unix_port_integration.sh and
# scripts/run_digital_twin_ci.sh before anything imports a sensortask_<device> module - see each
# script's own comment for why every one of them needs this.

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from buildgen.errors import BuildError  # noqa: E402
from buildgen.generate import generate_device  # noqa: E402

# Every real device (devices/*.toml) - not just wozi/dev, the two consumed by tests today, so the
# mechanism is proven fully general and future test-generalization work has every device's module
# already sitting on disk to import.
DEVICES = ("wozi", "dev", "arzi", "klkizi", "grkizi", "schlafzi")


def main() -> int:
    out_dir = REPO_ROOT / "build" / "generated_src"
    out_dir.mkdir(parents=True, exist_ok=True)
    for device in DEVICES:
        try:
            generated = generate_device(REPO_ROOT / "devices" / f"{device}.toml", REPO_ROOT / "src", REPO_ROOT / "ext")
        except BuildError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        (out_dir / f"sensortask_{device}.py").write_text(generated.module_source)
    print(f"Generated {len(DEVICES)} device module(s) into {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
