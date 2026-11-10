# Autonomous Scholarship Research Agent Container
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY core/ /app/core/

# Run as non-root user for container security
RUN useradd -u 1001 -m appuser && chown -R appuser:appuser /app
USER appuser

# Cloud Run Job Entrypoint
ENTRYPOINT ["python", "core/runner.py"]
CMD ["--limit", "5"]

