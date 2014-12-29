import sqlite3
import serial
from threading import Timer

door_unlocked = False;

conn = sqlite3.connect('doorlock.db')
c = conn.cursor()	

ser = serial.Serial("/dev/ttyACM0")

def ping():
	ser.write("PING;\n")
	ser.flush()
	t = Timer(10.0,ping)
	t.start() 

ping()

while 1 == 1:
	a = ser.readline()
	b = a.rstrip("\n\r;").split(",")
	if b[0] == "UNLOCK":
		t = (b[1],b[2])
		c.execute('SELECT p.name from dl_tokens t JOIN dl_persons p ON t.person_id = p.id WHERE t.token=? AND t.pin=?', t)
		r = c.fetchone()
		if r != None:
			ser.write("ACK;\n")
			door_unlocked = True;
			print("Door unlocked by " + r[0] + "(" + t[0] + ")")
		else:
			ser.write("NAK;\n")
			print("Unlocking failed (" + t[0] + "," + t[1] + ")")
		ser.flush()
	elif b[0] == "LOCK":
		door_unlocked = False;
		print("Door locked");
	elif b[0] == "PONG":
		if door_unlocked:
			ser.write("PONG,1;\n")
		else:
			ser.write("PONG,0;\n")
