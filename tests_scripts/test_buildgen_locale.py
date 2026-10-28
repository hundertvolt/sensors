"""The build reads and writes its text as UTF-8 whatever the host's locale: every device's whole build - module, boot
entries, facts, definitions, API reference, frozen set and the CLI's files - is the same under an ASCII locale with
Python's UTF-8 mode off as in UTF-8 mode, and the builds read every src/ file that carries non-ASCII text."""

import json
import subprocess
import sys
from pathlib import Path

# Run in a fresh interpreter, so the locale and UTF-8 mode under test are the process's own.
_PROBE = """
import hashlib, json, re, sys
from pathlib import Path
root, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(root))
from buildgen.api_reference import api_reference_json, generate_api_reference
from buildgen.definitions import generate_definitions
from buildgen.generate import generate_device, main
parts, frozen = [], set()
for toml in sorted((root / "devices").glob("*.toml")):
    r = generate_device(toml, root / "src", root / "ext", build_date="2026-01-01T00:00:00Z")
    parts += [r.module_source, r.boot_entry_source, r.boot_entry_noautostart_source, json.dumps(r.expected_facts, sort_keys=True),
              json.dumps(generate_definitions(r.model, root / "src"), sort_keys=True, ensure_ascii=False),
              api_reference_json(generate_api_reference(r.model, root / "src")), json.dumps(sorted(r.frozen_modules))]
    frozen |= set(r.frozen_modules)
    assert main([str(toml), "--out-dir", str(out / toml.stem)]) == 0
    parts += [re.sub(r"\\d{4}-\\d\\d-\\d\\dT\\d\\d:\\d\\d:\\d\\dZ", "<date>", p.read_bytes().decode("utf-8")) for p in sorted((out / toml.stem).iterdir())]
print(json.dumps({"parts": len(parts), "digest": hashlib.sha256("\\0".join(parts).encode("utf-8")).hexdigest(), "frozen": sorted(frozen)}))
"""


def _build(repo_root: Path, out: Path, *, utf8_mode: bool) -> "dict[str, object]":
    env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C.UTF-8" if utf8_mode else "C", "LANG": "C"}
    done = subprocess.run([sys.executable, "-I", "-X", f"utf8={int(utf8_mode)}", "-c", _PROBE, str(repo_root), str(out)], env=env, capture_output=True, text=True, encoding="utf-8", check=False, timeout=300)
    assert done.returncode == 0, done.stderr
    result: dict[str, object] = json.loads(done.stdout)
    return result


def test_every_devices_build_is_the_same_under_an_ascii_locale_as_in_utf8_mode(repo_root: Path, tmp_path: Path) -> None:
    assert _build(repo_root, tmp_path / "ascii", utf8_mode=False) == _build(repo_root, tmp_path / "utf8", utf8_mode=True)


def test_the_builds_read_every_src_file_that_carries_non_ascii_text(repo_root: Path, tmp_path: Path) -> None:
    # The locale test is only as wide as the files the builds read: a non-ASCII file outside every frozen set goes unread.
    non_ascii = {p.stem for p in (repo_root / "src").glob("*.py") if not p.read_bytes().isascii()}
    assert non_ascii, "no src/ file carries non-ASCII text - the locale test reads nothing a locale could break"
    frozen = _build(repo_root, tmp_path, utf8_mode=True)["frozen"]
    assert isinstance(frozen, list)
    assert non_ascii <= set(frozen), f"non-ASCII src/ files no device's build reads: {sorted(non_ascii - set(frozen))}"
