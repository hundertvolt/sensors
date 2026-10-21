A2 hand-back (lane A, final block). Branch audit/u34-a in S/wt-u34a, head 92ad46f, nothing uncommitted, nothing of mine running. Every step is applied and every check is green except test_twin_record, which goes red on the `src/` change as expected. The one open dependency is lane N's removal of `write_and_recvfrom()` (THIRD_PARTY:252, below).

**Commits:** 978d1bf merges `<UDPHDR>` 1b1da7e (nothing later from lane N), then 19a8e8e (steps 10+11), 9f496a3 (16, 18, 19), 48ec0ae (31), 5c21b2d (32 / R-10), 92ad46f (34 / R-18). Every commit has the two trailers and no audit IDs in its body.

**Steps:**
- **10:** applied. `src/LICENSE-captive_dns`:201 now has the header's holder string ("contributors" dropped). The year stays 2019 and nothing is appended, as R-11 and upstream_captive.md confirm.
- **11:** applied. The header reads `Apache-2.0 AND MIT`, with Apache-2.0 scoped to DNSQuery.
- **16, 18, 19:** applied with the packet's text word for word.
- **31:** new test, 4 functions, 0.26 s.
- **32:** the freezefs test now checks that THIRD_PARTY records exactly one commit and that it is `UPSTREAM_COMMIT`.
- **34:** the README bullet is rewritten; the map is untouched.

**Decisions (agent, 2026-10-21):**
- **README:** it quotes the owner's words as THIRD_PARTY:10-12 does (decision-record rule 2). Its list also names the ISL29125 driver and the aiodns credit, which the packet's list left out (sources THIRD_PARTY:56-63, :86-95).
- **Test:** besides the M.TSC.139 minimum, it checks that header and entry agree on licence, holder and year, including the scope sentence. It also checks that the licence file the entry names has the header's holder line. Without that, the old captive header would have passed, and step 10's "same holder string" would stay unpinned.
- **Checks:** I ran them once over all staged files before the five commits, not after each commit.

**mpy-cross byte compare (base 147ea3f vs head):** all four files are byte-identical, with default flags and with `-march=armv6m`, and their line counts are unchanged (224, 502, 723, 1571). Output is in S/u34/laneA/mpy/.

**Seen failing first:** I ran the new test on a scratch export of 978d1bf, before the header commits (S/u34/laneA/seen_attr.log). Two tests failed, naming:
- the fram, bmp3xx and isl29125 headers ("lines 2-3 are not …", plus "SPDX tag outside a header's lines 1-2" at :3);
- the captive header: "the header reads `Apache-2.0`, its entry states … ['Apache-2.0 AND MIT']";
- `src/LICENSE-captive_dns`'s holder line.

**Bites:** each ran in its own scratch copy (S/u34/laneA/bites_a2/, script tools2/bite_a2.sh); the clean control copy passes. The printed `rc=0` comes from the script's `echo`; each log ends "1 failed" or "2 failed".
- a planted header with no entry → `{'src/zz_planted.py': 0}`
- a second ISL29125 entry → `{…isl29125…: 2}`
- the UDP header from before the merge (a3b9094) → named, missing the discussion link
- an entry naming the non-existent `src/asy_dns_resolver.py` → named
- the bmp3xx entry year changed → named
- freezefs: another commit in THIRD_PARTY → named; the commit removed → `[]`

**A1's three forward sentences:**
- :158 is now true, and the test pins it.
- :266-269 is true after the merge, and the test pins it.
- :252 names only the `src/` class as having no combined method. I left it. It becomes true only once lane N's `write_and_recvfrom()` removal merges; this branch still has the method.

**Checks (logs in S/u34/laneA/a2/):**
- The 17 scans, the 4 extra pre-commit checks and the attribution/vendored files in one process: 984 passed. The one warning, "datasheets/ submodule not initialised", also appears at base.
- 27 readers, each in its own namespace: all green except **test_twin_record**, red with "changed since their twin run was recorded … device_scripts/…: api_sha256" (expected; the lead re-records it).
- mypy host pass (306 files) and main pass (262 files): both clean. ruff is clean.
- Unit tests at -1 and at 32768, base and head: captive 64/64, fram 104/104, bmp3xx 138/138, isl29125 246/246. Zero MemoryError and zero "memory allocation failed" in any log.

**Times** (base / head, two alternating rounds):
| file | base | head |
|---|---|---|
| vendored_freezefs | 0.30, 0.42 s | 0.28, 0.34 s |
| citations | 11.78, 11.38 s | 12.17, 11.41 s (+1.7 %) |
| legacy_paths | 2.10, 2.32 s | 2.13, 2.24 s |
| decision_vocabulary | 9.45, 9.08 s | 9.45, 9.40 s (+1.8 %) |

The unit-test pairs differ by at most 0.2 s. Nothing is over 10 %.

**Modes and scan:** the changes are comments, docs and tests only, so no firmware byte changes and no effect in STA, AP, Silent, Off or USB. Silent-failure scan: no `src/` code site. Neither test can pass by matching nothing: test 3 fails if the glob finds no files, because the entries name `src/` files, and the freezefs check needs exactly one match.

**Other:**
- Allowlist rows orphaned: none. The old texts survive only in PROJECT_AUDIT_PLAN.md:3149, the finding's own record.
- Relay lines written: none.
- Runs: checks_a2.sh, pid 7132, rc=0, start and done lines in RUNS.md. The other runs were under a minute. The temporary `typings` symlink is removed.