U29 lane D hand-back. Commit **b3d25ae** on audit/u29-d (S/wt-u29d, base e27b782), 6 files, +176/-13; not pushed. The harness refused to let me write S/u29/laneD/report.md (subagents can't write report files), so this hand-back is the whole record. Logs are in S/u29/laneD/.

**Steps**
- **Step 1, applied.** New tests_scripts/test_threat_model_statement.py:
  - Derives PUT routes and `_SYSTEM_CMDS` from source by ast, and dispatch fields from `buildgen.definitions.definitions_for_toml()` over `DEVICE_NAMES`. It does not import `_generate()` from the other test file.
  - Floors as briefed. Beyond the brief, `_a11_text()` also fails when nothing ends the section, so it cannot read on through Parts B-N and pass vacuously.
- **Step 2:** already landed at test_network_resilience.py:2-3. No edit.
- **A.11, applied:** opening paragraph, 16-row table, closing paragraph that names the check.
- **Pointers, applied:** CLAUDE.md, SPEC L.2 and L.3, the `HotspotPW` comment, pyproject's credential sentence and S104 reason, and the README sentence.
  - One more, in my own file: SPEC C.7.2's "threat model (CLAUDE.md)" now reads "(A.11)".
- **Step 9:** the comment cap stays green.

**Seen failing first** (on e27b782): each of the three derived-set tests failed with "SPECIFICATION.md has no '## A.11' heading"; the bite test passed.
- Planted bites in scratch copies all failed as intended: `_missing` returning [], PUT changed to POST, the str filter, the dispatch key, and the end detection.
- A scratch SPEC copy with `/notification`, `erasefram` and `Calibrate` removed failed each test with exactly its missing name.

**A.11 facts rewritten against the source:**
- **Modes:** the planned OFF mode ("permanently deactivated") no longer exists. A.4 (owner, 2026-10-08) now has Silent and Off (no readable Wi-Fi config). The modes, row 2 and row 12 follow it.
- **Row 1:** the 0.0.0.0/80 default is buildgen/codegen.py `_BOOT_KEYWORDS`, not a constructor default. I added the stream.py:183-187 and lwIP ip.c:122-146 cites.
- **Row 2:** compare-before-write is G.2, not C.5. "Before any task stops" became "before the supervised tasks stop". It now also says that from a command's acceptance every config PUT, `mempause` and `ResetErrors` answer "Failed". The datasheet cite is 2.8.3.1.5, Table 168.
- **Rows 3, 6, 11, 13:** `_cfg_overlay()`; `src/asy_captive_dns.py`; H.4; `config_filename()` in asy_config_manager.py.
- **Row 5:** IPv6 comes from the rp2 port's setting, not an lwIP default.
- **Row 7:** the DHCP server is MicroPython's shared/netutils/dhcpserver.c, which the cyw43 driver starts; it is not the driver's own server.
- **Row 8:** the hotspot is exposed whenever a unit runs it, including a unit not yet set up or just reset to defaults. Added network_cyw43.c:514-526. ruff confirms the one S105-visible copy of the default is test_buildgen_validate.py:337, which has its per-file exemption.
- **Row 9:** udp.c:261-311 plus modlwip.c:1257, the same cites C.7.2 uses. The "at most three" fallback servers is tagged (agent, 2026-09-30; owner-reviewed, 2026-10-02).
- **Every other cite holds as planned:** modlwip.c:427-439 and 1027-1037, tcp_in.c:326-335, modmachine.c:91-97, main.c:196, lwipopts_common.h:60, lwipopts.h:8 and 15, cyw43_config_common.h:44 and 110-115, cyw43_lwip.c:224-227, 229-234 and 237-239, opt.h:875.

**Red checks:** none.

**Relay** (7 lines under `## D`):
- CLAUDE.md already says A.11 holds "the history-scan result", which is only true once your row-15 sentence lands.
- The rewrites listed above.
- Row 8's grep: 100 audit/ lines and PROJECT_AUDIT_PLAN.md:2652 are left out of A.11. mockdata/samples.json and BACKLOG.md:946 are added. tests_hardware/ holds no copy.
- The C.7.2 pointer I changed beyond the brief.
- pyproject.toml:129-130 was left unchanged: its note has the owner tag but no A.11 pointer, and it wasn't in the brief.

**Silent-failure scan** (my files, all classes):
- New, covered and bitten: the three floors, and the end detection that stops a check matching too much.
- Residual, recorded: a name counts if it appears anywhere in A.11, not only in row 2; today every name is in row 2.
- No stale-tree mode: the check generates its definitions itself.
- The refusal after an accepted reboot or erase command is stated in row 2, consistent with A.8.
- src/ change is comment-only, so nothing new there.

**New file's time:** 0.75-0.79 s wall alone (4 passed). It's new, so it has no base-table entry.

**Runs and exits:**
- Base test run rc 1, as expected.
- After A.11: rc 0.
- The 12 checks (tunables register included): 780 passed, rc 0.
- ruff on my files and all scopes: rc 0. Host mypy on the new file: rc 0.
- Reader runs: the 105 files found by the grep (minus the 13 already run), 53 pure-parse in 6 groups and 52 heavy ones one per process under ns_xdg. All rc 0.
  - One deviation in that run: `test_digital_twin_boot_contiguity` first failed with "build/generated_src/ is missing or stale". My src/ comment edit came after the rebuild, so the inputs stamp was out of date; this was my sequencing error.
  - I stopped the runner by pid, reran rebuild.sh (rc 0), and confirmed the only output change was `_BUILD_DATE`, so the earlier passes stand. The remaining 32 files then passed.
- Skips are environmental only: html-validate is not installed, and the firmware build is opt-in via `RUN_SLOW_FIRMWARE_BUILD`.
- Every run is in RUNS.md. The 12-check run (61.7 s) was logged after it exited.
- Nothing of mine is running.
