#ifndef ASYNC_UART_h
#define ASYNC_UART_h

#include "Arduino.h"
#include "CRC_Check.h"

#define ASNYC_UART_NO_TIMEOUT 0

#define ASYNC_UART_OK 0
#define ASYNC_UART_IDLE 1
#define ASYNC_UART_WAITING 2
#define ASYNC_UART_TIMEOUT 3
#define ASYNC_UART_BUSY 4
#define ASYNC_UART_CRC_ERROR 5

#define ASYNC_UART_READ_IDLE 0
#define ASYNC_UART_READ_READY 1
#define ASYNC_UART_READ_COMPLETE_READY 2
#define ASYNC_UART_READ_COMPLETE_STARTED 3

#define ASYNC_UART_WRITE_IDLE 0
#define ASYNC_UART_WRITE_ACTIVE 1

class Async_UART
{
  public:
    Async_UART();
    void init(Uart *uart, long baudrate, CRC_Check *crc);
    bool start_reading(char *buffer, uint16_t max_size, unsigned long timeout_ms);
    bool start_reading_until_complete(char *buffer, uint16_t nbytes, unsigned long start_timeout_ms, unsigned long timeout_ms);
    bool cancel_read_timeout();
    bool start_writing(char *buffer, uint16_t nbytes);
    uint8_t check_reading();
    uint8_t check_reading_until_complete();
    uint8_t check_writing();
  private:
    bool _cancel_reading;
    uint8_t _read_status;
    uint8_t _write_status;
    uint16_t _read_nbytes;
    uint16_t _write_nbytes;
    uint16_t _read_addr;
    uint16_t _write_addr;
    unsigned long _read_time;
    unsigned long _start_timeout;
    unsigned long _read_timeout;
    char* _read_buffer;
    char* _write_buffer;
    Uart* _uart;
    CRC_Check* _crc;
};

#endif
