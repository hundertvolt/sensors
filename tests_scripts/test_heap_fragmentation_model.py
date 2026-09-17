"""Runs tests/_heap_fragmentation_model.py under the real Unix port and pins what it demonstrates:
same free memory, wildly different contiguity, decided purely by allocation ORDER. Regression cover
for the invariant any proposed fix must satisfy (HANDOVER_HARNESS_AND_HEAP_FRAGMENTATION.md Part 2)."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# Matches the handover's own Tier-0 figures. Small enough to stay fast, large enough that the
# fragmented case cannot be confused with allocator dust.
_HEAPSIZE = "400k"
_MODEL_TIMEOUT_S = 120.0
_SCENARIOS = ("interleaved", "survivors_first", "churn_first")


@dataclass(frozen=True)
class HeapMeasurement:
    largest: int
    free: int
    profile: tuple[int, ...]

    @property
    def contiguity(self) -> float:
        """Largest contiguous block as a fraction of free memory - the quantity the board's own
        floor is expressed in (80,000 of 108,736 = 73.6%), and the one that actually fails there."""
        return self.largest / self.free


def _parse_line(line: str) -> tuple[str, HeapMeasurement]:
    name, _, rest = line.partition(" ")
    head, _, profile_text = rest.partition(" profile=")
    fields = {key: int(value) for key, _, value in (token.partition("=") for token in head.split())}
    profile = tuple(int(v) for v in profile_text.strip().strip("[]").split(", ")) if profile_text.strip("[] \n") else ()
    return name, HeapMeasurement(largest=fields["largest"], free=fields["free"], profile=profile)


def _run_model(repo_root: Path, micropython_bin: Path) -> dict[str, HeapMeasurement]:
    env = dict(os.environ, TZ="UTC")  # CLAUDE.md: the Unix port's mktime() reads the host's $TZ
    result = subprocess.run(
        [str(micropython_bin), "-X", f"heapsize={_HEAPSIZE}", "tests/_heap_fragmentation_model.py"],
        capture_output=True, text=True, check=False, cwd=repo_root, env=env, timeout=_MODEL_TIMEOUT_S,
    )
    assert result.returncode == 0, f"the model failed to run:\n{result.stdout}\n{result.stderr}"
    parsed = dict(_parse_line(line) for line in result.stdout.splitlines() if line.strip())
    assert {"clean_heap", *_SCENARIOS} <= set(parsed), f"unexpected model output:\n{result.stdout}"
    return parsed


@pytest.fixture(scope="module")
def model(repo_root: Path, micropython_bin: Path) -> dict[str, HeapMeasurement]:
    return _run_model(repo_root, micropython_bin)


def test_free_memory_is_essentially_constant_across_every_scenario(model: dict[str, HeapMeasurement]) -> None:
    # THE point of the model. If free moved with the ordering, this would be a consumption defect
    # and the remedy would be "allocate less". It does not: the scenarios differ by <2% in free
    # while differing 3x in contiguity, which is what makes this a LAYOUT defect.
    frees = [model[name].free for name in _SCENARIOS]
    assert max(frees) - min(frees) < 0.02 * max(frees), f"free memory is supposed to be ~constant across scenarios, got {frees}"


def test_interleaving_long_lived_allocation_with_churn_fragments_the_heap(model: dict[str, HeapMeasurement]) -> None:
    # Models today's build: a survivor born after each burst of bus traffic. A few hundred bytes of
    # survivors, scattered, cost most of the contiguous heap.
    interleaved = model["interleaved"]
    assert interleaved.contiguity < 0.5, f"the interleaved case is supposed to fragment, got {interleaved.contiguity:.2f}"
    assert len(interleaved.profile) >= 8, f"a fragmented heap should profile as many comparable runs, got {interleaved.profile}"


def test_allocating_every_survivor_first_recovers_a_clean_heap(model: dict[str, HeapMeasurement]) -> None:
    # The proposed __init__-before-setup() invariant, in miniature. This is the number that says the
    # discipline is worth adopting: it does not merely improve contiguity, it restores it.
    survivors_first = model["survivors_first"]
    assert survivors_first.contiguity > 0.9, f"survivors-first is supposed to recover a ~clean heap, got {survivors_first.contiguity:.2f}"
    assert survivors_first.largest == model["clean_heap"].largest, "survivors-first should reach the clean-heap largest block exactly"


def test_survivors_first_strictly_beats_merely_separating_the_phases(model: dict[str, HeapMeasurement]) -> None:
    # Rules out the cheaper reading, "any separation will do". Churn-first separates the phases just
    # as completely and still loses ~40% of the heap, because the survivors then land above a heap
    # the churn already walked. ORDER matters, not just separation.
    assert model["churn_first"].contiguity < model["survivors_first"].contiguity, "survivors-first must beat churn-first, or the invariant is mis-stated"
    assert model["churn_first"].contiguity > model["interleaved"].contiguity, "churn-first should still beat interleaving"


def test_the_profiler_survives_the_fragmented_heap_it_exists_to_measure(model: dict[str, HeapMeasurement]) -> None:
    # Regression cover for a real defect in the handover's own sketch: it appended to a growing list
    # after claiming the largest run, so the append had to allocate from a heap whose biggest region
    # had just been consumed - and the instrument MemoryError'd on its own probe. An instrument that
    # dies on a fragmented heap is useless, since that is the only thing it is ever pointed at.
    for name in _SCENARIOS:
        profile = model[name].profile
        assert profile, f"{name} produced no free-run profile at all"
        assert list(profile) == sorted(profile, reverse=True), f"{name}'s profile must be descending by construction, got {profile}"
