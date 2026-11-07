"""Tests scripts/build_frozen_html.sh directly (real subprocess invocations, real freezefs output): the recursive,
multi-source-dir merge, the byte-reproducible archive (gzip -n, a pinned clock, sorted file order), the path-length
check before freezefs, and the gzip tree kept in its work directory until the next build (SPECIFICATION.md A.9)."""

import os
import re
import subprocess
from pathlib import Path

# The assertion technique throughout: freezefs writes each archived file's mount path as a plain
# literal in the generated .py, and this script gzips first, so every path ends in ".gz". Grepping
# the generated text for those literals checks what was archived without running it.


def _run_build_frozen_html(repo_root: Path, output_path: Path, html_src_dirs: str | None = None, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    # The gzip tree goes beside the output, never into the live tree's build/.
    env = {k: v for k, v in os.environ.items() if k != "HTML_SRC_DIRS"}
    env["FROZEN_HTML_WORK_DIR"] = str(output_path.parent / "work")
    if html_src_dirs is not None:
        env["HTML_SRC_DIRS"] = html_src_dirs
    return subprocess.run(
        [str(repo_root / "scripts" / "build_frozen_html.sh"), str(output_path)],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=check,
    )


def test_without_html_src_dirs_it_refuses_rather_than_building_something(repo_root: Path, tmp_path: Path) -> None:
    # No default source since html_stub/ was retired: a bare invocation names what is missing.
    env = {k: v for k, v in os.environ.items() if k != "HTML_SRC_DIRS"}
    out_file = tmp_path / "frozen_html.py"
    result = subprocess.run([str(repo_root / "scripts" / "build_frozen_html.sh"), str(out_file)], cwd=repo_root, env=env, capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "HTML_SRC_DIRS" in result.stderr
    assert not out_file.exists()


def test_a_single_source_dir_builds_every_file_under_the_html_mount(repo_root: Path, tmp_path: Path) -> None:
    src = tmp_path / "site"
    src.mkdir()
    for name in ("index.html", "style.css", "app.js", "favicon.ico"):
        (src / name).write_text(name, encoding="utf-8")
    out_file = tmp_path / "frozen_html.py"
    _run_build_frozen_html(repo_root, out_file, html_src_dirs=str(src))

    text = out_file.read_text(encoding="utf-8")
    for expected in ("/index.html.gz", "/style.css.gz", "/app.js.gz", "/favicon.ico.gz"):
        assert expected in text, expected
    assert '"/html"' in text or "'/html'" in text  # the mount target build_frozen_html.sh passes via --target


def test_html_src_dirs_recursive_multi_dir_merge_preserves_nested_subdirectories(repo_root: Path, tmp_path: Path) -> None:
    # Two independent source dirs, each contributing its own subtree - mirrors how
    # scripts/_stage_website.py stages index.html alongside a nested js/ subdirectory, and how the
    # legacy site's legacy/firmware/html_raw/{general,<device>} split worked.
    dir_a = tmp_path / "src_a"
    dir_b = tmp_path / "src_b"
    (dir_a / "sub").mkdir(parents=True)
    (dir_a / "top.txt").write_text("a-top", encoding="utf-8")
    (dir_a / "sub" / "inside.txt").write_text("a-nested", encoding="utf-8")
    (dir_b / "deep" / "nested").mkdir(parents=True)
    (dir_b / "other.txt").write_text("b-top", encoding="utf-8")
    (dir_b / "deep" / "nested" / "file.txt").write_text("b-deep", encoding="utf-8")

    out_file = tmp_path / "frozen_merge.py"
    _run_build_frozen_html(repo_root, out_file, html_src_dirs=f"{dir_a} {dir_b}")

    text = out_file.read_text(encoding="utf-8")
    for expected in ("/top.txt.gz", "/sub/inside.txt.gz", "/other.txt.gz", "/deep/nested/file.txt.gz"):
        assert expected in text, expected


def test_missing_source_dir_fails_instead_of_silently_producing_an_empty_archive(repo_root: Path, tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    result = _run_build_frozen_html(repo_root, tmp_path / "frozen_missing.py", html_src_dirs=str(missing), check=False)
    assert result.returncode == 1
    assert f"error: HTML_SRC_DIRS entry '{missing}' is not a directory - fix: point it at an existing source tree" in result.stderr
    assert not (tmp_path / "frozen_missing.py").exists()


def _site(root: Path, names: "tuple[str, ...]") -> Path:
    root.mkdir(parents=True)
    for name in names:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(f"content of {name}\n", encoding="utf-8")
    return root


def test_two_builds_of_one_tree_are_byte_identical_and_carry_no_build_time(repo_root: Path, tmp_path: Path) -> None:
    # gzip -n keeps every name and mtime out of the archive and freezefs runs on a pinned clock, so a rebuild with
    # every source file touched in between is the same module; the build time lives only in buildgen/version.py.
    site = _site(tmp_path / "site", ("index.html", "js/app.js", "style.css"))
    first, second = tmp_path / "one" / "frozen_html.py", tmp_path / "two" / "frozen_html.py"
    _run_build_frozen_html(repo_root, first, html_src_dirs=str(site))
    for path in site.rglob("*"):
        os.utime(path, (1_000_000_000, 1_000_000_000))
    _run_build_frozen_html(repo_root, second, html_src_dirs=str(site))
    assert first.read_bytes() == second.read_bytes()
    assert "date_frozen = const( '1970/01/01 00:00:00' )" in first.read_text(encoding="utf-8")


def test_the_archive_numbers_its_files_in_sorted_path_order(repo_root: Path, tmp_path: Path) -> None:
    # freezefs names each file's bytes in the order its directory walk meets it, which is the host filesystem's: the
    # walk is sorted, so the variable numbering follows the sorted served paths on every host.
    site = _site(tmp_path / "site", ("zeta.txt", "beta.txt", "alpha.txt", "sub/mid.txt", "gamma.txt"))
    out = tmp_path / "frozen_html.py"
    _run_build_frozen_html(repo_root, out, html_src_dirs=str(site))
    entries = re.findall(r"\(\s*'(/[^']+\.gz)',\s*\(\s*_f(\d+),", out.read_text(encoding="utf-8"))
    assert len(entries) == 5, entries
    assert [path for path, _var in sorted(entries, key=lambda e: int(e[1]))] == sorted(path for path, _var in entries)


def test_a_254_character_path_builds_and_a_255_character_one_fails_before_freezefs(repo_root: Path, tmp_path: Path) -> None:
    # freezefs allows a served path ("/" + its relative path, the .gz included) shorter than 255 characters and
    # raises with a traceback otherwise; the script names the path first.
    for length, ok in ((254, True), (255, False)):
        name = "a" * (length - len("/") - len(".gz") - len(".t")) + ".t"
        site = _site(tmp_path / f"site{length}", (name,))
        out = tmp_path / f"out{length}" / "frozen_html.py"
        result = _run_build_frozen_html(repo_root, out, html_src_dirs=str(site), check=False)
        if ok:
            assert result.returncode == 0, result.stderr
        else:
            assert result.returncode == 1
            assert f"error: website path /{name}.gz is 255 characters; freezefs allows at most 254 - fix: shorten it" in result.stderr
            assert "Traceback" not in result.stderr
            assert not out.exists()


def test_the_gzip_tree_is_wiped_at_the_start_and_kept_after_the_build(repo_root: Path, tmp_path: Path) -> None:
    out = tmp_path / "frozen_html.py"
    stale = tmp_path / "work" / "stale.html.gz"
    stale.parent.mkdir()
    stale.write_bytes(b"a previous build's file")
    result = _run_build_frozen_html(repo_root, out, html_src_dirs=str(_site(tmp_path / "site", ("index.html",))))
    assert not stale.exists(), "the previous build's file survived into this archive's tree"
    assert (tmp_path / "work" / "index.html.gz").is_file(), "the gzip tree must stay for inspection"
    assert "/stale.html.gz" not in out.read_text(encoding="utf-8")
    assert str(tmp_path / "work") in result.stdout
