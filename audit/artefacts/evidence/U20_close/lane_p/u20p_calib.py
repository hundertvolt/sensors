"""Scratch: print each contract row's printed line and the rule it carries."""
import sys
import pytest

sys.path[:0] = ["tests_scripts", "scripts", "."]
import test_buildgen_error_contract as c  # noqa: E402

if __name__ == "__main__":
    import tempfile
    from pathlib import Path
    from _pytest.monkeypatch import MonkeyPatch
    class Cap:
        def readouterr(self):
            import io
            return type("R", (), {"err": ""})
    for rule in sorted(c._ROWS):
        mp = MonkeyPatch()
        import contextlib, io
        err = io.StringIO()
        tmp = Path(tempfile.mkdtemp())
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                cap = type("C", (), {"readouterr": lambda self: type("R", (), {"err": err.getvalue()})()})()
                code, text, built = c._run(c._ROWS[rule], tmp, cap, mp)
        except BaseException as e:  # noqa: BLE001
            code, text, built = "EXC", f"{type(e).__name__}: {e}", []
        finally:
            mp.undo()
        line = text.strip().splitlines()[0] if text.strip() else ""
        rules = [b.rule for b in built if line.endswith(str(b))]
        print(f"{rule:38} {code} {rules} :: {line[:170]}")
