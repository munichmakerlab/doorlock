#!/usr/bin/env python3
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

import settings

DIR = os.path.dirname(os.path.realpath(__file__))

# config
DATABASE = DIR + '/doorlock.db'
SERIAL_PORTS = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2', '/dev/ttyUSB3']
DEBUG = False
LOG_FILENAME = DIR + "/doorlock.log"
LOG_LEVEL = logging.INFO
PONG_TIMEOUT = 30  # in sec

if os.path.exists("COM8"):
    SERIAL_PORT = 'COM8'
    DEBUG = True

# regular ping to frontend, every 10 seconds, 30 sec timeout
running = True


def ping():
    if not running:
        return
    ser.write(b"PING;\n")
    ser.flush()
    timer = Timer(10.0, ping)
    timer.start()


def statusChange():
    if lock.isUnlocked():
        ser.write(b"STATUS,1;\n")
        mqttc.publish(settings.MQTT_TOPIC, "1", 1, True)
    else:
        ser.write(b"STATUS,0;\n")
        mqttc.publish(settings.MQTT_TOPIC, "0", 1, True)
    ser.flush()


def feedback(topic, state):
    mqttc.publish("%s/%s" % (settings.MQTT_FEEDBACK_TOPIC, topic), str(state), 1, False)


def create_hash(text):
    h = hashlib.sha256()
    h.update(text.encode("utf-8"))
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
def on_connect(client, userdata, flags, reason_code, properties=None):
    logging.info("Connect with RC " + str(reason_code))


def on_disconnect(client, userdata, flags, reason_code, properties=None):
    logging.warning("Disconnected (RC " + str(reason_code) + ")")
    if reason_code != 0:
        try_reconnect(client)


# MQTT reconnect
def try_reconnect(client, time=60):
    try:
        logging.info("Trying reconnect")
        client.reconnect()
    except Exception:
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
mqttc = paho.Client(paho.CallbackAPIVersion.VERSION2, "mumalab_doorlock")
mqttc.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
mqttc.will_set(settings.MQTT_TOPIC, "?", 1, True)
mqttc.on_connect = on_connect
mqttc.on_disconnect = on_disconnect
try:
    mqttc.connect(settings.MQTT_HOSTNAME, settings.MQTT_PORT, 60)
except Exception as e:
    logger.error("Failed to connect to MQTT! Got exception: %s" % str(e))
mqttc.loop_start()

# lock implementation
if DEBUG:
    from simlock import SimLock
    lock = SimLock()
else:
    # from motorlock import MotorLock
    # lock = MotorLock()
    from zuko_wifi_lock import ZukoLock
    lock = ZukoLock()

lock.onStatusChange += statusChange
lock.onFeedback += feedback

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

        line = a.decode("ascii", errors="replace")
        b = line.rstrip("\n\r;").split(",")

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
            if r is not None:
                logger.warning("Valid unlock request by %s (%s)", r[0], t[0])
                ser.write(b"ACK;\n")
                lock.unlock()
            else:
                logger.error("Invalid unlock request (%s, %s)", t[0], b[2])
                ser.write(b"NAK;\n")
            ser.flush()

        elif b[0] == "RING":
            ring_doorbell()

        # Lock command "LOCK;"
        elif b[0] == "LOCK":
            logger.warning("Lock request")
            lock.lock()

        # reply to ping: "PONG;"
        elif b[0] == "PONG":
            if lock.isUnlocked():
                ser.write(b"STATUS,1;\n")
            else:
                ser.write(b"STATUS,0;\n")
            ser.flush()

    except serial.serialutil.SerialException:
        logger.error("Serial adapter disconnected! Sleeping and trying to reconnect...")
        sleep(10)
        ser = serial_connect()

    except KeyboardInterrupt:
        print("Received keyboard interrupt. Stopping...")
        running = False
        break

    except Exception as e:
        logger.error(e)
        exit(99)

logger.info("Stopping doorlock backend")
mqttc.loop_stop()
mqttc.disconnect()
