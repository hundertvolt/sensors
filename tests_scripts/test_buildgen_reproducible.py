"""Generated build inputs are byte-identical across hash seeds (SPECIFICATION.md Part L.4): two CPython
processes started with different PYTHONHASHSEEDs generate every device and both fixtures with one fixed
build date, so a set's iteration order reaching any output shows as a difference naming device and line."""

import json
import os
import subprocess
import sys
from pathlib import Path

from _devices import DEVICE_NAMES

_REPO = Path(__file__).resolve().parent.parent
_TOMLS = [*(f"devices/{d}.toml" for d in DEVICE_NAMES), "tests_scripts/buildgen_fixtures/multi_instance.toml", "tests_scripts/buildgen_fixtures/novel_combo.toml"]
_SEEDS = ("0", "4242")
# @tunable l0.buildgen_reproducible_timeout_s = 120
_TIMEOUT_S = 120

# Runs in each child: every output as the writer emits it (insertion order kept), stdout only, nothing written.
_PROGRAM = """
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from buildgen.api_reference import api_reference_json, generate_api_reference
from buildgen.definitions import generate_definitions
from buildgen.generate import generate_device
from buildgen.twin_wiring import compute_twin_wiring

outputs = {}
for toml in sys.argv[2:]:
    generated = generate_device(root / toml, root / "src", root / "ext", build_date="2026-01-01T00:00:00Z")
    outputs[Path(toml).stem] = {
        "module": generated.module_source,
        "boot_entry": generated.boot_entry_source,
        "boot_entry_noautostart": generated.boot_entry_noautostart_source,
        "wiring_plan": json.dumps(compute_twin_wiring(generated.model), indent=1),
        "expected_facts": json.dumps(generated.expected_facts, indent=1),
        "definitions": json.dumps(generate_definitions(generated.model, root / "src"), indent=1),
        "api_reference": api_reference_json(generate_api_reference(generated.model, root / "src")),
        "frozen_modules": "\\n".join(sorted(generated.frozen_modules)),
    }
print(json.dumps({"str_hash": hash("buildgen"), "outputs": outputs}))
"""


def _first_difference(a: str, b: str) -> str:
    for number, (line_a, line_b) in enumerate(zip(a.splitlines(), b.splitlines(), strict=False), start=1):
        if line_a != line_b:
            return f"line {number}: {line_a!r} != {line_b!r}"
    return f"one ends first (line counts {len(a.splitlines())} and {len(b.splitlines())})"


def test_every_generated_input_is_identical_across_hash_seeds() -> None:
    children = [
        subprocess.Popen([sys.executable, "-c", _PROGRAM, str(_REPO), *_TOMLS], env={**os.environ, "PYTHONHASHSEED": seed}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for seed in _SEEDS
    ]
    runs = []
    for seed, child in zip(_SEEDS, children, strict=True):
        out, err = child.communicate(timeout=_TIMEOUT_S)
        assert child.returncode == 0, f"PYTHONHASHSEED={seed}: {err}"
        runs.append(json.loads(out))
    # Not vacuous: the two processes really hashed strings differently.
    assert runs[0]["str_hash"] != runs[1]["str_hash"]
    first, second = runs[0]["outputs"], runs[1]["outputs"]
    assert sorted(first) == sorted(Path(t).stem for t in _TOMLS)
    differences = [f"{key} {part}: {_first_difference(text, second[key][part])}" for key, parts in first.items() for part, text in parts.items() if text != second[key][part]]
    assert differences == []
