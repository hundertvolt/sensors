N1 hand-back (lane N, branch audit/u34-n, worktree S/wt-u34n, from 147ea3f; nothing pushed, nothing uncommitted)

Commits: 1b1da7e (the UDP header), then d6db0e7 (the method removal with its tests).

Steps:
- Step 13 applied (1b1da7e). src/asy_udp_socket.py:1-3 now carries the packet's exact three lines (108/97/86 chars) with the discussion link. Three lines stayed three. The docstring had already landed (P1). mpy-cross v1.29.0 output, both -march=armv6m and plain, is byte-identical at base and head (sha256 9f455262…, S/u34/laneN/mpy_hdr/).
- R-7 applied (d6db0e7, one commit):
  - Removed `write_and_recvfrom()` and its `range(tries)` guard. asy_udp_socket.mpy goes from 2195 to 2056 B; nothing else in the image changes.
  - Deleted the retry-budget section (4 tests), the tries=0 test and the malformed-tries test.
  - Rewrote the three NTP-pattern tests onto a `_ntp_shaped_fetch()` helper. It follows `_fetch_ntp_reply()`'s shape: write() checked, then recvfrom() into `_NTP_PACKET_LEN` read from source, then disconnect() in finally. Each test asserts (sent, reply, torn_down). The garbage reply is now one 27-byte copy so it fits the 48-byte buffer.
  - Reworded the comments at the section head, the zero-length test and the "Sixth pass" block.
  - The two allow-listed texts (old :1364 and :1831) are unchanged.
  - Proof: `git grep -n write_and_recvfrom -- . ':!arduino' ':!audit' ':!legacy'` now finds only SPECIFICATION.md:6280 and THIRD_PARTY_LICENSES.md:196. The main mypy pass is green in both forms (no args: 262 files; `src tests tests_hardware/device_scripts`: 228). ruff is clean.
- Step 3 runs: all done, results below.

Decision (agent, 2026-10-21): I also removed `_ATTEMPT_TIMEOUT_MS`/`_EXHAUST_TIMEOUT_MS` and their `@tunable` tags (l1.asy_udp_socket_attempt_timeout_ms, l1.asy_udp_socket_exhaust_timeout_ms). Only the deleted tests read them, and the test file cannot be split across blocks.

Red check, waiting on N2: tests_scripts/test_tunables_register.py::test_the_tags_and_the_part_n_rows_agree says `SPECIFICATION.md:11892: l1.asy_udp_socket_attempt_timeout_ms is a tuned row, but no file carries its @tunable tag`, and the same for :11893 (exhaust). For N2:
- delete those two register rows;
- drop "(and so `write_and_recvfrom()`)" at SPEC:6279-6280.
The other 11 commit checks pass at both commits; the only warning is the datasheets/ submodule one. test_twin_record goes red as expected (not run; the lead re-records it).

Seen failing / bites: removing dead code needs no seen-failing test. The rewritten tests pass at once, so they are guards, and I bit them in scratch copies (S/u34/laneN/bites/, nothing committed):
- write() returns None: all 3 NTP tests fail;
- recvfrom()'s failure sentinel turned into b"": no_server_reachable fails;
- disconnect() reports False: all 3 fail;
- recvfrom() cuts one byte: success and garbage fail.
Each fails at its final assert.

Runs: base and head paired (wt-u33plan vs wt-u34n), seconds at -1 / 32768, all rc=0, 0 memory markers:
- test_asy_udp_socket: 7.24/7.24 → 6.43/6.47 (70 → 64 tests)
- test_asy_dns_client: 0.87/0.87 → 0.88/0.86
- test_asy_ntp_client: 24.57/24.91 → 24.53/24.72
- test_asy_captive_dns: 25.59/25.61 → 25.59/25.59
- Twin dev integration, head only: 23.24/24.49 (4 passed, 8 skipped, rc 0), against U32's 22.95/23.65. Its first try died at import because build/generated_src was stale after my src change (the require_fresh guard). I ran rebuild.sh and re-ran it.
- The paired driver was pid 18646, logged start and done in RUNS.md. Logs are in S/u34/laneN/. Nothing of mine is running.

Silent-failure scan (both files, all classes; modes STA, AP, Silent, Off, USB, plus a stale generated tree): nothing new.
- The only class-1 site was the removed guard catching TypeError but not OverflowError. The resolver's own guard catches both (asy_dns_client.py:148-149), so that class is now gone from the project.
- A stale tree fails loudly.
- Effect per mode: STA (NTP, DNS) and AP (captive DNS) keep their unchanged write()/recvfrom()/sendto() calls; Silent and Off send no UDP; USB is unaffected.

Relay: wrote `<UDPHDR> 1b1da7e` under `## N` in S/u34/relay.md.

For the lead: no allowlist rows are orphaned. THIRD_PARTY_LICENSES.md:189-198 still describes the paired write+read method; that edit is lane A's, under R-7's sentence.

Next block (N2) starts from d6db0e7. N1's files are finished. N2 still has to do:
- the SPEC edits (steps 9 and 15, the two tunable rows and the method mention, both quoted above);
- N's complete checks.