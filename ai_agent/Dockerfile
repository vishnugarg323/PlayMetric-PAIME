FROM paime-base

WORKDIR /app

# Install tesseract for OCR
RUN apt-get update && apt-get install -y tesseract-ocr && rm -rf /var/lib/apt/lists/*

# Copy the application code
COPY . .

# Install AI agent specific packages using cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt \
    # Install torch separately due to special index
    && pip install torch==2.1.0+cpu --index-url https://download.pytorch.org/whl/cpu

# Create necessary directories
RUN mkdir -p /app/logs /app/screenshots /app/shared_cache/ai_knowledge

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["python", "-u", "agent.py"]