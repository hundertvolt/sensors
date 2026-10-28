"""Scratch proof (not committed): BuildError requires rule and fix, and its text always names the fix."""
import pytest

from buildgen.errors import BuildError


def test_rule_and_fix_are_required() -> None:
    with pytest.raises(TypeError):
        BuildError("d", "m")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        BuildError("d", "m", rule="r")  # type: ignore[call-arg]


def test_the_text_always_ends_with_the_fix() -> None:
    e = BuildError("d", "m", rule="r.x", fix="do it", instance="i", field="f")
    assert (str(e), e.rule, e.fix, e.message) == ("[d/i.f] m - fix: do it", "r.x", "do it", "m")
