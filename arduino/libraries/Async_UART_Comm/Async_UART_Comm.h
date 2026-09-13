#ifndef ASYNC_UART_COMM_h
#define ASYNC_UART_COMM_h

#include "Arduino.h"
#include "CRC_Check.h"
#include "Async_UART.h"

// command byte definitions
#define ASYNC_UART_COMM_CMD_ACK 0x01
#define ASYNC_UART_COMM_CMD_GET 0x02
#define ASYNC_UART_COMM_CMD_SET 0x04

// message format definitions
#define ASYNC_UART_COMM_NUM_MSG_FIELDS 5
#define ASYNC_UART_COMM_MSG_UID 0
#define ASYNC_UART_COMM_MSG_CMD 1
#define ASYNC_UART_COMM_MSG_SIZE 2
#define ASYNC_UART_COMM_MSG_CHUNKS 3
#define ASYNC_UART_COMM_MSG_CUR_CHUNK 4
#define ASYNC_UART_COMM_MSG_PAYLOAD 5

// internal states of Async_UART_Comm::_check_comm()
#define ASYNC_UART_COMM_STATE_IDLE 0
#define ASYNC_UART_COMM_STATE_WRITE_STARTING 1
#define ASYNC_UART_COMM_STATE_WRITE_WRITING 2
#define ASYNC_UART_COMM_STATE_WRITE_READING 3
#define ASYNC_UART_COMM_STATE_READ_READING 4
#define ASYNC_UART_COMM_STATE_READ_READING_ACK 5
#define ASYNC_UART_COMM_STATE_READ_WRITING 6
#define ASYNC_UART_COMM_STATE_CLEARING 7

// internal states of Async_UART_Comm::loop_comm()
#define ASYNC_UART_COMM_MODE_IDLE 0
#define ASYNC_UART_COMM_MODE_START_GET 1
#define ASYNC_UART_COMM_MODE_READ_GET 2
#define ASYNC_UART_COMM_MODE_WRITE_SET 3
#define ASYNC_UART_COMM_MODE_LISTEN 4
#define ASYNC_UART_COMM_MODE_CLEARING 5

// internal return values of Async_UART_Comm::_check_comm()
#define ASYNC_UART_COMM_CHECK_IDLE 0
#define ASYNC_UART_COMM_CHECK_OK 1
#define ASYNC_UART_COMM_CHECK_WRITING 2
#define ASYNC_UART_COMM_CHECK_READING 3
#define ASYNC_UART_COMM_CHECK_READING_DONE 4
#define ASYNC_UART_COMM_CHECK_INVALID 5
#define ASYNC_UART_COMM_CHECK_CLEARING 6
#define ASYNC_UART_COMM_CHECK_STATE_ERROR 7

// **** public return values of Async_UART_Comm::loop_comm() ****
#define ASYNC_UART_COMM_IDLE 0
#define ASYNC_UART_COMM_OK 1
#define ASYNC_UART_COMM_SETTING 2
#define ASYNC_UART_COMM_GETTING 3
#define ASYNC_UART_COMM_LISTENING 4
#define ASYNC_UART_COMM_CLEARING 5

typedef bool (*getCB)(char**, uint16_t*, char);
// getCallback(char **src, uint16_t *size, char getID);
// **src: <to be filled when called> source buffer for transmitting. May be NULL if no payload to be sent.
// *size <to be filled when called> payload size to be sent. Forced to zero if **src is set to NULL
// getID: <filled with received setID> info for the called function which ID was demanded
// if callback returns false, the message is denied (buffers cleared)
// Will internally work like uart_set and use the parameters given by callback

typedef bool (*setCB)(char**, uint16_t*, uint16_t**, char);
// setCallback(char** dest, uint16_t* max_exp_size, uint16_t** received_size, char setID);
// *dest: <to be filled when called> destination buffer for receiving. May be set to NULL if no payload expected; this forces exp_size to zero.
// *max_size: <to be filled when called> expected size of payload (must fit into destination buffer)
// setID: <filled with received setID> info for the called function which ID was demanded
// if callback returns false, the message is denied (buffers cleared)
// Will internally work like uart_get and use the parameters given by callback

class Async_UART_Comm
{
  public:
    Async_UART_Comm();
    bool init(Uart* uart, long baudrate, uint8_t payload_size, unsigned long timeout, Serial_* debugOut);
    bool uart_listen(getCB getCallback, setCB setCallback);

    bool uart_set(char *src, uint16_t size, char setID);
    // *src is optional (may be NULL); size is then forced to zero

    bool uart_get(char *dest, uint16_t max_exp_size, uint16_t *received_size, char getID);
    // *dest is optional (may be NULL); max_exp_size is then forced to zero
    // *received_size is optional (may be NULL); max_exp_size is then expected size

    void clear_buffers();
    void set_debug(bool mode);
    uint8_t loop_comm();

  private:
    Async_UART _asy_uart;
    CRC_16 _crc16;

    Uart* _uart;
    Serial_* _debug;

    unsigned long _timeout;
    uint8_t _payload_size;
    uint8_t _uid;
    uint8_t _comm_mode;
    uint8_t _comm_state;
    uint8_t _exp_chunk;
    uint8_t _cur_chunk;
    uint8_t _num_chunks;
    uint16_t _set_size;
    uint16_t _get_size;
    uint8_t _get_id;
    uint16_t _get_addr;
    bool _clear;
    bool _enable_read_ack;
    bool _enable_writing;
    bool _write_timer_running;
    bool _debug_active;
    unsigned long _enable_write_time;
    uint16_t* _get_received_size;
    char* _get_dest;
    char* _set_src;
    char* _read_buffer;
    char* _write_buffer;
    getCB _get_callback;
    setCB _set_callback;
    void _inc_uid();
    bool _check_msg(uint8_t exp_cmd, uint8_t exp_chunk, uint8_t* msg_size, bool* last_chunk);
    uint8_t _check_comm();
    bool _write_with_ack();
    bool _read_with_ack(bool wait, bool auto_ack);
    bool _enable_ack();
    void _build_msg(uint8_t uid, uint8_t cmd, uint8_t chunks, uint8_t cur_chunk, uint8_t payload_size, char* payload);
    void _printDebug(const char* msg);
};

#endif
