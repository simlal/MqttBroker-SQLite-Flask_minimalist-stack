#!/bin/sh

# Copy prebuilt db.sqlite to /db only if it doesn't exist
if [ ! -f /db/db.sqlite ]; then
  echo "Initializing database..."
  cp /tmp/db.sqlite /db/db.sqlite
else
  echo "Database already initialized."
fi

# logging schema
echo "Database initialized with schema:"

sqlite3 /db/db.sqlite ".schema"
# If no arguments are provided, keep the container running
if [ $# -eq 0 ]; then
  echo "No command provided, keeping container alive..."
  exec tail -f /dev/null
else
  exec "$@"
fi
