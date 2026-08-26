#!/usr/bin/env bash
# Installs the three non-Chromium browser engines scripts/cross_browser_smoke.mjs drives
# (WebKitGTK, real Microsoft Edge, real Firefox) - idempotent, safe to re-run. Playwright's own
# Chromium (already used by the rest of tests_js/) is installed separately via `npx playwright
# install chromium`, unrelated to this script.
#
# Why these three specific install paths, not the "obvious" one for each:
# - WebKit: `webkit2gtk-driver` (ships /usr/bin/WebKitWebDriver, a real W3C WebDriver server for
#   WebKitGTK) is a plain apt package - no alternative needed.
# - Microsoft Edge: Microsoft's own apt repo (packages.microsoft.com) ships a real Linux Edge
#   build. Playwright can drive it directly via `chromium.launch({executablePath: ...})` (same
#   Blink/CDP protocol as Chromium), so no separate WebDriver server is needed for this one.
# - Firefox: Ubuntu's own `firefox` apt package is a snap-only stub (fails outright without a
#   working snapd, which this CI runner/most containers don't have) and every other usual source
#   (Mozilla's own CDN, the mozillateam PPA, Playwright's own bundled build) is blocked by this
#   project's outbound network policy where this was first verified. conda-forge (via
#   conda.anaconda.org, a different distribution channel entirely) packages a real, current
#   Firefox plus geckodriver (Mozilla's own official WebDriver server) and was reachable - see
#   SPECIFICATION.md Part H.7 for the full investigation trail.
set -euo pipefail

# --- WebKit: webkit2gtk-driver + xvfb (headless WebKitGTK needs a virtual display) ---
if ! command -v WebKitWebDriver >/dev/null 2>&1; then
    echo "== Installing webkit2gtk-driver + xvfb"
    sudo apt-get update
    sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends webkit2gtk-driver xvfb
else
    echo "== webkit2gtk-driver already installed, skipping"
fi

# --- Microsoft Edge: Microsoft's own apt repo ---
if ! command -v microsoft-edge-stable >/dev/null 2>&1; then
    echo "== Installing Microsoft Edge"
    curl -sS https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | sudo tee /usr/share/keyrings/microsoft-edge.gpg >/dev/null
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-edge.gpg] https://packages.microsoft.com/repos/edge stable main" \
        | sudo tee /etc/apt/sources.list.d/microsoft-edge.list >/dev/null
    sudo apt-get update
    sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends microsoft-edge-stable
else
    echo "== Microsoft Edge already installed, skipping"
fi

# --- Firefox + geckodriver: conda-forge via a standalone micromamba binary ---
# Deliberately unpinned (unlike toolchain/versions.toml's strict MicroPython pin) - this installs
# whatever conda-forge currently publishes as "firefox"/"geckodriver". Acceptable for a browser-
# engine-diversity smoke check (SPECIFICATION.md Part H.7's "Coverage depth" decision); bump
# CROSS_BROWSER_DIR below (or just delete it) to force a fresh install if conda-forge's build ever
# needs re-pulling.
CROSS_BROWSER_DIR="${CROSS_BROWSER_TOOLCHAIN_DIR:-$HOME/cross-browser-toolchain}"
FIREFOX_BIN="$CROSS_BROWSER_DIR/mamba_root/envs/ff/bin/firefox"
GECKODRIVER_BIN="$CROSS_BROWSER_DIR/mamba_root/envs/ff/bin/geckodriver"

if [ ! -x "$FIREFOX_BIN" ] || [ ! -x "$GECKODRIVER_BIN" ]; then
    echo "== Installing real Firefox + geckodriver from conda-forge (via micromamba)"
    mkdir -p "$CROSS_BROWSER_DIR/bin"
    micromamba_bin="$CROSS_BROWSER_DIR/bin/micromamba"
    if [ ! -x "$micromamba_bin" ]; then
        curl -sSL -o "$micromamba_bin" "https://github.com/mamba-org/micromamba-releases/releases/latest/download/micromamba-linux-64"
        chmod +x "$micromamba_bin"
    fi
    MAMBA_ROOT_PREFIX="$CROSS_BROWSER_DIR/mamba_root" "$micromamba_bin" create -y -n ff -c conda-forge firefox geckodriver
else
    echo "== Firefox + geckodriver already installed, skipping"
fi

echo "== Cross-browser toolchain ready:"
echo "   WebKitWebDriver: $(command -v WebKitWebDriver)"
echo "   Microsoft Edge:  $(command -v microsoft-edge-stable)"
echo "   Firefox:         $FIREFOX_BIN"
echo "   geckodriver:     $GECKODRIVER_BIN"
