# 2026-10-06T07:24:05Z — failed rows moved before their re-runs

- `b0/firmware_build_verify.log` (3 of 6 devices) and `gate-a/firmware_build_verify.log`, `gate-a/toolchain_test.log`:
  the baseline harness built firmware without the toolchain lock at 07:19:56 while family (a)'s locked build and
  `setup_toolchain.py test` ran; each wiped the other's `mpy-cross/build` (`genhdr/qstrdefs.generated.h` missing). All
  three passed when re-run alone.
- `gate-b/L1_test_sh_gc_default.log`: `tests/test_uart_comm_hazard.py` `_hammer_faulted` retention bound (register X01);
  the row passed when re-run alone.
- Each `results.jsonl` is the row file as it stood before the re-runs.
