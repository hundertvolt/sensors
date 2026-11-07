# Pass 4 merge — agent Y ledger (G6.md, G7.md, G8.md, G9.md, G10.md), 2026-09-29

G10.md: no Q or M line targets it; unchanged.

- Q06 | G9/R09 | applied | State "holds for uptime" replaced by the LEAD/R24 work item; Req gains "per LEAD/R24"; `system_service.py:80` and `asy_wifi_service.py:167` (`LockedCounter(max_val=0xFFFFFFFF)`) checked at HEAD
- Q13 | G8/R34 | applied | merged into the U24/U27 band-overflow clause; narrowed to the 16 `_next_port` step sites in 12 files (counted at HEAD): K.46's 18 also count `_next_static_mount` (`test_asy_webserver_service.py:1855`, a `/test_static_N` mount path) and `_tmp_scratch.py:60`'s `_next` (a scratch directory number), path counters with no port band
- Q15 | G9/R38 | applied | both restored tags added after H1.18's list as "likewise restored (pass 4)", not inside "all lost in `75f2e11`", since H.02/H.03 do not show that commit dropped them; SPEC:178 and `asy_sgp40_driver.py:596-599` checked at HEAD
- Q17 | G6/R24 | applied | Rank gains the owner-confirmed 20 ms default; the State's "idle poll" item amended; `asy_udp_socket.py:126` default 20 and captive DNS `recvfrom()` with no deadline (`timeout_ms=-1`, `:171-172`) checked
- Q19 | G6/R49 | applied | Req gains the no-probe/no-periodic-restart sentence, Sources the `d4814cc` message 2 quote, Rank a short owner tag (H.07 names Req and Rank); no register block allows a probe or periodic restart
- Q21 | G6/R26 | applied | Req: the NTP attempt's DNS resolution stays inside the lock, shown harmless; Rank gains the owner acceptance; `asy_ntp_client.py:431-440` (resolution inside the held lock) checked
- Q22 | G7/R01 | applied | Sources gains the 2026-08-13 owner quote
- Q23 | G9/R35 | applied | the script sites joined H1.10's list; `scripts/run_unix_port_integration.sh:6-8, :24` checked at HEAD (serve-forever, `localhost:8080`, no actor tag)
- Q24 | G8/R31 | applied | Sources gains the 2026-07-31 owner quote
- Q25 | G6/R47 | applied | Rank relabelled owner as written; the `build_info=` wiring kept as the agent part (Part L), since the owner's words do not cover it
- Q27 | G9/R02 | applied | Rank gains the 2026-07-22 owner direction; "gets that tag in U36" merged into the existing U36 CLAUDE.md:447-448 State item; CLAUDE.md:447-448 checked
- Q29 | G7/R39 | applied | Rank gains the per-instance keying owner decision; its "after question 2" part is M01 (LEAD_MERGE §1)
- M01 | G7/R39 | applied | Rank gains OR109.a (3) and the reading of `d4814cc`; Sources gains OR109.a (3); `buildgen/definitions.py:115-119, 381, 387` Config Store rows checked; agrees with the Req's `CFGMGR_<name>` rows
- Q31 | G8/R21 | applied | State gains the trigger-met item; SPEC:817-818 text and `setup_toolchain.py:36, 335, 379` checked; CLAUDE.md:981-983's "worked around by `_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND`" added to what goes on a clean build (F.18 names it as a site); the mbedtls/MicroPython hashes not checkable here (no git)
- Q32 | G6/R31 | applied | State replaced as written, plus the `asy_udp_socket.py:88-89` client `connect()` site; lwIP `udp.c:253-311` remote-port/IP test and `modlwip.c` `udp_connect()` for `SOCK_DGRAM` checked in the scratchpad's v1.29.0 checkout
- Q33 | G8/R50 | applied | merged into the existing "(confirm dorny semantics)" item, which it settles; `ci.yml:11-12` and `:35-41` checked
- Q34 | G8/R53 | applied | State gains the U28 re-pin item; `ci.yml:35` pin checked; "re-verifying F.49" written as G8/R50's push semantics
- Q35 | G8/R61 | applied | the U8 clause rewritten, not added beside it: vendored upstream stub replaces "`ext/` joins `mypy_path` under `follow_imports = silent`"; `pyproject.toml:359, 365, 409-411` checked; the unannotated `route/get/put` confirmed in upstream's `microdot.pyi` in the scratchpad clone (at `main`; the v2.6.2 content rests on F.52)
- Q36 | G6/R53 | applied | State gains the stub hash-check and the U36 legacy-version doc item; CLAUDE.md line range corrected :111-114 → :105-108 (the "untagged snapshot between `v2.0.1` and `v2.1.0`" sentence at HEAD); THIRD_PARTY_LICENSES.md:16-18 checked
- Q41 | G8/R19 | applied | State gains the U21/U36 doc item; added SPEC B.1:705-707, which states the same "matching major.minor … enforced" claim; docstring range given as `setup_toolchain.py:237-239`; SPEC:3443-3444 checked; the pico-sdk/picotool CMake lines not checkable here (rests on F.47)
- Q42 | G9/R12 | applied | appended as one U36 item; every site line and target range checked at HEAD; two corrections: `tests/_bus_hazard_catalog.py:277-278` → `:281-282` (the comment now sits there), and `toolchain/micropython_overrides.py:70` already cites B.14.1, so only its "CLAUDE.md Part F.6" half goes
