| `bus.address-collision` | two bmp3xx on i2c0, both address = 0x76 | bmp3xx_b | address |
| `bus.boot-clear-budget` | i2c0 and i2c1 both at timeout = 200000, asy_i2c_driver's _CLEAR_PULSES = const(18) | - | timeout |
| `bus.field-missing` | [bus.i2c0] without scl_pin | - | scl_pin |
| `bus.field-type` | [bus.i2c0].timeout = "200ms" | - | timeout |
| `bus.field-type` | uart pair with [bus.uart0].rxbuf = "512" | - | rxbuf |
| `bus.field-unknown` | [bus.i2c0].speed = 1 | - | speed |
| `bus.fixed-address-collision` | a second scd30 (name_ext = "b", irq_pin = 9) on i2c0 beside the first | scd30_b | - |
| `bus.i2c-frequency-range` | [bus.i2c0].frequency = 1000001 | - | frequency |
| `bus.i2c-timeout-max` | [bus.i2c0].timeout = 10000000 | - | timeout |
| `bus.i2c-timeout-range` | [bus.i2c0].timeout = 0 | - | timeout |
| `bus.not-a-table` | [bus] spi0 = 5 (a bus that is no table) | - | spi0 |
| `bus.uart-baudrate-range` | uart pair with [bus.uart0].baudrate = 7812501 | - | baudrate |
| `bus.uart-poll-idle-range` | uart pair with [bus.uart0].poll_idle_ms = 1 (below poll_wait_ms 2) | uart_link_init | poll_idle_ms |
| `bus.uart-poll-wait-range` | uart pair with [bus.uart0].poll_wait_ms = 0 | uart_link_init | poll_wait_ms |
| `bus.uart-rx-ring` | uart pair with [bus.uart0].rx_ring = 64 (below the 128-byte floor) | uart_link_init | rx_ring |
| `bus.uart-rx-ring` | uart pair with [bus.uart0].rx_ring = 1 | uart_link_init | rx_ring |
| `bus.uart-rx-ring` | uart pair with [bus.uart0].rx_ring = 384 | uart_link_init | rx_ring |
| `bus.uart-rxbuf-floor` | uart pair with [bus.uart0].rxbuf = 79 | uart_link_init | rxbuf |
| `bus.uart-rxbuf-range` | uart pair with [bus.uart0].rxbuf = 32767 | - | rxbuf |
| `bus.uart-shared` | uart pair with both links on bus = "uart0" | uart_link_resp | bus |
| `bus.uart-timeout-floor` | uart pair with [bus.uart1].poll_idle_ms = 976 | uart_link_resp | poll_idle_ms |
| `bus.uart-txbuf-range` | uart pair with [bus.uart0].txbuf = 31 | - | txbuf |
| `bus.unknown-id` | [bus.i2c7] (an id the Pico W has no bus for) | - | i2c7 |
| `bus.unused` | an extra [bus.i2c1] no instance names | - | i2c1 |
| `device.backlog-above-ceiling` | [device].max_connections = 4, backlog = 6 | - | backlog |
| `device.backlog-below-ceiling` | [device].max_connections = 4, backlog = 3 | - | backlog |
| `device.conn-fail-to-hotspot-range` | [device].conn_fail_to_hotspot = 0 | - | conn_fail_to_hotspot |
| `device.field-missing` | [device] without hostname | - | hostname |
| `device.field-type` | [device].name = 5 | - | name |
| `device.field-unknown` | [device].colour = 1 | - | colour |
| `device.hostname-convention` | [device].hostname = "SensorStationOther" | - | hostname |
| `device.hostname-label` | [device].name = "Te_st", hostname = "SensorStationTe_st" | - | hostname |
| `device.hostname-length` | [device].name = 60 x "T", hostname = "SensorStation" + 60 x "T" | - | hostname |
| `device.hotspot-password-length` | [device].hotspot_password = "short" | - | hotspot_password |
| `device.hotspot-time-min-range` | [device].hotspot_time_min = 35792 | - | hotspot_time_min |
| `device.max-connections-lwip` | [device].max_connections = 64 | - | max_connections |
| `device.max-connections-range` | [device].max_connections = 0 | - | max_connections |
| `device.ntp-retry-below-tick` | [device].ntp_retry_s = 1 | - | ntp_retry_s |
| `device.ntp-retry-max-below-retry` | [device].ntp_retry_s = 120, ntp_retry_max_s = 60 | - | ntp_retry_max_s |
| `device.ntp-retry-max-range` | [device].ntp_retry_max_s = 536870912 | - | ntp_retry_max_s |
| `device.table-missing` | no [device] table | - | - |
| `device.wiring-field-missing` | no [device.wiring].led_target, asy_wifi_service.py's led_target tag made required | - | led_target |
| `device.wiring-field-unknown` | [device.wiring].bogus_target = "fram" | - | bogus_target |
| `device.wiring-no-tag` | [device.wiring].led_target with asy_wifi_service.py's @wiring led_target tag removed | - | led_target |
| `device.wiring-not-table` | [device] wiring = "neopixel" (a string, not a table) | - | wiring |
| `gpio.claimed-twice` | neopixel with pin = 8 (scd30's irq_pin) | neopixel | pin |
| `gpio.no-function` | uart pair with [bus.uart0].tx_pin = 18 (UART0 CTS) | bus.uart0 | tx_pin |
| `gpio.not-usable` | scd30 with irq_pin = 23 | scd30 | irq_pin |
| `gpio.type` | scd30 with irq_pin = "8" | scd30 | irq_pin |
| `gpio.wrong-bus` | [bus.i2c0].scl_pin = 11, sda_pin = 10 (I2C1's pins) | bus.i2c0 | scl_pin |
| `gpio.wrong-role` | [bus.i2c0].scl_pin = 12, sda_pin = 13 (transposed) | bus.i2c0 | scl_pin |
| `instance.address-not-selectable` | scd30 with address = 0x61 | scd30 | address |
| `instance.bus-kind` | scd30 with bus = "spi0" | scd30 | bus |
| `instance.bus-undeclared` | scd30 with bus = "i2c1" (no [bus.i2c1]) | scd30 | bus |
| `instance.field-missing` | scd30 without irq_pin | scd30 | irq_pin |
| `instance.field-not-finite` | scd30 with gain = nan, against a synthetic # @limits gain 0.5..2.5 | scd30 | gain |
| `instance.field-not-in-set` | fram with max_size = 4096 | fram | max_size |
| `instance.field-out-of-range` | scd30 with trigger_s = 1801 | scd30 | trigger_s |
| `instance.field-type` | scd30 with bus = 0 | scd30 | bus |
| `instance.field-unknown` | scd30 with colour = 1 | scd30 | colour |
| `instance.irq-pull-up-type` | scd30 with irq_pull_up = 1 | scd30 | irq_pull_up |
| `instance.name-ext-missing` | scd30 without name_ext | scd30 | name_ext |
| `instance.name-ext-singleton` | notification with name_ext = "x" | notification_x | name_ext |
| `instance.no-buildspec-row` | an [[instance]] driver = "bogus2" whose asy_bogus2_driver.py resolves but has no buildspec row | bogus2 | - |
| `instance.requires-without-bus` | asy_neopixel_driver.py carrying # @requires bus.timeout>=1 | neopixel | - |
| `instance.uart-baud-mismatch` | uart pair with [bus.uart1].baudrate = 57600 | uart_link_resp | baudrate |
| `instance.uart-crc-mismatch` | uart pair with only the initiator's crc = "crc16" | uart_link_resp | crc |
| `instance.uart-crc-mode` | uart pair with the initiator's crc = "crc32" | uart_link_init | crc |
| `instance.uart-link-pair` | uart pair with both links role = "initiator" | - | - |
| `instance.uart-role` | uart pair with the responder's role = "peer" | uart_link_resp | role |
| `instance.uart-timeout-max` | uart pair, asy_uart_comm's _DEFAULT_TIMEOUT_MS = const(100000000) | uart_link_init | - |
| `instance.uart-transfer-cap` | uart pair with the initiator's max_transfer_bytes = 47 | uart_link_init | max_transfer_bytes |
| `names.logger-collision` | a bmp3xx instance whose asy_bmp3xx_driver.py says _NAME = const("NTP") | bmp3xx | - |
| `source.field-unknown` | sgp40 wiring.temperature_source = { source = "scd30", field = "Tmp" } | sgp40 | temperature_source |
| `src.const-missing` | asy_ntp_client.py's _NTP_CHECK_INTERV renamed, with [device].ntp_retry_s = 60 | - | _NTP_CHECK_INTERV |
| `src.default-missing` | uart pair stating no rx_ring, asy_uart_driver.UART.__init__'s rx_ring default a name, not a literal | - | rx_ring |
| `src.schema-missing` | asy_wifi_service.py's HotspotPW schema with max bound None | - | HotspotPW |
| `src.unreadable` | src/ without asy_wifi_service.py | - | HotspotPW |
| `wiring.default-attr-missing` | notification wiring.signal_sink = { default = true }, _DefaultSignalSink's request_signal renamed | notification | signal_sink |
| `wiring.default-class-missing` | sgp40 wiring.fram_target = { default = true } | sgp40 | fram_target |
| `wiring.default-key-missing` | sgp40 wiring.temperature_source = { default = true }, _DefaultTemperatureSource.__init__(self, *, temperature: float) | sgp40 | temperature_source |
| `wiring.default-key-unknown` | sgp40 wiring.temperature_source = { default = true, temperature = 20, bogus = 1 } | sgp40 | temperature_source |
| `wiring.field-missing` | notification without wiring.signal_sink | notification | signal_sink |
| `wiring.field-unknown` | scd30 wiring.led_target = "neopixel" | scd30 | led_target |
| `wiring.source-shape` | sgp40 wiring.temperature_source = { source = "scd30" } (no field) | sgp40 | temperature_source |
| `wiring.source-shape` | sgp40 wiring.temperature_source = { source = "scd30", field = 1 } | sgp40 | temperature_source |
| `wiring.source-unresolved` | sgp40 wiring.temperature_source = { source = "bme", field = "Temp" } | sgp40 | temperature_source |
| `wiring.target-class` | notification wiring.signal_sink = "fram" | notification | signal_sink |
| `wiring.target-type` | [device.wiring].led_target = 5 | - | led_target |
| `wiring.target-type` | scd30 wiring.fram_target = 5 | scd30 | fram_target |
| `wiring.target-unresolved` | sgp40 wiring.fram_target = "nothing" | sgp40 | fram_target |
| `wiring.warn-outside-notification` | scd30 wiring.warn_co2 = { source = "scd30", field = "CO2" } | scd30 | warn_co2 |
| `wiring.warn-unknown` | notification wiring.warn_radon = { source = "scd30", field = "CO2" } | notification | warn_radon |
