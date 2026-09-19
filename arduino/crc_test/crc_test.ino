// #include <CRC_Check.h>
// #include <Async_UART.h>
#include <Async_UART_Comm.h>

#define IDLE 0
#define LISTENING 1
#define GETTING 2
#define SETTING 3
#define UNINITIALIZED 4

// CRC_16 crc;
// CRC_None crc;
// Async_UART uart;

Async_UART_Comm uart_comm;

uint8_t readStatus;
uint16_t trigger;
char buf0[] = "Some long text to go, maybe even longer than one chunk of data so it needs to be split! It's most interesting if it arrives complete and in correct order.";
char buf1[] = "Some short text.";
uint16_t receivedBytes;
uint8_t listenStatus = UNINITIALIZED;
// char largebuf[640];

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  delay(1000);
  // uart.init(&Serial1, 115200, &crc);
  trigger = 0;
  uart_comm.init(&Serial1, 115200, 48, 2500, &Serial);
  uart_comm.set_debug(true);
  Serial.println("MAIN: UART Init.");
}

bool getCallback(char** src, uint16_t* size, char getID) {
  Serial.print("MAIN: UART Start getting. GetID: ");
  Serial.println((uint8_t)getID);
  switch (getID) {
    case 0x4a:
      *src = buf0;
      *size = 155;
      listenStatus = GETTING;
      return true;
    case 0x3b:
      *src = buf1;
      *size = 16;
      listenStatus = GETTING;
      return true;
    case 0x3c:
      *src = NULL;
      *size = 0;
      listenStatus = GETTING;
      return true;
    default:
      *src = NULL;
      *size = 0;
      listenStatus = IDLE;
      return false;
  }
}

bool setCallback(char** dst, uint16_t* exp_max_size, uint16_t** recv_size, char setID) {
  *recv_size = &receivedBytes;
  Serial.print("MAIN: UART Start setting. SetID: ");
  Serial.println((uint8_t)setID);
  switch (setID) {
    case 0x2d:
      *dst = buf0;
      *exp_max_size = 100;
      receivedBytes = 100;
      *recv_size =NULL;
      listenStatus = SETTING;
      return true;
    case 0x5f:
      *dst = buf0;
      *exp_max_size = 0;
      listenStatus = SETTING;
      *recv_size =NULL;
      return true;
    default:
      *dst = NULL;
      *exp_max_size = 0;
      listenStatus = IDLE;
      return false;
  }
}

void loop() {
  // put your main code here, to run repeatedly:
  delay(10);


  if (listenStatus == UNINITIALIZED) {
    Serial.println("UART Listen Status uninitialized, clearing input buffers.");
    uart_comm.clear_buffers();
    listenStatus = IDLE;
  }


  readStatus = uart_comm.loop_comm();
  //Serial.println(readStatus);
/*
  if ((readStatus == ASYNC_UART_COMM_CLEARING) &&
      (listenStatus != IDLE)) {
    Serial.println("MAIN: UART clearing, resetting listen status!");
    listenStatus = IDLE;
  }

  if ((readStatus == ASYNC_UART_COMM_IDLE) &&
      (listenStatus == IDLE)) {
    Serial.println("MAIN: UART Idle, start listening.");
    uart_comm.uart_listen(getCallback, setCallback);
    listenStatus = LISTENING;
  }

  if (readStatus == ASYNC_UART_COMM_OK) {
    if (listenStatus == SETTING) {
      Serial.println("MAIN: UART Setting done.");
      for (uint8_t n = 0; n < receivedBytes; n++) {  
        Serial.print(buf0[n]);
        }
        Serial.println("\n****");
      listenStatus = IDLE;
    } else if (listenStatus == GETTING) {
      Serial.println("MAIN: UART Getting done.");
      listenStatus = IDLE;
    }
  }*/
  /*
  trigger += 1;
    if (trigger == 4) {
    // trigger = 0;
    uart_comm.clear_buffers();
    } */
  
  // Serial.println(uart.check_reading());
  trigger += 1;
  
  if (trigger > 200) {
    trigger = 0;
    if (readStatus == ASYNC_UART_COMM_IDLE) {
      uart_comm.uart_set(NULL, 10, 0x1B);
      // uart_comm.uart_set(buf0, 155, 0x1A);
      // uart_comm.uart_get(buf0, 50, &receivedBytes, 0x34);
      // uart_comm.uart_get(NULL, 10, &receivedBytes, 0x22);

      /*
      // uart.start_reading(NULL, 20, 3000);
      for (uint8_t n = 0; n < 50; n++) {
        
       Serial.print(buf0[n]);
      }
      Serial.println("\n****");
      // uart_comm.build_msg(5, 1, 1, 1, 0, NULL);
      // uart_comm.write_with_ack(); */
   }
 }

  /*
  if (readStatus == -3) {
    Serial.println("UART start reading!");
    uart.start_reading_until_complete(buf, 10, 3500, 2500);
  }

  readStatus = uart.check_reading();
  if (readStatus == ASYNC_UART_WAITING) {
    Serial.println("UART waiting");
  } else if (readStatus == ASYNC_UART_TIMEOUT) {
    Serial.println("UART Timeout");
    readStatus = -3;
  } else if (readStatus == ASYNC_UART_CRC_ERROR) {
    Serial.println("UART CRC error");
    readStatus = -3; 
  } else if (readStatus == ASYNC_UART_OK) {
    Serial.println("UART read OK");
    for (uint8_t n = 0; n < 10; n++) {
      Serial.print(buf[n]);
    }
    Serial.println("\n****");
    readStatus = -3;
  }

  

  uart.start_writing(largebuf, 10);
  readStatus = uart.check_writing();
  if (readStatus == ASYNC_UART_WAITING) {
    Serial.println("UART waiting");
  } else if (readStatus == ASYNC_UART_BREAK) {
    Serial.println("UART Idle");
    readStatus = -3;
  } else if (readStatus == ASYNC_UART_OK) {
    Serial.println("UART Write OK");
  }
  delay(1000);
  */
}