"""Tests scripts/build_frozen_html.sh directly (real subprocess invocations, real freezefs output)
- in particular the recursive, multi-source-dir merge its own header comment describes
(SPECIFICATION.md Part B.11) but that had previously only been verified by hand."""

import os
import subprocess

# Assertion technique used throughout this file: freezefs (ext/freezefs/archive.py) writes each
# archived file's mount path as a plain literal string in the generated .py, e.g.
# "/sub/inside.txt.gz" (every file gets gzipped first by this script, so every archived path ends
# in ".gz"). Grepping the generated file's text for those literal strings is a real, direct check
# of what got archived - no need to run the frozen module under MicroPython to prove the merge
# worked.


def _run_build_frozen_html(repo_root, output_path, html_src_dirs=None, check=True):
    env = None
    if html_src_dirs is not None:
        env = {**os.environ, "HTML_SRC_DIRS": html_src_dirs}
    return subprocess.run(
        ["scripts/build_frozen_html.sh", str(output_path)],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=check,
    )


def test_default_html_stub_build_produces_the_expected_stub_files(repo_root, tmp_path):
    out_file = tmp_path / "frozen_html.py"
    _run_build_frozen_html(repo_root, out_file)

    assert out_file.is_file()
    text = out_file.read_text()
    for expected in ("/index.html.gz", "/style.css.gz", "/functions.js.gz", "/favicon.ico.gz"):
        assert expected in text, expected
    assert '"/html"' in text or "'/html'" in text  # the mount target build_frozen_html.sh passes via --target


def test_html_src_dirs_recursive_multi_dir_merge_preserves_nested_subdirectories(repo_root, tmp_path):
    # Two independent source dirs, each contributing its own subtree - mirrors how
    # scripts/build_website.sh stages html/{index.html,style.css,definitions.json} alongside a
    # nested js/ subdirectory, and how the old html_raw/general + html_raw/<device> split worked.
    dir_a = tmp_path / "src_a"
    dir_b = tmp_path / "src_b"
    (dir_a / "sub").mkdir(parents=True)
    (dir_a / "top.txt").write_text("a-top")
    (dir_a / "sub" / "inside.txt").write_text("a-nested")
    (dir_b / "deep" / "nested").mkdir(parents=True)
    (dir_b / "other.txt").write_text("b-top")
    (dir_b / "deep" / "nested" / "file.txt").write_text("b-deep")

    out_file = tmp_path / "frozen_merge.py"
    _run_build_frozen_html(repo_root, out_file, html_src_dirs=f"{dir_a} {dir_b}")

    text = out_file.read_text()
    for expected in ("/top.txt.gz", "/sub/inside.txt.gz", "/other.txt.gz", "/deep/nested/file.txt.gz"):
        assert expected in text, expected


def test_missing_source_dir_fails_instead_of_silently_producing_an_empty_archive(repo_root, tmp_path):
    result = _run_build_frozen_html(repo_root, tmp_path / "frozen_missing.py", html_src_dirs=str(tmp_path / "does-not-exist"), check=False)
    assert result.returncode != 0
    assert not (tmp_path / "frozen_missing.py").exists()
