# B8 merged head: checks (lead, 2026-11-04)

Int fast-forwarded d5c90b71 -> 8a32d826 (6f24e171, 3d0e36bb, the fix round 8a32d826); the tree is the one the unit's
fix round gated. `chain.sh` here, one step after another through `run.sh`, labels `b8i_`:

| step | result |
|---|---|
| rebuild (`S/u23/rebuild.sh`) | rc 0 |
| lint_direct (ruff, shellcheck, actionlint, zizmor, guards) | rc 0 |
| mypy main / host / twin | clean: 276 / 314 / 59 files |
| readers (`readers.txt`: the 14 changed tests_scripts files, the comment cap, the live ruff exemptions) | 2,257 passed, 6 skipped (`test_real_firmware_build_produces_a_valid_uf2`'s opt-in, one per device) |
| `tests/test_generated_boot_entry.py` at -1 and at 32768 | 5/5 each |
| npm lint, typecheck, test:unit | clean; 26 files, 1,272 passed |

Sizes from the unit (src/ untouched by the fix round): `src/` 194,883 B; dev `imageFreeBytes` 60,492 B (58,708 B at
d5c90b71, the falsification's plant reproduced both). The full suite at both GC stages ran in the unit's gate on
6f24e171; the fix round changed buildgen's checks and tests only, so CI's full run on the snapshot is its next proof.
