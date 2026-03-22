FROM python:3.12-slim

# Good defaults for containers
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# System packages needed for FFmpeg + common media/file handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    file \
    libmagic1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better build caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Optional but nice: run as a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Gunicorn will listen here inside the container
EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "wsgi:application"]