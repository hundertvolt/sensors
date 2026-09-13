#ifndef CRC_CHECK_h
#define CRC_CHECK_h

#include "Arduino.h"

#define CRC_CHECK_CRC_NONE_SIZE 0
#define CRC_CHECK_CRC_16_SIZE 2

class CRC_Check
{
  public:
    virtual void set_poly(uint16_t poly);
    virtual void set_preset(uint16_t preset);
    virtual void add(char *bytes, uint16_t length);
    virtual bool check(char *bytes, uint16_t length);
    virtual uint16_t size();
};

class CRC_None:public CRC_Check
{
  public:
    CRC_None();
    void set_poly(uint16_t poly);
    void set_preset(uint16_t preset);
    void add(char *bytes, uint16_t length);
    bool check(char *bytes, uint16_t length);
    uint16_t size();
};

class CRC_16:public CRC_Check
{
  public:
    CRC_16();
    void set_poly(uint16_t poly);
    void set_preset(uint16_t preset);
    void add(char *bytes, uint16_t length);
    bool check(char *bytes, uint16_t length);
    uint16_t size();
  private:
    uint16_t _crc16(char *bytes, uint16_t length);
    uint16_t _poly;
    uint16_t _preset;
};

#endif
