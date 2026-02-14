FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose web port
EXPOSE 5000

# Create startup script
RUN echo '#!/bin/bash\n\
python -m web.app &\n\
WEB_PID=$!\n\
python -m bot.main &\n\
BOT_PID=$!\n\
wait $WEB_PID $BOT_PID' > /app/start.sh && chmod +x /app/start.sh

# Start both bot and web server
CMD ["/app/start.sh"]
