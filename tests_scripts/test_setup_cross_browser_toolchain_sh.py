"""scripts/setup_cross_browser_toolchain.sh runs under `set -e`, so a bare `apt-get update` lets
one unrelated third-party source abort an install the main archive could serve. The real script is
executed against stubbed sudo/apt-get, with a control arm proving the tolerance is what does it."""

import subprocess
from pathlib import Path

import pytest

_SCRIPT = Path("scripts") / "setup_cross_browser_toolchain.sh"
_TOLERANCE = ' || echo "== apt-get update reported errors - continuing, the install below still gates"'


def _stub_tree(tmp_path: Path, *, update_rc: int, install_rc: int) -> tuple[Path, Path]:
    """A PATH whose sudo/apt-get are stubs, plus the Edge and Firefox binaries the script probes
    for - present so only the WebKit block, the one that reaches apt, actually runs."""
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    calls = tmp_path / "apt-calls.txt"
    # Absolute shebangs and an `env` stub, because the PATH below holds nothing else: the script
    # probes for WebKitWebDriver with `command -v`, so a host that has one would skip the only
    # block that reaches apt and pass this test for the wrong reason.
    (stub_bin / "sudo").write_text('#!/bin/bash\nexec "$@"\n')
    (stub_bin / "env").write_text('#!/bin/bash\nwhile [[ "$1" == *=* ]]; do export "$1"; shift; done\nexec "$@"\n')
    (stub_bin / "apt-get").write_text(
        "#!/bin/bash\n"
        f'echo "$@" >> {calls}\n'
        f'if [ "$1" = "update" ]; then echo "E: Failed to fetch a PPA" >&2; exit {update_rc}; fi\n'
        f"exit {install_rc}\n",
    )
    (stub_bin / "microsoft-edge-stable").write_text("#!/bin/bash\nexit 0\n")
    ff = tmp_path / "cross-browser" / "mamba_root" / "envs" / "ff" / "bin"
    ff.mkdir(parents=True)
    for name in ("firefox", "geckodriver"):
        (ff / name).write_text("#!/bin/bash\nexit 0\n")
        (ff / name).chmod(0o755)
    for stub in stub_bin.iterdir():
        stub.chmod(0o755)
    return stub_bin, calls


def _run(script: Path, tmp_path: Path, stub_bin: Path) -> subprocess.CompletedProcess[str]:
    # The stubs are the WHOLE PATH: nothing here can touch real system state, and the result
    # does not depend on which browsers this host happens to have installed.
    env = {
        "PATH": str(stub_bin),
        "HOME": str(tmp_path),
        "CROSS_BROWSER_TOOLCHAIN_DIR": str(tmp_path / "cross-browser"),
    }
    return subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, check=False, env=env)


@pytest.fixture
def script(repo_root: Path) -> Path:
    return repo_root / _SCRIPT


def test_an_unrelated_apt_source_that_fails_update_does_not_stop_the_install(script: Path, tmp_path: Path) -> None:
    stub_bin, calls = _stub_tree(tmp_path, update_rc=100, install_rc=0)
    result = _run(script, tmp_path, stub_bin)
    assert result.returncode == 0, f"the installer aborted on a failed apt-get update: {result.stdout}{result.stderr}"
    assert "webkit2gtk-driver" in calls.read_text(), "apt-get install never ran, so the update failure still stopped it"


def test_removing_the_tolerance_is_what_brings_the_abort_back(script: Path, tmp_path: Path) -> None:
    # The control arm: the same run against a copy whose `|| echo ...` is stripped must fail, so a
    # green result above is attributable to the tolerance rather than to the stubs being lenient.
    bare = tmp_path / "bare.sh"
    text = script.read_text()
    assert _TOLERANCE in text, "the apt_update tolerance this test is about is no longer in the script"
    bare.write_text(text.replace(_TOLERANCE, ""))
    stub_bin, calls = _stub_tree(tmp_path, update_rc=100, install_rc=0)
    result = _run(bare, tmp_path, stub_bin)
    assert result.returncode != 0, "a bare apt-get update somehow survived a failing update"
    assert "webkit2gtk-driver" not in calls.read_text()


def test_a_package_that_really_cannot_be_installed_still_fails(script: Path, tmp_path: Path) -> None:
    stub_bin, _ = _stub_tree(tmp_path, update_rc=0, install_rc=1)
    result = _run(script, tmp_path, stub_bin)
    assert result.returncode != 0, "a failed apt-get install was swallowed - the install must stay fatal"


def test_no_apt_get_install_tolerates_its_own_failure(script: Path) -> None:
    installs = [line for line in script.read_text().splitlines() if "apt-get install" in line]
    assert installs, "no apt-get install line found - this guard is pinned to the wrong script"
    for line in installs:
        assert "||" not in line, f"an apt-get install line tolerates its own failure: {line.strip()}"
