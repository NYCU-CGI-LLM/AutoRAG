# Multi-stage build for efficient uv-based Python application
FROM python:3.10-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Install system dependencies including parsing and OCR support
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libssl-dev \
    libmagic-dev \
    libgl1-mesa-dev \
    libglib2.0-0 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-kor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy the application code
COPY autorag/ ./autorag/
COPY api/ ./api/

# First install autorag package from its directory
WORKDIR /app/autorag
RUN uv pip install --system .

# Back to main app directory and install minimal requirements
WORKDIR /app
COPY requirements_minimal.txt .
RUN pip install -r requirements_minimal.txt

# Back to api directory for API-specific setup
WORKDIR /app/api

# Install additional packages for full functionality
RUN uv pip install --system \
    watchfiles \
    pdf2image \
    bert_score \
    nltk

# Download NLTK models
RUN python3 -c "import nltk; nltk.download('punkt_tab')" && \
    python3 -c "import nltk; nltk.download('averaged_perceptron_tagger_eng')"

# Copy and run import test
COPY test_autorag_import.py .
RUN python test_autorag_import.py && rm test_autorag_import.py

# Add autorag to Python path so it can be imported
ENV PYTHONPATH="/app:/app/autorag:${PYTHONPATH}"

# Create necessary directories
RUN mkdir -p celerybeat ../projects

# Copy and setup entrypoint script from build context
COPY api/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    sed -i 's/\r$//' /entrypoint.sh

# Expose ports
EXPOSE 8000 7690 8501 8100

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"] 