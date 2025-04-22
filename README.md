
# MQTT Broker with SQLite and Flask - Minimalist IoT Stack

A lightweight, containerized IoT backend stack with MQTT message broker, SQLite persistence, and Flask web interface.

## Introduction

### Overview

This project provides a complete, minimalist backend infrastructure for IoT applications, combining three essential components:

1. An MQTT broker for message passing between IoT devices
2. A SQLite database for persistent data storage
3. A Flask web application for data visualization and device management

The stack is fully containerized using Docker Compose, making it easy to deploy on any system with Docker installed. The Flask application performs dual roles - subscribing to MQTT topics to collect device data while also serving a web interface to visualize and interact with the stored information.

This project is designed as a companion to the [ESP32 Gateway project](https://github.com/simlal/norvi-esp32-gateway-mqtt), providing the server-side infrastructure to receive and process data from ESP32 devices.

A simple demonstration of the complete stack in action can be found [here](TODO) with [matching dashboard](TODO).

### Architecture

The architecture follows a microservices approach with three main components:

1. **MQTT Broker**: Eclipse Mosquitto provides a lightweight message broker implementing the MQTT protocol, enabling efficient publish/subscribe communication between IoT devices and the backend.

2. **SQLite Database**: A lightweight, file-based SQL database that stores device data persistently with minimal resource requirements.

3. **Flask Application**: A Python web application that:
   - Subscribes to MQTT topics to receive device data
   - Processes and stores incoming messages in the SQLite database
   - Provides a web interface for data visualization and device management
   - Enables publishing messages back to devices via MQTT

## System Requirements

- Docker and Docker Compose installed
- Minimum 512MB RAM and 1GB disk space
- Network connectivity for IoT devices to reach the MQTT broker
- Modern web browser for accessing the Flask interface

## Installation and Configuration

### Quick Start

1. Clone the repository:

```bash
git clone https://github.com/simlal/mqttbroker-sqlite-flask_minimalist-stack.git
cd mqttbroker-sqlite-flask_minimalist-stack
```

2. Configure the MQTT broker by editing `mosquitto.conf`:

```bash
# Review and modify if needed, especially security settings
nvim mosquitto.conf
```

3. Build and start the compose stack

```bash
docker compose -f docker-compose.yaml build
docker compose -f docker-compose.yaml up
```

4. Access the web interface at `http://localhost:5000`

### Configuration Options

#### MQTT Broker Configuration

The Mosquitto broker is configured through `mosquitto.conf`. Key parameters include:

- Listener configuration (port 1883)
- Authentication settings (if enabled)
- Persistence options
- Security settings (TLS, if needed)

#### Flask Application Configuration

The Flask application is configured through environment variables in the Docker Compose file:

- `FLASK_APP`: Entry point for the Flask application
- `FLASK_RUN_HOST`: Binding address (0.0.0.0 for container access)
- `DATABASE`: Path to SQLite database file
- `MQTT_BROKER_URL`: Internal Docker network address of the MQTT broker

### Development Mode

The project includes Docker Compose watch mode for development:

```bash
docker compose watch
```

This enables:

- Automatic syncing of local file changes to the container
- Container rebuilds when dependencies change (via uv.lock)

## Architecture Details

### MQTT Broker (Eclipse Mosquitto)

The MQTT broker handles communication between IoT devices and the backend system. Lightweight and efficient.

### SQLite Database

The database stores:

- Device information (MAC addresses, names, types)
- Sensor readings with timestamps

The SQLite file is stored in a Docker volume for persistence between container restarts.

### Flask Web Application

The Flask application (`app.py`) serves dual purposes:

1. **MQTT Client**: Subscribes to device topics and processes incoming messages
   - Subscribes to two specific topic patterns:
     - `MQTT_GATEWAY_TOPIC/#` for gateway device messages (with RSSI data)
     - `MQTT_TEMPERATURE_TOPIC/#` for temperature sensor data
   - Automatically timestamps incoming messages
   - Validates message content before database insertion

2. **Web Interface and API**: Provides visualization and programmatic access
   - Main routes (`/`, `/devices`, `/gateway-readings`, `/sensor-temperature-readings`)
   - RESTful API endpoints with proper validation and error handling
   - Support for date range filtering of sensor readings

#### Key Components

- **Database Management**: SQLite connection pooling with application context
  - `get_db()`: Provides singleton database connections
  - `query_db()`: Executes SQL with transaction support
  - `close_connection()`: Ensures proper connection cleanup

- **Message Processing**:
  - `process_gateway_data()`: Validates and stores gateway RSSI readings
  - `process_sensor_temp_data()`: Validates and stores temperature readings

- **MQTT Integration**:
  - `handle_mqtt_message()`: Processes incoming MQTT messages
  - `handle_connect()`: Manages broker connections and topic subscriptions

- **Testing Endpoints**:
  - `/api/publish-gateway-test`: Simulates gateway messages for testing
  - `/api/publish-temperature-test`: Simulates temperature sensor messages

## Usage

### Connecting Devices

IoT devices need to:

1. Connect to the MQTT broker at `host_ip:1883`
2. Publish data to topics following the pattern: `device/{mac_address}/data`
3. Subscribe to topics for receiving commands: `device/{mac_address}/command`

### API Endpoints

The Flask application provides these RESTful API endpoints:

- `GET /api/devices`: Lists all devices, with optional filtering by internal_id
- `GET /api/gateway-readings?macAddress=<mac>&readingsFrom=<date>&readingsTo=<date>`: Get gateway readings with optional date filtering
- `POST /api/gateway-readings`: Submit new gateway reading (requires JSON with macAddress, timestamp, rssi)
- `GET /api/sensor-temperature-readings?macAddress=<mac>&readingsFrom=<date>&readingsTo=<date>`: Get temperature readings with optional date filtering
- `POST /api/sensor-temperature-readings`: Submit new temperature reading (requires JSON with macAddress, timestamp, temperature)
- `POST /api/publish-gateway-test`: Test endpoint that publishes sample gateway data to MQTT
- `POST /api/publish-temperature-test`: Test endpoint that publishes sample temperature data to MQTT

### Web Interface

Minimalist web interface provides:

- Device dashboard that shows all registered devices
- Gateway readings view with signal strength history
- Temperature readings view with temperature history
- Date range filtering for all historical data
- Device selection dropdowns filtered by device type

## Further Development

Potential enhancements for this project:

1. Add user authentication for the web interface
2. Implement MQTT authentication for device security
3. Add data export/import functionality
4. Create alert systems for anomalous readings
5. Add time-series visualization for long-term trends
6. Implement device firmware update functionality via MQTT

## Conclusion

This minimalist IoT stack provides a solid foundation for collecting, storing, and visualizing data from connected devices. Its containerized architecture ensures easy deployment and maintenance, while the combination of MQTT, SQLite, and Flask offers a balanced approach to IoT backend development without the complexity and resource requirements of larger solutions.

The project demonstrates how working IoT systems can be built with lightweight, open-source components that can run on modest hardware while still providing reliable data handling and visualization capabilities.

## References

- [Eclipse Mosquitto Documentation](https://mosquitto.org/documentation/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [MQTT Protocol Specification](https://mqtt.org/mqtt-specification/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Flask-MQTT Extension](https://flask-mqtt.readthedocs.io/)
