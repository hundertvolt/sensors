"""Regression test: every reset goes through SystemService._reboot(), and the watchdog is armed once, first, in each
generated boot entry - another call site would reintroduce an unpaused reset or a circumventable watchdog. Strings and
comments are blanked before a scan, so a start line printing `WDT(` is no construction."""

import os

from _generated_tree import devices, require_fresh
from _src_const import py_value
from _tmp_scratch import TmpScratch

_SRC_DIR = "src"  # tests run from the repo root, like tests/_tmp_scratch.py's own "tests/_tmp" convention
_GENERATED = "build/generated_src"
_NEEDLES = ("system_reset(", "system_bootloader(", "machine.reset(", "machine.bootloader(")
_scratch = TmpScratch("reset_invariant")


def _code(source: str) -> str:
    # The source with every string literal's content and every comment blanked, its line structure kept.
    out = []
    i = 0
    while True:
        starts = [j for j in (source.find("#", i), source.find('"', i), source.find("'", i)) if j >= 0]
        if not starts:
            out.append(source[i:])
            return "".join(out)
        j = min(starts)
        out.append(source[i:j])
        if source[j] == "#":
            end = source.find("\n", j)
            i = len(source) if end < 0 else end
            continue
        quote = source[j : j + 3] if source[j : j + 3] in ('"""', "'''") else source[j]
        end = j + len(quote)
        while end < len(source) and source[end : end + len(quote)] != quote:
            end += 2 if source[end] == "\\" else 1
        body = source[j + len(quote) : end]
        out.append(quote + "\n" * body.count("\n") + quote)  # the content goes, its lines stay
        i = end + len(quote)


def _imports_reset(code: str) -> bool:
    return any(line.startswith("from machine import ") and any(name in ("reset", "bootloader") for name in line[20:].replace(",", " ").split()) for line in code.split("\n"))


def _planted(name: str, source: str) -> str:
    path = _scratch.path(name)
    with open(path, "w") as f:
        f.write(source)
    return path


def _product_files() -> "list[str]":
    require_fresh()
    src = [_SRC_DIR + "/" + name for name in sorted(os.listdir(_SRC_DIR)) if name.endswith(".py")]
    return src + [f"{_GENERATED}/sensortask_{device}.py" for device in devices()]


def _read(path: str) -> str:
    with open(path) as f:
        text: str = f.read()
    return text


def _reset_offenders(paths: "list[str]") -> "list[str]":
    # The four call shapes, a `from machine import` naming reset or bootloader, or a `machine` alias calling either;
    # a file showing none of them in its raw text is skipped before the slower blanking.
    offenders = []
    for path in paths:
        raw = _read(path)
        if not (any(needle in raw for needle in _NEEDLES) or "import machine as " in raw or _imports_reset(raw)):
            continue
        code = _code(raw)
        aliases = [line.split(" as ", 1)[1].strip() for line in code.split("\n") if line.startswith("import machine as ")]
        called = [alias for alias in aliases if alias + ".reset(" in code or alias + ".bootloader(" in code]
        if _imports_reset(code) or called or any(needle in code for needle in _NEEDLES):
            offenders.append(path)
    return offenders


def _statements(code: str) -> "list[str]":
    # The non-blank lines after the module docstring (blanked by _code()): the first statements of a flat generated file.
    if code.startswith(('"""', "'''")):
        code = code[code.find(code[:3], 3) + 3 :]
    return [line for line in code.split("\n") if line.strip()]


def test_reset_and_bootloader_calls_confined_to_system_service() -> None:
    # Imported in asy_system_service.py as system_reset/system_bootloader and called only from _reboot()'s action
    # callbacks: any other call site would bypass _storage_pause() and the _RESET_DELAY wait.
    paths = [path for path in _product_files() if path != _SRC_DIR + "/asy_system_service.py"]
    assert paths
    assert _reset_offenders(paths) == []
    assert _reset_offenders([_SRC_DIR + "/asy_system_service.py"]) == [_SRC_DIR + "/asy_system_service.py"]  # the scan sees the one real site


def test_the_watchdog_is_armed_once_first_in_each_generated_boot_entry_and_nowhere_else() -> None:
    # "must be hardcoded so no error ever can circumvent it" (owner, 2026-08-11, eaafc2f) is about injection; its
    # placement as the boot entry's first statement is SPECIFICATION.md Part A.7's (owner, 2026-09-25).
    derived = devices()
    entries = [f"{_GENERATED}/sensortask_{device}_main.py" for device in derived]
    noautostart = [f"{_GENERATED}/sensortask_{device}_main_noautostart.py" for device in derived]
    assert derived, "no device TOML - the floor: one boot entry per device"
    timeout = py_value("buildgen/validate.py", "_WDT_TIMEOUT_MS")
    assert isinstance(timeout, int)
    assert _wdt_problems(_product_files(), entries, noautostart, timeout) == []


def _wdt_problems(product: "list[str]", entries: "list[str]", noautostart: "list[str]", timeout: int) -> "list[str]":
    problems = [f"{path}: constructs a WDT" for path in product + noautostart if "WDT(" in _read(path) and "WDT(" in _code(_read(path))]
    first = ["from machine import WDT", f"watchdog = WDT(timeout={timeout})"]
    for path in entries:
        code = _code(_read(path))
        if code.count("WDT(") != 1 or _statements(code)[:2] != first:
            problems.append(f"{path}: the watchdog is not armed once, by its first two statements {first}")
    return problems


def test_a_planted_alias_reset_and_a_generated_watchdog_are_found() -> None:
    # The shapes the scans exist for, each in a scratch copy; a printed start line and a comment name WDT( harmlessly.
    alias = _planted("alias.py", "import machine as board\n\n\ndef go():\n    board.reset()\n")
    imported = _planted("imported.py", "from machine import Pin, bootloader as enter\n")
    quiet = _planted("quiet.py", "# machine.reset( in a comment\nprint('machine.reset(')\n")
    assert _reset_offenders([alias, imported, quiet]) == [alias, imported]
    module = _planted("sensortask_planted.py", "from machine import WDT\n\nwatchdog = WDT(timeout=8000)\n")
    entry = _planted("entry.py", '"""Doc."""\n\nimport sys\nfrom machine import WDT\n\nwatchdog = WDT(timeout=8000)\n')
    printed = _planted("printed.py", '"""Doc."""\n\nprint("asyncio.run(main(watchdog=WDT(timeout=8000)))")\n')
    assert _wdt_problems([module], [entry], [printed], 8000) == [
        module + ": constructs a WDT",
        entry + ": the watchdog is not armed once, by its first two statements ['from machine import WDT', 'watchdog = WDT(timeout=8000)']",
    ]


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
