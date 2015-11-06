#!/usr/bin/env python

import sqlite3
import serial
from threading import Timer
import logging
import hashlib
import os.path
from time import sleep
from datetime import datetime, timedelta
from sys import exit
import paho.mqtt.client as paho

import config

DIR = os.path.dirname(os.path.realpath(__file__))

# config
DATABASE = DIR + '/doorlock.db'
SERIAL_PORTS = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2', '/dev/ttyUSB3']
DEBUG = False
LOG_FILENAME = DIR + "/doorlock.log"
LOG_LEVEL = logging.INFO # Could be e.g. "DEBUG" or "WARNING"
PONG_TIMEOUT = 30  #in sec

if os.path.exists("COM8"):
    SERIAL_PORT = 'COM8'
    DEBUG = True

# regular ping to frontend, every 10 seconds, 30 sec timeout
running = True


def ping():
    if not running:
        return
    ser.write("PING;\n")
    ser.flush()
    timer = Timer(10.0, ping)
    timer.start()


def statusChange():
    if lock.isUnlocked():
        ser.write("STATUS,1;\n")
        mqttc.publish(config.topic, "1", 1, True)
    else:
        ser.write("STATUS,0;\n")
        mqttc.publish(config.topic, "0", 1, True)
    ser.flush()


def create_hash(text):
    h = hashlib.sha256()
    h.update(text)
    return h.hexdigest()


def ring_doorbell():
    logger.info("Ring Ring")


def serial_connect():
    for serial_port in SERIAL_PORTS:
        if os.path.exists(serial_port):
            logger.info("Using serial port %s" % serial_port)
            return serial.Serial(serial_port, timeout=6)
    logger.error("No valid serial port found. Sleeping and retrying...")
    sleep(60)
    return serial_connect()

# MQTT functions
def on_connect(mosq, obj, rc):
	logging.info("Connect with RC " + str(rc))

def on_disconnect(client, userdata, rc):
	logging.warning("Disconnected (RC " + str(rc) + ")")
	if rc <> 0:
		try_reconnect(client)

# MQTT reconnect
def try_reconnect(client, time = 60):
	try:
		logging.info("Trying reconnect")
		client.reconnect()
	except:
		logging.warning("Reconnect failed. Trying again in " + str(time) + " seconds")
		Timer(time, try_reconnect, [client]).start()

# get logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=LOG_LEVEL,
                    filename=LOG_FILENAME)
logger = logging.getLogger("doorlock")
logger.info("Starting doorlock backend")

# instantiate db connection
conn = sqlite3.connect(DATABASE)
c = conn.cursor()
logger.debug("Database opened")

# connect to serial port
ser = serial_connect()
logger.debug("Serial port to frontend opened")

# initialize MQTT
logging.info("Initializing MQTT")
mqttc = paho.Client("mumalab_doorlock")
mqttc.username_pw_set(config.broker["user"], config.broker["password"])
mqttc.will_set(config.topic, "?", 1, True)
mqttc.connect(config.broker["hostname"], config.broker["port"], 60)
mqttc.on_connect = on_connect
mqttc.on_disconnect = on_disconnect
mqttc.loop_start()

# lock implementation
if DEBUG:
    from simlock import SimLock

    lock = SimLock()
else:
    from motorlock import MotorLock

    lock = MotorLock()
lock.onStatusChange += statusChange

# start pinging frontend
last_successful_ping = datetime.now()
ping()


while True:
    try:
        a = ser.readline()
        if not a:
            if last_successful_ping + timedelta(seconds=PONG_TIMEOUT) < datetime.now():
                logger.warning("Got no PONG from Arduino from %d sec, reinitializing serial port" % PONG_TIMEOUT)
                try:
                    ser.close()
                except Exception as e:
                    logger.error("Failed to close serial port! Got exception: %s" % str(e))
                ser = serial_connect()
                ping()
                last_successful_ping = datetime.now()
            continue

        b = a.rstrip("\n\r;").split(",")

        if b == ["PONG"]:
            last_successful_ping = datetime.now()
            logger.debug("Got Pong...(%s)" % (str(last_successful_ping)))
        else:
            logger.debug(b)

        # Unlock command: "UNLOCK,<token>,<pin>;"
        # Reply with "ACK;" or "NAK;"
        if b[0] == "UNLOCK":
            t = (b[1], create_hash(b[1] + ":" + b[2]))
            c.execute(
                'SELECT p.name from dl_tokens t JOIN dl_persons p ON t.person_id = p.id WHERE t.token=? AND t.pin=? AND p.disabled =0',
                t)
            r = c.fetchone()
            if r != None:
                logger.warning("Valid unlock request by %s (%s)", r[0], t[0])
                ser.write("ACK;\n")
                lock.unlock()
            else:
                logger.error("Invalid unlock request (%s, %s)", t[0], b[2])
                ser.write("NAK;\n")
            ser.flush()

        elif b[0] == "RING":
            ring_doorbell()

        # Semi lock command "SEMI_LOCK;"
        # no reply expected by frontend
        elif b[0] == "SEMI_LOCK":
            logger.warning("Semi lock request");
            lock.lock()

        # Semi unlock command "SEMI_UNLOCK;"
        # no reply expected by frontend
        elif b[0] == "SEMI_UNLOCK":
            logger.warning("Semi unlock request");
            lock.unlock()
            
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

    except serial.serialutil.SerialException:
        logger.error("Serial adapter disconnected! Sleeping and trying to reconnect...")
        sleep(10)
        ser = serial_connect()

    except KeyboardInterrupt:
        print "Received keyboard interrupt. Stopping..."
        running = False
        break

    except Exception as e:
        logger.error(e)
        exit(99)

logger.info("Stopping doorlock backend")
mqttc.loop_stop()
mqttc.disconnect()
