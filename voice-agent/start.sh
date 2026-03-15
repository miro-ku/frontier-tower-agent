#!/bin/bash
# Start Unbrowse server in background
echo "[start] Starting Unbrowse server..."
unbrowse setup --skip-browser &
sleep 5

# Start the Python voice agent worker
echo "[start] Starting voice agent worker..."
exec python main.py
