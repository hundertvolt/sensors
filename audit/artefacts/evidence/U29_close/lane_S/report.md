# U29 lane S: the one-time history secret scan
Evidence: S/u29/laneS/scan_final.txt (final run, masked) and sec_history_scan.py. Values are named by commit, path, line and shape (length, character classes, sha256[:8]).

## 1. Completeness (R-5)
- Clone: `git clone --mirror https://github.com/hundertvolt/sensors` took 8.2 s. It is not shallow; its refspec is +refs/*:refs/*.
- Refs: 220 in all, made of 106 heads, 0 tags and 114 refs/pull/* (110 head, 4 merge).
- Commits: 2,406 in all; 2,377 come from heads and 29 only from pull refs.
- Session checkout: 104 origin/* refs (2,313 commits). The mirror adds 2 heads (claude/blissful-johnson-chdkxf, claude/whole-project-audit-plan-followup) and 93 commits. No origin/* commit is missing from the mirror and no shared branch differs.
- Not scanned: the session's 907 local-only commits (audit/* WIP heads), which are not public.
- Plan's figure (107 refs, 2,016 commits at 58c72c9): the commit count is reproduced exactly. The mirror's heads and tags, limited to commits dated on or before 2026-09-30 12:29:59Z, give 2,016 (2,042 with pull refs). The 107-ref state of that time cannot be rebuilt.
- Walk with the pathspec: 2,401 commits under --full-history against 2,316 by default. Two non-merge commits are pruned by default: 44e39e07 and fc2bd461 (scripts/_digital_twin_ci_suite.py, digital_twin/README.md).
- 5 commits touch only arduino/. They are excluded by path.

## 2. Script and runs
- How it runs: `nice -n 19 python3 -I sec_history_scan.py <git dir> e27b782 --contexts`. Stdlib only, 3-line header, one streaming pass.
- Input is A.U29.04's command plus three supersets:
  - --full-history.
  - --diff-merges=dense-combined, keeping only lines that are new against every parent (1,434 lines). Two files, tests_scripts/_script_loader.py and test_request_body_cap_headroom.py, first appear inside a merge's own resolution. The plain form and the literal --diff-filter=A listing both miss them.
  - %ct, so that "first" means the earliest commit.
- Lines read:
  - 2,020,783 added patch lines.
  - 374 gz or prof blobs with 834,262 lines. These are the audit/ evidence logs; their text never reaches a patch.
  - 46,177 lines of commit messages.
- Not read: 23 PDF blob versions (vendor datasheets and one paper) and 5 icon versions.
- Extensions are reported apart from the plan's own regexes:
  - (b): ghu_/ghr_, sk-ant-, GitLab, npm, PyPI, JWT, Bearer and URL user info.
  - (c): names ending in pw, passphrase or credential; unquoted = and YAML forms (non-code files only); nmcli; positional .connect(); prose "password `…`"; --password flags.
  - (d): the same forms for SSIDs.
  - (e): hex runs of 32 or more characters.
  - (f): the hyphen form of MAC addresses.
- Classification is keyed by sha256[:8] only, and a value is printed only once it is classified safe.
- A literal trace pass follows every withheld value through all added lines, blob lines and commit messages.
- Runs:

| Run | rc | Wall time | Note |
|---|---|---|---|
| 1 | 143 | 10m41 | My kill (pids 4171 and 4280). The tree load deadlocked on a pipe; fixed with a writer thread. |
| 2 | 143 | 4m42 | My kill (pid 8708). The output phase counted 7,032 leftover tokens one by one; fixed with token families. |
| 3 | 0 | 2m03 | Printed the character-class patterns described in item 15. The file was deleted. |
| 4 | 0 | 2m04 | |
| 5 | 143 | 0m40 | My kill (pid 20559), to add the labelling fix. |
| 6 (final) | 0 | 2m06 | Patch stream 33.6 s, blobs and messages 15.7 s, trace 8.7 s, tree load 5.6 s, tree counting and output about 62 s. |

## 3. Per pass
- (a) File names:
  - The plan's list matches only dev_legacy/config_BMP3XX.cfg and config_SGP40.cfg, added at e05f015d on 2026-08-27.
  - Renamed copies are in legacy/dev_drivers/ (7934fae1, 2026-10-06) and are in the tree. Their keys: FiltCoeff, MeanAtmTemp, PressOffset, PressOvers, SampleInterv, SeaLevelOffs, TempOffset, TempOvers / BackupMaxAge, BackupPeriod, WaitTimeNTP.
  - No WIFI config, .env, .pem, .key, .p12, .nmconnection, wpa_supplicant, secret* or credential* file was ever committed.
  - The extension matches three *token* names, all CSS design tokens.
- (b) Token shapes: the plan's shapes match 4 times, all in the prefix list at audit/actions/U29.md:220 (8b497d6c), with no token body. The extensions match once: a proxy URL with test user info on a .invalid host (tests_scripts/test_setup_toolchain_env.py:1393, 65088dec). There is no token and no private key.
- (c) Password-named literals: 46 distinct values, 25 of them found by the plan's regex.

| Class | Count | Details |
|---|---|---|
| accepted | 1 | <row-8-default>: 83 hits in 49 commits; first at 8c4a73d5 (PROJECT_NOTES.md:217); 230 occurrences in the tree. |
| placeholder | 24 | For example supersecret, hunter2hunter2, digital-twin-password, correct-horse-battery (the README example), password (twin), <row-8-default>9 (bound check), newpassword, fixture-hotspot. |
| no credential | 19 | Prose, code fragments, type annotations, the ******** mask, WRONG_PASSWORD, HotspotPW, the redaction marker, path and line references. |
| bench throwaway | 2 | The two values below. |
| real | 0 | |

  - ead195cc: 20 characters, upper, lower and digit, URL-safe alphabet.
    - Location: REAL_PW in tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py. It is at line 26 at c43e177d (2026-09-02) and moved to line 10 at dcb007dc (2026-09-09).
    - Lifetime: the file was deleted at c3df14e1 (2026-10-06).
    - Other occurrences: the only one is audit/sweeps/harvest_merge.py:18 at 23ec78c2, removed by 1a90d975. 0 in the tree.
  - ab75b959: 16 characters, upper, lower and digit, URL-safe alphabet. That is exactly the length secrets.token_urlsafe(12) produces in toolchain/setup_toolchain.py.
    - Location: BENCH_NETWORK_LOCKOUT_2026-09-04.md:24, the recovery script's bench AP credentials. Its SSID on line 23 matches the generator's form, sensors-bench-<6 hex>.
    - Lifetime: added at 29a14cad and deleted at 28c5d8ee, both on 2026-09-04.
    - Occurrences: 1 in all history, 0 in the tree.
- (d) SSIDs: 50 values, 39 of them found by the plan's regex.

| Class | Count | Details |
|---|---|---|
| bench | 3 | sensors-bench-ap, from the repro script at line 25. sensors-bench-<6 hex> in HANDOVER_HARNESS_AND_HEAP_FRAGMENTATION.md:78 (f83ca143), found by the plan's regex. The SSID in the lockout note at line 23. All three have 0 in the tree. |
| placeholder | 35 | |
| no SSID | 12 | Annotations, Valid/Invalid, prose, a metavar, the generator template. |
| real home name | 0 | |

- (e) High-entropy tokens: 31,606 tokens are set aside as identifiers. The families:

| Family | Occurrences | Distinct |
|---|---|---|
| git ids (40 hex) | 2,327 | 103 |
| build or cache artefact names | 1,863 | 10 |
| Claude session ids | 1,782 | 73 |
| lockfile hashes, hex | 1,696 | 1,696 |
| lockfile hashes, SRI | 1,047 | 437 |
| sha256 pins | 736 | 228 |
| mktemp names | 581 | 577 |
| paths and URLs | 237 | 97 |
| GitHub node ids | 179 | 134 |
| other hex: md5 and FRAM dumps (32), memscan heap dumps (36, 42, 512), twin-record logs (45), _bmp3xx_chip calibration bytes (42) | 122 | 67 |
| datasheet-derived text (a PDF diffed as text) | 12 | 9 |
| CI cache keys | 5 | 3 |
| base64 fixtures | 4 | 1 |

  The 20 leftovers: 18 identifiers, 1 USB by-id fixture path whose serial appears nowhere else, and 1 bench password (ab75b959).
- (f) MACs and private IPs ("tree" is the count at e27b782):

| Kind | Items | Tree count |
|---|---|---|
| MAC, real bench | OUI d8:3a:dd, 2 MACs, 15 hits, first at 28c5d8ee in BACKLOG.md:243 | 4, all in audit/ (actions/U1.md, actions/U21.md, refined/FINDINGS.md, refined/S12.md) |
| MAC, documentation | 00:00:5e (RFC 7042 range) | 8 |
| MAC, placeholder | aa:bb:cc, 11:11:11, ff:ff:ff | 7, 2, 3 |
| IPv4, real LAN | 192.168.<bench>.x, 12 distinct: .1, .42, .53 to .58 (the openHAB things), .67 (.claude/settings.json, since removed), .75 | .57 ×4 in audit/ (harvest/HW.md, harvest/raw/out_H07.md, refined/FINDINGS.md, refined/S12.md); every other 0 |
| IPv4, placeholder | 10.0.0.x, 10.20.30.4x, 10.255.255.254, 172.16.0.9, 192.168.1.x, 192.168.4.55 | test copies remain |
| IPv4, upstream | 192.168.4.1 (the CYW43 AP default), 192.168.0.10 (quoted mqtt_as setup) | 74, 0 |

## 4. GitHub's view (R-7)
- security_and_analysis returned: secret_scanning enabled, push_protection enabled, non_provider_patterns disabled, validity_checks disabled, dependabot_security_updates disabled. The repository is public, MIT, branch main.
- The alerts call (--paginate) returned 403 from this session's proxy: "Access to this GitHub API path is not permitted through this proxy." I did not retry it.
- The GitHub connector's secret-scanning call checks content you send it; it does not list alerts. I did not use it.

## 5. Disposition
- Accepted: <row-8-default>, row 8 (owner, 2026-09-26).
- Bench throwaway, ead195cc. Basis (owner, 2026-09-25): "that is a generated login … It's a pure throwaway board-bench-password, low risk, no alarm here". It stays in history; the tracked copy is gone.
- Bench throwaway, ab75b959. Decided on the owner's behalf (agent, 2026-10-20), from the owner's 2026-09-25 words "Such temp credentials are usually generated, and persisting one in a file rather is a stylistic (and not safety) breach". It stays in history; the tracked copy is gone. Its SSID is not the bench SSID recorded on 2026-09-17, so the AP has been regenerated since; I did not check this on hardware.
- Placeholder: 24 (c), 35 (d) and 1 (b).
- No credential: 19 (c), 12 (d), 4 (b) and every (e) item.
- Bench identifier: 3 SSIDs, 2 MACs and 12 IPs. They stay in history. None is in the tree outside audit/; 8 copies sit in audit/ and go when audit/ is deleted.
- Real: none, so nothing is parked. Remedies, if one is ever found, are the owner's choice: rotate it or rewrite the history.

## 6. Differences from the preliminary pass, explained
1. Scope:
   - 220 refs and 2,406 commits, against 107 and 2,016. The difference is the pull refs plus later commits; the heads alone give 2,016 at 58c72c9's date.
   - This scan also reads merge-resolution lines, --full-history, gz blobs and commit messages, and it runs (b) and (f).
2. (c), new: a second bench password, ab75b959. It is in prose, which the plan's regex cannot match because it needs ':' or '='.
3. (c), refined:
   - The repro password is at line 26 at its first commit; line 10 is where it sat at 58c72c9.
   - The audit copy, added at 23ec78c and removed at 1a90d97, is the only other occurrence.
4. (c), split: "placeholder or default" becomes 24 placeholders plus 19 matches that are not credentials.
5. (d), new: two generated bench SSIDs. One (f83ca143) is matched by the plan's own regex but is not named in the preliminary pass. There is still no home network name.
6. (a): unchanged, plus the later renamed copies.
7. (b): unchanged, no token.

## 7. Step 4 at e27b782 (all four checks: yes)
- Both repro scripts are absent from the tree. ls-tree prints nothing; both were deleted at c3df14e1. Their names survive only in PROJECT_AUDIT_PLAN.md and audit/.
- pyproject.toml does not mention them. No "repro" anywhere; the S105/S106 block at :344-350 names only digital_twin/launch.py and tests_scripts/test_buildgen_validate.py.
- tests_hardware/README.md never names them. Its only Timer line, :1468, is about bare machine.Timer.
- tests_scripts/test_device_script_config_flush.py names no deleted file. It names only the fixtures keeps.py, cleans.py and scratch_build.py (:253-258) and src/asy_base_classes.py (:136, present); the comment at :68-70 names no file.

## 8. Row 15 sentence
As in item 12 above.