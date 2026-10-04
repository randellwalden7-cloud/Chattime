#!/bin/sh
set -eu
# Railway mounts persistent volumes as root. Drop privileges before serving.
mkdir -p /app/data
chown chattime:chattime /app/data
exec python start_server.py
