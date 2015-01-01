from eventhook import EventHook
import logging
import RPi.GPIO as GPIO

class MotorLock():
	def __init__(self):
		self.locked = True
		self.onStatusChange = EventHook()
		self.logger = logging.getLogger("motorlock")
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(4, GPIO.OUT)
	
	def lock(self):
		if self.locked:
			self.logger.warning("already locked")
			return
		self.logger.info("locking...")
		self.locked = True
		GPIO.output(4, GPIO.LOW)
		self.onStatusChange.fire()
		
	def unlock(self):
		if not self.locked:
			self.logger.warn("already unlocked")
		self.logger.info("unlocking...")
		self.locked = False
		GPIO.output(4, GPIO.HIGH)
		self.onStatusChange.fire()
		
	def isUnlocked(self):
		return not self.locked
