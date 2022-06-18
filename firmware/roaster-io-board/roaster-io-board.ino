#include <max6675.h>
#include <Wire.h>
#include <EEPROM.h>

#define SLAVE_ADDRESS 0x08

#define TC1_CS 10
#define TC2_CS 9
#define SCK 13
#define MISO 12
#define HEATER A0
#define FAN A1


byte i2cMessageIn[3];
byte roasterState = 0; // 1- idle 2- roasting 3- cooling 4- error

MAX6675 thermocouple_1(SCK, TC1_CS, MISO);
MAX6675 thermocouple_2(SCK, TC2_CS, MISO);

double temp_sensor_1 = 0;
double temp_sensor_2 = 0;
double temperature = 0;
int setpointTemp = 0;

void setup() 
{
  Serial.begin(115200);
  Wire.begin(SLAVE_ADDRESS);

  Wire.onReceive(receiveData);
  Wire.onRequest(sendData);

  pinMode(HEATER, OUTPUT);
  pinMode(FAN, OUTPUT);

  digitalWrite(HEATER, LOW);
  digitalWrite(FAN, LOW);

  Serial.println("Setup complete");
//  EEPROM.update(0, 230);
  setpointTemp = EEPROM.read(0);
  Serial.println(setpointTemp);

}

void loop() {

  temp_sensor_1 = thermocouple_1.readCelsius();
  temp_sensor_2 = thermocouple_2.readCelsius();

  if (temp_sensor_1 > temp_sensor_2) 
  {
    temperature = temp_sensor_1;
  }
  else {
    temperature = temp_sensor_2;
  }
  
//  temperature = (temp_sensor_1 + temp_sensor_2) / 2;

//  if (abs(temp_sensor_1 - temp_sensor_2) > 15)
//  {
//      Serial.println("temp sensor mismatch");
//      roasterState = 99;
//  }
  
  Serial.print("Temp: ");
  Serial.println(temperature);
  
  switch(roasterState)
  {
    case 0: // idle
      digitalWrite(HEATER, LOW);
      digitalWrite(FAN, LOW);
      
      break;
      
    case 1: // start roast
      Serial.println("Start roast");
      digitalWrite(HEATER, HIGH);
      digitalWrite(FAN, HIGH);
      roasterState = 2;
      EEPROM.update(0, setpointTemp);
      break;
      
    case 2: // roasting
      Serial.println("Roasting");
      if (temperature >= setpointTemp)
      {
        Serial.println("Roasting – setpoint hit");
        digitalWrite(HEATER, LOW);
        roasterState = 3; // cooling
      }
      break;
      
    case 3:
      digitalWrite(HEATER, LOW);
      Serial.println("Cooling");
      if (temperature <= 60)
      {
        Serial.println("Cooling - stopped");
        digitalWrite(FAN, LOW);
        roasterState = 0; // idle
      }
      break;

    case 99:
      digitalWrite(HEATER, LOW);
      digitalWrite(FAN, LOW);
      Serial.println("Temp sensor mismatch!");
      Serial.println(temp_sensor_1);
      Serial.println(temp_sensor_2);
      
      if (abs(temp_sensor_1 - temp_sensor_2) < 10)
      {
        Serial.println("Temp sensors agree again!");
        Serial.println(temp_sensor_1);
        Serial.println(temp_sensor_2);
        roasterState = 0; // idle
      }
      break;
      
    default:
      Serial.println("Hit default case");
      
      digitalWrite(HEATER, LOW);
      digitalWrite(FAN, LOW);
      break;
  }
  delay(1000);
}

void receiveData(int bytecount)
{  
  for (int i = 0; i < bytecount; i++) {
    i2cMessageIn[i] = Wire.read();
//    Serial.print("I2C Message In: ");
//    Serial.println(i2cMessageIn[i], HEX);
  }

//  Serial.print("I2C Message In: ");
//  Serial.println(i2cMessageIn, HEX);
  
  handleMessage();
  
}

void handleMessage()
{

  switch (i2cMessageIn[0]) {
    case 1: // get status
//      Serial.println("Status requested");
      break;
    case 2: // start roast
      Serial.println("Start roast requested");
      setpointTemp = i2cMessageIn[1];
//      Serial.println(i2cMessageIn);
//      Serial.print("Set temp: ");
//      Serial.println(setpointTemp);
      roasterState = 1;
      break;
    case 3: // cancel roast
      Serial.println("cancel roast requested");
      roasterState = 3;
      break;
    case 4: // cancel cooling
      Serial.println("cancel cooling requested");
      roasterState = 0;
      break;
  }
  
}

void sendData()
{

  switch (i2cMessageIn[0]) {
    case 1: // get status
//      Serial.print("Status response: ");
//      Serial.println((int)temperature);
      Wire.write((int)temperature);
      Wire.write(roasterState);
      break;
    case 2: // start roast
      Serial.println("Start roast response");
      Wire.write(0x33);
      break;
    case 3: // cancel roast
      Serial.println("Cancel roast requested");
      Wire.write(0x34);
      break;
    case 4: // cancel roast
      Serial.println("Cancel cooling requested");
      Wire.write(0x35);
      break;
    case 5: // get saved temp setpoint
      Serial.print("Setpoint requested:");
      Serial.println(setpointTemp);
      Wire.write(setpointTemp);
      break;
  }

}
