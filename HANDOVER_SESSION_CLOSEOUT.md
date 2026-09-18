# Session closeout handover — `claude/automated-build-chain-nuzumw` (PR #58)

**Throwaway file.** Written 2026-09-18 by the session that reviewed and closed out PR #104 and
PR #103 on this branch, for the follow-on session tasked with the pre-merge sweep. Delete it once
that sweep has read it and reported; nothing here is a permanent fact worth keeping (anything that
was got migrated to CLAUDE.md / SPECIFICATION.md / BACKLOG.md at the time, and those pointers are
named below).

## Why this file exists

The follow-on session's recipe is: *find everything opened, everything closed, and everything
opened-but-never-closed* — applied in parallel and cross-referenced to (a) the originating
session's whole conversation, (b) the documentation and comments the PR touched, (c) the code,
solutions and tests it touched, and (d) the PR's full diff. Items (b)-(d) are readable from the
repo. Item (a) is not: the conversation is gone when that session starts. **This file is item (a)**,
written as a ledger of facts, findings and their open/closed state — not as a narrative of how
anything was debugged.

## Standing exception, explicitly out of scope

**Heap fragmentation is NOT this sweep's business.** A separate session is actively working it
(PR #105; `HANDOVER_HARNESS_AND_HEAP_FRAGMENTATION.md` is its handover, and the one remaining bench
failure at the close of PR #103 is that defect). Do not chase it, do not report it as an unclosed
item, do not "fix" anything it touches. If a finding below appears to overlap it, leave it.

---

## 1. What this session actually did, in order

Five units of work, each driven by a direct request from the project owner.

1. **Audit of `buildgen/` and the generated build chain** (predates the PR #104 review).
2. **Review of PR #104** (`claude/sensortask-test-economy`, the ~10x test-suite speedup) after it
   merged into this branch, plus the follow-up fixes it needed.
3. **A hardware-wear audit**, triggered by the owner's standing direction after the review surfaced
   a test that wrote 396MB per run.
4. **A factual question about where `TEST_PARALLELISM` is set** (answered; no code change).
5. **Review of PR #103** (`claude/digital-twin-wifi-fram-persistence-fix`, the FRAM-logging and
   ResetErrors real-hardware fold-in) after it merged, plus the six fixes it needed.

Everything below is organised as an **opened → closed ledger**, because that is what the recipe
needs. Section 7 is the short list of things this session opened and did **not** close.

---

## 2. Unit 1 — `buildgen/` audit (closed)

| Opened | Closed by | State |
| --- | --- | --- |
| Does `buildgen` really generate all 6 real devices correctly? | Generated and inspected output for all six; all build and are covered by tests. | **Closed** |
| `_LEGACY_WIRING_PLANS` was a hardcoded fallback shortcutting real generation | Eliminated; the chain now generates fully, no legacy plan table. | **Closed** |
| Device-variant facts leaking outside `devices/*.toml` | Repo-wide scan performed; leaks fixed. | **Closed** |
| Gaps in buildgen/generated-code test coverage | Audited and closed. | **Closed** |
| Stale test-file pointers across docs and code | Fixed. | **Closed** |
| `REAL_HARDWARE_HANDOVER.md` carried substantively stale claims | Three edits: the superseded 600s/350s timeout-override fix, and a heap section pointing at a removed BACKLOG entry while calling 32M open. | **Closed** |

---

## 3. Unit 2 — PR #104 review (test economy, ~10x speedup)

### What PR #104 did, verified rather than assumed

Split monolithic per-device test files into a shared `register_for_device()` scenario library plus
thin per-device wrapper files, so each device's batch runs as its own parallelisable Unix-port
process. **Coverage preservation was verified by diffing the `@_register` / `@_register_param`
decorator names before and after for all three split families (byte-identical) and the `^def test_`
names in the integration file (identical)** — not by counting tests. Families: 55x6 sensortask,
15x6 webserver-concurrency, 3x6 twin construction.

### Findings this session raised against PR #104, and their state

| # | Finding | State |
| --- | --- | --- |
| 2.1 | Stale pointer: `scripts/test.sh` named `tests/test_sensortask.py` for the dynamic per-device `__import__()`; the real file is `tests/_sensortask_scenarios.py`. | **Closed** (`f4ee45c`) |
| 2.2 | The 180→240 per-file timeout narrative did not name the then-monolithic file. | **Closed** — rewritten to name `tests/_webserver_concurrency_scenarios.py`. |
| 2.3 | **Real defect PR #104's own safety audit missed:** a duplicated port base. `test_asy_wifi_service.py` and `test_asy_dns_client.py` both claimed 54000. | **Closed** — wifi_service moved. |
| 2.4 | **Real defect, same class:** the entire UDP test tier sat *inside* the OS ephemeral range (`/proc/sys/net/ipv4/ip_local_port_range` = 32768-60999), exposed by `tests_scripts/`'s own `_free_port()` now running concurrently because of the backgrounding change. Duplicate **unicast UDP** bind *succeeds* on Linux with SO_REUSEADDR → silent datagram misdelivery, not `EADDRINUSE`. | **Closed** (`48ff128`) — seven files moved below 32768: udp_socket 51000→21000, captive_dns 52000→22000, ntp_client 53000→23000, dns_client 54000→24000, ntp_wifi_dns 55000→25000, ntp_fram_system 56000→26000, wifi_service →27000. Each carries a two-line note; the rule "a new socket-binding test file claims an unused base below 32768" is recorded in `scripts/test.sh`. |
| 2.5 | **Hang:** `TEST_PARALLELISM<=0` made the dispatch loop's `wait -n \|\| true` busy-spin forever without ever dispatching. 0 is a plausible "turn parallelism off" guess; 1 is what actually does that. | **Closed** (`f4ee45c`) — clamped to `>= 1` with a warning. |
| 2.6 | **The job pool's one unbounded wait:** the backgrounded `tests_scripts/` pytest job had no timeout, against CLAUDE.md's standing "hanging tests are never allowed" rule. | **Closed** (`a092800`) — `TESTS_SCRIPTS_TIMEOUT_S`, default 1200s (~5x its measured ~248s). |
| 2.7 | `README.md` did not document `TEST_PARALLELISM` / `TESTS_SCRIPTS_TIMEOUT_S`, and stated `PER_FILE_TIMEOUT_S`'s default as 180 when it is 240. | **Closed** — documented; "two environment variables" → "five"; the new per-file `[<name>]` output tagging documented. |

### Things checked and found already sound (do not re-audit)

- **Target-side hardware wear gating** — `flash_cycle`, `scd30_write` (now `persistence_write`),
  `scd30_extra_write` (AND-gated), `long_soak`, `multi_day_rollover`. Already rigorous; nothing to fix.
- **Electrical bus contention** — no I2C/SPI pin is ever `Pin.OUT`; only the Neopixel data line.
- **A port-53 hypothesis of mine was wrong.** I reasoned from code that
  `test_asy_wifi_service.py` binds `0.0.0.0:53`. Direct observation (240 `ss -uln` samples across a
  full run) showed it never does. Recorded because the *method* matters: direct observation
  corrected inference.
- **`-X heapsize` history**: 8M → 32M (WP1/WP2 FRAM-wiring growth) → root-caused back down to 16M by
  the per-device split. `gc.collect()` is forbidden as a stabilisation tool by standing rule, and
  was empirically ineffective here anyway. `scripts/test.sh`'s own comment is the authoritative
  history; CLAUDE.md points at it rather than duplicating it.

---

## 4. Unit 3 — the hardware-wear audit (closed, and it created a standing rule)

### The trigger

`tests/test_tmp_scratch.py` deliberately created **400,000 flat sibling directories** in the shared
`tests/_tmp` root on every run, to re-demonstrate that a **retired** implementation's shared-root
`os.listdir()` raises `MemoryError`. Cost, measured directly via `/proc/diskstats`: **396MB of
physical disk writes per run**, in `unit-tests` and `unit-tests-coverage` both, plus every local run.

**I initially documented this as a "characteristic... bounded and confirmed harmless" instead of
treating it as a defect.** The owner corrected that directly: *"That's not the kind of good ways to
test... This would kill even a host SSD over time! Any tests which could potentially damage hardware
of both host and target are to be strictly avoided!"* That correction is the origin of the standing
rule below.

### What closed it

- The 400k test was **replaced**, not tuned: `_RecordingOs` records every `os` call a full
  `TmpScratch` lifecycle makes, and the test asserts none of them reads the shared root. Result:
  **0.006s instead of 21.3s, 392KB instead of 396MB**, and strictly stronger — a reintroduced
  `os.listdir(_ROOT)` now fails immediately rather than only once the root has grown enormous.
  **Proven non-vacuous** by injecting exactly that regression into `_ensure_dir()`, confirming the
  failure, then restoring with a zero diff.
- A companion behavioural test uses **25** siblings, not 400,000 — the invariant is independence
  from sibling *count*, which a handful proves as well as a huge number.
- Whole-suite disk writes: **~440MB → 46MB**. System time: **17.5s → 8.7s**.
- **CLAUDE.md gained a hard rule**: *"No test may inflict avoidable wear on real hardware — the
  host's own SSD included, not just the target's flash/NVM"* (owner's explicit standing direction,
  2026-09-17), closing with: *"When a test seems to need brute-force scale, that is the signal to
  find the invariant instead."*
- **Audit for siblings of that shape: performed, none found.** The rest of the suite is clean.

**State: fully closed.** The only live obligation is the standing rule itself.

---

## 5. Unit 4 — the `TEST_PARALLELISM` question (answered, no change)

Owner asked where it is actually set. Answer as given: **nowhere sets it.** `scripts/test.sh` was
the sole site and only *read* it as an optional env override with a computed default. `.github/
workflows/ci.yml` never exports it, so CI runs at the computed default. `README.md` and seven
`tests/*.py` comments only reference it.

**This is now partly superseded** — PR #103 replaced the flat default with autodetection, and this
session then moved that autodetection (see 6.1). The structural answer is unchanged: still no file
sets it, it is still only an override.

---

## 6. Unit 5 — PR #103 review (FRAM logging, ResetErrors, harness hardening)

PR #103 merged as `35dc816` (32 commits, 44 files, +3156/−278, **no `src/` changes at all** — it is
entirely harness, tooling, tests and docs).

### Independently verified as correct (do not re-verify)

- `scripts/lint.sh` + all three typecheck passes clean, **155/47/104 files**.
- `scripts/test.sh`: **83/83** MicroPython files, `tests_scripts/` **1225 passed / 7 skipped** (now
  1227 after this session's two new guards), exit 0.
- The `devices/*.toml` race fix is sound: `scripts/_generate_sensortask_modules.py:35` really is the
  only glob, and `build_website.sh` names its device explicitly — the "nothing else re-globs" claim
  holds.
- The `set -e` hazard I suspected in `_detect_parallelism` (a mid-`&&`-list failure inside process
  substitution) — **tested directly; bash does not abort.** Safe.
- `_errcount_required()`'s `if not entry: raise` is sound because `_shape_errcount_entry()` returns
  `{"counter": 0, "history": []}`, never `{}`, for a never-logged module. Every assertion site is
  device-gated, and every real device carries sgp40/scd30/fram, so no device can hard-fail on a
  module it lacks.
- `[1-9][0-9]* passed` in `_require_clean_hardware_run.sh` correctly refuses `0 passed` even inside
  a line carrying other numbers.
- The `tests_js/` `it.each` lengths-not-strings fix is behaviour-preserving: `validLengths` comes
  from a `new Set`, so the filtered case sets are identical.
- The EXIT-trap cleanup kills both the subshell and its `timeout` child by recorded PID, with no
  `pkill`/procps dependency (a `--variant=minbase` chroot has none).

### Findings this session raised against PR #103, all now fixed in `014d65b`

| # | Finding | State |
| --- | --- | --- |
| 6.1 | **The parallelism speed probe measured a host this script had already loaded.** It sat 262 lines *after* the `tests_scripts/` background launch, so it timed the interpreter with pytest saturating every core. Measured on this project's 4-core x86 sandbox: **131-141ms across 8 idle samples vs 391ms in situ** — 2x/8 jobs where the host warrants 4x/16, and non-deterministic run to run. | **Closed** — whole resolution moved ahead of the launch; now reads **137ms → 16 jobs**. `tests_scripts/test_test_sh.py` asserts the ordering (every unit test around it runs the extracted function in isolation on an idle machine, so none could have caught it). Wall clock barely moved (4m30.9s → 4m28.3s) because the backgrounded pytest tier is the binding constraint at both settings — the defects were the non-determinism and the probe not measuring what it claimed. |
| 6.2 | **BACKLOG item 28 quoted "117ms → 16 jobs (unchanged from before)" as if that were what the script did.** Those figures were measured in isolation. | **Closed** — item 28 corrected with the in-situ numbers and the fix. |
| 6.3 | **"A run spends zero persistence writes" contradicted the rule settled in the same PR** — in `tests_hardware/README.md` two paragraphs after stating it, and in the `--allow-persistence-writes` `--help`. A default bench run *does* spend the prerequisite writes (`joined_hotspot`'s SSID clear/restore; `_recover_stale_dut_credentials()`'s push). | **Closed** — both corrected. The **flash tier's** zero claim is accurate and kept: every prerequisite writer is bench-only (`dut_ip` is unused in `tests_hardware/flash/`; verified). |
| 6.4 | **Eleven `test_hotspot_role_reversal.py` tests carried `@persistence_write` purely for depending on `joined_hotspot`** — DNS probes, GET sweeps, static content, malformed-packet handling, none of which spends a write. That is exactly what the owner's 2026-09-18 rule keeps unmarked, and it bought nothing: eleven *unmarked* dependents still pulled the fixture in, so its writes happened anyway. Cause: markers placed before the rule was settled, not re-swept after. | **Closed** — markers dropped from those eleven; three kept (`representative_put_round_trips`, `invalid_credentials_rejected`, `real_credentials_put_succeeds`) because those PUT a persisting field themselves. Measured: the file went **14 deselected / 11 collected → 3 / 22**; the bench tier **23 deselected → 12**. Every quoted count in README / handover / `_require_clean_hardware_run.sh` updated against a real `--collect-only` run. |
| 6.5 | **`test_digital_twin_generated_boot.py` rolled its own `devices/*.toml` glob** instead of `_devices.DEVICE_NAMES`, dropping the `zz_test_` filter — and it is the one suite that would actually *boot* a leaked malformed fixture, since collection precedes `conftest.py`'s reclamation fixture. Six other modules already went through `_devices`. | **Closed** — switched to `DEVICE_NAMES` + `device_toml()`. |
| 6.6 | **The marker completeness guard is blind to a PUT whose body is not a literal dict.** | **Closed** — blind spot enumerated and triaged by a new guard; exactly one exists (`test_put_oversized_body_is_rejected_with_413_over_the_normal_network`, provably safe: rejected with 413 inside vendored microdot before any handler). |
| 6.7 | **A failed *first* `date +%s%N` left `probe_start` at 0**, making `probe_ms` the epoch in milliseconds → the **1x** branch, the opposite of the "never silently slower than before" the comment promises. | **Closed** — both clock reads guarded; an unusable clock now resolves to 0 (fast branch) in every direction. |

### Quality observations worth carrying forward (not action items)

- PR #103's documentation discipline is genuinely high: BACKLOG item 24 explicitly says
  *"contradicts what this item previously said"* and retracts two of its own earlier conclusions
  (the twin-is-a-floor claim; the ~0.6s-marginal-per-source figure) against real bench measurement.
- `tests_scripts/test_test_sh.py`'s two-arm EXIT-trap probe (prove the orphan survives *without* the
  trap, then that it dies *with* it) and its `_without_comments()` helper (strip comments so the
  "must not use pkill" check cannot pass on the comment that mentions pkill) are the right shape for
  non-vacuous guards. Use them as the pattern.

---

## 7. Opened by this session and NOT closed

Short list. Everything else above is closed.

1. **The two-chroot pre-push gate is unsatisfied for every `scripts/` change on this branch.**
   CLAUDE.md requires clean-chroot verification on Ubuntu noble (GCC 13) **and** Debian trixie
   (GCC 14) before pushing any `scripts/` change. This branch has changed `scripts/test.sh` and
   `scripts/_require_clean_hardware_run.sh` repeatedly, including in this session's own `014d65b`.
   PR #103 states plainly that its bench-session chroot runs were done at base `d65f98f`, which
   predates every `scripts/` change in it, and calls the residual risk low but the gate the owner's
   to waive. **That waiver has not been given.** This session could not satisfy it either: an
   earlier attempt damaged this sandbox's `/dev` (see §8) and chroot verification was abandoned
   here. The bench Pi4 or the owner's own box is the right place.
2. **PR #58 does not merge cleanly into `main` — 30 conflicts.** Measured with `git merge-tree
   --write-tree origin/main HEAD` on 2026-09-18 at `014d65b`. Notable shapes, because they are not
   ordinary text conflicts:
   - **modify/delete**: `src/sensortask_dev.py` and `digital_twin/run_dev_integration.py` are
     *deleted* here (retired by buildgen / Session 6.2) but *modified* on main.
   - **add/add**: `src/asy_isl29125_driver.py`, `tests/test_asy_isl29125_driver.py`,
     `tests/test_digital_twin_isl29125.py`, `tests/test_digital_twin_isl29125_autorange.py`,
     `tests_hardware/device_scripts/isl29125_lighting_scenarios.py`,
     `tests_hardware/device_scripts/isl29125_mechanism_envelope.py` — the ISL29125 driver landed
     independently on both sides.
   - Plus `.github/workflows/ci.yml`, `BACKLOG.md`, `SPECIFICATION.md`, `DEVICE_REFERENCE.md`,
     `digital_twin/machine.py`, `html/definitions/dev.json`, `js/definitions.js`,
     `mockdata/dev.json`, `tests_hardware/conftest.py` and others.
   **This is the single largest concrete blocker to merging.** Resolving it needs real judgement
   (particularly the add/add ISL29125 set: which side's driver is authoritative), not a mechanical
   merge, and the repo's own rule is to regenerate generated files with the repo's tooling rather
   than hand-merge them.
3. **CI does not run on this branch.** `.github/workflows/ci.yml` triggers only on `pull_request`
   and pushes to `main`. PR #58 is a **draft**, so pushes here trigger no checks. I corrected myself
   on this during the session after wrongly justifying something with "CI will verify it" — do not
   assume a green history exists for this branch's own commits. The last known-green full CI run was
   PR #103's, all 23 jobs at `fbd7516` (run `35339090499`).

## 8. Two incidents worth knowing about (both resolved, no repo impact)

- **`/dev` damage in this sandbox.** `chroot_bootstrap.sh`'s opening `rm -rf "$CHROOT"` ran while a
  stopped earlier run still had `/proc`, `/sys`, `/dev`, `/dev/pts` bind-mounted, deleting host
  device nodes *through the mount*. Recovered by unmounting all four binds, then `mknod` for every
  node (virtio is major **254** in this sandbox, not the usual 253) plus `/dev/fd` and
  `stdin`/`stdout`/`stderr` symlinks. **Carry-forward rule:** never `rm -rf` a chroot path with live
  bind mounts; `findmnt` first. No repo files were affected.
- **I almost altered a recorded measurement.** I changed a "327 real `build_system()` calls" figure
  to 330, then reverted it and kept 327 with a clarifying parenthetical instead. Recorded because
  the principle matters for the sweep: a measurement is a fact with a date, not a number to keep
  consistent with a later count.

## 9. Verification state at handover

At `014d65b`, on this sandbox:

- `scripts/lint.sh` — clean (ruff, shellcheck, actionlint, zizmor).
- `scripts/typecheck.sh` — clean, all three passes, **155 / 47 / 104** files.
- `scripts/test.sh` — **83/83** MicroPython files, `tests_scripts/` **1227 passed / 7 skipped**,
  `ALL PASSED`, exit 0, 4m28.3s at 16 jobs.
- Parallelism probe: **137ms → 4x → 16 jobs** on a 4-core x86 sandbox.
- Real-hardware tiers were **not** run here (no board attached, and no owner go-ahead in this
  session). Their last real run is PR #103's bench session: **1 failed / 82 passed**, the single
  failure being the heap-fragmentation defect that is out of scope per the exception above.
