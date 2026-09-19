"""Regression coverage for _tmp_scratch.py's TmpScratch, the shared per-test-file scratch-dir
helper every test_*.py with its own config-file isolation needs now uses instead of its own
copy-pasted _TMP_DIR/_next_dir/_sweep_stale_tmp_dirs() trio."""

import os

import _tmp_scratch  # the module object itself, for the os-swap in the shared-root invariant test
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
    # Simulates a previous run of this same file, whose _next_dir would have restarted at 0 and reused the
    # same directory name, leaving a real persisted config file behind - the actual mechanism that used to
    # make a "Valid" write silently read back as "Unchanged". A fresh TmpScratch() must not let it survive.
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


class _RecordingOs:
    # Stands in for the `os` binding inside _tmp_scratch itself, recording (call, path) for every directory
    # operation and forwarding to the real one. Swapping a module's own imported name is this project's
    # mocking mechanism, MicroPython having no unittest.mock, and the builtin module cannot be patched.
    def __init__(self, calls: "list[tuple[str, str]]") -> None:
        self._calls = calls

    def listdir(self, path: str) -> "list[str]":
        self._calls.append(("listdir", path))
        return os.listdir(path)

    def mkdir(self, path: str) -> None:
        self._calls.append(("mkdir", path))
        os.mkdir(path)

    def rmdir(self, path: str) -> None:
        self._calls.append(("rmdir", path))
        os.rmdir(path)

    def remove(self, path: str) -> None:
        self._calls.append(("remove", path))
        os.remove(path)


def test_no_operation_ever_reads_the_shared_root_only_its_own_key_subtree() -> None:
    # The whole point of TmpScratch over the retired per-file _sweep_stale_tmp_dirs() trio, asserted as the
    # structural invariant it actually is - "every op stays scoped to <key>, never tests/_tmp's shared root"
    # - rather than inferred from a symptom.
    #
    # The old shape's real failure was an os.listdir() on the shared root, whose allocation scales with
    # every file's leftover entries, so what has to stay true is simply that no TmpScratch operation reads
    # that root. Proven directly by recording every os call a full lifecycle makes.
    #
    # This replaces a test that populated the shared root with 400,000 real sibling directories to reproduce
    # that MemoryError, at a measured 396MB of physical disk writes per run, in two CI jobs plus every local
    # run, to re-demonstrate a defect in an implementation this repo no longer contains.
    #
    # The assertion is also strictly stronger: a reintroduced listdir(_ROOT) fails here immediately, where
    # the scale test only noticed once the root had grown enormous.
    calls: list[tuple[str, str]] = []
    key = "scratchtest_root_untouched"
    own = _ROOT + "/" + key
    _tmp_scratch.os = _RecordingOs(calls)  # type: ignore[assignment]
    try:
        scratch = TmpScratch(key)  # construction wipes its own subtree
        _write(scratch.path("flat.cfg"))
        _write(scratch.dir() + "nested.cfg")
        scratch.dir("labelled")
        scratch.teardown()
    finally:
        _tmp_scratch.os = os  # restoring the real module needs no ignore - only the stand-in above does

    assert calls, "recorded nothing - the os wrappers never took effect, so this test proves nothing"
    for name, path in calls:
        assert not (name == "listdir" and path.rstrip("/") == _ROOT), f"{name}({path!r}) reads tests/_tmp's shared root - the one thing TmpScratch must never do, since that allocation scales with every other file's entries"
        # mkdir(_ROOT) is the one legitimate touch of the root itself: idempotent, EEXIST-swallowed,
        # and what makes concurrent construction from several test processes safe.
        assert path.rstrip("/") == _ROOT or path.startswith(own + "/") or path == own, f"{name}({path!r}) escapes this scratch's own {own!r} subtree"

    assert not _exists(own)  # teardown still actually removed it


def test_unrelated_siblings_in_the_shared_root_do_not_affect_a_scratchs_own_behavior() -> None:
    # The behavioral companion to the structural assertion above: with unrelated entries in the shared root,
    # a scratch's construct/dir/teardown cycle still works and leaves them alone. A deliberately cheap
    # population - the invariant is independence from sibling COUNT, which a handful proves as well.
    try:
        os.mkdir(_ROOT)
    except OSError:
        pass
    siblings = [_ROOT + "/unrelated_sibling_" + str(i) for i in range(25)]
    for path in siblings:
        try:
            os.mkdir(path)
        except OSError:
            pass
    try:
        scratch = TmpScratch("scratchtest_sibling_independence")
        created = [scratch.dir() for _ in range(3)]
        for path in created:
            assert _exists(path)
        scratch.teardown()
        for path in created:
            assert not _exists(path)
        for path in siblings:
            assert _exists(path), f"teardown removed an unrelated sibling {path!r} - it must only ever touch its own key subtree"
    finally:
        for path in siblings:
            try:
                os.rmdir(path)
            except OSError:
                pass


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
