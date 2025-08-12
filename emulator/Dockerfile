FROM python:3.11-slim

WORKDIR /app

# Copy the application code
COPY . .

# Install Python requirements
RUN pip install -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/screenshots

# Enable demo mode by default
ENV DEMO_MODE=true

EXPOSE 5555

# Start backend service only (no emulator)
CMD ["uvicorn", "emulator_web:app", "--host", "0.0.0.0", "--port", "5555"]