"""Every retry count tuned in testing is in one table (owner, 2026-10-20: "Simply put, do the consistent rule adaptation
to tests only and only for those running into timeout."): a timeout retry: three attempts, two retries (E.3.1); an event
retry keeps its recorded count; a bound is no retry. An unclassified count fails by name; both tiers read theirs."""

import os
import re
from pathlib import Path
from typing import NamedTuple

from test_tunables_register import _HASH_SUFFIXES, _SKIP_DIRS, _SLASH_SUFFIXES, Tag, _scan_file

_SCOPES = ("tests", "digital_twin", "tests_scripts", "tests_hardware", "scripts", "tests_js")
_FILES = ("vitest.config.js",)
# A poll bound (`_tries`) waits for a state and never repeats a failed step, so no retry count is named so.
_COUNT = re.compile(r"@tunable [a-z][a-z0-9_]*\.[a-z][a-z0-9_]*(?:_attempts|_retries|_rebinds) = ")
_TIMEOUT, _EVENT, _BOUND = "timeout retry", "event retry, outside the rule", "a bound, not a retry"
_RULE = {"_attempts": "3", "_retries": "2"}


class Kind(NamedTuple):
    kind: str
    value: str = ""
    reason: str = ""


_TABLE: "dict[str, Kind]" = {
    "runner.per_file_attempts": Kind(_TIMEOUT, reason="a test file, the scenario harness or the pytest tier that ran into its timeout"),
    "l0.vitest_timeout_retries": Kind(_TIMEOUT, reason="a JS test, its beforeEach/afterEach included, that ran into vitest's timeout"),
    "tool.uv_sync_attempts": Kind(_EVENT, "3", "a network step's transient failure: a third party's outage must never read as a red test; not a timeout retry"),
    "l3.toolchain_flash_boot_picotool_load_attempts": Kind(_EVENT, "5", "picotool load exits while no BOOTSEL device is enumerated yet; not a timeout retry"),
    "l3.heap_probe_retries": Kind(_EVENT, "3", "the probe still holds its own buffer through a stale root; not a timeout retry"),
    "l4.bus_concurrency_under_api_load_ceiling_retry_attempts": Kind(_EVENT, "3", "a ceiling refusal under concurrent API load, the stack's reject-when-full; not a timeout retry"),
    "l4.harness_max_device_rebinds": Kind(_EVENT, "2", "a reset re-enumerates the CDC device under another node; not a timeout retry"),
    "l4.hotspot_role_reversal_join_attempts": Kind(_EVENT, "5", "nmcli's own rescan can miss a hotspot is_ssid_visible() just saw (recorded 2026-09-08); not a timeout retry"),
    "l4.network_resilience_capture_attempts": Kind(_EVENT, "3", "a reset landing in the hotspot fallback sends no NTP request to capture; not a timeout retry"),
    "l4.network_resilience_join_attempts": Kind(_EVENT, "3", "the hotspot join's window, before and after one reported reset; not a timeout retry"),
    "l4.wifi_networking_association_attempts": Kind(_EVENT, "2", "one association can fail outside the DUT (measured 2026-09-19: 1 miss in 3 suite runs); not a timeout retry"),
    "ntp.sync_retries": Kind(_EVENT, "3", "the firmware's own NTP sync retries, mirrored by its test: product behaviour; not a timeout retry"),
    "l1.uart_comm_hazard_recovery_attempts": Kind(_BOUND, reason="the transactions the protocol gets to recover in: the assertion itself"),
    "l2.uart_comm_hazard_recovery_attempts": Kind(_BOUND, reason="the transactions the protocol gets to recover in: the assertion itself"),
    "l4.network_resilience_over_ceiling_attempts": Kind(_BOUND, reason="the connections above the ceiling that must all be refused: the assertion's sample"),
    "runner.port_lock_attempts": Kind(_EVENT, "10", "a take lost to another taker of a dead holder's lock, the three libraries alike; not a timeout retry"),
    "l1.lwip_host_fill_attempts": Kind(_BOUND, reason="the settles the arena gets to stop taking writes: the assertion's limit"),
    "l3.uart_comm_hazards_recovery_attempts": Kind(_BOUND, reason="the transactions both ends get to recover in on silicon: the assertion itself"),
}

_TIER_START = 'tests_scripts_inner_pidfile="$results_dir/tests_scripts.pid"\n'
_TIER_END = "tests_scripts_pid=$!\n"
_TIER_LOOP = "for ((attempt = 1; attempt <= max_attempts; attempt++)); do"
_PER_FILE_COUNT = "# @tunable runner.per_file_attempts = 3\nmax_attempts=3\n"


def check_counts(tags: "list[Tag]") -> "list[str]":
    problems = []
    for tag in tags:
        kind = _TABLE.get(tag.id)
        if kind is None:
            problems.append(f"{tag.path}:{tag.line}: {tag.id} is a retry count no class holds - classify it in _TABLE")
            continue
        want = _RULE.get(tag.id[tag.id.rindex("_") :], "") if kind.kind == _TIMEOUT else kind.value
        if kind.kind != _BOUND and tag.literal != want:
            problems.append(f"{tag.path}:{tag.line}: {tag.id} = {tag.literal}, the table holds {want or 'no count'} ({kind.kind})")
    return problems


def retry_tags(root: Path) -> "list[Tag]":
    # The retry counts tagged in the testing scopes, read as the register reads every tag; files naming none are skipped.
    files = [root / name for name in _FILES]
    for scope in _SCOPES:
        for directory, subdirs, names in os.walk(root / scope):
            subdirs[:] = sorted(d for d in subdirs if d not in _SKIP_DIRS)
            files += [Path(directory) / n for n in sorted(names) if Path(n).suffix in _HASH_SUFFIXES | _SLASH_SUFFIXES | {".py"}]
    tags: list[Tag] = []
    problems: list[str] = []
    for path in files:
        if _COUNT.search(path.read_text(encoding="utf-8")):
            _scan_file(root, path, tags, problems)
    assert not problems, "\n".join(problems)
    return [t for t in tags if t.id.endswith(("_attempts", "_retries", "_rebinds"))]


def tier_findings(test_sh: str, vitest_config: str) -> "list[str]":
    # The pytest tier's launch loops up to the per-file count, set before it; the JS tier's retry object carries its tag.
    found = []
    start = test_sh.find(_TIER_START)
    block = test_sh[start : test_sh.find(_TIER_END, start)] if start != -1 else ""
    if _TIER_LOOP not in block:
        found.append(f"scripts/test.sh: the tests_scripts/ tier is not launched in {_TIER_LOOP!r}")
    if not -1 < test_sh.find(_PER_FILE_COUNT) < start:
        found.append("scripts/test.sh: runner.per_file_attempts is not set before the tests_scripts/ tier is launched")
    if not re.search(r"\n\s*retry: \{\n\s*// @tunable l0\.vitest_timeout_retries = (\d+)\n\s*count: \1,\n", vitest_config):
        found.append("vitest.config.js: no retry object whose count carries l0.vitest_timeout_retries")
    return found


def test_every_retry_count_in_testing_is_classified_and_follows_the_rule(repo_root: Path) -> None:
    tags = retry_tags(repo_root)
    assert tags, "no retry count found in the testing scopes - the scan reads nothing"
    problems = check_counts(tags)
    assert not problems, "\n".join(problems)


def test_every_classified_count_is_still_tagged(repo_root: Path) -> None:
    gone = sorted(set(_TABLE) - {t.id for t in retry_tags(repo_root)})
    assert not gone, f"classified but tagged nowhere in the testing scopes: {gone} - remove them from _TABLE"


def test_both_tiers_retry_through_their_tagged_count(repo_root: Path) -> None:
    found = tier_findings((repo_root / "scripts" / "test.sh").read_text(encoding="utf-8"), (repo_root / "vitest.config.js").read_text(encoding="utf-8"))
    assert not found, "\n".join(found)


def test_an_unclassified_or_off_rule_count_is_named(tmp_path: Path) -> None:
    held = [Tag("tests/b.py", 5, "l4.hotspot_role_reversal_join_attempts", "5"), Tag("tests/c.py", 7, "l1.uart_comm_hazard_recovery_attempts", "9"), Tag("tests/d.py", 9, "runner.per_file_attempts", "3")]
    off = [Tag("tests/a.py", 3, "l1.new_knob_retries", "2"), Tag("tests/b.py", 5, "l4.hotspot_role_reversal_join_attempts", "3"), Tag("tests/e.py", 2, "l0.vitest_timeout_retries", "3")]
    assert check_counts(held) == []
    assert check_counts(off) == [
        "tests/a.py:3: l1.new_knob_retries is a retry count no class holds - classify it in _TABLE",
        "tests/b.py:5: l4.hotspot_role_reversal_join_attempts = 3, the table holds 5 (event retry, outside the rule)",
        "tests/e.py:2: l0.vitest_timeout_retries = 3, the table holds 2 (timeout retry)",
    ]
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "a.py").write_text("# @tunable l1.new_knob_retries = 2\n_RETRIES = 2\nTEXT = '# @tunable l1.in_a_string_retries = 9'\n", encoding="utf-8")
    (tmp_path / "vitest.config.js").write_text("", encoding="utf-8")
    assert [(t.id, t.literal) for t in retry_tags(tmp_path)] == [("l1.new_knob_retries", "2")]


def test_a_tier_that_does_not_read_its_count_is_named() -> None:
    launch = f"{_PER_FILE_COUNT}{_TIER_START}(\n    {_TIER_LOOP}\n        :\n    done\n) &\n{_TIER_END}"
    config = "    test: {\n        retry: {\n            // @tunable l0.vitest_timeout_retries = 2\n            count: 2,\n        },\n"
    assert tier_findings(launch, config) == []
    assert tier_findings(launch.replace(_TIER_LOOP, "for attempt in 1; do"), config) == [f"scripts/test.sh: the tests_scripts/ tier is not launched in {_TIER_LOOP!r}"]
    assert tier_findings(_TIER_START + launch.replace(_TIER_START, ""), config) == ["scripts/test.sh: runner.per_file_attempts is not set before the tests_scripts/ tier is launched"]
    assert tier_findings(launch, config.replace("count: 2", "count: 3")) == ["vitest.config.js: no retry object whose count carries l0.vitest_timeout_retries"]
