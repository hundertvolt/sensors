# Phase A-L — brief for the action-list agents (2026-09-29)

Common part for every A-L agent. Your UNITS and HEAD follow in the prompt that launched you.

You are an A-L agent of the whole-project audit of the `sensors` repo at /home/user/sensors (branch
`claude/whole-project-audit-plan`). Audit execution is BLOCKED. You change nothing except your output files
`/home/user/sensors/audit/actions/<UNIT>.md` (one per unit you were given). Append as you go so partial work survives.

## Why

The owner (OR106, 2026-09-29): "Step by step create a complete action list of which changes would be done in
execution, including higher order changes in other parts ("blast radius")". OR106.a: every register work line
becomes one or more concrete changes (site: file and function or doc section; what changes; why, with the register
ID), each with its blast radius — callers, generated code and buildgen templates, the `js/` mirror, tests at every
tier, the digital twin, SPEC/CLAUDE.md/README text, TOMLs, UART_C_PORT_CHANGELOG entries; built unit by unit in plan
4.1 order. The next step (A-C) merges all changes to one site into one and orders them; the owner then gives the
execution go-ahead on that list. So every action must be precise enough to implement without a further question,
and every blast-radius slot must be the result of a search, not a guess.

**Accuracy before speed (owner, OR107.a).** Never cut a check short or sample. If your input is more than you can
do properly, finish fewer blocks completely and list the rest as NOT-DONE in the ledger — never skim.

## Read first

CLAUDE.md; `audit/CONSOLIDATION.md` sections 1, 2, 3 and 9; `PROJECT_AUDIT_PLAN.md` 4.1 (units) and the owner rows
of section 3.2 your blocks cite (each a quote row plus an ".a" reading; the most recent owner decision wins; OR64: a
missing owner trace never proves the owner did not decide); your input file(s)
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/al/input_<UNIT>.md` (every live
register block whose State names the unit, in full); the action files of earlier units already in `audit/actions/`
(reference their actions instead of repeating them).

Units: U0 ENV · U1 legacy move · U2 error-number catalog · U3 log-repeat rule · U4 compare-before-write · U5 config
objects and `max-args` · U6 one-source website definitions · U7 tier ladder and runner summary · U8 `@tunable` ·
U9 LED pilot · U10 XCUT · U11 CORE · U12 ALGO · U13 BUS · U14 PLAT · U15 SENS · U16 STOR · U17 UART · U18 NET ·
U19 REST · U20 GEN · U21 TOOL · U22 LED re-check · U23 WEB · U24 TEST · U25 TWIN · U26 HW · U27 SCR · U28 CI ·
U29 SEC · U30 MEM · U31 PERF · U32 PAR · U33 DOC · U34 LIC · U35 B3 test campaign · U36 B4 docs · U37 B5 close ·
C hardware rounds. Test levels (OR45.a): L0 host (`tests_scripts/`, `tests_js/`), L1 unit (`tests/`, Unix port),
L2 twin (`digital_twin/`, `tests/test_digital_twin_*`), L3 flash (`tests_hardware/flash`, device scripts), L4 bench
(`tests_hardware/bench`).

## Constraints (binding)

Read-only on the repo; git read-only (log, show, blame, diff, grep); no tests, builds, `uv`, `npm`, `mpremote`, port
binding, network. Never read `arduino/`. `ext/` only for Microdot semantics. The legacy tree (`python/`,
`modules/`, `build-*.sh`, `dev_legacy/`, `html_raw/`) is reference-only: an oracle, never an action site (U1's move
is the one exception: it moves the tree, it does not edit it). Generated modules: read them through
`buildgen/codegen.py`'s templates. Scratch for ad-hoc `python3` scripts:
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/al/<UNIT>/`. Primary sources under
the scratchpad: MicroPython v1.29.0 `mp/`, v1.28.0 `mp128/`, lwIP `lwip/`, cyw43 `cyw43/`, Microdot `microdot/`,
datasheet text `dstxt/`. Never state a fact from memory: open the site and cite it at HEAD.

## Method, per register block of your unit

1. Take every work clause of the block's State (and any Req part not yet true at HEAD) that names your unit. A
   clause naming only other units is theirs; skip it. A block with no clause for your unit but listed in your input
   (the unit appears in a site hint or a note) gets a ledger line saying so.
2. Open every site at HEAD. Register line numbers may be stale: cite the current ones. If the work is already done
   at HEAD, say so with evidence (DONE-AT-HEAD). If the register's premise is wrong at HEAD, say what is true and
   propose the register fix.
3. Write one action per distinct change at one site. A change that needs edits at several sites of the same
   mechanism (a function and its only caller) may be one action if listing them all; a doc change at a different
   file is its own action when it is the clause's main work, otherwise it sits in the Docs slot.
4. Fill the blast radius by searching (grep the changed symbol, constant, message text, error number, field name,
   config key, route, CSS class) across `src/`, `buildgen/`, `devices/`, `digital_twin/`, `tests/`,
   `tests_scripts/`, `tests_hardware/`, `js/`, `tests_js/`, `html/`, `scripts/`, `toolchain/`, `.github/`, the
   config files and every doc (`SPECIFICATION.md`, `CLAUDE.md`, `README.md`, `BACKLOG.md`, `DEVICE_REFERENCE.md`,
   `UART_C_PORT_CHANGELOG.md`, `digital_twin/README.md`, `tests_hardware/README.md`). Name every existing test that
   pins today's behaviour and would break or need adapting, and every new test the register asks for (level, file,
   what it proves). "—" in a slot means you searched and found nothing.
5. Choices: where the register or an owner row settles an option, follow it. Where a detail is open and an owner
   row or the register decides it by reading, decide and say from which. Only a genuine owner-level choice becomes
   an owner question; still write the action with your recommended option, marked "pending Qn".
6. Text an action writes into a permanent file (code, comments, tests, CLAUDE.md, SPECIFICATION.md, README,
   BACKLOG, TOMLs, CI) never cites a temporary audit ID — OR rows, unit labels, register IDs, HR/RF/D4/list labels,
   WP/Session/Step labels, action IDs: state the fact in place, provenance as an actor tag "(owner, <date>)" /
   "(agent, <date>)" (G9/R12, OR68.a (4)). IDs belong only in the action file's Why and Depends slots, or in a `[src: …]` note beside the planned text, which the executor never writes. CI checkouts
   are shallow (no `fetch-depth` in `ci.yml`): a check needing git history or a submodule says how it gets it.
8. Recovery ladder (owner, 2026-09-30, OR113.a): every fault on a bus, a participant or a service recovers with the
   smallest possible blast radius and escalates only when the milder step fails — retry; recover the participant;
   clear the bus; re-initialise the controller; restart the task; reboot; watchdog last — at boot and mid-operation,
   each rung bounded, logged once per event, race-free, tested at every level that can reach it. Where a unit's
   code has a fault path, plan its rungs.
9. Owner words: quote exactly; call something the owner's only with an owner source. The action's Why cites the
   register ID(s) and the owner row(s) the register cites.

## Output format (`audit/actions/<UNIT>.md`)

```
# A-L <UNIT> — <area name> (HEAD <sha>)

## Actions

### A.<UNIT>.nn <imperative title, max 10 words>
- **Why**: <register ID(s)> — <the clause, short> (<owner row or rank>)
- **Site**: `<path>:<lines>` <function / section>
- **Change**: <what changes, precise enough to implement; before → after where useful>
- **Blast**: callers <…> · generated <…> · js <…> · tests <existing that change: …; new: Lk file — proves …> · twin <…> · docs <…> · toml <…> · uart <Class A/B entry text, or —>
- **Depends**: <A.<unit>.nn list, or —>
- **Kind**: code | test | doc | rule | hardware (one or more)

## Ledger
| register block | clause for this unit (short) | result: action IDs · DONE-AT-HEAD (evidence) · NO-CLAUSE · NOT-DONE (why) |

## Register fixes
<block ID: the exact line to change, with the evidence — stale line numbers, wrong premise, wrong unit>

## Open points
<numbered owner questions in the owner's format — a top-level decision in max 10 words, then options each with its
consequence — only after self-resolving from owner rows, the register and the sources; cite the actions they settle>
```

Every input block gets a ledger row. FINAL REPLY (max 150 words): per unit the counts (blocks, actions,
DONE-AT-HEAD, NOT-DONE), the register fixes and open points as one line each.
