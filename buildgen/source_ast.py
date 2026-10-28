"""One parsed tree per source text: every pass and every device reading one driver file shares it, so
the build parses each file once. A shared tree is read-only: nothing in buildgen/ edits a node
(tests_scripts/test_buildgen_source_ast.py proves it over a whole build of every device)."""

import ast
import functools


def parse_source(source: str, filename: str = "<unknown>") -> ast.Module:
    # Keyed on the text alone: a tree carries no file name, so one text read under many paths (each
    # test's own copy of a driver) is one tree. A SyntaxError is never cached and names the caller's file.
    try:
        return _parse(source)
    except SyntaxError:
        return ast.parse(source, filename=filename)


@functools.lru_cache(maxsize=1024)
def _parse(source: str) -> ast.Module:
    return ast.parse(source)
