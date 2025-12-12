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

# Copy database schema and scripts
COPY db/init_db.py ./init_db.py
COPY db/clear_db.py ./clear_db.py

# Create data directories
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Create startup script
RUN echo '#!/bin/bash\n\
echo "🔧 Initializing database schema..."\n\
python /app/init_db.py\n\
echo "🚀 Starting orchestrator service..."\n\
python -m src.main\n\
' > /app/start.sh && chmod +x /app/start.sh

# Run the service with initialization
CMD ["/app/start.sh"]
