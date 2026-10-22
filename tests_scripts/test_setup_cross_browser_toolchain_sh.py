"""scripts/setup_cross_browser_toolchain.sh run against stub sudo/apt-get/curl/gpg/tee: an unrelated failing apt source
does not stop it (with a control arm), Xvfb has its own check, every apt fetch is bounded and retried as the installer's
are, and Microsoft's key and the micromamba binary are verified before use, a bad download leaving nothing behind."""

import hashlib
import re
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module

_SCRIPT = Path("scripts") / "setup_cross_browser_toolchain.sh"
_TOLERANCE = ' || echo "== apt-get update reported errors - continuing, the install below still gates"'
# The real tools the script itself runs; everything that installs, fetches or needs root is a stub.
_REAL_TOOLS = ("mkdir", "chmod", "mv", "rm", "mktemp", "cat", "sha256sum")
_OTHER_FINGERPRINT = "0123456789ABCDEF0123456789ABCDEF01234567"
# The fake download's own content: a micromamba that records its call and lays out the Firefox env.
_FAKE_MICROMAMBA = '#!/bin/bash\necho "micromamba $*" >> "$STUB_LOG"\nmkdir -p "$MAMBA_ROOT_PREFIX/envs/ff/bin"\n'


def _write_stub(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def _real(tool: str) -> str:
    found = shutil.which(tool)
    assert found is not None, f"{tool} is not on this host's PATH"
    return found


def _stub_tree(tmp_path: Path, *, update_rc: int = 0, install_rc: int = 0, present: "tuple[str, ...]" = ("microsoft-edge-stable", "firefox"), key_fingerprints: "tuple[str, ...]" = (), http_error: bool = False, offered: "tuple[str, ...]" = ("webkitgtk-webdriver",)) -> "tuple[Path, Path]":
    # A PATH holding only the stubs and the real tools the script runs: a host's own WebKitWebDriver, Xvfb or Edge can
    # never skip a block and pass a test for the wrong reason, and nothing touches real system state (tee writes here).
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    log = tmp_path / "calls.txt"
    log.touch()
    for tool in _REAL_TOOLS:
        (stub_bin / tool).symlink_to(_real(tool))
    _write_stub(stub_bin / "sudo", '#!/bin/bash\nexec "$@"\n')
    _write_stub(stub_bin / "env", '#!/bin/bash\nwhile [[ "$1" == *=* ]]; do export "$1"; shift; done\nexec "$@"\n')
    _write_stub(stub_bin / "apt-get", (
        "#!/bin/bash\n"
        f'echo "apt-get $*" >> {log}\n'
        f'if [[ " $* " == *" update "* ]]; then echo "E: Failed to fetch a PPA" >&2; exit {update_rc}; fi\n'
        f"exit {install_rc}\n"
    ))
    # apt-cache policy: a candidate version for each offered package, "(none)" for any other name, as apt prints for a
    # name another package still refers to (Ubuntu 26.04's webkit2gtk-driver).
    _write_stub(stub_bin / "apt-cache", (
        "#!/bin/bash\n"
        f'echo "apt-cache $*" >> {log}\n'
        'pkg="${*: -1}"\n'
        f'case " {" ".join(offered)} " in *" $pkg "*) candidate=2.52.6 ;; *) candidate="(none)" ;; esac\n'
        'printf "%s:\\n  Installed: (none)\\n  Candidate: %s\\n" "$pkg" "$candidate"\n'
    ))
    (tmp_path / "tee").mkdir()
    _write_stub(stub_bin / "tee", f'#!/bin/bash\necho "tee $*" >> {log}\n{_real("cat")} > "{tmp_path}/tee/${{1##*/}}"\n')
    # curl: logs its arguments and writes the URL's body to -o; as an HTTP error, real curl keeps the error body and exits
    # 0 unless given --fail (-f), when it writes nothing and exits 22.
    (tmp_path / "micromamba.body").write_text(_FAKE_MICROMAMBA, encoding="utf-8")
    _write_stub(stub_bin / "curl", (
        "#!/bin/bash\n"
        f'echo "curl $*" >> {log}\n'
        'out=""; fail=0; while [ "$#" -gt 0 ]; do case "$1" in -o) out="$2"; shift ;; --fail) fail=1 ;; --*) ;; -*f*) fail=1 ;; esac; url="$1"; shift; done\n'
        f'if [ {int(http_error)} -eq 1 ]; then [ "$fail" -eq 1 ] && exit 22; echo "<html>404 Not Found</html>" > "$out"; exit 0; fi\n'
        f'case "$url" in *micromamba*) {_real("cat")} {tmp_path}/micromamba.body > "$out" ;; *) echo "fake armored key" > "$out" ;; esac\n'
    ))
    listing = "".join(f"pub:-:2048:1:{fpr[-16:]}:1446074508:::-:::scSC::::::23::0:\\nfpr:::::::::{fpr}:\\n" for fpr in key_fingerprints)
    _write_stub(stub_bin / "gpg", (
        "#!/bin/bash\n"
        f'echo "gpg $*" >> {log}\n'
        f'if [[ " $* " == *" --show-keys "* ]]; then printf "{listing}"; exit 0; fi\n'
        'echo "dearmored key"\n'
    ))
    for name in present:
        if name == "firefox":
            ff = tmp_path / "cross-browser" / "mamba_root" / "envs" / "ff" / "bin"
            ff.mkdir(parents=True)
            for binary in ("firefox", "geckodriver"):
                _write_stub(ff / binary, "#!/bin/bash\nexit 0\n")
        else:
            _write_stub(stub_bin / name, "#!/bin/bash\nexit 0\n")
    return stub_bin, log


def _run(script: Path, tmp_path: Path, stub_bin: Path) -> "subprocess.CompletedProcess[str]":
    # The stubs are the WHOLE PATH, so the result does not depend on which browsers this host has installed.
    (tmp_path / "tmp").mkdir(exist_ok=True)
    env = {
        "PATH": str(stub_bin),
        "HOME": str(tmp_path),
        "TMPDIR": str(tmp_path / "tmp"),
        "STUB_LOG": str(tmp_path / "calls.txt"),
        "CROSS_BROWSER_TOOLCHAIN_DIR": str(tmp_path / "cross-browser"),
    }
    return subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, check=False, env=env, timeout=60)


def _calls(log: Path, tool: str) -> "list[str]":
    return [line for line in log.read_text(encoding="utf-8").splitlines() if line.startswith(f"{tool} ")]


def _constant(text: str, name: str) -> str:
    match = re.search(rf"^{name}=(\S+)$", text, re.MULTILINE)
    assert match is not None, f"the script no longer sets {name}"
    return match.group(1)


def _matching_copy(script: Path, tmp_path: Path) -> Path:
    # The script with its pinned SHA-256 replaced by the fake download's, so the verified path runs to its end.
    text = script.read_text(encoding="utf-8")
    pinned = _constant(text, "MICROMAMBA_SHA256")
    copy = tmp_path / "matching.sh"
    copy.write_text(text.replace(pinned, hashlib.sha256(_FAKE_MICROMAMBA.encode()).hexdigest()), encoding="utf-8")
    return copy


@pytest.fixture
def script(repo_root: Path) -> Path:
    return repo_root / _SCRIPT


@pytest.fixture(scope="module")
def setup_toolchain(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "toolchain" / "setup_toolchain.py", "setup_toolchain")


def test_an_unrelated_apt_source_that_fails_update_does_not_stop_the_install(script: Path, tmp_path: Path) -> None:
    stub_bin, log = _stub_tree(tmp_path, update_rc=100)
    result = _run(script, tmp_path, stub_bin)
    assert result.returncode == 0, f"the installer aborted on a failed apt-get update: {result.stdout}{result.stderr}"
    assert any(call.endswith(" install -y --no-install-recommends webkitgtk-webdriver") for call in _calls(log, "apt-get")), "apt-get install never ran, so the update failure still stopped it"


def test_removing_the_tolerance_is_what_brings_the_abort_back(script: Path, tmp_path: Path) -> None:
    # The control arm: the same run against a copy whose `|| echo ...` is stripped must fail, so a
    # green result above is attributable to the tolerance rather than to the stubs being lenient.
    bare = tmp_path / "bare.sh"
    text = script.read_text(encoding="utf-8")
    assert _TOLERANCE in text, "the apt_update tolerance this test is about is no longer in the script"
    bare.write_text(text.replace(_TOLERANCE, ""), encoding="utf-8")
    stub_bin, log = _stub_tree(tmp_path, update_rc=100)
    result = _run(bare, tmp_path, stub_bin)
    assert result.returncode != 0, "a bare apt-get update somehow survived a failing update"
    assert not any(" install " in call for call in _calls(log, "apt-get"))


def test_a_package_that_really_cannot_be_installed_still_fails(script: Path, tmp_path: Path) -> None:
    stub_bin, _ = _stub_tree(tmp_path, install_rc=1)
    result = _run(script, tmp_path, stub_bin)
    assert result.returncode != 0, "a failed apt-get install was swallowed - the install must stay fatal"


def test_no_apt_get_install_tolerates_its_own_failure(script: Path) -> None:
    installs = [line for line in script.read_text(encoding="utf-8").splitlines() if re.search(r"apt-get\b[^|]*\sinstall\s+-y\b", line)]
    assert installs, "no apt-get install line found - this guard is pinned to the wrong script"
    for line in installs:
        assert "||" not in line, f"an apt-get install line tolerates its own failure: {line.strip()}"


def test_every_apt_fetch_is_bounded_and_retried_as_the_installers_are(script: Path, tmp_path: Path, setup_toolchain: ModuleType) -> None:
    stub_bin, log = _stub_tree(tmp_path)
    assert _run(script, tmp_path, stub_bin).returncode == 0
    calls = _calls(log, "apt-get")
    assert len(calls) >= 2, calls  # the Xvfb and WebKit installs and the updates before them
    options = " ".join(setup_toolchain.apt_options())
    for call in calls:
        assert call.startswith(f"apt-get {options} "), f"an apt-get call without the installer's fetch bound and retries ({options}): {call}"


def test_with_xvfb_and_webkit_present_no_apt_call_is_made_and_the_summary_names_xvfb(script: Path, tmp_path: Path) -> None:
    stub_bin, log = _stub_tree(tmp_path, present=("microsoft-edge-stable", "firefox", "Xvfb", "WebKitWebDriver"))
    result = _run(script, tmp_path, stub_bin)
    assert result.returncode == 0, result.stderr
    assert _calls(log, "apt-get") == []
    assert f"Xvfb:            {stub_bin / 'Xvfb'}" in result.stdout


def test_webkit_present_without_xvfb_installs_only_xvfb(script: Path, tmp_path: Path) -> None:
    stub_bin, log = _stub_tree(tmp_path, present=("microsoft-edge-stable", "firefox", "WebKitWebDriver"))
    assert _run(script, tmp_path, stub_bin).returncode == 0
    installs = [call for call in _calls(log, "apt-get") if " install " in call]
    assert len(installs) == 1 and installs[0].endswith(" xvfb"), installs


# WebKitGTK 2.45.5 renamed the driver package; both names ship /usr/bin/WebKitWebDriver, and the newer is taken first.
@pytest.mark.parametrize(("offered", "installed"), [
    (("webkitgtk-webdriver",), "webkitgtk-webdriver"),  # Ubuntu 25.04 on, the CI runner's 26.04
    (("webkit2gtk-driver",), "webkit2gtk-driver"),  # Ubuntu 24.04
    (("webkitgtk-webdriver", "webkit2gtk-driver"), "webkitgtk-webdriver"),
])
def test_xvfb_present_without_webkit_installs_only_the_driver_apt_offers(script: Path, tmp_path: Path, offered: "tuple[str, ...]", installed: str) -> None:
    stub_bin, log = _stub_tree(tmp_path, present=("microsoft-edge-stable", "firefox", "Xvfb"), offered=offered)
    assert _run(script, tmp_path, stub_bin).returncode == 0
    installs = [call for call in _calls(log, "apt-get") if " install " in call]
    assert len(installs) == 1 and installs[0].endswith(f" {installed}"), installs


def test_a_driver_apt_offers_under_neither_name_exits_1_naming_both_and_installs_nothing(script: Path, tmp_path: Path) -> None:
    stub_bin, log = _stub_tree(tmp_path, present=("microsoft-edge-stable", "firefox", "Xvfb"), offered=())
    result = _run(script, tmp_path, stub_bin)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "webkitgtk-webdriver" in result.stderr and "webkit2gtk-driver" in result.stderr, result.stderr
    assert not [call for call in _calls(log, "apt-get") if " install " in call]


def test_a_key_with_another_fingerprint_exits_1_and_writes_no_keyring(script: Path, tmp_path: Path) -> None:
    stub_bin, log = _stub_tree(tmp_path, present=("firefox", "Xvfb", "WebKitWebDriver"), key_fingerprints=(_OTHER_FINGERPRINT,))
    result = _run(script, tmp_path, stub_bin)
    assert result.returncode == 1, result.stderr
    assert _OTHER_FINGERPRINT in result.stderr and _constant(script.read_text(encoding="utf-8"), "EDGE_KEY_FINGERPRINT") in result.stderr
    assert _calls(log, "tee") == [] and not any("--dearmor" in call for call in _calls(log, "gpg"))
    assert _calls(log, "apt-get") == []


def test_a_key_file_carrying_a_second_key_is_refused(script: Path, tmp_path: Path) -> None:
    expected = _constant(script.read_text(encoding="utf-8"), "EDGE_KEY_FINGERPRINT")
    stub_bin, log = _stub_tree(tmp_path, present=("firefox", "Xvfb", "WebKitWebDriver"), key_fingerprints=(expected, _OTHER_FINGERPRINT))
    assert _run(script, tmp_path, stub_bin).returncode == 1
    assert _calls(log, "tee") == []


def test_microsofts_key_is_fetched_failing_on_http_errors_and_dearmored_once_checked(script: Path, tmp_path: Path) -> None:
    expected = _constant(script.read_text(encoding="utf-8"), "EDGE_KEY_FINGERPRINT")
    stub_bin, log = _stub_tree(tmp_path, present=("firefox", "Xvfb", "WebKitWebDriver"), key_fingerprints=(expected,))
    result = _run(script, tmp_path, stub_bin)
    assert result.returncode == 0, result.stderr
    (fetch,) = _calls(log, "curl")
    assert re.search(r"\s-\w*f", fetch), f"the key download does not fail on an HTTP error, so an error body would be kept: {fetch}"
    assert (tmp_path / "tee" / "microsoft-edge.gpg").read_text(encoding="utf-8") == "dearmored key\n"
    edge = [call for call in _calls(log, "apt-get") if call.endswith(" microsoft-edge-stable")]
    assert len(edge) == 1 and "Acquire::Retries=" in edge[0], edge


def test_an_http_error_on_the_micromamba_download_leaves_no_executable(script: Path, tmp_path: Path) -> None:
    stub_bin, _ = _stub_tree(tmp_path, present=("microsoft-edge-stable", "Xvfb", "WebKitWebDriver"), http_error=True)
    assert _run(script, tmp_path, stub_bin).returncode != 0
    assert list((tmp_path / "cross-browser").rglob("micromamba*")) == []


def test_a_micromamba_checksum_mismatch_exits_1_and_leaves_no_executable(script: Path, tmp_path: Path) -> None:
    stub_bin, log = _stub_tree(tmp_path, present=("microsoft-edge-stable", "Xvfb", "WebKitWebDriver"))
    result = _run(script, tmp_path, stub_bin)
    assert result.returncode == 1, result.stderr
    assert "SHA-256" in result.stderr
    assert list((tmp_path / "cross-browser").rglob("micromamba*")) == []
    assert not any(line.startswith("micromamba ") for line in log.read_text(encoding="utf-8").splitlines())


def test_a_verified_micromamba_of_the_pinned_release_is_installed_and_run(script: Path, tmp_path: Path) -> None:
    stub_bin, log = _stub_tree(tmp_path, present=("microsoft-edge-stable", "Xvfb", "WebKitWebDriver"))
    result = _run(_matching_copy(script, tmp_path), tmp_path, stub_bin)
    assert result.returncode == 0, result.stderr
    (fetch,) = _calls(log, "curl")
    version = _constant(script.read_text(encoding="utf-8"), "MICROMAMBA_VERSION")
    assert f"/releases/download/{version}/micromamba-linux-64" in fetch and re.search(r"\s-\w*f", fetch), fetch
    installed = tmp_path / "cross-browser" / "bin" / "micromamba"
    assert installed.read_text(encoding="utf-8") == _FAKE_MICROMAMBA and installed.stat().st_mode & 0o111
    assert any(line.startswith("micromamba create ") for line in log.read_text(encoding="utf-8").splitlines())


def test_an_unverified_micromamba_left_by_an_older_run_is_fetched_again(script: Path, tmp_path: Path) -> None:
    stub_bin, log = _stub_tree(tmp_path, present=("microsoft-edge-stable", "Xvfb", "WebKitWebDriver"))
    stale = tmp_path / "cross-browser" / "bin" / "micromamba"
    stale.parent.mkdir(parents=True)
    _write_stub(stale, "<html>an HTTP error body an unchecked download kept</html>\n")
    assert _run(_matching_copy(script, tmp_path), tmp_path, stub_bin).returncode == 0
    assert len(_calls(log, "curl")) == 1
    assert stale.read_text(encoding="utf-8") == _FAKE_MICROMAMBA


@pytest.mark.parametrize("fingerprint", ["expected", _OTHER_FINGERPRINT])
def test_no_temporary_file_outlives_the_run(script: Path, tmp_path: Path, fingerprint: str) -> None:
    expected = _constant(script.read_text(encoding="utf-8"), "EDGE_KEY_FINGERPRINT")
    stub_bin, _ = _stub_tree(tmp_path, present=("Xvfb", "WebKitWebDriver"), key_fingerprints=(expected if fingerprint == "expected" else fingerprint,))
    _run(script, tmp_path, stub_bin)
    assert list((tmp_path / "tmp").iterdir()) == []
    assert list((tmp_path / "cross-browser").rglob("*.part")) == []
