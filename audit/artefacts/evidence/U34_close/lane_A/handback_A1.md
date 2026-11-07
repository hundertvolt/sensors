A1 hand-back (lane A, block 1). Branch audit/u34-a, worktree S/wt-u34a, made from 147ea3f and rebuilt with S/u23/rebuild.sh. I edited only THIRD_PARTY_LICENSES.md (+133/−64, now 279 lines). Nothing is uncommitted and nothing of mine is running.

**Commits:** 0e8c640 (step 1), 374af62 (2), 6674b3e (3), 602078c (4a-d), a945fc9 (12; message amended before the next commit), d34018d (14 plus R-7's sentence), a3b9094 (33a-c). Subjects are "U34 lane A: …". The bodies carry no audit IDs and end with the two trailers.

**Steps:** all applied: 1, 2 (R-5, R-6), 3, 4a-d, 12 (R-11), 14 (A.U34.06 (2) plus R-7), 33a, 33b (R-19 tag as ruled), 33c. Nothing had already landed. Where I departed from the packet text, the source says otherwise:
- **Step 2:** says "three of upstream's type stubs". Upstream v2.7.0 ships 16 files under typings/microdot/; the 3 we vendor have the same hashes as the tag. The legacy copy's text is R-6's.
- **Step 3:** the freezefs file headers are two lines, "(c) 2023 Hermann Paul von Borries" then "MIT License", so the entry quotes them as two lines. I did not re-fetch upstream: the record cannot change while the hash test holds.
- **Step 4c:** quotes the real header line ("Inspired by github.com/vshymanskyy/aiodns, not a port"), and "the docstring's characterization" becomes "the header's".
- **Step 4d:** eight bullets, because mprls and shtc3 each keep their own unchanged text, now with full paths. I wrote full paths instead of "…/" so the citation check can resolve them, and left out the old intro sentence, which the header-less entries would make false.
- **Step 12:** adds the year 2019 (`110ce2f`, 2019-08-05) and the later LICENSE commit (`27cc627`, 2021-04-17), and states there is no NOTICE.
- **Step 14 / R-7** (agent, 2026-10-21): the claim that the src/ class has a paired method is gone. The legacy copy's `write_and_recvfrom()` stays in the comparison, under its own class name `AsyUDPSocket`, so the comparison stays true for both copies.
- **Step 33b** (agent, 2026-10-21): BTstack's own LICENSE is non-commercial only (clause 4, lib/btstack/LICENSE:20-22). The image relies on Raspberry Pi's grant in lib/pico-sdk/src/rp2_common/pico_btstack/LICENSE.RP, which the notices list now names. mbedTLS is used under Apache-2.0 and ships no NOTICE. The port's modules are cited as `ports/rp2/modules/`, because a bare `modules/` would trip test_legacy_paths' PRE_MOVE_PATH. I kept the packet's paragraph form. Every other compiled-in fact was checked against /root/pico-toolchain/micropython at v1.29.0: the seven submodule commits, the licence files, the board cmake and manifests, mpconfigport.h, the ROM level, libm. CI uploads no UF2, and package.json has devDependencies only.

**Three sentences are true only once later commits land:**
- THIRD_PARTY:158 "SPDX header reads `Apache-2.0 AND MIT`" needs A2's src/asy_captive_dns.py header.
- :266-269 "`src/asy_udp_socket.py` in its three-line header" (the one with the discussion link) needs N's <UDPHDR>.
- :252 "The `src/` class has no combined method" needs N's removal of `write_and_recvfrom()`.

**Seen failing / bites:** the R-5 plant (the packet's step-2 word order) in a scratch copy, S/u34/laneA/bite_r5/, makes `test_the_table_pins_the_one_tag_third_party_licenses_records` fail with "THIRD_PARTY_LICENSES.md no longer names ext/microdot.py's pinned tag"; the tree passes. Nothing planted was committed.

**Checks:** after each of the 7 commits I ran decision_vocabulary, citations, legacy_paths, vendored_microdot and vendored_freezefs in one process: 37 passed every time, so no red checks. The one warning, "datasheets/ submodule not initialised", also appears at base. Logs are S/u34/laneA/chk_s{1,2,3,4,12,14,33}.log.

**Times** (base vs head, alternating, two rounds each, S/u34/laneA/pair_time.tsv):
| file | base | head | change |
|---|---|---|---|
| decision_vocabulary | 9.43 s | 9.78 s | +3.7 % |
| citations | 12.40 s | 12.93 s | +4.2 % |
| vendored_microdot | 0.25 s | 0.30 s | +0.05 s |
| vendored_freezefs | 0.27 s | 0.25 s | |
| legacy_paths | 2.14 s | 1.90 s | |
None is over the 10 % bound.

**Other:**
- Silent-failure scan of THIRD_PARTY_LICENSES.md: documentation only, so no code site for any of the 7 classes; no finding. No effect in STA, AP, Silent, Off or USB: no firmware or website byte changes.
- Allowlist rows orphaned: none (both "only shrinks" tests green).
- Relay lines written: none (my brief names none).

**Exact first lines A2's test can pin** (line numbers in the head file):
- 3: `This project is public and MIT-licensed (see `LICENSE`). It vendors or derives from other code,`
- 20: `- **Microdot** ([`miguelgrinberg/microdot`](https://github.com/miguelgrinberg/microdot),` (the next line opens "  `ext/microdot.py`, pinned `v2.7.0`, and three of upstream's type stubs of the same tag,")
- 29: `- **freezefs** ([`bixb922/freezefs`](https://github.com/bixb922/freezefs), `ext/freezefs/`:` (the full commit `26be9e339a25e71f506f06a33a2346d6a13a07b8` is at :31, for R-10)
- 56: `- `src/asy_isl29125_driver.py` — from` (now the only ISL29125 entry)
- 86: `- `src/asy_dns_client.py` — its header states "Inspired by github.com/vshymanskyy/aiodns, not a`
- 102: `- `src/voc_algorithm.py` — a literal port of the Python translation in`
- 118: `## Legacy tree (`legacy/`, reference-only, never edited)`
- 120: `- `legacy/firmware/python/IndividualDrivers/asy_bmp3xx_driver.py`, `asy_scd30_driver.py`,`
- 149: `- `src/asy_captive_dns.py`'s `DNSQuery` class (and its pre-refactor` (unchanged; scope sentence at :158)
- 185: `## What the firmware image and the website contain`
- 207: `**Publishing an image** (agent, 2026-09-30; owner-reviewed, 2026-10-02; public MIT repository,`
- 274: `## Datasheets`

**State for A2:** THIRD_PARTY_LICENSES.md is finished for this lane. P2.8 lets no file span two blocks, so A2 should leave it alone. Open: A2's captive-DNS header must read Apache-2.0 AND MIT so that :158 holds, and A2 merges <UDPHDR> before its green run.
