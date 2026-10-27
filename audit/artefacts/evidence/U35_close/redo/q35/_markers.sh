#!/bin/bash
# Read-only: per action, count git grep hits of a landing marker on a ref (outside audit/ and arduino/).
# Usage: _markers.sh <repo> <ref>
R=$1; REF=$2
m() {  # id pattern [pathspec]
  local id=$1 pat=$2; shift 2
  local out
  out=$(git -C "$R" grep -c -E -e "$pat" "$REF" -- "${@:-.}" ':!arduino' ':!audit' 2>/dev/null | sed "s|^$REF:||" | head -4 | tr '\n' ' ')
  printf '%-7s %-45.45s -> %s\n' "$id" "$pat" "${out:-NONE}"
}
m .06 'accepted trade-off' SPECIFICATION.md
m .06t 'def test_a_clean_transa' tests
m .10 'class DrivenTime' tests
m .11 "reproduced here" tests/test_asy_bmp3xx_driver.py
m .12a 'sleep\(0\)  # let the responder' tests
m .12b 'ready\.wait\(\)' tests/test_asy_ntp_client.py
m .13 'DrivenTime' tests/test_asy_neopixel_driver.py tests/test_asy_notification_service.py tests/test_notification_neopixel_integration.py
m .14 'fix_address_soon' tests
m .15a 'wait_for\(server_task, 5\)|wait_for\(first_reply_task, 5\)' tests
m .15b 'serve_once\(.*\) is True' tests
m .16 'sibling_inside_window' tests
m .17 'entry\[1\] != _BMP_ADDR' tests
m .18 '_ISOLATION_BOUND_S' tests
m .19a 'default_address' tests/_bus_hazard_catalog.py
m .19b '_RESERVED_RANGES' tests/test_bus_hazard_multi_device.py
m .20 'FRAM_SPI' tests/test_bus_hazard_multi_device.py
m .21 'general_call' tests_hardware/device_scripts
m .24 'heavy-file list names' scripts tests_scripts
m .25 '_MEM_SAMPLE_INTERVAL_MS *=' scripts
m .26 'st_size' scripts/_digital_twin_ci_suite.py
m .27 '^_SOAK_CYCLES *=|_MEM_TREND_TOLERANCE_SD_MULTIPLIER *=' scripts
m .29 'zero_think' scripts tests tests_scripts
m .30 'escaping_the_supervisor|never_fed|feeds_once_then_never' tests
m .31 'test-watchdog-fault|WDT_AT_FAULT' digital_twin scripts tests tests_scripts
m .33 'forty_days|days_of_uptime' tests
m .34 'dropped_one_second|never_skew_elapsed' tests
m .38 'run1_errcount|normal.boot' scripts/_digital_twin_ci_suite.py
m .39 '_normal_boot_log_failures' tests_scripts
m .40 'allowed_warnings' tests_hardware/bench/test_end_to_end_timing.py
m .41 'branch no input can reach' SPECIFICATION.md
m .42a 'stand-in domain error|ArithmeticError' tests/test_math_helpers.py
m .42b 'errno=98|ID check failed' src
m .43 'newer snapshot was staged' src
m .44a 'if self.poly is None' src/asy_crc_checks.py
m .44b 'except ValueError' src/asy_crc_checks.py
m .45 'logger: .*PrintLogHistory' src/asy_base_classes.py
m .46 'future caller' js
m .47 'narrow the Optional|narrows? the type' src/asy_uart_comm.py src/asy_fram_manager.py src/asy_uart_link_driver.py
m .48 'cancel_at_each_await' tests
m .49 '"exception"' tests_hardware/twin_record.json
m .55a 'errno=82|_RaisingPackInto' src tests
m .56 'estimated' SPECIFICATION.md
m .57 'Test campaign' BACKLOG.md
