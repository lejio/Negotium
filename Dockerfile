# ─────────────────────────────────────────────────────────────────────
# Negotium — Dockerfile
#
# Bundles Python 3.13, Chromium, ChromeDriver, and all pip packages
# into a single container. No host setup required.
#
# Build:  docker build -t negotium .
# Run:    docker run --rm --env-file .env negotium
# ─────────────────────────────────────────────────────────────────────
FROM python:3.13-slim

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# ── 1. System deps + Chromium ────────────────────────────────────────
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        fonts-liberation \
        libnss3 \
        libxss1 \
        libasound2t64 \
        libatk-bridge2.0-0 \
        libgtk-3-0 \
        wget \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Tell Selenium where to find Chromium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# ── 2. Python dependencies ───────────────────────────────────────────
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── 3. Application code ─────────────────────────────────────────────
COPY . .

# ── 4. Run ───────────────────────────────────────────────────────────
CMD ["python", "main.py"]
