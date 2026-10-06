# Audit register

Temporary, like `PROJECT_AUDIT_PLAN.md`: removed with `audit/` at phase D. Plan 4.5 defines its fields, plan 4.7 the
lease and resumption procedure.

## Header

| field | value |
|---|---|
| lease | session `01BWfjT6GSD7bxCP57j86vB8` (https://claude.ai/code/session_01BWfjT6GSD7bxCP57j86vB8), since 2026-10-06 |
| released | — |
| audit branch | `claude/whole-project-audit-plan` (PR https://github.com/hundertvolt/sensors/pull/107) |
| go-ahead | OR145 (plan 3.2), 2026-10-06: implementation up to the first required real-hardware step |
| planning baseline | `4dc80ef` |
| audit baseline | `798e5a7` (`origin/main` at the go-ahead; already an ancestor of the audit branch, so anchors resolve at the branch head and only BACKLOG.md lines from :350 on move by +1) |
| current phase | B0 (unit U0) |
| work order | `audit/order/WORK_ORDER.md` (1909 changes, 6571 steps, 0 violations) |

## Unit table

| unit | scope | state | commit |
|---|---|---|---|
| U0 | B0 ENV: baseline, apparatus, prevention rules, B0 doc pass | not started | — |
| U0R | dependency refresh after the baseline | not started | — |
| U1 | legacy move to `legacy/` | not started | — |
| U2 | error-number catalog | not started | — |
| U3 | central log-repeat rule, one entry per event | not started | — |
| U4 | compare-before-write primitive, SCD30 onto it | not started | — |
| U5 | config objects and `max-args` | not started | — |
| U6 | one-source website definitions | not started | — |
| U7 | tier ladder and runner summary block | not started | — |
| U8 | `@tunable` scheme | not started | — |
| U8C | `@tunable` classification of tests | not started | — |
| U8C2 | search gaps of the test-tier classification | not started | — |
| U9 | LED pilot | not started | — |
| U10 | XCUT: system-wide contracts | not started | — |
| U11 | CORE | not started | — |
| U12 | ALGO | not started | — |
| U13 | BUS | not started | — |
| U14 | PLAT | not started | — |
| U15 | SENS | not started | — |
| U16 | STOR | not started | — |
| U17 | UART protocol | not started | — |
| U18 | NET | not started | — |
| U19 | REST | not started | — |
| U20 | GEN | not started | — |
| U21 | TOOL | not started | — |
| U22 | LED re-check | not started | — |
| U23 | WEB | not started | — |
| U24 | TEST | not started | — |
| U25 | TWIN | not started | — |
| U26 | HW levels L3/L4 | not started | — |
| U27 | SCR | not started | — |
| U28 | CI | not started | — |
| U29 | SEC | not started | — |
| U30 | MEM | not started | — |
| U31 | PERF | not started | — |
| U32 | PAR | not started | — |
| U33 | DOC | not started | — |
| U34 | LIC | not started | — |
| U35 | B3 test campaign | not started | — |
| U36 | B4 docs pass | not started | — |
| U37 | B5 close of execution | not started | — |
| C | hardware rounds (own go-ahead per session) | not started | — |
| D | close: plan and audit/ removed, one merge into main | not started | — |

## Non-interference (A.U0.04)

Applied from the first executing agent on:

- One worktree per executing agent (`git worktree add`); auditors and verifiers never write in the lead's checkout.
  Implementation agents work on disjoint files only.
- Every port-binding command (`scripts/test.sh`, `npm test`, twin runs, coverage) runs under
  `flock /tmp/sensors-audit-ports.lock` until U0 proves network-namespace isolation (M.PROC.003 (5a)); firmware builds
  under `flock /tmp/sensors-audit-toolchain.lock`. A private toolchain copy (with its own `setcap`) only when the shared
  one is locked longer than the agent can wait, never by default.
- Before a rerun, the twin's FRAM log is read; `digital_twin/fram_state.json`, `digital_twin/scd30_state.json`,
  `digital_twin_ci_logs/`, `htmlcov*/`, `coverage*.xml` and failed-run output move to `audit/archive/<UTC timestamp>/`
  (the last 3 kept). Only pure scratch is deleted; evidence is moved, never deleted.
- Fault planting and repeat runs are budgeted first, run on tmpfs, at most about 20 repeats, as confirmation only. A
  timing failure under contention stays unconfirmed until reproduced alone. A retry is never a fix (OR37.a (2)).
- Worktrees and scratch branches go when their unit closes.

## Unreachable sources (OR4.a)

| source | reason | needed for |
|---|---|---|

## Owner-review list (OR2.c)

Decisions taken on the owner's behalf during execution, for the B5 review.

| unit | decision | reasoning |
|---|---|---|

## Parked deltas (OR2.c, OR106.a)

Findings during execution that need a change outside the work order; each passes A-C as a delta before it is applied.

| unit | finding | state |
|---|---|---|
| U15 | SCD30 temperature offset truncated (`src/asy_scd30_driver.py` `int(offset * 100)`): one tick = 0.01 °C (Interface Description §1.4.7), so 4,585 of 65,536 float32 inputs write one tick low and read back 0.01 K under the PUT value. Upstream Adafruit `3eb3b52` uses `round()`. Legacy deployed driver also truncates, so this is a D.1 flag (behaviour vs field behaviour). Found by the refresh, family (g). | parked; A-C delta before U15 |
| U18 | NTP accepts 44-47-byte replies (`src/asy_ntp_client.py`, no length check; `tests/test_asy_ntp_client.py` pins `_truncated(44)` as accepted). The NTP header is a fixed 48 bytes; upstream micropython-lib `9ec1830` rejects shorter replies. Receiver-side tightening. Found by the refresh, family (g). | parked; A-C delta before U18 |
| U18 | NTP accepts a zero transmit timestamp: raw 0 maps through the era step to 2036-02-07, inside the 2025-2100 plausibility window, so a malformed reply with stratum ≠ 0 sets the RTC to 2036. Upstream micropython-lib `5139530` rejects it. Receiver-side tightening. Found by the refresh, family (g). | parked; A-C delta before U18 |

## Findings

| ID | title | area | severity | status |
|---|---|---|---|---|
