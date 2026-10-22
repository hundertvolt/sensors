# Real-hardware items for the phase-C rounds (M.PROC.029, A.U35.54)

Requirement: every B3 item that needs silicon, with its level, gate, twin-first record and the property it proves, mapped to an `audit/actions/C.md` inventory row H01-H83 (a row with none is added to both, A.U37.05); handed to U37 for BACKLOG's "Real-hardware work still owed". Per round: lower levels first on the same commit, FRAM logs read and saved first, standard board state at start and end, wear gates default-off unless the round names one. Nothing here runs in B3. Completion: every item has its round and inventory row. A defect any file records goes the OR12.a path (fixed with a regression test seen failing first, or an owner question), never a note alone, and passes A-C as a delta before it is applied (OR106.a). The file is complete when every row is terminal: biting, fixed, or justified with its reason. Opened by A.U35.01 / M.PROC.022 (agent, 2026-10-22); deleted with `audit/` at phase D.

| item | source | level | round (H row) | gate | twin-first record | property proved |
|---|---|---|---|---|---|---|

## Items

From M.PROC.029's list (agent, 2026-10-22); every H row checked present in audit/actions/C.md at `e1ad71f`. Gates are
the default-off markers a round must name; a twin-first record is A.U35.49's.

| item | source | level | round (H row) | gate | twin-first record | property proved |
|---|---|---|---|---|---|---|
| silicon arm of the hardware memory gates | A.U35.05 (3), M.PROC.037 | L3/L4 | R1 (H43) | none | open (A.U35.49) | a caught allocation failure prints the interpreter's wording and turns both hardware gates red |
| lone-BMP3xx general call | A.U35.21 | L3 | R1 | none | open (A.U35.49) | the lone-BMP3xx general-call expectation, as A.U35.21 states it |
| torn write on the bench reset race | A.U35.40 | L4 | R3 | persistence_write | open (A.U35.49) | the torn-write expectation on the bench reset race, as A.U35.40 states it |
| silicon-only interaction, recombination and rung cells | A.U35.08, A.U35.09, M.PROC.026 | L3/L4 | R1 (H71) | none | open (A.U35.49) | every conformance.md queue_c cell (236 at the walked commit) |
| OR115 lwIP stall, then the override hammer | A.U21.14 | L4 | R4 (H39) | flash_cycle | open (A.U35.49) | the stall reproduces on the unpatched image and the override ends it |
| OR116 CRC16 over the jumper and on a reflashed image | A.S0930.05, A.S0930.06 | L3, L4 | R1 (H37), R4 (H38) | flash_cycle (H38) | open (A.U35.49) | both CRC modes interoperate over real wire |
| the four SystemCmd words on the board | A.S0930.28, .29, .39, .40 | L3/L4 | R1-R3 (H13, H14) | persistence_write (resetconfig) | open (A.U35.49) | function, refusal, timing and race of each word on silicon |
| two-image GC proof | SPECIFICATION.md E.6.1 | L3/L4 | R7 (H45) | flash_cycle | open (A.U35.49) | both GC stages hold on silicon |
| bench trigger timestamps for the read stagger | - | L4 | R5 (H19) | long_soak | open (A.U35.49) | trigger spacing over a long run |
| speed-probe bands on the bench Pi4, no board | A.U35.23 | host | R0 (H56) | none | open (A.U35.49) | the probe bands and step timings on the real host |
| l3./l4. tunable rows | M.PROC.028 | L3/L4 | R1/R4/R5 (H55) | none | open (A.U35.49) | each estimated tunable measured |
