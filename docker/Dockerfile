FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install dependencies with verbose output
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -v -r requirements.txt

# Copy application code
COPY . .

# Install the package in development mode
RUN pip install -e .

# Create necessary directories with proper permissions BEFORE switching to non-root user
RUN mkdir -p db reports knowledge && \
    chmod -R 777 db reports knowledge && \
    touch .env.example && \
    chmod 644 .env* 2>/dev/null || true

# Add the src directory to Python path
ENV PYTHONPATH="/app:/app/research_crew_crew/src:${PYTHONPATH:-}"

# Create a non-root user and switch to it
RUN useradd -m appuser
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1
# Default API key (override this in production with secure value)
ENV API_KEY="dev-api-key"
ENV SERPER_API_KEY=5132e3092ec60bdb8d754fe19c9fd9dd84497b31
ENV OPENAI_API_KEY=""
ENV GITHUB_TOKEN=""

# Load .env file
RUN echo "if [ -f /app/.env ]; then source /app/.env; fi" >> /home/appuser/.bashrc

# Expose the port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "api.api:app", "--host", "0.0.0.0", "--port", "8000"]
