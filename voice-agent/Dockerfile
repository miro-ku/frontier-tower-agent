FROM python:3.12-slim

# Install Node.js for Unbrowse
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Unbrowse globally
RUN npm install -g unbrowse

# Copy app
COPY . .

# Start script launches Unbrowse + Python worker
CMD ["bash", "start.sh"]
