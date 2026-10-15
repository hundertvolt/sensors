# U17 close evidence

Each folder holds a lane's working logs (paths inside name the scratch worktrees they ran in; files over 100 KB gzipped).

| folder | what it shows | cited by |
|---|---|---|
| `lane_c/` | the comm module: tests seen failing before C1 and the body (`before_c1.txt`, `probe_before.txt`, `b2_before.txt`), the COBS wrong-length fix seen failing (`cobs_seen_failing.txt`), the planted-stall sweep on the wall clock and on the poll-round clock (`sweep_wall*.txt`, `sweep_clock.txt`), the final runs at both GC stages, and the sweep tools | SF-U17-01, -07..-12, -16 |
| `lane_r/` | the driver and codec: R1 and phase-2 tests seen failing, the final runs at both stages, the lane notes | SF-U17-01, -05, -06, -07 |
| `lane_p/` | the piece buffer and the I2C clock tests: probes, the planted 60 ms stall failing the wall-clock forms | SF-U17-02, -17 |
| `lane_h/` | the hazard tier: wall times before and after at -1, 32768 and settrace (`times.txt`), the 300 ms stall exposure sweeps (`exp/`) | SF-U17-01, -03, the A-22 review row |
| `lane_l/` | the link exerciser: the copy-out and behaviour tests seen failing, the OF-33 wall-clock flips at stall point 2, the final runs | SF-U17-01, -13, -14 |
| `lane_t/` | the twin link: the runner's KeyError and the base body's missed diagnostic seen failing, final runs at both stages on the overlay | SF-U17-07, OF-74 |
| `retention_windows/` | the three retention tests judged one heap sample: probes, the in-file sampling, the plants | SF-U17-19 |
| `gate_final/` | the close gates | the commit's local-gate paragraph |
| `lane_u/` | the changelog check: stubbed negatives, the pre-edit changelog's 100 findings, the two scan fixes seen failing | SF-U17-18 |
