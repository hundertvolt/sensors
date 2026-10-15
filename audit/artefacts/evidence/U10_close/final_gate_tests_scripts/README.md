# The final U10 gate's two host-check failures

The gate on 798cc44 failed two `tests_scripts/` tests at both GC stages; every MicroPython test file passed:

- `test_lint_ceilings.py::test_each_ruff_ceiling_sits_at_its_measured_maximum[max-statements]`: "max-statements = 78
  sits above the measured maximum". Root cause: the lead's setter-contract fix (0b9993d) has the generated pause
  callback return the setter's answer, one emitted statement fewer, so `buildgen/codegen.py`'s `_emit_callbacks`
  went from 78 to 77 statements. The ceiling ratchets down: 77 (BACKLOG's chroot list records it).
- `test_readiness_gates.py::test_an_unread_flag_on_a_class_that_carries_none_fails`: its planted edit anchors on
  `return await self.pr.setup()`, which the lead's NeoPixel readiness fix (9e39042) replaced with
  `await self.pr.setup()` / `return True`. The anchor follows the code; the negative case still fails as planned.

Both commits ran only the checks they touched, not the whole host tier; the gate caught it. Fixed in 146e33f on the
integration branch; the two files and three doc checks pass after (454 tests). The two logs are the failing output.
