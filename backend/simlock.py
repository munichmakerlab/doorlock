from eventhook import EventHook
import logging

class SimLock():
	def __init__(self):
		self.locked = True
		self.onStatusChange = EventHook()
		self.logger = logging.getLogger("simlock")
	
	def lock(self):
		if self.locked:
			self.logger.warning("already locked")
			return
		self.logger.info("locking...")
		self.locked = True
		self.onStatusChange.fire()
		
	def unlock(self):
		if not self.locked:
			self.logger.warn("already unlocked")
		self.logger.info("unlocking...")
		self.locked = False
		self.onStatusChange.fire()
		
	def isUnlocked(self):
		return not self.locked
