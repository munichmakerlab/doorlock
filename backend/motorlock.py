from eventhook import EventHook
import logging
import RPi.GPIO as GPIO
from time import sleep


class MotorLock():
    def __init__(self):
        self.PIN_FDBK_SVP = 23
        self.PIN_FDBK_STEUERFALLE = 24
        self.PIN_FDBK_DOOR = 8
        self.PIN_FDBK_ERROR = 7
        self.onFeedback = EventHook()
        self.locked = True
        self.onStatusChange = EventHook()
        self.logger = logging.getLogger("motorlock")
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(4, GPIO.OUT)
        GPIO.setup(18, GPIO.OUT)
        # GPIO.setup(17, GPIO.IN)
        # GPIO.setup(21, GPIO.IN)
        # GPIO.add_event_detect(17, GPIO.FALLING, callback=self.button_callback, bouncetime=1000)
        # GPIO.add_event_detect(21, GPIO.FALLING, callback=self.button_callback, bouncetime=1000)

        GPIO.setup(self.PIN_FDBK_SVP, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PIN_FDBK_STEUERFALLE, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PIN_FDBK_DOOR, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PIN_FDBK_ERROR, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        GPIO.add_event_detect(self.PIN_FDBK_SVP, GPIO.BOTH, callback=self.feedback_callback, bouncetime=300)
        GPIO.add_event_detect(self.PIN_FDBK_STEUERFALLE, GPIO.BOTH, callback=self.feedback_callback, bouncetime=300)
        GPIO.add_event_detect(self.PIN_FDBK_DOOR, GPIO.BOTH, callback=self.feedback_callback, bouncetime=300)
        GPIO.add_event_detect(self.PIN_FDBK_ERROR, GPIO.BOTH, callback=self.feedback_callback, bouncetime=300)

        self.locked = (GPIO.input(4) == GPIO.LOW)
        self.logger.info("Locked?: %s" % self.locked)

    def feedback_callback(self, channel):
        self.logger.debug("GPIO feedback interrupt called on channel " + str(channel))
        topic = "unknown"
        state = GPIO.input(channel)
        if channel == self.PIN_FDBK_SVP:
            topic = "svp"
        elif channel == self.PIN_FDBK_STEUERFALLE:
            topic = "steuerfalle"
        elif channel == self.PIN_FDBK_DOOR:
            topic = "door"
        elif channel == self.PIN_FDBK_ERROR:
            topic = "error"

        self.onFeedback.fire(topic=topic, state=state)

    def button_callback(self, channel):
        self.logger.debug("GPIO button interrupt called on channel " + str(channel))
        sleep(1)
        if GPIO.input(channel) == GPIO.HIGH:
            self.logger.debug("Bounce")
            return

        if channel == 17:
            self.logger.warning("Lock button pressed")
            self.lock()
        elif channel == 21:
            self.logger.warning("Unlock button pressed")
            self.unlock()

    def lock(self):
        if self.locked:
            self.logger.warning("already locked")
            return
        self.logger.info("locking...")
        self.locked = True
        GPIO.output(4, GPIO.LOW)
        GPIO.output(18, GPIO.HIGH)
        self.onStatusChange.fire()

    def unlock(self):
        if not self.locked:
            self.logger.warning("already unlocked")
        self.logger.info("unlocking...")
        self.locked = False
        GPIO.output(4, GPIO.HIGH)
        GPIO.output(18, GPIO.LOW)
        self.onStatusChange.fire()

    def isUnlocked(self):
        return not self.locked
