#include "Arduino.h"
#include "Async_UART_Comm.h"

Async_UART_Comm::Async_UART_Comm()
{
}

bool Async_UART_Comm::init(Uart* uart, long baudrate, uint8_t payload_size, unsigned long timeout, Serial_* debugOut) {
  this->_read_buffer = (char *)malloc((ASYNC_UART_COMM_NUM_MSG_FIELDS + payload_size + CRC_CHECK_CRC_16_SIZE) * sizeof(char));
  this->_write_buffer = (char *)malloc((ASYNC_UART_COMM_NUM_MSG_FIELDS + payload_size + CRC_CHECK_CRC_16_SIZE) * sizeof(char));
  if ( (this->_read_buffer == NULL) || (this->_write_buffer == NULL) ) {
    return false;
  }
  this->_payload_size = payload_size;
  this->_timeout = timeout;
  this->_asy_uart.init(uart, baudrate, &this->_crc16);
  this->_uid = 0;
  this->_comm_mode = ASYNC_UART_COMM_MODE_IDLE;
  this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
  this->_clear = false;
  this->_debug = debugOut;
  this->_enable_read_ack = true;
  this->_enable_writing = true;
  this->_write_timer_running = false;
  this->_debug_active = false;
  return true;
}

bool Async_UART_Comm::uart_listen(getCB getCallback, setCB setCallback) {
  if (this->_comm_mode == ASYNC_UART_COMM_MODE_IDLE) {
    this->_get_callback = getCallback;
    this->_set_callback = setCallback;
    this->_enable_writing = true;        // skip timer onĺy in listen mode.
    this->_write_timer_running = false;  // if peer requests something, it's definitely up again.
    if (_read_with_ack(true, true)) {
      _printDebug("Uart_Comm_uart_listen: LISTEN waiting for first message");
      this->_comm_mode = ASYNC_UART_COMM_MODE_LISTEN;
      return true;
    }
  }
  _printDebug("Uart_Comm_uart_listen: Busy, LISTEN command not started!");
  return false;
}

bool Async_UART_Comm::uart_set(char *src, uint16_t size, char setID) {
  if (this->_comm_mode == ASYNC_UART_COMM_MODE_IDLE) {
    this->_set_src = src;
    this->_set_size = (this->_set_src == NULL) ? 0 : size;
    this->_cur_chunk = 1; // first chunk = set command
    uint16_t num_chunks = (this->_set_size / this->_payload_size) + 1; // integer number of chunks; +1 --> first payload = setID
    if ( ((this->_set_size % this->_payload_size) > 0) ||   // add one chunk if remainder > 0
         (num_chunks < 2) ) {                               // add one chunk (empty, just for ACK feedback) if message without payload
      num_chunks += 1;
    }
    if (num_chunks > 0xFF) {  // too large for num chunks field
      _printDebug("Uart_Comm_uart_set: SET command not started, payload too large!");
      return false;
    }
    this->_num_chunks = (uint8_t)num_chunks;
    _inc_uid();
    _build_msg(this->_uid, ASYNC_UART_COMM_CMD_SET, this->_num_chunks, this->_cur_chunk, 1, &setID);
    if (_write_with_ack()) {
      _printDebug("Uart_Comm_uart_set: Start SET command");
      this->_comm_mode = ASYNC_UART_COMM_MODE_WRITE_SET;
      return true;
    }
  }
  _printDebug("Uart_Comm_uart_set: Busy, SET command not started!");
  return false;
}

bool Async_UART_Comm::uart_get(char *dest, uint16_t max_exp_size, uint16_t *received_size, char getID) {
  if (this->_comm_mode == ASYNC_UART_COMM_MODE_IDLE) {
    this->_get_dest = dest;
    this->_get_size = (this->_get_dest == NULL) ? 0 : max_exp_size;
    this->_get_id = getID;
    this->_get_received_size = received_size;
    if (this->_get_received_size != NULL) {
      *this->_get_received_size = 0;
    }
    _inc_uid();
    _build_msg(this->_uid, ASYNC_UART_COMM_CMD_GET, 1, 1, 1, &getID);
    if (_write_with_ack()) {
      _printDebug("Uart_Comm_uart_get: Start GET command");
      this->_comm_mode = ASYNC_UART_COMM_MODE_START_GET;
      return true;
    }
  }
  _printDebug("Uart_Comm_uart_get: Busy, GET command not started!");
  return false;
}

void Async_UART_Comm::clear_buffers() {
  _printDebug("Uart_Comm_clear_buffers: Clearing input buffers!");
  this->_clear = true;  // set flag for clearing
}

void Async_UART_Comm::set_debug(bool mode) {
  this->_debug_active = mode;
}

uint8_t Async_UART_Comm::loop_comm() {
  uint8_t comm_status = _check_comm();
  switch (this->_comm_mode) {
    case ASYNC_UART_COMM_MODE_IDLE:
      switch (comm_status) {                // IDLE expected, CLEARING may occur, everything else is an error
        case ASYNC_UART_COMM_CHECK_IDLE:
          return ASYNC_UART_COMM_IDLE;

        case ASYNC_UART_COMM_CHECK_CLEARING:
          this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
          _printDebug("Uart_Comm_loop_comm: Forced into Clearing mode!");
          return ASYNC_UART_COMM_CLEARING;

        case ASYNC_UART_COMM_CHECK_WRITING:
        case ASYNC_UART_COMM_CHECK_READING:
        case ASYNC_UART_COMM_CHECK_READING_DONE:
        case ASYNC_UART_COMM_CHECK_OK:
        case ASYNC_UART_COMM_CHECK_INVALID:
        case ASYNC_UART_COMM_CHECK_STATE_ERROR:
        default:
          this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
          _printDebug("Uart_Comm_loop_comm: IDLE mode error!");
          clear_buffers();
          return ASYNC_UART_COMM_CLEARING;
      }

    case ASYNC_UART_COMM_MODE_START_GET:
      switch (comm_status) {
        case ASYNC_UART_COMM_CHECK_WRITING:
        case ASYNC_UART_COMM_CHECK_READING:
        case ASYNC_UART_COMM_CHECK_READING_DONE:
          return ASYNC_UART_COMM_GETTING;

        case ASYNC_UART_COMM_CHECK_OK:
          this->_exp_chunk = 1;
          this->_get_addr = 0;
          _printDebug("Uart_Comm_loop_comm: GET command issued successfully");
          if (_read_with_ack(false, false)) {  // ACK is issued whenever ASYNC_UART_COMM_MODE_READ_GET is okay
            this->_comm_mode = ASYNC_UART_COMM_MODE_READ_GET;
            _printDebug("Uart_Comm_loop_comm: GET waiting for first response");
            return ASYNC_UART_COMM_GETTING;
          }
          this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
          _printDebug("Uart_Comm_loop_comm: Busy, GET not waiting for response!");
          clear_buffers();
          return ASYNC_UART_COMM_CLEARING;

        case ASYNC_UART_COMM_CHECK_CLEARING:
          this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
          _printDebug("Uart_Comm_loop_comm: Forced into Clearing mode!");
          return ASYNC_UART_COMM_CLEARING;

        case ASYNC_UART_COMM_CHECK_IDLE:
        case ASYNC_UART_COMM_CHECK_INVALID:
        case ASYNC_UART_COMM_CHECK_STATE_ERROR:
        default:
          this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
          _printDebug("Uart_Comm_loop_comm: GET command error!");
          clear_buffers();
          return ASYNC_UART_COMM_CLEARING;
      }

    case ASYNC_UART_COMM_MODE_READ_GET:
      switch (comm_status) {
        case ASYNC_UART_COMM_CHECK_WRITING:
        case ASYNC_UART_COMM_CHECK_READING:
          return ASYNC_UART_COMM_GETTING;

        case ASYNC_UART_COMM_CHECK_READING_DONE:  // reading done, ACK to be enabled
          uint8_t msg_size;
          uint16_t msg_addr;
          bool last_chunk;
          if (_check_msg(ASYNC_UART_COMM_CMD_SET, this->_exp_chunk, &msg_size, &last_chunk)) {  // expect SET as reply to GET
            if (this->_exp_chunk == 1) { // first message always contains getID as payload
              if ((uint8_t)this->_read_buffer[ASYNC_UART_COMM_MSG_PAYLOAD] != this->_get_id) {
                this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
                _printDebug("Uart_Comm_loop_comm: GET getID to setID mismatch!");
                clear_buffers();
                return ASYNC_UART_COMM_CLEARING;
              }
            } else if (msg_size == 0) {                  // received empty message
              if (this->_get_received_size == NULL) {    // fixed expected message size
                if (this->_get_size != 0) {              // expected size not zero --> error
                  this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
                  _printDebug("Uart_Comm_loop_comm: GET expected message with payload but got empty!");
                  clear_buffers();
                  return ASYNC_UART_COMM_CLEARING;
                }  // here, message size and fixed expected size are both 0 --> okay
              } else {  // this->_get_received_size != NULL -> variable message size
                *this->_get_received_size = 0;
              }   // here, message size is 0 and message size is variable --> okay
              _printDebug("Uart_Comm_loop_comm: sending ACK for message with no payload");
              this->_exp_chunk = 0;  // unique marker for message done
              _enable_ack();  // Last message was okay
              return ASYNC_UART_COMM_GETTING;
            } else {  // regular nonzero payload message
              msg_addr = this->_get_addr + msg_size;
              if ( (msg_addr > this->_get_size) || (&this->_get_dest == NULL) ) {  // message too large for buffer
                this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
                _printDebug("Uart_Comm_loop_comm: GET size too large for dest buffer!");
                clear_buffers();
                return ASYNC_UART_COMM_CLEARING;
              }
              memcpy(&this->_get_dest[this->_get_addr],
                     &this->_read_buffer[ASYNC_UART_COMM_MSG_PAYLOAD],
                     msg_size * sizeof(char)); // copy payload chunk into dest buffer
              this->_get_addr = msg_addr;  // store address to continue with next chunk
            }
            if (last_chunk) {
              if (this->_get_received_size == NULL) {  // handle as expected fixed size
                if (this->_get_size != this->_get_addr) {
                  this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
                  _printDebug("Uart_Comm_loop_comm: GET size final value does not match expected size!");
                  clear_buffers();
                  return ASYNC_UART_COMM_CLEARING;
                }
              } else { // handle as variable size with large buffer
                *this->_get_received_size = this->_get_addr;   // store full received_size
              }
              _printDebug("Uart_Comm_loop_comm: GET read successfully, send ACK");
              this->_exp_chunk = 0;  // unique marker for message done
              _enable_ack();  // Last message was okay
              return ASYNC_UART_COMM_GETTING;
            }
            this->_exp_chunk += 1;
            _enable_ack();  // any message is okay when arrived here
            return ASYNC_UART_COMM_GETTING;
          }
          this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING; // _check_msg was false if arrived here
          _printDebug("Uart_Comm_loop_comm: GET->SET command error!");
          clear_buffers();
          return ASYNC_UART_COMM_CLEARING;

        case ASYNC_UART_COMM_CHECK_OK:       // ACK was sent successfully
          if (this->_exp_chunk > 0) {  // still receiving
            if (_read_with_ack(false, false)) {
              _printDebug("Uart_Comm_loop_comm: GET command waiting for response");
              return ASYNC_UART_COMM_GETTING;
            }
            this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;  // not returned here -> send ACK error
            _printDebug("Uart_Comm_loop_comm: ACK error!");
            clear_buffers();
            return ASYNC_UART_COMM_CLEARING;
          }
          this->_comm_mode = ASYNC_UART_COMM_MODE_IDLE;  // done, return to idle
          _printDebug("Uart_Comm_loop_comm: GET finished successfully");
          return ASYNC_UART_COMM_OK;

        case ASYNC_UART_COMM_CHECK_CLEARING:
          this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
          _printDebug("Uart_Comm_loop_comm: Forced into Clearing mode!");
          return ASYNC_UART_COMM_CLEARING;

        case ASYNC_UART_COMM_CHECK_IDLE:
        case ASYNC_UART_COMM_CHECK_INVALID:
        case ASYNC_UART_COMM_CHECK_STATE_ERROR:
        default:
          this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
          _printDebug("Uart_Comm_loop_comm: GET command error!");
          clear_buffers();
          return ASYNC_UART_COMM_CLEARING;
      }

    case ASYNC_UART_COMM_MODE_WRITE_SET:
      uint16_t cur_addr, cur_size;
      switch (comm_status) {
        case ASYNC_UART_COMM_CHECK_WRITING:
        case ASYNC_UART_COMM_CHECK_READING:
        case ASYNC_UART_COMM_CHECK_READING_DONE:
          return ASYNC_UART_COMM_SETTING;

        case ASYNC_UART_COMM_CHECK_OK:
          if (this->_cur_chunk >= this->_num_chunks) {  // done
            this->_comm_mode = ASYNC_UART_COMM_MODE_IDLE;  // done, return to idle
            _printDebug("Uart_Comm_loop_comm: SET finished successfully");
            return ASYNC_UART_COMM_OK;
          }
          cur_addr = (this->_cur_chunk - 1) * this->_payload_size; // sent bytes; chunk 1 = command, no payload, does not count
          cur_size = this->_set_size - cur_addr;                   // number of next payload bytes
          cur_size = (cur_size <= this->_payload_size) ? cur_size : this->_payload_size; // limit to max size
          this->_cur_chunk += 1;
          _inc_uid(); // get new UID for message
          if (this->_set_src == NULL) {
            _build_msg(this->_uid, ASYNC_UART_COMM_CMD_SET, this->_num_chunks, this->_cur_chunk, 0, NULL);
          } else {
            _build_msg(this->_uid, ASYNC_UART_COMM_CMD_SET, this->_num_chunks, this->_cur_chunk, cur_size, &this->_set_src[cur_addr]);
          }
          if (_write_with_ack()) {
            _printDebug("Uart_Comm_loop_comm: Sending SET chunk");
            return ASYNC_UART_COMM_SETTING;
          }
          this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
          _printDebug("Uart_Comm_loop_comm: SET command error!");
          clear_buffers();
          return ASYNC_UART_COMM_CLEARING;

        case ASYNC_UART_COMM_CHECK_CLEARING:
          this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
          _printDebug("Uart_Comm_loop_comm: Forced into Clearing mode!");
          return ASYNC_UART_COMM_CLEARING;

        case ASYNC_UART_COMM_CHECK_IDLE:
        case ASYNC_UART_COMM_CHECK_INVALID:
        case ASYNC_UART_COMM_CHECK_STATE_ERROR:
        default:
          this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
          _printDebug("Uart_Comm_loop_comm: SET command error!");
          clear_buffers();
          return ASYNC_UART_COMM_CLEARING;
      }

    case ASYNC_UART_COMM_MODE_LISTEN:
      char msgID;
      uint8_t exp_cmd, msg_size;
      bool last_chunk;
      uint16_t num_chunks;
      switch (comm_status) {
        case ASYNC_UART_COMM_CHECK_WRITING:
        case ASYNC_UART_COMM_CHECK_READING:
        case ASYNC_UART_COMM_CHECK_READING_DONE:
          return ASYNC_UART_COMM_LISTENING;

        case ASYNC_UART_COMM_CHECK_OK:
          exp_cmd = (ASYNC_UART_COMM_CMD_GET | ASYNC_UART_COMM_CMD_SET);  // expect both SET or GET (aligned bitwise)
          if (_check_msg(exp_cmd, 1, &msg_size, &last_chunk)) {           // valid message
            if (msg_size == 1) { // first payload always has size 1, is chunk 1 and has the command message ID as first element
              msgID = this->_read_buffer[ASYNC_UART_COMM_MSG_PAYLOAD];
            } else {
              this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
              _printDebug("Uart_Comm_uart_listen: Received message contains no MessageID!");
              clear_buffers();
              return ASYNC_UART_COMM_CLEARING;
            }
          } else {
            this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
            _printDebug("Uart_Comm_uart_listen: Received message is neither GET nor SET!");
            clear_buffers();
            return ASYNC_UART_COMM_CLEARING;
          }

          if (this->_read_buffer[ASYNC_UART_COMM_MSG_CMD] == ASYNC_UART_COMM_CMD_GET) {
            _printDebug("Uart_Comm_uart_listen: Received GET command, start SET to reply");
            if (this->_get_callback(&this->_set_src, &this->_set_size, msgID)) {
              this->_set_size = (this->_set_src == NULL) ? 0 : this->_set_size;
              num_chunks = (this->_set_size / this->_payload_size) + 1; // integer number of chunks; +1 --> first payload = setID
              if ( ((this->_set_size % this->_payload_size) > 0) ||   // add one chunk if remainder > 0
                   (num_chunks < 2) ) {                               // add one chunk (empty, just for ACK feedback) if message without payload
                num_chunks += 1;
              }
              if (num_chunks > 0xFF) {  // too large for num chunks field
                this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
                _printDebug("Uart_Comm_uart_listen: LISTEN->SET command not started, payload too large!");
                clear_buffers();
                return ASYNC_UART_COMM_CLEARING;
              }
              this->_num_chunks = (uint8_t)num_chunks;
              this->_cur_chunk = 1; // first chunk = set command
              _inc_uid();
              _build_msg(this->_uid, ASYNC_UART_COMM_CMD_SET, this->_num_chunks, this->_cur_chunk, 1, &msgID);
              if (_write_with_ack()) {
                _printDebug("Uart_Comm_uart_listen: Start LISTEN->SET command");
                this->_comm_mode = ASYNC_UART_COMM_MODE_WRITE_SET;
                return ASYNC_UART_COMM_SETTING;
              }
              _printDebug("Uart_Comm_uart_listen: Busy, LISTEN->SET command not started!");
            } else {  // _get_callback returned false
              _printDebug("Uart_Comm_uart_listen: Get Callback returned FALSE, cancelling operation!");
            }
            this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
            clear_buffers();
            return ASYNC_UART_COMM_CLEARING;
          }

          if (this->_read_buffer[ASYNC_UART_COMM_MSG_CMD] == ASYNC_UART_COMM_CMD_SET) {
            _printDebug("Uart_Comm_uart_listen: Received SET command");
            if(this->_set_callback(&this->_get_dest, &this->_get_size, &this->_get_received_size, msgID)) {
              this->_get_size = (this->_get_dest == NULL) ? 0 : this->_get_size;
              this->_get_id = msgID;
              this->_exp_chunk = 2; // first chunk with the message ID was the command itself already!
              this->_get_addr = 0;
              if (this->_get_received_size != NULL) {
                *this->_get_received_size = 0;
              }
              if (_read_with_ack(false, false)) {  // No new UID required, as no GET command is issued. Read with timeout from here.
                this->_comm_mode = ASYNC_UART_COMM_MODE_READ_GET; // ACK is issued whenever ASYNC_UART_COMM_MODE_READ_GET is okay
                _printDebug("Uart_Comm_uart_listen: Start LISTEN->GET command");
                return ASYNC_UART_COMM_GETTING;
              }
               _printDebug("Uart_Comm_uart_listen: Busy, LISTEN->GET command not started!");
            } else {  // _set_callback returned false
              _printDebug("Uart_Comm_uart_listen: Set Callback returned FALSE, cancelling operation!");
            }
            this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
            clear_buffers();
            return ASYNC_UART_COMM_CLEARING;
          }
        // in (the actually impossible) case of no return until here, code will correctly fall to "default" state!

        case ASYNC_UART_COMM_CHECK_CLEARING:
          this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
          _printDebug("Uart_Comm_uart_listen: Forced into Clearing mode!");
          return ASYNC_UART_COMM_CLEARING;

        case ASYNC_UART_COMM_CHECK_IDLE:
        case ASYNC_UART_COMM_CHECK_INVALID:
        case ASYNC_UART_COMM_CHECK_STATE_ERROR:
        default:
          this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
          _printDebug("Uart_Comm_loop_comm: LISTEN command error!");
          clear_buffers();
          return ASYNC_UART_COMM_CLEARING;
      }

    case ASYNC_UART_COMM_MODE_CLEARING:
      switch (comm_status) {
        case ASYNC_UART_COMM_CHECK_CLEARING:
          return ASYNC_UART_COMM_CLEARING;

        case ASYNC_UART_COMM_CHECK_OK:
          this->_comm_mode = ASYNC_UART_COMM_MODE_IDLE;
          _printDebug("Uart_Comm_loop_comm: Clearing UART Buffers done");
          return ASYNC_UART_COMM_OK;

        case ASYNC_UART_COMM_CHECK_INVALID:
        case ASYNC_UART_COMM_CHECK_STATE_ERROR:
        default:
          _printDebug("Uart_Comm_loop_comm: Clearing error, retrying...");
          clear_buffers();
          return ASYNC_UART_COMM_CLEARING;
      }

    default:
      this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
      _printDebug("Uart_Comm_loop_comm: State error, clearing buffers!");
      clear_buffers();
      return ASYNC_UART_COMM_CLEARING;
  }
}

void Async_UART_Comm::_inc_uid() {
  this->_uid = (this->_uid >= 0xFE) ? 0 : this->_uid + 1;
}

bool Async_UART_Comm::_check_msg(uint8_t exp_cmd, uint8_t exp_chunk, uint8_t* msg_size, bool* last_chunk) {
  *msg_size = 0;
  if (!((uint8_t)this->_read_buffer[ASYNC_UART_COMM_MSG_CMD] & exp_cmd)) {
    _printDebug("UART_Comm_check_msg: Unexpected command ID!");
    return false;
  }
  if ((uint8_t)this->_read_buffer[ASYNC_UART_COMM_MSG_CUR_CHUNK] > (uint8_t)this->_read_buffer[ASYNC_UART_COMM_MSG_CHUNKS]) {
    _printDebug("UART_Comm_check_msg: Chunk index too high!");
    return false;
  }
  if ((uint8_t)this->_read_buffer[ASYNC_UART_COMM_MSG_CUR_CHUNK] != exp_chunk) {
    _printDebug("UART_Comm_check_msg: Unexpected chunk ID!");
    return false;
  }
  *last_chunk = ( this->_read_buffer[ASYNC_UART_COMM_MSG_CUR_CHUNK] == this->_read_buffer[ASYNC_UART_COMM_MSG_CHUNKS]);
  *msg_size = (uint8_t)this->_read_buffer[ASYNC_UART_COMM_MSG_SIZE];
  if ( (*msg_size < 0) || (*msg_size > this->_payload_size) ) {
    _printDebug("UART_Comm_check_msg: Invalid payload size!");
    return false;
  }
  return true;
}

bool Async_UART_Comm::_write_with_ack() {
  if (this->_comm_state == ASYNC_UART_COMM_STATE_IDLE) {
    _printDebug("Uart_Comm_write_with_ack: Start write with ack");
    this->_comm_state = ASYNC_UART_COMM_STATE_WRITE_STARTING;
    return true;
  }
  _printDebug("Uart_Comm_write_with_ack: Busy, write with ack not started!");
  return false;
}

bool Async_UART_Comm::_read_with_ack(bool wait, bool auto_ack) {
  if (this->_comm_state == ASYNC_UART_COMM_STATE_IDLE) {
    this->_enable_read_ack = auto_ack;
    unsigned long startTimeout = (wait) ? ASNYC_UART_NO_TIMEOUT : this->_timeout;
    if (this->_asy_uart.start_reading_until_complete(this->_read_buffer,
                                                      ASYNC_UART_COMM_NUM_MSG_FIELDS + this->_payload_size,
                                                      startTimeout,
                                                      this->_timeout)) {
      _printDebug("Uart_Comm_read_with_ack: Start read with ack");
      this->_comm_state = ASYNC_UART_COMM_STATE_READ_READING;
      return true;
    } // if start_reading_until_complete returns false, it's internally busy as well
  }
  _printDebug("Uart_Comm_read_with_ack: Busy, read with ack not started!");
  return false;
}

bool Async_UART_Comm::_enable_ack() {
  if ( (this->_comm_state == ASYNC_UART_COMM_STATE_READ_READING_ACK) &&
       (!this->_enable_read_ack) ) {
    this->_enable_read_ack = true;
    return true;
  }
  return false;
}

void Async_UART_Comm::_build_msg(uint8_t uid, uint8_t cmd, uint8_t chunks, uint8_t cur_chunk, uint8_t payload_size, char* payload) {
  this->_write_buffer[ASYNC_UART_COMM_MSG_UID] = (char)uid;
  this->_write_buffer[ASYNC_UART_COMM_MSG_CMD] = (char)cmd;
  this->_write_buffer[ASYNC_UART_COMM_MSG_SIZE] = (char)payload_size;
  this->_write_buffer[ASYNC_UART_COMM_MSG_CHUNKS] = (char)chunks;
  this->_write_buffer[ASYNC_UART_COMM_MSG_CUR_CHUNK] = (char)cur_chunk;  // set message header fields
  if (payload != NULL) {
    memcpy(&this->_write_buffer[ASYNC_UART_COMM_MSG_PAYLOAD], payload, payload_size * sizeof(char)); // copy payload into tx buffer
  } else {
    payload_size = 0;
  }
  if (payload_size < this->_payload_size) { // if msg not full, empty remaining space
    memset(&this->_write_buffer[ASYNC_UART_COMM_MSG_PAYLOAD + payload_size], 0x00, this->_payload_size - payload_size);
  }
}

uint8_t Async_UART_Comm::_check_comm() {
  uint8_t comm_status;
  uint8_t ch_rd, ch_rd_cm, ch_wr;
  if (this->_clear) {
    _printDebug("Uart_Comm_check_comm: Stopping all UART operations");
    this->_enable_writing = false;  // disallow any new writing operations
    this->_write_timer_running = false; // stop any timer, must be started when clearing is done
    ch_rd = this->_asy_uart.check_reading();                   // store into variables to ensure all checks are actually executed
    ch_rd_cm = this->_asy_uart.check_reading_until_complete(); // and the UART state being driven. might not be the case if
    ch_wr = this->_asy_uart.check_writing();                   // inside the AND condition (if e.g. first is false, check is already cancelled)
    if ( (ch_rd == ASYNC_UART_IDLE) &&  // trigger both periodic read functions until both are idle
         (ch_rd_cm == ASYNC_UART_IDLE) && // no more read operations ongoing
         (ch_wr == ASYNC_UART_IDLE) ) {  // no more writing operations ongoing
      _printDebug("Uart_Comm_check_comm: UART idle, start clearing");
      this->_comm_state = ASYNC_UART_COMM_STATE_CLEARING;  // actual clearing read operation can be started
      this->_clear = false;
    } else {
      _printDebug("Uart_Comm_check_comm: Waiting for UART to be idle");
      this->_asy_uart.cancel_read_timeout();  // something is still reading, cancel timeout, skip state machine until done
      return ASYNC_UART_COMM_CHECK_CLEARING;
    }
  } else {  // no clearing pending or already ongoing
    if ( (!this->_enable_writing) &&  // writing currently disabled (happens just above when clearing is pending)
         (this->_write_timer_running) ) { // only if the timer is running and valid (set in CLEARING state)
      unsigned long current_time = millis();
      unsigned long current_timeout = (this->_timeout * 3) >> 1;  // 1.5 times the usual timeout
      if ((current_time - this->_enable_write_time) >= current_timeout) {  // timeout is over
        _printDebug("Uart_Comm_check_comm: Writing timeout over, writing enabled");
        this->_enable_writing = true;
        this->_write_timer_running = false;
      }
    }
  }

  switch(this->_comm_state) {
    case ASYNC_UART_COMM_STATE_IDLE:
      ch_rd = this->_asy_uart.check_reading();
      ch_rd_cm = this->_asy_uart.check_reading_until_complete();
      ch_wr = this->_asy_uart.check_writing();
      if ( (ch_rd == ASYNC_UART_IDLE) &&     // Check if UART is *really* idle
           (ch_rd_cm == ASYNC_UART_IDLE) &&
           (ch_wr == ASYNC_UART_IDLE) ) {
        return ASYNC_UART_COMM_CHECK_IDLE;
      }
      _printDebug("Uart_Comm_check_comm: UART is not idle in comm idle state!");
      return ASYNC_UART_COMM_CHECK_INVALID;

    case ASYNC_UART_COMM_STATE_WRITE_STARTING:
      if (this->_enable_writing) {
        if (this->_asy_uart.start_writing(this->_write_buffer, ASYNC_UART_COMM_NUM_MSG_FIELDS + this->_payload_size)) {  // CRC is implicitely included!
          _printDebug("Uart_Comm_check_comm: Writing started");
          this->_comm_state = ASYNC_UART_COMM_STATE_WRITE_WRITING;
          return ASYNC_UART_COMM_CHECK_WRITING;
        } // if start_writing returns false, it's internally busy
        this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
        _printDebug("Uart_Comm_check_comm: Write-Starting cannot start writing, internally busy!");
        return ASYNC_UART_COMM_CHECK_INVALID;
      } // if arrived here, writing is not enabled yet
      return ASYNC_UART_COMM_CHECK_WRITING;

    case ASYNC_UART_COMM_STATE_WRITE_WRITING:
      comm_status = this->_asy_uart.check_writing();
      switch(comm_status) {
        case ASYNC_UART_IDLE: // idle UART while writing should never happen, catch anyhow
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Write-Writing unexpectedly idle!");
          return ASYNC_UART_COMM_CHECK_IDLE;

        case ASYNC_UART_WAITING: // not yet finished with writing, keep waiting
          return ASYNC_UART_COMM_CHECK_WRITING;

        case ASYNC_UART_OK: // finished writing, wait for ACK response
          if (this->_asy_uart.start_reading_until_complete(this->_read_buffer,
                                                           ASYNC_UART_COMM_NUM_MSG_FIELDS + this->_payload_size,
                                                           this->_timeout,
                                                           this->_timeout) ) {
            this->_comm_state = ASYNC_UART_COMM_STATE_WRITE_READING;
            _printDebug("Uart_Comm_check_comm: Write-Writing successful, waiting for ACK");
            return ASYNC_UART_COMM_CHECK_READING;
          }
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Write-Writing cannot start write-reading, internally busy!");
          return ASYNC_UART_COMM_CHECK_INVALID;

        default:
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Write-Writing state error!");
          return ASYNC_UART_COMM_CHECK_STATE_ERROR;
      }

    case ASYNC_UART_COMM_STATE_WRITE_READING:
      comm_status = this->_asy_uart.check_reading_until_complete();
      switch(comm_status) {
        case ASYNC_UART_IDLE: // idle UART while writing should never happen, catch anyhow
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Write-Reading unexpectedly idle!");
          return ASYNC_UART_COMM_CHECK_IDLE;

        case ASYNC_UART_BUSY:
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Write-Reading unexpectedly busy!");
          return ASYNC_UART_COMM_CHECK_INVALID;

        case ASYNC_UART_WAITING:
          return ASYNC_UART_COMM_CHECK_READING;

        case ASYNC_UART_OK:
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Write-Reading done");
          if (this->_read_buffer[ASYNC_UART_COMM_MSG_CMD] == ASYNC_UART_COMM_CMD_ACK) {
            if (this->_read_buffer[ASYNC_UART_COMM_MSG_UID] == this->_write_buffer[ASYNC_UART_COMM_MSG_UID]) {
            return ASYNC_UART_COMM_CHECK_OK;  // ACK command and correct message UID
            } else {
              _printDebug("Uart_Comm_check_comm: Write-Reading wrong UID!");
            }
          } else {
            _printDebug("Uart_Comm_check_comm: Write-Reading response was not ack!");
          }
          return ASYNC_UART_COMM_CHECK_INVALID;

        case ASYNC_UART_TIMEOUT:
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Write-Reading timeout!");
          return ASYNC_UART_COMM_CHECK_INVALID;

        case ASYNC_UART_CRC_ERROR:
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Write-Reading CRC error!");
          return ASYNC_UART_COMM_CHECK_INVALID;

        default:
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Write-Reading state error!");
          return ASYNC_UART_COMM_CHECK_STATE_ERROR;
      }

    case ASYNC_UART_COMM_STATE_READ_READING:
      comm_status = this->_asy_uart.check_reading_until_complete();
      switch(comm_status) {
        case ASYNC_UART_IDLE: // idle UART while writing should never happen, catch anyhow
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Read-Reading unexpectedly idle!");
          return ASYNC_UART_COMM_CHECK_IDLE;

        case ASYNC_UART_BUSY:
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Read-Reading unexpectedly busy!");
          return ASYNC_UART_COMM_CHECK_INVALID;

        case ASYNC_UART_WAITING:
          return ASYNC_UART_COMM_CHECK_READING;

        case ASYNC_UART_OK:
          this->_comm_state = ASYNC_UART_COMM_STATE_READ_READING_ACK;
          _printDebug("Uart_Comm_check_comm: Read-Reading done, wait for ACK enable");
          return ASYNC_UART_COMM_CHECK_READING_DONE;

        case ASYNC_UART_TIMEOUT:
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Read-Reading timeout!");
          return ASYNC_UART_COMM_CHECK_INVALID;

        case ASYNC_UART_CRC_ERROR:
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Read-Reading CRC error!");
          return ASYNC_UART_COMM_CHECK_INVALID;

        default:
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Read-Reading state error!");
          return ASYNC_UART_COMM_CHECK_STATE_ERROR;
      }

    case ASYNC_UART_COMM_STATE_READ_READING_ACK:
      if (this->_enable_read_ack) {
        _printDebug("Uart_Comm: ACK enabled");
        _build_msg( (uint8_t)this->_read_buffer[ASYNC_UART_COMM_MSG_UID], ASYNC_UART_COMM_CMD_ACK, 1, 1, 0, NULL); // Build ACK msg (CRC is already checked at this point)
        if (this->_asy_uart.start_writing(this->_write_buffer, ASYNC_UART_COMM_NUM_MSG_FIELDS + this->_payload_size)) {  // CRC is implicitely included!
          _printDebug("Uart_Comm: Start Read-Writing ack msg");
          this->_comm_state = ASYNC_UART_COMM_STATE_READ_WRITING;
          return ASYNC_UART_COMM_CHECK_WRITING;
        }
        this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
        _printDebug("Uart_Comm_check_comm: Read-Reading cannot start read-writing, internally busy!");
        return ASYNC_UART_COMM_CHECK_INVALID;
      }
      return ASYNC_UART_COMM_CHECK_WRITING;

    case ASYNC_UART_COMM_STATE_READ_WRITING:
      comm_status = this->_asy_uart.check_writing();
      switch(comm_status) {
        case ASYNC_UART_IDLE: // idle UART while writing should never happen, catch anyhow
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Read-Writing unexpectedly idle!");
          return ASYNC_UART_COMM_CHECK_IDLE;

        case ASYNC_UART_WAITING: // not yet finished with writing, keep waiting
          return ASYNC_UART_COMM_CHECK_WRITING;

        case ASYNC_UART_OK: // finished writing, wait for ACK response
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Read-Writing done");
          return ASYNC_UART_COMM_CHECK_OK;  // Done sending ACK

        default:
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Read-Writing state error!");
          return ASYNC_UART_COMM_CHECK_STATE_ERROR;
      }

    case ASYNC_UART_COMM_STATE_CLEARING:
      comm_status = this->_asy_uart.check_reading();
      this->_enable_read_ack = true; // reset flag to default in case of errors
      switch(comm_status) {
        case ASYNC_UART_IDLE: // currently inactive, start reading as much as possible
          if (this->_asy_uart.start_reading(NULL,     // discard contents, don't read into any buffer
                                           ASYNC_UART_COMM_NUM_MSG_FIELDS + this->_payload_size + CRC_CHECK_CRC_16_SIZE, // read in msg-size chunks
                                           (this->_timeout * 3) >> 1) ) {  // 1.5 times the usual timeout
            _printDebug("Uart_Comm_check_comm: Start or continue clearing UART buffers...");
            return ASYNC_UART_COMM_CHECK_CLEARING;
          }
          _printDebug("Uart_Comm_check_comm: Clearing UART buffers not yet started, still internally busy, retrying...");
          return ASYNC_UART_COMM_CHECK_INVALID;

        case ASYNC_UART_BUSY:
          _printDebug("Uart_Comm_check_comm: Clearing UART buffers not yet started, still busy, retrying...");
          return ASYNC_UART_COMM_CHECK_INVALID;

        case ASYNC_UART_WAITING:
          return ASYNC_UART_COMM_CHECK_CLEARING;

        case ASYNC_UART_TIMEOUT:  // here, a timeout means no more contents in the buffer
          _printDebug("Uart_Comm_check_comm: Clearing UART buffers done");
          this->_enable_write_time = millis();  // start timer for re-enabling write operations
          this->_write_timer_running = true;
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          return ASYNC_UART_COMM_CHECK_OK;

        case ASYNC_UART_OK: // one full chunk cleared, go on reading...
          _printDebug("Uart_Comm_check_comm: Clearing UART ongoing");
          return ASYNC_UART_COMM_CHECK_CLEARING;  // Done sending ACK

        default:  // no valid return value, should be impossible to happen
          this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
          _printDebug("Uart_Comm_check_comm: Clearing UART state error!");
          return ASYNC_UART_COMM_CHECK_STATE_ERROR;
      }

    default:
      this->_comm_state = ASYNC_UART_COMM_STATE_IDLE;
      _printDebug("Uart_Comm_check_comm: General communication state error!");
      return ASYNC_UART_COMM_CHECK_STATE_ERROR;
  }
}

void Async_UART_Comm::_printDebug(const char* msg) {
  if ( (this->_debug_active) && (this->_debug != NULL) ) {
    this->_debug->println(msg);
  }
}
