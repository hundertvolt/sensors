"""Regression coverage for _tmp_scratch.py's TmpScratch, the shared per-test-file scratch-dir
helper every test_*.py with its own config-file isolation needs now uses instead of its own
copy-pasted _TMP_DIR/_next_dir/_sweep_stale_tmp_dirs() trio."""

import os
import time

from _tmp_scratch import _ROOT, TmpScratch, teardown_all


def _write(path: str, content: str = "x") -> None:
    with open(path, "w") as f:
        f.write(content)


def _exists(path: str) -> bool:
    try:
        os.stat(path)
    except OSError:
        return False
    return True


def test_dir_returns_a_fresh_existing_directory_each_call() -> None:
    scratch = TmpScratch("scratchtest_fresh")
    try:
        first = scratch.dir()
        second = scratch.dir()
        assert first != second
        assert _exists(first.rstrip("/"))
        assert _exists(second.rstrip("/"))
    finally:
        scratch.teardown()


def test_dir_accepts_an_optional_label_for_readability() -> None:
    scratch = TmpScratch("scratchtest_label")
    try:
        path = scratch.dir("scd30")
        assert path.rstrip("/").endswith("_scd30")
    finally:
        scratch.teardown()


def test_path_returns_a_file_location_not_yet_present() -> None:
    scratch = TmpScratch("scratchtest_path")
    try:
        path = scratch.path("config_NOTIFY.cfg")
        assert not _exists(path)
    finally:
        scratch.teardown()


def test_path_removes_a_value_left_by_an_earlier_call_with_the_same_name() -> None:
    # The exact bug _sweep_stale_tmp_dirs() existed for: a second call reusing the same name must
    # never silently observe a value an earlier call in this same run already wrote.
    scratch = TmpScratch("scratchtest_path_reuse")
    try:
        path = scratch.path("config_NOTIFY.cfg")
        _write(path, "first")
        path_again = scratch.path("config_NOTIFY.cfg")
        assert path_again == path
        assert not _exists(path_again)
    finally:
        scratch.teardown()


def test_teardown_removes_the_whole_subtree_including_nested_files() -> None:
    scratch = TmpScratch("scratchtest_teardown")
    d = scratch.dir()
    _write(d + "config_A.cfg")
    _write(d + "config_B.cfg")

    scratch.teardown()

    assert not _exists(d.rstrip("/"))
    assert not _exists(_ROOT + "/scratchtest_teardown")


def test_constructing_a_new_scratch_wipes_a_stale_directory_left_by_an_earlier_process() -> None:
    # Simulates a previous run of this same file (its own _next_dir would have restarted at 0 and
    # reused the same directory name) leaving a real, persisted config file behind - the actual
    # mechanism that used to make a "Valid" write silently read back as "Unchanged". A fresh
    # TmpScratch() for the same key must never let that leftover survive to be observed.
    stale = _ROOT + "/scratchtest_stale/1"
    try:
        os.mkdir(_ROOT)
    except OSError:
        pass
    os.mkdir(_ROOT + "/scratchtest_stale")
    os.mkdir(stale)
    _write(stale + "/config_NTP.cfg", '{"NTP_Host": "stale.example.org"}')

    scratch = TmpScratch("scratchtest_stale")
    try:
        assert not _exists(stale)  # the whole key directory, this leftover included, is gone
        fresh = scratch.dir()
        assert not _exists(fresh + "config_NTP.cfg")
    finally:
        scratch.teardown()


def test_two_scratch_keys_never_touch_each_others_directories() -> None:
    a = TmpScratch("scratchtest_iso_a")
    b = TmpScratch("scratchtest_iso_b")
    try:
        keep = b.dir()
        _write(keep + "marker.cfg")

        a.teardown()  # must not affect b's own directory at all

        assert _exists(keep + "marker.cfg")
    finally:
        a.teardown()
        b.teardown()


def test_construction_and_teardown_tolerate_a_missing_key_directory_entirely() -> None:
    # The very first run on a fresh checkout - or the first-ever use of a brand new key - has
    # nothing to remove yet, whether or not tests/_tmp's shared root itself already exists from an
    # earlier test in this same process. Must not raise either way.
    scratch = TmpScratch("scratchtest_never_used_before")
    scratch.teardown()
    scratch.teardown()  # a second, redundant teardown must also be a safe no-op


def test_teardown_all_clears_every_registered_scratch_and_the_registry_itself() -> None:
    a = TmpScratch("scratchtest_all_a")
    b = TmpScratch("scratchtest_all_b")
    dir_a = a.dir()
    dir_b = b.dir()

    teardown_all()

    assert not _exists(dir_a.rstrip("/"))
    assert not _exists(dir_b.rstrip("/"))
    # A second call must be a cheap no-op, not re-walk (and re-fail on) already-removed paths.
    teardown_all()


def _old_style_shared_root_listdir() -> None:
    # A minimal reproduction of the retired per-file _sweep_stale_tmp_dirs(prefix)'s one expensive
    # operation (see the git history of the then-monolithic tests/test_sensortask.py, since split
    # into tests/_sensortask_scenarios.py + six per-device files): os.listdir() on
    # tests/_tmp's shared ROOT - an allocation that scales with every file's own leftover entries,
    # not just the caller's own.
    os.listdir(_ROOT)


def test_large_unrelated_sibling_entry_count_crashes_the_old_shared_root_listdir_but_not_tmpscratch() -> None:
    # Direct regression for the real, reproduced failure mode this helper replaces. 400,000 flat
    # sibling entries is the exact, directly-confirmed count at which os.listdir() on tests/_tmp's
    # shared root raises a real, uncaught MemoryError under -X heapsize=32M - the same flag
    # scripts/test.sh always runs this suite with. This test proves both halves of the fix in one
    # place: the old shape genuinely does break at this scale (not just asserted in prose), and
    # TmpScratch - which never lists the shared root at all, only ever its own key subdirectory -
    # does not, because the failure mode is structurally unreachable for it regardless of how
    # large an unrelated sibling count grows. mkdir/rmdir at this scale cost ~10s/~4s respectively
    # (measured directly) - affordable relative to this suite's own per-file timeout budget.
    try:
        os.mkdir(_ROOT)
    except OSError:
        pass
    sibling_count = 400_000
    for i in range(sibling_count):
        try:
            os.mkdir(_ROOT + "/unrelated_sibling_" + str(i))
        except OSError:
            pass

    try:
        try:
            _old_style_shared_root_listdir()
        except MemoryError:
            pass  # confirms this population is genuinely large enough to reproduce the real bug
        else:
            raise AssertionError(f"expected the old shared-root os.listdir() to MemoryError against {sibling_count} entries - this population is no longer large enough to prove the regression it's meant to")

        t0 = time.ticks_ms()
        scratch = TmpScratch("scratchtest_large_sibling_count")
        try:
            for _ in range(20):
                scratch.dir()
        finally:
            scratch.teardown()
        elapsed_ms = time.ticks_diff(time.ticks_ms(), t0)
        # Generous bound (a healthy run is low tens of ms): this is a crash/scaling regression
        # guard, not a tight performance budget - see this test's own docstring.
        assert elapsed_ms < 5000, f"TmpScratch work took {elapsed_ms}ms against {sibling_count} unrelated siblings - expected it to be insensitive to that count entirely"
    finally:
        for i in range(sibling_count):
            try:
                os.rmdir(_ROOT + "/unrelated_sibling_" + str(i))
            except OSError:
                pass


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
