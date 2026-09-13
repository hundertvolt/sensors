/**
 * Copyright (C) 2021 Bosch Sensortec GmbH
 *
 * SPDX-License-Identifier: BSD-3-Clause
 * 
 */

/* If compiling this examples leads to an 'undefined reference error', refer to the README
 * at https://github.com/BoschSensortec/Bosch-BSEC2-Library
 */
/* The new sensor needs to be conditioned before the example can work reliably. You may run this
 * example for 24hrs to let the sensor stabilize.
 */

/**
 * basic_config_state.ino sketch :
 * This is an example for integration of BSEC2x library using configuration setting and has been 
 * tested with Adafruit ESP8266 Board
 * 
 * For quick integration test, example code can be used with configuration file under folder
 * Bosch_BSEC2_Library/src/config/FieldAir_HandSanitizer (Configuration file added as simple
 * code example for integration but not optimized on classification performance)
 * Config string for H2S and NonH2S target classes is also kept for reference (Suitable for
 * lab-based characterization of the sensor)
 */

#define AIRQUALITY     1
#define CLASSIFICATION 2

#define SENSOR_MODE AIRQUALITY

#include <wdt_samd21.h>
#include <Async_UART_Comm.h>
#include <bsec2.h>

typedef struct {
  int8_t measRunning;
  int8_t stateUpdated;
  int8_t lastBsecError;
  int8_t lastSensorError;
  uint32_t systemUptime;
} system_status;

#if (SENSOR_MODE == AIRQUALITY)
  typedef struct {
    float temperature;
    float humidity;
    float compensated_temperature;
    float compensated_humidity;
    float pressure;
    float gas_resistance;
    float stabilization_status;
    float run_in_status;
    float gas_percentage;
    float iaq;
    float static_iaq;
    float co2_equivalent;
    float breath_bvoc;
    uint16_t valid;
    uint16_t new_data;
  } meas_data;
#elif (SENSOR_MODE == CLASSIFICATION)
  typedef struct {
    float temperature;
    float humidity;
    float pressure;
    float gas_resistance;
    float raw_gas_index;
    float gas_estimate_1;
    float gas_estimate_2;
    float gas_estimate_3;
    float gas_estimate_4;
    uint16_t valid;
    uint16_t new_data;
  } meas_data;
#endif

meas_data AllMeasData;
meas_data AllMeasDataCache;

system_status SystemStatus;
system_status SystemStatusCache;

unsigned long lastTimestamp;
bool updateWatchdog;
int32_t temp_compensation;
char debug_cmd;
bool print_debug;

// Communication commands for UART
#define UART_GET_MEASUREMENTS 0x20
#define UART_GET_BSEC_STATE 0x21
#define UART_GET_SYSTEM_STATE 0x22

#define UART_SET_START_MEASUREMENT 0x30
#define UART_SET_BSEC_STATE 0x31
#define UART_SET_SYSTEM_RESET 0x32
#define UART_SET_TEMP_COMP 0x33
#define UART_SET_DEBUG_MODE 0x34

// UART listening states
#define LISTEN_IDLE 0
#define LISTEN_LISTENING 1
#define LISTEN_GETTING 2
#define LISTEN_GETTING_MEASUREMENTS 3
#define LISTEN_GETTING_BSEC_STATE 4
#define LISTEN_GETTING_SYS_STATE 5
#define LISTEN_SETTING 6
#define LISTEN_SETTING_BSEC_STATE 7
#define LISTEN_SETTING_START 8
#define LISTEN_SETTING_TCOMP 9
#define LISTEN_SETTING_DEBUG 10
#define LISTEN_SETTING_RESET 11
#define LISTEN_UNINITIALIZED 12
uint8_t listenStatus = LISTEN_UNINITIALIZED;

// System operation states
#define SYSTEM_MEAS_RUNNING  1
#define SYSTEM_MEAS_WAITING  0
#define SYSTEM_MEAS_ERROR   -1

#define SYSTEM_STATE_UPDATED 1
#define SYSTEM_STATE_DEFAULT 0
#define SYSTEM_STATE_ERROR  -1

// Validity and data flags
#define MEAS_DATA_INVALID 0
#define MEAS_DATA_VALID   1

#define NO_NEW_MEAS_DATA  0
#define NEW_MEAS_DATA     1

#if (SENSOR_MODE == AIRQUALITY)
const uint8_t bsec_config[] = {
                                #include "config/bme680/bme680_iaq_33v_3s_4d/bsec_iaq.txt"
                              };
#elif (SENSOR_MODE == CLASSIFICATION)
const uint8_t bsec_config[] = {
                                #include "config/FieldAir_HandSanitizer/bsec_selectivity.txt"
                              };
#endif

/**
 * @brief : This function checks the BSEC status, prints the respective error code. Halts in case of error
 * @param[in] bsec  : Bsec2 class object
 */
void checkBsecStatus(Bsec2 bsec);

/**
 * @brief : This function is called by the BSEC library when a new output is available
 * @param[in] input     : BME68X sensor data before processing
 * @param[in] outputs   : Processed BSEC BSEC output data
 * @param[in] bsec      : Instance of BSEC2 calling the callback
 */
void newDataCallback(const bme68xData data, const bsecOutputs outputs, Bsec2 bsec);

/* Create an object of the class Async_UART_Comm */
Async_UART_Comm uart_comm;

/* Create an object of the class Bsec2 */
Bsec2 envSensor;
static uint8_t bsecState[BSEC_MAX_STATE_BLOB_SIZE];

/* Entry point for the example */
void setup(void)
{
  // first start watchdog
  updateWatchdog = true;
  wdt_init(WDT_CONFIG_PER_256);  // found to need at least _PER_64

  debug_cmd = 0;
  Serial.begin(115200);
  print_debug = false;
  
  SystemStatus.measRunning = SYSTEM_MEAS_WAITING;
  SystemStatus.stateUpdated = SYSTEM_STATE_DEFAULT;
  SystemStatus.lastBsecError = BSEC_OK;
  SystemStatus.lastSensorError = BME68X_OK;
  SystemStatus.systemUptime = 0;
  lastTimestamp = millis();

  memset(&AllMeasData, 0x00, sizeof(meas_data));
  memset(&AllMeasDataCache, 0x00, sizeof(meas_data));
  temp_compensation = 0;

  // UART communication protocol setup, must match peer setup
  if (!uart_comm.init(&Serial1, 115200, 20, 1000, &Serial)) {
    updateWatchdog = false;   // reset if UART is not initializing
  }
  uart_comm.set_debug(false);

/* Desired subscription list of BSEC2 outputs */

#if (SENSOR_MODE == AIRQUALITY)
  bsecSensor sensorList[] = {
          BSEC_OUTPUT_RAW_TEMPERATURE,
          BSEC_OUTPUT_RAW_PRESSURE,
          BSEC_OUTPUT_RAW_HUMIDITY,
          BSEC_OUTPUT_RAW_GAS,
          BSEC_OUTPUT_STABILIZATION_STATUS,
          BSEC_OUTPUT_RUN_IN_STATUS,
          BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_TEMPERATURE,
          BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_HUMIDITY,
          BSEC_OUTPUT_GAS_PERCENTAGE,
          BSEC_OUTPUT_IAQ,
          BSEC_OUTPUT_STATIC_IAQ,
          BSEC_OUTPUT_CO2_EQUIVALENT,
          BSEC_OUTPUT_BREATH_VOC_EQUIVALENT
  };
  #define BSEC_NUM_OUTPUTS 13
#elif (SENSOR_MODE == CLASSIFICATION)
  bsecSensor sensorList[] = {
          BSEC_OUTPUT_RAW_TEMPERATURE,
          BSEC_OUTPUT_RAW_PRESSURE,
          BSEC_OUTPUT_RAW_HUMIDITY,
          BSEC_OUTPUT_RAW_GAS,
          BSEC_OUTPUT_RAW_GAS_INDEX,
          BSEC_OUTPUT_GAS_ESTIMATE_1,
          BSEC_OUTPUT_GAS_ESTIMATE_2,
          BSEC_OUTPUT_GAS_ESTIMATE_3,
          BSEC_OUTPUT_GAS_ESTIMATE_4
  };
  #define BSEC_NUM_OUTPUTS 9
#endif

    Wire.begin();

    /* Valid for boards with USB-COM. Wait until the port is open */
    
    /* Initialize the library and interfaces */
    if (!envSensor.begin(BME68X_I2C_ADDR_LOW, Wire))
    {
        checkBsecStatus(envSensor);
    }

    /* Load the configuration string that stores information on how to classify the detected gas */
	if (!envSensor.setConfig(bsec_config))
    {
        checkBsecStatus (envSensor);
    }

#if (SENSOR_MODE == AIRQUALITY)
    /* Subscribe for the desired BSEC2 outputs */
    if (!envSensor.updateSubscription(sensorList, ARRAY_LEN(sensorList), BSEC_SAMPLE_RATE_LP))
    {
        checkBsecStatus (envSensor);
    }
#elif (SENSOR_MODE == CLASSIFICATION)
    /* Subscribe for the desired BSEC2 outputs */
    if (!envSensor.updateSubscription(sensorList, ARRAY_LEN(sensorList), BSEC_SAMPLE_RATE_SCAN))
    {
        checkBsecStatus (envSensor);
    }
#endif

    /* Whenever new data is available call the newDataCallback function */
    envSensor.attachCallback(newDataCallback);

    if (print_debug) { Serial.println("\nBSEC library version " + \
            String(envSensor.version.major) + "." \
            + String(envSensor.version.minor) + "." \
            + String(envSensor.version.major_bugfix) + "." \
            + String(envSensor.version.minor_bugfix)); }
}

/* Function that is looped forever */
void loop(void)
{
    uint8_t readStatus;
    /* Call the run function often so that the library can
     * check if it is time to read new data from the sensor
     * and process it.
     */

    if (SystemStatus.measRunning == SYSTEM_MEAS_RUNNING) {
      if (!envSensor.run()) {
          checkBsecStatus (envSensor);
      }
    }

    if (listenStatus == LISTEN_UNINITIALIZED) {
      if (print_debug) { Serial.println("UART Listen Status uninitialized, clearing input buffers."); }
      uart_comm.clear_buffers();
      listenStatus = LISTEN_IDLE;
    }

    if ( (listenStatus != LISTEN_GETTING_MEASUREMENTS) &&
         (AllMeasData.new_data == NEW_MEAS_DATA) ) {
      memcpy(&AllMeasDataCache, &AllMeasData, sizeof(meas_data));
      AllMeasData.new_data = NO_NEW_MEAS_DATA;
      if (print_debug) { Serial.println("Measurement data copied to UART cache."); }
    }

    if (listenStatus != LISTEN_GETTING_SYS_STATE) {
      memcpy(&SystemStatusCache, &SystemStatus, sizeof(system_status));
    }

    readStatus = uart_comm.loop_comm();

    if ((readStatus == ASYNC_UART_COMM_CLEARING) &&
        (listenStatus != LISTEN_IDLE)) {
      if (print_debug) { Serial.println("UART clearing, resetting listen status!"); }
      listenStatus = LISTEN_IDLE;
    }

    if ((readStatus == ASYNC_UART_COMM_IDLE) &&
        (listenStatus == LISTEN_IDLE)) {
      if (print_debug) { Serial.println("UART Idle, start listening."); }
      uart_comm.uart_listen(getCallback, setCallback);
      listenStatus = LISTEN_LISTENING;
    }

    if (readStatus == ASYNC_UART_COMM_OK) {
      switch (listenStatus) {
        case LISTEN_SETTING:
          if (print_debug) { Serial.println("MAIN: UART Setting done."); }
          break;
        case LISTEN_SETTING_BSEC_STATE:
          if (SystemStatus.measRunning != SYSTEM_MEAS_WAITING) {
            if (print_debug) { Serial.println("MAIN: Setting state is only allowed when measurement is waiting to start!"); }
            break;
          }
          if (print_debug) { Serial.println("MAIN: UART Getting BSEC state done."); }
          if (envSensor.setState(bsecState)) {
            if (print_debug) { Serial.println("MAIN: BSEC state set successfully."); }
            SystemStatus.stateUpdated = SYSTEM_STATE_UPDATED;
          } else {
            if (print_debug) { Serial.println("MAIN: BSEC state set error!"); }
            SystemStatus.stateUpdated = SYSTEM_STATE_ERROR;
            checkBsecStatus (envSensor);
          }
          break;
        case LISTEN_SETTING_START:
          if (SystemStatus.measRunning != SYSTEM_MEAS_WAITING) {
            if (print_debug) { Serial.println("MAIN: Measurement already running or in error state!"); }
            break;
          }
          if (print_debug) { Serial.println("MAIN: BSEC starting measurement."); }
          SystemStatus.measRunning = SYSTEM_MEAS_RUNNING;
          checkBsecStatus (envSensor);
          break;
        case LISTEN_SETTING_TCOMP:
          envSensor.setTemperatureOffset((float)(temp_compensation * 0.001));
          if (print_debug) { Serial.println("MAIN: BSEC temperature compensation set to " + String((float)(temp_compensation * 0.001))); }
          checkBsecStatus (envSensor);
          break;
        case LISTEN_SETTING_DEBUG:
          if (debug_cmd > 0) {
            print_debug = true;
            uart_comm.set_debug(true);
            Serial.println("MAIN: Debug outputs enabled.");
          } else {
            if (print_debug) { Serial.println("MAIN: Disabling debug outputs now."); }
            print_debug = false;
            uart_comm.set_debug(false);
          }
          break;
        case LISTEN_SETTING_RESET:
          if (print_debug) { Serial.println("MAIN: System reset scheduled."); }
          updateWatchdog = false;
          break;
        case LISTEN_GETTING:
          if (print_debug) { Serial.println("MAIN: UART Getting done."); }
          break;
        case LISTEN_GETTING_MEASUREMENTS:
          if (print_debug) { Serial.println("MAIN: UART Getting Measurements done."); }
          AllMeasDataCache.new_data = NO_NEW_MEAS_DATA;
          break;
        case LISTEN_GETTING_SYS_STATE:
        if (print_debug) { Serial.println("MAIN: UART Getting System State done."); }
        break;
      }
      listenStatus = LISTEN_IDLE;
    }
  unsigned long current_time = millis();
  while ((current_time - lastTimestamp) >= 1000) {    // overflow safe calculation
    if (SystemStatus.systemUptime < 0xFFFFFFFF) {     // Enough for counting a bit more than 136 years :)
      SystemStatus.systemUptime += 1;
    }
    lastTimestamp += 1000;
  }
  if (updateWatchdog) {
    wdt_reset();
  }
}

void newDataCallback(const bme68xData data, const bsecOutputs outputs, Bsec2 bsec)
{
    if (!outputs.nOutputs)
        return;

    if (print_debug) { Serial.println("BSEC outputs:\n\ttimestamp = " + String((int) (outputs.output[0].time_stamp / INT64_C(1000000)))); }
    uint8_t valid_results = 0;
	
    for (uint8_t i = 0; i < outputs.nOutputs; i++)
    {
        const bsecData output  = outputs.output[i];
        switch (output.sensor_id)
        {
            case BSEC_OUTPUT_RAW_TEMPERATURE:
                if (print_debug) { Serial.println("\ttemperature = " + String(output.signal)); }
                AllMeasData.temperature = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_RAW_PRESSURE:
                if (print_debug) { Serial.println("\tpressure = " + String(output.signal)); }
                AllMeasData.pressure = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_RAW_HUMIDITY:
                if (print_debug) { Serial.println("\thumidity = " + String(output.signal)); }
                AllMeasData.humidity = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_RAW_GAS:
                if (print_debug) { Serial.println("\tgas resistance = " + String(output.signal)); }
                AllMeasData.gas_resistance = output.signal;
                valid_results += 1;
                break;

#if (SENSOR_MODE == AIRQUALITY)
            case BSEC_OUTPUT_STABILIZATION_STATUS:
                if (print_debug) { Serial.println("\toutput stabilization status= " + String(output.signal)); }
                AllMeasData.stabilization_status = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_RUN_IN_STATUS:
                if (print_debug) { Serial.println("\trun-in status = " + String(output.signal)); }
                AllMeasData.run_in_status = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_TEMPERATURE:
                if (print_debug) { Serial.println("\tcompensated temperature = " + String(output.signal)); }
                AllMeasData.compensated_temperature = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_HUMIDITY:
                if (print_debug) { Serial.println("\tcompensated humidity = " + String(output.signal)); }
                AllMeasData.compensated_humidity = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_GAS_PERCENTAGE:
                if (print_debug) { Serial.println("\tgas percentage = " + String(output.signal)); }
                AllMeasData.gas_percentage = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_IAQ:
                if (print_debug) { Serial.println("\tIAQ = " + String(output.signal)); }
                AllMeasData.iaq = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_STATIC_IAQ:
                if (print_debug) { Serial.println("\tStatic IAQ = " + String(output.signal)); }
                AllMeasData.static_iaq = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_CO2_EQUIVALENT:
                if (print_debug) { Serial.println("\tCO2 Equivalent = " + String(output.signal)); }
                AllMeasData.co2_equivalent = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_BREATH_VOC_EQUIVALENT:
                if (print_debug) { Serial.println("\tBreath VOC Equivalent = " + String(output.signal)); }
                AllMeasData.breath_bvoc = output.signal;
                valid_results += 1;
                break;

#elif (SENSOR_MODE == CLASSIFICATION)
            case BSEC_OUTPUT_RAW_GAS_INDEX:
                if (print_debug) { Serial.println("\tgas index = " + String(output.signal)); }
                AllMeasData.raw_gas_index = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_GAS_ESTIMATE_1:
                if (print_debug) { Serial.println("\taccuracy = " + String(output.accuracy)); }
                if (print_debug) { Serial.println("\tclass 1 probability : " + String(output.signal * 100) + "%"); }
                AllMeasData.gas_estimate_1 = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_GAS_ESTIMATE_2:
                if (print_debug) { Serial.println("\tclass 2 probability : " + String(output.signal * 100) + "%"); }
                AllMeasData.gas_estimate_2 = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_GAS_ESTIMATE_3:
                if (print_debug) { Serial.println("\tclass 3 probability : " + String(output.signal * 100) + "%"); }
                AllMeasData.gas_estimate_3 = output.signal;
                valid_results += 1;
                break;
            case BSEC_OUTPUT_GAS_ESTIMATE_4:
                if (print_debug) { Serial.println("\tclass 4 probability : " + String(output.signal * 100) + "%"); }
                AllMeasData.gas_estimate_4 = output.signal;
                valid_results += 1;
                break;
#endif
            default:
                break;
        }
    }
    if (valid_results == BSEC_NUM_OUTPUTS) {
      AllMeasData.valid = MEAS_DATA_VALID;
    } else {
      AllMeasData.valid = MEAS_DATA_INVALID;
    }
    AllMeasData.new_data = NEW_MEAS_DATA;
}

void checkBsecStatus(Bsec2 bsec)
{
    SystemStatus.lastBsecError = bsec.status;
    SystemStatus.lastSensorError = bsec.sensor.status;

    if (bsec.status < BSEC_OK)
    {
        if (print_debug) { Serial.println("BSEC error code : " + String(bsec.status)); }
        SystemStatus.measRunning = SYSTEM_MEAS_ERROR;
    } else if (bsec.status > BSEC_OK)
    {
        if (print_debug) { Serial.println("BSEC warning code : " + String(bsec.status)); }
    }

    if (bsec.sensor.status < BME68X_OK)
    {
        if (print_debug) { Serial.println("BME68X error code : " + String(bsec.sensor.status)); }
        SystemStatus.measRunning = SYSTEM_MEAS_ERROR;
    } else if (bsec.sensor.status > BME68X_OK)
    {
        if (print_debug) { Serial.println("BME68X warning code : " + String(bsec.sensor.status)); }
    }
}

// Callback for UART SET commands
bool setCallback(char** dst, uint16_t* exp_max_size, uint16_t** recv_size, char setID) {
  if (print_debug) { Serial.println("UART SET Callback. SetID: " + String((uint8_t)setID)); }
  *recv_size = NULL; // use fixed size only here
  switch (setID) {
    case UART_SET_BSEC_STATE:
      if (SystemStatus.measRunning != SYSTEM_MEAS_WAITING) {  // when running or in error, don't change the state any more
        return false;
      }
      *dst = (char*)bsecState;
      *exp_max_size = BSEC_MAX_STATE_BLOB_SIZE;
      listenStatus = LISTEN_SETTING_BSEC_STATE;
      return true;
    case UART_SET_START_MEASUREMENT:
      *dst = NULL;
      *exp_max_size = 0;
      if (SystemStatus.measRunning == SYSTEM_MEAS_WAITING) {  // issue command only when waiting for it (not running, no error)
        listenStatus = LISTEN_SETTING_START;
      }
      return true;
    case UART_SET_TEMP_COMP:
      *dst = (char*)&temp_compensation;  // temp_compensation --> int32_t
      *exp_max_size = sizeof(int32_t);
      listenStatus = LISTEN_SETTING_TCOMP;
      return true;
    case UART_SET_DEBUG_MODE:
      *dst = &debug_cmd;
      *exp_max_size = sizeof(char);
      listenStatus = LISTEN_SETTING_DEBUG;
      return true;
    case UART_SET_SYSTEM_RESET:
      *dst = NULL;
      *exp_max_size = 0;
      listenStatus = LISTEN_SETTING_RESET;
      return true;
    default:
      *dst = NULL;
      *exp_max_size = 0;
      listenStatus = LISTEN_IDLE;
      return false;
  }
}

// Callback for UART GET commands
bool getCallback(char** src, uint16_t* size, char getID) {
  if (print_debug) { Serial.println("UART GET Callback. GetID: " + String((uint8_t)getID)); }
  switch (getID) {
    case UART_GET_MEASUREMENTS:
      *src = (char*)&AllMeasDataCache;
      *size = sizeof(meas_data);
      listenStatus = LISTEN_GETTING_MEASUREMENTS;
      return true;
    case UART_GET_BSEC_STATE:
      if (!envSensor.getState(bsecState))
        return false;
      *src = (char*)bsecState;
      *size = BSEC_MAX_STATE_BLOB_SIZE;
      listenStatus = LISTEN_GETTING_BSEC_STATE;
      return true;
    case UART_GET_SYSTEM_STATE:
      *src = (char*)&SystemStatusCache;
      *size = sizeof(system_status);
      listenStatus = LISTEN_GETTING_SYS_STATE;
      return true;
    default:
      *src = NULL;
      *size = 0;
      listenStatus = LISTEN_IDLE;
      return false;
  }
}
