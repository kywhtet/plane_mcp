FROM python:3.12-slim

WORKDIR /app

# Install build dependencies and cleanup
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first for better caching
COPY pyproject.toml .
COPY plane_mcp/ ./plane_mcp/

RUN pip install --no-cache-dir "hatchling" && \
    pip install --no-cache-dir .

EXPOSE 4200

CMD ["python", "-m", "plane_mcp", "--transport", "sse", "--host", "0.0.0.0", "--port", "4200"]
