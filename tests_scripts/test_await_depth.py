"""The longest static await chain from any task top is pinned (SPECIFICATION.md F.1): a resumed task re-enters its whole
chain in C, so a chain deeper than the budget fails until the C-stack budget is re-derived on the board, a recursive one
always. The analysis: tests_scripts/_await_depth.py, its rules pinned below on fabricated modules."""

from pathlib import Path

import pytest
from _await_depth import Chain, Program, load_program, program_from_sources
from _devices import DEVICE_NAMES

REPO_ROOT = Path(__file__).resolve().parent.parent
# @tunable mem.max_await_depth = 28
_MAX_AWAIT_DEPTH = 28
# A base, a sibling one level deep like it and a subclass whose step is three levels: the precision rules' fixture.
_FAMILY = (
    "import asyncio\n\n\nclass Base:\n    async def step(self):\n        pass\n\n\n"
    "class Shallow(Base):\n    async def step(self):\n        pass\n\n\n"
    "class Deep(Base):\n    async def step(self):\n        await one()\n\n\n"
    "async def one():\n    await two()\n\n\nasync def two():\n    pass\n\n\n"
)


def _over_budget(chains: "list[Chain]", budget: int = _MAX_AWAIT_DEPTH) -> "list[Chain]":
    # Past the budget, or recursive: a cut cycle stands for a chain with no bound.
    return [chain for chain in chains if chain.depth > budget or any(level.endswith(" (cycle)") for level in chain.path)]


def _solved(sources: "dict[str, str]") -> "dict[str, int]":
    # Each top's own deepest chain, keyed by the top's label.
    program = program_from_sources(sources)
    program.solve()
    return {chain.path[0]: chain.depth for chain in program.chains()}


@pytest.fixture(scope="module")
def chains(program: Program) -> "list[Chain]":
    return program.chains()


@pytest.fixture(scope="module")
def program() -> Program:
    # One generation of every device, shared by the checks below.
    built = load_program(REPO_ROOT, DEVICE_NAMES)
    built.solve()
    return built


def test_no_await_chain_is_deeper_than_the_budget(chains: "list[Chain]") -> None:
    deeper = _over_budget(chains)
    assert not deeper, f"{len(deeper)} chain(s) past the {_MAX_AWAIT_DEPTH}-level budget or recursive; the first, {deeper[0].depth} levels: " + " -> ".join(deeper[0].path)


def test_the_walk_reaches_every_kind_of_task_top(chains: "list[Chain]") -> None:
    # Not vacuous: the supervisor, every reader's read loop, the server callback, the REST dispatch a wait_for() starts,
    # each device's boot entry, and a route handler resolved through Microdot's registration, all reached.
    tops = {chain.path[0] for chain in chains}
    for top in ("SystemService._supervise", "WebserverService._serve", "Microdot.handle_request", "UARTComm._listen_loop"):
        assert top in tops, (top, sorted(tops))
    for reader in ("BMP3XX_Reader", "ISL29125_Reader", "SCD30_Reader", "SGP40_Reader"):
        assert f"{reader}._read_loop" in tops, (reader, sorted(tops))
    for device in DEVICE_NAMES:
        assert f"sensortask_{device}.main" in tops, (device, sorted(tops))
    assert any(level.startswith("WebserverService._get_") for chain in chains for level in chain.path), "no route handler reached"
    assert chains[0].depth == max(chain.depth for chain in chains)


def test_a_fabricated_chain_one_level_past_the_budget_fails() -> None:
    levels = _MAX_AWAIT_DEPTH + 1
    body = "".join(f"async def f{i}():\n    await f{i + 1}()\n\n\n" for i in range(levels - 1)) + f"async def f{levels - 1}():\n    pass\n"
    program = program_from_sources({"deep": f"import asyncio\n\n\n{body}\n\nasyncio.create_task(f0())\n"})
    program.solve()
    found = program.chains()
    assert [chain.depth for chain in found] == [levels]
    assert _over_budget(found) == found
    assert _over_budget(found, budget=levels) == []


def test_a_wait_for_starts_its_own_chain_after_its_two_frames() -> None:
    source = (
        "import asyncio\n\n\nasync def outer():\n    await asyncio.wait_for(inner(), 1)\n\n\n"
        "async def inner():\n    await leaf()\n\n\nasync def leaf():\n    await asyncio.sleep_ms(1)\n\n\n"
        "asyncio.create_task(outer())\n"
    )
    assert _solved({"m": source}) == {"m.outer": 3, "m.inner": 3}


def test_an_async_with_counts_its_enter_and_exit_methods() -> None:
    source = (
        "import asyncio\n\n\nclass Guard:\n    async def __aenter__(self):\n        await held()\n\n"
        "    async def __aexit__(self, *exc):\n        return None\n\n\n"
        "async def held():\n    await asyncio.sleep_ms(1)\n\n\nasync def top():\n    async with Guard():\n        pass\n\n\n"
        "asyncio.create_task(top())\n"
    )
    assert _solved({"m": source}) == {"m.top": 4}


def test_an_inherited_method_resolves_on_the_class_that_runs_it() -> None:
    # The base's loop awaits self.step(): run on a Shallow it reaches Shallow.step only, never Deep's override.
    source = (
        "import asyncio\n\n\nclass Base:\n    async def loop(self):\n        await self.step()\n\n"
        "    def start(self):\n        return asyncio.create_task(self.loop())\n\n\n"
        "class Deep(Base):\n    async def step(self):\n        await one()\n\n\n"
        "class Shallow(Base):\n    async def step(self):\n        pass\n\n\n"
        "async def one():\n    await two()\n\n\nasync def two():\n    pass\n\n\n"
        "Deep().start()\nShallow().start()\n"
    )
    assert _solved({"m": source}) == {"Deep(Base).loop": 4, "Shallow(Base).loop": 2}


def test_a_construction_is_exactly_the_class_it_names() -> None:
    # Base() is a Base: its step is Base's own, never the override of Deep, though Deep is constructed too.
    source = _FAMILY + "async def top():\n    plain = Base()\n    await plain.step()\n\n\n_SPARE = Deep()\nasyncio.create_task(top())\n"
    assert _solved({"m": source}) == {"m.top": 2}


@pytest.mark.parametrize(
    "tail",
    [
        "async def run(worker: Base):\n    await worker.step()\n\n\nasync def top():\n    await run(Deep())\n",
        (
            "class Maker(Base):\n    @classmethod\n    def make(cls):\n        return cls()\n\n    async def spawn(self):\n        await self.make().step()\n\n\n"
            "class DeepMaker(Maker):\n    async def step(self):\n        await one()\n\n\nasync def top():\n    await DeepMaker().spawn()\n"
        ),
    ],
    ids=["a subclass passed through a resolved call", "a classmethod's cls() on a subclass"],
)
def test_a_constructed_subclass_keeps_its_override(tail: str) -> None:
    # Soundness: the class a construction makes is followed wherever it goes, cls() making whichever class cls is.
    assert _solved({"m": _FAMILY + tail + "\n\nasyncio.create_task(top())\n"}) == {"m.top": 5}


def test_a_parameter_every_call_resolves_takes_only_what_the_calls_pass() -> None:
    # run() is only ever handed a Shallow: its Base annotation does not bring in the constructed Deep.
    source = _FAMILY + "async def run(worker: Base):\n    await worker.step()\n\n\nasync def top():\n    await run(Shallow())\n\n\n_SPARE = Deep()\nasyncio.create_task(top())\n"
    assert _solved({"m": source}) == {"m.top": 3}


@pytest.mark.parametrize(
    "tail",
    [
        "class Runner:\n    async def run(self, worker: Base):\n        await worker.step()\n\n\nasync def top(found=None):\n    await Runner().run(Shallow())\n    await found.run(Deep())\n",
        "async def run(worker: Base):\n    await worker.step()\n\n\nasync def top(*found):\n    await run(Shallow())\n    await run(*found)\n",
        "_KEPT = Deep()\n\n\nasync def run(worker: Base = _KEPT):\n    await worker.step()\n\n\nasync def top():\n    await run(Shallow())\n    await run()\n",
        "import store\n\n\nasync def run(worker: Base):\n    await worker.step()\n\n\nasync def top():\n    await run(Shallow())\n    await run(store.pick())\n",
        "import later\n\n\nasync def run(worker: Base):\n    await worker.step()\n\n\nasync def top():\n    await run(Shallow())\n    await later.call(run, Deep())\n",
        (
            "async def run(worker: Base):\n    await worker.step()\n\n\nasync def top():\n    w = Shallow()\n    await run(w)\n"
            "    for pending in [run(w) for w in (Deep(),)]:\n        await pending\n"
        ),
        (
            "class Box:\n    def __init__(self):\n        self.worker = Shallow()\n\n    def attach(self, worker: Base):\n        self.worker = worker\n\n"
            "    async def go(self):\n        await self.worker.step()\n\n\nasync def top():\n    await Box().go()\n"
        ),
    ],
    ids=["an unresolved call", "a starred argument", "an omitted argument's default", "a value the flow does not know", "a reference handed on", "a comprehension's call", "a method nothing here calls"],
)
def test_a_parameter_a_call_may_fill_unseen_keeps_its_annotation(tail: str) -> None:
    # Soundness: where a call the walk cannot bind may reach run()'s or attach()'s worker, it can be any constructed Base.
    assert _solved({"m": _FAMILY + tail + "\n\n_SPARE = Deep()\nasyncio.create_task(top())\n"}) == {"m.top": 5}


def test_a_construction_whose_value_is_dropped_still_makes_its_class_concrete() -> None:
    # Soundness: the bare Deep() runs Deep's __init__ all the same, so an annotated Base can be a Deep.
    source = _FAMILY + "import store\n\n\nasync def top():\n    worker: Base = store.pick()\n    await worker.step()\n\n\n_SPARE = Shallow()\nDeep()\nasyncio.create_task(top())\n"
    assert _solved({"m": source}) == {"m.top": 4}


def test_a_recursive_await_fails_the_budget_whatever_its_depth() -> None:
    # A recursion re-enters without bound at run time: its cut counts one level, so the cut itself fails the budget.
    source = "import asyncio\n\n\nasync def ping():\n    await pong()\n\n\nasync def pong():\n    await ping()\n\n\nasyncio.create_task(ping())\n"
    program = program_from_sources({"m": source})
    program.solve()
    found = program.chains()
    assert [chain.path for chain in found] == [("m.ping", "m.pong", "m.ping (cycle)")]
    assert _over_budget(found) == found


def test_a_chain_cut_by_a_cycle_is_never_reused_from_another_top() -> None:
    # Reached from a, y is cut at x and one level short; b, reaching y first, must see its whole chain.
    source = (
        "import asyncio\n\n\nasync def a():\n    await x()\n\n\nasync def b():\n    await y()\n\n\n"
        "async def x():\n    await y()\n\n\nasync def y():\n    await x()\n\n\n"
        "asyncio.create_task(a())\nasyncio.create_task(b())\n"
    )
    assert _solved({"m": source}) == {"m.a": 4, "m.b": 4}


def test_a_site_awaiting_a_coroutine_or_an_asyncio_awaitable_counts_the_deeper() -> None:
    # One await whose value is either the project's one-frame leaf() or wait_for_ms()'s two frames: the deeper counts.
    source = (
        "import asyncio\n\n\nasync def leaf():\n    pass\n\n\nasync def top(flag):\n    pending = leaf()\n"
        "    if flag:\n        pending = asyncio.wait_for_ms(asyncio.sleep_ms(1), 5)\n    await pending\n\n\n"
        "asyncio.create_task(top(1))\n"
    )
    assert _solved({"m": source}) == {"m.top": 3}


def test_the_memo_on_a_cycle_gives_what_a_walk_remembering_every_stack_gives(monkeypatch: pytest.MonkeyPatch) -> None:
    # Memoised with the stack's members on key's own cycle: equal to a memo keyed by the whole stack, from every top.
    source = (
        "import asyncio\n\n\nasync def x():\n    await y()\n\n\nasync def y():\n    await z()\n    await x()\n\n\n"
        "async def z():\n    await x()\n    await y()\n    await t1()\n\n\nasync def t1():\n    await t2()\n\n\nasync def t2():\n    pass\n\n\n"
        "asyncio.create_task(x())\nasyncio.create_task(y())\nasyncio.create_task(z())\n"
    )
    exact = _solved({"m": source})
    monkeypatch.setattr(Program, "_component", lambda self, key: frozenset(self._site_cache) | {key})
    assert _solved({"m": source}) == exact == {"m.x": 5, "m.y": 4, "m.z": 4}
