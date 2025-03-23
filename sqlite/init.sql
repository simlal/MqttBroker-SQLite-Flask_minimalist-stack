CREATE TABLE esp32_temperatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    temperature REAL NOT NULL,
    received_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    gateway_rssi INTEGER
);
