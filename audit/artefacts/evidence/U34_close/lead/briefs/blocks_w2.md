# U34 wave 2 blocks (lead, 2026-10-21). Each block reads `S/u34/briefs/common_u34.md` first, then its section here,
# then the previous block of its lane's hand-back (`S/u34/handbacks/<L>1_final.md`) and `S/u34/owed_w2.md`.

## A2 (lane A's final block; about 60-75 calls)
Continue on `audit/u34-a` in `S/wt-u34a` (head `a3b9094`; THIRD_PARTY_LICENSES.md is finished: leave it alone).
1. Merge `<UDPHDR>` `1b1da7e` (lane N's header commit, relayed under `## N`) first; nothing later from lane N.
2. Steps in packet order:
   - 10: src/LICENSE-captive_dns (R-11: its year stays, no NOTICE to append; confirm against
     `S/u34/upstream_captive.md`).
   - 11: src/asy_captive_dns.py's header. It must read `Apache-2.0 AND MIT`, Apache-2.0 scoped to `DNSQuery`, so that
     THIRD_PARTY_LICENSES.md's scope sentence (A1's :158) holds.
   - 16, 18, 19: the three driver headers.
   - Every header keeps its line count; an mpy-cross byte compare of the four `src/` files, base against head, proves
     the frozen bytecode unchanged (LEAD NOTES 7).
   - 31: the new tests_scripts/test_third_party_attribution.py. Seen failing first: on a tree without the headers, it
     names each one; plant a header with no entry in a scratch copy and see it named. A1's hand-back lists the exact
     first lines it may pin.
   - 32 / R-10: test_vendored_freezefs.py's check that THIRD_PARTY_LICENSES.md names `UPSTREAM_COMMIT`. It is a guard
     that passes at once, so bite it in a scratch copy.
   - 34 (R-18): README.md's licence bullet; the map stays as it is.
3. A1's three forward-dependent sentences: THIRD_PARTY :158 (your step 11), :266-269 (`<UDPHDR>`, merged) and :252
   (lane N's removal of `write_and_recvfrom()`, not yours: confirm the text names the `src/` class only as having no
   combined method, and leave it).
4. Lane A's complete checks:
   - A's readers (P2.2), the 17 repo-wide scans and the paired times (base `S/wt-u33plan`).
   - The four `src/` files' unit tests once at each GC stage on your head, as a smoke check of comment-only edits.
   - `tests_scripts/test_twin_record.py` is red on the `src/` change: expected; report it, do not fix it.

## N2 (lane N's final block; about 35-50 calls)
Continue on `audit/u34-n` in `S/wt-u34n` (head `d6db0e7`; N1's code and test files are finished: leave them alone).
SPECIFICATION.md only, each site located by its text:
- step 9 (R-17): A.1's "freezefs 2.4, unmodified" becomes "freezefs `main` at `26be9e3`, unmodified"; nothing else in A.1.
- step 15 (R-16): the K.9 bullet "(SPDX header + attribution, matching the file's existing entries)".
- the UDP mention: drop "(and so `write_and_recvfrom()`)" and reword its sentence to the current state (the method is
  gone; `git grep -n write_and_recvfrom` names it).
- Part N: the rows `l1.asy_udp_socket_attempt_timeout_ms` and `l1.asy_udp_socket_exhaust_timeout_ms` leave, because
  their `@tunable` tags left with the only tests that read them (N1, `d6db0e7`). Ruling (lead, 2026-10-21): a register
  row whose tag is gone is removed with it; no other Part N row changes. `test_tunables_register.py` names both rows red
  on your base: that is the seen-failing line, and it goes green after.
- B.10.1, owed by lane C (`S/u34/owed_w2.md`): the Playwright cache sentence also names the runner identity.
Each commit says "no meaning change" or names the change. Lane N's complete checks:
- the SPEC readers (U33's list in `S/u34/lane_plan.md` P2.2, lane N), test_tunables_register and the 17 repo-wide
  scans, with paired times against `S/wt-u33plan`;
- `scripts/lint.sh`'s passes on your head.
Your edit changes no code, so N1's unit and twin runs on `d6db0e7` stand for lane N's code. Do not re-run them.

## T2 (lane T's final block; about 40-55 calls)
Continue on `audit/u34-t` in `S/wt-u34t` (head `334acd0`; T1's config and test files are finished: leave them alone).
Its gitignored `.venv` (a copy) and `typings` (a copy) are yours to use, then remove with literal paths at the end.
1. R-14: measure `disallow_any_unimported` per pass (the three passes and the three single-file runs of
   `scripts/typecheck.sh`, each once with the flag forced on in a scratch copy of its config, nothing committed): the count
   and every site (path:line) go in your hand-back. Decide nothing on it; no config line changes.
2. R-15 / step 24: BACKLOG.md's chroot list gains one paragraph after its last one (find U33's last entry by text),
   with no audit IDs. It names:
   - pyproject.toml's CPY001 comment and its removed baseline entries, plus host_typecheck.ini's removed section
     (lint and typecheck legs);
   - the subset guard in tests_scripts/test_mypy_any_baseline.py and the new tests_scripts/test_third_party_attribution.py
     (lane A; `scripts/test.sh` leg, host Python only);
   - tests_scripts/test_vendored_freezefs.py (never listed so far; no leg affected beyond `scripts/test.sh`'s pytest tier);
   - `.github/workflows/ci.yml` (`S/u34/owed_w2.md`: CI only, no chroot leg).
3. Lane T's complete checks:
   - `scripts/lint.sh` and `scripts/typecheck.sh` on your head;
   - T's readers (P2.2) and the 17 repo-wide scans, with paired times against `S/wt-u33plan`;
   - test_citations after the BACKLOG edit.
