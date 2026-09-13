#include "Arduino.h"
#include "CRC_Check.h"

CRC_None::CRC_None() {}  // No CRC, does neutral operations

void CRC_None::set_poly(uint16_t poly) {}

void CRC_None::set_preset(uint16_t preset) {}

void CRC_None::add(char *bytes, uint16_t length) {}

bool CRC_None::check(char *bytes, uint16_t length) {
  return true;
}

uint16_t CRC_None::size() {
  return CRC_CHECK_CRC_NONE_SIZE;
}

CRC_16::CRC_16()  // CRC16 (2 bytes)
{
  this->_poly = 0x1021;
  this->_preset = 0xFFFF;
}

void CRC_16::set_poly(uint16_t poly) {
  this->_poly = poly;  // set individual polynomial
}

void CRC_16::set_preset(uint16_t preset) {
  this->_preset = preset;  // set individual preset
}

void CRC_16::add(char *bytes, uint16_t length) {
  uint16_t crc = _crc16(bytes, length);
  bytes[length] = (char)0xFF & crc;           // insert CRC into next 2 bytes
  bytes[length + 1] = (char)0xFF & crc >> 8;  // array must have sufficient size!
}

bool CRC_16::check(char *bytes, uint16_t length) {
  uint16_t crc = _crc16(bytes, length + 2);
  return crc == 0;  // check if CRC is valid (CRC over payload and CRC == 0)
}

uint16_t CRC_16::size() {
  return CRC_CHECK_CRC_16_SIZE;   // CRC checksum size in bytes
}

uint16_t CRC_16::_crc16(char *bytes, uint16_t length) {
  uint8_t i;       // Actual CRC algorithm
  uint16_t data;
  uint16_t crc = this->_preset;

  if (length == 0) {
    return (crc);
  }

  do {
    for (i = 0, data = (uint16_t) 0xFF & *bytes++; i < 8; i++, data >>= 1) {
      if ((crc & 0x0001) ^ (data & 0x0001)) {
        crc = (crc >> 1) ^ this->_poly;
      } else {
        crc >>= 1;
      }
    }
  } while (--length);
  return (crc);
}
