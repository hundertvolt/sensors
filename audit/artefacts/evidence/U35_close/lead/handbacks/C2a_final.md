C2a hand-back (lane C, branch audit/u35-c, worktree S/wt-u35c). Commit b6ef8d3, on top of feae592. Nothing is uncommitted. Nothing was pushed or relayed.

**Steps**
- **40, applied.** `test_cancelling_a_resolve_at_each_await_leaves_no_socket_open` runs a real loopback fake server on a driven clock with 1 ms turns. After every cancel, a `SocketLedger(asy_udp_socket)` shows every product socket closed. The test also asserts that cancels landed both before the query left and while the reply was awaited, that the completed count resolved, and that `wakes() == []`.
  - Deviation: the fake server is closed by the sweep's teardown rather than checked as an invariant. It is test rig, not product.
- **55, applied.** `test_the_sync_task_survives_a_cancel_at_every_await` runs the real `_sync_loop()` and attempt over the file's scripted fake socket. A new `gate_ms` makes each send and receive a driven 5 ms wait. `endless=True`, `max_steps=16`.
  - Invariants: `wifi_mode_lock`, `_data_lock` and `cfgmgr._config_lock` are free, and every fake socket is disconnected.
  - Phases asserted: before the socket, in the write, in the receive, and after the sync.
- **56, applied to six sites, not the brief's four.** The step text says "every" `wait_for(…, 5)`, so it covers the plain `server_task` form and the `served` form. Sites (base lines): :2723, :2775, :2813, :2827, :3090 and :3121, plus the discarded `serve_once(None)` at :2818. All now `assert … is True`.
- **D.15, done last.** The dns file's 16 module-level helpers are now in alphabetical order. They were moved with no content change (checked by line multiset).

**Seen failing and bites** (scratch copies; nothing planted was committed)
- Before the fix, the ntp sweep failed with `AttributeError` (`PrintLogHistory` has no `_write_lock`). I dropped that lock from the invariants.
- dns, `finally`→`else` in `resolve_ipv4`: "cancelled after 1 turns: 1 socket(s) left open".
- ntp, the same plant in `_fetch_ntp_reply`: "cancelled after 1 turns: 1 socket(s) left open".
- ntp, `async with` replaced by a bare acquire/release: "cancelled after 1 turns: wifi_mode_lock is still locked".
- ntp, `serve_once` returning `None`: all 5 serve tests fail at the new asserts.

**Checks**
- ruff clean. mypy at 0 with no args and with `src tests tests_hardware/device_scripts`.
- The 12 pre-commit tests_scripts checks plus microtest and radio_shape_corpus: 829 passed. That run was before the 2-line `isinstance` fix; the fix adds no comment, import or decision text.

**Runs** (all rc 0; zero MemoryError and zero "memory allocation failed" in every log)
- Paired base/head (pid 24581, in RUNS.md), seconds:
  - dns: 0.91 → 0.93 at -1; 0.88 → 0.92 at 32768.
  - ntp: 24.13 → 24.04 at -1; 24.63 → 24.53 at 32768. ntp did not grow.
- Repeated after the disk-full window: the dns run at -1 and the dns bite (both first ran at 17:14).

**OF-211**
- No deterministic guard can be built in lane C's files. A runtime guard needs a choke point that every unit socket file passes through: `tests/microtest.py`, `digital_twin/unixport/_unix_port_udp_addr_shim.py` or `tests/_udp_port_redirect.py`. None of those is lane C's, and the shim also serves the twins, which use the real ports.
- A socket wrapper is not an option either: polling a non-fd object hangs in CI (CLAUDE.md's hang rule).
- The fallback is not done. U27's held-responder audit has to be re-run over every socket-touching file, and then the D2 E.1 line relayed under `## D`. Both are owed by C2b; no relay line written.

**Decisions (agent, 2026-10-21)**
- Step 56 covers all six `wait_for` sites plus the discarded `serve_once(None)`, per the step's "every".
- The ntp sweep uses the real attempt with a gated fake socket, not a fake attempt; it is stronger, with the same invariants.
- `_INTEGRATION_CFG` is now a module constant, shared by `_make_integration_client` and the sweep.
- The fake server's and fake socket's waits read a `_Clocked` stand-in, the same pattern as test_shared_helpers.

**Facts owed**
- C2b/C3: `DrivenTime.__enter__` reads `module.time` unconditionally. `asy_udp_socket` has no `time`, so `test_asy_dns_client.py` lends it one with `_LentTime`. A `getattr` in `_fake_time.py` (C's file, not this block's) would remove that workaround; captive/udp sweeps will hit the same thing.
- No allowlist rows orphaned; no tunables added.

**C2b's start state:** b6ef8d3. dns and ntp are done except OF-211's audit and relay line. udp and webserver_connections are untouched; R-2's `_DrivenClock` removal is still pending (C1's fact).

Nothing of mine is running.
