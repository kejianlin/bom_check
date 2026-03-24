FROM python:3.10-slim

LABEL maintainer="your-email@company.com"
LABEL description="PLM BOM Validation System"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir flask flask-cors waitress

COPY . .

RUN mkdir -p logs reports temp/uploads && \
    chmod +x bom_validator.py sync/plm_sync.py api_server.py

ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/health')" || exit 1

CMD ["python", "api_server.py"]
