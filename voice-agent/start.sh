#!/bin/bash
# Start Unbrowse server in background (if Node.js available)
if command -v npx &>/dev/null; then
  echo "[start] Starting Unbrowse server..."
  npx unbrowse setup --no-start 2>/dev/null
  npx unbrowse serve &
  UNBROWSE_PID=$!
  echo "[start] Unbrowse started (PID: $UNBROWSE_PID)"
  sleep 2
fi

# Start the Python voice agent worker
echo "[start] Starting voice agent worker..."
exec python main.py
