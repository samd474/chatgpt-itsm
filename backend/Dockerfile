FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

# libmagic1 lets python-magic inspect upload signatures instead of trusting the browser's MIME type.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libmagic1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
