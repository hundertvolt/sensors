# Lane B seen-failing-first record (B1)
- test_stage_website.py (new, before scripts/_stage_website.py and html/favicon.ico existed): 32 failed in 6.69s
  (FileNotFoundError on scripts/_stage_website.py / html/favicon.ico; real-tree case "can't open file .../scripts/_stage_website.py").
- test_build_website_sh.py: 2 failed, 11 passed: both --stage-only cases, "error: no devices/--stage-only.toml" (exit 1).
- test_build_device_websites_sh.py: module fixture fails, "error: unknown option --stage-only" (exit 2), every case errors.
- Baselines (HEAD copies, nice 19, pytest): test_build_website_sh 6.25 s (12 passed); test_build_device_websites_sh 4.09 s (8 passed).

# B1 committed: 6f2f221 (wt-u23b, branch audit/u23-b)
- After: test_stage_website 32/32 (3.3 s wall); test_build_website_sh 13/13 (8.5 s; HEAD 6.25 s); test_build_device_websites_sh 15/15 (9.4 s; HEAD 4.09 s).
- tests/test_website_build_integration.py on a temp-built wozi site: 7/7 at -1 and 32768, 0 memerr (0.25 s each).
- Red, allow-list rows retired (lead): _decision_vocab_allowlist.txt:173, :549; _citation_allowlist.txt:113.
