#!/usr/bin/env bash
# Installs Xvfb and the three non-Chromium engines scripts/cross_browser_smoke.mjs drives (WebKitGTK, real Microsoft
# Edge, real Firefox) - idempotent, safe to re-run, every download verified before use. Playwright's own Chromium comes
# from `npx playwright install chromium` instead and is unrelated to this script.
#
# None of the three channels below is the obvious one for its engine; SPECIFICATION.md Part H.7's
# "Why each engine comes from the channel it does" has the investigation trail for all three.
set -euo pipefail
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    cat <<'EOF'
Usage: scripts/setup_cross_browser_toolchain.sh
Installs WebKitGTK's driver and Xvfb, Microsoft Edge and Firefox with geckodriver for
scripts/cross_browser_smoke.mjs; idempotent. Needs sudo for the apt steps.

Environment:
  CROSS_BROWSER_TOOLCHAIN_DIR   where Firefox and geckodriver go (default: ~/cross-browser-toolchain)
EOF
    exit 0
fi
if [ "$#" -gt 0 ]; then
    echo "error: unknown argument '$1' - scripts/setup_cross_browser_toolchain.sh takes none (see --help)" >&2
    exit 2
fi

# Every apt fetch gives up past the timeout and is retried, as toolchain/setup_toolchain.py's apt_options() has it: a
# stalled mirror fails the step naming the package rather than holding it to the CI job's own limit.
# @tunable tool.uv_sync_attempts = 3
NETWORK_ATTEMPTS=3
# @tunable tool.apt_acquire_timeout_s = 30
APT_ACQUIRE_TIMEOUT_S=30
APT_OPTIONS=(-o "Acquire::Retries=$((NETWORK_ATTEMPTS - 1))" -o "Acquire::http::Timeout=$APT_ACQUIRE_TIMEOUT_S" -o "Acquire::https::Timeout=$APT_ACQUIRE_TIMEOUT_S")
# Microsoft's package-signing key ("Microsoft (Release signing)"): the fingerprint gpg --show-keys reads from the key
# served at https://packages.microsoft.com/keys/microsoft.asc (agent, 2026-10-19).
EDGE_KEY_FINGERPRINT=BC528686B50D79E339D3721CEB3E94ADBE1229CF
# micromamba only bootstraps the Firefox env, so it is pinned (agent, 2026-10-19): the SHA-256 is the release's own
# https://github.com/mamba-org/micromamba-releases/releases/download/2.9.0-0/micromamba-linux-64.sha256, re-hashed here.
MICROMAMBA_VERSION=2.9.0-0
MICROMAMBA_SHA256=366cd9cd8be14df1ab8ed50352a82111082a36686b2d389fdb79a92c3fafb3e3

# The one trap removes every temporary file, set before the first is made: a failed or interrupted run leaves none.
tmp=""
partial=""
cleanup() {
    if [ -n "$tmp" ]; then rm -rf "$tmp"; fi
    if [ -n "$partial" ]; then rm -f "$partial"; fi
}
trap cleanup EXIT
tmp=$(mktemp -d)

# Non-fatal, like toolchain/setup_toolchain.py's own ensure_apt_packages(): an unrelated
# third-party source (a PPA that 403s or whose key expired) must not stop an install from the main
# archive. Every apt-get install below stays fatal, so a package we really need still fails loudly.
apt_update() {
    sudo apt-get "${APT_OPTIONS[@]}" update || echo "== apt-get update reported errors - continuing, the install below still gates"
}

# The version apt would install for package $1, or nothing: a renamed package's old name reads "Candidate: (none)".
apt_candidate() {
    local line
    apt-cache policy "$1" 2>/dev/null | while read -r line; do
        case "$line" in "Candidate: (none)") ;; "Candidate: "*) echo "${line#Candidate: }" ;; esac
    done || true
}

# The one primary key a key file holds, or nothing: a file carrying any second key is refused with the rest.
primary_fingerprint() {
    local listing kind value previous="" found=""
    listing=$(GNUPGHOME="$tmp/gnupg" gpg --batch --show-keys --with-colons "$1")
    while IFS=: read -r kind _ _ _ _ _ _ _ _ value _; do
        if [ "$kind" = "fpr" ] && [ "$previous" = "pub" ]; then
            if [ -n "$found" ]; then return 0; fi
            found="$value"
        fi
        previous="$kind"
    done <<<"$listing"
    echo "$found"
}

# --- Xvfb: the virtual display WebKitGTK and Firefox run on, even headless ---
if ! command -v Xvfb >/dev/null 2>&1; then
    echo "== Installing xvfb"
    apt_update
    sudo env DEBIAN_FRONTEND=noninteractive apt-get "${APT_OPTIONS[@]}" install -y --no-install-recommends xvfb
else
    echo "== Xvfb already installed, skipping"
fi

# --- WebKit: its WebDriver package, webkitgtk-webdriver since WebKitGTK 2.45.5 (Ubuntu 25.04 on), webkit2gtk-driver
# before (Ubuntu 24.04); both ship /usr/bin/WebKitWebDriver, and the newer name wins where apt offers both ---
if ! command -v WebKitWebDriver >/dev/null 2>&1; then
    apt_update
    webkit_package=""
    for name in webkitgtk-webdriver webkit2gtk-driver; do
        if [ -n "$(apt_candidate "$name")" ]; then webkit_package=$name; break; fi
    done
    if [ -z "$webkit_package" ]; then
        echo "error: apt offers neither webkitgtk-webdriver nor webkit2gtk-driver, the two packages WebKitWebDriver ships in" >&2
        exit 1
    fi
    echo "== Installing $webkit_package"
    sudo env DEBIAN_FRONTEND=noninteractive apt-get "${APT_OPTIONS[@]}" install -y --no-install-recommends "$webkit_package"
else
    echo "== WebKitWebDriver already installed, skipping"
fi

# --- Microsoft Edge: Microsoft's own apt repo, its key checked by fingerprint before apt trusts it ---
if ! command -v microsoft-edge-stable >/dev/null 2>&1; then
    echo "== Installing Microsoft Edge"
    mkdir -m 700 "$tmp/gnupg"
    curl -fsS -o "$tmp/microsoft.asc" https://packages.microsoft.com/keys/microsoft.asc
    fingerprint=$(primary_fingerprint "$tmp/microsoft.asc")
    if [ "$fingerprint" != "$EDGE_KEY_FINGERPRINT" ]; then
        echo "error: https://packages.microsoft.com/keys/microsoft.asc holds key ${fingerprint:-(none, or more than one)}, not Microsoft's $EDGE_KEY_FINGERPRINT - no keyring or apt source was written" >&2
        exit 1
    fi
    GNUPGHOME="$tmp/gnupg" gpg --batch --dearmor <"$tmp/microsoft.asc" | sudo tee /usr/share/keyrings/microsoft-edge.gpg >/dev/null
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-edge.gpg] https://packages.microsoft.com/repos/edge stable main" \
        | sudo tee /etc/apt/sources.list.d/microsoft-edge.list >/dev/null
    apt_update
    sudo env DEBIAN_FRONTEND=noninteractive apt-get "${APT_OPTIONS[@]}" install -y --no-install-recommends microsoft-edge-stable
else
    echo "== Microsoft Edge already installed, skipping"
fi

# --- Firefox + geckodriver: conda-forge via a standalone micromamba binary ---
# Unpinned (agent, 2026-08-26), unlike toolchain/versions.toml's MicroPython pin (Part H.7). Delete
# CROSS_BROWSER_DIR below to force a fresh pull.
CROSS_BROWSER_DIR="${CROSS_BROWSER_TOOLCHAIN_DIR:-$HOME/cross-browser-toolchain}"
FIREFOX_BIN="$CROSS_BROWSER_DIR/mamba_root/envs/ff/bin/firefox"
GECKODRIVER_BIN="$CROSS_BROWSER_DIR/mamba_root/envs/ff/bin/geckodriver"

if [ ! -x "$FIREFOX_BIN" ] || [ ! -x "$GECKODRIVER_BIN" ]; then
    echo "== Installing real Firefox + geckodriver from conda-forge (via micromamba)"
    mkdir -p "$CROSS_BROWSER_DIR/bin"
    micromamba_bin="$CROSS_BROWSER_DIR/bin/micromamba"
    # A binary an older, unchecked run left is checked too, and fetched again unless it is the pinned release.
    if ! { [ -x "$micromamba_bin" ] && echo "$MICROMAMBA_SHA256  $micromamba_bin" | sha256sum -c --status -; }; then
        partial="$micromamba_bin.part"
        curl -fsSL -o "$partial" "https://github.com/mamba-org/micromamba-releases/releases/download/$MICROMAMBA_VERSION/micromamba-linux-64"
        if ! echo "$MICROMAMBA_SHA256  $partial" | sha256sum -c --status -; then
            echo "error: micromamba $MICROMAMBA_VERSION's download does not have the pinned SHA-256 $MICROMAMBA_SHA256 - nothing was installed" >&2
            exit 1
        fi
        chmod +x "$partial"
        mv -f "$partial" "$micromamba_bin"
        partial=""
    fi
    MAMBA_ROOT_PREFIX="$CROSS_BROWSER_DIR/mamba_root" "$micromamba_bin" create -y -n ff -c conda-forge firefox geckodriver
else
    echo "== Firefox + geckodriver already installed, skipping"
fi

echo "== Cross-browser toolchain ready:"
echo "   Xvfb:            $(command -v Xvfb)"
echo "   WebKitWebDriver: $(command -v WebKitWebDriver)"
echo "   Microsoft Edge:  $(command -v microsoft-edge-stable)"
echo "   Firefox:         $FIREFOX_BIN"
echo "   geckodriver:     $GECKODRIVER_BIN"
