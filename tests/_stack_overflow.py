"""stack_overflow(): the interpreter's own C-stack exhaustion, from a real recursion (py/runtime.c:1786, v1.29.0), run
untraced, since a limit reached inside the coverage tracer would end tracing for the whole file."""

from _untraced import untraced


def stack_overflow() -> RuntimeError:
    def dive(depth: int) -> int:
        return dive(depth + 1)

    try:
        untraced(lambda: dive(0))
    except RuntimeError as e:
        return e
    raise AssertionError("no recursion limit reached")
