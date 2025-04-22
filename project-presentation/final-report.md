---
geometry: margin=3cm
---

# Final Report for IFT-744 Advanced IoT session project

**Student:**

- Name: Simon Lalonde
- CIP: lals2906
- Email: <lals2906@usherbrooke.ca>

**Assignement**

- Course: IFT744 - Advanced Topics in Networking and IoT
- Professor: Dr. Bessam Abdulrazak
- Date:  April 25th 2025

**Project**

_Rust‑Based IoT Gateway for Network Coverage Optimization: Real‑Time Temperature and RSSI Monitoring with data logging in vendor-agnostic cloud storage_

## Project Overview

The project aims to develop a Rust-based firmware for an IoT gateway that
optimizes network coverage for temperature sensor nodes in a cold-chain
monitoring solution with a focus on real-time data collection and logging to a
portable and vendor-agnostic cloud/backend storage solution.

The gateway is based on an Industrial grade ESP32-WROOM32 module by Norvi
(Norvi IIOT AE04[1]), which is a low-power microcontroller with built-in Wi-Fi
and Bluetooth capabilities including an LCD display for real-time monitoring of
the temperature data and Wifi signal strength for optimizing the placement of
the gateway.

The firmware is developped in Rust[2] for its memory safety and performance
benefits while taking advantage of the Embassy Async framework[3] for
asynchronous programming and compatibility with Espressif's HAL[4] (Hardware
Abstraction Layer) for the ESP32 platform.

The cloud backend leverages Docker containers[5] to provide a portable and
vendor-agnostic solution for data storage and processing. By using Mosquitto
MQTT broker[6], a SQLite Database[7], and a Flask web server[8], the backend
is designed to be easily deployable on any cloud platform, allowing for
flexibility in choosing the best solution for the specific use case.

## Problem Statement

### Needs of IoT Cold-Chain Monitoring and Gaps in current Solutions

Cold-chain monitoring is essential for ensuring the integrity of temperature-sensitive
products, such as pharmaceuticals and food items, during transportation and storage.
Recent literature projects often only rely on a single Arduino node and
breakout board sensors [9] with/or without a display [10] or tied to a single cloud provider [11].
Also, most of the solutions hardware are on developments boards such as Arduino or Raspberry Pi not suitable
for production use.
Finally, commercial solutions often are too expensive for small-scale deployments or tied to a single cloud provider [12, 13].

One of the main challenges in large environments is the optimization of network coverage for
the sensor nodes, which can be affected by various factors such as distance, obstacles, and
interference of low range protocols such as Wifi and Bluetooth[14].

This is why using a sensor mesh network
is key to have a simple to deploy solution with a single gateway to cloud and multiple sensor nodes
that can cover a wider area while having only a single point of access to the cloud.

### Objectives of this project

The main objectives of this project are:

- Develop a Rust-based firmware for an IoT gateway that can optimize network coverage for temperature sensor nodes in a cold-chain monitoring solution.
- Have reliable hardware for the gateway and sensor nodes that can be used in production and using industrial grade sensors (PT100, DS18B20, etc.)
- Focus on both real-time monitoring with display and data logging to cloud
- Provide a portable and vendor-agnostic cloud/backend storage solution that can be easily deployed on any cloud platform or on-premises.

Even though the initial goal of the project was to have the sensor mesh network, we still managed to
have the gateway and the cloud backend working with a single sensor node which is enough to demonstrate the
concept of the project.

## Methodology

### Hardware

The hardware used for this project is the Norvi IIOT AE04[1], which is an
industrial-grade ESP32-WROOM32 module with built-in Wi-Fi, Bluetooth and OLED display. By leveraging its
Analog to Digital Converter (ADC) and GPIO pins, the module can be used to also connect other hardware such as custom PCBs and sensors (see [Fig. 1](./media/figure-1.jpeg)).

The sensor used is a PT100 temperature sensor, which is a high-precision
temperature sensor that can be used for cold-chain monitoring. The PT100 sensor is connected to the
Norvi IIOT AE04 module using a custom PCB that includes an ADC and a digital-to-analog converter (DAC) to convert the analog signal from the PT100 sensor to a digital signal that can be read by the ESP32 module.
This would be a similar setup on the sensor nodes, but with a smaller PCB and a battery for portability.

### Software

#### Bare Metal Rust Firmware on ESP32 with Embassy

\
The firmware is developed in Rust[2] using the Embassy Async framework[3] for
asynchronous programming and compatibility with Espressif's (Xtensa CPU/ESP32 MCU maker) HAL[4] crates.

By compiling the binary with the `SSID` (in the `.cargo/config.toml`) and `SSID_PASSWORD` environment variables,
we can have a portable solution that can be deployed easily on any Wifi network.

Using the `esp` toolchain with `rustup`, we can flash the firmware on the ESP32 module using the `espflash` command. All the project dependencies are managed by `cargo`, making the firmware fully open-sourced regardless of the MCU (even in this case the ESP32). Easily flash via serial wire using a micro-USB cable.

#### Cloud Backend

\
The cloud backend is developed in Python using Flask[8] for the web server (which also acts as a PubSub interface with the MQTT broker) and SQLite[7] for the database. The Mosquitto MQTT broker[6] is used to receive the data from the ESP32 module and store it in the SQLite database.

All the components are containerized using Docker[5] as services using the Docker Compose API[15].
By using a file-based volume for the SQLite database, the database is resilient to container restarts and can be easily backed up or migrated to another cloud provider or other on-premise hardware.

Each component of the cloud backend can be configured:

- `mosquitto.conf`: Security settings, port mapping etc.
- `config.py`: Flask application settings, such as the database path and MQTT broker URL, TLS settings, etc.
- `init.sql`: SQLite database initialization script, which creates the necessary tables and indexes for the application.

## IoT Architecture

Even though the project is incomplete, the architecture still covers an end-to-end solution for
cold-chain monitoring with a single gateway and eventual sensor node additions.
On the backend side, no cloud provider is used, but the solution is portable and can be deployed on any cloud provider or on-premise hardware.

A full architecture diagram can be seen in [Fig. 2](./media/figure-2.jpeg).

### Gateway hardware setup

Using custom PCBs, the gateway can be modded to add additional analog sensors (such as PT100, DS18B20, etc.) and digital sensors (such as DHT11, DHT22, etc.) to monitor the temperature and humidity of the environment if no sensor nodes are used.

The wiring diagram for the gateway can be seen in [Fig. 3](./media/figure-3.jpeg).

### Gateway/sensor node firmware

The firmware is structured in 2 main compilation binaries, 1 for the gateway and 1 for the sensor nodes.
Only the gateway is fully implemented and working which can be found in `src/bin/main_gateway.rs`.

The main gateway contains the main loop which initializes the ADC, the display and spawns the connection and display refresh tasks.
Since both sensor nodes and gateway are ESP32 based, the `common` modules include a `wifi.rs` and `temperature.rs` modules
that are shared between the two binaries. Only the `display.rs` is specific to the gateway.

By separating modules into different files, we can easily add new features and functionalities to the project. The main modules are:

- `gateway_lib`: Contains the `display.rs` and `requests.rs` modules that handle the display and http requests for Internet API calls.
Also the `rng.rs` provides a simple random number generator for the ESP32 module to simulate temperature readings.
- `common`: Contains the `wifi.rs` and `temperature.rs` modules that handle the wifi connection and potentially the temperature sensor readings.
- `main_gateway`: Contains the main loop for the gateway and the tasks that are spawned for the display, wifi connection, RSSI and temperature data updates
and MQTT-related actions (connecting to the MQTT broker, publishing to topics, etc.).

The flow chart for the gateway firmware can be seen in [Fig. 4](./media/figure-4.png).

### Backend infrastructure

The backend architecture follows a 'microservices-like' approach with three main components, each with their own responsabilities:

1. **MQTT Broker**: Eclipse Mosquitto  handles communication between IoT devices and the backend system. Lightweight and efficient.

2. **SQLite Database**: A lightweight, file-based SQL database that stores device data persistently with minimal resource requirements.

The database stores:

- Device information (MAC addresses, names, types)
- Gateway RSSI signal strength values
- Sensor readings with timestamps

3. **Flask Application**: A Python web application (`app.py`) that serves a dual purpose:

- **MQTT Client**: Subscribes to device topics and processes incoming messages
  - Subscribes to two specific topic patterns:
    - `MQTT_GATEWAY_TOPIC/#` for gateway device messages (with RSSI data)
    - `MQTT_TEMPERATURE_TOPIC/#` for temperature sensor data
  - Automatically timestamps incoming messages
  - Validates message content before database insertion

- **Web Interface and API**: Provides visualization and programmatic access
  - Main routes (`/`, `/devices`, `/gateway-readings`, `/sensor-temperature-readings`)
  - RESTful API endpoints with  validation and error handling
  - Support for date range filtering of sensor readings
  - Subscribes to MQTT topics to receive device data
  - Processes and stores incoming messages in the SQLite database
  - Provides a web interface for data visualization and device management
  - Enables publishing messages back to devices via MQTT

Thus, we can have a fully functional web application that can be used to monitor the temperature and RSSI values of the gateway and sensor nodes
while also providing a RESTful API to access the data programmatically, data persistence with a SQL database and
a MQTT broker to communicate with the devices.

#### Docker Compose

\

Since the backend is containerized using Docker Compose, we can easily deploy the application on any cloud provider or on-premise hardware.
By leveraging Docker's DNS resolution[16], we can use the service names as hostnames to communicate between the different components of the application thus
simplifying the configuration and deployment process.

Again, we can see the encompassing network in the architecture diagram in [Fig. 2](./media/figure-2.jpeg).

## Results and test cases

The project is still in its early stages, but certain milestones have been achieved on both the firmware and backend side.

### Achievements

#### Firmware

\

- Connection task (with constant reconnection) of the ESP32 Gateway to Wifi
- Working display with RSSI and temperature values
- Connection to the MQTT broker and publishing of RSSI and temperature values

#### MQTT-SQL-Web API backend

\

- Docker Compose setup with Mosquitto, SQLite and Flask
- SQLite database with tables for devices, readings and gateway RSSI values
- Flask web application with RESTful API endpoints for CRUD operations

## References

[1]: Norvi. (2025). NORVI IIOT-AE04-I – Datasheet. <https://www.norvi.lk/docs/norvi-iiot-ae04-i-datasheet/>

[2]: Rust Foundation. (2023). Rust Programming Language. <https://www.rust-lang.org/>

[3]: Embassy Project. (2023). Embassy - Embedded Async Framework. <https://embassy.dev/>

[4]: ESP-RS Team. (2023). ESP-HAL - Hardware Abstraction Layer for Espressif chips. <https://github.com/esp-rs/esp-hal>

[5]: Docker, Inc. (2023). Docker - Build, Share, and Run Any App, Anywhere. <https://www.docker.com/>

[6]: Eclipse Foundation. (2023). Eclipse Mosquitto - An open source MQTT broker. <https://mosquitto.org/>

[7]: SQLite Consortium. (2023). SQLite - A C-language library that implements a small, fast, self-contained SQL database engine. <https://www.sqlite.org/>

[8]: Pallets Team. (2023). Flask - Python web development, one drop at a time. <https://flask.palletsprojects.com/>

[9]: Durgaprasad Kamat _et al._ (2024). IOT Based Cold Management Chain. _IJRASET_. <https://doi.org/10.22214/ijraset.2024.60986>

[10]: Kumar Baghel _el al._ (2024). IoT-Based Integrated Sensing and Logging Solution for Cold Chain Monitoring Applications. _IEEE Journal of Radio Frequency Identification_. <https://doi.org/10.1109/JRFID.2024.3488534>

[11]: Alshadi _et al._ (2024). An IoT Smart System for Cold Supply Chain Storage and Transportation Management. _ETASR_. <http://dx.doi.org/10.48084/etasr.6857>

[12]: Pakala and Agrawal (2022). Impacting Food Waste & Foodborne Illness with AWS IoT Core for LoRaWAN Cold-Chain Sensors. AWS Whitepaper. <https://aws.amazon.com/blogs/iot/connectedfresh-aws-iot-lorawan-food-travel/>

[13]: Koretz (2019). Securing the pharmaceutical supply chain with Azure IoT. Microsoft Whitepaper. <https://azure.microsoft.com/en-us/blog/securing-the-pharmaceutical-supply-chain>

[14]: Meguerdichian _et al._ (2001). Coverage Problems in Wireless Ad-hoc Sensor Networks. IEEE INFOCOM. <http://doi.org/10.1109/INFCOM.2001.916633>

[15]: Docker, Inc. (2023). Docker Compose - Define and run multi-container applications with Docker. <https://docs.docker.com/compose/>

[16]: Docker, Inc. (2023). Networking overview. <https://docs.docker.com/engine/network/>
