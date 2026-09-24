# Catalog: instrumentation — what measures, and how to rebuild it

**What this is.** The measurement side of this branch's connection-scaling and serving work
(2026-09-22/24): special builds, harnesses, calibrations, hardware tools and the traps that cost
time, including the silicon instrument chain, measurement principles and bench traps of the
2026-09-23/24 hardware sittings (whose handovers are deleted; the results are
`HEAP_FRAGMENTATION_MEASUREMENTS.md` §7R). The tests they suggest are in `CATALOG_UNIT_TESTS.md` §7.
None of it belongs in the everyday suites — too slow, too build-specific, or it needs the
board. Its companion, `CATALOG_UNIT_TESTS.md`, holds the tests that do. Only methods that finally
worked are listed; withdrawn claims and dead ends are one line each in §9.

**Temporary, this session's working catalog only.** Kept current while this work continues (a
instrument added, changed or retired on this topic gets its entry in the same commit), then processed
into the permanent docs and **deleted before the branch merges**. The twin32 tooling itself is never committed
(owner, 2026-09-23); what survives the merge is its documentation (MEASUREMENTS §7Q, §7R, §10). Scratch
entries here carry what is needed to rebuild them for the rest of this session.

---

## 1. The board-faithful twin: a 32-bit, frozen Unix port

**Why.** The ordinary twin (64-bit, not frozen, 16 MB heap) never came near the board's allocation
failures. A 64-bit build doubles dicts, lists and frames but not strings, so it ranks the wrong
allocation first. Not frozen, importing the firmware costs ~541 KB of heap that the board spends in
flash. The 32-bit frozen build has the RP2040's own object sizes — 4-byte pointers, 16-byte GC
blocks — and it reproduced the board's failing call sites and sizes **exactly**: `/status` pieces
~870 B, an errcount entry at 296 B, `/measurements` at 509-614 B, and later the static page's
1,025 B read.

**Build** (a new build dir; the MicroPython checkout itself is never edited):

```
apt-get install -y gcc-multilib            # check: a C program printing sizeof(void*) prints 4 under gcc -m32
cd <toolchain>/micropython/ports/unix
make -j8 BUILD=build-heapprobe32 \
  VARIANT_DIR=<toolchain>/build_overrides/unix_kbd_intr_variant \
  CC="gcc -m32" CXX="g++ -m32" LD="gcc -m32" MICROPY_PY_FFI=0 \
  CFLAGS_EXTRA="-Wno-array-bounds" FROZEN_MANIFEST=<manifest.py>
```

- `MICROPY_FORCE_32BIT` is **silently ignored** by 1.29's Makefile; the first attempt built 64-bit.
  Verify with `file`: `ELF 32-bit LSB pie, Intel 80386`. About 2 minutes.
- The manifest:
  ```
  include("<toolchain>/build_overrides/unix_kbd_intr_variant/manifest.py")
  freeze("<repo>/src"); freeze("<repo>/ext"); freeze("<gen>")
  freeze("<repo>/digital_twin"); freeze("<repo>/frozen_modules"); freeze("<site_dir>")
  ```
  - `<gen>` is a copy of `build/generated_src` with `max_connections=64` patched into
    `sensortask_dev.py`, so admission never caps a sweep.
  - `<site_dir>` holds `dev`'s real website, built with
    `scripts/build_website.sh dev <site_dir>/frozen_website_dev.py` (§3).
  - For a pre-fix arm, freeze a copy of the old `src/` (`git archive <rev> src`) into its own build
    dir, and compare two binaries.
- **Shadow arms**: a file on `MICROPYPATH` still wins over a frozen module of the same name. So
  `MICROPYPATH=<dir>:.frozen` A/Bs one module without a rebuild. Shadow every arm, the control
  included, so the shadow's own compile cost is common to all of them. The same trick on the ordinary
  binary is how "fails when reverted" is proven for unit tests.
- **Never a committed tool or CI gate** (owner, 2026-09-23; `BACKLOG.md` items 44 and 45).

**Calibration to the board** (32-bit twin, shipped code at the time, 12 rounds, failures per run at
N = 4 / 5 / 7):

| twin heap | failures | |
| --- | --- | --- |
| 500k | – / 24 / 36 | too harsh |
| 530k | 11 / 12 / 24 | |
| **560k** | 6 / 7 / 13 | matches the board at 5 and 7 — **the harsher bound** |
| **600k** | 0 / 0 / 2 | **the gentler bound** |

- The board sits between 560k and 600k.
- The heap for an image sized for L connections is `base_k × 1024 − (L − 7) × 2,324`, where
  2,324 B is lwIP's per-connection `.bss` cost from real ELFs.
- F (8 connections) at 560k is 571,116 B; G (16) is 552,524 B.
- The twin's heaps are larger than the board's (F: 187,712 B) because the twin's fake FRAM keeps a
  262,144 B image in the same heap.

**Discount these twin-only effects**:
- An 804 B failure: `network.WLAN` is a Python fake whose 200-slot call-log deque is (200 + 1) × 4 B.
- Allocating fakes: the watchdog's `feed()`, `SPI.write`'s `bytes(buf)`, and the FRAM image.
- A UART 264 B receive that failed only on the 64-bit twin.
- **Under rounds load, the twin is optimistic near the wall by two levels or more.** Pre-fix silicon
  image G failed its first JSON route at N = 10, while the 32-bit twin showed none through 12. The
  throughput-matched twin below closes that gap for peak load.

**The throughput-matched peak twin (2026-09-24).** The board is CPU-bound, serving ~2.2 requests/s
at every limit, so a request lives ~N / 2.2 s and the in-flight live set grows with N. An
unthrottled twin serves 50-100× faster, so its requests hardly overlap and it looks far too good.
- **CPU quota**: once the twin answers `/status`, put its PID in a cgroup v1 CPU controller at
  **3.5 % of one core** (`/sys/fs/cgroup/cpu/twintest`, `cpu.cfs_period_us` 100000,
  `cpu.cfs_quota_us` 3500). Boot runs unthrottled; only serving is throttled. Check that completed
  requests per 60 s land near the board's 121-149.
- **Real admission**: patch `max_connections=int(os.getenv("MAXCONN") or "64")` into the generated
  `sensortask_dev.py` that gets frozen, and set `MAXCONN` to the image's limit.
- **Heap**: calibrate on silicon failures at peak load. For F′ (8 connections) that gives ≈ 564,648 B.
  For H (10 connections) the bracket is 554,000-560,000 B. Other limits follow the 2,324 B per
  connection rule.
- **Scratch** (never committed): `boot_peak.py` (the silicon `_peak_sampler` logic, a rejection
  counter on `_open_conns.increment`, loud `err_s`, dev's site, `COLLECT=1` for the exact live set);
  `drive_peak.py <port> <N> [dur]` (the `--peak` shape: back-to-back clients over the 9-path mix and
  the SGP40 reset PUT every 3 s); `sweep_peak.py <heap> <thr> <Nlist> <tag>` (env `QUOTA`,
  `MAXCONN`, `SETTLE`, `DUR`; one fresh twin per level).
  - `sweep_peak.py` waits 12 s after the load, so the last 10 s `PEAK_SUMMARY` includes every rejection.
  - Its verdict counts host resets beyond the device's own rejections as true failures.
- **Validated**: F′ predicted 0 true failures at 7 and ≈ 0.3 % at 8, and silicon matched both. Host
  refusals equal device rejections exactly (1,336 = 1,336) when the counter is installed at webserver
  creation.
- **Known limit**: below the limit the twin refuses less than the board does (its closes are faster).
  Use it for failure rates and heap, not for refusal percentages.

## 2. The serving sweep in the twin (*scratch*)

Four small scripts, rebuilt from this description:

- **`sweep.py <heap> <threshold> <N,N,…> [rounds] [port] [tag]`.** Env: `TWIN_BIN`, `SHADOW`, `BOOT`,
  `BLOCK`. For each N it:
  - boots a fresh twin (`boot.py --module sensortask_dev --device dev --host 127.0.0.1 --port <p>
    --gc-threshold <t> --duration 600`, cwd = repo root, `MICROPYPATH=<shadow>:.frozen`, `TZ=UTC`);
  - waits until `GET /` answers 200;
  - runs the driver;
  - stops the twin with SIGINT;
  - parses the log for `allocating (\d+)` sizes and `max free sz`.

  Multiply `max free sz` by `BLOCK`, which is 16 on the 32-bit twin and 32 on 64-bit. A hard-coded
  × 32 doubled every 32-bit figure until it was fixed; no committed number was affected. About
  1-1.5 min per level.
- **`drive.py <port> <N> <rounds>`** follows the load-driver rules that proved necessary:
  - one real socket per request;
  - a `threading.Barrier(N)`, so the burst is simultaneous;
  - bodies are **drained, never kept**;
  - **every body is checked against `Content-Length`**, or against the file's known size where none
    is sent, and a short one is labelled `-trunc`;
  - a 1 s settle between rounds, because a slot outlives its response.

  Paths: `/status /sensors /measurements / /networking /system`, plus `/js/app.js` with `WITH_JS=1`.
- **`boot.py`** runs the frozen `run_generic_integration` plus a `micropython.mem_info()` sampler.
  Env: `SAMPLE_MS`, `MAPS`, and `COLLECT=1` for an extra post-collect map.
- **`boot_site.py`** is `boot.py` plus two lines that turned out to be essential:
  - `sys.modules["frozen_html"] = frozen_website_dev`, so the twin serves **dev's real site** rather
    than `html_stub/`'s sub-1 KB page;
  - a wrapper on `print_log.PrintLogHistory.err_s` that prints every call.

  **A failure in the response-write phase reaches only `err_s`** (the FRAM error log) and prints
  nothing at the twin's debug level. Those two gaps together are why the twin missed the static-page
  defect that silicon found.

**Also scratch:**
- `classify.py`: groups `MemoryError` tracebacks by size and the last three frames.
- `maps.py`: tabulates free space, largest run and `placeable(n)` per dump.
- `bodies.py`/`equiv.py`: a sha256 of every route's full body per arm. This is how the fix was proven
  byte-identical on all six routes.
- `bigdumps.py`: spies on `json.dumps` for each route's largest single dump.
- `respcost.py`/`statparts.py`: price one request step by step, as
  `gc.collect(); a = gc.mem_alloc(); …` per step, 3 reps, zero spread. `/status`'s churn went
  70,208 B → 15,648 B.
- `latency.py`: 60 sequential `/status`, median and p90.

**Key results** (32-bit twin, dev's site, `-1`, 12 rounds): see MEASUREMENTS §7Q.12 and §7Q.14.
- **Pre-fix:** the first cut page at N = 6 on the 1,025 B read, on both F's and G's heap — the
  board's own result.
- **Fixed:** clean through 12 on G's heap and through 8 on F's, including with `/js/app.js` in the
  load. The JSON wall comes at 14, with 249-257 B pieces.

## 3. Rules the measurements taught

- **Use the `dev` build's own website.** `dev` carries every module and gets every change first, so
  its site is the largest and bites hardest. Build it with `scripts/build_website.sh dev <out.py>`:
  `index.html.gz` is 9,292 B and `js/app.js.gz` 16,292 B. The `wozi` site (7,175 B) under-reported:
  the first cut page came at 8 instead of 6.
- **A body can fail after its `200`.** Count a request as served only if its body is complete. Make
  every error path visible; in the twin that means printing `err_s`.
- **Allocation size is the variable, not churn volume.** At `gc.threshold(-1)` a loaded heap keeps
  ~100 KB free as small holes and no large run. At the failure instant the twin had 0 holes ≥ 870 B,
  74-95 ≥ 300 B and ~300 ≥ 128 B.
- **`gc.threshold(32768)` hides it.** It collects ~3× per `/status`, which re-places the working set.
  That changes the layout, not the stability.
- **Drive from the host and drain** (Part E.9). A client inside the DUT's heap measures its own
  ~5.5 KB read buffer.
- **Measurement design:**
  - sample at a proven peak;
  - use a non-perturbing instrument (`mem_info(1)` parsed by `tests_hardware/heap_map.py`);
  - report absolute placement capacity (`placeable(size)`), not a percentage;
  - establish the within-setting spread before comparing settings;
  - never let the load scale with the setting;
  - measure transients with a collect first and survivors in a fresh process per repeat;
  - use a monotonicity check as a validity gate: a contiguity figure that rises with N is placement
    luck, reported as inconclusive rather than explained away;
  - never add a transient live set to a permanent (survivor, `.bss`) budget — the first asks "are
    there enough holes of the right size at peak", the second "how much is gone for good";
  - prefer the deterministic quantities where board time is scarce: exact admission, ELF/heap sizes,
    and a wall, which is a step change and so robust to the noise that defeats gradients.
- Ballast guards use the largest free run, not `gc.mem_free()`.

**Principles from the peak-load sittings** (condensed; they hold for any future instrument):
- **Question and pass criterion first.** Stable means zero true failures **and** zero device
  allocation lines, caught-and-logged ones included. A refusal at a saturated ceiling is expected.
  Peak means back-to-back clients at the ceiling plus forced internal work (the hammer test's SGP40
  reset PUT) on the full task graph. Rounds with pauses are typical load, not peak: at 6 they
  overstated free heap by ~20 KB.
- **The verdict and the measurement are separate.** Classify every instrument as invasive or not.
  A collecting sampler may measure but not judge. Take the verdict from the least-instrumented run
  that can give it, and the heap figure from the run that measures it exactly. Two runs are better
  than one approximate run.
- **Controls.** When the instrument could cause the effect, run the same load without it
  (`--peak --no-sampler`). Measure the instrument's own cost: script heap footprint, sampler
  throughput (~10-20 %). Report heap both as measured and production-equivalent.
- **Two views, and a gap is a finding.** Compare host refusals with device rejections, and host 500s
  with device allocation lines (two lines per failure). Check every body, not only the status code.
  Validate the reference too.
- **Verify the object under test**: macros read back, ensemble check, linker heap against its
  prediction, build date from `/system`, static `Content-Length` and `gzip -t`. State the
  percentage base.
- **One fresh boot per data point.** Failures near the wall are probabilistic (4 in 7 boots for F′
  at 8), so one clean run proves little, and a 0 vs 1 difference is chance. Report counts and
  percentages. Zero failures in ~1,350 requests only bounds the rate at ~0.2 %; heap margin is what
  separates neighbouring limits.
- **State the bias direction.** A 5 s snapshot bounds the peak from one side. rp2 has no exact
  end-of-GC signal (no `__del__` on user-class instances, no `weakref`), so a non-collecting
  sampler's heap figure is biased low. Re-derive a tool's printed summary from the raw data when a
  label looks wrong.
- **Evidence hygiene.** Read `errcount` before anything writes. Capture `machine.reset_cause()`
  straight after an unexpected reset. Keep raw output verbatim. Don't edit the tool or the device
  script while chained runs are pending. Restore bench state between runs.

## 4. Allocation need per source: the sieve

**Committed:** `tests_hardware/device_scripts/allocation_need_per_source.py`, parsed by
`heap_map.parse_allocation_need()` and gated by
`tests_hardware/bench/test_serving_heap_at_default_gc.py::test_every_source_and_route_fits_a_small_free_run`.

- **Method.** At each rung k of `(1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32, 48, 64, 96, 128)` blocks:
  1. Fill every free block bottom-up with 1-block tuples. One-block allocations advance the scan
     hint, so they land in address order.
  2. Keep one tuple in every k + 1 and drop the rest, so no free run exceeds k blocks.
  3. Run every source (`status:*`, `maintenance:*`, `errcount:*`, `data:*`, `cfg:*`, `settings:*`)
     and every whole route. Include `route:/`, going through microdot's own `Response.body_iter()`.

  A probe's **need** is the smallest effective run at which it, and every larger rung, is clean.
- **Instrument lessons:**
  - Blockers placed by lowest-fit land in low dust, and holes merge.
  - A `range()` object leaves garbage in the pattern; use a counter.
  - Every line printed on a sieve must be built before it.
  - The fake watchdog allocates: feed it per rung on the twin, per probe on rp2.
  - Exact from ~6 blocks up; below that the readings floor at ≤ 192 B.
- **Gate 480 B.** A rung's measured size wanders: the same `/status` read 336 B and 400 B. 480 B sits
  between rung 24 (384-400 B) and rung 32 (512 B).
- **Results:**

  | | shipped | fixed, twin | fixed, silicon |
  | --- | --- | --- | --- |
  | `/status` | 1,024 B | 320 B | 320 B |
  | `/sensors` / `/measurements` | 768 / 512 B | 256 B | 256 B |
  | every individual source | ≤ 192 B | ≤ 192 B | ≤ 144 B |
  | `/` | 1,536 B | 320 B | not yet probed |

  About 9 s on the twin.

## 5. Running hardware instruments in the twin first

Every hardware tool on this topic was run end to end against the 32-bit twin before it went to a
board, and that caught bugs each time. *Scratch* stand-ins:

- **`twin_wrap.py <device_script>`** repeats `run_generic_integration`'s setup:
  - `prewarm_poll_set()`;
  - the UDP address shim;
  - FRAM/SCD30 state paths;
  - the wiring plan from `build/generated_src/sensortask_<DEVICE>_wiring_plan.json`.

  It then `exec`s the device script's **unchanged** source. With `SITE=1` it aliases dev's site. Run
  it from a directory holding the device's `config_*.cfg`, on port 80.
- **`validate_bench.py <heap> need|sweep`** imports `test_serving_heap_at_default_gc` and runs its own
  test functions with a fake `Board` whose `run_isolated()` runs `twin_wrap.py`.
- **`validate_sweep_tool.py <heap> <levels…>`** does the same for `combined_load_sweep.run_level()`.
  It uses a fake `BenchBridge` and caps the tool's 45 s post-reset settle.
- **Bugs caught this way, before silicon:**
  - the merged-hole sieve;
  - `_open_conns.get_value()` read without `await` — a coroutine is always truthy, so the script
    "saw load" forever;
  - the failure-dump wrapper dropping the `filename` keyword on `_get_static`, which turned every
    `/js/app.js` into a 500.
- **Known limit:** the ordinary twin build admits 64 connections, so it does not model refusals.
  The peak twin (§1) does, through `MAXCONN`.

## 6. Hardware tools (committed; need the board)

- **`tests_hardware/bench/test_serving_heap_at_default_gc.py`** — about 12 minutes, one boot, at
  `gc.threshold(-1)`.
  - The need test (§4).
  - `test_serving_sweep_at_the_reactive_default`: levels 4 … ceiling + 2, 12 rounds each, over 7
    paths including `/js/app.js`. Each body is labelled `-truncated` or `-unframed`.
  - It asserts zero memory markers, `served == min(n, ceiling) × 12`, and that every other request
    was refused.
  - It is driven by `device_scripts/serving_at_default_gc.py`, which detects idle, load and idle
    phases from `_open_conns` (enter at 2 of 3 busy polls, leave after 10 quiet polls, 600 s hard
    window). That script dumps the heap before and after the load and at the instant of each failure
    (at most 3).
- **`tests_hardware/combined_load_sweep.py`** + **`device_scripts/serving_stability_under_combined_load.py`**
  — the per-boot silicon sweep behind every §7R figure. **Removed from the tree 2026-09-24** once the
  limit was settled; last present at commit `4914a25`, and HEAP_FRAGMENTATION_MEASUREMENTS.md §10
  carries its full description. The points that made it trustworthy:
  - **One fresh boot per listed level**, a repeated level being a repeated run; failures near the
    wall are probabilistic, so a single clean run proves little.
  - The idle reference is accepted only as a 200 whose non-empty body equals its `Content-Length`,
    retried: every device-script boot drops and rejoins WLAN at ~6 s, and a reference caught in
    that drop once came back 0 B and made every correct page look truncated.
  - Each request is ok, refused (`is_ceiling_close()`, the hammer test's own classification) or a
    true failure with its reason. **STABLE** = zero true failures, zero device lines matching
    `MEMORY_ERROR_MARKERS`, and the driver thread finished.
  - A torn heap-map capture (`HeapMapError`) is printed and does not kill the level's tally.
  - Five modes: rounds; `--margin` (collect before each map; verdict not evidence); `--peak`
    (back-to-back clients + the SGP40 reset PUT, non-collecting 20 ms sampler, device rejection
    count cross-checked against host refusals); `--peak --margin` (exact live set; verdict not
    evidence); `--peak --no-sampler` (the control).
  - Run against the 32-bit twin first: on the pre-fix firmware it reported UNSTABLE at 8 from its
    host-side body check alone (the device printed nothing), which is why that check exists.
- **The silicon measurement chain around it** (instruments A-I of the peak-load sittings):
  - **A, image verification.** Configure `devices/<d>.toml` and `[lwip]`, then
    `uv run scripts/build_firmware.py dev`. Run `check_lwip_ensemble(macros, max_connections=L)`
    and `read_lwip_macros_from_build()` (every macro equals the firmware's). Read the GC heap from the
    linker as `0x20040000 − __GcHeapStart` and predict it as 187,712 + (8 − L) × 2,324 B; this matched
    to the byte on H, G′, E6, E7 and E6′. On the board, check `/system` `build.buildDate` and static
    `Content-Length`. Keep each `.uf2` aside for reflashing.
  - **B, flash and bring-up** (scratch). Flash with `Board().enter_bootloader()`, wait for
    `picotool info` (≤ 20 s), then `picotool load -x -v`. Bring up with `kick_all_stations()`, a hard
    reset, a 55 s `tail_log` for `WLAN connection established`, then poll `/status` until
    `networking.Connected`. Retry once: the board fell back to hotspot mode three times after a reset.
  - **C, `Board.run_isolated()`**: `mpremote … exec "import machine; machine.WDT(timeout=8000)" run
    <script>`. An 8 s hardware watchdog is armed, and the interpreter is not reset.
  - **D, `device_scripts/serving_stability_under_combined_load.py`** (removed with the tool): sets and prints its gc
    threshold, then starts `sensortask_dev.main()`. In peak mode it wraps `_open_conns.increment`
    as soon as `sensortask_dev.webserver` exists and counts increments above the limit. At 20 s it
    prints `after_boot` and `READY`, then runs a 150 s window with one probe:

    | switch | probe | verdict is evidence? |
    | --- | --- | --- |
    | none (rounds) | `mem_info(1)` map every 5 s | yes |
    | `_COLLECT_BEFORE_SAMPLE` (`--margin`) | the same after `gc.collect()` | no |
    | `_PEAK_SAMPLE_MS = 20` (`--peak`) | `gc.mem_free()` + `_open_conns.value` (plain int, no allocation); a rise ≥ 2 KB counts as a GC; `PEAK_NEW_MIN`, `PEAK_SUMMARY … rejected=`, `PEAK_AT conns=k` | yes, but its heap figure is biased low by up to 15-30 KB |
    | `_PEAK_SAMPLE_MS = 100` + collect (`--peak --margin`) | exact live set per open-connection count | no |
    | `_NO_SAMPLER` (`--peak --no-sampler`) | nothing; `FOOTPRINT` once | yes, the control |
  - **F, analysis.** Percentages are of `mem_info`'s total, which is the linker figure minus 4,352 B
    of GC tables. Device allocation lines ÷ 2 = failures. `_margin_line` takes the settled idle as the
    median of the last third, and the load window as every sample up to the last one below 95 % of it.
  - **G, controls.** An import-only script's `FOOTPRINT` baseline is 52,960 B. The device script
    costs 2,720 B on top, 3,008 B with the rejection counter; production doesn't pay it. Samplers cost
    ~10-20 % of completed requests.
  - **I, evidence.** Read `errcount` before a sitting. `mpremote exec "import machine;
    print(machine.reset_cause())"` straight after a serial I/O error. `journalctl -k` gives USB
    disconnect times.
- **`test_serving_heap_at_default_gc.py`'s failing-sweep report is truncated**: the assertion
  message keeps 2,000 characters, and the host tallies print after it. Use the per-boot tool for levels.
- **`tests_hardware/bench/test_network_resilience.py`**:
  - `test_the_board_holds_exactly_the_connection_ceiling_this_tree_configures`;
  - `test_a_full_ceiling_of_concurrent_requests_is_each_served_a_complete_body`;
  - `test_a_concurrent_page_load_is_byte_identical_to_an_uncontended_one`;
  - `error_log_helpers.assert_no_module_logged_a_new_error`, which snapshots every FRAM module's
    counter.
- **`tests_hardware/bench/test_heap_under_connection_ceiling.py`** with
  `device_scripts/heap_under_connection_ceiling.py` — the heap while a full ceiling is genuinely
  held. Four layered defects, each visible only once the one above was fixed:
  - no connection can be held past ~15 s (`outer_cap_s`; a silent one closes after 5 s), so a 55 s
    hold measured an idle heap — holders now drip a header line and **recycle at 10 s**;
  - started together they expired together (7 → 0 → 7), so each is **staggered** by
    `i × 10 s / N`, and the sampled minimum of the live count is what makes a dump a peak reading;
  - holder threads must be **stoppable and joined**: one that outlived its test caused a
    37-failure cascade in every later network test;
  - `run_isolated()` leaves `main.py` stopped, so the test **restores the board to serving**
    (`kick_all_stations()` → `hard_reset()` → wait for HTTP) in its own `finally`.
  - The device script emitted `<<<MEM …` while `heap_map.parse_labelled()` reads
    `=== MAP <label> ===`: every dump was discarded until the formats were unified.
- **`harness.py`**:
  - `configured_max_connections()`;
  - `discover_max_connections(dwell_s=0.3)` — its dwell must stay under the 5 s idle close;
  - `_wait_for_slots_to_drain` — a slot releases 0.71-0.84 s after the client closes.

## 7. lwIP sizing and connection cost

- **Source of truth** is `toolchain/versions.toml` `[lwip]`: PCB 9, SEG 48, `MEM_SIZE` 12,000
  (sized for `max_connections = 6`), MSS 800, WND and SND_BUF 6,400, among others. The measured
  pattern per limit L: PCB = L + 3, SEG = L × 8, `MEM_SIZE` = L × 2,000.
- **Before the build**, `check_lwip_ensemble()` checks the set.
- **After the build**, `verify_lwip_macros_in_build()` preprocesses a probe against the real
  translation unit and demands a sentinel plus every value. This runs in every `build_firmware()`
  and in CI.
- **Why the override is built the way it is:**
  - `MEMP_NUM_UDP_PCB` and `LWIP_STATS` are bare `#define`s, so they need the header shim.
  - `CFLAGS_EXTRA` loses to the include order on rp2; `MICROPY_BOARD_DIR` is the working redirect.
  - TIME_WAIT connections use the same PCB pool.
  - `LWIP_STATS=1` costs 1,916 B and gives per-pool exhaustion counters (read via `stats_display()`
    in C, which this firmware does not call). Never needed: the serial console's `MemoryError`
    tracebacks named the GC heap directly.
- **Permanent cost, from real ELFs** (`arm-none-eabi-nm`, `__GcHeapEnd − __GcHeapStart`):
  - 196 B per PCB alone;
  - **2,324 B per connection for a coherent ensemble**, the same at every step from 4 to 16;
  - silicon agrees: G has 18,592 B less heap than F, which is 8 × 2,324.
  - Buffer options cost far more: `PBUF_POOL_SIZE` 16 → 32 is 15,644 B.
- **Transient and residual cost, twin:**
  - ~5,170 B live per parked connection after a collect;
  - after 40-80 served requests, a flat 1.5-1.6 KB residue in total, not per connection;
  - `/status` latency at a fixed offered load of 4 is flat at 4.2-4.5 ms, for limits from 4 to 16.
- **Live set at peak, silicon**: each open connection holds ~7.5-8 KB (idle-to-peak drop per open
  connection under the collecting sampler: 45.2 KB / 6 on E6, 53.4 KB / 7 on E7). At 6 there is
  ~21 % free at peak and the largest block is ~1.5 KB; at 7, 14.3 % and 528 B. The wall is the
  `/status` piece of 242-257 B.
- **Saturation**: `_open_conns` also counts connections that are still closing, so back-to-back
  clients see ~70 % refusals at every limit. Throughput stays flat at ~2.2 requests/s.

## 8. Traps

- `mpremote` interrupts `main.py` but does not reset the interpreter. A device script must set
  `gc.threshold` itself, and every output should show `GC_THRESHOLD=`.
- A `pkill -f`/`pgrep -f` wait loop matches its own command line. Wait on a log marker instead.
- Two twins on one port contaminate each other's results. Two suites that bind real ports never
  overlap.
- `scripts/run_digital_twin_ci.sh` rebuilds `frozen_modules/frozen_html.py` with the real site. Run
  ad hoc afterwards, the concurrency files fail on `html_stub/`'s `/style.css`. `scripts/test.sh`
  rebuilds the stub first.
- **Unix port:**
  - no `getsockname()`;
  - `getaddrinfo()` returns a packed sockaddr;
  - `asyncio` has only `Lock` and `Event`, no `Semaphore`;
  - `os.environ` is missing, so use `os.getenv`;
  - `micropython.mem_info()` with any argument prints the full map.
- **Silicon bench**:
  - Every device-script boot drops and rejoins WLAN at ~6 s uptime. A first "is it up" probe can
    succeed on the old link, and a reference fetch in that drop once came back 0 B.
  - Leave > 45 s between a reset and the next `mpremote` attach; a watchdog reset at attach is likely otherwise.
  - After a reset the board may come up in hotspot mode: `kick_all_stations()` + hard reset.
  - A running Python process keeps its loaded code, while each new invocation of a host tool
    re-reads it and its device script, so don't edit either between chained runs.
  - Device scripts build their own `AsyFramManager` over the same FRAM, so `errcount` afterwards is
    context, not evidence. A pair E31 (status byte not IDLE at write) + W73 (block 1 invalid,
    restored from block 0) is what an interrupted FRAM block write leaves; the two-copy scheme recovers it.
- **CI from a cloud session:** runner logs are blocked, but check-run annotations are readable.
  Oversubscription can be emulated with `taskset -c 0,1`.

## 9. Withdrawn or dead ends (one line each)

- The "3.5× contiguity cliff at 7 → 8": it was sampled after the burst, with an allocating probe.
- "1.3 ms per connection": the load scaled with the setting.
- The "18-connection bar" and "12 KB free per connection": a client inside the DUT's heap. "47
  caught / 63 fatal": the transport path alone, nothing else running — an upper bound, not a wall.
- Cutting churn (joining pieces, gating response construction to 1-3 at a time) changed nothing,
  because size is the variable. A 128 B cap is no better than 256 B: the pieces list grows instead,
  and the writes double.
- The first heap-recovery script, and a per-response cost script, were dropped once
  `serving_at_default_gc.py` covered both.
- Rounds load as a "peak" figure: pauses and 5 s snapshots miss the moment all N allocate.
- `--margin`'s printed idle and median before `53ac222`: a mid-boot sample, and a median spanning post-load idle.
- The non-collecting peak sampler's heap figure: read late after a GC, biased low; never a peak.
- The device rejection counter installed at `READY`: host > device by 0-21; now installed at webserver creation.
- A reference fetch that accepted a 0 B body taken during the WLAN drop.
- "~13-14 KB per connection at peak plus 2,324 B static": the 13-14 KB is the E6 → E7 drop in free
  heap at peak, which already contains the static part and idle noise; the live set per open
  connection is ~7.5-8 KB (§7).
