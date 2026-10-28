Review of e27b782..442a564 (arduino/, legacy/ and ext/ not read). I found 2 correctness defects, 2 text-rule defects, 1 incomplete credential list and 2 doc defects. Line numbers are at 442a564.

**1. Correctness**
- **Defect: suite hooks are never retried.** vitest.config.js:43-48 and SPECIFICATION.md:4889-4893 (E.3.1) say a timed-out "test or hook" is retried twice. In vitest 5.0.3 the retry loop exists only in `runTest()` (node_modules/vitest/dist/chunks/run.BTlFXlnv.js:3862-3960), so it covers only beforeEach/afterEach. `runSuite()` (:4016-4075) runs beforeAll/afterAll once, and on failure marks the suite's tests skipped. Real case: tests_js/live-backend-put-matrix.test.js:180-185 boots a twin in `beforeAll(startLiveMatrix)`, under browser mode's default 30 s hookTimeout (index.DpLw24bj.js:14745). Effect: a timed-out twin start fails that device's whole matrix with no retry, against the owner's "Two retries everywhere" / "JS tier", while the docs say it is retried.
- **Defect: two web CI budgets use a different retry-budget definition.** B.10.1 (SPEC:1720-1722) defines the budget as (warm + largest single retry budget) × 1.25, rounded up to 5 min. The unit rows count that budget as timeout × attempts, the first attempt included (SPEC:1680-1681, :12035: 1,200 s × 3 = 60 min). The new web rows count only the two retries: `l0.vitest_timeout_retries` × `l0.live_concurrent_tabs_timeout_ms` = 6.7 min (SPEC:12024, :12026, :11084). Counted like the unit rows (3 × 200 s = 10 min):
  - web-unit-tests: (3.28 + 10) × 1.25 = 16.6, so 20 min.
  - web-coverage: (3.40 + 10) × 1.25 = 16.75, so 20 min.
  Both stay at 15 min. The stated "1.5×" margin is really about 1.13×, below the rule's own 25%.
- **Gap, not a defect: actions on every Apply are outside the threat-model check.** test_threat_model_statement.py cannot pass vacuously, and it misses no PUT route, SystemCmd word or dispatch field (it checks against floors: ROUTES' 5 PUTs, all 5 `_SYSTEM_CMDS`, `ResetErrors`/`SystemCmd`). It does not see `alwaysExecuted` fields: src/asy_scd30_driver.py:131 `ForceCalRef` runs a forced recalibration on every Apply. A.11 covers it only as "the SCD30's NVM-backed fields".
- **Checked, no defect found:**
  - scripts/test.sh:364-399: retries 124, and 137 only once past the bound; removes the run record before each attempt; RETRIED-PASS reaches the summary, the L0 verdict and the root-cause line (:870-925); the annotation fires only on FAIL (:968).
  - The vitest RegExp matches `makeTimeoutError()`'s text (:3403) and no failed assertion.
  - test_retry_counts.py's table matches every tagged count in its scopes.
  - The L2 bound follows the service's real waits (asy_wifi_service.py:757-791, asy_base_classes.py:548).
  - The new Part N rows match their tags and sites.

**2. Project text rules**
- **Audit-ID form:** SPEC:11989 adds "after the H2 collision". The label is defined only in uart_comm_hazards.py's docstring; the sibling l2 row (SPEC:11471) says "after both transmitted" instead.
- **Actorless standing rule:** SPEC:1252-1253 (A.11) says "A new route, `SystemCmd` word, dispatch field or UDP service joins this table in the same change" with no "(agent, 2026-10-20)".
- **"No meaning change" that changes meaning:** CLAUDE.md:215 changes "The one known real credential already in this repo" to "The one real credential in this repo", dropping the "known" qualifier. Commit b3d25ae says "no meaning change". Effect: CLAUDE.md now makes an absolute claim that contradicts A.11 row 15 (SPEC:1247), which records two generated bench access-point passwords in the history. Row 15's own "no real credential is committed" says the same thing next to that finding.
- Owner quotes: all verbatim. Comment blocks: none over 3 prose lines.

**3. Credentials**
- No real credential, bench network name or MAC was added. audit/sec_history_scan.py classifies values by sha256 prefix and holds no secret.
- **Incomplete list:** A.11 row 8 (SPEC:1240) says it names "Every place the default is written", but omits PROJECT_AUDIT_PLAN.md:2652 (root, outside audit/), which contains `<row-8-default>`.

**4. Docs against code**
- The two vitest claims under 1 (E.3.1 and the vitest.config.js comment) are false for beforeAll/afterAll.
- BACKLOG.md:908-910 lists the `vitest.config.js` retry under the "`scripts/test.sh` leg". No leg of the chroot recipe runs vitest; test_retry_counts.py only reads the config as text. It belongs under "no leg runs them", as the entry above it does.
- **Checked and true:** tests_hardware/README.md's hotspot paragraph (5 attempts, a recovery note per retry, `_configure_hotspot_ap()` only configuring an inactive AP); CLAUDE.md's backstop sentence; the README premise; E.1, E.2.1 and B.10.1's arithmetic; A.11 rows 1, 2 (shutdown refusals), 3, 6, 9, 13 and 15's `.gitignore` rule.

I wrote one temporary file by mistake (an A.11 extract in the scratchpad) and deleted it. Nothing else was written.
