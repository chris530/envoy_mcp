FROM python:3.11-slim

# Install dependencies for Go and pprof
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Go
ENV GO_VERSION=1.22.2
RUN curl -LO https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz \
    && rm go${GO_VERSION}.linux-amd64.tar.gz

# Add Go to PATH
ENV PATH="/usr/local/go/bin:${PATH}"

# Install pprof CLI
RUN go install github.com/google/pprof@latest

# Add Go bin to PATH so pprof is available
ENV PATH="/root/go/bin:${PATH}"

# Set workdir and install Python deps
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY envoy_mcp.py .

# Default command
CMD ["fastmcp", "run", "envoy_mcp.py", "--transport", "sse", "--host", "0.0.0.0", "--port", "8080"]

