# W3b brief: firmware-fact docs and one bounded removal (lead, 2026-11-12)

S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
Worktree: S/wt-w3b (branch audit/w3b, at 0e27f1c1). Work and commit ONLY there. Never push. No hardware.

## Owner rules that bind this unit
Minimal complexity, no dropped features, no known or new gaps, no runaway chains, no drift into fixing tests; the
focus is firmware and buildgen. So: docs state current firmware facts; the one code change is a bounded removal.
Do exactly the items below. Anything else you notice: list it in your hand-back, do not change it.

## Hard constraints (binding, verbatim from the lead)
- Never read `arduino/`: put `':!arduino'` in every git grep and git log. Never edit `ext/`, `legacy/`, `python/`,
  `modules/`, `audit/`.
- Filter EVERY view or grep of repo text through `grep -v -i -E "hotspot|passw|psk|ssid|wificonfig|credential"`.
  Never view these files whole: devices/*.toml, generated modules, SPECIFICATION.md, CLAUDE.md, BACKLOG.md,
  README.md, src/asy_wifi_service.py, PROJECT_AUDIT_PLAN.md. Read them by line ranges or greps, filtered. A line the
  filter hides is unread, never evidence of absence. Never print, copy or write any Wi-Fi credential or password.
- Never open anything under /root/.claude/. Bound every recursive grep with a path list and `timeout 60`.
- No mpremote, picotool, nmcli, iw, iptables. Do not run the test suites (the lead runs the checks). No network.
- Text outside audit/ cites no audit IDs (OF-nn, U35, W3b, FINDINGS ...). Every comment block (Python `#`, docstring)
  is at most 3 prose lines. Docs hold current state, not history ("was", "used to", "removed in" are history).
- Commit with `git -C S/wt-w3b commit -F <msgfile>`; the message ends with these two lines:
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01BWfjT6GSD7bxCP57j86vB8
  One commit for item 1, one for items 2-6. No amend after a commit.

## Items
1. Remove the unpatched-lwIP negative control (the owner: negative tests easily become overkill; this one cannot
   reach its failure at the shipped TCP_SND_BUF 1,600 B and needs a control image, an option and runner plumbing).
   - tests_hardware/bench/test_modlwip_send_stall.py: delete test_send_stall_on_the_unpatched_image and
     `_REMOVAL_SIGNAL`; drop imports and helpers only it used (check each: json, Path, reflash, wait_until,
     save_errcount, save_fram_raw, BenchBridge, _SERVING_TIMEOUT_S ...). Module docstring: describe the one test
     (the override returns EAGAIN; the normal image must not stall); 3 lines at most.
   - KEEP test_no_send_stall_with_the_override and every bound unchanged. KEEP tests_hardware/bench/_load.py's
     round_image/image_deviations (other tests use them). KEEP the modlwip_eagain override, toolchain/, and
     tests/lwip_host/ unchanged.
   - tests_hardware/conftest.py:393 the `--lwip-control-image` option, and anything only it feeds.
   - tests_scripts/test_tests_hardware_collect_matrix.py:87 the option's entry (and any count that follows from it).
   - BACKLOG.md:~127-131 the control-proof item: drop the control-image text; keep any part still open.
   - tests_hardware/README.md: every line on the control image / the option / its flash cycles (:1689 row and others).
   - SPECIFICATION.md B.14 (B.14.4 and near): any sentence saying the round proves the stall on an unpatched image.
   Find all with: timeout 60 git grep -n -E "unpatched|control image|lwip-control|lwip_control|LWIP_CONTROL" --
   src tests tests_hardware tests_scripts scripts toolchain buildgen digital_twin '*.md' ':!arduino' ':!audit'
   (filtered). Leave the CRC16 and rollover tests' image handling as is.
2. SPECIFICATION.md near line 8461 (connection budget): it still cites the retired 100,000 B after-build bound.
   State the current one: build survivors (used minus the baseline allocation) at most 41,000 B (owner, 2026-11-11),
   measured 35,936-36,176 B on the dev image; the largest free block after the build at least 32,768 B (measured
   35,136 B); in operation, free after one collect 81,984-82,400 B against the serving demand 68,790 B at the
   connection ceiling. Take names from tests_hardware/device_scripts/heap_headroom_after_full_system_build.py
   (_MAX_ADDED) and the tunables register (heap_headroom_after_full_system_build_max_added). Fix every other doc line
   still giving 100,000 B as the bound (bounded grep for "100,000|100_000|100000").
3. SPECIFICATION.md F.1's longest-chain sentence describes the async form and an FRAM-written FRAM log; the FRAM log
   is RAM-only (SPEC ~:498), and the FRAM path is now plain calls (src/asy_fram_manager.py, _send_and_read). SPEC Part
   N `mem.max_await_depth`'s basis names the old verify-pass / FRAM-manager-log chain and ignores plain levels.
   Restate both from the current code. Silicon facts (dev image, 2026-11-11): C-stack quiet setup peak 4,796 B,
   provoked end 6,060 B; the bound: the provoked end leaves at least 1,024 B (owner, 2026-11-11).
4. BACKLOG.md, open questions: one entry, current state only. On the image with TCP_SND_BUF 6,400 one send-stall run
   (2026-11-11) left the board not answering for more than 90 s, loop alive, link reading connected, until a reset;
   nothing in src/ or modlwip holds longer than 15 s; a CYW43 TX flow-control stall (cyw43_ll.c ~651-692) is the
   unconfirmed hypothesis. Not seen since TCP_SND_BUF 1,600 (the send-stall test passes, page 0.51-0.63 s); the 6 h
   HTTP soak is the check.
5. BACKLOG.md, refactor targets: one line. src/asy_i2c_driver.py ~352-353: writeto_then_readfrom (wrapped) calls
   self.writeto / self.readfrom_into (also wrapped), one extra C-stack frame per I2C read, as the FRAM path carried
   before it became plain calls; within the C-stack bound. Record only: no code change.
6. Two one-line doc placements, each verified against the code first (skip one the code contradicts, say why):
   - DEVICE_REFERENCE.md ~:106 (WaitTimeNTP): "**`0` means never wait**: the backup is restored at once, its age
     checked only if the clock is already set then." (src/asy_sgp40_driver.py _run_restore()).
   - scripts/build_device_websites.sh :12 (usage) and :52 (comment): "out_root holds only staged pages: a
     subdirectory with an index.html is removed whole" in place of "may be any directory the caller names".
   Also check: does any doc (SPEC I.4(f.1), HEAP_FRAGMENTATION_MEASUREMENTS.md, README.md) still describe boot-time
   gc.collect() calls as present? src/ and buildgen/ make none. Fix any such line to current state.

## Hand-back
Your final message (at most 30 lines): the two commit hashes; per item what changed (file:line) or why not; lines
removed/added per commit (git diff --stat); anything noticed and left. Do not write report files.
