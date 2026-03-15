#!/bin/bash
# Start Unbrowse server in background
echo "[start] Starting Unbrowse server..."
unbrowse serve &
sleep 3

# Start the Python voice agent worker
echo "[start] Starting voice agent worker..."
exec python main.py
