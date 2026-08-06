FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt-get/lists/*

# Set timezone
ENV TZ=Asia/Phnom_Penh

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pytz

COPY . .

CMD ["python", "bot.py"]
