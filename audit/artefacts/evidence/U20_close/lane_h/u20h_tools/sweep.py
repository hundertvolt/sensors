"""Scratch tool: drop the future import from the given host files and quote each runtime annotation that the
guard flags (whole annotation quoted). --dry prints what it would do. Run from the worktree root."""
import ast
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, "tests_scripts")
spec = importlib.util.spec_from_file_location("guard", "tests_scripts/test_host_annotations.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

dry = "--dry" in sys.argv
paths = [a for a in sys.argv[1:] if a != "--dry"]
for path in paths:
    text = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(text)
    guarded = guard.type_checking_only_names(tree)
    first_bound = {}
    for index, stmt in enumerate(tree.body):
        for name in guard._bound_names([stmt]):
            first_bound.setdefault(name, index)
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    spans = []
    for annotation, when in guard._runtime_annotations(tree):
        if annotation is None:
            continue
        bad = [n for n in guard._unquoted_names(annotation) if n.id in guarded or (when is not None and first_bound.get(n.id, -1) >= when)]
        if not bad:
            continue
        seg = ast.get_source_segment(text, annotation)
        if annotation.lineno != annotation.end_lineno or '"' in seg or "'" in seg:
            print(f"MANUAL {path}:{annotation.lineno}: {seg!r}")
            continue
        start = offsets[annotation.lineno - 1] + len(lines[annotation.lineno - 1].encode()[: annotation.col_offset].decode())
        end = offsets[annotation.end_lineno - 1] + len(lines[annotation.end_lineno - 1].encode()[: annotation.end_col_offset].decode())
        assert text[start:end] == seg, (path, annotation.lineno, text[start:end], seg)
        spans.append((start, end, seg))
    for start, end, seg in sorted(spans, reverse=True):
        if dry:
            print(f"QUOTE {path}: {seg}")
        text = text[:start] + '"' + seg + '"' + text[end:]
    future = "from __future__ import annotations\n"
    if text.count(future) != 1:
        print(f"NOFUTURE {path}")
    else:
        i = text.index(future)
        after = text[i + len(future):]
        before = text[:i]
        if after.startswith("\n") and (before.endswith("\n\n") or before == ""):
            after = after[1:]
        text = before + after
    if not dry:
        Path(path).write_text(text, encoding="utf-8")
