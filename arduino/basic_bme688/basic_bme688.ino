#include "bsec.h"

/* Configure the BSEC library with information about the sensor
    18v/33v = Voltage at Vdd. 1.8V or 3.3V
    3s/300s = BSEC operating mode, BSEC_SAMPLE_RATE_LP or BSEC_SAMPLE_RATE_ULP
    4d/28d = Operating age of the sensor in days
    generic_18v_3s_4d
    generic_18v_3s_28d
    generic_18v_300s_4d
    generic_18v_300s_28d
    generic_33v_3s_4d
    generic_33v_3s_28d
    generic_33v_300s_4d
    generic_33v_300s_28d
*/
const uint8_t bsec_config_iaq[] = {
#include "config/generic_33v_3s_4d/bsec_iaq.txt"
};


// Helper functions declarations
void checkIaqSensorStatus(void);

// Create an object of the class Bsec
Bsec iaqSensor;

String output;

// Entry point for the example
void setup(void)
{
  /* Initializes the Serial communication */
  Serial.begin(115200);
  Serial1.begin(115200);
  delay(1000);

  iaqSensor.begin(BME68X_I2C_ADDR_LOW, Wire);
  output = "\nBSEC library version " + String(iaqSensor.version.major) + "." + String(iaqSensor.version.minor) + "." + String(iaqSensor.version.major_bugfix) + "." + String(iaqSensor.version.minor_bugfix);
  Serial.println(output);
  checkIaqSensorStatus();

  iaqSensor.setConfig(bsec_config_iaq);
  checkIaqSensorStatus();

  bsec_virtual_sensor_t sensorList[13] = {
    BSEC_OUTPUT_IAQ,
    BSEC_OUTPUT_STATIC_IAQ,
    BSEC_OUTPUT_CO2_EQUIVALENT,
    BSEC_OUTPUT_BREATH_VOC_EQUIVALENT,
    BSEC_OUTPUT_RAW_TEMPERATURE,
    BSEC_OUTPUT_RAW_PRESSURE,
    BSEC_OUTPUT_RAW_HUMIDITY,
    BSEC_OUTPUT_RAW_GAS,
    BSEC_OUTPUT_STABILIZATION_STATUS,
    BSEC_OUTPUT_RUN_IN_STATUS,
    BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_TEMPERATURE,
    BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_HUMIDITY,
    BSEC_OUTPUT_GAS_PERCENTAGE
  };

  iaqSensor.updateSubscription(sensorList, 13, BSEC_SAMPLE_RATE_LP);
  checkIaqSensorStatus();

  // Print the header
  output = "Timestamp [ms], IAQ, IAQ accuracy, Static IAQ, CO2 equivalent, breath VOC equivalent, raw temp[°C], pressure [hPa], raw relative humidity [%], gas [Ohm], Stab Status, run in status, comp temp[°C], comp humidity [%], gas percentage";
  Serial.println(output);
}

// Function that is looped forever
void loop(void)
{
  if (Serial1.available()) {
    int inByte = Serial1.read();
    Serial.write(inByte);
  }
  unsigned long time_trigger = millis();
  if (iaqSensor.run()) { // If new data is available
    output = "{\"TS\": " + String(time_trigger) + ", ";
    output += "\"IAQ\": " + String(iaqSensor.iaq) + ", ";
    output += "\"IAQA\": " + String(iaqSensor.iaqAccuracy) + ", ";
    output += "\"IAQS\": " + String(iaqSensor.staticIaq) + ", ";
    output += "\"CO2E\": " + String(iaqSensor.co2Equivalent) + ", ";
    output += "\"bVOCE\": " + String(iaqSensor.breathVocEquivalent) + ", ";
    output += "\"RT\": " + String(iaqSensor.rawTemperature) + ", ";
    output += "\"PR\": " + String(iaqSensor.pressure) + ", ";
    output += "\"RH\": " + String(iaqSensor.rawHumidity) + ", ";
    output += "\"GO\": " + String(iaqSensor.gasResistance) + ", ";
    output += "\"ST\": " + String(iaqSensor.stabStatus) + ", ";
    output += "\"RI\": " + String(iaqSensor.runInStatus) + ", ";
    output += "\"CT\": " + String(iaqSensor.temperature) + ", ";
    output += "\"CH\": " + String(iaqSensor.humidity) + ", ";
    output += "\"GP\": " + String(iaqSensor.gasPercentage) + "}";
    Serial.println(output);
    Serial1.println(output);
  } else {
    checkIaqSensorStatus();
  }
}

// Helper function definitions
void checkIaqSensorStatus(void)
{
  if (iaqSensor.bsecStatus != BSEC_OK) {
    if (iaqSensor.bsecStatus < BSEC_OK) {
      output = "BSEC error code : " + String(iaqSensor.bsecStatus);
      Serial.println(output);
    } else {
      output = "BSEC warning code : " + String(iaqSensor.bsecStatus);
      Serial.println(output);
    }
  }

  if (iaqSensor.bme68xStatus != BME68X_OK) {
    if (iaqSensor.bme68xStatus < BME68X_OK) {
      output = "BME68X error code : " + String(iaqSensor.bme68xStatus);
      Serial.println(output);
    } else {
      output = "BME68X warning code : " + String(iaqSensor.bme68xStatus);
      Serial.println(output);
    }
  }
}


void loadState(void)
{
  if (EEPROM.read(0) == BSEC_MAX_STATE_BLOB_SIZE) {
    // Existing state in EEPROM
    Serial.println("Reading state from EEPROM");

    for (uint8_t i = 0; i < BSEC_MAX_STATE_BLOB_SIZE; i++) {
      bsecState[i] = EEPROM.read(i + 1);
      Serial.println(bsecState[i], HEX);
    }

    iaqSensor.setState(bsecState);
    checkIaqSensorStatus();
  } else {
    // Erase the EEPROM with zeroes
    Serial.println("Erasing EEPROM");

    for (uint8_t i = 0; i < BSEC_MAX_STATE_BLOB_SIZE + 1; i++)
      EEPROM.write(i, 0);

    EEPROM.commit();
  }
}

void updateState(void)
{
  bool update = false;
  if (stateUpdateCounter == 0) {
    /* First state update when IAQ accuracy is >= 3 */
    if (iaqSensor.iaqAccuracy >= 3) {
      update = true;
      stateUpdateCounter++;
    }
  } else {
    /* Update every STATE_SAVE_PERIOD minutes */
    if ((stateUpdateCounter * STATE_SAVE_PERIOD) < millis()) {
      update = true;
      stateUpdateCounter++;
    }
  }

  if (update) {
    iaqSensor.getState(bsecState);
    checkIaqSensorStatus();

    Serial.println("Writing state to FRAM");
    fram.writeEnable(true);
    fram.write(0x1, bsecState, BSEC_MAX_STATE_BLOB_SIZE);
    fram.write8(0x0, BSEC_MAX_STATE_BLOB_SIZE);
    fram.writeEnable(false);

    // for (uint8_t i = 0; i < BSEC_MAX_STATE_BLOB_SIZE ; i++) {
    //  fram.write8(i + 1, bsecState[i]);
    //  Serial.println(bsecState[i], HEX);
    //}

    for (uint8_t i = 0; i < BSEC_MAX_STATE_BLOB_SIZE ; i++) {
    Serial.println(fram.read8(i + 1), HEX);
    }
  }
}


