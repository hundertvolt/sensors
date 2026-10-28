# CMr1: tests of a differently wired part run on every device wiring it (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneC/cmr1/`.
This redoes lane C's CM (d24e225, lost) and CM2 (lost, its brief too). The map, not proof:
`S/u35r/recovered/handbacks/CM_final.md` (what CM changed, measured and reverted, and why), `S/u35r/verify/V3.md` rows
99, 123 and 124, and `S/u35r/handbacks_redo/N5r.md` (N5r's picks table and the scanner facts; N5r is in your base).

## The owner's rule (verbatim, `S/u35r/recovered/owner_rulings_after_LN118.md`; binding)
"My words about not having tests arbitrarily fixed for specific configurations or devices still hold. They shall all be
treated the same, only depending on their hardware configuration. But matrix deduplication is something different! If
the pattern is like "the first device runs specific tests, which are always and guaranteed present and always identical
for every device, fully independent from their configuration", and any device could be the first to be tested, then it
is a good thing as it saves time and is not actually device specific." and "So target minimal changes." and "Single
device tests with different wiring should actually be avoided, so these tests should go for all devices."
So: a test whose part is wired differently across devices runs on every device that wires it; a test whose subject is
identical on every device (a mechanism using the device only as a vehicle) keeps its one device. Decide each site by
measurement (what the generated wiring plans and TOMLs actually give per device), not by name.

## Items
1. The pick sites, every one found by search on your base (`device_with(`, `devices_with(`, `generated_devices()[0]`,
   `DEVICE_NAMES[0]`, `_FRAM_DEVICE`, `_driver_specific`, first-device helpers in tests/, tests_scripts/ and the twin
   test files), each classed: differently wired -> every device wiring it; identical -> stays, with the measured reason
   in its comment where none states it. CM's list (CM_final.md) is a map: the integration file's `_driver_specific()`,
   network_neopixel :630, neopixel_wifi's NeoPixel pick, test_fram_less_boot, the scenarios' `_lag_run`, bus_hazard's
   `_FRAM_DEVICE` (10 tests) and its sgp40/scd30 picks, fram, clock_jump, ntp, the scd30 and sgp40 helpers, hot_replug,
   launch. Assertions kept; every per-device list asserts non-empty.
2. CM's three per-device defects, fixed in the tests (each shown first as the failure CM saw):
   (1) an iteration inheriting the previous device's board (`machine.reset_peripherals()` per iteration, or the
   file's existing per-test reset); (2) a port band overrun (reuse ports per word first; if a band must still widen,
   widen it in tests/_port_bands.py with no overlap, test_port_bands green, and name it in the hand-back);
   (3) neighbour chips' timers parking a task on a shared bus (build the bus inside the run, as the `_SHARED` cases do).
3. Cost: no file grows past CHECKLIST 14's bound by booting per scenario where one boot per device job serves
   (CM measured the integration file 165 -> 303 s summed with a boot per scenario: share one boot per device job across
   its driver-specific scenarios, each scenario still independent in what it asserts). Base and head timed back to back.
4. The wiring-contract scanner (tests_scripts/test_twin_wiring_contract.py): each comprehension gets its own scope (the
   false positive CM and N5r found), and a name unpacked from a comprehension (`(x,) = [...]`) is tracked (N5r's blind
   spot). Both seen red first on a scratch file (the false positive flagged by the old scanner and not the new; the
   hidden read missed by the old and caught by the new).
5. SPECIFICATION.md E.2.1's device sentence (the integration file's docstring cites it): hand the sentence back for D3
   with its line; do not edit SPEC.

## Proof and checks
Each changed twin/MicroPython test file on every device it now runs on, at both stages with build-standard directly,
zero memory markers; a bite per widened site: a scratch copy of one device's wiring (a generated plan or TOML in a
throwaway copy, regenerated with `S/u23/rebuild.sh` on that copy) that only the widened test catches; times base and
head back to back. tests_scripts readers of changed files; ruff, the mypy passes (stubs at `S/shared/typings`), the
comment cap, test_citations, test_decision_vocabulary, test_tunables_register, test_port_bands. No scripts/test.sh or
twin CI against the shared toolchain. Port-binding runs in the namespace, nice 19. Past 80 tool calls, commit what is
green at a seam and hand back the rest.

## Not yours
src/, toolchain/, digital_twin/, buildgen/, devices/*.toml (scratch copies only), audit/ records except
audit/b3/matrices.md's pick rows, every allow-list (hand back the row you need). Commit subject `U35 lane CMr1:
<summary>`, the two trailers; do not push. Hand-back: commits; every site with its class and measured reason; the
defects' red and green; times; the scanner bites; the D3 sentence; last line "nothing of mine is running".

## Shell discipline (binding, lead, 2026-10-27)
Run scripts you wrote to files (`bash <file>`, `python3 <file>`), never a `bash -c` holding rm or a nohup chain (a
safety check refused that form once); a deletion is its own command with a literal path or "${var:?}"; a refused
command stops you. A run killed at its timeout must not leave its interpreter running: start it in its own session and
kill the group. Lint with `S/u35/lead/lint_direct.sh` (redo_common.md).
