---
name: bench-routines
description: The order of work for a bench session on the real dev board, and how a code session reads what the bench hands back. Use it at the start of every bench session and whenever you reflash, reset, talk to the board over its REPL or mpremote, save or clear its FRAM error logs, run or rerun a hardware tier, watch a long run, configure the bench host, write or read a hand-back or relay, or diagnose a board that stops answering. It indexes the harness's existing board-control functions so nothing is written twice, and holds the bench's rules, checklists and repeat symptoms.
---

# Bench routines (the real dev board)

Everything here touches real hardware and needs the owner's go-ahead given in the bench session's own conversation;
a reflash needs the owner's OK each time, asked by the bench session itself. `tests_hardware/README.md` is the
technical reference ("Running", "Bench traps", "Persistence-write gating"); this skill is the order of work. The
`work-routines` skill reads the logs and holds the symptom table; `tree-care` sets the host up
(`scripts/_preflight.sh --bench`).

## Standing rules

- One heavy host job at a time, and none while a board run is going: a clean-chroot leg or a twin run on the bench
  host can pause it for seconds, which reads as a board fault.
- Fetch before every new command. The lead's relays arrive on the bench branch, newest entry on top; a relay you did
  not fetch is an instruction you did not follow. `git pull --ff-only`, and stop if it fails.
- Keep full logs local, in git-ignored `logs/`, named `logs/<YYYYmmddTHHMMSSZ>_<step>_<what>.<ext>`. A hand-back
  carries lines, not logs.
- Count every real flash cycle as it happens, one ledger line each: `FC +1 <UTC> <commit>`. A rerun of a step that
  flashes is another cycle; a per-step budget figure is not the count.
- Write no new board-control code before checking the index below: the harness already does it, with its retries.

## Board control: what already exists

Run an ad-hoc call from the repository root as `.venv/bin/python -c "import sys; sys.path[:0] = ['tests_hardware',
'.']; import harness; ..."`; `tests_hardware/kick_then_reset.py` is the model for a small script of your own.

| To | Use | Note |
|---|---|---|
| Find the board | `harness.Board()` (`MPREMOTE_DEVICE`, else the one board by id); `scripts/mpremote_connect.sh`; `uv run toolchain/setup_toolchain.py board` | |
| See who is on the access point | `bench_control.bench_associated_station_macs(BenchBridge().wifi_iface())` | read-only |
| Clear leftover host network state | `BenchBridge().clear_leftovers()` | only this project's fault rules, netem and profiles; brings the AP up |
| Reset it so it rejoins | `.venv/bin/python tests_hardware/kick_then_reset.py`; `harness.reset_board()` | an unkicked reset strands it in its hotspot |
| Bring it back to serving | `harness.restore_board_to_serving(board, BenchBridge(), dut_ip)` | `from bench_control import BenchBridge` |
| Flash an image | `harness.reflash(board, uf2)`, then `harness.restore_board_to_serving(...)` | build with `uv run scripts/build_firmware.py dev`; the restore kicks the AP's old entry |
| A REPL build | `scripts/build_firmware.py dev --no-autostart` | the filesystem must hold no `boot.py`/`main.py` |
| Run code on it | `Board.exec(expr)`, `Board.run_isolated(script)` ("Testing a driver by hand over mpremote") | stops `main.py`: diagnose passively |
| Read its console | `Board.tail_log(seconds)`; `harness.boot_lines()`, `harness.crash_lines()` sort it | replays buffered history: watch `SysUptime`, not repeats |
| Why it reset | `harness.reset_reason(dut_ip)` with the REASON bits | before anything flashes, resets or clears |
| Save its evidence | `error_log_helpers.save_errcount(dut_ip, reason)` first, then `harness.save_fram_raw(board, reason)` | `/status`'s RAM-only fields (`ResetReason`, `SysUptime`) die with the next reset; the dump stops `main.py`, so restore after it |
| Clear its logs | `error_log_helpers.reset_all_error_logs(dut_ip, reason)` | saves first itself; read the section below first |
| Load or heap figures | `tests_hardware/README.md`, "Measuring heap and serving under load" | its probes exist: do not copy them |
| System commands | `tests_hardware/README.md`, "System commands" | each saves the FRAM evidence first |

## Bench host configuration

- `uv run toolchain/setup_toolchain.py env --tier bench` builds the `br0` bridge and its access point; the bridge
  always carries `eth0`'s own MAC, and a test that tears down host networking keeps the recovery timer armed for its
  whole window (CLAUDE.md, the `br0` rules; SPECIFICATION.md B.13).
- Passwordless sudo for exactly the commands the tier runs: `tests_hardware/README.md`, "Prerequisites" item 2.
- `MPREMOTE_DEVICE` and `BENCH_DEVICE` name the board; `BENCH_AP_PASSWORD` is optional. Keep them in an untracked
  env file, never in git, and never print a password.
- The board's standard state (DebugLevel 5, FRAM write-protect clear, no `config_HWTEST_*` file): the session
  fixtures check it; `--repair-standard-state` repairs it as a listed prerequisite write.

## Session start

1. `date -u` for every stamp you write. Fetch; read the relay entries you have not seen; `git pull --ff-only`.
2. `scripts/_preflight.sh --bench`, then `GET /status` answers 200 and `Mode` is STA, not the hotspot. A board in its
   hotspot after a reset usually missed its kick, not a code fault.
3. Save `/status` as `logs/<UTC>_start_status.json`, then `python3 scripts/_errcount_digest.py` on it; note
   `ResetReason` with its REASON bits, `BuildDate` and `SysUptime`.
4. Does the head need a new image? Compare the flashed image's commit (the image record's `commit`, or the board's
   `BuildDate` against the record) with HEAD over the firmware's inputs:
   ```
   git diff --name-only <flashed commit> HEAD -- src ext devices buildgen html js toolchain \
       scripts/build_firmware.py scripts/build_website.sh
   ```
   Empty: the image stays, say so. Anything listed: a new image, which waits for the owner's OK.

## Before a reflash

1. The owner's OK for this reflash, in this session.
2. The session-start evidence saved and, where the step asks for it, the raw FRAM dump.
3. `pull --ff-only` succeeded and the build's image record reads `"dirty": false`: edit nothing while it builds.
4. `harness.reflash()`, then `harness.restore_board_to_serving()` (kick, reset, wait for `/status`). Check the
   board's `BuildDate` against the new record. Add the ledger line.

## Before anything that clears the FRAM logs

A `ResetErrors` PUT, an erase test and the soak tier's `reset_all_error_logs` all destroy the only evidence a reboot
leaves, and a `ResetErrors` clears every source at once. First: save `/status`
(`logs/<UTC>_pre_clear_<what>_status.json`), list every device script run against the board since the last read (a
device script's own FRAM manager overwrites production's first chunk), and copy the newest
`build/archive/<runner>/<UTC>/` out to `logs/`.

## Running, watching and rerunning

- A tier goes through its runner (`scripts/run_bench_hardware_suite.sh`, `run_flash_hardware_suite.sh`, ...); any
  pytest flag passes through. Log the selection with the run: the `-k` text, HEAD and the image's `BuildDate`.
- Watch a long run by its own output, not by polling the board: one `GET /status` cost the board up to 0.74 s of CPU
  on the bench (2026-11-06) and distorts what the run measures. With a monitor tool, follow `tail -n0 -F LOG | grep --line-buffered -E
  'FAILED|ERROR |ABORT|Result: FAIL|memory allocation failed|MemoryError|Unhandled exception'` and act on the first
  line rather than at the end.
- Rerun only what failed: `python3 scripts/_failed_tests.py build/archive/<runner>/<UTC>/run_record.json` prints the
  `-k` for it (`--nodeids` for exact ids; `-k` cannot spell a parameter, so it reruns every parameter of a failed
  function).
- After every run: copy `build/archive/<runner>/<UTC>/` to `logs/` at once (each runner keeps only its newest
  three), then `scripts/_log_verdict.py` on the log and `scripts/_errcount_digest.py START.json NOW.json` against the
  session-start save. Only what the run added belongs to it; the harness's exact rule for a gain between two reads is
  `tests_hardware/error_log_helpers.py`'s `gained_entries()`.

## The hand-back

Append, never rewrite. One block per run:

```
<UTC> step <n> rerun <k>: <selection>; HEAD <short sha>; image <BuildDate>
<_log_verdict.py's lines for the run's log>
errcount added: <_errcount_digest.py's changed lines, or "none">
ResetReason after: <n> (<REASON bits>); flash cycles today: <n>; logs/<file names>
status: confirmed | inferred | not traced, and why
```

Never paste a raw log, a whole console, a FRAM dump or a picotool progress bar into it; name the file under `logs/`.
A code session reads a bench log without fetching it to disk: `git show <ref>:<path> | python3
scripts/_log_verdict.py -`.

## Bench symptoms diagnosed more than once

| Symptom | Known cause | Confirming check |
|---|---|---|
| Board in its hotspot, unreachable, a whole tier passes 0 tests after a reset | A reset with no kick leaves a stale station entry at the access point | Was the last reset kicked (`harness.kick_then_reset()`, `kick_after_reset()`)? The AP's `journalctl` lines show the station's comings and goings (`tests_hardware/README.md`, the stale-entry rows) |
| A FRAM log entry the test cannot have caused | Carried over from an earlier test or device script | `_errcount_digest.py START.json NOW.json`: an entry already in the start save is not this run's; read the test's `provokes_log` |
| `ResetReason` 2 | FORCE bit: a harness reset after a script consumed the boot. TIMER bit: a real watchdog expiry | Read the REASON bits beside it (`tests_hardware/README.md`, "Bench traps") |
| The DUT stops answering while you diagnose it | Your own `mpremote exec`/`run` stopped `main.py` | Diagnose passively: `hard_reset()`, `Board.tail_log()`, watch `SysUptime` ("Bench traps") |
| Resets or no status at the connection ceiling | `max_connections` reached | The all-small-bodies control, two minutes ("Bench traps") |
| A host-only stage touches the board | The tier's session fixtures reach for a board | Run it with `--twin`, or point `MPREMOTE_DEVICE` at a path with no board (`/dev/no-pico-serial-device-detected`) |
| Timeouts and twin feed gaps on the bench host only | The host is loaded (a chroot leg, parallel twins) | `/proc/loadavg` and the `== Test parallelism:` line; rerun with nothing else running |
