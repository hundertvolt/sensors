# Catalog: instrumentation — what measures, and how to rebuild it

**What this is.** The measurement side of this branch's connection-scaling and serving work
(2026-09-22/23): special builds, harnesses, calibrations, hardware tools and the traps that cost
time. None of it belongs in the everyday suites — too slow, too build-specific, or it needs the
board. Its companion, `CATALOG_UNIT_TESTS.md`, holds the tests that do. Only methods that finally
worked are listed; withdrawn claims and dead ends are one line each in §9.

**Temporary, this session's working catalog only.** Kept current while this work continues (a
instrument added, changed or retired on this topic gets its entry in the same commit), then processed
into the permanent docs and **deleted before the branch merges**. The twin32 tooling itself is never committed
(owner, 2026-09-23); what survives the merge is its documentation (MEASUREMENTS §7Q, §10). Scratch
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
- **The twin is optimistic near the wall by two levels or more.** Pre-fix silicon image G failed its
  first JSON route at N = 10, while the 32-bit twin showed none through 12.

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
  - measure transients with a collect first and survivors in a fresh process per repeat.
- Ballast guards use the largest free run, not `gc.mem_free()`.

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
- **Known limit:** the twin build admits 64 connections, so the refusals at N > 8 are not modelled.

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
- **`tests_hardware/combined_load_sweep.py`** — the hardware session's per-boot sweep (§10.9 of
  `BENCH_SITTING_2026-09-23_HANDOVER.md`). **Temporary, to be removed once this work closes; what it
  does is recorded here so it can be rebuilt.**
  - `DUT_IP=<ip> uv run python tests_hardware/combined_load_sweep.py <levels…> [--threshold -1]
    [--raw-dir d]`.
  - **One fresh boot per listed level**, and a repeated level is a repeated run. Pre-fix failures at
    N = 5-6 were probabilistic, 1 run in 2-3, so a single clean run proves little.
  - It writes a copy of `device_scripts/serving_stability_under_combined_load.py` with its
    `gc.threshold(-1)` line replaced.
  - Host threads send 12 rounds of N concurrent GETs over
    `/status /sensors / /measurements /status /networking /sensors /system /js/app.js`.
  - The static bodies must match an idle reference fetch (made after the board answers `/status`);
    the JSON bodies must parse.
  - **STABLE** means every body complete, zero device lines matching `MEMORY_ERROR_MARKERS`, and the
    driver thread finished. Between levels it runs `kick_all_stations()`, a hard reset and a 45 s
    settle. Exit 0 only if every level is STABLE.
  - Validated in the twin (dev's site, fixed firmware): STABLE at 4, 6 and 8, with every body
    complete. On the pre-fix firmware at G's heap it reports **UNSTABLE at N = 8**: two `/` bodies
    were cut off, at 0 and 1,024 B. The device printed no line for them (the twin does not print
    `err_s` for this tool), so **the host-side body check alone catches the defect**, which is why
    it exists.
- **`tests_hardware/bench/test_network_resilience.py`**:
  - `test_the_board_holds_exactly_the_connection_ceiling_this_tree_configures`;
  - `test_a_full_ceiling_of_concurrent_requests_is_each_served_a_complete_body`;
  - `test_a_concurrent_page_load_is_byte_identical_to_an_uncontended_one`;
  - `error_log_helpers.assert_no_module_logged_a_new_error`, which snapshots every FRAM module's
    counter.
- **`tests_hardware/bench/test_heap_under_connection_ceiling.py`** with
  `device_scripts/heap_under_connection_ceiling.py`. No connection can be held past ~15 s
  (`outer_cap_s`), so holders stagger and recycle at 10 s, and holder threads must be stoppable and
  joined; one that was not caused a 37-failure cascade.
- **`harness.py`**:
  - `configured_max_connections()`;
  - `discover_max_connections(dwell_s=0.3)` — its dwell must stay under the 5 s idle close;
  - `_wait_for_slots_to_drain` — a slot releases 0.71-0.84 s after the client closes.

## 7. lwIP sizing and connection cost

- **Source of truth** is `toolchain/versions.toml` `[lwip]`: PCB 11, SEG 64, `MEM_SIZE` 16,000,
  MSS 800, WND and SND_BUF 6,400, among others.
- **Before the build**, `check_lwip_ensemble()` checks the set.
- **After the build**, `verify_lwip_macros_in_build()` preprocesses a probe against the real
  translation unit and demands a sentinel plus every value. This runs in every `build_firmware()`
  and in CI.
- **Why the override is built the way it is:**
  - `MEMP_NUM_UDP_PCB` and `LWIP_STATS` are bare `#define`s, so they need the header shim.
  - `CFLAGS_EXTRA` loses to the include order on rp2; `MICROPY_BOARD_DIR` is the working redirect.
  - TIME_WAIT connections use the same PCB pool.
  - `LWIP_STATS=1` costs 1,916 B.
- **Permanent cost, from real ELFs** (`arm-none-eabi-nm`, `__GcHeapEnd − __GcHeapStart`):
  - 196 B per PCB alone;
  - **2,324 B per connection for a coherent ensemble**, the same at every step from 4 to 16;
  - silicon agrees: G has 18,592 B less heap than F, which is 8 × 2,324.
  - Buffer options cost far more: `PBUF_POOL_SIZE` 16 → 32 is 15,644 B.
- **Transient and residual cost, twin:**
  - ~5,170 B live per parked connection after a collect;
  - after 40-80 served requests, a flat 1.5-1.6 KB residue in total, not per connection;
  - `/status` latency at a fixed offered load of 4 is flat at 4.2-4.5 ms, for limits from 4 to 16.

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
- **CI from a cloud session:** runner logs are blocked, but check-run annotations are readable.
  Oversubscription can be emulated with `taskset -c 0,1`.

## 9. Withdrawn or dead ends (one line each)

- The "3.5× contiguity cliff at 7 → 8": it was sampled after the burst, with an allocating probe.
- "1.3 ms per connection": the load scaled with the setting.
- The "18-connection bar", "12 KB free per connection" and "47 caught / 63 fatal": each measured with
  a client inside the DUT's heap.
- Cutting churn (joining pieces, gating response construction to 1-3 at a time) changed nothing,
  because size is the variable. A 128 B cap is no better than 256 B: the pieces list grows instead,
  and the writes double.
- The first heap-recovery script, and a per-response cost script, were dropped once
  `serving_at_default_gc.py` covered both.
