CREATE TABLE temperature_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mesh_id INTEGER REFERENCES devices(id),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    temperature REAL NOT NULL,
    received_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    gateway_id INTEGER REFERENCES devices(id),
    gateway_rssi INTEGER
);

CREATE TABLE devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    internal_id INTEGER NOT NULL,
    mac_address TEXT NOT NULL UNIQUE,
    chip TEXT CHECK(chip IN ('ESP32-WROOM', 'ESP32-WROOM-32D')) NOT NULL,
    info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- insert devices used for project
INSERT INTO devices (internal_id, mac_address, chip, info) VALUES (0, '3C:E9:0E:72:12:4C', 'ESP32-WROOM', 'NORVI_IIOT_GATEWAY');
INSERT INTO devices (internal_id, mac_address, chip, info) VALUES (4, '40:91:51:CB:A4:64', 'ESP32-WROOM-32D', 'MESH_TEMPERATURE_SENSOR_1');
INSERT INTO devices (internal_id, mac_address, chip, info) VALUES (6, 'E0:5A:1B:30:B3:38', 'ESP32-WROOM-32D', 'MESH_TEMPERATURE_SENSOR_2');
