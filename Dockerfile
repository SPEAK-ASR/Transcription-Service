# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files (with service account key included via .dockerignore changes)
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Set the Google Application Credentials environment variable
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/keys/service-account-key.json

# The service account key path will be set during runtime
# Google recommends not setting credentials in the Dockerfile
# Instead, mount the volume or set it as an environment variable during deployment

# Create a non-root user and change permissions
RUN addgroup --system app && adduser --system --group app \
    && chown -R app:app /app

# Switch to non-root user
USER app

# Command to run the application in production mode with gunicorn
# Uses the PORT environment variable provided by Cloud Run
CMD ["sh", "-c", "gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000}"]