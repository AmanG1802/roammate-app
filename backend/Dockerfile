FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

COPY . .

RUN chmod +x /app/scripts/decode-secrets.sh

ENTRYPOINT ["/app/scripts/decode-secrets.sh"]
# --proxy-headers + --forwarded-allow-ips="*" let uvicorn trust Railway's
# X-Forwarded-Proto, so absolute redirect URLs (and OAuth callbacks, etc.) are
# built with https:// instead of http://. Without this the edge terminates TLS
# and uvicorn sees plain http, emitting http:// redirects the browser blocks as
# mixed content. Railway is the single trusted hop in front of the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
