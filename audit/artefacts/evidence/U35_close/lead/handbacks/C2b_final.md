C2b hand-back (lane C, branch audit/u35-c, worktree S/wt-u35c). Commits: d6928f7 and 0547def, on top of b6ef8d3. Nothing is uncommitted. Nothing was pushed. No relay line written. About 67 tool calls.

**Steps**
- **First item, done.** On b6ef8d3: the 12 pre-commit checks plus readers gave 829 passed. dns 47/47 and ntp 189/189 passed at -1 and 32768, zero memory markers.
- **DrivenTime fact, applied (d6928f7).** With `sleeps=True`, a module that has no `time` gets only its `asyncio` driven and is lent no `time`. Without sleeps, such a module is still refused with AttributeError. `_LentTime` is removed from the dns test.
- **64, applied (d6928f7).** The join test runs under `DrivenTime(asy_udp_socket, sleeps=True)`: `run_until` waits until A is parked in its backoff holding the lock, then `advance(_RETRY_BACKOFF_MS)`. Assertions unchanged; the run is now bounded by `_CONNECT_BOUND_S`.
- **65, partly.** Committed: the ready()/recvfrom-with-no-deadline half, with the step's invariants. That covers the lock, `_sock is None or connected`, a following good connect, and the ledger after teardown.
  - Held back: the `_connect()` half. It fails on the product: "cancelled after 1 turns: a socket left half set up". The teardown adds "the next connect to a good address failed".
  - **Defect at src/asy_udp_socket.py:56-76** (class 6). A cancel during the backoff `sleep_ms` at :73 skips the self-heal at :75-76, so `_sock` stays set with `connected` False. Every later `_connect()` then skips setup, until someone calls `disconnect()`.
  - Today this is latent in every mode on every device. Every caller (dns/ntp per-request sockets, and captive DNS's server loop at src/asy_captive_dns.py:142) disconnects in its own `finally`.
  - Fix checked in a scratch copy: move the `if not self.connected: await self._disconnect_locked()` block into a `finally:` of that try. The full sweep then passes 65/65.
  - The file is in no lane (lanes.py), so the lead routes it. The fixed src and the two-half test are in S/u35/laneC/bite_udp/fix/.
- **66 / R-2, applied (0547def).** `_DrivenClock`/`_Timer` are replaced by `DrivenTime(asy_webserver_service, sleeps=True)`. `_driven()` now uses `run_until`, with a driven 60 s limit. Readers use `_driven_sleep` (the module's own asyncio.sleep).
  - The feeder now sleeps on the module's asyncio. Before that, its real 10 ms sleep left `run_until` with no wake, and the load test failed at virtual 60000 ms. Its gap is still measured in real time.
- **67: not started.** Goes to C3.
- **OF-211 fallback: not done.** Goes to C3: U27's held-responder audit over every socket file at both stages, then the D2 E.1 line under `## D`.

**Seen failing first / bites** (scratch copies, nothing planted committed)
- test_driven_time's new test failed on the base `__enter__` with AttributeError. Bite: tolerating a missing `time` without sleeps too fails it at `assert refused`.
- udp sweep, socket-drop leak planted in `_poll`: "1 socket(s) left open".
- udp join test, `advance(backoff - 1)`: TimeoutError.
- webserver: a planted 0.999 s per-call timeout fails the expect-100 test.

**Checks:** ruff clean. mypy (no args, and src tests tests_hardware/device_scripts) at 0, twice. Pre-commit checks plus readers: 829 passed before each commit.

**Runs** (all rc 0, zero MemoryError and zero "memory allocation failed"; RUNS.md pids 16549, 1338, 26794 and one rerun)
- All 21 `_fake_time` importers green at both stages on d6928f7's tree.
- udp, base → head: 6.44/6.44 → 5.97/5.95 at -1; 6.51/6.42 → 5.95/5.94 at 32768. Faster.
- webserver_connections, base → head: 1.70/1.21 → 1.41/1.44 at -1; 1.33/1.38 → 1.35/1.61 at 32768 (+9 %, 0.13 s, within both bars).
- test_driven_time 0.05/0.05; dns 0.89/0.90.

**Decisions (agent, 2026-10-21):** hold back 65's connect half until the product fix lands; the feeder reads the module's asyncio (so the EAGAIN test stays on real time); the virtual limit is untagged, like ROUNDS.

**Modes:** test-only commits. STA, AP, Silent, Off and USB are unaffected on every device.

**C3 starts from 0547def.** Owed:
- 67 (sweep over `_serve()`), then D.15 order for test_asy_webserver_connections.py and test_asy_udp_socket.py;
- 65's connect half, with the src fix once routed;
- the OF-211 audit and its `## D` line.

No allowlist rows orphaned; no tunables added or removed.

nothing of mine is running
