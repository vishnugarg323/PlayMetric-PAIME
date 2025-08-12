FROM python:3.11-slim

WORKDIR /app

# Copy the application code
COPY . .

# Install system dependencies and emulator requirements
RUN apt-get update && apt-get install -y wget unzip libgl1-mesa-dev default-jre

# Set up Android SDK paths
ENV ANDROID_HOME=/sdk
ENV PATH=$PATH:/sdk/cmdline-tools/latest/bin:/sdk/platform-tools:/sdk/emulator

# Download and install Android command line tools
RUN mkdir -p /sdk/cmdline-tools && \
    wget https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip -O /sdk/cmdline-tools.zip && \
    unzip /sdk/cmdline-tools.zip -d /sdk/cmdline-tools && \
    mv /sdk/cmdline-tools/cmdline-tools /sdk/cmdline-tools/latest && \
    rm /sdk/cmdline-tools.zip

# Install platform-tools, emulator, and ARM system image (no KVM required)
RUN yes | /sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=/sdk "platform-tools" "emulator" "system-images;android-30;google_apis;arm64-v8a"

# Create AVD with ARM image
RUN echo "no" | /sdk/cmdline-tools/latest/bin/avdmanager create avd -n test_avd -k "system-images;android-30;google_apis;arm64-v8a" --device "pixel"

# Install Python requirements
RUN pip install -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/screenshots

EXPOSE 5555

# Start emulator and service on container startup
CMD emulator -avd test_avd -no-window -no-audio -gpu off & \
    sleep 60 && \
    adb devices && \
    uvicorn emulator_web:app --host 0.0.0.0 --port 5555