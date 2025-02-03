#include <Arduino.h>
#include <SPI.h>
#include "SoftwareSerial.h"

#define INT 4  // Interrupt pin to start data transfer
#define INH1 9 // U1 INH pin, (INH LOW = OUTPUT ACTIVE)

uint8_t inCmd;

SoftwareSerial mySerial(2, 3); // Use pin 2 for RX, TX is unused

// SPI codes to send to shift register
const uint8_t chan[13] = 
{ 0b11111111, 
  0b11111100, 
  0b11111101, 
  0b11111110,
  0b11111111,
  0b01110011,
  0b01110111,
  0b01111011,
  0b01111111,
  0b10001111,
  0b10011111,
  0b10101111,
  0b10111111 };

float readings[12];
float maxCode = pow(2, 24); // maximum ADC code

void writeValues(){

  for(uint8_t i = 0; i < 12; i++){

    Serial.print(readings[i], 8);

    if (i < 11)
      Serial.print("\t");
    else 
      Serial.print("\n");

  }
  
}
  
void setChannel(uint8_t chanNum) {

  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
  SPI.transfer(chan[chanNum]);
  SPI.endTransaction();
  digitalWrite(SS, HIGH);
  digitalWrite(SS, LOW);
  if (chanNum > 0 && chanNum < 5)
    digitalWrite(INH1, LOW);
  else
    digitalWrite(INH1, HIGH);

}

void readSensors() {

  for(uint8_t i = 1; i < 13; i++){
  
    setChannel(i); // set channel to communicate with

    // clear anything out of the buffer
    while (mySerial.available() > 0) {
      mySerial.read();
    }

    digitalWrite(INT, LOW);  // trigger sensor to transfer data
    delayMicroseconds(100);  // make sure the interrupt will trigger
    digitalWrite(INT, HIGH);
    
    uint8_t bytesReceived = 0;
    uint8_t inBytes[4];
    bool timeout = false;
    uint32_t adcCode = 0;
    uint32_t time = millis();

    // read in 4 bytes from sensor or timeout
    while (bytesReceived < 4 && timeout == false) {

      if (mySerial.available() > 0){

        inBytes[bytesReceived] = mySerial.read();
        bytesReceived++;

      } else if (millis() >= time + 10UL){

        timeout = true;

      }

    }

    // convert ADC code to magnetic field in uT
    if (timeout){

      readings[i-1] = 999.;

    } else {

      adcCode += ((uint32_t)inBytes[0] << 24) + ((uint32_t)inBytes[1] << 16) + ((uint32_t)inBytes[2] << 8) + (uint32_t)inBytes[3];

      if (adcCode & 0x20000000){

        adcCode &= 0x1FFFFFE0;
        adcCode >>= 5;
        readings[i-1] = 250.0 * (float)adcCode / maxCode;

      } else {

        adcCode &= 0x1FFFFFE0;
        adcCode >>=5;
        readings[i-1] = 250.0 * ((float)adcCode / maxCode - 1);

      }

    }

  }

  setChannel(chan[0]); // disconnect all sensors

}

void setup() {
  
  Serial.begin(115200);
  Serial.setTimeout(5);
  mySerial.begin(9600);
  SPI.begin();
  pinMode(INT, OUTPUT);
  pinMode(INH1, OUTPUT);
  digitalWrite(INT, HIGH);  // Idles high
  digitalWrite(INH1, HIGH); // Disable U1 output
  digitalWrite(SS, LOW);    // Drive high to latch 595 output
  setChannel(chan[0]);      // Disable all 4052 outputs

}

void loop() {

  // wait for an R to read and transmit the sensor values
  if (Serial.available() > 0){

    inCmd = Serial.read();

    if(inCmd == 'R') {

      readSensors();
      writeValues();

    } else if(inCmd == 'I') {

      Serial.println("Magnetometer Controller");

    }

  }

}
