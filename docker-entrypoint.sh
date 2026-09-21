#!/bin/sh
set -e

if [ ! -f /config/connector.config.json ]; then
    cp /app/configs/connector.config.example.json /config/connector.config.json
fi

exec "$@"