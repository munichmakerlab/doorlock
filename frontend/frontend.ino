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
  {'7','8','9'},
  {'4','5','6'},
  {'1','2','3'},
  {'E','0','P'}
};
byte rowPins[ROWS] = {5, 4, 3, 2}; //connect to the row pinouts of the keypad
byte colPins[COLS] = {8, 7, 6}; //connect to the column pinouts of the keypad

Keypad keypad = Keypad( makeKeymap(keys), rowPins, colPins, ROWS, COLS );

#include <LiquidCrystal.h>
LiquidCrystal lcd(A3, A2, A1, A0, A5, A4);

States state = LOCKED;
long timeout_start = 0;
long timeout = 10000;

String serial_buffer = "";
String serial_unfinished_line = "";
String buffer = "";

int Epin = A7;

void updateDisplay() {
  lcd.clear();
  if (state == LOCKED) {
    lcd.print("You shall not pass! ");
    lcd.setCursor(0, 1);
    lcd.print("                    ");
  } else if (state == SEMI_LOCKED) {
    lcd.print("It's open...        ");
    lcd.setCursor(0, 1);
    lcd.print("Press E to enter :)");
  } else if (state == PIN_ENTRY) {
    lcd.print("Enter PIN & press P ");
    lcd.setCursor(0, 1);
    for (int i = 0; i < buffer.length(); i++) {
      lcd.print("*");
    }
  } else if (state == WAIT_FOR_UNLOCK) {
    lcd.print("Waiting for         ");
    lcd.setCursor(0, 1);
    lcd.print("       confirmation ");
  } else if (state == INVALID_PIN) {
    lcd.print("  > Invalid PIN <   ");
    lcd.setCursor(0, 1);
    lcd.print("> Please try again <");
  } else if (state == UNLOCKED) {
    lcd.print("It's open...        ");
    lcd.setCursor(0, 1);
    lcd.print("Just come on in! =) ");
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

bool checkE() {
 if (analogRead(Epin) < 1000) {
   return true;
 }
 return false;
}

void callRing() {

  Serial.print("RING;");

  lcd.clear();
  lcd.print("Ding     Ding     Ding     Ding     Ding");
  lcd.setCursor(5, 1);
  lcd.print("Dong     Dong     Dong     Dong");

  for (int positionCounter = 0; positionCounter < 20; positionCounter++) {
    lcd.scrollDisplayLeft();
    delay(200);
  }

  updateDisplay();
}

void setup() {
  lcd.begin(20, 2);
  lcd.print("Booting....");
  delay(500);

  Serial.begin(9600);		// Initialize serial communications with the PC

  SPI.begin();			// Init SPI bus
  mfrc522.PCD_Init();		// Init MFRC522

  updateDisplay();
}


void loop() {
  if (Serial.available() > 0) {
    byte incomingByte = Serial.read();
    if (incomingByte == '\n') {
      if (serial_unfinished_line == "PING;") {
        Serial.println("PONG;");
      } else if (serial_unfinished_line.startsWith("STATUS,")) {
        String tmp = serial_unfinished_line.substring(7,8);
        if (tmp == "0") {
          if (state != LOCKED) {
            setState(LOCKED);
          }
        } else if (tmp == "1") {
          if (state != UNLOCKED) {
            setState(UNLOCKED);
          }
        } else if (tmp == "2") {
          if (state != SEMI_LOCKED) {
            setState(SEMI_LOCKED);
          }
        }
      } else {
        serial_buffer = serial_unfinished_line;
      }
      serial_unfinished_line = "";
    } else {
      serial_unfinished_line += (char)incomingByte;
    }
  }

  if (state == SEMI_LOCKED) {
    if ( checkE() ) {
      Serial.print("SEMI_UNLOCK;");
      timeout_start = millis();
    }
  } else if (state == LOCKED) {
    if ( checkE() ) {
      callRing();
    }

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
      if (key == 'P' || key == 'E') {
        Serial.print("UNLOCK,");
        char tmp[16];
        for (byte i = 0; i<mfrc522.uid.size; i++) {
          sprintf(tmp,"%.2X",mfrc522.uid.uidByte[i]);
          Serial.print(tmp);
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
    if (serial_buffer != "") {
      if (serial_buffer == "ACK;") {
        setState(UNLOCKED);
      } else {
        setState(INVALID_PIN);
      }
      serial_buffer = "";
    } else if (timeoutExpired()) {
      setState(LOCKED);
    }
  } else if (state == UNLOCKED) {
    if ( checkE() ) {
      callRing();
    }

    char key = keypad.getKey();

    if (key) {
      if (key == 'P' || key == 'E') {
        if (buffer == "0") {
          Serial.println("LOCK;");
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
    char key = keypad.getKey();
    if (key) {
      setState(PIN_ENTRY);
      buffer += key;
      updateDisplay();
    } else if (timeoutExpired()) {
      setState(LOCKED);
    }
  } else {
    Serial.println("state not implemented");
    delay(1000);
  }
}
