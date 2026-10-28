# Pass 2 verification — lead rulings

Inputs: `V1.md` (G1-G3, 19 defects), `V2.md` (G4-G5, 14), `V3.md` (G6-G8, 14 entries, V14 covering 8
requirements), `V4.md` (G9, G10, LEAD, 21). Every defect was checked by its verifier against the source;
the lead read each one. Ruling: **apply the verifier's Fix as written**, except as below.

| Defect | Ruling |
|---|---|
| V3/V14, V4/V03 (list-L items with an owner trail: ranked owner in some groups, agent in others) | Not relabelled now. OR71.a (0) answered "keep them, labelled as agent design" for all 75, while about 25 of them carry an owner trail in their introducing commit; that is an OR3 fine-tune question (owner question 4, LEAD.md section 4). Until answered, each such requirement keeps its current rank with the note "rank per owner question 4"; G9/R38's kept list is completed per V4/V03 and becomes the question's option (b) list. |
| V4/V01 (boot order; LEAD section 1 #3, G5/R05, harmonization 42) | Accepted. The owner confirmed OR47.a (1)'s order ("1. yes"); the code starts timers before tasks. The lead's resolution is withdrawn: G5/R05 states OR47.a (1)'s order as the requirement and records the code's order as a finding; owner question 3 asks which order stands. |
| V3/V07 (emptying the DNS fallback list from the website) | Resolved without a question: OR56.a (2) makes the list "a website-visible, user-changeable networking setting that can be emptied", so the website offers an explicit clear action for it (sent only on that action); A24 stays as it is for `PW`. |
| V3/V12 (soak trend retry) | Accepted: fail closed; a remaining retry need is parked for the owner (execution-time OR2.c parking), never kept on the agent's decision. |
| V3/V13 (G8/R61 `disallow_any_explicit` "holds") | Accepted: State "open — owner question 2". |
| V4/V19, V4/V20, V4/V21 (LEAD/R01, R17, R18) | Applied by the lead in LEAD.md. |

The fixes change ranks, dates, scope wording and four factual counts; no fix changes what execution
builds except V1/V01 (L0 and the stop-before-hardware rule in the runner requirement), V1/V17 (the
repair exception restored), V2/V14 (the documented-runtime-failure guard kept), V3/V07 (clear action),
V3/V11 (no port redirect seams) and V4/V01 (boot order open).
