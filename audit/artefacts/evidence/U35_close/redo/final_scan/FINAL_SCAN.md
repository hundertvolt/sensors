# Final bird's-eye scan: consolidated result (2026-11-13)

Owner request 10:30:59. Release head 590cffcf, baseline 25caf528. Six fresh scanners (FWA, FWB, BUILD, TESTS, DOCS,
DECISIONS), four fresh adversarial verifiers (V_FWA, V_FWB, V_BUILD, V_DT); DECISIONS-1 and -3 verified by the lead.
43 findings raised (FWA 7, FWB 6, BUILD 12, TESTS 7, DOCS 8, DECISIONS 3); after verification and merging
duplicates they sort into the lists below.

## Verdict
- Product: the owner's decisions hold (65 decided features and 21 confirmed gaps located, none reversed, nothing
  superseded lingering); the drift's named code leftovers are gone (timed checks, per-episode flags, 26 raise sites,
  C-stack report calls, NeoPixel rewrite, sample-age checks, retries, UART-FRAM coupling).
- Left: small code leftovers; the test machinery still about twice its pre-audit size; the standing docs do not
  carry the owner's restraining rulings of 10-28..11-11, so a future session would get the drift's rule set back.
- Lead's own misses: the D step did not reconcile BACKLOG's owed list with the final bench round; the brief listed
  the boot-confined gc.collect as decided although an agent had removed it on 11-10.

## Confirmed (safe, worth doing; no device behaviour change except where noted)
Firmware: FWA-1 (unreachable non-dict guard chain, ~7 + 1 test); FWA-3 (duplicate FRAM begin helper, ~12);
FWA-5 (single-caller `_republish`, ~-12); FWB-2 (leftover MemoryError arm of the removed escalation wait, ~4;
behaviour only on an exhausted heap: watchdog reset with the same code); FWB-3 (3 audit-added typing-only guards in
UARTComm, ~3 + Class B changelog line); FWB-4 (dead typing members in asy_api_response, 4); FWB-6 part (errcount
severity colour: owner said "the look stays exactly as it is" on that row -> restore, ~6).
Build: BUILD-2/TESTS-5 (CI caps 175/175/95 from an agent sizing rule -> ~95/85/95, 6-10); BUILD-5 (test-only
helpers out of buildgen.validate, ~45 moved); BUILD-7 (apt rate bound plumbing never decides, ~80-120); BUILD-9
(build check over src constants only, ~25).
Tests: TESTS-4 narrowed (control arms in 3 gate files, ~345); TESTS-7 (dead audit/ exclusions, ~4);
BUILD-3/TESTS-3 (stale "commit the twin record" rule and citations, ~6-10).
Docs: DOCS-1 = DECISIONS-2 (+DOCS-5 word) (owner's restraining rulings into SPEC 0.2 + pointers, ~+10);
DOCS-2 narrowed (drop "never ask, decide on the owner's behalf", ~5); DOCS-3 (11-10 precedence rule, +2);
DOCS-6 = DECISIONS-1 (reconcile BACKLOG owed list and the reset-code table with the final round, row by row;
final-wiring entry out, its 08-08 credit to SPEC A.10); DOCS-7 (lead -> agent credits, 3 words); DOCS-8 (bench
skill wording, 3 words, keep the owner quote); DECISIONS-3 (the agreed upstream-findings bundle entry, 1 bullet);
FWA-4 doc part (2 SPEC lines wrong about session_begin).

## For the owner (one at a time)
1. FWB-1: the website's Apply sends untouched toggles/dropdowns (agent-added 10-13); can silently revert another
   client's change and write flash. Recommend: back to sending only what the user changed.
2. DOCS-7 gc: the boot-confined gc.collect (owner-approved 09-18) was removed by an agent on 11-10 without an owner
   word. The final image without it passed every bench run. Recommend: keep it removed, record the owner's word.
3. FWA-2: SCD30's config error log is RAM-only through a special flag (agent widening, 09-30); the 11-09 rule says
   FRAM if it has something to log. Recommend: FRAM like the others (one ~30 B chunk; flag and scaffolding go).
4. DOCS-4: four-tier hazard tests for "every shared resource" (owner yes to the audit plan row, 09-26) vs the later
   tiering rulings. Recommend: back to the original rule (new I2C/SPI bus devices).
5. TESTS-1 + BUILD-4: tests of the test machinery grew ~8,400 lines; the gc-site gate is 757 lines. Recommend: a
   bounded cut (~1,200 lines: the gc gate back to a short check, test_shared_helpers, the rest of TESTS-4) and
   leave the remainder.

## Minor (true, not worth a change) and refuted
Minor: FWA-4 code, FWA-6, FWA-7, FWB-5, DOCS-5 (folded into DOCS-1), BUILD-1, BUILD-6, BUILD-8, BUILD-11,
BUILD-12 remainder, TESTS-2 residue, TESTS-6, DOCS-8, FWB-3 pre-audit guards.
Refuted: TESTS-2 (owner accepted O4 topic G, 11-12), BUILD-10, BUILD-12 as proposed, BUILD-3's writer removal,
FWB-6 "Resolution:" hint and console.error, DOCS-4 E.2.3 Load sentence (owner source OR49).
