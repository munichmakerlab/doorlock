import sqlite3
import serial
from threading import Timer
import logging
import hashlib
import os.path

# config 
DATABASE = 'doorlock.db'
SERIAL_PORT = '/dev/ttyACM0'
DEBUG = False

if os.path.exists("COM8"):
	SERIAL_PORT = 'COM8'
	DEBUG = True

# regular ping to frontend, every 10 seconds
# TODO: Add timeout
running = True
def ping():
	if not running:
		return
	ser.write("PING;\n")
	ser.flush()
	t = Timer(10.0,ping)
	t.start()

def statusChange():
	if lock.isUnlocked():
		ser.write("STATUS,1;\n")
	else:
		ser.write("STATUS,0;\n")
	ser.flush()

def create_hash(text):
	h = hashlib.sha256()
	h.update(text)
	return h.hexdigest()

# get logger
logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level = logging.INFO)
logger = logging.getLogger("doorlock")
logger.info("Starting doorlock backend")

# instantiate db connection
conn = sqlite3.connect(DATABASE)
c = conn.cursor()	
logger.debug("Database opened")

# connect to serial port
ser = serial.Serial(SERIAL_PORT)
logger.debug("Serial port to frontend opened")

# lock implementation
if DEBUG:
	from simlock import SimLock
	lock = SimLock()
else:
	from motorlock import MotorLock
	lock = MotorLock()
lock.onStatusChange += statusChange

# start pinging frontend
ping()

while 1 == 1:
	try:
		a = ser.readline()
		b = a.rstrip("\n\r;").split(",")
		
		# Unlock command: "UNLOCK,<token>,<pin>;"
		# Reply with "ACK;" or "NAK;"
		if b[0] == "UNLOCK":
			t = (b[1],create_hash(b[2]))
			c.execute('SELECT p.name from dl_tokens t JOIN dl_persons p ON t.person_id = p.id WHERE t.token=? AND t.pin=? AND p.disabled =0', t)
			r = c.fetchone()
			if r != None:
				logger.warning("Valid unlock request by %s (%s)",r[0], t[0])
				ser.write("ACK;\n")
				lock.unlock()
			else:
				logger.error("Invalid unlock request (%s, %s)", t[0], b[2])
				ser.write("NAK;\n")
			ser.flush()
		
		# Lock command "LOCK;"
		# no reply expected by frontend
		elif b[0] == "LOCK":
			logger.warning("Lock request");
			lock.lock()
		
		# reply to ping: "PONG;"
		# passing status to frontend afterwards
		elif b[0] == "PONG":
			if lock.isUnlocked():
				ser.write("STATUS,1;\n")
			else:
				ser.write("STATUS,0;\n")
			ser.flush()
	
	except KeyboardInterrupt:
		print "Received keyboard interrupt. Stopping..."
		running = False
		break		  
