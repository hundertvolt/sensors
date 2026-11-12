L_flash: per-module bytecode size, written by the lead (2026-10-28T07:35)
Method: each src/*.py at 25caf528 and at 497b3eda compiled by the pinned mpy-cross (v1.29.0, mpy v6.3), file bytes.
Renamed modules are mapped to their new names. Frozen bytecode in the image is laid out differently, but in proportion.
Context: the dev image of 2026-10-26 holds about 1,158 KB of the 1,200 KB firmware region, about 43 KB free.
- src/ total: 164,566 B before the audit, 211,648 B now: +47,082 B (+29 %), more than the remaining headroom.
- Largest growth: asy_system_service +5,614; asy_base_classes +5,297; asy_webserver_service +4,509; asy_uart_driver
  +3,980; asy_scd30_driver +3,674; asy_print_log +2,689; asy_config_manager +2,363; asy_ntp_client +2,191;
  asy_sgp40_driver +2,070; asy_uart_link_driver +2,016; asy_fram_manager +1,982; asy_i2c_driver +1,977;
  asy_uart_comm +1,756; asy_wifi_service +1,642.
- Smaller now: asy_neopixel_driver -275, asy_notification_service -309, asy_udp_socket -342.
- The generated device modules at the head are 6.8-7.8 KB per device. Their pre-audit size is not measured: it would
  take running buildgen at 25caf528. Scan D compares their emitters.
Full table: S/u35/lead/flash/ (mpy_sizes.sh, out/).
