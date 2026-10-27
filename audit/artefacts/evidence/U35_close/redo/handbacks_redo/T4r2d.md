T4r2d hand-back, saved by the lead from the message it sent (2026-10-27). Commit 5756c785 on audit/u35-t4r2d (on aa146d83).

T4r2d hand-back. Worktree S/wt-u35t4r2d, branch audit/u35-t4r2d. One commit, **5756c785**, on aa146d83. Nothing is pushed and nothing is uncommitted. About 70 tool calls; both of my items are finished.

**Fold (1), done (5756c785).** The scenario `client_gone_mid_response_is_counted` (family webserver_requests, needs_site, its own boot):
- It GETs every route plus the staged site's files (`_site_paths`, read from the frozen_html.py header lines), then picks the largest body, /js/app.js at 28,782 B.
- It checks that body is bigger than the pinned send buffer plus the client's receive floor (4,608 + 2,304). If no body is, it raises UnmetPremiseError (`_largest_past`).
- It requests that body on a raw socket, receive buffer at its floor, reads only the status line, then resets with SO_LINGER 0.
- It asserts: HTTPDropped is exactly before+1; WEBSERVER's newest entry is W 48; the following GET /status is served; the reset connection logged one SNDBUF_PINNED line; every accepted socket was pinned at the host's floor (read independently by CPython) and below its size at accept.
- Fact re-checks: the Unix port has no `socket.SO_SNDBUF` and no getsockopt (modsocket.c:722-727). Linux doubles a request and clamps it to its floor: 4,608 on this kernel. rp2's TCP_SND_BUF is 6,400 B (lwipopts_common.h:94). A loopback socket starts at **3,939,840 B**, so without the pin a whole page fits the kernel at once.

**Knob:** `--test-pin-send-buffer`, TestFlags field 14, `_test_pin_send_buffer` and `_test_send_buffer` (libc getsockopt through ffi). It comes with the usage text, a README row and its `_FLAG_TABLE` row (tests_scripts/test_twin_runner_test_flags.py:18). The table is a registry, but please review the row.
- Its test runs a real start_server/accept through the rebound `_serve`. It checks: pinned < size at accept; pinned >= 2048 (socket(7)); a request of 2 reads back the same floor; the reader matches tcp_wmem[1] on a fresh socket.
- New host tests: `_largest_past` (pick and skip) and `_site_paths` (paths, and a RuntimeError when the module lists no file; that is a silent-failure scan fix, class 4, twin and tooling mode).

**Red first** (logs in S/u35/laneT/t4r2d/):
- Knob file on the base runner, both stages, 45/47: "TestFlags() takes 13 positional arguments but 14 were given" and "no attribute '_test_pin_send_buffer'" (logs/red_knob_*).
- Plant `_peer_gone` dropped from the write path (asy_webserver_service.py:421, scratch copy): dev, both stages, "HTTPDropped 0 -> 0" (scen/plant_peer_gone_*).
- Plant: the knob does not pin. Dev, both stages, red at the pin check: 3939840 instead of 4608 (scen/plant_no_pin_*). In that run the drop was still counted: unpinned, the twin writes slower than the client resets, so the outcome rests on timing.
- To prove the pin is what holds the write open, a scratch-only 1 s pause before the reset:
  - unpinned + pause: "HTTPDropped 0 -> 0" at both stages (scen/plant_no_pin+pause_*);
  - pinned + pause: PASSED at both stages (scen/plant_pause_*).
- Host-test bites (`<=` changed to `<`, `.gz` kept): 2 failed. Without the refusal: "DID NOT RAISE".

**Green:**
- Fold (1) on dev at -1 and 32768: 6.9 s and 7.0 s; on arzi: 5.6 s and 5.6 s (scen/g1final_*).
- Knob file: 47/47 at both stages, zero memory markers (logs/green_knob4_*).
- Timing, side by side with HEAD's file (logs/timing.txt): 1.39-1.45 s against 1.39-1.40 s at -1, and 1.46 s against 1.45-1.46 s at 32768. That is at most 4 % slower, under the 10 % limit.
- Checks: lint_direct rc=0; twin mypy 53 files and host mypy 309 files, both cold, 0 issues. The cap, citations, vocabulary, tunables and conventions checks plus 13 static readers: 990 passed. The 8 twin-starting readers (private toolchain): 1077 passed (logs/checks3/4.log).
- Two findings fixed along the way: an "accepted" phrase that tripped the vocabulary check, and a 121-character comment line that counts as two.

**Item 5, done, proof only (no file change, so no commit):**
- Scratch plant: the 2nd PUT /system sleeps past the outer cap, and the reclaim trace is held for 4.9 s.
- Measured in the twin logs: reclaimed after 14.94-15.03 s (cap 15 s), trace held 4.95-4.96 s, closed at 19.90-19.98 s.
- Old timeout (15 + 2.129 = 17.13 s): red at both stages, "a load thread raised", `TimeoutError('timed out')` (scen/p5_old_*).
- Today's timeout (24.26 s): PASSED at both stages, 68.0 s and 72.6 s (scen/p5_today_*).

**Notes for the lead:**
- No new tunable, no allow-list row, no write site added or changed, no stale SPEC sentence (SPECIFICATION.md:561, :1049 and :8395 still hold).
- Optional: the README fidelity table's Network row (digital_twin/README.md:249) could name the pin. Not done, since that is the twin record's.
- The private toolchain S/tc-t4r2d and the plant tree are deleted. Every run has its RUNS.md lines; the seq_green1 wrapper (about 30 s) has none of its own.

nothing of mine is running
