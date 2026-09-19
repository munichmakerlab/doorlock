from eventhook import EventHook
import logging
from time import sleep
import requests
import settings


class ZukoLock():
    def __init__(self):
        self.logger = logging.getLogger("doorlock")
        self.onStatusChange = EventHook()
        self.onFeedback = EventHook()
        self.locked = True
        self.logger.info("Locked?: %s" % self.locked)

    def feedback_callback(self, channel):
        self.logger.debug("ignoring(!) GPIO feedback interrupt called on channel " + str(channel))

    def button_callback(self, channel):
        self.logger.debug("ignoring(!) GPIO button interrupt called on channel " + str(channel))

    def lock(self):
        if self.locked:
            self.logger.warning("already locked")
            return
        self.logger.info("locking...")
        self.locked = True
        # self.onStatusChange.fire()

    def unlock(self):
        if not self.locked:
            self.logger.warning("already unlocked")
        self.logger.info("unlocking...")
        try:
            if requests.get(settings.ZUKO_LOCK_URL).ok:
                self.logger.debug("door open http request ok")
            else:
                self.logger.warning("door open http request failed")
        except Exception:
            self.logger.warning("door open http request failed with exception")
        self.locked = False
        self.onStatusChange.fire()
        sleep(1)
        self.lock()

    def isUnlocked(self):
        return not self.locked
