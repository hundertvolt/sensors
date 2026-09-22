#!/usr/bin/env bash
# Installs the three non-Chromium engines scripts/cross_browser_smoke.mjs drives (WebKitGTK, real
# Microsoft Edge, real Firefox) - idempotent, safe to re-run. Playwright's own Chromium comes from
# `npx playwright install chromium` instead and is unrelated to this script.
#
# None of the three channels below is the obvious one for its engine; SPECIFICATION.md Part H.7's
# "Why each engine comes from the channel it does" has the investigation trail for all three.
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
# Deliberately unpinned, unlike toolchain/versions.toml's MicroPython pin (Part H.7). Delete
# CROSS_BROWSER_DIR below to force a fresh pull.
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
