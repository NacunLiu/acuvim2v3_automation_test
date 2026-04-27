FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# OpenCV, Pillow/ImageGrab-related packages, and general build/runtime deps.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libgl1 \
    libglib2.0-0 \
    iputils-ping \
    libsm6 \
    libxext6 \
    libxrender1 \
    nmap \
    scrot \
    x11-apps \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

COPY communication_protocol_test/ /app/

CMD ["python", "run.py"]
# test