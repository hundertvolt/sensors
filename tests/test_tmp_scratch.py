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


def test_large_unrelated_sibling_entry_count_does_not_slow_or_crash_this_files_own_scratch() -> None:
    # Direct regression for the real, reproduced failure mode this helper replaces: the old
    # per-file _sweep_stale_tmp_dirs(prefix) called os.listdir() on tests/_tmp's shared ROOT, an
    # allocation that scaled with (and, at a large enough count, crashed with a real MemoryError
    # on) every OTHER file's own leftover entries, not just this file's. TmpScratch never lists
    # the shared root at all - every operation is scoped to this file's own key subdirectory - so
    # it must stay fast and crash-free no matter how many unrelated sibling entries pile up
    # alongside it. 4000 flat sibling directories is well beyond anything one real
    # scripts/test.sh run's own 66 files could organically create in the numbered-subdir shape
    # this replaces, and already large enough to make an O(n) shared-root listdir cost show up
    # against the bounded, O(1)-in-n cost this test asserts on.
    try:
        os.mkdir(_ROOT)
    except OSError:
        pass
    sibling_count = 4000
    for i in range(sibling_count):
        try:
            os.mkdir(_ROOT + "/unrelated_sibling_" + str(i))
        except OSError:
            pass

    try:
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
