# Use base image with ADB support pre-installed
ARG BASE_IMAGE=playmetric-base-adb:latest
FROM ${BASE_IMAGE}

# Install aapt for APK analysis (orchestrator-specific)
RUN apt-get update && apt-get install -y \
    aapt \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install only orchestrator-specific dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create data directories
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "src.main_v2"]
