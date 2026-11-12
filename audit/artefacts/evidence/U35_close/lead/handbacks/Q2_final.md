Q2 hand-back (lane Q, the lane's last block). Branch audit/u35-q in S/wt-u35q, head 53b10dc (on top of 5fba3da). Nothing uncommitted, nothing pushed, nothing of mine running. About 66 tool calls.

**Steps by verdict**
- **Q1's class-4 item (src/asy_udp_socket.py:76): no change, state stated.**
  - A False from `_disconnect_locked()` leaves nothing behind. It clears `_sock`, `poller` and `connected` before its unregister and close (:84-87).
  - So the next `_connect()` sees `_sock is None` (:57) and builds a fresh socket.
  - The caller learns of the failure through `connected` False. `ready()` returns False (:127), so recvfrom gives (None, None) and write/sendto give None. Captive DNS then logs `_ERR_INIT` (asy_captive_dns.py:124-125), and NTP logs `_ERR_NTP_NOT_SENT` (asy_ntp_client.py:261-263).
  - In the pinned v1.29.0 source, neither half of the teardown can fail:
    - `poll_unregister` never raises (extmod/modselect.c:505-524).
    - lwIP's MP_STREAM_CLOSE returns 0 (modlwip.c:1600, 1668-1710), and `mp_stream_close` raises only on MP_STREAM_ERROR (py/stream.c:444-452).
    - The Unix port's close also returns 0 (ports/unix/modsocket.c:135-149).
  - A scratch run planted a failing unregister on a failed bind (S/u35/laneQ/q2/udp_selfheal.log). Results: ready() False; nothing left behind; the half-built socket was still closed; the next `_connect()` connected.
- **71: applied (53b10dc).** `test_cancelling_a_wifi_task_at_each_await_leaves_the_mode_lock_free` sweeps three paths over fresh clients with one-yield sleeps:
  - `_run_sta_mode()`, 11 counts; `_run_silent_mode()` with an attempt due, 11 counts; `_flash_led()`, 5 counts (it never ends).
  - Invariants: the mode lock is free, `_ledflash` is None or done, the LED is as the cancel found it, and the LED is dark while silent.
- **79: applied (53b10dc).** `test_cancelling_run_at_each_await_disconnects_and_logs_nothing` sweeps `run()` on `_FakeUDPS` with one query, 6 counts.
  - Invariants: `disconnect()` runs exactly once if `run()` began, and never if it was cancelled before its first step; no recvfrom after it; ErrCount 0.
  - The replies per count read [0,0,0,1,1,1], so the sweep crosses the answer.
  - `_FakeUDPS` now counts its disconnects, and `disconnect_called` is a property derived from that count. `_RaisingDisconnectUDPS` was updated to match.
- **The audit: done, green.** Details are under the relay line below.

**Seen failing.** Both sweeps passed at once, so they were bitten in scratch copies. Each failed naming its behaviour; the copies are deleted:
- b71a, lock released only on the normal path: "cancelled after 1 turns: wifi_mode_lock is still locked". Only the new test caught it.
- b71b, toggle unguarded while silent: "…the LED lit while silent".
- b71c, the flash task turns the LED off when cancelled: "…the cancel changed the LED from True to False".
- b71d, an orphaned flash task: "…a flash task left running".
- b79, skipped release in run()'s finally: "cancelled after 1 turns: disconnect() called 0 times, run() began 1".

**Runs** (all rc 0, no retries, zero MemoryError and zero "memory allocation failed" in every log)
- Paired base→head, two rounds each. Neither file grew:
  - wifi: 24.44/24.45 → 24.45/24.44 at -1; 24.84/24.83 → 24.79/24.77 at 32768.
  - captive: 25.58/25.67 → 25.57/25.58 at -1; 25.58/25.60 → 25.59/25.59 at 32768.
- Pass counts: wifi 269/269, captive 65/65 at both stages.
- Pre-commit: ruff 0; both main mypy passes 0 (264 and 230 files); the 12 checks: 799 passed.
- The 17 scans plus readers: 1210 passed, 125 s. Readers: lock_order, radio_shape_corpus and third_party_attribution (by name); port_bands, exception_handler_contract, microtest, threshold_runner, config_paths_resolve and test_sh (they scan the test files as a set).
- RUNS.md: pids 28987 and 1994, both done rc 0.
- tests_scripts/test_twin_record.py is still expected red from Q1's src change. Not run.

**Relay line written under `## D`.** It gives D2 the E.1 rule and the audit's result.
- No deterministic guard exists, so the held-responder audit is the check behind E.1's port sentence (SPECIFICATION.md:4799-4802).
- Audit: 56 socket files, the 4 PER_DEVICE ones on all 6 devices, at both stages. Beside the held 127.0.0.1:123 NTP responder and a :53 captive DNS: 152 runs, all rc 0 at the first try, 0 memory markers.
- 0 NTP and 0 DNS requests reached the holders.
- "ntp took False" in hold.log is a harmless second bind attempt: the responder's constructor already holds the port. Only EADDRINUSE returns False. U27's log shows the same line.

**Silent-failure scan** of my two files and the udp item (classes 1-7; STA, AP, Silent, Off, USB, boot, twin shutdown): nothing new. The udp class-4 item is safe as built (above). Test-only changes: no effect in any mode or on any device.

**Decisions (agent, 2026-10-21)**
- The audit set is the union of U27's NTP-naming files and every tests/test_*.py that names a socket, UDP, DNS, NTP, webserver, wifi or sensortask module. This is the broader, safer set.
- The holder also holds :53, because the finding names both ports.
- The holder and each test share one namespace, one test at a time, with a load gate of at most 4 heavy processes.
- I kept `disconnect_called` as a property over the new count, so the fake does not record the same fact twice.

**For the lead:** LEAD NOTES 36, which the brief cites, is in neither lane_plan.md nor lead/lead_notes.md. I worked from the brief's text.

Lane Q's complete checks are done; no lane-Q work is left.

Logs: S/u35/laneQ/q2/ (p_*.log, bite_*.log, scans.log, pre_*.log, udp_selfheal.log, audit/audit.tsv, audit/audit.out, audit/hold.log, audit/a_*.log).