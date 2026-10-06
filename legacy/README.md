# Legacy firmware and snapshots

The code the owner's deployed units run, and one captured board filesystem, kept as reference next to the refactored
firmware in the repository root. Paths below are relative to this directory.

## What this is

Reference only: nothing here is edited, linted, type-checked, tested, built in CI or completed (owner, 2026-09-11,
paraphrase). It may be run in a scratch directory as a reference for published values, with nothing committed (owner,
2026-09-26, paraphrase). Moving it here was the one change it ever got (owner, 2026-09-25: "all legacy code, scripts
and functions should remain in the repo as a reference, but be all located in one /legacy folder, containing
structured subfolders"); every file is byte-identical to its pre-move form.

## `firmware/`

The firmware the legacy units run, on MicroPython **1.24.1** (owner, 2026-09-26: "all legacy real devices run
1.24.1"):

- `firmware/python/CommonDrivers/`, `firmware/python/IndividualDrivers/` and `firmware/python/Manifest/manifest.py`
- `firmware/modules/_boot.py` and `firmware/modules/sensortask-{arzi,dev,neu,wozi}.py`
- `firmware/html_raw/{general,arzi,dev,wozi}/`
- the four `firmware/build-<device>.sh` and `firmware/update_and_install.txt`

How a build runs: each `build-<device>.sh` assembles `python/build/` (the drivers, the manifest and the gzipped
website frozen into `frozen_html.py`), swaps `modules/_boot.py` and `modules/sensortask-<device>.py` into upstream's
`ports/rp2/modules/`, runs `make -C ports/rp2 BOARD=RPI_PICO_W FROZEN_MANIFEST=<path>`, copies `firmware.uf2` and
restores `_boot.py`. It expects `firmware/` to be the `py-include` directory inside a MicroPython checkout; the scripts
pin no MicroPython version.

## `dev_drivers/`

The dev unit's on-device filesystem as captured on 2026-08-27 over `mpremote` (`e05f015`), when that unit still ran
1.24.1: code the repository never otherwise had. `dev_drivers/sensortask-dev.py` is internally inconsistent as
captured (a wrong `asy_FRAM_manager` import name, an SHTC3 that is not fitted, a NeoPixel pin that is not the real
one); `dev_drivers/sensortask_test.py` is the more consistent reference for what was running.

## Baseline

The legacy tree at the repository's HEAD is the comparison baseline for legacy-versus-refactor questions (owner,
2026-09-26, paraphrase).

## Edits after the 2026-07-13 import (`8c4a73d`)

Complete per `git log` over the legacy paths:

- `2bda920` (2026-07-22): the BMP3xx IIR coefficient encoding in
  `firmware/python/IndividualDrivers/asy_bmp3xx_driver.py`, `firmware/modules/sensortask-wozi.py` and
  `firmware/html_raw/wozi/sensorconfig.html`; the only behavioural edit.
- `b6cb852` (2026-08-20): build paths in the four `firmware/build-*.sh`.
- `ba80b9d` and `383d17b` (2026-08-20): attribution comments in `firmware/python/CommonDrivers/captive_dns.py` and
  `firmware/python/CommonDrivers/asy_udp_socket.py`.
- `7a27ca1` (2026-07-13) and `a297b0f` (2026-08-20): the "SUPERSEDED" preamble of `firmware/update_and_install.txt`,
  non-behavioural; its "1.26" is stale, the units run 1.24.1.
