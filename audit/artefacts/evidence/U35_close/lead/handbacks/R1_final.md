R1 hand-back (root cause only). No commits, no tracked file edited. Probes, plants, logs and analysers are in S/u35/laneR/. Nothing of mine is running. RUNS.md has 19 start lines and 19 done lines. 62 tool calls.

**(a) Fold (14): the SCD30 nulls are a test-harness artefact. No firmware defect, so no class 4.**
- T3a's "unplanted" h14 run executed `S/u35/laneT/t3a_plant14/test_one.py`. The Unix port puts the script's own directory first on sys.path (ports/unix/main.c:688, v1.29.0). So the plant's `asy_base_classes.py` loaded in both runs.
- That plant changed line 455 to `return {name: values}`, which is exactly the `sensor_conf is None` branch. SCD30 is the only one of the three drivers that fails through it: a failed snapshot makes `_config_snapshot` return None, then `_get_mgr_cfg` returns None (asy_scd30_driver.py:247-249). So SCD30 sent `dict.fromkeys(cfg)`, all nulls. BMP3XX and ISL29125 fail through the callback branch (:461/:468), which the plant left alone, so they kept the marker.
- Proof: the same file copied into a clean directory passes 1/1 with all three markers (laneR/r1_a_1_wt-u35r_dev_-1.log). Run from the plant directory it gives T3a's nulls exactly (r1_a_2).
- Real hardware never sends nulls:
  - rp2 I2C raises ETIMEDOUT or EIO (machine_i2c.c:151-154).
  - Each SCD30 data word carries a CRC-8 (Interface Description), and a CRC mismatch raises (asy_scd30_driver.py:735).
  - `_config_snapshot` turns any of these into None, and the base class sends the marker (:454-455).
  - `_get_sensors` passes the marker through unchanged (asy_webserver_service.py:643), and `_get_settings_flat` maps it per field (:649-655).
- Effect: none on all six SCD30 devices (arzi, dev, grkizi, klkizi, schlafzi, wozi), in every mode. STA and AP serve the marker; Silent, Off and USB serve no API. No src fix is needed.
- Owed to lane T:
  - The draft test is a guard (green on head). T3a's plant bites only its SCD30 path.
  - bmp3xx and isl29125 each need a bite at the callback branch.
  - The control copy must run from a directory with no plant in it.

**(b) The drift red**
- **Rate:** full file, dev -1, alternating, base and head running side by side: base 0/16, head 0/16 (r1_rateA/B.sum). T3a's record holds one real drift red, the pair run. Its two "re" reds were `NameError: name '_yield_until' isn't defined`, not drift. So the red rate is about 1 in 17 head runs and 0 in 17 base runs, which shows no base/head difference. The test is unchanged and runs second on dev, before the changed watchdog test.
- **Mechanism:** 68 single-test probe runs (a census after each reading) show no per-death retention: the floors are flat from death 3 (0 B per death in every run, 32 B resolution). They do show transients that span all three reads of one death, or of 2-3 deaths in a row:
  - +192 or +416 B in about half the runs, and -32 B dips often;
  - under the heaviest census (probe 6), dips of -64 to -128 B at death 4 in 14 of 16 runs. Two of those reproduced the red exactly (r1_p6a_5 and r1_p6a_7: "32 B retained per supervised death").
  - T3a's list has the same shape: steady at 1303680 with one -224 B dip at death 4. The minimum of deaths 3-5 picks that dip: 224/4 = 56.
- **What the transient is:** not found at line level. At the outlier readings, the census was identical to a steady death in all of these:
  - every live task's await chain (function and bytecode offset at each level), and the type of every frame slot;
  - the IOQueue map, and `_tracked` (length 32, capacity 128);
  - every module object's attributes, including container lengths;
  - the twin's links, machine and network registries, and `_exc_context`.
  - That leaves sizes of objects inside frames (types matched, sizes were not compared), or stale words that `gc.collect()` scans conservatively: the C stack and frame stack slots above sp. This is my leading hypothesis and it is unproven. Analysers: an_probe.py, an_state.py, an_tw.py.
- **Verdict on the method:** yes, one transient sets the verdict. A dip in deaths 3-5 fails a healthy run. A dip in deaths 7-9 hides up to dip/4 B per death of real retention.
- **Fix (lane T, tests/test_digital_twin_sensortask_integration.py:603-604):** replace the slope with Theil–Sen, the median of the 21 pairwise slopes over deaths 3-9, keeping the 32 B bound. Copy: laneR/b_fix/test_fix.py.
  - Offline, over 101 recorded drift lists: the 49 unperturbed runs read at most 10.7 B, and T3a's list reads 0.
  - Adding a planted 64 B per death to the unperturbed runs reads at least 53.3 B.
  - Real runs: the fix is green 4/4 (r1_fix.sum). The fix plus `bytearray(16)` per death (64 B) is red 4/4 at "64 B retained", even with +416 and +192 transients in the list (r1_plant.sum).
  - Limits:
    - Two transients at deaths 8-9 (seen once, in probe 5) read 38 B.
    - Three mid-window transients plus the plant read 32.0, which is still red.
    - Repeated-median is worse: it misses that plant.
  - Not yet run at 32768 or under settrace; that is lane T's to run.

**Deviation:** I ran two probes, and the fix/plant pair, in one worktree at once, against CHECKLIST 12. 3 of the 68 probe runs logged this at boot: `CFGMGR_SYSTEM Error writing config tests/_tmp/dtsi_dev/1/config_SYSTEM.cfg - running unpersisted: [Errno 2] ENOENT`. The cause is the shared tests/_tmp scratch path; the 40 full-file runs, which never shared a tree, show it 0 times. In those 3 runs the deaths were still flat afterwards.

**Runs:** a rc1 (expected plant); rateA and rateB rc0; probes p1-p4 rc0; p5's first attempt rc1 (my probe's NameError), rerun rc0; p6a rc1 (the two reproduced reds); p6b rc0; fix rc0; plant rc1 (the bites).
