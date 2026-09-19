"""Runtime settings loaded from ``backend/.env``.

Secrets belong in that ignored file, never in Python source or Git.
"""

import os
from pathlib import Path


ENV_FILE = Path(__file__).with_name(".env")


def load_env(path=ENV_FILE):
    """Load simple KEY=VALUE entries without replacing process environment."""
    if not path.is_file():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key.strip():
            raise ValueError("Invalid .env line: %r" % line)
        os.environ.setdefault(key.strip(), value.strip())


def required(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError("Missing required setting %s in %s" % (name, ENV_FILE))
    return value


load_env()

MQTT_HOSTNAME = required("MQTT_HOSTNAME")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = required("MQTT_USERNAME")
MQTT_PASSWORD = required("MQTT_PASSWORD")
MQTT_TOPIC = required("MQTT_TOPIC")
MQTT_FEEDBACK_TOPIC = required("MQTT_FEEDBACK_TOPIC")
ZUKO_LOCK_URL = required("ZUKO_LOCK_URL")
