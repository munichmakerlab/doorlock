# Doorlock Frontend
Arduino-based frontend for the MuMaLab hackerspace doorlock.

It's supposed to use a LCD, a 3x4 keypad and a RFID reader. That's too much pins for the Arduino Uno, so for now, there's no LCD. Instead, display output is send to the serial port, which will later also be used for communication with the backend.

## Libraries
* RFID Reader: https://github.com/miguelbalboa/rfid
* Keypad: http://playground.arduino.cc/code/Keypad