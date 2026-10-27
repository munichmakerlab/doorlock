# Timings
MAIN_GATE_SECONDS_UNTIL_STOP = 4
WORKSHOP_GATE_SECONDS_UNTIL_STOP = 4
UNLOCK_DOOR_SECONDS = 20

# Configuration for the fallback if the door has an issue and won't open.
# If the user presents his key UNLOCK_ATTEMPTS_UNTIL_GATE_OPENS times within TIMESPAN_FOR_UNLOCK_ATTEMPTS (seconds), the gate will open as a fallback.
UNLOCK_ATTEMPTS_UNTIL_GATE_OPENS = 2 # set it to 0 if the gate shouldn't open at all
TIMESPAN_FOR_UNLOCK_ATTEMPTS = 180 # seconds

# GPIO outputs
MAIN_GATE_UP_GPIO = 2
MAIN_GATE_STOP_GPIO = 3

WORKSHOP_GATE_UP_GPIO = 4
WORKSHOP_GATE_STOP_GPIO = 17

UNLOCK_DOOR_GPIO = 23

# GPIO inputs
REED_SENSOR_DOOR_GPIO = 24
SPACE_STATUS_GPIO = 25

# MQTT configuration currently not needed (Oct. 2026)
#
# broker = {
# 	"hostname": "HOSTNAME_OF_YOUR_MQTT_BROKER",
# 	"port": 1883,
# 	"user": "MQTT_USERNAME",
# 	"password": "MQTT_PASSWORD"
# 	}
#
# topic = "mumalab/room/door/status"
