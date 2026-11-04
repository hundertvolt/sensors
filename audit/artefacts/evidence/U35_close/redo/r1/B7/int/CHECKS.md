# B7 merged head's checks (lead, 2026-11-04)

B7's 42153dc4 merged into the integration head a97ec884 as **d5c90b71** (tree 375423e8, clean). The merge adds to B7's
tree only int's two lines in `tests/test_asy_system_service.py`. Each step through `S/u35/lead/run.sh`, one at a time:

| Step | rc | Result |
| --- | --- | --- |
| rebuild (`rebuild.sh`) | 0 | generated modules and every device's site |
| lint (`lint_direct.sh`) | 0 | clean |
| mypy main / host / twin | 0 | no issues in 276 / 314 / 59 files |
| `tests_scripts/test_comment_block_cap.py` | 0 | 657 passed |
| `tests/test_asy_system_service.py`, gc -1 / 32768 | 0 / 0 | 187/187 each |
| `scripts/test.sh --coverage` (`mc_cov.sh`, 14 min) | 3 | every test passed, 0 memory markers; report not rendered |
| `scripts/build_firmware.py dev` | 0 | 1,170,092 of 1,228,800 B, **58,708 B free** (57,868 B at d6bc7617) |

Exit 3 is "tests passed, coverage short" (SPECIFICATION.md E.5.3). The render step's `uv run` needs `coverage==7.16.2`,
which the offline namespace cannot fetch and the cache lacks (`b7i_render_probe`: "Packages were unavailable because
the network was disabled"); CI's coverage job has the network. The settrace build's test result, this check's purpose
(snapshot 29's failure was one), is green.
