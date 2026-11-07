#!/bin/bash
cd /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u17h
OUT=../u17h/exp
for variant in hz_noclock tests/test_uart_comm_hazard; do
  f=$variant.py; [ "$variant" = hz_noclock ] && f=../u17h/exp/hz_noclock.py
  tag=$(basename $variant)
  for sub in break_like corrupted_byte_stream dropped_byte two_fragments lost_final_ack peer_initiating_mid_transaction_is_detected receive_overrun second_call size_mismatch_against truncated_frame duplicated_bytes injected_noise one_sided_silence long_run_of_transactions crc_appears_on_the_wire probed_payload_offset overrun_plus_duplication; do
    TZ=UTC MICROPYPATH="build/generated_src:src:tests:frozen_modules:.frozen" nice -n 19 timeout 1200 /root/pico-toolchain/micropython/ports/unix/build-standard/micropython -X heapsize=16M $OUT/exposure_sweep_h.py $f 300 100000 -15 $sub 2>&1 | grep -E "^(ok|FLIP|BASEFAIL|SKIPLONG)" >> $OUT/exposure_$tag.log
  done
done
echo done
