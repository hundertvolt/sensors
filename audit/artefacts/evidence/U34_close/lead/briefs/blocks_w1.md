# U34 wave 1 blocks (lead, 2026-10-21). Each block reads `S/u34/briefs/common_u34.md` first, then its section here.

## A1 (lane A, attribution; about 65-75 calls)
THIRD_PARTY_LICENSES.md only, steps in packet order: 1, 2 (R-5, R-6), 3, 4a-d, 12's SPDX scope sentence (R-11: the
facts are in `S/u34/upstream_captive.md`), 14's :208-210 (A.U34.06 (2)) and R-7's sentence (the paired-method
comparison leaves: `write_and_recvfrom()` is removed by lane N), 33a, 33b (R-19), 33c. Checks after each commit:
test_decision_vocabulary, test_citations, test_legacy_paths, test_vendored_microdot (with R-5's plant in a scratch
copy), test_vendored_freezefs. A2 (README, the headers, the new attribution test) is a fresh block after you: leave
every other file alone. Hand-back adds the exact text of each new entry's first line, which A2's test will pin.

## N1 (lane N, the UDP socket; about 55-70 calls)
1. `<UDPHDR>` first: step 13, src/asy_udp_socket.py:1-3 only (the discussion link; three lines stay three), committed
   alone and relayed under `## N` as `<UDPHDR> <hash>` the moment it exists; mpy-cross byte compare base vs head.
2. R-7: tests/test_asy_udp_socket.py first (delete the method's tests, rewrite the three NTP-pattern tests onto
   `write()`/`recvfrom()` in the shape src/asy_ntp_client.py uses, reword the named comments, keep :1364 and :1831's
   allow-listed texts byte-identical), then remove `write_and_recvfrom()` and its `tries` guard from
   src/asy_udp_socket.py, in one commit. Proof: `git grep -n write_and_recvfrom -- . ':!arduino' ':!audit' ':!legacy'`
   names only THIRD_PARTY_LICENSES.md (lane A's) and SPECIFICATION.md (N2's), and the main mypy pass is green.
3. Runs at both GC stages, base and head paired: tests/test_asy_udp_socket.py, test_asy_dns_client.py,
   test_asy_ntp_client.py, test_asy_captive_dns.py; the twin dev integration
   (`tests/test_digital_twin_sensortask_integration.py`, dev) at both stages on the head. SPECIFICATION.md is N2's.

## T1 (lane T, the type-check configuration; about 55-70 calls)
pyproject.toml, host_typecheck.ini, digital_twin/typecheck.ini, tests_scripts/test_mypy_any_baseline.py: R-2 (try
removing each of the 8 zero-`Any` entries; keep a removal only when `scripts/typecheck.sh`'s three passes and its three
single-file runs accept it), R-3 (the subset guard, seen failing first on an extra exemption in a tmp config), R-4 (no
`mypy_path` change), R-13 (the six ANN401 entries stay while they fire; confirm each fires), step 22's CPY001 comment,
step 27, step 28's residue, step 37 (both twin entries confirmed). One full `scripts/typecheck.sh` after the removals
(time it). Hand-back adds, per pass, every module still exempted with its explicit-`Any` sites (path:line) and the
config lines that leave with it (LEAD NOTES 3). BACKLOG.md and R-14's measurement are T2's.

## C1 (lane C, CI; about 30-45 calls; the lane's only block, so it runs C's complete checks)
R-8 (OF-208): the pin in tests_scripts/test_ci_workflow.py first, seen failing at base on all four Playwright keys;
then .github/workflows/ci.yml's identity step (text identical to `.github/actions/setup-micropython-toolchain/action.yml`'s)
before each of the four caches and its output in each key. The Firefox key stays (P2.1). Step 21 check-only. Checks:
`scripts/lint.sh` (actionlint, zizmor), C's readers (P2.2), the 17 scans.
