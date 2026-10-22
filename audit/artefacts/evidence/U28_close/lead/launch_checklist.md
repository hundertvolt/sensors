# U28 launch checklist (the lead, before each wave and the API resume)

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Placeholders the briefs keep literal until
filled in the launch or resume message: `<API>` (`audit/u28-api`: R1 on `b1fecfb`), `<W1>` (`audit/u28-w1`: C, W, R, P plus
the lead step). Never edit a brief a lane is already reading. CONCURRENCY rule 12 for every launch: files row in
`S/u21/RUNS.md`, `comm -12`, `ps` heavy count; one lead_todo line per event.

## Before wave 1 (C, W, R at `b1fecfb`)
1. Base: `git -C /home/user/sensors rev-parse b1fecfb` resolves; CI on `b1fecfb` green (run 38777834467, 45/45); `[ -c
   /dev/null ]`.
2. L0 done (brief_lead.md): `S/u28/host_findings.txt` written, the sets rewritten by `python3 -I S/u28/tools/lanes.py`.
3. Disjointness: `cd S/u28; for a in C W R P LEAD; do for b in C W R P LEAD; do [[ $a < $b ]] && comm -12 <(sort
   files_$a.txt) <(sort files_$b.txt); done; done` prints nothing, and `cat files_{C,W,R,P,LEAD}.txt | sort | uniq -d` prints
   nothing; rerun after any set change.
4. Each lane's set in `S/u21/RUNS.md`; at most six agents (this unit holds four at once); no gate running; `ps` matches
   RUNS.md.
5. Toolchain and copies: `/root/pico-toolchain/micropython/ports/unix/build-{standard,settrace,lwip}/micropython`,
   `/root/pico-toolchain/micropython/mpy-cross/build/mpy-cross`, `/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin`,
   `S/shared/node_modules`, `S/shared/typings`; `sha256sum S/shared/package-lock.json` equals `git -C /home/user/sensors show
   b1fecfb:package-lock.json | sha256sum`; `/home/user/sensors/.venv` current with `b1fecfb`'s lock (`uv lock --check`).
6. Names free: branches `audit/u28-{c,w,r,p,x,api,w1,w2}`, worktrees `S/wt-u28{c,w,r,p,x}`; `S/u28/relay.md` holds only its
   headings (`## C`, `## W`, `## R`, `## P`); `S/u28/lane{C,W,R,P,X}/` exist.
7. The base sweep done (`S/u28/base_times.tsv`) before any lane compares an after-time.
8. Points the lead rules on before launch (each brief already takes the default): R-1/R-2 (four code lanes kept whole),
   R-3 (R1 the one API stop), R-5 (owner question 1's default), R-8 (the e2e matrix shape), R-11 (the lock and one-liners),
   R-14 (the open-finding defaults), R-15 (the datasheet move at `<W2>`), R-18 (no real-port guard in U28).

## Launch messages
Each carries: the base hash, the lane's L0 host-finding lines (C, W, R), the `base_times.tsv` path, and for P `<API>`'s hash
and R1's red lines naming P's files.

## Resuming R and launching wave 1b (P on `<API>`)
1. `<API>` per brief_lead.md "The API merge"; R's R1 hand-back lists every red line by file and owner: copy P's into P's
   launch message with `<API>`'s hash.
2. Disjointness again (R's remaining set, C, W, P, LEAD); RUNS.md rows; names free; `ps` heavy count (one heavy run per lane;
   P's twin file and W's live JS runs are wall-time bound).

## Before wave 2 (X on `<W1>`)
1. `<W1>` per brief_lead.md; the relay complete (C, W, R, P sections filled; the lead's budget lines follow after CI).
2. RUNS.md row; names free (`audit/u28-x`, `S/wt-u28x`); nothing else of the unit running beside X but the lead's records.
