# U24 W2 lead step (the one merge point), compiled from lead_todo 17:00-20:35. Line numbers are W1 31d5bfc's;
# lanes do not edit the allow-lists, so they hold at W2. Every retirement: print the line, check it names what the
# hand-back says, then delete. Each retirement's check runs green after; each edit seen failing first.

## 1. Merges in wt-u24w1 (audit/u24-w1 -> W2), `git merge --no-ff`, one at a time, each conflict root-read
U3 b69328f; U4 77f9c2d; M cc8d32f (contains U2 b76ddb7); D adf4f4f (merged db4db10); U1 d00e02c (lane V stopped: its items are OF-150..152); B d1c9d9c; K e262d67 (on 5b92b67 = 9efb630's test.sh patch);
then the PR head 9efb630 (U23 fixes 9ddad1c/c3258eb/73f675c on tests_js: J moved the twin launch into
tests_js/_twin_process.js -> keep both: J's process module, the fixes' per-check context + drain + named failures).
After: uv.lock untouched? (no lane touched it) - check `git diff 31d5bfc -- uv.lock package-lock.json` is empty.

## 2. Retirements (allow-lists only shrink; lead only)
- pyproject.toml Any-baseline: H :442 :445; U3 :446 :452 :453 :456 :463 :467 :471 :474 :488; U2 :455 :458 :466
  :475-477 :485-487; U4 :459-462 :464 :470 :480-484; U1 :454 :457 :465 :468 :469 :489 (D: none).
- digital_twin/typecheck.ini :68-69 (U3). host_typecheck.ini :62-63 :65-66 :68-69 :77-78 :80-81 (T); :41-42 :65-66 (B).
- ANN401 pyproject: :298 (U1); :278 (U3); :279 :285-287 :291 :301 (U2); :299-300 (U4); :309 (T); :252 reason stale (F).
- _decision_vocab_allowlist.txt: :266 :399 :402 :404 (U4); :395 :412 (U3); :302 :304 :318 :319 :351 (U2);
  :515 (one of two identical) :517 :526 :577 :578 (J); :567 (T); :220 :255 :257 :274 :276 :277 :421 (U1); :528 (B); :202 (D).
- _citation_allowlist :99-101 (U4).
- tests_scripts/test_microtest.py _JSON_LOADS_ALLOWED :21 :25 :27 (D).
- test_no_variant_literals _NOT_YET_CLEANED: :73-75 (U4); :51 :76 :77 (U2); :52 :84 (D); :107-126 :128 (T, 21);
  by content "scripts/run_unix_port_integration.sh" (:45) and "tests_scripts/test_test_sh.py" (:127) (S).
- test_import_placement _PENDING: :123 :126 :127 :135-141 :147 :153 :191-193 (T, 15); :83-86 :98-99 (F); :78-80 :100-103 (U2).
- tests_scripts/test_ntp_generated_wiring.py :3 :44 :45 :49 :53 -> `_make_ntp` (U2 renamed under H's rule).

## 3. Lead edits (each seen failing first where behaviour)
a. Stale "no per-test reset" comments: U4 test_ticks_rollover.py:412, test_asy_i2c_driver.py:50; U3 _uart_comm_harness.py:70, test_asy_uart_comm.py:138, test_asy_uart_driver.py:91, test_asy_uart_link_driver.py:52 (check each against K's harness first).
b. Step 264 -> LANE B (brief_laneB.md).
c. Vacuity floors -> LANE B.
d. Step 298 partly (boot markers) -> review list (agent, conservative), no product logging.
e. (f) done by K (e262d67). K's consequence, in-unit: a hung file that swallows the INT exits 137 at the hard stop and is
   no longer retried (SIGTERM gave 124 + retry). Keep the standing backstop unchanged: 137 after the timeout retries
   like 124 (scripts/test.sh ~:546-554), seen failing first in test_test_sh.py. The swallowing sites are OF-155.
f. (g) orphan generated modules -> LANE B.
g. test_buildgen_generate +22 % -> LANE B.
h. U1's const mirror -> import of D's constant (wave2_rulings 1; pure migration, both GC stages).
i. Clone groups (U4): the 256 KB FRAM part x4, _UTCValid x7 -> lead edit only if a U24 step names the fold; else an open finding (CONCURRENCY 13).
j. (o) src_const typing -> OF-153 (open finding, CONCURRENCY 13), not a W2 edit.
k. Y: BACKLOG entry for the coverage pin; Y: UART_C_PORT_CHANGELOG Class B banner row (relay_facts).
m. DONE (lead): _async_harness._cleared() guard (reap + cancel), test seen failing (segfault) -> green 15/15.
l. K's, M's and B's hand-back items for the lead; B's retiring host_typecheck.ini rows.

## 4. Then
Static checks (ruff 8 scopes, three mypy passes cold), the timed sweep only for files touched at W2 (base_times.tsv),
tests_scripts doc/convention checks -> wave 3 (X, Y with relay_facts.md) -> the gate alone (gate_v10 layout) ->
close records (OF-149; OF-145/146 decided; U23 CI chain; U23 CI-fix evidence; Chromium 141 vs 153 finding) -> squash,
push, CI via hooks, U24 owner report.
