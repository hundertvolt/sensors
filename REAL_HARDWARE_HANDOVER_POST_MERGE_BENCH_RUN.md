# Real-hardware handover — the post-merge bench run

Temporary file, same convention as every handover before it: **delete once its results are
migrated** into `REAL_HARDWARE_TEST_QUEUE.md`, `SPECIFICATION.md` and
`HEAP_FRAGMENTATION_MEASUREMENTS.md`. Written 2026-09-19 by a session with **no** real-hardware
go-ahead — every claim below is `[SRC]` (read out of the source) or `[MOCK]` (proven at the mock
tier). **Nothing here is `[HW]`.**

**Nothing in this file authorizes anything.** CLAUDE.md's gate stands: the session that runs this
needs the project owner's go-ahead **in its own conversation**. A go-ahead given to the session that
wrote this, or to any earlier bench sitting, does not carry over. `tests_hardware/README.md` remains
the technical reference for prerequisites, flags and safety facts.

It sits alongside `REAL_HARDWARE_HANDOVER_WEBSERVER_BODY_CAP.md`, which is still open on exactly one
row (W5). This file is the wider one: it exists because the branch has since merged 22 commits of
base, and because the owner asked for a full bench tier run in its own right.

---

## 1. The one thing this sitting must do

**One full bench-tier run, default flags, no soak.**

```
scripts/run_bench_hardware_suite.sh
```

No arguments. That is the whole instruction, and the three constraints the owner set are satisfied
by the defaults rather than by anything you have to remember:

- **Flash-write flag disabled.** `--allow-persistence-writes` is **off unless passed**, and so are
  `--allow-flash-cycle`, `--allow-scd30-extra-write` and `--allow-neopixel-sweep`
  (`tests_hardware/conftest.py`). Pass **none** of them. Every row in the queue marked
  *BLOCKED on D1* stays blocked this sitting — that is the intended outcome, not an omission.
- **No hours-long soak.** `run_bench_hardware_suite.sh` passes
  `-m "not long_soak and not multi_day_rollover"` itself, and its own comment says it ignores
  `--soak-tier`/`--allow-multi-day-rollover-wait` passed by mistake. The way to start a soak is to
  invoke a *different* script, `scripts/run_bench_soak_tests.sh` — **do not**. One caveat worth
  knowing rather than discovering: the runner appends `"$@"` **after** its own `-m`, and pytest
  keeps only the last `-m`, so a caller-supplied `-m` would silently replace the soak exclusion.
  Running it with **no arguments**, as instructed above, cannot hit that.
- **"Full bench tier" already includes the flash tier.** The runner passes both
  `tests_hardware/flash` and `tests_hardware/bench` to pytest, so this single command is the
  superset run, not half of one.

### Read the deselected count, not the word "clean"

`scripts/_require_clean_hardware_run.sh` reports a **deselected** count beside its verdict, on
purpose: the wear gates **deselect** rather than skip, and deselection is invisible to every
pass/fail check. "Clean" here means *everything that ran, passed* — never *everything ran*. With no
flags passed, a substantial deselected count is **expected and correct**; the last two sittings both
reported **27 deselected** on the bench tier. A number far from that is itself worth writing down.

Reference point for the totals, so a shortfall is noticeable: the 2026-09-19 sittings collected
**93 passed / 4 skipped / 27 deselected** before this branch's five `§1D` rows existed, and
**97 passed + 1 failed / 4 skipped / 27 deselected** with them. Expect roughly that again.

### Before anything writes: read `errcount`

CLAUDE.md's standing rule, and it has cost real evidence twice. `GET /status`, save the whole
`errcount` table verbatim, **before** the suite starts — the tests call `reset_all_error_logs()`
themselves, so a post-run read is too late. Then check what was last run against this board: an
isolated-driver device script builds its own `AsyFramManager` over the same chip and can leave a
plausible-looking fabricated entry behind (`tests_hardware/README.md` has the mechanism; queue §2A
F9 is the worked example).

---

## 2. What changed since the last sitting, and therefore rides along

Nothing below needs a separate invocation — the run in §1 covers all of it. This section exists so a
red result is read correctly rather than chased.

### 2.1 W5 was rewritten, and it is the one row that can still fail

`test_concurrent_mixed_body_sizes_are_never_answered_with_the_wrong_status` (renamed from
`..._never_destabilise_the_real_server`). The previous sitting found it failing 5/5, and correctly
established that it was measuring the **connection ceiling**, not the body cap: refusals land at
every body size, 64 B included, and begin *at* `max_connections = 4`.

It now asserts what the cap actually owns — **every client that IS answered is answered correctly**
— and tolerates a ceiling refusal. Read a failure like this:

| symptom | meaning |
|---|---|
| a **wrong status** (200 for an oversized body, or 413 for one under the cap) | the real thing this row exists to catch. `src/` is implicated. |
| a **non-ceiling exception**, a `TimeoutError` above all | deliberately *not* tolerated — something hung. Do not relax it. |
| "too few answered" / "never saw both verdicts" | the run was too starved to prove anything. **Re-run; do not widen.** |
| a `ConnectionResetError`/`BrokenPipeError` on any arm | expected, counted, not a failure. |

Replayed host-side against all four of the previous sitting's recorded runs it passes each one
(18-20 answered, 0 wrong), but **that is a replay, not silicon** — this is its first real run.

It also now takes a `time.sleep(1.0)` settle before launching its workers, for the reason
`test_connections_at_and_above_the_real_socket_limit_degrade_cleanly` already takes one: a slot is
released in `_serve()`'s `finally`, *after* `_close_writer()` awaits the close, so the preceding
`reset_all_error_logs()` PUT can still be holding one. That is also the explanation for the previous
sitting's "resets begin *at* the ceiling rather than beyond it" — three free slots, four clients.

### 2.2 W3 now sends a corrected, larger body

The schema maximum was documented as **1,132 B** and is actually **1,312 B**. The difference is not
arithmetic: 1,132 is the *NTP group alone*, justified by `js/render.js` submitting one group at a
time, which is true of the website and **not of the API** — `_put_sensors()` iterates `body.items()`
and the flat handlers apply every field they recognise. A cap must serve what the API accepts.
W3 sends the corrected size, so its pass is a slightly stronger statement than last time; margin is
1.56x, not 1.8x.

`tests_scripts/test_request_body_cap_headroom.py` now derives both sides in CI — the cap out of
`WebserverService.__init__` by AST, the schema out of the real `buildgen` model per device — so this
figure cannot drift again unnoticed. **No hardware needed for that one**; it is named here only so
the corrected number is not mistaken for a regression.

### 2.3 What the base merge did and did not bring

Audited file by file, because a clean merge is where semantic breakage hides:

- **`src/` is untouched by the base — zero changes.** The shipped firmware carries no merge risk,
  and nothing in this sitting is testing merged firmware behaviour that did not exist before.
- **`tests/machine.py` and `digital_twin/machine.py` both corrected `Pin.PULL_UP` from 2 to 1**
  (and added `PULL_DOWN = 2`), matching the real rp2 values and `typings/`' own stub. Every consumer
  uses the symbolic name, never the literal, so this changes no behaviour — but it does mean the
  **mock-conformance probe and silicon now agree on the pull constants**, where the twin previously
  disagreed. If `isl29125_mock_conformance_probe.py` reports a pull mismatch, that is new
  information, not the old known divergence.
- **`scd30_same_device_rw_concurrency.py` gained a 12 s post-reset settle**, which unblocked
  `test_isl29125_cross_device_concurrency_with_its_i2c1_neighbours`. **Already bench-verified by the
  session that wrote it** (`RESULT: PASS reader=40/40`), so it is not owed — it simply runs again
  here. Its NVM-write budget is unchanged: exactly one `set_ambient_pressure()`.
- **`test_memory_stress_bench.py`'s `_FRAM_BACKED_MODULES` gained `ISL29125`.** Additive and
  `.get()`-guarded, so it costs nothing on a variant without it.
- **The base added no new hardware test functions at all**, and every test fake it touched is
  comment-only changed apart from the `PULL_UP` line above (verified at token level).

### 2.4 One dead helper, recorded rather than used

`tests_hardware/error_log_helpers.py` gained `assert_module_error_log_clean()`, which is **defined
and called from nowhere**. It is the right tool for a module whose normal operation includes a
legitimate warning, and our own `§1D` rows deliberately use the stricter `assert_module_error_log_empty()`
against `WEBSERVER` because the evidence says an empty log holds there even at 24-way concurrency.
Not a defect; flagged so a future session either uses it or drops it rather than assuming it is
load-bearing.

---

## 3. What this sitting must NOT do

- **No `--allow-persistence-writes`**, and none of the other wear flags. The owner set this
  explicitly. Queue rows R1, R4, R5, R8's reboot arm, R12 and S3 therefore stay blocked.
- **No soak.** Not `scripts/run_bench_soak_tests.sh`, not `--allow-multi-day-rollover-wait`.
- **No threshold re-fitting.** If a heap row in `tests_hardware/` fails, that is a finding. The
  `§7G` placement checks are derived from the measured worst reachable allocation, not from a board
  reading, and must not be moved to accommodate one.
- **No weakening of W5** beyond what §2.1 sanctions, and nothing at all in `src/`.

---

## 4. What to write down

- The verdict line **in full**, including passed / failed / skipped / **deselected**.
- `GET /status`'s `errcount` before the run and after it, and for `WEBSERVER` specifically — every
  `§1D` row asserts it stays empty, and a 413 is raised inside vendored Microdot before any of our
  code runs, so anything appearing there is a genuine finding about this project.
- For W5: whether any worker reported an **exception string rather than a status**, and which kind
  (§2.1's table decides what it means).
- Anything in the `HEAP ` / `MAP ` / `DELTA ` lines that moved, and `retained=` on every `HEAP ` line
  (a non-zero one on a `_retryN` line means the figure must not be used — queue §2A F5).

Then migrate: the row statuses into `REAL_HARDWARE_TEST_QUEUE.md`, anything about the body cap into
`SPECIFICATION.md` Part I.6 as `[HW]`, and **delete this file**. If W5 comes back green, delete
`REAL_HARDWARE_HANDOVER_WEBSERVER_BODY_CAP.md` with it — W5 is the only row keeping it open.
