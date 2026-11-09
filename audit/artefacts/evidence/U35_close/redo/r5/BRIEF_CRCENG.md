# R5 unit crceng: one native CRC engine, and the byte loops beside it (lead, 2026-11-09)

## Read first
`S/u35r/r1/common_r1.md` (binding, its "Every level" and "The platform first" lines above all; labels `crceng_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/r5/CPRIM.md` (the
evidence: sections 1, 2 and 3.2-3.3), `S/u35r/findings/FINDINGS.md` 12.113-12.117, the chip probe
`S/u35/lead/probes_20261109/crc_chip.py` (its `viper_hoisted_crc`: 0.95 ms for 264 B on the RP2040, "same" value),
`S/u35r/r5/HANDBACK_BFIX.md`. Code: the integration tree `S/wt-u35int` at a202591d.

## Owner (verbatim)
- 2026-11-09 17:33:38: "Micropyhton has a C implementation for CRC which can replace the existing modules? Finding such
  cases absolutely *is* the spirit, ..."
- 2026-11-07 17:31:00: "Probably applying this this already answers the open questions about the checksum from, and
  respecting, multiple points of view." 16:47:31: "... from there on minimal, efficient and lean changes."

## Your work (worktree `S/wt-crceng`, branch `audit/crceng` from int `a202591d`; create it; commit locally, never push)
1. `src/asy_crc_checks.py`: one `@micropython.viper` engine for widths 8, 16 and 32 (MSB-first, no reflection, no final
   XOR, the module's three polynomials and inits) replaces `_crc` and `_crc_wide`, its 32-bit constants converted once
   before the loop and the word masked explicitly (x64 has 64-bit words). Every value stays bit-identical: the CRC-8 is
   Sensirion's wire, the CRC-16 the UART peer's contract, the CRC-32 the stored FRAM chunks. The per-byte yield goes
   (no CRC holds the loop past ~1 ms). Whether the public methods stay coroutines: decide by the figure - a coroutine
   frame per call (160-416 B, SPEC I.2) against the call sites to change; prefer plain functions if the sites are few.
   `run_inc()`/`check_inc()` have no `src/` caller since bfix: they go with their pinning tests, if nothing else needs
   them. SGP40's backup chunk then holds its `_op_lock` ~1 ms for its CRC instead of ~272 rounds (quiesce's 8 s bound).
2. The project's first viper code, done once and cleanly: ruff's `builtins` for the viper names in `pyproject.toml`
   (one line), one `# type: ignore[arg-type]` per viper function where mypy needs it and nowhere else,
   `S/u35r/r0/module_sizes.sh` gets `-march=armv6m` (it is lead tooling: say the line in the hand-back, do not edit
   it). Check that the frozen image builds (`scripts/build_firmware.py dev`) and that both Unix-port binaries and the
   twin agree; a viper body shows as unexecuted under coverage (advisory only): say so where Part E.5 lists such gaps.
3. The byte loops beside it, each same-result: `asy_uart_driver.py` `_rx_copy` (viper or slice moves, no allocation in
   the steady state); `asy_fram_manager.py`'s verify compare by slice `==` (if bfix's compare left one); `asy_i2c_driver.py`
   `_bytes_to_int` -> `int.from_bytes`. The UART write gate (`asy_uart_comm.py:385-393`: a deadline waited in 20 ms
   steps, 75 rounds per hold-off) waits its deadline once. `buildgen/validate.py`'s poll rule admits `poll_idle_ms = 1`
   (1,000 rounds a second per idle link): a floor from the link's physics (a frame's wire time at its baud), stated.
4. Report only, change nothing: COBS (`asy_framing_codecs.py`, wired on no device) and `_rx_line_len` (no `src/` caller)
   - their owner records (git, SPECIFICATION.md, PROJECT_AUDIT_PLAN.md, the owner rulings file) and whether removing
   them is a removal the owner must decide.
5. Tests first (seen red on a202591d where they pin a change): every width bit-identical to independent oracles over
   random and edge inputs (the suite's CPython oracles, zero, one, 264 and 512 bytes); the residue property; the golden
   FRAM image (bfix's T3) still reads back; the cost tests that pinned the per-byte yield (`tests/test_asy_crc_checks.py`
   :836-863) go with the yield (list them first); the SGP40 chunk's `_op_lock` hold in rounds is pinned low.
   `tests_hardware/device_scripts/loop_stretch_timing.py` follows the API if it changes (its CRC fact stays).
6. Docs, current state, fewest lines: Part I's CRC paragraph and F.3's rows (the yield and its ruling gone, the
   engine named, the chip figure 0.95 ms per 264 B with its condition); SPECIFICATION.md's "fixed because the chips and
   the UART peer depend on them" (grep it) corrected for CRC-32 (only FRAM); a Part F line that the project uses the
   native emitter, where, and its limits that bind (no default args, masks, no 64-bit product); the UART changelog,
   one Class B entry (same wire bytes).

## Never
Never change a CRC value, a wire byte or the stored chunk format. Never edit `ext/`; never read `arduino/`; never open
`/root/.claude/`; no hardware. No `gc.collect()`, no new delay. Credential filter on every view of SPECIFICATION.md,
CLAUDE.md, `devices/`, generated modules and `audit/`; never print, copy or write any Wi-Fi credential or the hotspot
password.

## Checks
Each touched test file at both GC stages while fixing; `lint_direct.sh`; the three mypy passes; then the gate as
common_r1 says under `S/u35/lead/heavy.lock` holding the line `crceng` (unit bchain may hold it: wait while it exists;
`rm` it, literal path, its own command, after). Sizes and `imageFreeBytes` against a202591d.

## Limits and hand-back
Write only the files above and their tests. One commit. Budget about 2 % of the week. Hand back by 01:00 UTC:
`S/u35r/r5/HANDBACK_CRCENG.md` (at most 30 lines, as common_r1 says, with need against cost per changed operation),
your commit, one line per headline result, and last "nothing of mine is running".
