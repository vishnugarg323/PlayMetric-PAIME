FROM paime-base

WORKDIR /app

# Copy the application code
COPY . .

# Install backend specific packages using cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/apks /app/logs

# Set environment variable for Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]