R3 lane M hand-back, written by the agent (Wed Nov  4 19:17:05 UTC 2026)

Worktree `S/wt-r3`, branch `audit/r3`, from `17688315`. Every run went through `S/u35/lead/run.sh`, one at a time.
The tree is clean apart from my one commit (`git status`: only the `node_modules` link, never staged). Working
records: `S/u35r/r3/m/` (`coverage.md`, `plants.md`, `twin.md`, `twin_record.json`, `heap.md`, `probes.md`, and
`data/` with each run's raw results). `m/ftmp/` is deleted, and so are the plant snapshot and copy root in `/dev/shm`.
Nothing touched a board or the host's network config. Nothing was pushed.

## Totals

- Runs: 28 labels. The six brief runs took about 2.2 h of machine time; the reproductions about 0.8 h; A1 about 0.2 h.
- Plants: 72 planted, 69 red, the twin gate's control green, 2 survivors: 1 gap and 1 below its test's stated
  granularity.
- Coverage: 13 unexecuted src/ lines beyond the tracer artefacts, 1 of them a gap. 6 generated lines, all guards.
  2,605 host-chain lines, each with a reason. Dead lines: none.
- Twin runner: 126 instruments, 68 pass, 58 exception (19 bench, 39 reds). Of the reds: (a) 0, (b) 31, (c) 8. One (c)
  is a test defect, root-caused.
- Heap probe: 94 files, none grows per test. Probes: 8 on the twin, 5 proposed fidelity rows (A10).
- A1: commit `26705ef8`, +121 / -12. Gaps for the lead: 3.

## The runs (label, rc, wall clock) and what each closes

| # | label | rc | wall | what |
|---|---|---|---|---|
| 0 | `r3m_rebuild` | 0 | 6 s | rebuild.sh on the final tree |
| 1 | `r3m_collect` | 0 | 2 s | `pytest tests_hardware --collect-only`: 234 collected, 203 selected, 31 deselected by the wear gates, **0 errors**. Closes P2's collection half. |
| 2 | `r3m_cov` | **3** | 864 s | `scripts/test.sh --coverage`: every test passed (129 files, 6,786 tests_scripts tests, 5,441 MicroPython tests). rc 3 means only "coverage report not rendered": `uv run`'s offline cache in this sandbox lacks `coverage==7.16.2`, class (c), the sandbox. |
| 2a | `r3m_cov_render` | 0 | 5 s | the kept raw dumps rendered with the shared venv's coverage 7.16.2, outside the tree |
| 2b | `r3m_e51` | 0 | 1 s | e51_sweep's own functions over src/ and the generated modules; its self-test passes. Classes in `m/coverage.md`. Closes OR16 (3), OR22, OR23 and OR25 (3), with gap G1. |
| 3a | `r3m_plant_check` | 0 | 10 s | snapshot; every anchor matched its count; plant.py's selftest passed |
| 3 | `r3m_plant` | 0 | 2,149 s | the plant run (`m/plants.md`). Closes OR16 (4), OR19 (3) and OR21 (1), with gap G2. |
| 3b | `r3m_fram_budget`, `r3m_fram_budget2` | 0 | 0-1 s | measured the FRAM budget's figures, planted and unplanted, to read the `named.fram_alloc` survivor |
| 4 | `r3m_twinrec` | 0 | 2,097 s | `scripts/record_twin_instrument_runs.py`, both stages. Its JSON moved to `m/twin_record.json`, with the classed reasons. Closes OR29.a (4). |
| 4a | `r3m_twinrec_texts` | 0 | 2,097 s | the runner's own loop again, keeping each failure's text. Every red was reproduced here. |
| 4b | `r3m_listener_repro` | 0 | 20 s | 20 back-to-back runs of `flash/test_modlwip_listener_close.py --twin`: 19 red, EADDRINUSE |
| 4c | `r3m_voc_repro1`, `r3m_voc_repro` | 0 | 77 s, 386 s | the SGP40 VOC quality test at 32768: 2 of 15 red, "algorithm looks frozen" |
| 5 | `r3m_heap` | 0 | 367 s | the per-file live-heap probe (`m/heap.md`). Closes OR38's heap half (R1's B36 carry). |
| 6 | `r3m_probes` | 0 | 35 s | the bench's eight probes on the twin, both stages, diffed against the campaign's silicon output (`m/probes.md`). Closes P6. |
| A1 | `r3m_a1_tp_green`, `_tp_probe`, `_tp_green2`, `_tp_red3`, `_dns_green`, `_dns_red`, `_dns_red2`, `_lint`, `_mypy`, `_final` | 0 | 9-155 s | A1, below. `_tp_red` and `_tp_red2` (0 s) did not run the test: the first output was filtered away, the second found the generated tree stale after the src plant. `_tp_red3` rebuilt first. |

## Gaps (the evidence, then the proposed test or fix in one line)

- **G1, coverage:** `src/asy_scd30_driver.py:313` (`results["ContMeas"] = FAILED`) is unexecuted.
  - Its direct test went with `dddb3902`: it dropped the bus with `deinit()`, a no-op since then.
  - The path is reachable: the snapshot reads, then the stop command's write is refused (`:668-672`).
  - Proposed test: in `tests/test_asy_scd30_driver.py`, ContMeas False with the snapshot answered and the address NAKed
    (`nak_addresses`) before the stop command; it answers `Failed` and logs one E CHIP_SET.
- **G2, plant survivor `r3.i2c.stretch_yield`:** `await asyncio.sleep_ms(1)` in `_scl_released()`'s awaited branch, made
  `pass`, stays green at both stages.
  - The held-SCL tests reach the wait and its timeout, but none checks that another task runs meanwhile.
  - So a runtime clear could spin up to `timeout_us` (50 ms by default) per wait while holding the loop (F.3; the
    routine's own comment, `src/asy_i2c_driver.py:35-37`).
  - Proposed test: in `tests/test_asy_i2c_driver.py`, a runtime `clear()` whose SCL reads low lets a sibling task run
    before it returns `_REC_SCL_HELD`.
- **G3, twin runner, class (c), a test defect:**
  - `tests_hardware/device_scripts/listener_close_leaves_the_pcb_pools.py:27` uses `_PORT = 50100`, which is inside the
    host's ephemeral range (32768-60999).
  - The twin half's bind without SO_REUSEADDR (`_port_held()`) meets a TIME_WAIT connection there and gets EADDRINUSE
    (98). The connection is left by its own round trip within 60 s (19 of 20 back to back), or by any earlier
    connection whose ephemeral port was 50100 (the recorder's -1 run).
  - Silicon is not affected.
  - Proposed fix: the twin half uses a port below the ephemeral range.

Not gaps:
- The `named.fram_alloc` survivor is below its test's stated granularity (`m/plants.md`, survivor 1).
  - A per-chunk-write plant adds about 200 B, inside the 11 % headroom left after B3 lowered the blank setup to
    26,464-26,944 B (budget 30,000 B).
  - The test's own target is caught: a 16 B allocation per CS cycle prices the valid setup at 23,232 B (budget 23,000)
    and the first blank setup at 30,464 B.
- No heap probe file grows per test.
- No twin red is a product defect.

## Fidelity rows for the fix round (A10, rows only, `m/probes.md` gives the text)

1. **BMP3XX STATUS:** reading a DATA register clears drdy (DS001 Table 27; bench 0x10). The twin keeps it set (0x70),
   so in the twin the driver's STATUS poll always reads ready. Open: a twin correction.
2. **BMP3XX PWR_CTRL:** the bench reads 0x13 during a forced conversion and 0x03 after; the twin reads 0x00 for both.
   Open: a twin correction for the enable bits.
3. **BMP3XX OSR after 0xB6:** the bench part (id 0x50) reads 0x00; both datasheets and the twin say 0x02. The existing
   row ("the reset as on silicon", `digital_twin/README.md:239`) is stale for OSR. To settle on the bench.
4. **SGP40 serial:** the datasheet (3.4) and the bench give the same three words on every read; the twin draws fresh
   random words per read (`digital_twin/_sgp40_chip.py:91-94`). Open: a twin correction.
5. **SCD30 read before any command:** the bench reads 0xDD bytes, the twin zeros. Accepted: no driver path does it.

The FRAM WEL, scheduler-drop and country-code differences are already covered by existing rows.

## Dead lines

None in src/, the generated modules or the host chain. No line was removed. The 25 stale e51 verdicts are sites that
R1 and R2 removed, or that their tests now execute (the subtraction).

## A1: commit `26705ef8` on `audit/r3`

Subject: "U35: a full soft-callback queue and a DNS flood at the hotspot each get their twin test". It changes two files,
+121 / -12.

**`tests/test_digital_twin_timer_pool.py` (+99 / -3)**
- The patch's full test, in its current form:
  - `_SPELL_CALLBACKS`, `_FAST_PERIOD_MS`, `_count_fires`, `_error_counts`, and `_until`'s `bound_ms`;
  - `_HEALTH_FIELD`, `_read_after` and `_readers`, taken from before `80b513b5`, which removed them with the reader
    test.
- On the unplanted tree as patched, the test was red at both stages (`r3m_a1_tp_green`):
  - SGP40 moved 0 → 1, a W 65 SGP_NO_BACKUP (`r3m_a1_tp_probe`);
  - the cause: R1's SGP40 logs its boot-owed "No backup found!" at its first restore, which now lands after the
    snapshot;
  - the fix, in the test: each reader's first read comes before the counts are taken (decision, agent, 2026-11-04,
    stated in the commit). The W is designed behaviour, so no product change.
- Then green on all six devices at both stages (`r3m_a1_final`).
- Seen red on a planted break (`r3m_a1_tp_red3`): a BMP3XX trigger made a one-shot re-armed from its own callback.
  Both stages fail with "bmp3xx never read again after the spell".
- Reverted, rebuilt, green.

**`scripts/_digital_twin_scenarios.py` (+22 / -9)**
- The DNS flood went in, inside the boot the exclusive port-53 leg already makes. That leg's only scenario is
  `wifi_sta_failure_falls_back_to_hotspot_and_drives_the_real_dns_server`.
- After the existing checks it sends 200 three-byte datagrams. It then expects the next query answered and DNSSRV's
  count unchanged.
- The query loop became `_dns_answer()`, shared by the first query and the one after the flood.
- No new boot, no timeout change, no new file.
- Green at both stages (`r3m_a1_dns_green`). Seen red on two planted breaks:
  - logging every dropped query (`r3m_a1_dns_red`): "no answer to a query after the flood", because the persisted
    writes stall the server;
  - logging only the first (`r3m_a1_dns_red2`): "DNSSRV's count 0 -> 1".
- With the flood the scenario took 55.6-55.9 s per stage.

Checks run while fixing:
- lint_direct: ruff, shellcheck, actionlint, zizmor, the gc sites;
- the three mypy passes;
- `tests_scripts/test_digital_twin_scenarios.py`, `test_comment_block_cap.py` and `test_microtest.py`: 786 passed.

Not run: the full gate, per the brief.

## Decisions taken (agent, 2026-11-04)

- **Plant scope:**
  - Re-plant each record plant whose enclosing function changed since `2e826c28` (the record's commit), or one of whose
    catching tests changed or went.
  - Adapt the 7 whose anchor moved. Plant 7 of R1's own complex-measurement sites.
  - Trigger 6 check-style tests whose self-bite test `95e4fbde` removed and whose subject R1 changed.
  - The other bite-removed convention checks are not triggered, by the owner's "the sensitivity proof is done once"
    and the straightforward-test scope.
  - 53 plants carried over unchanged. Details: `m/plants.md`.
- **The twin runner's `--reasons`:** the 35 kept reasons, plus a placeholder for every other path, so that the record
  is written in one run. Each placeholder was then classed after reproduction, and the classed reasons replaced them in
  `m/twin_record.json`. Reasons updated against the R0 text:
  - `test_system_commands`: the erase cuts now pass;
  - `test_heap_layout`: 32768 only, the live arm;
  - `test_sensor_accuracy`: the VOC index stays constant, not only at its floor;
  - `test_uart_crossover`: the ring-size failure up front.
- **Coverage:** rendered with the shared venv's coverage, because `uv run`'s offline cache could not resolve it. The
  host chain is classed per file, with the error paths named.
- **A1:** the reader-first-read wait above.
- **A2:** I kept the ACTION_LIST cut. The record is in `m/`, not committed.

## Findings outside my deliverable

- (c) The coverage render's dependency is missing from the offline uv cache in this sandbox.
  - `scripts/test.sh --coverage` exits 3 here even when every test passes.
  - CI is unaffected (it has network).
- For round 1: `flash/test_uart_crossover.py::test_no_frame_is_lost_while_interrupts_are_off` fails up front on
  silicon, as in the twin, until `devices/dev.toml` sizes `rx_ring`. This is already a BACKLOG entry.
- (b) `flash/test_heap_layout.py` fails at 32768 only (55 blocks above the high band, bound 32).
  - The script sets -1 itself, but the runner applies the stage before the script's imports
    (`digital_twin/run_device_script.py:127`).
  - The mechanism is inferred, not measured on its own.
  - At -1 both arms now hold; at R0 they did not.
- (b) The SGP40 VOC quality check's twin flake: an integer index constant over the 8 post-blackout samples, at 2 or 5,
  not only at the floor (2 of 15 at 32768).

Nothing of mine is running.

## Fix round (written by the agent, Wed Nov  4 21:14 UTC 2026)

`FIX_BRIEF.md`'s twelve items, then R3's gate. Six commits on `audit/r3` on top of `26705ef8`, head `5613c35e`; the tree
is clean; nothing pushed. Every new or strengthened test was seen red on the named plant, at both GC stages unless it
is a host test, then green; each plant was reverted (`git checkout`) and the tree rebuilt.

| # | item | commit | +/- | red seen on |
|---|---|---|---|---|
| 1 | ISL29125 `test_start_timer_degrades_when_the_alarm_pool_is_exhausted` takes its siblings' assertions (period -1, no callback, ErrCount 0) and `irq_handler == reader._on_irq` | `cffecb57` | +4 / -1 | the INT handler wired as a lambda around `_on_irq` (`r3m_fx1_red`): the old `is not None` passed it |
| 2 | twin BMP3XX power cycle: ErrCount unchanged with no E or W entry, OSR/CONFIG at `_bmp3xx_chip`'s own `_OSR_RESET`/`_CONFIG_RESET` (no literal); the comment's "(x1, no IIR)" now "reset values" | `cffecb57` | +7 / -3 | an `err_s` on every read (`r3m_fx2_red_e`, the old W-only check passed it); OSR rewritten to 0x05 every cycle (`r3m_fx2_red_reg`) |
| 3 | `tests_scripts/test_record_twin_instrument_runs.py`: the five behaviour tests from `497b3eda` (helper `:23-48`, tests `:83-138` but `test_every_exception_names_its_reason`), no committed record read | `1c949aae` | +96 / 0 (new file) | five breaks in the runner at once, each failing its own test (`r3m_fx3_red`, 5 failed): all of a module's failures charged to each script; the staged-line check dropped; the plugin's `gc_threshold` set dropped; the API hash reading the script alone; the missing-port message changed |
| 4 | twin SCD30: a missed RDY edge with the line high is read at the `_trigger_half_ticks`-th base tick, not before, with no entry | `cffecb57` | +37 / 0 | the fallback's `_read_event.set()` made `pass` (`r3m_fx4_red`: due at none of 6 ticks) |
| 5 | SCD30 ContMeas False, the stop command NAKed after the snapshot: `Failed` and one E CHIP_SET | `cffecb57` | +19 / 0 | `results["ContMeas"] = FAILED` made `VALID` (`r3m_fx5_red`) |
| 6 | I2C: a runtime `clear()` with SCL held lets a sibling task run before it returns `_REC_SCL_HELD` | `cffecb57` | +25 / -1 (and `cancel` imported) | `r3.i2c.stretch_yield` (`r3m_fx6_red`: "the sibling ran 0 times") |
| 7 | `test_the_lowered_uptime_limit_leaves_the_output_unchanged` goes, with `_UPTIME_GAMMA`/`_UPTIME_GATING`, only it used | `f26f6ada` | 0 / -27 | removal; no doc line names it outside `audit/`. Knowledge: it compared the C reference's uptime saturation (F16(32766)) with the port's lowered 16383 limit; the limit went in `1206e862`; its code is at `26705ef8` |
| 8 | the flash loop-lag test in `PERMANENT_SKIPS` with its reason | `8882a25b` | +2 / 0 | no new test; a misspelt node id fails the existing `test_the_permanent_skip_names_a_test_that_exists` (`r3m_fx8_red`), green after |
| 9 | `uart_comm_hazards.py`: `_evidence()` (both drivers' `rx_overruns`/`discarded_bytes`, each link logger's held entries) on h1a, h2, the stalled TX, and a race or field sweep whose clean exchange failed | `8882a25b` | +21 / -6 | test-side only; one twin run (`r3m_fx9_twin`): `test_comm_hazards_are_serialised_refused_or_recovered` 2/2 passed, and the facts carry the evidence (e.g. the stalled TX's responder log at count 27, `discarded_bytes` [0, 55]) |
| 10 | listener-close twin half on port 30100 | `8882a25b` | +1 / -1 | **stopped: larger than the brief** (below) |
| 11 | fidelity rows 1-5 in `digital_twin/README.md`'s table | `6378bb60` | +5 / 0 | rows only. Row 3 stands beside `:239`'s "the reset as on silicon", now contradicted for OSR, unchanged as asked |
| 12 | `src/asy_scd30_driver.py:171` `Datasheets/` → `datasheets/` | `6378bb60` | +1 / -1 | comment; bytecode identical (`r3m_fx12_mpy`: `cmp` equal, 12,472 B) |
| — | the soft-callback queue test's ignore codes in ascending order | `5613c35e` | +1 / -1 | my A1 defect (class (b)), found by the gate's first -1 run (`test_suppression_form.py`); `r3m_gate_fix_supp` green |

**Item 10, stopped.** The port change is in (30100: below 32768-60999 and every band in `tests/_port_bands.py`, no fixed port
of the tree near it), and it removes the clash with another connection's TIME_WAIT on an ephemeral 50100. But ten
back-to-back twin runs stay red from the second on (`r3m_fx10_try`: 1 green, 9 red, EADDRINUSE): the script's own
round trip closes the accepted connection first, so the TIME_WAIT pcb sits on its own port 30100 and refuses the next
run's no-SO_REUSEADDR bind for about 60 s. Measured, not committed: closing the client before the accepted connection
in `_round_trip()` (a 3-line reorder; rp2 never reaches it, its connect is refused first) makes all ten green
(`r3m_fx10_probe`). For the lead: admit the reorder, or keep the port alone.

**Gate** (each step alone; wall clock from `run.sh`, peak RSS the largest waited-for descendant, `resource.getrusage(RUSAGE_CHILDREN)`):

| step | label | rc | wall | peak RSS | result |
|---|---|---|---|---|---|
| lint (ruff, shellcheck, actionlint, zizmor, gc sites) | `r3m_gate_lint` | 0 | 9 s (4 s lint) | 233 MB | clean |
| typecheck (three mypy passes) | `r3m_gate_mypy` | 0 | 21 s | 330 MB | 276 / 312 / 59 files, no issues |
| `scripts/test.sh` at -1, first | `r3m_gate_test_m1` | **1** | 700 s | 749 MB | one tests_scripts failure, the ignore-code order above |
| `scripts/test.sh` at -1, after `5613c35e` | `r3m_gate_test_m1b` | 0 | 694 s | 749 MB | files 137 passed, 0 failed, 80 skipped, 6 deselected; tests_scripts 6,792 passed; MicroPython tests 5,832 passed |
| `GC_THRESHOLD=32768 scripts/test.sh` | `r3m_gate_test_32768` | 0 | 720 s | 749 MB | the same counts |
| dev twin suite / harness at -1, then at 32768 | `r3m_gate_twin` | 0 | 659 s / 58 s, 632 s / 58 s | 52 MB each | suite 329 + 15 checks passed at each stage; harness 1 passed (the hotspot DNS scenario with the flood), 1 skipped (arzi-only), 65 deselected (shared port 53) |

npm not run (no `js/` or `tests_js/` change). Sizes (`r3m_sizes`, `m/sizes_head.tsv` at `5613c35e`): 28 src modules,
every line count and bytecode size equal to `17688315`'s (194,883 B in all); no module grew.
