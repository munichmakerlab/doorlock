/* Typical pin layout used:
 * ------------------------------------------------------------
 *             MFRC522      Arduino       Arduino   Arduino
 *             Reader/PCD   Uno           Mega      Nano v3
 * Signal      Pin          Pin           Pin       Pin
 * ------------------------------------------------------------
 * RST/Reset   RST          9             5         D9
 * SPI SS      SDA(SS)      10            53        D10
 * SPI MOSI    MOSI         11 / ICSP-4   51        D11
 * SPI MISO    MISO         12 / ICSP-1   50        D12
 * SPI SCK     SCK          13 / ICSP-3   52        D13
 */

#include "states.h"

#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN		9		// 
#define SS_PIN		10		//

MFRC522 mfrc522(SS_PIN, RST_PIN);	// Create MFRC522 instance

#include <Keypad.h>

const byte ROWS = 4; //four rows
const byte COLS = 3; //three columns
char keys[ROWS][COLS] = {
  {'1','2','3'},
  {'4','5','6'},
  {'7','8','9'},
  {'*','0','#'}
};
byte rowPins[ROWS] = {5, 4, 3, 2}; //connect to the row pinouts of the keypad
byte colPins[COLS] = {8, 7, 6}; //connect to the column pinouts of the keypad

Keypad keypad = Keypad( makeKeymap(keys), rowPins, colPins, ROWS, COLS );

States state = LOCKED;
long timeout_start = 0;
long timeout = 10000;

String buffer = "";

void updateDisplay() {
  if (state == LOCKED) {
    Serial.println("+--------------------+");
    Serial.println("|                    |");
    Serial.println("| Hello Stranger!    |");
    Serial.println("|   Door is locked.  |");
    Serial.println("|                    |");
    Serial.println("+--------------------+");
  } else if (state == PIN_ENTRY) {
    Serial.println("+--------------------+");
    Serial.println("|Entry token read.   |");
    Serial.println("|Please enter PIN:   |");
    Serial.print("| ");
    for (int i = 0; i < buffer.length(); i++) {
      Serial.print("*");
    }
    for (int i = 0; i < 18-buffer.length(); i++) {
      Serial.print(" ");
    }
    Serial.println(" |");
    Serial.println("|                    |");
    Serial.println("+--------------------+");
  } else if (state == WAIT_FOR_UNLOCK) {
    Serial.println("+--------------------+");
    Serial.println("|                    |");
    Serial.println("| Waiting for        |");
    Serial.println("|       unlocking    |");
    Serial.println("|                    |");
    Serial.println("+--------------------+");
  } else if (state == INVALID_PIN) {
    Serial.println("+--------------------+");
    Serial.println("|                    |");
    Serial.println("| Invalid PIN        |");
    Serial.println("|   Pleas try again. |");
    Serial.println("|                    |");
    Serial.println("+--------------------+");
  } else if (state == UNLOCKED) {
    Serial.println("+--------------------+");
    Serial.println("|     Welcome!       |");
    Serial.println("| The space is open. |");
    Serial.println("|                    |");
    Serial.println("| Press 0# to lock.  |");
    Serial.println("+--------------------+");
  }
}

bool timeoutExpired() {
  return (millis() - timeout_start > timeout);
}

void resetTimeout() {
  timeout_start = millis();
}

void setState(States new_state) {
  state = new_state;
  buffer = "";
  updateDisplay();
  resetTimeout();
}

void setup() {
  Serial.begin(9600);		// Initialize serial communications with the PC
  SPI.begin();			// Init SPI bus
  mfrc522.PCD_Init();		// Init MFRC522
  updateDisplay();
}

void loop() {
  if (state == LOCKED) {
    // Look for new cards
    if ( ! mfrc522.PICC_IsNewCardPresent()) {
      return;
    }
    // Select one of the cards
    if ( ! mfrc522.PICC_ReadCardSerial()) {
      return;
    }
    mfrc522.PICC_HaltA();
    
    buffer = "";
    setState(PIN_ENTRY);
    
  } else if (state == PIN_ENTRY) {  
    char key = keypad.getKey();
    
    if (key) {
      if (key == '#' || key == '*') {
        Serial.print("UNLOCK,");
        for (byte i = 0; i<mfrc522.uid.size; i++) {
          Serial.print(mfrc522.uid.uidByte[i],HEX);
        }
        Serial.print(",");
        Serial.print(buffer);
        Serial.print(";");
        Serial.println();
        setState(WAIT_FOR_UNLOCK);        
      } else {
        buffer += key;
        updateDisplay();
        timeout_start = millis();
      }
    } else {
      if (timeoutExpired()) {
        setState(LOCKED);
      }
    }
  } else if (state == WAIT_FOR_UNLOCK) {
    if (Serial.available() > 0) {
      byte incomingByte = Serial.read();
      if (incomingByte == '\n') {
        Serial.println(buffer);
        if (buffer == "ACK;") {
          setState(UNLOCKED);
        } else {
          setState(INVALID_PIN);
        }
      } else {
        buffer += (char)incomingByte;
        resetTimeout();
      }
    } else if (timeoutExpired()) {
      setState(LOCKED);
    }
  } else if (state == UNLOCKED) {
    char key = keypad.getKey();
    
    if (key) {
      if (key == '#' || key == '*') {
        if (buffer == "0") {
          Serial.print("LOCK;");
          setState(LOCKED);
        }        
      } else {
        buffer += key;
        timeout_start = millis();
      }
    } else if (buffer.length() > 0 && timeoutExpired()) {
      buffer = "";
    }
  } else if (state == INVALID_PIN) {
    if (timeoutExpired()) {
      setState(LOCKED);
    }
  } else {
    Serial.println("state not implemented");
    delay(1000);
  }
      /*
      // Dump debug info about the card; PICC_HaltA() is automatically called
        for (byte i = 0; i<mfrc522.uid.size; i++) {
          Serial.print(mfrc522.uid.uidByte[i],HEX);
        }
        mfrc522.PICC_HaltA();
        Serial.println();
        */
}
