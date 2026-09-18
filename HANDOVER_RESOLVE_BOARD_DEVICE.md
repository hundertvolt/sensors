# Handover — `resolve_board_device()` consolidation

**Temporary file. Delete it once read; nothing else references it.**

Closes the "still open, not fixed" item in `HANDOVER_HARNESS_AND_HEAP_FRAGMENTATION.md` §1.7.

## What changed

`tests_hardware/harness.py` now imports `detect_pico_serial_devices()` from
`toolchain/setup_toolchain.py` instead of carrying a second, looser copy of device discovery. The
two can no longer drift. Three behaviour changes follow:

- **Identification is by USB vendor ID**, not a bare `ttyACM*` scan, so a non-Pico ACM device can
  never be selected.
- **Two boards attached is a hard error** naming both, mirroring `resolve_pico_device()`, instead
  of a silent `sorted(...)[0]`.
- **No board attached returns `/dev/no-pico-serial-device-detected`**, a path that cannot exist.
  This is deliberate and load-bearing: the `board` fixture skips on an unreachable device and that
  tier is documented as "collectible with nothing attached", so this must not raise — and the
  sentinel means mpremote never opens some other device's port just to discover there is no board.

Naming is unchanged: the returned path is still the `/dev/serial/by-id/...` symlink. Matching those
links by **target** rather than by name also drops the hardcoded `MicroPython_Board_in_FS_mode`
product string. Directories are injectable (`by_id_dir`, `sys_tty_dir`, `dev_dir`), like
`detect_pico_serial_devices()`'s own.

## Proof

**Bench [HW]** — filesystem reads plus one passive port open/close; no board command, no reset, no
flash write. `resolve_board_device()` returns
`/dev/serial/by-id/usb-MicroPython_Board_in_FS_mode_e66130100f372d34-if00`, **byte-identical to the
previous implementation's answer**; it resolves to `/dev/ttyACM0`, `idVendor` `2e8a`, and
`is_device_present()` is `True`. So on this bench's real topology nothing moves.

**Host [SRC]** — `tests_scripts/test_resolve_board_device.py`, 7 tests over fabricated `/sys`,
`/dev` and by-id trees. The bench has exactly **one** serial device attached, so the multi-device
cases cannot be exercised live; that is why the selection logic is proven here instead.

Gates: lint, all three typecheck passes, `tests_scripts` at 1225 passed / 7 skipped.

## Correction to §1.7's framing

§1.7 said the bare `ttyACM*` fallback "could select the Arduino UART peer rather than the Pico".
Tested against fabricated hosts, that is narrower than stated: with **both** devices present the old
code already picked correctly, because the by-id glob is itself Pico-specific and wins before the
bare scan. It only picked a foreign device when **no board was attached at all** — it opened the
peer's port to find that out. Real, but never "drives the wrong board".

The project owner states the failure that actually occurred was re-enumeration of the one board
(`ttyACM0` → `ttyACM1` after a reboot) stranding scripts that hardcode `ttyACM0` — which is what the
by-id name already fixes.

## Open, deliberately not taken

**`scripts/mpremote_connect.sh:8`** — `device="${MPREMOTE_DEVICE:-/dev/ttyACM0}"` is the one
remaining hardcoded node, and the one entry point an erratic re-enumeration can still strand. Not
fixed here because a `scripts/` change requires the two-chroot pre-push gate (CLAUDE.md), which is
the project owner's call, not a drive-by edit. `tests_hardware/README.md` now names it as that
known exposure.
