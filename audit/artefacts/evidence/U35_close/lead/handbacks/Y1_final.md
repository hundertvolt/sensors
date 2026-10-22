Y1 hand-back (lane Y, block 1). Branch audit/u35-y at 6a59b8e in S/wt-u35y, built from f3fff0e with rebuild.sh. Nothing is uncommitted and nothing is pushed.

**Commits.** Each module left in one commit, together with its baseline line and its `_RESIDUAL` row. None of these four modules had an ANN401 entry.
- 3c70aeb: test_digital_twin_bus_hazard_concurrency. `Coroutine[Any, Any, X]` becomes `Coroutine[object, object, X]`. Its section in digital_twin/typecheck.ini is gone.
- 0135187: test_cross_browser_smoke_probe. The JSON is now read through TypedDicts (`_Definitions`/`_Section`/`_Group`/`_Field`, `_Verdict`/`_Outcome`). The expected probe is now computed from the same JSON file pickProbe() read (a JSON round trip, equivalent content) (agent, 2026-10-21).
- 822db92: tests_hardware/conftest.py. The note fixtures return `_ResultNote`/`_SessionNote` Protocols, the shapes flash/conftest.py already uses. The self-test in test_mypy_any_baseline now uses `scripts._hardware_verdict` as its listed host module instead of `conftest` (no meaning change; it needs a new pick when U37 clears that module).
- e97b709: serving_at_default_gc. `_Route` is now a Protocol inside the TYPE_CHECKING block. The wrapper's first parameter is renamed `self` to `owner`: no positional-only `/`, because the MicroPython parser rejects it (probe: SyntaxError) and ruff rejects the `__x` form (PYI063). The only URL part any route has is `filename`, so the call is unchanged at runtime.
- 6a59b8e: src/asy_system_service.py:228. The comment said read loops still return bool, which is stale (every loop returns None now). It now names the reason that still holds. Comment only, same line count, and the mpy-cross output is byte-identical: 11289 bytes, both sides compiled from the same relative path (S/u35/laneY/mpy/).

**Still listed, with why:**
- **asy_system_service** (:229, :230, :297, :480, :744). Settled under the stubs: `Task` is covariant, so the clean form is the existing TaskStarter alias (Task[None]).
  - Task[object] fails on list invariance at the generated `start_tasks(_collect_task_starters())`. It also fails against the Task[None]-typed doubles at tests/_sensortask_scenarios.py:488 and :1646 and tests/test_digital_twin_sensortask_integration.py:458-461 and :510-514.
  - The TaskStarter form passes the twin pass. It leaves exactly 4 main-pass errors, all in tests/test_asy_system_service.py (:1237, :1922, :2121, :3037), caused by its six `Task[object]` annotations (:1132, :1207, :1922, :2118, :2227, :3031). That file is lane P's.
  - Fact owed to P and the lead: once P moves those six to Task[None], the module leaves, using the TaskStarter form.
- **machine, main pass** (:251, :261, :270, :276, :722, :857, :1483). `_CallLog` entries are heterogeneous tuples; typing them `object` gives 173 errors in 22 other files.
  - :722 and :857 type cleanly as `rp2.DMA` (0 errors, checked), and :1483 could take the overload form the twin uses.
  - Not done: the module stays listed either way, and the edit would mean re-running every importer of machine (agent, 2026-10-21).
- **machine, twin pass** (:134, :422, :467). `I2C.devices` is Any-valued by design. Typing it `_I2CDevice` gives 26 errors: 5 in machine.py (each chip fake implements only part of the protocol) and 21 in tests that reach chip-specific state, most of them in other lanes' files. So the twin pass is not empty, and digital_twin/typecheck.ini's :32 clause and :35-36 comment stay.
- **test_bus_hazard_generated** (:44, :67, :77, :87, :99, :148, :165). A ready diff is at S/u35/laneY/bhg_typed.diff: it uses tests/_twin_devices.py's TypedDicts and renames the SPI loop variable.
  - It leaves exactly 3 arg-type errors (:72, :104, :130). They come from `_bus_hazard_catalog`'s `build_bus_occupants` (:426) and `scenario_each_occupant_never_touches_an_unexpected_address` (:740), which take `list[dict[str, Any]]`.
  - That catalog is Y2's file, so the diff lands in Y2's catalog commit, with the lead handing this file to Y2.
- **Baseline now:** main pass 10 modules, twin pass 1 (machine), host pass 1 (scripts._hardware_verdict).

**Not started: OF-32.** It is left for the next block.
- `_now_us()` (digital_twin/machine.py:930) is `ticks_diff(ticks_us(), _epoch_us)`, so it is valid only for under 2**29 µs (about 537 s) of a link's lifetime.
- :901's `_stall_offset_us` is a second ticks_diff, between two epochs, with the same bound.
- Still owed: the seen-failing test in test_digital_twin_machine.py, paired times, and the twin dev integration at both stages.

**Seen failing and bites:** none. The Any removals are migrations: their proof is the three mypy passes plus test_mypy_any_baseline and test_ruff_exemptions_live.

**Checks:**
- ruff is clean on every file I changed.
- The 12 before-commit checks ran 5 times: 797 passed each time, 0 red.
- scripts/typecheck.sh after every commit: rc=0, 10/10 checks.
- Readers (28 files: the pyproject, ini, conftest, device-script and twin-fake readers, plus the smoke probe itself): 417 passed.
- tests_hardware --collect-only: 196/227 on both base and head.
- No allowlist row orphaned. No relay lines written. No MemoryError and no "memory allocation failed" in any output.

**Effect per mode:** none in STA, AP, Silent, Off or USB, on any device. These are type-only edits; the device script is bench-only and its call is unchanged at runtime.

**Times:**
- typecheck.sh: base 24.4 s; after each commit 25.3, 23.8, 22.9, 22.4 and one untimed run, each from a cold cache.
- Twin bus hazard, head only (annotation-only edit): 151.04 s at -1 and 152.06 s at 32768, against 150.15 and 152.79; 22/22 passed at both stages.

**State for Y2:**
- The worktree keeps a gitignored .venv (a copy of wt-lint's, shebangs rewritten) and a typings/ copy of S/shared/typings. Remove them with literal paths at the lane's end.
- Every run is logged in RUNS.md and exited 0, except that the first driver run's start line was missed (its done line says so). Nothing of mine is running.
