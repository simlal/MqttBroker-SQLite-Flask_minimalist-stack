from flask import Flask, render_template, request, g
from flask_mqtt import Mqtt

import os
from pathlib import Path
import logging
from datetime import datetime
import sqlite3
import json

###### CONFIGURE APP WITH ENV VARIABLES ######
from config import (
    LOG_LEVEL,
    MQTT_BROKER_URL,
    MQTT_BROKER_PORT,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    MQTT_KEEPALIVE,
    MQTT_TLS_ENABLED,
    MQTT_TOPIC,
    HOST_URL,
    PORT,
    DEBUG_MODE,
    DATABASE_PATH,
)


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


###### Logging config ######
logger = configure_logger(__name__, getattr(logging, LOG_LEVEL))

###### Flask app config and Mqtt wrapper ######
app = Flask(__name__)

# Configure Flask app
app.config["MQTT_BROKER_URL"] = MQTT_BROKER_URL
app.config["MQTT_BROKER_PORT"] = MQTT_BROKER_PORT
app.config["MQTT_USERNAME"] = MQTT_USERNAME
app.config["MQTT_PASSWORD"] = MQTT_PASSWORD
app.config["MQTT_KEEPALIVE"] = MQTT_KEEPALIVE
app.config["MQTT_TLS_ENABLED"] = MQTT_TLS_ENABLED
app.config["DATABASE"] = DATABASE_PATH

mqtt_client = Mqtt(app)
logger.debug(f"Flask app config: {app.config}")


###### SQLITE DB Conn/Query helpers ######
def get_db():
    # Singleton db conn
    if "db" not in g:
        db_path = app.config["DATABASE"]
        logger.debug(f"Connecting to database: {db_path}")
        g.db = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row

    return g.db


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def row_obj_to_dict(obj: sqlite3.Row) -> dict:
    return {col: obj[col] for col in obj.keys()}


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


### MQTT FUNCS ###
@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
    data = dict(topic=message.topic, payload=message.payload.decode())
    logger.info(f"Received message on topic: {data['topic']} with payload: {data['payload']}")


@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected successfully")
        mqtt_client.subscribe(MQTT_TOPIC)
    else:
        logger.error(f"Bad connection. Code: {rc}")


### Flask routes ###
@app.route("/", methods=["GET"])
def index():
    # TODO: SELECT + JOIN LATEST READINGS
    # TODO: MAKE BASE + REF BASE IN TEMPLATE
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template("index.html", now=now)


@app.route("/readings", methods=["GET"])
def readings():
    # TODO: FILTER TIMESTAMP WITH PARAMS AND DISPLAY
    logger.info("PARAMS: ")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template("readings.html", now=now)


@app.route("/devices", methods=["GET"])
def devices():
    api_response = get_devices()
    devices_data = json.loads(api_response)["devices"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template("devices.html", devices=devices_data, now=now)


### Flask API Endpoints ###
@app.route("/api/publish", methods=["POST"])
def publish_message():
    # TODO: ACTUALLY PUBLISH TO MQTT
    data = request.get_json()
    logger.info(f"Request body: {data}")
    return json.dumps({"statusCode": 200, "message": "DATA PUBLISHED to TOPIC"})
    # publish_result = mqtt_client.publish(request_data["topic"], request_data["msg"])
    # return jsonify({"code": publish_result[0]})
    #


@app.route("/api/readings", methods=["GET"])
def get_readings():
    cur = get_db().cursor()
    # Filter last N readings and according to from-to daterange
    logger.debug(f"Request Params: {request.args}")
    n_max_readings = request.args.get("nMaxReadings")
    date_from = request.args.get("dateFrom")
    date_to = request.args.get("dateTo")

    readings = [1, 2, 3]
    return json.dumps({"statusCode": 200, "readings": readings})


@app.route("/api/devices", methods=["GET"])
def get_devices():
    # Filter by internal_id
    internal_ids = request.args.get("internal_id", "")
    internal_ids = internal_ids.split(",") if internal_ids else []
    logger.info(f"Retrieving devices with {internal_ids=} from db...")

    if internal_ids:
        placeholders = ",".join(["?"] * len(internal_ids))
        stmt = f"SELECT * FROM devices WHERE internal_id IN ({placeholders})"
        devices_obj = query_db(stmt, internal_ids)
    else:
        stmt = "SELECT * FROM devices"
        devices_obj = query_db(stmt)

    # Return all fetched devices
    devices = []
    if devices_obj:
        for device_obj in devices_obj:
            device = {
                k: v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v
                for k, v in row_obj_to_dict(device_obj).items()
            }
            devices.append(device)
    logger.info(f"Retrieved devices: {devices}")
    return json.dumps({"statusCode": 200, "devices": devices})


if __name__ == "__main__":
    app.run(host=HOST_URL, port=PORT, debug=DEBUG_MODE)
