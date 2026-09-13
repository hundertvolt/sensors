#include "Arduino.h"
#include "Async_UART.h"

Async_UART::Async_UART()
{
  this->_cancel_reading = false;
  this->_read_status = ASYNC_UART_READ_IDLE;
  this->_write_status = ASYNC_UART_WRITE_IDLE;
  this->_read_addr = 0;
  this->_write_addr = 0;
  this->_read_time = 0;
  this->_start_timeout = ASNYC_UART_NO_TIMEOUT;
  this->_read_timeout = ASNYC_UART_NO_TIMEOUT;
}

void Async_UART::init(Uart *uart, long baudrate, CRC_Check *crc) {
  this->_uart = uart;
  this->_uart->begin(baudrate);
  this->_crc = crc;
}

bool Async_UART::start_reading(char *buffer, uint16_t max_size, unsigned long timeout_ms) {  // read at max max_size characters with timeout
  if (this->_read_status == ASYNC_UART_READ_IDLE) {
    this->_cancel_reading = false;
    this->_read_status = ASYNC_UART_READ_READY;
    this->_read_nbytes = max_size;
    this->_read_time = millis();
    this->_read_timeout = timeout_ms;
    this->_read_buffer = buffer;   // buffer is allowed to be NULL here for just emptying the input
    return true;  // initiate reading if interface is not busy
  }
  return false;
}

bool Async_UART::start_reading_until_complete(char *buffer, uint16_t nbytes, unsigned long start_timeout_ms, unsigned long timeout_ms) {
  if (this->_read_status == ASYNC_UART_READ_IDLE) {
    this->_cancel_reading = false;
    this->_read_status = ASYNC_UART_READ_COMPLETE_READY;
    this->_read_addr = 0;
    this->_read_nbytes = nbytes;
    this->_read_time = millis();
    this->_start_timeout = start_timeout_ms;
    this->_read_timeout = timeout_ms;
    this->_read_buffer = buffer;
    return true;  // initiate reading if interface is not busy
  }
  return false;
}

bool Async_UART::cancel_read_timeout() {
  if (this->_read_status == ASYNC_UART_READ_IDLE) {
    return false;  // no operation pending, cannot cancel anything
  }
  this->_cancel_reading = true;
  return true;
}

bool Async_UART::start_writing(char *buffer, uint16_t nbytes) {
  if (this->_write_status == ASYNC_UART_WRITE_IDLE) {
    this->_write_status = ASYNC_UART_WRITE_ACTIVE;
    this->_write_addr = 0;
    this->_write_nbytes = nbytes;
    this->_write_buffer = buffer;
    this->_crc->add(this->_write_buffer, this->_write_nbytes);  // add CRC - make sure buffer is large enough!
    this->_write_nbytes += this->_crc->size();  // add CRC size to bytes to transmit
    return true;  // initiate writing if interface is not busy
  }
  return false;
}

uint8_t Async_UART::check_reading() {   // asynchronous repetitive status check for reading one character
  if (this->_read_status == ASYNC_UART_READ_IDLE) {
    return ASYNC_UART_IDLE;  // no reading operation active
  }
  if ( (this->_read_status == ASYNC_UART_READ_COMPLETE_READY) ||
       (this->_read_status == ASYNC_UART_READ_COMPLETE_STARTED) ) {
    return ASYNC_UART_BUSY;  // other reading operation already active
  }

  int avail = this->_uart->available();
  if (avail == 0) {    // No new characters available
    unsigned long current_time = millis();
    if ( ( (this->_read_timeout == ASNYC_UART_NO_TIMEOUT) ||
         ( (current_time - this->_read_time) <= this->_read_timeout)) &&
       (!this->_cancel_reading) ) {
      return ASYNC_UART_WAITING;  // no timeout or still time to go
    }
    this->_cancel_reading = false;
    this->_read_status = ASYNC_UART_READ_IDLE;
    return ASYNC_UART_TIMEOUT;  // timeout triggered
  }

  // if not returned until here, new characters were received
  int loopUntil = (avail <= this->_read_nbytes) ? avail : this->_read_nbytes;  // read as many chars as possible, but not more than max
  if (this->_read_buffer == NULL) {    // if no destination buffer given, just empty the UART buffers by reading
    for (int n = 0; n < loopUntil; n++) {
      this->_uart->read();
    }
  } else {
    for (int n = 0; n < loopUntil; n++) {
      this->_read_buffer[n] = this->_uart->read();  // read into dest buffer
    }
  }
  this->_read_status = ASYNC_UART_READ_IDLE;
  return ASYNC_UART_OK;
}

uint8_t Async_UART::check_reading_until_complete() {   // asynchronous repetitive status check for reading
  if (this->_read_status == ASYNC_UART_READ_IDLE) {
    return ASYNC_UART_IDLE;  // no reading operation active
  }
  if (this->_read_status == ASYNC_UART_READ_READY) {
    return ASYNC_UART_BUSY;  // other reading operation already active
  }

  if (this->_uart->available() == 0) {    // No new characters available
    unsigned long current_time = millis();
    unsigned long current_timeout;
    if (this->_read_status == ASYNC_UART_READ_COMPLETE_READY) {  // Still waiting for first character
      current_timeout = this->_start_timeout;           // timeout for transmission begin
    } else {                                            // characters were already received
      current_timeout = this->_read_timeout;            // timeout for transmission continuation
    }
    if ( ( (current_timeout == ASNYC_UART_NO_TIMEOUT) ||
         ( (current_time - this->_read_time) <= current_timeout) ) &&
       (!this->_cancel_reading) ) {
      return ASYNC_UART_WAITING;  // no timeout or still time to go
    }
    this->_cancel_reading = false;
    this->_read_status = ASYNC_UART_READ_IDLE;
    return ASYNC_UART_TIMEOUT;  // timeout triggered
  }

  // if not returned until here, new characters were received in time
  uint16_t readbytes = this->_read_nbytes + this->_crc->size(); // characters + checksum size to read

  while ( (this->_uart->available() > 0) && (this->_read_addr < readbytes) ) {
    this->_read_buffer[this->_read_addr] = this->_uart->read();
    this->_read_addr++;
  }  // read until no more received characters are available or expected number of characters was received

  if (this->_read_addr < readbytes) {  // not yet the expected number
    this->_read_time = millis();       // for timeout
    this->_read_status = ASYNC_UART_READ_COMPLETE_STARTED; // remember transmission was started
    return ASYNC_UART_WAITING;
  }
  this->_read_status = ASYNC_UART_READ_IDLE;  // if arrived here, transmission is complete
  if (this->_crc->check(this->_read_buffer, this->_read_nbytes)) {  // check validity
    return ASYNC_UART_OK;
  }
  return ASYNC_UART_CRC_ERROR;
}

uint8_t Async_UART::check_writing() {   // asynchronous repetitive status check for writing
  if (this->_write_status == ASYNC_UART_READ_IDLE) {
    return ASYNC_UART_IDLE;  // no writing operation active
  }
  int available = this->_uart->availableForWrite();         // transmission buffer free size
  int remaining = this->_write_nbytes - this->_write_addr;  // remaining characters to transmit
  if (available >= remaining) {  // remaining characters all fit into TX buffer
    this->_uart->write(&this->_write_buffer[this->_write_addr], remaining);  // write all at once
    this->_write_status = ASYNC_UART_WRITE_IDLE;  // end of transmission
    return ASYNC_UART_OK;
  } else if (available > 0) {  // buffer too small, but some space available
    this->_uart->write(&this->_write_buffer[this->_write_addr], available);  // write as much as space allows
    this->_write_addr += available;  // remember where to continue
    return ASYNC_UART_WAITING;
  }
  return ASYNC_UART_WAITING;  // no space in TX buffer available yet
}
