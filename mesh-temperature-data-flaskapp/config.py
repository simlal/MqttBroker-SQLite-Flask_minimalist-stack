import os
from pathlib import Path

# Base configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG")

# MQTT configuration
MQTT_BROKER_URL = os.environ.get("MQTT_BROKER_URL", "broker.hivemq.com")
MQTT_BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", 1883))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")
MQTT_KEEPALIVE = int(os.environ.get("MQTT_KEEPALIVE", 5))
MQTT_TLS_ENABLED = os.environ.get("MQTT_TLS_ENABLED", "False").lower() == "true"
# MQTT topics
MQTT_BASE_TOPIC = os.environ.get("MQTT_BASE_TOPIC", "/readings")
MQTT_GATEWAY_TOPIC = f"{MQTT_BASE_TOPIC}/gateway/#"
MQTT_TEMPERATURE_TOPIC = f"{MQTT_BASE_TOPIC}/temperature/#"

# Server configuration
HOST_URL = os.environ.get("HOST_URL", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))
DEBUG_MODE = os.environ.get("DEBUG_MODE", "ON").lower() == "on"

# Database configuration
# Use an absolute path for Docker compatibility
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = os.environ.get("DATABASE", str(BASE_DIR / "../data/db.sqlite"))
