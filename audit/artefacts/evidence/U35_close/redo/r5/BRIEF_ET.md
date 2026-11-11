# R5 unit ET: the final image's three open behaviours, traced (lead, 2026-11-11; read-only)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `et_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Tree: int `S/wt-u35int` at
015dda9f, read only (never write there, never run anything in it). The bench's results: on
`origin/claude/u35-bench-campaign` (fetch it), `audit/artefacts/evidence/U35_close/redo/hw_round1/HANDBACK.md`, the
sections "Bench 2026-11-11 11:20 UTC - d" (final image) and the c section before it (the GC control image: the same
image without gc.threshold); earlier rounds' results for the same nodes are in that file's git history (`git log -p`,
filtered). The pinned MicroPython checkout: `S/tc-c/micropython` (ports/rp2, lib/lwip, extmod/modlwip.c); the overrides
the build applies: `toolchain/micropython_overrides.py` and SPECIFICATION.md B.14 (read filtered).

## Owner (verbatim)
- 2026-11-09 22:27:31: "... don't drop real features and don't introduce or reintroduce gaps. Lean, functional, no
  losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"

## Your work: for each, the mechanism with file:line evidence, whether earlier rounds passed it, what changed since,
## and whether it is a product defect, a test defect or a stated limit; then the smallest fix and its consequences
- E2 `tests_hardware/bench/test_modlwip_send_stall.py::test_no_send_stall_with_the_override`. Final image: the page load
  hit the 10.01 s client timeout with 5 connections at zero window, /status max 1.28 s, stopped 0 s, drained, page after
  True. Control: page 1.61 s, /status 10.01 s, stopped 10.51 s. The test's own rule: "A failed bound goes to the owner as
  an override change (a short POLLOUT back-off), never a larger bound". Which resource do the zero-window clients hold
  (lwipopts.h MEM_SIZE, TCP_SND_BUF, MEMP_NUM_TCP_SEG, PBUF_POOL), what frees it near 10 s (the per-call timeout?), what
  the override's EAGAIN path does to the asyncio writer (a poll-ready spin?), and would a short POLLOUT back-off, or
  something else, bring the page under 3 s. Say plainly if no change within the product can.
- E4 `tests_hardware/bench/test_uart_link_under_api_load.py::test_a_multi_chunk_set_echoes_intact_under_serving_load`.
  Final: 69 of 81 intact, 12 failures from round 46 on ("stored False, answer None"), UART_init Failures 0 -> 28,
  Transfers 17 -> 18; teardown UART_init E85 UART_REENTRANT and WEBSERVER W51 (both on control too: 76 of 86, 10,
  0 -> 29). What fails from round 46 (the REST call, the reentrancy guard, the ring, the peer), and what Part J,
  F.5.8/F.5.9 and the test promise under serving load.
- E5 The teardown codes and one counter: bus_concurrency `...never_corrupts...` reports SGP40 counter 2 under load;
  teardowns carry NTP E71 (x6 tests), SGP40 W33/W34/W35/W65, WEBSERVER W51 (x2), ISL29125 W31, and new on the final
  image ISL29125 E13 CHIP_SET in `test_reset_reasons.py::test_a_loop_ended_by_an_exception_after_boot_is_attributed`
  [exception] and E55 ISL_STATUS_READ + E1 STREAK in its [base]. Step 5 had 6 failed and 13 teardown/setup errors and 4b
  9 failed: map every failed node and error the HANDBACK names to A (twin divergence), B (boot wait), C (stale test), E2,
  E4, E5 or unexplained. For each code: declared by the test's provokes_log, a consequence of what the test does, or
  unexplained.

## Never
Never edit any tree or branch; never run a test, a probe or a build; git, grep and read-only text tools only. Never read
`arduino/` (`':!arduino'` in every git grep and git log); never view SPECIFICATION.md, CLAUDE.md, BACKLOG.md, README.md,
`devices/`, `audit/` or `src/asy_wifi_service.py` unfiltered. Never open `/root/.claude/`. No hardware, no mpremote.
Scratch only under `S/u35r/r5/ftmp_et/`.

## Hand-back
`S/u35r/r5/E_TRACE.md` (at most 60 lines; first line "et hand-back, written by the agent (<date -u>)"): per item the
mechanism, the evidence, the class (product / test / stated limit), the smallest fix with its consequences (lines, RAM,
an image change or not), and your confidence. Budget about 1 % of the week. Your last line: "nothing of mine is running".
