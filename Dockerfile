FROM python:3.9-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install Playwright and browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy your app
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
