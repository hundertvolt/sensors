# U27 rulings taken by the lead during the waves (after rulings.md R-1..R-25; same form)

- R-27 (agent, 2026-10-15): no lane lets `unix_port_ensure` set up. The shared `/root/pico-toolchain` record names U21's
  `setup_toolchain.py` (sha256 1ad16ee3; the tree's is 4aca53fa, U25's signal hold in `run()`, no build effect), and a
  setup there removes and rebuilds every build dir under the lanes running beside it. T and S run every real
  ensure-calling script (`scripts/test.sh`, the twin runners) with `PICO_TOOLCHAIN_DIR=S/u27tc`: a private copy (micropython
  and build_overrides copied; pico-sdk, picotool and node linked) re-recorded by `setup_toolchain.py test` from `<API>`'s
  inputs (0c0ad52's). B, whose tree edits `setup_toolchain.py`, runs none for real (stubs only). A run that prints
  "rebuilding the Unix ports" is stopped by pid and reported. The lead re-records `/root/pico-toolchain` with `test`,
  nothing running beside it, at `<W1>` (after B's edits) and again before the gate if `<W2>` moved an input. Reversal: drop
  the copy and point the lanes at the shared dir once its record is current.
