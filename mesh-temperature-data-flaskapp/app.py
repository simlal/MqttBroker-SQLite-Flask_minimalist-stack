from flask import Flask, Request, render_template, request, g
from flask_mqtt import Mqtt

import logging
from datetime import datetime
import sqlite3
import json
from typing import Any
import random

###### CONFIGURE APP WITH ENV VARIABLES ######
from config import (
    LOG_LEVEL,
    MQTT_BASE_TOPIC,
    MQTT_BROKER_URL,
    MQTT_BROKER_PORT,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    MQTT_KEEPALIVE,
    MQTT_TLS_ENABLED,
    MQTT_GATEWAY_TOPIC,
    MQTT_TEMPERATURE_TOPIC,
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
    if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
        get_db().commit()
    return (rv[0] if rv else None) if one else rv


def row_obj_to_dict(obj: sqlite3.Row) -> dict:
    return {col: obj[col] for col in obj.keys()}


###### flask helpers ######
def get_json_from_req(request: Request) -> Any | None:
    content_type = request.headers.get("Content-Type")
    if content_type == "application/json":
        return request.json
    else:
        return None


# Processing gateway data logic from /api endpoints or handle_mqtt_message
def process_gateway_data(data: dict) -> str:
    gateway_mac = data.get("macAddress")
    if gateway_mac is None:
        return json.dumps({"statusCode": 400, "error": "'macAddress' required in body"})

    # Gateway id from mac address
    stmt = "SELECT id FROM devices WHERE mac_address = ? AND info LIKE '%GATEWAY%'"
    gateway_id_row = query_db(stmt, (gateway_mac,), one=True)
    if gateway_id_row is None:
        return json.dumps({"statusCode": 404, "error": f"Gateway with MAC_address={gateway_mac} not found"})
    else:
        gateway_id = gateway_id_row[0]

    # Validate its a gateway

    # Insert a new reading
    timestamp, rssi = data.get("timestamp"), data.get("rssi")
    if timestamp is None or rssi is None:
        return json.dumps({"statusCode": 400, "error": "Missing either of 'timestamp' or 'rssi' in body"})
    # Data validation of timestamp and rssi
    try:
        timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return json.dumps(
            {
                "statusCode": 400,
                "error": f"Invalid datetime format: {timestamp}. Required format: 'YYYY-MM-DD HH:MM:SS'",
            }
        )
    try:
        rssi = int(rssi)
    except ValueError:
        return json.dumps({"statusCode": 400, "error": f"Invalid rssi format. Could not convert {rssi} to int."})

    logger.info(f"Inserting new reading for gatewayId={gateway_id} of rssi={rssi}")
    stmt = "INSERT INTO gateway_readings (device_id, timestamp, rssi) VALUES (?, ?, ?)"
    query_db(stmt, (gateway_id, timestamp, rssi))

    return json.dumps({"statusCode": 200, "device_id": gateway_id})


def process_sensor_temp_data(data: dict) -> str:
    sensor_mac = data.get("macAddress")
    if sensor_mac is None:
        return json.dumps({"statusCode": 400, "error": "'macAddress' required in body"})

    # Sensor id from mac address
    stmt = "SELECT id FROM devices WHERE mac_address = ? AND info LIKE '%TEMPERATURE%'"
    sensor_id_row = query_db(stmt, (sensor_mac,), one=True)
    if sensor_id_row is None:
        return json.dumps({"statusCode": 404, "error": f"Sensor with MAC_address={sensor_mac} not found"})
    else:
        sensor_id = sensor_id_row[0]

    # Insert a new reading
    timestamp, temperature = data.get("timestamp"), data.get("temperature")
    if timestamp is None or temperature is None:
        return json.dumps({"statusCode": 400, "error": "Missing either of 'timestamp' or 'temperature' in body"})
    # Data validation of timestamp and temp
    try:
        timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return json.dumps(
            {
                "statusCode": 400,
                "error": f"Invalid datetime format: {timestamp}. Required format: 'YYYY-MM-DD HH:MM:SS'",
            }
        )
    try:
        temperature = float(temperature)
    except ValueError:
        return json.dumps(
            {"statusCode": 400, "error": f"Invalid temp format. Could not convert {temperature} to float."}
        )

    logger.info(f"Inserting new reading for sensorId={sensor_id} of rssi={temperature}")
    stmt = "INSERT INTO sensor_temperature_readings (device_id, timestamp, temperature) VALUES (?, ?, ?)"
    query_db(stmt, (sensor_id, timestamp, temperature))

    return json.dumps({"statusCode": 200, "device_id": sensor_id})


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "db", None)
    if db is not None:
        db.close()


### MQTT FUNCS ###
@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
    # OPTIMIZE: ALL devices known upfront, no insert into 'devices' table if message contains new MAC
    with app.app_context():
        processed_message = None
        try:
            payload = message.payload.decode()
            logger.info(f"Received message with payload={payload}")
            data = json.loads(payload)

            if MQTT_GATEWAY_TOPIC in message.topic:
                logger.info(f"Processing message from gateway topic: {message.topic}")
                # Preparing payload
                # FIX: No real time clock in gateway for now, lets use received time as timestamp, overriding
                data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                logger.info(data)
                processed_message = process_gateway_data(data)
            elif MQTT_TEMPERATURE_TOPIC in message.topic:
                logger.info(f"Processing message from temperature topic: {message.topic}")
                # FIX: No real time clock in gateway for now, lets use received time as timestamp, overriding
                data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                processed_message = process_sensor_temp_data(data)
            else:
                logger.warning(f"Not processing topic {message.topic}")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON payload from: {message.payload}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {str(e)}")

        if processed_message:
            logger.info(f"Processed message with db operation: {processed_message}")


@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected successfully")
        # Subscribe to all sensors and gateways
        mqtt_client.subscribe(f"{MQTT_GATEWAY_TOPIC}/#")
        mqtt_client.subscribe(f"{MQTT_TEMPERATURE_TOPIC}/#")
        logger.info(f"Subscribed to topics: {MQTT_GATEWAY_TOPIC}/# and {MQTT_TEMPERATURE_TOPIC}/#")
    else:
        logger.error(f"Bad connection to MQTT broker. Code: {rc}")


###### Flask routes ######
@app.route("/", methods=["GET"])
def index():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template("index.html", now=now)


@app.route("/gateway-readings", methods=["GET"])
def gateway_readings():
    # Get available gateway devices for selection
    devices_response = json.loads(get_devices())
    all_devices = devices_response.get("devices", [])
    gateway_devices = [device for device in all_devices if "GATEWAY" in device.get("info", "").upper()]

    # Get gateway readings if a specific gateway is selected
    gateway_mac = request.args.get("macAddress")
    gateway_readings = {"statusCode": 200, "gatewayReadings": []}

    # Update readings data when selected
    if gateway_mac:
        api_resp_gateway = get_gateway_readings()
        gateway_readings = json.loads(api_resp_gateway)

    logger.info(gateway_readings)
    # Format date for the template
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Optional date range filters (pass through to template for form values)
    readings_from = request.args.get("readingsFrom")
    readings_to = request.args.get("readingsTo")

    return render_template(
        "gateway_readings.html",
        devices=gateway_devices,
        gateway_data=gateway_readings,
        selected_device=gateway_mac,
        readings_from=readings_from,
        readings_to=readings_to,
        now=now,
    )


@app.route("/sensor-temperature-readings", methods=["GET"])
def sensor_temperature_readings():
    # Get available temperature devices for selection
    devices_response = json.loads(get_devices())
    all_devices = devices_response.get("devices", [])
    temp_devices = [device for device in all_devices if "TEMPERATURE" in device.get("info", "").upper()]

    # Get temperature readings if a specific device is selected
    sensor_mac = request.args.get("macAddress")
    temp_readings = {"statusCode": 200, "sensorTemperatureReadings": []}

    if sensor_mac:
        api_resp_temp = get_sensor_temp_readings()
        temp_readings = json.loads(api_resp_temp)

    # Format date for the template
    logger.info(temp_readings)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Optional date range filters
    readings_from = request.args.get("readingsFrom")
    readings_to = request.args.get("readingsTo")

    return render_template(
        "sensor_temperature_readings.html",
        devices=temp_devices,
        sensor_data=temp_readings,
        selected_device=sensor_mac,
        readings_from=readings_from,
        readings_to=readings_to,
        now=now,
    )


@app.route("/devices", methods=["GET"])
def devices():
    api_response = get_devices()
    devices_data = json.loads(api_response)["devices"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template("devices.html", devices=devices_data, now=now)


### Flask API Endpoints ###


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
    logger.debug(f"Retrieved devices: {devices}")
    return json.dumps({"statusCode": 200, "devices": devices})


@app.route("/api/gateway-readings", methods=["POST"])
def insert_gateway_reading():
    # Filter by mac address first
    data = get_json_from_req(request)
    if data is None:
        return json.dumps({"statusCode": 400, "error": "Expected Content-Type: application/json"})

    return process_gateway_data(data)


@app.route("/api/gateway-readings", methods=["GET"])
def get_gateway_readings():
    # Filter by mac address first
    gateway_mac = request.args.get("macAddress")
    if gateway_mac is None:
        return json.dumps({"statusCode": 400, "error": "required 'macAddress' in params"})

    # Gateway id from mac address
    stmt = "SELECT id FROM devices WHERE mac_address = ?"
    gateway_id_row = query_db(stmt, (gateway_mac,), one=True)
    if gateway_id_row is None:
        return json.dumps({"statusCode": 404, "error": f"Gateway with MAC_address={gateway_mac} not found"})
    else:
        device_id = gateway_id_row[0]

    # If no from-to range provided, return all readings otherwise filter
    readings_from = request.args.get("readingsFrom")
    readings_to = request.args.get("readingsTo")

    # stmt builder with filters
    logger.debug(f"request arguments: {request.args}")

    if readings_from and readings_to:
        stmt = "SELECT * from gateway_readings WHERE device_id = ? AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp DESC"
        readings_obj = query_db(stmt, (device_id, readings_from, readings_to))

    elif readings_from:
        stmt = "SELECT * from gateway_readings WHERE device_id = ? AND timestamp >= ? ORDER BY timestamp DESC"
        readings_obj = query_db(stmt, (device_id, readings_from))
    elif readings_to:
        stmt = "SELECT * from gateway_readings WHERE device_id = ? AND timestamp <= ? ORDER BY timestamp DESC"
        readings_obj = query_db(stmt, (device_id, readings_to))
    else:  # all readings
        stmt = "SELECT * from gateway_readings WHERE device_id = ? ORDER BY timestamp DESC"
        readings_obj = query_db(stmt, (device_id,))

    readings = []
    if readings_obj:
        for reading_obj in readings_obj:
            reading = {
                k: v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v
                for k, v in row_obj_to_dict(reading_obj).items()
            }
            readings.append(reading)

    logger.info(f"Retrieved {len(readings)} readings for device_id={device_id}")
    return json.dumps({"statusCode": 200, "gatewayReadings": readings})


@app.route("/api/sensor-temperature-readings", methods=["GET"])
def get_sensor_temp_readings():
    # Filter by mac address first
    sensor_mac = request.args.get("macAddress")
    if sensor_mac is None:
        return json.dumps({"statusCode": 400, "error": "required 'macAddress' in params"})

    # Sensor id from mac address
    stmt = "SELECT id FROM devices WHERE mac_address = ?"
    sensor_id_row = query_db(stmt, (sensor_mac,), one=True)
    if sensor_id_row is None:
        return json.dumps({"statusCode": 404, "error": f"Sensor with MAC_address={sensor_mac} not found"})
    else:
        sensor_id = sensor_id_row[0]

    # If no from-to range provided, return all readings otherwise filter
    readings_from = request.args.get("readingsFrom")
    readings_to = request.args.get("readingsTo")

    # stmt builder with filters
    logger.debug(f"request arguments: {request.args}")
    logger.debug(f"Querying temps for sensor with device_id={sensor_id}")

    if readings_from and readings_to:
        stmt = "SELECT * from sensor_temperature_readings WHERE device_id = ? AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp DESC"
        readings_obj = query_db(stmt, (sensor_id, readings_from, readings_to))

    elif readings_from:
        stmt = (
            "SELECT * from sensor_temperature_readings WHERE device_id = ? AND timestamp >= ? ORDER BY timestamp DESC"
        )
        readings_obj = query_db(stmt, (sensor_id, readings_from))
    elif readings_to:
        stmt = (
            "SELECT * from sensor_temperature_readings WHERE device_id = ? AND timestamp <= ? ORDER BY timestamp DESC"
        )
        readings_obj = query_db(stmt, (sensor_id, readings_to))
    else:  # all readings
        stmt = "SELECT * from sensor_temperature_readings WHERE device_id = ? ORDER BY timestamp DESC"
        readings_obj = query_db(stmt, (sensor_id,))

    readings = []
    if readings_obj:
        for reading_obj in readings_obj:
            reading = {
                k: v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v
                for k, v in row_obj_to_dict(reading_obj).items()
            }
            readings.append(reading)

    logger.info(f"Retrieved {len(readings)} readings for sensor_id={sensor_id}")
    return json.dumps({"statusCode": 200, "sensorTemperatureReadings": readings})


@app.route("/api/sensor-temperature-readings", methods=["POST"])
def insert_sensor_temp_readings():
    # Filter by mac address first
    data = get_json_from_req(request)
    if data is None:
        return json.dumps({"statusCode": 400, "error": "Expected Content-Type: application/json"})

    return process_sensor_temp_data(data)


@app.route("/api/publish-gateway-test", methods=["POST"])
def publish_gateway_test():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {"macAddress": "3C:E9:0E:72:12:4C", "timestamp": now, "rssi": random.randint(10, 100)}
    data_to_pub = json.dumps(data)
    topic = f"{MQTT_GATEWAY_TOPIC}/{data['macAddress']}"
    logger.info(f"Publishing on {topic=} with data: {data_to_pub}")
    success, msg_id = mqtt_client.publish(topic, bytes(data_to_pub, "utf-8"))
    if success == 0:
        return json.dumps({"statusCode": 200, "msgId": msg_id})
    else:
        return json.dumps({"statusCode": 400, "error": f"Could not connect to broker. Code: {success}"})


@app.route("/api/publish-temperature-test", methods=["POST"])
def publish_temperature_test():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {"macAddress": "E0:5A:1B:30:B3:38", "timestamp": now, "temperature": random.uniform(15, 25)}
    data_to_pub = json.dumps(data)
    topic = f"{MQTT_TEMPERATURE_TOPIC}/{data['macAddress']}"
    logger.info(f"Publishing on {topic=} with data: {data_to_pub}")
    success, msg_id = mqtt_client.publish(topic, bytes(data_to_pub, "utf-8"))
    if success == 0:
        return json.dumps({"statusCode": 200, "msgId": msg_id})
    else:
        return json.dumps({"statusCode": 400, "error": f"Could not connect to broker. Code: {success}"})


if __name__ == "__main__":
    app.run(host=HOST_URL, port=PORT, debug=DEBUG_MODE)
