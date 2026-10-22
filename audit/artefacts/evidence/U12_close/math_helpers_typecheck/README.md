# Main mypy pass: float | None operand in the over-margin humidity test

Seen by U13 lane T's typecheck on 081b60e (U12 merged onto U11): `tests/test_math_helpers.py:303`
multiplied `abs_humidity()`'s `float | None` result. Cause: the U12 lead commit d35df03 ran the unit
file at both GC stages but not `scripts/typecheck.sh`. `before_081b60e.log` reproduces it (rc 1, one
error). Fix 3bd977d narrows the result first; all three passes clean, the file 90/90 at -1 and 32768.
