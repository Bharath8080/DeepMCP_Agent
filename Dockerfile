# Use a lighter, stable base image (3.10/3.11 has more prebuilt wheels)
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CHAINLIT_HOST=0.0.0.0 \
    CHAINLIT_PORT=8000 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install only what’s really needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python dependencies (parallel, faster)
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

# Copy only app code (cached layers preserved if requirements.txt unchanged)
COPY . .

# Create non-root user
RUN useradd -m myuser && chown -R myuser:myuser /app
USER myuser

# Expose port
EXPOSE 8000

# Run Chainlit
CMD ["chainlit", "run", "app.py", "--port", "8000", "--host", "0.0.0.0"]
