FROM node:22-slim

RUN apt-get update && apt-get install -y socat && rm -rf /var/lib/apt/lists/*
RUN npm install -g unbrowse

EXPOSE 8080

# Start Unbrowse on localhost:6969, proxy 0.0.0.0:8080 → localhost:6969
CMD echo "y" | unbrowse setup --skip-browser & \
    sleep 5 && \
    socat TCP-LISTEN:8080,fork,reuseaddr,bind=0.0.0.0 TCP:127.0.0.1:6969
