"""One parsed tree per source text: every pass and every device reading one driver file shares it, so
the build parses each file once. A shared tree is read-only: nothing in buildgen/ edits a node
(tests_scripts/test_buildgen_source_ast.py proves it over a whole build of every device)."""

import ast
import functools


def parse_source(source: str, filename: str = "<unknown>") -> ast.Module:
    # Both arguments always reach the cache: it keys on the call as made, so `f(s)` and
    # `f(s, "<unknown>")` would otherwise be two entries for one tree.
    return _parse(source, filename)


@functools.lru_cache(maxsize=1024)
def _parse(source: str, filename: str) -> ast.Module:
    # A SyntaxError is never cached, so each caller raises its own with the file named.
    return ast.parse(source, filename=filename)
