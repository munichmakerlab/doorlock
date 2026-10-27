from eventhook import EventHook
import logging
from threading import Lock, Timer
from time import monotonic
import requests
import RPi.GPIO as GPIO

from config import (
    TIMESPAN_FOR_UNLOCK_ATTEMPTS,
    UNLOCK_ATTEMPTS_UNTIL_GATE_OPENS,
    UNLOCK_DOOR_GPIO,
    UNLOCK_DOOR_SECONDS,
)


class ZukoLock():
    def __init__(self):
        self.logger = logging.getLogger("doorlock")
        self.onStatusChange = EventHook()
        self.onFeedback = EventHook()
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(UNLOCK_DOOR_GPIO, GPIO.OUT, initial=GPIO.LOW)
        self.locked = True
        self._lock_timer = None
        self._unlock_attempts = 0
        self._unlock_attempts_timer = None
        self._unlock_attempts_deadline = None
        self._unlock_attempts_lock = Lock()
        self.logger.info("Locked?: %s" % self.locked)

    def feedback_callback(self, channel):
        self.logger.debug("ignoring(!) GPIO feedback interrupt called on channel " + str(channel))

    def button_callback(self, channel):
        self.logger.debug("ignoring(!) GPIO button interrupt called on channel " + str(channel))

    def lock(self):
        if self._lock_timer is not None:
            self._lock_timer.cancel()
            self._lock_timer = None
        GPIO.output(UNLOCK_DOOR_GPIO, GPIO.LOW)
        if self.locked:
            self.logger.warning("already locked")
            return
        self.logger.info("locking...")
        self.locked = True
        # self.onStatusChange.fire()

    def _reset_unlock_attempts(self, deadline):
        with self._unlock_attempts_lock:
            # An expired timer must not clear a newer attempt window.
            if self._unlock_attempts_deadline == deadline:
                self._unlock_attempts = 0
                self._unlock_attempts_deadline = None
                self._unlock_attempts_timer = None

    def _count_unlock_attempt(self):
        with self._unlock_attempts_lock:
            now = monotonic()
            if self._unlock_attempts_deadline is None or now >= self._unlock_attempts_deadline:
                if self._unlock_attempts_timer is not None:
                    self._unlock_attempts_timer.cancel()
                self._unlock_attempts = 0
                self._unlock_attempts_deadline = now + TIMESPAN_FOR_UNLOCK_ATTEMPTS
                self._unlock_attempts_timer = Timer(
                    TIMESPAN_FOR_UNLOCK_ATTEMPTS,
                    self._reset_unlock_attempts,
                    args=(self._unlock_attempts_deadline,),
                )
                self._unlock_attempts_timer.daemon = True
                self._unlock_attempts_timer.start()
            self._unlock_attempts += 1
            return self._unlock_attempts

    def unlock(self):
        attempt = self._count_unlock_attempt()
        if not self.locked:
            self.logger.warning("already unlocked")
        self.logger.info("unlocking...")

        if UNLOCK_ATTEMPTS_UNTIL_GATE_OPENS > 0 and attempt == UNLOCK_ATTEMPTS_UNTIL_GATE_OPENS:
            try:
                # For the time when the gate controller box is wired to the RPi (needs further code adjustments):
                # GPIO.output(MAIN_GATE_UP_GPIO, GPIO.HIGH)
                # sleep(0.5)
                # GPIO.output(MAIN_GATE_UP_GPIO, GPIO.LOW)
                # sleep(MAIN_GATE_SECONDS_UNTIL_STOP)
                # GPIO.output(MAIN_GATE_STOP_GPIO, GPIO.HIGH)
                # sleep(0.5)
                # GPIO.output(MAIN_GATE_STOP_GPIO, GPIO.LOW)
                if requests.get("http://tor:opengate@10.10.20.43/open?who=tor", timeout=5).ok:
                    self.logger.debug("door open http request ok")
                else:
                    self.logger.warning("door open http request failed")
            except Exception:
                self.logger.warning("door open http request failed with exception")
        else:
            if self._lock_timer is not None:
                self._lock_timer.cancel()
            try:
                GPIO.output(UNLOCK_DOOR_GPIO, GPIO.HIGH)
            except Exception:
                self.logger.warning("error while opening door via GPIO")

            self.locked = False
            self._lock_timer = Timer(UNLOCK_DOOR_SECONDS, self.lock)
            self._lock_timer.start()
        self.onStatusChange.fire()

    def isUnlocked(self):
        return not self.locked
