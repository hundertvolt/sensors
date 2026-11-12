"""Pins every rp2 constant the twin models to the value its cited v1.29.0 source line holds; a pin move that changes one
fails here and names the line to re-read (CLAUDE.md's re-check practice)."""

import sys

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import machine
import microtest
import network
from machine import SPI, UART, Pin
from neopixel import NeoPixel

microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)


def test_pin_modes() -> None:
    assert Pin.IN == 0  # ports/rp2/machine_pin.h:34 MACHINE_PIN_MODE_IN
    assert Pin.OUT == 1  # machine_pin.h:35
    assert Pin.OPEN_DRAIN == 2  # machine_pin.h:36
    assert Pin.ALT == 3  # machine_pin.h:37


def test_pin_pulls_alternate_function_and_edges() -> None:
    assert Pin.PULL_UP == 1  # ports/rp2/machine_pin.c:44 GPIO_PULL_UP
    assert Pin.PULL_DOWN == 2  # machine_pin.c:45 GPIO_PULL_DOWN
    assert Pin.ALT_I2C == 3  # machine_pin.c:513 GPIO_FUNC_I2C, pico-sdk hardware/structs/io_bank0.h:34
    assert Pin.IRQ_FALLING == 0x04  # machine_pin.c:508, pico-sdk hardware/gpio.h:193 GPIO_IRQ_EDGE_FALL
    assert Pin.IRQ_RISING == 0x08  # machine_pin.c:507, gpio.h:194 GPIO_IRQ_EDGE_RISE


def test_spi_bit_order_and_dma_threshold() -> None:
    assert SPI.MSB == 1  # pico-sdk hardware/spi.h:186 SPI_MSB_FIRST
    assert SPI.LSB == 0  # spi.h:185 SPI_LSB_FIRST
    assert machine._SPI_DMA_MIN_SIZE == 32  # ports/rp2/machine_spi.c:267 dma_min_size_threshold


def test_uart_stream_and_buffer_bounds() -> None:
    assert UART._MP_STREAM_POLL == 3  # py/stream.h:39
    assert UART._DEFAULT_BUFFER_SIZE == 256  # ports/rp2/machine_uart.c:67 DEFAULT_BUFFER_SIZE
    assert UART._MIN_BUFFER_SIZE == 32  # machine_uart.c:68
    assert UART._MAX_BUFFER_SIZE == 32766  # machine_uart.c:69
    assert UART._UART_INVERT_MASK == 3  # machine_uart.c:82-84 UART_INVERT_TX | UART_INVERT_RX
    assert UART._DEFAULT_BAUDRATE == 115200  # machine_uart.c:39 DEFAULT_UART_BAUDRATE


def test_watchdog_timer_and_reset_causes() -> None:
    assert machine._WDT_TIMEOUT_MAX_MS == 8388  # ports/rp2/machine_wdt.c:38 WDT_TIMEOUT_MAX (RP2040)
    assert machine._ALARM_POOL_SIZE == 16  # pico-sdk pico/time.h:362 PICO_TIME_DEFAULT_ALARM_POOL_MAX_TIMERS
    assert machine.PWRON_RESET == 1  # ports/rp2/modmachine.c:57 RP2_RESET_PWRON
    assert machine.WDT_RESET == 3  # modmachine.c:58 RP2_RESET_WDT


def test_mem_backup_region_sizes() -> None:
    assert len(machine.mem_backup(0)) == 4  # ports/rp2/machine_mem_backup.c:39 scratch[0..3]
    assert len(machine.mem_backup(1)) == 3  # machine_mem_backup.c:40 scratch[5..7]


def test_neopixel_colour_order() -> None:
    assert NeoPixel.ORDER == (1, 0, 2, 3)  # micropython-lib micropython/drivers/led/neopixel/neopixel.py:9


def test_network_link_codes_and_power_on_seeds() -> None:
    assert network.STAT_IDLE == 0  # lib/cyw43-driver/src/cyw43.h:98 CYW43_LINK_DOWN
    assert network.STAT_CONNECTING == 1  # cyw43.h:99 CYW43_LINK_JOIN
    assert network.STAT_GOT_IP == 3  # cyw43.h:101 CYW43_LINK_UP
    assert network.STAT_CONNECT_FAIL == -1  # cyw43.h:102 CYW43_LINK_FAIL
    assert network.STAT_NO_AP_FOUND == -2  # cyw43.h:103 CYW43_LINK_NONET
    assert network.STAT_WRONG_PASSWORD == -3  # cyw43.h:104 CYW43_LINK_BADAUTH
    assert network.country() == "XX"  # extmod/modnetwork.c:71
    assert network.hostname() == "PicoW"  # ports/rp2/boards/RPI_PICO_W/mpconfigboard.h:8


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
