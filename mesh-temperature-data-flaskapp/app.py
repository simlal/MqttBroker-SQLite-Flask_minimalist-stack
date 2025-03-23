import logging
from flask import Flask, render_template, request
from flask_mqtt import Mqtt

import requests
import json


def configure_logger(name: str, log_level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Only add a handler if one doesn't exist yet
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# Flask app with mqtt config
logger = configure_logger(__name__, logging.INFO)
app = Flask(__name__)

# TODO: CHANGE TO LOCAL MOSQUITTO CLIENT RAN ON SAME DOCKER COMPOSE
app.config["MQTT_BROKER_URL"] = "broker.emqx.io"
app.config["MQTT_BROKER_PORT"] = 1883
app.config["MQTT_USERNAME"] = ""  # Set this item when you need to verify username and password
app.config["MQTT_PASSWORD"] = ""  # Set this item when you need to verify username and password
app.config["MQTT_KEEPALIVE"] = 5  # Set KeepAlive time in seconds
app.config["MQTT_TLS_ENABLED"] = False  # simple

topic = "/esp32/temperature"

mqtt_client = Mqtt(app)


### MQTT FUNCS ###
@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
    data = dict(topic=message.topic, payload=message.payload.decode())
    logger.info(f"Received message on topic: {data['topic']} with payload: {data['payload']}")


@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected successfully")
        mqtt_client.subscribe(topic)
    else:
        logger.error(f"Bad connection. Code: {rc}")


### FLASK ENDPOINTS ###
@app.route("/")
def index():
    # logger.info("GET at root")
    return render_template("index.html")


@app.route("/api/publish", methods=["POST"])
def publish_message():
    data = request.get_json()
    logger.info(f"Request body: {data}")
    return json.dumps({"statusCode": 200, "message": "DATA PUBLISHED to TOPIC"})
    # publish_result = mqtt_client.publish(request_data["topic"], request_data["msg"])
    # return jsonify({"code": publish_result[0]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
