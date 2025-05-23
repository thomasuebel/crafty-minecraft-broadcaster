# Start with a slim Python base image
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install build dependencies and runtime dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# Start with a clean, minimal image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY crafty_api.py minecraft_broadcaster.py web_server.py main.py ./

# Set environment variables with default values
ENV CRAFTY_API_URL="https://localhost:8443/api/v2" \
    CRAFTY_USERNAME="" \
    CRAFTY_PASSWORD="" \
    BROADCAST_IP="255.255.255.255" \
    MINECRAFT_BROADCAST_PORT=4445 \
    CHECK_INTERVAL=30 \
    ENABLE_WEB_SERVER="true" \
    WEB_SERVER_HOST="0.0.0.0" \
    WEB_SERVER_PORT=8080 \
    TEMPLATES_DIR="/app/templates"

# Expose web server port
EXPOSE 8080

# Run script
CMD ["python", "main.py"]