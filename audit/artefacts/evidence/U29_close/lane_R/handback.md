U29 lane R hand-back. Commit **0e43108** on audit/u29-r (S/wt-u29r, base e27b782, not pushed): 2 files, +108/-6, nothing outside files_R.txt. digital_twin/network.py is untouched: no new knob was needed. I could not write S/u29/laneR/report.md because the harness blocks report files for subagents (the CHECKLIST says the same), so this hand-back is the full record. Logs and times.tsv are in S/u29/laneR/.

Steps:
1. **Pyflakes allowance (applied).**
   - The existing single lifted ruff run now also passes `lint.pyflakes.allowed-unused-imports = []`. There is no second ruff process.
   - `_unused_import_of()` matches the way ruff does: I checked ruff 0.16.10 with a probe file. An entry covers its own name and its submodules, so `a.b` covers `a.b.c`, but `manual_x` does not cover `pkg.manual_x`. A 5-case parametrized test pins this.
   - New test `test_every_allowed_unused_import_is_still_imported_unused` names each dead entry. The docstring names the allowance and stays at 3 lines.
   - All six real entries are live, so there is no dead line for you to remove.
2. **L2 radio rung (applied, test only).**
   - New test: `test_two_failed_joins_re_select_the_radio_once_and_the_link_comes_back`.
   - Scenario: a linked station gets `raise_on["connect"] = (OSError, (5,), _RUNG_AT)`, where `_RUNG_AT` is read from `_RECOVER_DEVICE_AT`, then `disconnect()`.
   - It asserts: STA constructions +1, one `deinit()` (counted by a wrapper on the instance), one W DEVICE_RECOVERY slot, and the link back within a bound derived only from the service's own constants plus the armed tick period.
   - The service's 60 s retry wait would make the run over 2 minutes. A test-local `_SteppedWifiAsyncio` caps each WiFi sleep at `_STA_CONNECT_POLL_S`, and the poll itself keeps its real step. No tunable or Part N row was added.

Deviations, both decided by me (agent, 2026-10-20):
- `set_access_point_up(up=False)` does not drop a held link in the twin, so the test drops it with `disconnect()` and the access point stays up.
- The test runs on the first generated device only (arzi) and skips elsewhere with a named reason. The reason is SPECIFICATION.md E.2.1's: a device-independent mechanism gains nothing from six runs.

Seen failing first, and bites (scratch copies, now deleted):
- Planted allowance entry: fails at `test_ruff_exemptions_live.py:141` naming 'planted_never_imported'.
- Lift removed from the ruff command: all six real entries are named dead.
- Rung bite (`_recover_device()` returning None): "AssertionError: 2 failed joins re-selected the radio 0 times, not once". The first attempt was refused because the copy's generated tree was stale; it passed after regenerating.

Red checks: none.
- The 12 common.md checks plus test_suppression_form.py: 799 passed.
- ruff: clean on both files.
- mypy twin pass: clean after one fix (an unused `type: ignore` became real once I annotated `conn: WifiService`). Host pass: clean.

Silent-failure scan, two new findings, both relayed:
- The twin's `WLAN.connect()` succeeds on an inactive STA where silicon raises `OSError(EPERM)` (cyw43_ctrl.c:637-640). This is safe in src today because `active(True)` always comes first.
- A held twin link survives the access point going down, where silicon's link-down event drops it (cyw43_ctrl.c:402-413).
- Coverage of both modes (a fake answering where silicon raises, a check matching nothing) is otherwise fine.

Relay (S/u29/relay.md `## R`, 7 lines): the commit; the allowance (all live); doc pointers outside my set (SPECIFICATION.md:4362-4363, pyproject.toml:157-158); the access-point deviation; the device choice against E.2.1's wording, which today names only driver-specific scenarios; the two fidelity findings.

Times (before → after, seconds). Everything is within 10%, with zero MemoryError / "memory allocation failed" in any log.

| File | -1 | 32768 | settrace |
| --- | --- | --- | --- |
| integration, arzi (runs the new test) | 111.47 → 118.03, final 118.12 (+6.0%) | 113.50 → 121.56 (+7.1%, 3 heavy at start), final 119.68 (+5.4%) | 114.35 → 121.60 (+6.3%) |
| integration, wozi (skips it) | 22.83 → 22.15 | 23.06 → 22.97 | 23.65 → 23.45 |
| test_ruff_exemptions_live.py | 11.49 / 9.33 cold before; same tree alternated 5.03 → 5.37 mean (+6.7%); pre-commit 5.75 | – | – |

The other four devices at -1 after: 21.6–23.2 s, all skipping the new test.

Runs and exits:
- before: wozi and arzi at -1/32768/settrace, rc 0.
- after: arzi and wozi at all three stages, plus dev, grkizi, klkizi, schlafzi at -1, rc 0.
- final: arzi -1 and 32768, wozi -1, rc 0.
- Bites rc 1, as intended. Checks rc 0. Every run over a minute has its RUNS.md lines. Nothing of mine is running.
