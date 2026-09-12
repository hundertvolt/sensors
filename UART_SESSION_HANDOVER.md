# UART work — handover to a non-hardware session (2026-09-12)

**Temporary file. Delete it once the open items below are closed** and anything permanent has moved
into `SPECIFICATION.md`/`BACKLOG.md`/`tests_hardware/README.md`.

This session ran on the real bench Pi4 with the UART crossover jumper. The next session is assumed
to have **no hardware**. Everything below is written for that: what is already proven, what is still
open, and specifically which parts can and cannot be worked on without a board.

---

## 1. State of the branch

`claude/uart-protocol-promotion-ttaheg`, last pushed commit `c82149f`. **One uncommitted change is
in the working tree** — see §2, it is the fix for the currently red CI and should be committed first.

Everything is green locally except the item in §2. Verified this session:

| Context | Result | Needs hardware? |
|---|---|---|
| `scripts/lint.sh`, `scripts/typecheck.sh` (3 passes) | clean | no |
| `scripts/test.sh` (60 files) | ALL PASSED | no |
| `scripts/run_digital_twin_ci.sh` (11 runs) | PASSED | no |
| `npm run lint` / `typecheck` / `lint:html` / `lint:css` | clean | no |
| `npm test` (Vitest, real Chromium) | 702 tests, 11 files | no |
| `tests_scripts/` (pytest) | 71 passed, 2 skipped | no |
| Hardware: UART tiers alone | 8/8 | **yes** |
| Hardware: full flash+bench sweep | 96 passed, 2 known skips | **yes** |
| Hardware: mid soak ×3, short soak | 4 passed each | **yes** |
| Clean chroot, trixie (GCC 14.2.0) and noble (GCC 13.3.0) | both passed | no (needs root) |

## 2. OPEN AND URGENT — CI is red, the fix is written but uncommitted

`tests/test_uart_comm_hazard.py` is modified in the working tree. **Commit it.** CI run
`34710413595` failed on exactly two of this session's new tests:

```
FAIL test_sustained_hammering_never_degrades_or_grows_the_heap_nocrc
  AssertionError: 64 bytes retained across 150 hammered transactions
FAIL test_hammering_a_faulted_link_never_raises_and_still_recovers_nocrc
  AssertionError: 128 bytes retained across a second 30-failure burst
```

**Cause was the test, not the code.** Both assertions used an *absolute* `gc.mem_alloc()` delta
bound (a few frames wide), chosen because both measured exactly 0 bytes on the bench. A
GitHub runner's interpreter caching sprinkles a few dozen bytes that this host does not, so the
absolute bound was host-dependent. In rate terms CI saw 0.43 B/transaction and 4.3 B/failure —
nothing at all.

**A leak is a rate, not a total**: it scales with work done, while caching noise is a fixed sprinkle.
The working-tree fix asserts per-operation rates instead (`< 1.0 B/transaction`, `< 16.0 B/failure`),
both far below a real leak — one retained frame is 13+ B/transaction, and the failure path's own
one-time cost is ~114 B/failure.

**The new bounds were verified to still bite**, not merely to go green: injecting a deliberate
16-byte-per-transaction leak into `_note_valid_frame()` fails all three memory tests at 380
B/transaction and 433 B/failure. Source was restored afterwards; `git diff src/` is empty.

**What the next session must do**: commit the working-tree change, push, confirm CI goes green.
`scripts/test.sh` was stopped mid-run at handoff, so re-run it first. No hardware needed for any
of this.

## 3. OPEN — errno 32 blind spot, deliberately documented rather than fixed

Owner decision (2026-09-12): keep it simple, do not add coupling. **Do not "fix" this without
asking.** Full account: `SPECIFICATION.md` Part J.6, `UART_C_PORT_CHANGELOG.md` B26.

`_resync()` gates the "bytes arriving but no frame ever valid" diagnostic on
`drained and self._valid_frames == 0`, but `readinto_until_complete()` has already consumed the
short frame's bytes while waiting for a full-length one and discarded them on timeout — so
`_drain()` finds an empty line. Measured `drained == 0` at all five resyncs against a genuinely
`payload_size`-mismatched peer.

Consequence: errno 32 fires for a peer spewing onto an idle line (a bad baud rate, typically) but
**not** for a speak-when-spoken-to peer, which instead shows repeated errno 22 plus wrnno 10. That
second pattern is the signature the C-port reconciliation should look for.
`_check_a_peer_that_never_produces_a_valid_frame_is_diagnosed` pins the *current* behaviour, so it
inverts if anyone closes the gap.

Both candidate fixes were rejected as more coupling than a logging line is worth: a driver flag
existing solely for `asy_uart_comm` to read, or changing `readinto_until_complete()`'s sentinel
contract for every caller.

## 4. OPEN — the fakes cannot catch a clamp regression

Already in BACKLOG.md. `tests/machine.py` and `digital_twin/machine.py` now expose
`would_have_blocked_bytes`, which counts what a real read would have blocked on — but neither models
the *wait* itself. A regression of the F.5.8 read clamp would still pass both tiers silently.
Modelling the wait properly is test-infrastructure work and **needs no hardware**.

## 5. Two standing rules established this session

- **Every hazard check runs in both CRC modes.** `tests/test_uart_comm_hazard.py` registers each
  `_check_*` twice (`_nocrc`, `_crc16`) — 48 checks, 96 tests. Two are single-mode by construction
  (`_MODE_SPECIFIC`), because their subject *is* one configuration. The deployed link runs
  `CRC_Pass`, so the no-CRC path is the one in the field.
- **Every hammer runs under `gc.threshold(-1)` as well as 32768** (CLAUDE.md's rule). `-1` is
  MicroPython's real default; a threshold is defense in depth, never the fix for a design that
  still needs one big allocation.

## 6. Measurement traps that cost real time — read before writing any memory or timing test

Every one of these produced a confident, stable, wrong number first.

- **Never bisect a twin soak's runtime to a code change** (`SPECIFICATION.md` Part E.7). It gives a
  repeatable answer that is wrong — it once attributed a regression to a function with zero call
  sites reached. Count the operation instead.
- **An absolute heap-delta bound is host-dependent.** §2 above. Assert a per-operation rate.
- **The twin's `UARTLink.wire_log` is unbounded**, one byte per delivered byte — ~15-95 kB over a
  few hundred transactions. It reads as a leak in the code under test. Clear it in the measurement
  loop.
- **An asyncio loop-latency probe cannot tell "loop idle on a timer" from "loop blocked."** The
  driver's own cooperative `sleep_ms(poll_wait_ms)` puts both at ~2 ms. Time the C calls directly.
- **A probe that reads its peak before the watchdog task next runs reports 0 for everything.** Give
  it a turn (`await asyncio.sleep_ms(0)` a few times) before reading.
- **`I2C.scan()` is synchronous** and blocks the loop for a 128-address sweep. Using it as "bus
  load" models nothing production does — it inflated a measured worst-case RTT from 112 ms to 574 ms.
- **Cross-test contamination is real**: one process, one task queue, no parent/child tracking in
  MicroPython asyncio, so listeners parked by earlier tests keep allocating. Isolate before
  believing a per-test number.
- **`ErrNum` mixes errnos and wrnnos in one ring sharing a number space** (wrnno 10 = resync,
  errno 10 = bad `payload_size`), and every fault also resyncs, so the newest entry is almost always
  the resync warning. Filter on `ErrType == "E"`.
- **Nested `asyncio.run()` segfaults the Unix port** — no traceback, no `N/N passed` line, the file
  just dies mid-run. Any helper that drives its own `run()` (`hazard_pair()`, `_clean_ack_bytes()`)
  must be called from synchronous test scope only. Hit twice this session.

## 7. What the next session can and cannot do

**Can, with no hardware**: everything in §2, §4 and §6; the whole mock and twin tiers; lint,
typecheck, `scripts/test.sh`, `scripts/run_digital_twin_ci.sh`, the web tier, and CI.

**Cannot**: anything under `tests_hardware/`. Those need the bench Pi4, the board and the crossover
jumper, **and the project owner's go-ahead given directly in that session's own conversation**
(CLAUDE.md hard rule — a go-ahead given to this session does not carry over). The three device
scripts added this session (`uart_read_never_blocks_the_loop.py`, `uart_idle_poll_rate.py`,
`uart_link_under_concurrent_system_load.py`) are all hardware-only.

**Note on the web tier**: `toolchain/setup_toolchain.py env --tier generic` now installs the
`.nvmrc`-pinned Node itself (from nodejs.org, checksum-verified, into `$PICO_TOOLCHAIN_DIR/node`),
then `npm ci` and the Playwright Chromium build. It defers to a matching Node already on `PATH`.
Deliberately not apt: trixie ships Node 20 against this repo's pinned 22.
