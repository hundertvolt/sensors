lr draft, written by the agent (Tue Nov 10 20:12:01 UTC 2026)
## Relay <UTC> - lead to bench: the last round, on the final image
New head: <bench sha> (main line <int sha>, CI green). src/ changed since snapshot 58: a new image. First: a fresh
session with the owner's go-ahead; uv 0.13.7 in .uvpin/bin (the new pin; `run` puts it first, refuses any other);
`mv $H/logs/1.log $H/logs/1_round1.log`, so the flash guard waits for today's dump. Ask the owner for each flash cycle.
a. `run 1 2`, board still on snapshot 58: FRAM evidence first (/status with errcount, the raw dump; clear nothing),
   then env --tier bench on the new pins with the package list. Then `run 4a` (host only, nothing beside it).
b. From this head, two throwaway worktrees, never committed, in this order: lwIP control (setup_toolchain.py:697's
   override call out, `--output <abs>/control.uf2`, record "overrides": []), then GC control (codegen.py:830's
   gc.threshold line out, `<abs>/gc_control.uf2`, record dirty: true), the last rp2 build before 3g.
c. `GC_CONTROL_IMAGE=<abs>/gc_control.uf2 run 3g 5gh`: the default flash and bench tiers without the threshold (pass:
   green, no allocation-failure text), then 5gh: /status read by 6, 6, 6, then 2 readers, 60 s each, 120 s idle and
   one collect after each, mem_free and the largest free block every second.
d. `run 3 5h`: 3 builds and flashes this head's dev image; 4b, 5 and 5h as in 3. Per tier: verdict, every ResetReason,
   errcount after each step, the UART figures, the FRAM command hold, C-stack peak, free alarms, ISL29125 G01/G02, the
   SGP40 (voc, raw) samples. A red in 3g-5h: stop and send it (a fix means both images again, before any opt-in wear).
e. `run 9 10m`: crc16 hazards (both ends' logs and ring counters at a failing exchange), the 10 min soak (SGP40
   cadence, ~600 cycles) and the mid soak. Step 11 is done: not again.
f. `run 12a 12g`: boot feed stamps, ring peak (both rings 512 B), DNS idle poll, ResetErrors budget (clears every
   FRAM log 15 times, its own /status read first), general call per chip, 12g the FRAM chunk timing (no CS settles).
g. `run 16b` (BMP3XX calibration bytes, soft-reset half); `CH13=1 run 13` once the owner's AP is on channel 13.
h. Long soaks 10c-10h, 6 h 20 each, one a day as the owner chooses (10g the HTTP soak, 10e triggers, 10h FRC values).
i. Wear, once my `cleared:` line is in WEAR.txt: `run 7f 10b` (LWIP_CONTROL_IMAGE=<abs>/control.uf2, the NeoPixel
   rig; 8f/8b five flash cycles), then `run 15` (two; ends on this image). A passed wear step never runs again.
j. With the owner, no runner step active: M1 (isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry, 30 min,
   <lead: before or after 7f>); real_fram_persistence_across_power_cycle (no SCD30 pressure read any more);
   run_pin_reset_keeps_or_clears_the_record; the bridge by env --tier bench under its timer, a second armed by hand.
k. Host, no runner step active: noble and trixie at this head in the existing chroots, `mount -t tmpfs tmpfs
   "$CHROOT/tmp"` first; no new chroot (if trixie's is gone, tell me first).
Wear: 9 flash cycles, 126 owned config writes, 14 SCD30 NVM writes, up to 422 prerequisite writes. Figures as before.
## 2. Per step: rows (CLOSE_STATUS) · round1.sh · FC/FS owned/NVM/prerequisite · sheet min (11-05/06 full run)
1 FRAM rule, B48, L01 · :27 · 0 · 5 (<1); 2 B43, L07 packages · :28 · 0 · 30 (14); 4a :69's basis · :29 · 0 · 180 (58)
3g 4g 5g L01, L03, B16, B44 · :30-32 · 1/0/1/202 · 305 (1, 22, 34); 5gh 5h L05 · missing: 2 rows + 8 lines · 0 · 16 each
3 4b 5 L01, L03, B16, B19, B21-B23, B26, B34, B36, B38, B39, B41, B44, F3, L07 1/4/11 · :33-35 · 1/0/0/202 · 335 (4, 24, 73)
9 L07 · :36 · 0 · 10 (3); 10a 10m B28, L03 · :37-38 · 0/0/0/16 · 105 (15, 33; red); 11 L07 · :39 · done; 12f · out (8 lines)
12a-12e B20, B41, L02, B45, B33 · :40-44 · 0 · 29; 12g L04, B19 · missing: 12f's row + 1 line · 0 (FRAM at 0x30000+) · 3
16b B38 · :46 · 0 · 3; 13 L07 item 8 · :47 · 0 · 3; 10c-10h L02, B46 (10g), L01 (10e), L07 (10h) · :48-53 · 0 · 380 each
7f 7b B21, B35, B17, B03, B04, B24, B42, B44 · :54-55 · 0/122/13/0 · 120; 10b B32, L07 · :58 · 0/4/0/2 · 60
8f 8b B30, B44 · :56-57 · 5/0/0/0 · 90; 15 B47 · :59 · 2/0/0/0 · 170. Not in the runner: B17 M1, RUN pin, power cut ~45;
  B31 ~15; B52 ~1 h a leg. Board ~14 h sheet (~5 h measured), soaks 38 h, wear ~7 h; FC 9, FS 126, NVM 14, pre 422.
## 3. round1.sh against bc53cdfa (-U0; -U1: ftmp_lr/round1_u1.diff), the probe edit; the relay above goes after both
```diff
--- a/audit/artefacts/evidence/U35_close/redo/hw_round1/round1.sh
+++ b/audit/artefacts/evidence/U35_close/redo/hw_round1/round1.sh
@@ -32,0 +33 @@
+  "5gh|heap_loads_gc_control|16|0|0|0|0|end|GC_CONTROL_IMAGE, DUT_IP|heap_loads ctl"
@@ -35,0 +37 @@
+  "5h|heap_loads|16|0|0|0|0|end|DUT_IP|heap_loads"
@@ -45 +47 @@
-  "12f|held_sda_resets|8|0|0|0|0|end|DUT_IP; owner: scope optional|held_sda"
+  "12g|fram_chunk_timing|3|0|0|0|0|end|-|framchunk"
@@ -74,0 +77,8 @@
+heap_loads() {  # 5gh, 5h: /status read by 6, 6, 6, then 2 readers, one collect after each idle (lead, 2026-11-10)
+  local p=$H/probes_20261110 c=$L/heap_loads${1:+_$1}.out
+  [ -z "${1:-}" ] || [ -n "${GC_CONTROL_IMAGE:-}" ] || { echo "NOTE GC_CONTROL_IMAGE unset: owed"; return 0; }
+  sed "${1:+/^gc\.threshold(32768)\$/d}" "$p/snap58_heap_loads.py" > "$L/heap_loads.py"  # ctl: no threshold, as that image boots
+  sed "s#^SCRIPT = .*#SCRIPT = \"$L/heap_loads.py\"#" "$p/heap_loads_host.py" > "$L/heap_loads_host.py"
+  uv run --no-sync python "$L/heap_loads_host.py" "$c" && python3 "$p/heap_loads_summary.py" "$c" && grep -q '^DONE' "$c"
+}
+
@@ -191,7 +201 @@
-held_sda() {  # row 12f: SDA held, then each reset kind; /status and /sensors once the product serves again
-  local m
-  for m in machine_reset watchdog; do
-    mpc held_sda_reset.py 60 -e "s/^MODE = .*/MODE = \"$m\"/"
-    py get status 180 && py get sensors 30
-  done
-}
+framchunk() { : > "$L/mp.out"; mp "$H/probes_20261110/fram_chunk_timing_frozen.py" 180; grep -q '^FRAMCHUNK done' "$L/mp.out"; }  # row 12g
```
Probe: hw_handover/mp/ring_peak_final.py:33 `(the SCD30 reset alone waits 2.5 s)` -> `waits 2 s)`; no other probe changes.
## 4. What cannot be done yet, and where sources disagree (said, not decided)
- No instrument: BACKLOG:64-66's damaged-config boot (the repair write's stretch, one gated flash write; no hit in
  tests_hardware); 16b's power-on half (HANDOVER:127-129; B38's A02 bytes come from 4b and 16b alike). The step-1 guard
  (round1.sh:63) accepts 11-05's DONE, hence the mv. Unverified: a passing 4b keeps the SGP40 samples (F3). Unread
  (filter): 10b's needs field, REPORT 7 item 12, BACKLOG:387 (`sudo -k`).
- M1 before S3b (BACKLOG:35-40) vs 7f on wear day 1, M1 on day 2 (HANDOVER:91-92). codegen.py:830, setup_toolchain.py:697
  at bfa240fa vs HANDOVER:23/:28 (:835, :671), A.C.09 (C.md:408, :704). rx_ring 512 B (dev.toml:54/:66; BACKLOG:229-236) vs
  HANDOVER:104-106's 8192 B. HANDOVER:138 (the cut reads AmbPres), B29/B52 OWNER vs 12.177 (settled). L02 omits 10b (not
  run). HANDOVER names 12f 4 times. 4a and the chroot legs' test.sh overlap on the Pi. O6 (a) needs 11-07's trixie chroot.
