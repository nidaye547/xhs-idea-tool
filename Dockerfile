FROM python:3.11-slim

WORKDIR /app

# Install system deps for playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-unifont \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcursor1 \
    libxext6 \
    libxi6 \
    libxinerama1 \
    libxrandr2 \
    libxrender1 \
    libxshmfence1 \
    libxtst6 \
    libpango-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first, then install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright chromium only
RUN playwright install chromium

COPY . .

CMD ["python", "src/scheduler.py"]
