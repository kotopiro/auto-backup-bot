#!/bin/bash

echo "🚀 Auto Backup Bot - Starting..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please copy .env.example to .env and configure it."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check required variables
required_vars=("BOT_TOKEN" "DISCORD_CLIENT_ID" "DISCORD_CLIENT_SECRET" "TURNSTILE_SITE_KEY" "TURNSTILE_SECRET_KEY")

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required environment variable: $var"
        exit 1
    fi
done

echo "✅ Environment variables loaded"

# Create data directory
mkdir -p data
echo "✅ Data directory created"

# Start web server in background
echo "🌐 Starting web server..."
python -m web.app &
WEB_PID=$!
echo "✅ Web server started (PID: $WEB_PID)"

# Wait for web server to start
sleep 3

# Start Discord bot
echo "🤖 Starting Discord bot..."
python -m bot.main &
BOT_PID=$!
echo "✅ Discord bot started (PID: $BOT_PID)"

# Function to handle shutdown
shutdown() {
    echo ""
    echo "🛑 Shutting down..."
    kill $WEB_PID $BOT_PID 2>/dev/null
    wait $WEB_PID $BOT_PID 2>/dev/null
    echo "✅ Shutdown complete"
    exit 0
}

# Trap SIGINT and SIGTERM
trap shutdown SIGINT SIGTERM

echo ""
echo "✨ Auto Backup Bot is running!"
echo "📝 Web interface: http://localhost:5000"
echo "🤖 Bot status: Running"
echo "Press Ctrl+C to stop"
echo ""

# Wait for processes
wait $WEB_PID $BOT_PID
