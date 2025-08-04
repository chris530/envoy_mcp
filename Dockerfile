FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY envoy_mcp.py .

CMD ["fastmcp","run","envoy_mcp.py","--transport","sse","--host","0.0.0.0","--port","8080"]
