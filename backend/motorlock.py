from eventhook import EventHook
import logging
import RPi.GPIO as GPIO


class MotorLock():
    def __init__(self):
        self.locked = True
        self.onStatusChange = EventHook()
        self.logger = logging.getLogger("motorlock")
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(4, GPIO.OUT)
	GPIO.setup(18, GPIO.OUT)
	GPIO.setup(17, GPIO.IN)
        GPIO.setup(21, GPIO.IN)
	GPIO.add_event_detect(17, GPIO.FALLING, callback = self.button_callback, bouncetime = 300)
        GPIO.add_event_detect(21, GPIO.FALLING, callback = self.button_callback, bouncetime = 300)
        self.locked = (GPIO.input(4) == GPIO.LOW)

    def button_callback(self, channel):
        if channel == 17:
            self.logger.info("Close button pressed")
            self.lock()
        elif channel == 21:
            self.logger.info("Unlock button pressed")
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
            self.logger.warn("already unlocked")
        self.logger.info("unlocking...")
        self.locked = False
        GPIO.output(4, GPIO.HIGH)
	GPIO.output(18, GPIO.LOW)
        self.onStatusChange.fire()

    def isUnlocked(self):
        return not self.locked
