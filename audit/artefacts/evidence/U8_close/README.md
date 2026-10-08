# U8 close: what failed on the way, and why

## `npm run -s lint` and `typecheck` exit 1 with no output (lead's gate commands, d38fceb)

Reproduced (`npmrepro/`): sourcing a second venv's `activate` first runs `deactivate`, which restores the PATH saved
before the lead had prepended Node 24, so `npm` resolved to the host's `/opt/node22`. The project's `devEngines`
(`node >=24 <25`, `onFail: error`) refused it with `EBADDEVENGINES`, and `npm -s` silenced that message. The guard did
its job; the silence came from the lead's `-s`. Both checks pass under Node 24. The gate no longer uses `npm -s`, and
sets PATH after activating a venv.

## The gate (d38fceb)

Both `scripts/test.sh` stages: 88/88 MicroPython files, 3867 tests; `tests_scripts` 2770 passed, 6 skipped (CI's
firmware compiles); zero memory markers, no retried file; the warnings are the known unregistered bench markers. The twin
suite on all six devices: 236-302 checks each, all passed. `npm test`: 1082 passed, 5 skipped, each named in its block
(the same five as U7). Lint, the three typecheck passes (with every Any-baseline entry verified still needed, per-entry
removal probe) and the JS lint and typecheck clean.
