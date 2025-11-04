FROM python:3.11-slim

WORKDIR /app

# Install Android SDK platform tools (for ADB)
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    && wget -q https://dl.google.com/android/repository/platform-tools-latest-linux.zip \
    && unzip platform-tools-latest-linux.zip -d /opt \
    && rm platform-tools-latest-linux.zip \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/platform-tools:${PATH}"

# Copy requirements from emulator_manager directory
COPY emulator_manager/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module from root
COPY shared /app/shared

# Copy source code from emulator_manager directory
COPY emulator_manager/src /app/src

CMD ["python", "-m", "src.main"]
