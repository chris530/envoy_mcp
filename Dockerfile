FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY envoy_mcp.py .

CMD ["python", "envoy_mcp.py"]
