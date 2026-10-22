#!/usr/bin/env bash
# M.PROC.024: a scratch Unix port with rp2's 2**30 ticks period, built from a copy of the pinned checkout (never written).
# ticks_ms()/ticks_us() start TICKS30_WRAP_IN_MS ms before their wrap (unset: the host's own clock). Audit only, deleted at close.
# Usage: ticks30_build.sh build|check <scratch dir> | probe <scratch dir> <tree> [hold_s] (the OF-32 link probe, real clock).
set -euo pipefail
mode=${1:?build or probe}
scratch=$(realpath -m "${2:?scratch dir}")
repo=$(cd "$(dirname "$0")/../.." && pwd)
src=${PICO_TOOLCHAIN_DIR:-/root/pico-toolchain}/micropython
mp="$scratch/micropython"
bin="$mp/ports/unix/build-ticks30/micropython"
py=/home/user/sensors/.venv/bin/python
period=1073741824  # 1 << 30: rp2's MICROPY_PY_TIME_TICKS_PERIOD (31-bit small ints), as a literal so make's shell needs no quoting

build() {
    case "$scratch/" in "$(realpath "$src")"/* | /root/pico-toolchain/*) echo "refused: $scratch is inside the toolchain"; exit 2 ;; esac
    rm -rf "${mp:?}"
    mkdir -p "$mp"
    # Every port but unix, its prebuilt trees, .git and the four libraries unix never compiles stay behind.
    excludes=(--exclude=./.git "--exclude=./ports/unix/build-*" --exclude=./lib/btstack --exclude=./lib/pico-sdk --exclude=./lib/tinyusb --exclude=./lib/cyw43-driver)
    for port in "$src"/ports/*; do [ "$(basename "$port")" = unix ] || excludes+=("--exclude=./ports/$(basename "$port")"); done
    tar -C "$src" "${excludes[@]}" -cf - . | tar -C "$mp" -xf -
    "$py" -I - "$mp/ports/unix/unix_mphal.c" <<'PATCH'
import sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
for name in ("ms", "us"):
    anchor = "mp_uint_t mp_hal_ticks_%s(void) {\n" % name
    if text.count(anchor) != 1:
        sys.exit("ticks30 patch: anchor %r not found exactly once" % anchor)
    text = text.replace(anchor, "static mp_uint_t ticks30_raw_%s(void) {\n" % name)
text += r"""
// ticks30 scratch patch: one fixed offset per counter so both wrap TICKS30_WRAP_IN_MS ms after their first read.
#include <stdlib.h>
static int ticks30_ready;
static mp_uint_t ticks30_off_ms, ticks30_off_us;
static void ticks30_init(void) {
    const char *env = getenv("TICKS30_WRAP_IN_MS");
    ticks30_ready = 1;
    if (env == NULL || *env == '\0') {
        return;
    }
    mp_uint_t wrap_ms = (mp_uint_t)strtoull(env, NULL, 10);
    mp_uint_t period = MICROPY_PY_TIME_TICKS_PERIOD;
    ticks30_off_ms = period - (ticks30_raw_ms() + wrap_ms) % period;
    ticks30_off_us = period - (ticks30_raw_us() + wrap_ms * 1000) % period;
}
mp_uint_t mp_hal_ticks_ms(void) {
    if (!ticks30_ready) {
        ticks30_init();
    }
    return ticks30_raw_ms() + ticks30_off_ms;
}
mp_uint_t mp_hal_ticks_us(void) {
    if (!ticks30_ready) {
        ticks30_init();
    }
    return ticks30_raw_us() + ticks30_off_us;
}
"""
open(path, "w", encoding="utf-8").write(text)
PATCH
    # The rig's own overrides (safe SIGINT path, GC mark stack, mbedtls flag), written into the scratch tree.
    vars_json=$("$py" -I - "$repo/toolchain" "$mp" "$scratch/build_overrides" <<'VARS'
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import micropython_overrides
print(json.dumps(micropython_overrides.apply_unix_kbd_intr_override(Path(sys.argv[2]), Path(sys.argv[3]))))
VARS
)
    variant_dir=$("$py" -I -c 'import json, sys; print(json.loads(sys.argv[1])["VARIANT_DIR"])' "$vars_json")
    make_vars=(VARIANT=standard "VARIANT_DIR=$variant_dir" BUILD=build-ticks30 "CFLAGS_EXTRA=-DMICROPY_PY_TIME_TICKS_PERIOD=$period")
    LC_ALL=C.UTF-8 nice -n 19 make -C "$mp/ports/unix" -j2 "${make_vars[@]}" > "$scratch/build.log" 2>&1 || { tail -n 30 "$scratch/build.log"; exit 1; }
    if grep -nE '\b(error|warning):' "$scratch/build.log"; then echo "build reported diagnostics"; exit 1; fi
    "$py" -I - "$repo/toolchain" "$mp/ports/unix" "$vars_json" <<'VERIFY'
import json, os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import micropython_overrides
make_vars = dict(json.loads(sys.argv[3]), BUILD="build-ticks30", CFLAGS_EXTRA="-DMICROPY_PY_TIME_TICKS_PERIOD=1073741824")
env = dict(os.environ, LC_ALL="C.UTF-8")
micropython_overrides.verify_unix_kbd_intr_in_build(Path(sys.argv[2]), make_vars, "build-ticks30", env=env)
micropython_overrides.verify_unix_gc_stack_in_build(Path(sys.argv[2]), make_vars, "build-ticks30", env=env)
print("overrides compiled in")
VERIFY
    check
    echo "built $bin"
}

check() {
    "$bin" -c "import time; assert time.ticks_add(0, -1) == $period - 1, 'period'; print('period', time.ticks_add(0, -1) + 1)"
    # The offset: 1500 ms before the wrap at start, past it 1.6 s later, on both counters.
    TICKS30_WRAP_IN_MS=1500 "$bin" -c "
import time
ms0, us0 = time.ticks_ms(), time.ticks_us()
assert $period - 1600 < ms0 <= $period - 1500 and $period - 1600000 < us0 <= $period - 1400000, (ms0, us0)
time.sleep(1.6)
ms1, us1 = time.ticks_ms(), time.ticks_us()
assert ms1 < 200 and us1 < 200000 and 1550 < time.ticks_diff(ms1, ms0) < 1700, (ms1, us1)
print('wrap crossed', ms0, '->', ms1, 'ms;', us0, '->', us1, 'us')"
}

probe() {
    local tree hold probe_py rc=0
    tree=$(realpath "${3:?tree}")
    hold=${4:-600}
    probe_py=$(mktemp "$scratch/of32_probe.XXXXXX.py")  # one file per run: concurrent probes never share it
    cat > "$probe_py" <<'PROBE'
# A twin UARTLink alive past 2**29 us on the 2**30 build, real clock: a byte keeps its wire time, a stall keeps its window.
import sys
import time

import _flash_stall
import machine
from machine import UART, Pin, UARTLink

HOLD_S = int(sys.argv[1]) if len(sys.argv) > 1 else 600
fails = []


def wait_byte(uart, limit_ms):
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < limit_ms:
        if uart.any():
            return uart.read()
        time.sleep_ms(1)
    return None


def stall_burst(label, a, b):
    dropped = b.rx_fifo_dropped
    a.write(bytes(40))
    erases, extra = _flash_stall.FLUSH_ERASES, _flash_stall.FLUSH_EXTRA_PAGES
    _flash_stall.FLUSH_ERASES, _flash_stall.FLUSH_EXTRA_PAGES = 0, 13
    try:
        _flash_stall.stall(0)
    finally:
        _flash_stall.FLUSH_ERASES, _flash_stall.FLUSH_EXTRA_PAGES = erases, extra
    time.sleep_ms(10)
    b.any()
    kept = len(b.read() or b"")
    lost = b.rx_fifo_dropped - dropped
    ok = kept > 0 and lost > 0
    print("%s stall %s: kept %d, lost to the full FIFO %d" % ("PASS" if ok else "FAIL", label, kept, lost))
    if not ok:
        fails.append("stall " + label)
    _flash_stall.windows.clear()


machine.reset_peripherals()
a, b = UART(0, tx=Pin(0), rx=Pin(1)), UART(1, tx=Pin(8), rx=Pin(9))
UARTLink(a, b)
start = time.ticks_ms()
print("period", time.ticks_add(0, -1) + 1, "ticks_ms", time.ticks_ms(), "ticks_us", time.ticks_us())
stall_burst("at 0 s (control)", a, b)
for at_s in list(range(0, HOLD_S + 1, 100)):
    while time.ticks_diff(time.ticks_ms(), start) < at_s * 1000:
        time.sleep_ms(200)
    a.write(b"\x5a")
    got = wait_byte(b, 1000)
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    ok = got == b"\x5a"
    print("%s byte at %d ms (past 2**29 us: %s, ticks_us %d): %r" % ("PASS" if ok else "FAIL", elapsed, elapsed * 1000 > (1 << 29), time.ticks_us(), got))
    if not ok:
        fails.append("byte at %d s" % at_s)
stall_burst("at %d s" % (time.ticks_diff(time.ticks_ms(), start) // 1000), a, b)
print("probe", "FAIL " + ", ".join(fails) if fails else "PASS")
sys.exit(1 if fails else 0)
PROBE
    TZ=UTC TICKS30_WRAP_IN_MS=${TICKS30_WRAP_IN_MS:-300000} MICROPYPATH="$tree/digital_twin:$tree/src:.frozen" \
        timeout $((hold + 120)) "$bin" -X heapsize=16M "$probe_py" "$hold" || rc=$?
    rm -f "$probe_py"
    return "$rc"
}

case "$mode" in
    build) build ;;
    check) check ;;
    probe) probe "$@" ;;
    *) echo "usage: ticks30_build.sh build|check <scratch dir> | probe <scratch dir> <tree> [hold_s]"; exit 2 ;;
esac
