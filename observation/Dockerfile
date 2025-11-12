# Use base image with ADB support pre-installed
ARG BASE_IMAGE=playmetric-base-adb:latest
FROM ${BASE_IMAGE}

# Copy requirements and install only observation-specific dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create data directories
RUN mkdir -p /data/screenshots /data/logs

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the service
CMD ["python", "-m", "src.main"]
