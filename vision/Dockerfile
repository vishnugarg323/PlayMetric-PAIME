# Vision AI Service - LLaVA/GPT-4V/Gemini
FROM playmetric-base-ml:latest

WORKDIR /app

# Copy requirements (only vision-specific dependencies)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY src/ ./src/

# Create model cache directory
RUN mkdir -p /data/models

# Expose port
EXPOSE 8006

# Run the vision service
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8006"]
