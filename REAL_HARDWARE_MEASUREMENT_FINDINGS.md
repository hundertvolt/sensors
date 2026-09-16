# Real-hardware measurement findings — boot latency, WP1-WP8 + the `CFGMGR_SYSTEM` fix

Temporary file, same convention as the `WP_RESTART_HANDOVER.md`/`REAL_HARDWARE_HANDOVER.md` pair
that preceded it: delete once its contents are either migrated into `SPECIFICATION.md`/`CLAUDE.md`/
`BACKLOG.md` or confirmed not to apply. The headline numbers and the two conclusions they support
are **already migrated** (see "What is already migrated" below); what is kept here is the raw data,
the evidence chain, the reusable harness, and the method pitfalls — the things a summary drops but a
session repeating or extending this work needs.

## Session facts

- **Date**: 2026-09-16. **Board**: the `dev` bench board, the only device ever physically flashed
  (CLAUDE.md's WoZi/dev rule). MAC `d8:3a:dd:25:0e:0b`, DHCP-reserved at `192.168.85.57` on the
  bench `br0`/`br0-wifi-ap` bridge. USB serial `e66130100f372d34`.
- **Host**: the bench Pi4 itself (Debian trixie), running this session directly.
- **Go-ahead**: given by the project owner in-conversation, explicitly including firmware flashes,
  explicitly excluding SCD30 write tests and anything unrelated to the topic.
- **Base at time of measurement**: `claude/wp-restart-handover-execution`; results have since been
  rebased onto `claude/automated-build-chain-nuzumw` (`e100d81`), where PR #101 and the
  `CFGMGR_SYSTEM` fix are already merged.
- **`DebugLevel` was 5 throughout**, confirmed by `GET /system` before starting and again at the
  end. Nothing in this session wrote device config, so no flash-wear or `DebugLevel`-reset concerns
  apply (`picotool load` of a UF2 does not touch the filesystem region — the built images report
  `FLASH_FS: 0 B`, so the board's config survived all four flashes).

## Measurement protocol

Deliberately *not* `tests_hardware/bench/test_end_to_end_timing.py`'s existing cold-boot test: that
one polls at `poll_interval_s=1.0`, which cannot resolve a ~2s difference with any confidence. A
purpose-built harness was used instead (full source at the end of this file).

Per commit:

1. `git worktree add --detach <tmp> <commit>` — the **harness stays constant on the working
   checkout while only the firmware varies**. This is the part that makes the comparison valid;
   building each image from its own tree also means each one carries its own `buildgen` output,
   not the current tree's.
2. `uv run scripts/build_firmware.py dev --output <tmp>.uf2` (~3 min each). Always `dev`, never
   `wozi`.
3. `board.enter_bootloader()`, then `sudo picotool load -x -v <uf2>` with bounded retry — picotool
   has no internal retry for USB BOOTSEL re-enumeration and fails with exit 249 if called too soon.
   In practice **every one of the four flashes succeeded on attempt 2**, never attempt 1.
4. One warm-up boot, discarded: a fresh flash reboots abruptly and its first rejoin carries
   flash-cycle-specific AP churn rather than steady-state boot cost.
5. Five measured cycles: `bench.kick_all_stations()` → `board.hard_reset()` → `t0` → poll
   `GET /status` every 200ms until a real HTTP `200`, with an 0.8s per-attempt socket timeout.
   `kick_all_stations()` before each reset is mandatory, not hygiene — a stale AP station-table
   entry otherwise blocks the DUT's rejoin entirely (`tests_hardware/README.md`'s documented
   finding).
6. The DUT's own `system.SysUptime` at the moment of that first `200` is recorded alongside, which
   separates on-device boot cost from WiFi-association/DHCP cost.

## Raw data — all 20 measured cycles

| Commit | What it is | Cycle times (s) | Median | Mean | Spread | `SysUptime` at first `200` |
|---|---|---|---|---|---|---|
| `25e0e19` | pre-WP baseline | 7.70, 7.76, 7.76, 7.74, 7.72 | **7.74** | 7.74 | 0.06 | 5, 5, 5, 5, 5 |
| `9cf8a9c` | WP1+WP2 | 9.77, 9.75, 9.80, 9.80, 9.81 | **9.80** | 9.79 | 0.06 | 6, 6, 6, 6, 6 |
| `e47d4e1` | WP1-WP8 complete | 9.73, 9.76, 10.58, 10.51, 9.74 | **9.76** | 10.06 | 0.85 | 5, 5, 6, 6, 5 |
| `7cd8dd1` | + `CFGMGR_SYSTEM` setup-order fix | 10.66, 10.66, 10.65, 10.72, 10.73 | **10.66** | 10.68 | 0.08 | 6, 6, 6, 6, 6 |

Warm-up boots (discarded, listed for completeness): 7.76s, 9.62s, 9.71s, 10.32s — all within their
own group's range, so discarding them changed no conclusion.

**On `e47d4e1`'s wider spread**: two of its five cycles (10.58s, 10.51s) sit ~0.8s above the other
three, and those are exactly the two whose `SysUptime` read 6s rather than 5s. This looks like a
boundary effect in when the device's own 1-second uptime tick lands relative to the webserver
becoming reachable, not instability — the other three cycles cluster at 9.73-9.76s, matching
`9cf8a9c` closely. Median is the honest statistic here; the mean (10.06s) is dragged by those two.

## Conclusions the data supports

1. **WP1+WP2 costs ~+2.05s of real boot latency** (7.74 → 9.80s, +27%). With ±0.06s spread in both
   groups, this is far outside noise.
2. **WP3-WP8 add nothing measurable** (9.80 → 9.76s median, inside spread). The entire WP1-WP8
   delta belongs to WP1+WP2's FRAM chunk growth.
3. **The digital twin's absolute numbers were never a real baseline.** Its "before WP1" figure of
   ~1.9-2.2s is the task graph resolving with zero SPI wire time and no WiFi modelled at all;
   real pre-WP boot is already 7.74s, because WiFi association and DHCP dominate it. Roughly 2-4s
   of every measurement here is network, not device — `SysUptime` at first `200` is only 5-6s in
   every single cycle.
4. **The twin's *delta* prediction was nonetheless good**: it predicted WP2 alone would add
   ~1.4-1.8s; the real WP1+WP2 delta is ~2.05s. Worth remembering when deciding how much to trust a
   future twin measurement — shape yes, absolute value no.
5. **Watchdog**: 23 consecutive real reboots across four flashed images produced **no `WDT_RESET`**.
   Against CLAUDE.md's actual standard ("does not starve the watchdog", not "boots fast"), every
   measured state passes.

## The `webserver` lazy-setup hypothesis — tested, does not apply

`REAL_HARDWARE_HANDOVER.md` §2 proposed that `WebserverService`'s lazy `self.pr.setup()` inside
`_run()` lands in the contended window (every other module's task-start FRAM access already queued
on the same `FRAM_SPI` lock) and might be the dominant cost, with the fix being a real `setup()`
method plus inclusion in `buildgen/codegen.py`'s `setup_order`.

**Measured, not inferred**: `d.webserver.pr.initialized` reads `True` from a clean boot. The
contended window therefore costs it *time*, not correctness. And WP2 adds no new chunk to
`webserver` itself (it has no `cfgmgr`), so it cannot account for a delta that WP1 and WP2 jointly
produce. Moving one module's single chunk operation out of the contended window is not justified by
this data. **The proposed change was deliberately not made.**

## `CFGMGR_SYSTEM` — §2a confirmed, then the merged fix verified

Three independent lines of evidence, gathered before `7cd8dd1` was merged:

1. **Boot log, captured from line zero.** `CFGMGR_SYSTEM` appears **0 times** in a full boot log in
   which all six sibling `CFGMGR_*` loggers (`WIFI`, `NTP`, `SGP40`, `BMP3XX`, `ISL29125`,
   `NOTIFY`) each print their config read preceded by a `FRAM Data read successfully from block 0`
   / `FRAM Both blocks valid and data verified` pair.
2. **Live object inspection.** From a clean boot, `d.sysfunct.cfgmgr.pr.initialized` is `False`
   while `CFGMGR_WIFI`/`CFGMGR_NTP`/`CFGMGR_SGP40`/`SYSTEM`/`WEBSERVER` all read `True`.
   `d.sysfunct.cfgmgr.pr.fram is not None` is `True`, so the chunk **was** allocated — this was
   never a FRAM capacity problem, purely setup ordering.
3. **The code path.** `buildgen/codegen.py` emitted `await sysfunct.setup()` before
   `await fram.setup()`. `SystemService.setup()` calls `await self.cfgmgr.setup()` →
   `pr.setup()`, which finds `AsyFramManager` not yet set up, so both `_read()` and `_write()` fail
   and `initialized` stays `False`. `print_log.py`'s `_store_err()` then takes its
   `if not self.initialized: return` branch on *every later call* — the entry lands in the in-RAM
   `history` deque and never reaches FRAM.

The practical consequence is worth stating plainly: `GET /status`'s `errcount` showed a
`CFGMGR_SYSTEM` block that looked exactly like its persisted siblings but was never persisted at
all. That is a quiet hole in CLAUDE.md's "read the FRAM-persisted per-module error logs before
clearing anything" rule, for that one module.

**The fix (`7cd8dd1`, authored by a parallel session, moving `fram` ahead of `sysfunct`) was then
built and flashed here and verified on the same board, same protocol**: `CFGMGR_SYSTEM` now reads
`initialized == True`. This is the fourth row of the table above.

## Open question: why does the fix cost +0.90s?

Moving `fram` ahead of `sysfunct` raised median boot-to-first-`200` from 9.76s to 10.66s — **+0.90s,
with ±0.04s spread, so unambiguously real.** The expected cost is one additional FRAM-backed
logger's `setup()`, independently established at **~170ms**. +0.90s is roughly five times that, and
this session did not explain it.

Candidate explanations, none verified:
- `CFGMGR_SYSTEM`'s `_read()` fails on a never-before-written chunk (bad CRC8) and then `_write()`
  runs, i.e. two full chunk operations rather than one — still short of 900ms on its own.
- `SystemService.setup()` now genuinely resolves `DebugLevel` from a working `cfgmgr` where it
  previously bailed out early, so `_apply_level()` fans out across every registered level setter at
  a point in the boot where it previously did not.
- Second-order effects from every subsequent `setup()` in the batch now running one position later
  relative to FRAM readiness.

**Worth understanding before the same `setup_order` reorder is treated as free elsewhere.** It does
not threaten the watchdog budget, so it is not urgent and is explicitly not a reason to revert the
fix. Tracked in `BACKLOG.md`.

## Method pitfalls — read this before repeating any of it

These cost real time in this session and are not documented anywhere else.

- **`Ctrl-C` on the live system starves the watchdog.** Interrupting `main()` to inspect objects
  stops the loop; the WDT's 8388ms cap then fires. The abrupt reset hits the stale-AP-station-table
  hazard, the DUT fails to rejoin, and it falls back to **hotspot mode** (`WIFI Hotspot mode is
  active` / `Connected stations: []`). Recovery is `kick_all_stations()` + `hard_reset()`. Keep any
  Ctrl-C probe under ~3s end to end and send Ctrl-D (soft reset) immediately after.
- **The board re-enumerates to a different `/dev/ttyACM*` node after some resets.** It moved
  `ttyACM0` → `ttyACM1` → back to `ttyACM0` across this session. `/dev/ttyACM0` simply vanishing
  looks exactly like a dead board; check `lsusb` for `2e8a:0005` and `ls /dev/ttyACM*` before
  concluding anything. Resolve the node dynamically rather than hardcoding it.
- **`mpremote run` soft-resets before executing**, so it cannot inspect a live system's state —
  module globals come back as `None`. Use a raw serial Ctrl-C + REPL paste instead. **This produced
  a real false finding in this session**: an early probe reported `SYSTEM` and `WEBSERVER` loggers
  as uninitialized alongside `CFGMGR_SYSTEM`, because it ran moments after an `mpremote run` had
  reset the board, before `start_and_check_tasks()` (which calls `SystemService`'s own
  `pr.setup()`) and the webserver task had run. From a clean boot only `CFGMGR_SYSTEM` is affected.
  **Always let the board reach a steady state before probing, and re-confirm any negative result.**
- **A hard reset's USB re-enumeration swallows the first ~2 seconds of boot output** — exactly the
  window the `setup()` batch runs in. A serial capture that reconnects across the reset starts too
  late to see it. Use a **soft reset** (Ctrl-D) instead: it re-runs the same `_boot` →
  `build_system()` → setup-batch path while keeping the CDC link up, so the log is complete from
  line zero.
- **`build/generated_src/sensortask_dev.py` is not what gets built.** `scripts/build_firmware.py`
  generates into a temporary directory; the checked-out `build/generated_src/` copy can be hours
  stale and will happily show you the *old* setup order after you have already built the new one.
  Verify generated output via `buildgen.generate.generate_device(Path("devices/dev.toml"),
  Path("src"))` in-process instead.
- **`picotool` in this environment has USB support** (both `/usr/local/bin/picotool` and the
  toolchain-built one) — `tests_hardware/README.md`'s warning about a no-USB build applies to a
  sandbox, not to this bench host.

## FRAM error-log snapshots

Captured before touching the board, per CLAUDE.md's standing rule. Only non-zero counters shown; 21
chunks present throughout.

| Module | Pre-flash baseline | After the 3-commit campaign (18 boots) | Final (after the 4th image) |
|---|---|---|---|
| `FRAM` | 14: `E31 W71 E31 W72 E46 W71 E31 W71 E31 W72` | 13: `E90 E30 W72 E92 E10 E61 E31 W71 E31 W72` | 2: `E31 W73` |
| `SGP40` | 2: `W10 ×2` | 10: `W10 ×10` | 16: `W10 ×5 W13 ×3 W11 ×2` |
| `DNSSRV` | 0 | 2: `W10 ×2` | 2: `W10 ×2` |
| `UART_init` | 0 | 6: `E20 W10 E20 W10 E22 W10` | 8 |
| `UART_resp` | 0 | 6: `E20 W10 E20 W10 E20 W10` | 8 |
| `WIFI` | 0 | 0 | 11: `W6 ×10` |

Read these as **artifacts of the campaign, not field evidence**. The `UART_*`, `SGP40` and `DNSSRV`
entries are ordinary boot transients on a bench board reset 23 times. The `FRAM` entries are
consistent with abrupt reboots landing during real FRAM activity (four `picotool` flashes plus 23
hard resets) — this is the same hazard the bench tier's own recombination test exercises
deliberately. The `WIFI` `W6 ×10` block corresponds to the hotspot-fallback episode described under
"Method pitfalls". No `errno`/`wrnno` interpretation is attempted here: that numbering is being
handled in a separate session, per the handover doc's own instruction.

One genuine oddity, recorded without explanation: **`FRAM`'s counter went 14 → 13 → 2 across the
session**, i.e. it decreased. A counter that is not monotonic across reboots is worth a look, but it
was not chased here — it is not obviously connected to anything this session was measuring, and
could simply be a ring-buffer accounting detail rather than a defect.

## What was deliberately not run

Per the project owner's explicit scoping ("do not run tests completely unrelated to the current
topics in favor of time"):

- **`scripts/run_flash_hardware_suite.sh` and `scripts/run_bench_hardware_suite.sh` were not run.**
  Neither answers the boot-latency question, and both cost substantial board wall-clock time.
- **No SCD30 write tests**, per standing instruction (`--allow-scd30-writes` never passed).
- **The hotspot role-reversal scenario was not run** — its stage 6 carries the permanent-WLAN-
  deactivation risk.
- **No device config was written**, so `DebugLevel` never needed restoring and no sensor EEPROM was
  touched.

If a future session wants a regression sweep on top of these findings, those suites are the obvious
next step and nothing here blocks them.

## What is already migrated

- `SPECIFICATION.md`'s boot-latency note: the four-row table, the protocol, the three conclusions,
  the `webserver`-hypothesis rejection, and the fix's +0.90s cost.
- `BACKLOG.md`: the `CFGMGR_SYSTEM` entry (defect closed, cost open).
- `TEST_SUITE_ECONOMY_HANDOVER.md`: its inbound reference to the now-deleted
  `REAL_HARDWARE_HANDOVER.md` made self-contained.

**Not yet migrated, and the reason this file still exists**: the method pitfalls section (it belongs
in `tests_hardware/README.md` if the project owner agrees), the raw per-cycle data, the FRAM
snapshot table, and the non-monotonic `FRAM` counter observation.

## The harness, for reuse

`measure_boot.py` — flashes one image, then runs N timed cycles. Invoked as
`uv run python measure_boot.py "<label>" <uf2> <cycles> <out.json>`.

```python
def try_status(ip, timeout_s=0.8):
    """One bounded GET /status. Returns the parsed body on 200, else None."""
    try:
        with socket.create_connection((ip, 80), timeout=timeout_s) as s:
            s.settimeout(timeout_s)
            s.sendall(b"GET /status HTTP/1.0\r\nHost: %s\r\nConnection: close\r\n\r\n" % ip.encode())
            buf = b""
            while len(buf) < 65536:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
    except OSError:
        return None
    if not buf.startswith(b"HTTP/1.0 200") and not buf.startswith(b"HTTP/1.1 200"):
        return None
    _, _, body = buf.partition(b"\r\n\r\n")
    try:
        return json.loads(body)
    except ValueError:
        return None


def one_cycle(board, bench):
    bench.kick_all_stations()   # mandatory - stale AP station entries block the rejoin outright
    board.hard_reset()
    t0 = time.monotonic()
    while time.monotonic() < t0 + 180.0:
        body = try_status(DUT_IP)
        if body is not None:
            return time.monotonic() - t0, body.get("system", {}).get("SysUptime")
        time.sleep(0.2)
    raise SystemExit("no HTTP 200 within the ceiling")
```

Flashing, with the retry that `picotool` itself lacks:

```python
board.enter_bootloader()
for attempt in range(6):
    load = subprocess.run(["sudo", "picotool", "load", "-x", "-v", str(uf2)],
                          capture_output=True, text=True, timeout=180, check=False)
    if load.returncode == 0:
        break
    time.sleep(2.0)
```

Live-object probe — Ctrl-C only (no Ctrl-D, so globals survive), read fast, soft-reset immediately
so the watchdog does not bite:

```python
with serial.Serial(dev, 115200, timeout=0.3) as port:
    port.write(b"\x03")
    time.sleep(0.6)
    port.reset_input_buffer()
    for stmt in statements:            # e.g. "import sensortask_dev as d",
        port.write(stmt.encode() + b"\r\n")   # "print(d.sysfunct.cfgmgr.pr.initialized)"
        time.sleep(0.22)
    time.sleep(0.8)
    out = port.read(port.in_waiting or 1).decode("utf-8", errors="replace")
    port.write(b"\x04")                # resume the system before the WDT's 8388ms cap
```

Full boot log from line zero — soft reset, not hard, so the USB CDC link survives:

```python
with serial.Serial(dev, 115200, timeout=0.5) as port:
    port.write(b"\x03"); time.sleep(0.5); port.reset_input_buffer()
    port.write(b"\x04")
    deadline = time.monotonic() + 40.0
    while time.monotonic() < deadline:
        raw = port.readline()
        if raw:
            lines.append(raw.decode("utf-8", errors="replace").rstrip("\r\n"))
```
