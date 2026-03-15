#!/bin/bash

# Unbrowse uses port 6969 by default; ensure it doesn't conflict with Railway's PORT
export UNBROWSE_PORT=6969

# Accept Unbrowse ToS and run setup (non-interactive, starts server in background)
echo "[start] Setting up Unbrowse..."
yes | unbrowse setup --skip-browser 2>&1 &
sleep 8

# Verify server is running
if curl -s http://localhost:6969/health > /dev/null 2>&1; then
  echo "[start] Unbrowse server is running on port 6969"
else
  echo "[start] Unbrowse server not available, continuing without it"
fi

# Start the Python voice agent worker
echo "[start] Starting voice agent worker..."
exec python main.py
