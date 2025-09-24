# Multi-stage build for Pyserv  framework
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r pyserv  && useradd -r -g pyserv  pyserv 

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM base as production

# Copy application code
COPY src/ ./src/
COPY setup.py .
COPY README.md .

# Install the package
RUN pip install -e .

# Create logs directory
RUN mkdir -p /app/logs && chown -R pyserv :pyserv  /app

# Switch to non-root user
USER pyserv 

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "-c", "from pyserv import Application; app = Application(); app.run(host='0.0.0.0', port=8000)"]

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    pytest-xdist \
    black \
    isort \
    flake8 \
    mypy \
    bandit \
    safety \
    coverage

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/
COPY setup.py .
COPY pytest.ini .
COPY README.md .

# Install in development mode
RUN pip install -e .

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8000

# Default command for development
CMD ["python", "-m", "pyserv .cli", "start", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Testing stage
FROM development as testing

# Run tests
RUN pytest tests/ -v --cov=src/pyserv --cov-report=xml --cov-report=term-missing

# Build stage for CI/CD
FROM base as builder

# Copy application code
COPY src/ ./src/
COPY setup.py .

# Build wheel
RUN pip install build && python -m build --wheel

# Final production image with wheel
FROM base as production-wheel

# Copy wheel from builder
COPY --from=builder /app/dist/*.whl /tmp/

# Install from wheel
RUN pip install /tmp/*.whl && rm /tmp/*.whl

# Create non-root user and directories
RUN groupadd -r pyserv  && useradd -r -g pyserv  pyserv  && \
    mkdir -p /app/logs && chown -R pyserv :pyserv  /app

USER pyserv 

EXPOSE 8000

CMD ["python", "-c", "from pyserv import Application; app = Application(); app.run(host='0.0.0.0', port=8000)"]




