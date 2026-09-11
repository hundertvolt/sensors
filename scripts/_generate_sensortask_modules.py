#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Pre-generates every real device's `sensortask_<device>.py` via `buildgen` into gitignored
`build/generated_src/`, regenerated fresh every run - lets tests statically importing
`sensortask_wozi`/`sensortask_dev` keep working (BUILD_CHAIN_PLAN.md's Session 6; SPECIFICATION.md E.3).
Also writes each device's `buildgen.twin_wiring.compute_twin_wiring()` plan alongside its module
(`sensortask_<device>_wiring_plan.json`) - the one extra artifact `scripts/_digital_twin_ci_suite.py`
needs to boot every device under `digital_twin/run_generic_integration.py` (Session 6.2)."""

# Usage: uv run scripts/_generate_sensortask_modules.py
# Called by scripts/test.sh, scripts/typecheck.sh, scripts/run_unix_port_integration.sh and
# scripts/run_digital_twin_ci.sh before anything imports a sensortask_<device> module - see each
# script's own comment for why every one of them needs this.

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from buildgen.errors import BuildError  # noqa: E402
from buildgen.generate import generate_device  # noqa: E402
from buildgen.twin_wiring import compute_twin_wiring  # noqa: E402


def main() -> int:
    out_dir = REPO_ROOT / "build" / "generated_src"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Every real device (devices/*.toml) - not just wozi/dev, the two consumed by tests today, so
    # the mechanism is proven fully general and future test-generalization work has every device's
    # module already sitting on disk to import. Discovered from the directory, not a hand-kept
    # list, so a 7th device never needs a second edit here to actually get generated.
    device_tomls = sorted(REPO_ROOT.glob("devices/*.toml"))
    for device_toml in device_tomls:
        device = device_toml.stem
        try:
            generated = generate_device(device_toml, REPO_ROOT / "src", REPO_ROOT / "ext")
        except BuildError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        (out_dir / f"sensortask_{device}.py").write_text(generated.module_source)
        wiring_plan = compute_twin_wiring(generated.model)
        (out_dir / f"sensortask_{device}_wiring_plan.json").write_text(json.dumps(wiring_plan))
    print(f"Generated {len(device_tomls)} device module(s) + wiring plan(s) into {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
