# Use base image with ML/CV dependencies pre-installed
ARG BASE_IMAGE=playmetric-base-ml:latest
FROM ${BASE_IMAGE}

# Install Android tools (not in base-ml)
RUN apt-get update && apt-get install -y \
    android-tools-adb \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install only agent-specific dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create data directories
RUN mkdir -p /data/models /agent/data

# Expose port
EXPOSE 8004

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Run the service
CMD ["python", "-m", "src.main_v2"]
