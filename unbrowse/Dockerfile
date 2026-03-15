FROM node:22-slim

RUN apt-get update && apt-get install -y socat && rm -rf /var/lib/apt/lists/*
RUN npm install -g unbrowse

# Pre-accept ToS by creating config
RUN mkdir -p /root/.unbrowse && echo '{"tos_accepted":true}' > /root/.unbrowse/config.json

EXPOSE 8080

# Start Unbrowse, then proxy 0.0.0.0:8080 → localhost:6969
CMD unbrowse setup --skip-browser --no-start 2>/dev/null; \
    unbrowse health & \
    sleep 5 && \
    socat TCP-LISTEN:8080,fork,reuseaddr,bind=0.0.0.0 TCP:127.0.0.1:6969
