"""The legacy tree lives under legacy/ only (CLAUDE.md legacy rule): no current file names a pre-move
path (an old root directory, a root build script or the install notes), and the moved tree sits
where the rules say it does."""

import fnmatch
import re

from _repo_scan import read_text, repo_files

# A pre-move path: an old root directory not preceded by a path segment, the two bare directory
# names, a root build script in any spelling (glob, brace, placeholder) or the install notes.
PRE_MOVE_PATH = re.compile(
    r"(?<![\w./-])(?:python|modules|html_raw|dev_legacy)/"
    r"|(?<![\w/])(?:dev_legacy|html_raw)\b"
    r"|(?<![\w/.-])build-[\w*<>{},-]+\.sh"
    r"|(?<![\w/])update_and_install\.txt",
)
# legacy/ is the tree itself; arduino/ is outside this project's scope and datasheets/ holds PDFs.
# The audit working set goes in the audit's own close commit, which deletes it.
_SKIPPED_PREFIXES = ("legacy/", "arduino/", "datasheets/", "audit/")
_SKIPPED_FILES = frozenset({"PROJECT_AUDIT_PLAN.md", "tests_scripts/test_legacy_paths.py"})
# The old root directories; test_citations.py checks a citation into one instead of passing it over.
PRE_MOVE_ROOTS = ("python", "modules", "html_raw", "dev_legacy")
_OLD_ROOTS = tuple(f"{root}/" for root in PRE_MOVE_ROOTS)
_OLD_ROOT_FILES = ("build-*.sh", "update_and_install.txt")


def test_no_current_file_names_a_pre_move_legacy_path() -> None:
    hits: list[str] = []
    for path in repo_files():
        if path.startswith(_SKIPPED_PREFIXES) or path in _SKIPPED_FILES or (text := read_text(path)) is None:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            hits.extend(f"{path}:{number}: {match.group(0)}" for match in PRE_MOVE_PATH.finditer(line))
    assert not hits, "pre-move legacy paths - repath each to legacy/firmware/... or legacy/dev_drivers/...:\n" + "\n".join(f"  {hit}" for hit in hits)


def test_the_pattern_matches_every_pre_move_form_and_no_current_one() -> None:
    pre_move = (
        "python/CommonDrivers/x", "modules/_boot.py", "html_raw/x", "dev_legacy/README.md", "dev_legacy",
        "build-x.sh", "build-*.sh", "build-{a,b}.sh", "build-<device>.sh", "update_and_install.txt",
    )
    current = (
        "legacy/firmware/python/CommonDrivers/x", "legacy/firmware/modules/_boot.py", "legacy/firmware/build-x.sh",
        "legacy/firmware/html_raw/x", "legacy/firmware/update_and_install.txt", "legacy/dev_drivers/asy_bsec_driver.py",
    )
    look_alikes = (
        "micropython/micropython#6924", "ports/rp2/modules/rp2.py", "$(PORT_DIR)/modules", "frozen_modules/",
        "global-modules/-/", "ports/unix/build-standard", "build-{board}", '"modules": [',
    )
    for text in pre_move:
        assert PRE_MOVE_PATH.search(f"see {text} here"), text
    for text in (*current, *look_alikes):
        assert not PRE_MOVE_PATH.search(f"see {text} here"), text


def test_the_legacy_tree_is_where_the_rules_say() -> None:
    files = repo_files()
    stray = [p for p in files if p.startswith(_OLD_ROOTS) or ("/" not in p and any(fnmatch.fnmatch(p, g) for g in _OLD_ROOT_FILES))]
    assert not stray, f"tracked files at a pre-move legacy location: {stray}"
    for root in ("legacy/firmware/python/", "legacy/firmware/modules/", "legacy/firmware/html_raw/", "legacy/dev_drivers/"):
        assert any(p.startswith(root) for p in files), f"nothing tracked under {root}"
    build_scripts = [p for p in files if fnmatch.fnmatch(p, "legacy/firmware/build-*.sh") and p.count("/") == 2]
    assert len(build_scripts) == 4, build_scripts
    for path in ("legacy/firmware/update_and_install.txt", "legacy/README.md"):
        assert path in files, f"{path} is not tracked"
