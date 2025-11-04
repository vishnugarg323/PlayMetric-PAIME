# Android Emulator with VNC support
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    openjdk-11-jdk \
    wget \
    unzip \
    x11vnc \
    xvfb \
    supervisor \
    socat \
    libglu1-mesa \
    libpulse0 \
    libnss3 \
    libxcomposite1 \
    libxcursor1 \
    libxi6 \
    libxtst6 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV PATH=${PATH}:${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools:${ANDROID_SDK_ROOT}/emulator

# Download and install Android SDK
RUN mkdir -p ${ANDROID_SDK_ROOT}/cmdline-tools && \
    cd ${ANDROID_SDK_ROOT}/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip && \
    unzip commandlinetools-linux-9477386_latest.zip && \
    mv cmdline-tools latest && \
    rm commandlinetools-linux-9477386_latest.zip

# Accept licenses and install SDK packages (ARM for non-KVM support)
RUN yes | sdkmanager --licenses && \
    sdkmanager "platform-tools" "platforms;android-30" "system-images;android-30;google_apis_playstore;arm64-v8a" "emulator"

# Set HOME for AVD creation
ENV HOME=/root

# Create AVD (ARM for Windows Docker compatibility)
RUN echo "no" | avdmanager create avd \
    -n test_device \
    -k "system-images;android-30;google_apis_playstore;arm64-v8a" \
    -d "pixel_4" \
    --force

# Verify AVD was created
RUN ls -la /root/.android/avd/ && \
    ${ANDROID_SDK_ROOT}/emulator/emulator -list-avds

# Create supervisor config
RUN mkdir -p /var/log/supervisor

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose VNC port and ADB port
EXPOSE 5900 5554 5555

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
